import pandas as pd
import numpy as np
import panel as pn
import holoviews as hv
import hvplot.pandas  # noqa
import param

hv.extension("bokeh")

# =========================
# Paleta (según tu PDF)
# =========================
COLOR_FONDO_BASE   = "#E6E6E6"
COLOR_TEXTO        = "#222222"
COLOR_FONDO_CARD   = "#FAFAFA"
COLOR_GUIA         = "#BDBDBD"

COLOR_REGULAR      = "#0072B2"
COLOR_SUPERIOR     = "#D55E00"
COLOR_DIESEL       = "#009E73"

COLOR_REAL         = "#111111"
COLOR_NAIVE        = "#9E9E9E"
COLOR_SNAIVE       = "#6E6E6E"
COLOR_HOLTWINTERS  = "#4B4B4B"

COLOR_HOVER        = "#F0E442"
COLOR_ANOMALIA     = "#C00000"

COLOR_BY_BASE = {
    "Regular":  COLOR_REGULAR,
    "Superior": COLOR_SUPERIOR,
    "Diesel":   COLOR_DIESEL,
}

# =========================
# Estado compartido
# =========================
class _AnomalyState(param.Parameterized):
    anomaly_dates = param.List(default=[])

ANOMALY_STATE = _AnomalyState()


# =========================
# Utilidades
# =========================
def _right_header(text: str):
    return pn.pane.Markdown(
        f"### {text}",
        styles={"text-align": "right", "margin": "0 8px 6px 0"}
    )

def _ensure_fecha(df: pd.DataFrame) -> pd.Series:
    """Devuelve Serie datetime llamada 'fecha' (desde columna o índice)."""
    if "fecha" in df.columns:
        f = pd.to_datetime(df["fecha"])
    else:
        f = pd.to_datetime(df.index)
    return f.rename("fecha")

def _base_from(col: str) -> str:
    try:
        base, _ = col.split("_", 1)
    except ValueError:
        base = col
    return base


