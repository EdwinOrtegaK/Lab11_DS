import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import HoverTool, NumeralTickFormatter

hv.extension('bokeh')

COLOR_BY_BASE = {
    'Regular': '#1f77b4',
    'Superior': '#ff7f0e',
    'Diesel':   '#2ca02c',
}

def _split_name(col: str):
    try:
        base, suf = col.split('_', 1)
    except ValueError:
        base, suf = col, ''
    return base, suf.lower()

def _hex_to_rgb(hexcolor: str):
    hexcolor = hexcolor.lstrip('#')
    return tuple(int(hexcolor[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def _lighten_hex(hexcolor: str, factor: float = 0.45):
    """Mezcla con blanco; factor 0.0 = mismo color, 1.0 = blanco."""
    r, g, b = _hex_to_rgb(hexcolor)
    lr = int(r + (255 - r) * factor)
    lg = int(g + (255 - g) * factor)
    lb = int(b + (255 - b) * factor)
    return _rgb_to_hex((lr, lg, lb))

def _color_for(col: str) -> str:
    base, suf = _split_name(col)
    base_color = COLOR_BY_BASE.get(base, '#1f77b4')
    return _lighten_hex(base_color, 0.45) if suf.startswith('con') else base_color

def _apply_series_alphas(plot, element):
    """*_Imp opaco; *_Con más tenue."""
    for r in plot.state.renderers:
        name = getattr(r, "name", "") or ""
        is_con = name.lower().endswith('_con')
        g  = getattr(r, "glyph", None)
        ns = getattr(r, "nonselection_glyph", None)
        sg = getattr(r, "selection_glyph", None)
        mg = getattr(r, "muted_glyph", None)

        fa = 0.65 if is_con else 1.0
        la = 0.95 if is_con else 1.0

        for glyph in (g, ns, sg):
            if glyph is None:
                continue
            if hasattr(glyph, "fill_alpha"): glyph.fill_alpha = fa
            if hasattr(glyph, "line_alpha"): glyph.line_alpha = la

        if mg is not None:
            if hasattr(mg, "fill_alpha"): mg.fill_alpha = 0.25
            if hasattr(mg, "line_alpha"): mg.line_alpha = 0.25

def _unmute_on_init(plot, element):
    for r in plot.state.renderers:
        if hasattr(r, "muted"):
            r.muted = False

def _ensure_fecha(df: pd.DataFrame) -> pd.Series | pd.DatetimeIndex:
    """Devuelve la columna/índice de fechas como Series o DatetimeIndex."""
    if 'fecha' in df.columns:
        return pd.to_datetime(df['fecha'])
    return pd.to_datetime(df.index)

def _to_period_labels(fechas, freq: str) -> pd.Index | pd.Series:
    """Convierte fechas a etiquetas de periodo (Año o Trimestre) como strings."""
    if isinstance(fechas, pd.DatetimeIndex):
        if freq == "Año":
            return fechas.year.astype(str)
        else:
            return fechas.to_period('Q').astype(str)
    else:
        s = pd.to_datetime(fechas)
        if freq == "Año":
            return s.dt.year.astype(str)
        else:
            return s.dt.to_period('Q').astype(str)

def _nice_hover_bars(plot, element):
    """Un HoverTool por stack con tooltips correctos."""
    fig = plot.state
    fig.tools = [t for t in fig.tools if not isinstance(t, HoverTool)]

    for r in fig.renderers:
        g = getattr(r, "glyph", None)
        col = getattr(g, "top", None)
        if not isinstance(col, str):
            continue

        r.name = col

        ht = HoverTool(
            renderers=[r],
            tooltips=[("Periodo", "@Periodo"),
                      ("Valor", f"@{{{col}}}{{0,0.##}}")],
            mode="mouse",
        )
        fig.add_tools(ht)

def barras_apiladas_view(df: pd.DataFrame, series_w, range_w):
    """
    Barras apiladas por producto/serie con:
      - Frecuencia: Año o Trimestre
      - Colores consistentes y *_Con* más tenue
    """
    freq_w = pn.widgets.RadioButtonGroup(
        name="Agregación", options=["Año", "Trimestre"], value="Año"
    )

    @pn.depends(series_w.param.value, range_w.param.value_throttled, freq_w.param.value)
    def _view(series_sel, drange, freq):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie para mostrar.**")

        # Filtrar por rango temporal
        fechas = _ensure_fecha(df)
        start, end = pd.to_datetime(drange[0]), pd.to_datetime(drange[1])
        mask = (fechas >= start) & (fechas <= end)
        dff = df.loc[mask].copy()
        fechas_f = fechas[mask]

        if dff.empty:
            return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        # Etiquetas de periodo (Año / Trimestre)
        dff['Periodo'] = _to_period_labels(fechas_f, freq)

        # Largo y agrupar por Periodo/Producto
        use_cols = ['Periodo'] + list(series_sel)
        long = dff[use_cols].melt(id_vars='Periodo', var_name='Producto', value_name='valor')
        grp = long.groupby(['Periodo', 'Producto'], as_index=False)['valor'].sum()

        # Pivot y orden cronológico por Periodo
        piv = grp.pivot(index='Periodo', columns='Producto', values='valor').fillna(0).reset_index()

        if freq == "Trimestre":
            key = pd.PeriodIndex(piv['Periodo'], freq='Q')
            piv = piv.iloc[key.argsort()].reset_index(drop=True)
        else:
            key = piv['Periodo'].astype(int)
            piv = piv.iloc[key.argsort()].reset_index(drop=True)

        ycols = [c for c in piv.columns if c != 'Periodo']

        # Colores por serie según *_Imp vs *_Con
        series_colors = [_color_for(c) for c in ycols]

        bars = piv.hvplot.bar(
            x='Periodo', y=ycols,
            stacked=True, height=320, width=1000,
            legend='top_left', xlabel="Periodo", ylabel="Valor",
            color=series_colors, tools=[]
        ).opts(
            legend_muted=True, muted_alpha=0.15,
            yticks=6,
            yformatter=NumeralTickFormatter(format="0,0"),
            hooks=[_nice_hover_bars, _apply_series_alphas, _unmute_on_init]
        )

        return pn.Column(
            pn.pane.Markdown("### 3) Barras apiladas por producto"),
            pn.Row(freq_w),
            bars
        )

    return pn.Column(_view)
