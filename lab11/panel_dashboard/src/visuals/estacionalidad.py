# src/visuals/estacionalidad.py
import pandas as pd
import numpy as np
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import NumeralTickFormatter, HoverTool
from holoviews import Cycle

hv.extension("bokeh")

# Paleta consistente con el resto
COLOR_BY_BASE = {
    'Regular': '#1f77b4',
    'Superior': '#ff7f0e',
    'Diesel':   '#2ca02c',
}

def _right_header(text: str):
    return pn.pane.Markdown(
        f"### {text}",
        styles={'text-align': 'right', 'margin': '0 8px 6px 0'}
    )

def _style_for(colname: str):
    """
    Devuelve (color, dash) para una columna como 'Regular_Imp' o 'Regular_Con'.
    - Color depende del prefijo base (Regular/Superior/Diesel).
    - Dash es 'solid' para *_Imp y 'dashed' para *_Con.
    """
    try:
        base, suf = colname.split('_', 1)
    except ValueError:
        base, suf = colname, ''
    color = COLOR_BY_BASE.get(base, '#1f77b4')
    dash  = 'dashed' if suf.lower().startswith('con') else 'solid'
    return color, dash

def _legend_tweak(plot, element):
    fig = plot.state
    if getattr(fig, "legend", None):
        lg = fig.legend[0]
        lg.location = "top_left"
        lg.title = "Variable"
        lg.background_fill_alpha = 0.85
        lg.border_line_color = "lightgray"
        lg.spacing = 2
        lg.label_text_font_size = "10pt"
        lg.title_text_font_style = "bold"

def _ensure_fecha(df: pd.DataFrame) -> pd.Series:
    """Devuelve una Serie datetime llamada 'fecha' (desde columna o índice)."""
    if 'fecha' in df.columns:
        f = pd.to_datetime(df['fecha'])
    else:
        f = pd.to_datetime(df.index)
    return f.rename('fecha')

def _pretty_hover(plot, element):
    """Hover con fecha legible y separador de miles."""
    fig = plot.state
    for t in fig.tools:
        if isinstance(t, HoverTool):
            t.tooltips = [
                ("fecha", "@fecha{%F}"),
                ("valor", "$y{0,0}")
            ]
            t.formatters = {"@fecha": "datetime"}
            t.mode = "vline"
            t.point_policy = "snap_to_data"

def estacionalidad_view(df: pd.DataFrame, series_w, range_w):
    """
    Línea + puntos (superpuestos) para todas las series seleccionadas
    en un solo gráfico, filtrado por el DateRangeSlider.
    """
    @pn.depends(series_w.param.value, range_w.param.value_throttled)
    def _view(series_sel, drange):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie.**")

        # Asegurar columna 'fecha' y filtrar por rango
        f = _ensure_fecha(df)
        x = df.copy()
        x = x.assign(fecha=f)
        mask = (x['fecha'] >= pd.to_datetime(drange[0])) & (x['fecha'] <= pd.to_datetime(drange[1]))
        sub = x.loc[mask, ['fecha'] + list(series_sel)].dropna(how='all')

        if sub.empty:
            return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        curves = []
        scatters = []
        for col in series_sel:
            if col not in sub.columns:
                continue
            color, dash = _style_for(col)

            c = sub.hvplot(
                x='fecha', y=col, kind='line',
                color=color, line_dash=dash, line_width=2,
                height=400, width=1200,
                label=col,
                tools=['hover']
            )
            p = sub.hvplot.scatter(
                x='fecha', y=col,
                color=color, size=4, alpha=0.85,
                legend=False, tools=['hover']
            )
            curves.append(c)
            scatters.append(p)

        chart = (hv.Overlay(curves) * hv.Overlay(scatters)).opts(
            width=1000, height=400,
            ylabel='Valor',
            yticks=6,
            yformatter=NumeralTickFormatter(format="0,0"),
            show_legend=True,
            legend_position='top_left',
            legend_muted=False,
            hooks=[_pretty_hover, _legend_tweak],
        )

        return pn.Column(
            _right_header("2) Estacionalidad Mes x Año"),
            pn.pane.HoloViews(chart, width=1000, height=400, sizing_mode='fixed')
        )

    return pn.Column(_view)