# =========================
# Z-scores respecto a media móvil
# =========================
def _roll_stats(y: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    mu = y.rolling(window=window, min_periods=window).mean()
    sd = y.rolling(window=window, min_periods=window).std(ddof=0)
    return mu, sd

def _zscores_vs_time(ser: pd.Series, window: int) -> pd.DataFrame:
    mu, sd = _roll_stats(ser, window)
    resid = ser - mu
    z = resid / sd
    out = pd.DataFrame({
        "fecha": ser.index,
        "valor": ser.values,
        "media": mu.values,
        "std":   sd.values,
        "resid": resid.values,
        "z":     z.values
    }).dropna()
    return out


# =========================
# Vista principal
# =========================
def anomalias_view(df: pd.DataFrame, series_w, range_w):
    """
    Dispersión de z-score vs tiempo por series seleccionadas.
    - Controles: ventana (3/6/12), umbral |z|, toggle "Mostrar media móvil".
    - Salida reactiva: ANOMALY_STATE.anomaly_dates (fechas con |z|>=umbral).
    """
    ventana_w = pn.widgets.RadioButtonGroup(
        name="Ventana (meses)", options=[3, 6, 12], value=12
    )
    umbral_w = pn.widgets.FloatSlider(
        name="Umbral |z|", start=0.5, end=4.0, step=0.1, value=2.0
    )
    mostrar_linea_w = pn.widgets.Checkbox(name="Mostrar media móvil", value=True)

    @pn.depends(
        series_w.param.value,
        range_w.param.value_throttled,
        ventana_w.param.value,
        umbral_w.param.value,
        mostrar_linea_w.param.value
    )
    def _view(series_sel, drange, ventana, umbral, show_mu):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie.**")

        # Filtrar por rango
        f = _ensure_fecha(df)
        x = df.assign(fecha=f)
        mask = (x["fecha"] >= pd.to_datetime(drange[0])) & (x["fecha"] <= pd.to_datetime(drange[1]))
        x = x.loc[mask]

        if x.empty:
            ANOMALY_STATE.anomaly_dates = []
            return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        overlays = []      # aquí SOLO metemos Overlays
        fechas_anom = []   # acumulador de fechas anómalas
        mu_lines = []      # líneas de media móvil por serie (para panel aparte)

        for s in series_sel:
            if s not in x.columns:
                continue

            color = COLOR_BY_BASE.get(_base_from(s), COLOR_REAL)
            ser = x.set_index("fecha")[s].astype(float).dropna()
            if ser.empty:
                continue

            stats = _zscores_vs_time(ser, ventana)

            # Puntos base (z vs tiempo)
            base_pts = stats.hvplot.scatter(
                x="fecha", y="z", color=color, alpha=0.9, size=5,
                legend=False, tools=["hover"], height=380, width=1000, ylabel="z-score"
            )

            # Líneas de referencia
            ref0 = stats.assign(z0=0).hvplot.line(x="fecha", y="z0", color=COLOR_GUIA, line_dash="dotted")
            refp = stats.assign(zu=umbral).hvplot.line(x="fecha", y="zu", color=COLOR_GUIA, line_dash="dashed")
            refn = stats.assign(zl=-umbral).hvplot.line(x="fecha", y="zl", color=COLOR_GUIA, line_dash="dashed")

            # Puntos de anomalía
            anmask = np.abs(stats["z"]) >= umbral
            anoms = stats.loc[anmask]
            if not anoms.empty:
                fechas_anom.extend(list(anoms["fecha"].values))
                an_pts = anoms.hvplot.scatter(
                    x="fecha", y="z", color=COLOR_ANOMALIA, size=7, alpha=0.95,
                    marker="triangle", legend=False, tools=["hover"]
                )
            else:
                an_pts = hv.Overlay([])

            # Formateos simples (evitar .opts sobre Layouts)
            base_pts = base_pts.opts(yticks=7)
            an_pts   = an_pts.opts(yticks=7)
            ref0     = ref0.opts(yticks=7)
            refp     = refp.opts(yticks=7)
            refn     = refn.opts(yticks=7)

            # Overlay válido (sin Layouts)
            overlay_piece = (base_pts * an_pts * ref0 * refp * refn)
            overlays.append(overlay_piece)

            # (Opcional) Media móvil en panel aparte
            if show_mu:
                mu_line = stats.hvplot.line(
                    x="fecha", y="media", color=color, line_dash="dotdash", alpha=0.9,
                    ylabel="Media móvil"
                ).opts(height=160, width=1000)
                mu_lines.append(mu_line)

        if not overlays:
            ANOMALY_STATE.anomaly_dates = []
            return pn.pane.Markdown("**Sin datos modelables para las series seleccionadas.**")

        # Combinar overlays (todos son Overlays)
        chart = hv.Overlay(overlays)

        # Actualizar fechas anómalas globales
        if fechas_anom:
            uniq = sorted(pd.to_datetime(pd.Index(fechas_anom)).unique())
            ANOMALY_STATE.anomaly_dates = uniq
        else:
            ANOMALY_STATE.anomaly_dates = []

        # Tabla de anomalías
        def _anom_table():
            rows = []
            for s in series_sel:
                if s not in x.columns:
                    continue
                ser = x.set_index("fecha")[s].astype(float).dropna()
                if ser.empty:
                    continue
                stats = _zscores_vs_time(ser, ventana)
                anmask = np.abs(stats["z"]) >= umbral
                if anmask.any():
                    t = stats.loc[anmask, ["fecha", "valor", "media", "resid", "z"]].copy()
                    t["serie"] = s
                    rows.append(t)
            if not rows:
                return pn.pane.Markdown("_Sin anomalías con el umbral actual._", styles={"margin": "4px 0 0 0"})
            tab = pd.concat(rows).sort_values(["fecha", "serie"]).reset_index(drop=True)
            tab = tab[["fecha", "serie", "valor", "media", "resid", "z"]]
            return pn.widgets.Tabulator(tab.head(200), height=220, pagination="local", page_size=10)

        # Construcción de layout
        col = [
            _right_header("5) Detector de anomalías — z-score vs tiempo"),
            pn.Row(ventana_w, umbral_w, pn.Spacer(width=12), mostrar_linea_w),
            pn.pane.HoloViews(chart, width=1000, height=380, sizing_mode="fixed"),
            pn.pane.Markdown("**Anomalías detectadas** (|z| ≥ umbral)"),
            _anom_table()
        ]

        # Si se pidió media móvil, la mostramos debajo (combinada por series)
        if show_mu and mu_lines:
            mu_chart = hv.Overlay(mu_lines).opts(height=160, width=1000)
            col.insert(3, pn.pane.HoloViews(mu_chart, sizing_mode="fixed"))

        return pn.Column(*col)

    return pn.Column(_view)