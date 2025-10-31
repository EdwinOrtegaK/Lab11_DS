# src/visuals/caja_violin.py
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import HoverTool, NumeralTickFormatter

hv.extension("bokeh")

COLOR_BY_BASE = {'Regular': '#1f77b4', 'Superior': '#ff7f0e', 'Diesel': '#2ca02c'}

def _right_header(text: str):
    return pn.pane.Markdown(f"### {text}", styles={'text-align': 'right','margin':'0 8px 6px 0'})

def _ensure_fecha(df: pd.DataFrame) -> pd.Series:
    if 'fecha' in df.columns: f = pd.to_datetime(df['fecha'])
    else: f = pd.to_datetime(df.index)
    return f.rename('fecha')

def _pretty_hover(plot, element):
    fig = plot.state
    for t in fig.tools:
        if isinstance(t, HoverTool):
            t.tooltips = [("Mes","@Mes"), ("valor","$y{0,0}")]
            t.mode = "mouse"

def _base_from(col: str) -> str:
    try: base, _ = col.split('_',1)
    except ValueError: base = col
    return base

def caja_violin_view(df: pd.DataFrame, series_w, range_w):
    tipo_w = pn.widgets.RadioButtonGroup(name="Tipo", options=["Caja","Violín"], value="Caja")

    @pn.depends(series_w.param.value, range_w.param.value_throttled, tipo_w.param.value)
    def _view(series_sel, dr, tipo):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie.**")

        f = _ensure_fecha(df)
        x = df.assign(fecha=f).loc[(f>=pd.to_datetime(dr[0])) & (f<=pd.to_datetime(dr[1]))]
        if x.empty:
            return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        x = x.assign(Mes=x['fecha'].dt.month.astype(int))
        long = x[['Mes']+list(series_sel)].melt(id_vars='Mes', var_name='Serie', value_name='valor').dropna()

        plots = []
        for s in series_sel:
            base = _base_from(s)
            color = COLOR_BY_BASE.get(base, '#1f77b4')
            df_s = long[long['Serie']==s]
            if df_s.empty:
                continue

            if tipo == "Caja":
                # Usar by='Mes' (NO pasar x=)
                g = df_s.hvplot.box(
                    y='valor', by='Mes',
                    color=color, width=1000, height=400,
                    ylabel='Valor', xlabel='Mes', legend=False, tools=['hover']
                )
            else:
                # También by='Mes' en violín
                g = df_s.hvplot.violin(
                    y='valor', by='Mes',
                    color=color, width=1000, height=400,
                    ylabel='Valor', xlabel='Mes', legend=False, tools=['hover']
                )

            g = g.opts(hooks=[_pretty_hover], yformatter=NumeralTickFormatter(format="0,0"))
            subtitle = pn.pane.Markdown(f"**{s}**", styles={'text-align':'right','margin':'4px 8px 0 0'})
            plots.append(pn.Column(subtitle, g, sizing_mode="stretch_width"))

        if not plots:
            return pn.pane.Markdown("**Sin datos para las series seleccionadas.**")

        return pn.Column(_right_header("4) Distribución mensual — Caja/Violín"), tipo_w, *plots)

    return pn.Column(_view)