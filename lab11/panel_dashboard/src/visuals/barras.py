# src/visuals/barras.py
import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import HoverTool, NumeralTickFormatter
from holoviews import Cycle

hv.extension('bokeh')

_PALETTE = ['#1f77b4','#ff7f0e','#2ca02c','#d62728',
            '#9467bd','#e377c2','#7f7f7f','#bcbd22']

def _unmute_on_init(plot, element):
    # fuerza que nada arranque “muted”
    for r in plot.state.renderers:
        if hasattr(r, "muted"):
            r.muted = False

def _ensure_fecha(df: pd.DataFrame) -> pd.Series | pd.DatetimeIndex:
    """Devuelve la columna/índice de fechas como Series o DatetimeIndex."""
    if 'fecha' in df.columns:
        return pd.to_datetime(df['fecha'])
    return pd.to_datetime(df.index)


def _to_period_labels(fechas, freq: str) -> pd.Index | pd.Series:
    """
    Convierte fechas (Series o DatetimeIndex) a etiquetas de periodo (Año o Trimestre)
    devolviendo strings (para eje X categórico).
    """
    if isinstance(fechas, pd.DatetimeIndex):
        if freq == "Año":
            return fechas.year.astype(str)
        else:  # Trimestre
            return fechas.to_period('Q').astype(str)
    else:  # Series
        s = pd.to_datetime(fechas)
        if freq == "Año":
            return s.dt.year.astype(str)
        else:
            return s.dt.to_period('Q').astype(str)

def _nice_hover_bars(plot, element):
    """Un HoverTool por renderer (stack) con tooltips correctos."""
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
            tooltips=[
                ("Periodo", "@Periodo"),
                ("Valor", f"@{{{col}}}{{0,0.##}}"),
            ],
            mode="mouse",
        )
        fig.add_tools(ht)

def _force_solid_colors(plot, element):
    fig = plot.state
    for r in fig.renderers:
        g = getattr(r, "glyph", None)
        if g is None:
            continue
        if hasattr(g, "fill_alpha"): g.fill_alpha = 1.0
        if hasattr(g, "line_alpha"): g.line_alpha = 1.0
        ns = getattr(r, "nonselection_glyph", None)
        if ns is not None:
            if hasattr(ns, "fill_alpha"): ns.fill_alpha = 1.0
            if hasattr(ns, "line_alpha"): ns.line_alpha = 1.0
        sg = getattr(r, "selection_glyph", None)
        if sg is not None:
            if hasattr(sg, "fill_alpha"): sg.fill_alpha = 1.0
            if hasattr(sg, "line_alpha"): sg.line_alpha = 1.0
        mg = getattr(r, "muted_glyph", None)
        if mg is not None:
            if hasattr(mg, "fill_alpha"): mg.fill_alpha = 0.25
            if hasattr(mg, "line_alpha"): mg.line_alpha = 0.25

def barras_apiladas_view(df: pd.DataFrame, series_w, range_w):
    """
    Barras apiladas por producto/serie con:
      - Modo: valores absolutos o % del total
      - Frecuencia: Año o Trimestre
      - Selector 'Producto activo' que sincroniza series_w
    """

    # Widgets
    modo_w = pn.widgets.ToggleGroup(
        name="Modo", options=["Valor", "% del total"], value="Valor",
        behavior="radio"
    )
    freq_w = pn.widgets.RadioButtonGroup(
        name="Agregación", options=["Año", "Trimestre"], value="Año"
    )
    activo_w = pn.widgets.Select(name="Producto activo", options=["(Todos)"], value="(Todos)")

    # Cuando el usuario elige un producto activo, sincronizamos el checkbox global
    def _push_active_to_series(event):
        val = event.new
        if val and val != "(Todos)":
            series_w.value = [val]
    activo_w.param.watch(_push_active_to_series, 'value')

    @pn.depends(series_w.param.value, range_w.param.value_throttled,
                modo_w.param.value, freq_w.param.value)
    def _view(series_sel, drange, modo, freq):
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
        periodo_labels = _to_period_labels(fechas_f, freq)
        dff['Periodo'] = periodo_labels

        # Largo → agrupar
        use_cols = ['Periodo'] + list(series_sel)
        long = dff[use_cols].melt(id_vars='Periodo', var_name='Producto', value_name='valor')
        grp = long.groupby(['Periodo', 'Producto'], as_index=False)['valor'].sum()

        # Modo: % del total o valor
        if modo == "% del total":
            tot = grp.groupby('Periodo', as_index=False)['valor'].sum().rename(columns={'valor': 'total'})
            grp = grp.merge(tot, on='Periodo', how='left')
            grp['valor'] = np.where(grp['total'] > 0, grp['valor'] / grp['total'] * 100.0, 0.0)
            ylabel = "Participación (%)"
        else:
            ylabel = "Valor"

        # Pivot para hvplot
        piv = grp.pivot(index='Periodo', columns='Producto', values='valor').fillna(0)

        piv = piv.reset_index()
        ycols = [c for c in piv.columns if c != 'Periodo']

        try:
            if freq == "Trimestre":
                order = pd.PeriodIndex(piv.index, freq='Q').sort_values()
                piv = piv.loc[order.astype(str)]
            else:
                order = pd.Index(piv.index.astype(int)).sort_values()
                piv = piv.loc[order.astype(str)]
        except Exception:
            piv = piv.sort_index()

        # Actualizar opciones del selector "Producto activo"
        opts = ["(Todos)"] + list(piv.columns)
        if activo_w.options != opts:
            activo_w.options = opts

        bars = piv.hvplot.bar(
            x='Periodo', y=ycols,
            stacked=True, height=320, width=900,
            legend='top_left', xlabel="Periodo", ylabel=ylabel,
            color=Cycle(_PALETTE),
            tools=[]
        ).opts(
            legend_muted=True, muted_alpha=0.15,
            yticks=6, 
            yformatter=NumeralTickFormatter(format="0,0"),
            fill_alpha=1.0, line_alpha=1.0,
            nonselection_fill_alpha=1.0,
            nonselection_line_alpha=1.0,
            selection_fill_alpha=1.0, selection_line_alpha=1.0,
            hooks=[_nice_hover_bars, _force_solid_colors, _unmute_on_init]
        )

        return pn.Column(
            pn.pane.Markdown("### 3) Barras apiladas por producto"),
            pn.Row(modo_w, pn.Spacer(width=20), freq_w, pn.Spacer(width=20), activo_w),
            bars
        )

    return pn.Column(_view)
