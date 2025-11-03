# src/visuals/real_predicho.py
import pandas as pd
import numpy as np
import panel as pn
import holoviews as hv
import hvplot.pandas
from bokeh.models import HoverTool, NumeralTickFormatter
import param

hv.extension("bokeh")

class _ModelsState(param.Parameterized):
    selected = param.List(default=[])

MODELS_STATE = _ModelsState()

COLOR_BY_BASE = {'Regular': '#1f77b4', 'Superior': '#ff7f0e', 'Diesel': '#2ca02c'}

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    _HAS_SM = True
except Exception:
    _HAS_SM = False

def _right_header(text: str):
    return pn.pane.Markdown(f"### {text}", styles={'text-align':'right','margin':'0 8px 6px 0'})

def _ensure_fecha(df: pd.DataFrame) -> pd.Series:
    if 'fecha' in df.columns: f = pd.to_datetime(df['fecha'])
    else: f = pd.to_datetime(df.index)
    return f.rename('fecha')

def _pretty_hover(plot, element):
    fig = plot.state
    for t in fig.tools:
        if isinstance(t, HoverTool):
            t.tooltips = [("fecha","@fecha{%F}"), ("valor","$y{0,0}")]
            t.formatters = {"@fecha":"datetime"}
            t.mode = "vline"; t.point_policy = "snap_to_data"

def _base_from(col: str) -> str:
    try: base, _ = col.split('_',1)
    except ValueError: base = col
    return base

def _sn12(arr: pd.Series, m=12) -> pd.Series:
    return arr.shift(m)

def _naive(arr: pd.Series) -> pd.Series:
    return arr.shift(1)

def _holt_winters(arr: pd.Series, seasonal_periods=12) -> pd.Series:
    # Devuelve in-sample fitted values alineadas con el índice
    model = ExponentialSmoothing(arr, trend='add', seasonal='add', seasonal_periods=seasonal_periods, initialization_method="estimated")
    res = model.fit(optimized=True)
    return pd.Series(res.fittedvalues, index=arr.index)

def real_predicho_view(df: pd.DataFrame, series_w, range_w):
    modelos = ["Naive","S-Naive(12)"]
    if _HAS_SM: modelos.append("Holt-Winters")

    model_w = pn.widgets.CheckBoxGroup(name="Modelos", options=modelos, value=["Naive"])
    MODELS_STATE.selected = list(model_w.value)

    @pn.depends(model_w.param.value, watch=True)
    def _sync_selected(models):
        # Mantén sincronizado el estado compartido con las checkboxes
        MODELS_STATE.selected = list(models)

    @pn.depends(series_w.param.value, range_w.param.value_throttled, model_w.param.value)
    def _view(series_sel, dr, modelos_sel):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie.**")

        f = _ensure_fecha(df)
        x = df.assign(fecha=f).loc[(f>=pd.to_datetime(dr[0])) & (f<=pd.to_datetime(dr[1]))]
        if x.empty: return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        overlays = []
        for s in series_sel:
            if s not in x.columns: continue
            base = _base_from(s); color = COLOR_BY_BASE.get(base, '#1f77b4')
            ser = x.set_index('fecha')[s].astype(float).dropna()

            if ser.empty: continue

            # Real
            real_line = ser.hvplot.line(width=1000, height=400, color=color, line_width=2, label=f"{s} (Real)",
                                        tools=['hover']).opts(hooks=[_pretty_hover])
            series_ol = real_line

            # Predicciones in-sample (fitted) como líneas punteadas
            if "Naive" in modelos_sel:
                yhat = _naive(ser)
                series_ol *= yhat.hvplot.line(color=color, line_dash='dashed', alpha=0.9, label=f"{s} — Naive")

            if "S-Naive(12)" in modelos_sel:
                yhat = _sn12(ser, 12)
                series_ol *= yhat.hvplot.line(color=color, line_dash='dotted', alpha=0.9, label=f"{s} — S-Naive(12)")

            if "Holt-Winters" in modelos_sel and _HAS_SM:
                try:
                    yhat = _holt_winters(ser, 12)
                    series_ol *= yhat.hvplot.line(color=color, line_dash='dotdash', alpha=0.95, label=f"{s} — Holt-Winters")
                except Exception:
                    pass

            series_ol = series_ol.opts(
                ylabel="Valor", yticks=6, yformatter=NumeralTickFormatter(format="0,0"),
                show_legend=True, legend_position='top_left'
            )
            overlays.append(series_ol)

        if not overlays:
            return pn.pane.Markdown("**No hay datos modelables para las series seleccionadas.**")

        chart = hv.Overlay(overlays)
        return pn.Column(_right_header("6) Real vs Predicho"), model_w, pn.pane.HoloViews(chart, width=1000, height=400, sizing_mode='fixed'))

    return pn.Column(_view)
