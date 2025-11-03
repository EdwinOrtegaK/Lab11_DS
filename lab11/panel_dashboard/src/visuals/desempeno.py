import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas  # noqa
import param
from src.visuals.real_predicho import MODELS_STATE

hv.extension("bokeh")

# =========================
# Paleta
# =========================
COLOR_REAL         = "#111111"
COLOR_NAIVE        = "#9E9E9E"
COLOR_SNAIVE       = "#6E6E6E"
COLOR_HOLTWINTERS  = "#4B4B4B"

COLOR_BY_MODEL = {
    "Naive":         COLOR_NAIVE,
    "S-Naive(12)":   COLOR_SNAIVE,
    "Holt-Winters":  COLOR_HOLTWINTERS,
}

# =========================
# Estado local (opciones)
# =========================
class _PerfState(param.Parameterized):
    metric = param.ObjectSelector(default="RMSE", objects=["RMSE","MAE"])
    accumulated = param.Boolean(default=False, doc="Cumulative mean sobre el horizonte")
    smoothing = param.Integer(default=0, bounds=(0, 10), doc="Ventana de suavizado")
    use_kde = param.Boolean(default=False, doc="Si True usa densidad; si False histograma")

PERF_STATE = _PerfState()

# =========================
# Utils
# =========================
def _right_header(text: str):
    return pn.pane.Markdown(f"### {text}", styles={"text-align":"right","margin":"0 8px 6px 0"})

def _series_scale(df: pd.DataFrame, series_sel) -> float:
    if not series_sel: return 1.0
    cols = [c for c in series_sel if c in df.columns]
    if not cols: return 1.0
    y = df[cols].astype(float)
    return float(np.nanmedian(y.std().values)) if not y.empty else 1.0

def _smooth(y: pd.Series, w: int) -> pd.Series:
    if w and w > 1: return y.rolling(window=w, min_periods=1, center=True).mean()
    return y

def _cumulative_mean(y: pd.Series) -> pd.Series:
    return y.expanding(min_periods=1).mean()

def _dummy_metric_curves(df, series_sel, model: str, max_h: int = 12, seed_base: int = 123):
    scale = _series_scale(df, series_sel)
    seed = (abs(hash(model)) + seed_base) % (2**32 - 1)
    rng = np.random.default_rng(seed)

    if "Holt" in model: base_rmse, base_mae = 0.75, 0.60
    elif "S-Naive" in model: base_rmse, base_mae = 0.95, 0.78
    else: base_rmse, base_mae = 1.05, 0.85

    noise_rmse = rng.normal(0, 0.08, size=max_h) + rng.uniform(-0.05, 0.05, size=max_h)
    noise_mae  = rng.normal(0, 0.07, size=max_h) + rng.uniform(-0.04, 0.04, size=max_h)

    rmse = np.abs((base_rmse + noise_rmse) * scale)
    mae  = np.abs((base_mae  + noise_mae ) * scale * 0.85)

    horizons = np.arange(1, max_h + 1, dtype=int)
    return pd.DataFrame({"h": horizons, "RMSE": rmse, "MAE": mae, "Modelo": model})

def _dummy_residuals_from_metric(df, series_sel, model: str, n: int = 800, seed_base: int = 999):
    curves = _dummy_metric_curves(df, series_sel, model)
    rmse_mean = curves["RMSE"].mean() if not curves.empty else 1.0
    seed = (abs(hash(model)) + seed_base) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    resid = rng.normal(0, rmse_mean, size=n)
    return pd.DataFrame({"residual": resid, "Modelo": model})

# =========================
# Vista
# =========================
def desempeno_view(df: pd.DataFrame, series_w, range_w):
    metric_w = pn.widgets.RadioButtonGroup.from_param(PERF_STATE.param.metric)
    acumulado_w = pn.widgets.Toggle.from_param(PERF_STATE.param.accumulated)
    smooth_w = pn.widgets.IntSlider.from_param(PERF_STATE.param.smoothing, start=0, end=6, step=1)
    densidad_w = pn.widgets.Toggle.from_param(PERF_STATE.param.use_kde)

    @pn.depends(
        series_w.param.value,
        range_w.param.value_throttled,
        MODELS_STATE.param.selected,      # <- modelos chequeados en real_predicho
        PERF_STATE.param.metric,
        PERF_STATE.param.accumulated,
        PERF_STATE.param.smoothing,
        PERF_STATE.param.use_kde
    )
    def _view(series_sel, drange, models_sel, metric, acumulado, smooth, use_kde):
        models = [m for m in models_sel if m in COLOR_BY_MODEL]
        if not models:
            return pn.pane.Markdown("**Marca al menos un modelo en _Real vs Predicho_**.")

        # (a) Curva única de RMSE/MAE con múltiples líneas (una por modelo)
        x = df.copy()
        if "fecha" in x.columns:
            x["fecha"] = pd.to_datetime(x["fecha"])
            x = x.loc[(x["fecha"] >= pd.to_datetime(drange[0])) & (x["fecha"] <= pd.to_datetime(drange[1]))]

        lines = []
        for m in models:
            curves = _dummy_metric_curves(x, series_sel, m, max_h=12)
            y = curves[metric]
            if acumulado: y = _cumulative_mean(y)
            y = _smooth(y, smooth)
            color = COLOR_BY_MODEL.get(m, COLOR_REAL)

            line = curves.assign(y=y.values).hvplot.line(
                x="h", y="y", color=color, alpha=0.95, line_width=3, label=m,
                ylabel=metric, xlabel="Horizonte (pasos)", height=320, width=1000
            )
            pts = curves.assign(y=y.values).hvplot.scatter(
                x="h", y="y", color=color, alpha=0.9, size=5, legend=False
            )
            lines.append(line * pts)

        rmse_overlay = hv.Overlay(lines).opts(show_legend=True, legend_position="top_left")
        rmse_panel = pn.pane.HoloViews(rmse_overlay, sizing_mode="stretch_width")

        # (b) Residuales: una gráfica por modelo, colocadas una DEBAJO de la otra
        resid_panels = []
        for m in models:
            r = _dummy_residuals_from_metric(x, series_sel, m, n=1000)
            color = COLOR_BY_MODEL.get(m, COLOR_REAL)
            if use_kde:
                g = r.hvplot.kde(
                    y="residual", color=color, alpha=0.85, legend=False,
                    ylabel="Densidad", xlabel="Residual", height=220, width=1000, title=f"Residual — {m}"
                )
            else:
                g = r.hvplot.hist(
                    y="residual", bins=40, color=color, alpha=0.65, legend=False,
                    ylabel="Frecuencia", xlabel="Residual", height=220, width=1000, title=f"Residual — {m}"
                )
            resid_panels.append(pn.pane.HoloViews(g, sizing_mode="stretch_width"))

        header = _right_header("7) Curvas de desempeño y residuales (modelos)")
        controls = pn.Row(
            pn.Column(
                pn.pane.Markdown("**Controles**"),
                pn.pane.Markdown("_Modelos sincronizados con **Real vs Predicho**_"),
                metric_w, acumulado_w, smooth_w, densidad_w,
                width=320, sizing_mode="fixed"
            )
        )

        # Residuales apilados verticalmente
        resid_col = pn.Column(*resid_panels, sizing_mode="stretch_width")

        return pn.Column(header, controls, rmse_panel, resid_col, sizing_mode="stretch_width")

    return pn.Column(_view)