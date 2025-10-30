# src/visuals/panorama.py
import panel as pn, holoviews as hv
import hvplot.pandas
from bokeh.models import RangeTool, BoxAnnotation, NumeralTickFormatter, HoverTool
import pandas as pd
from pandas.api.types import is_numeric_dtype

def _pretty_hover(plot, element):
    from bokeh.models import HoverTool
    fig = plot.state

    for r in fig.renderers:
        try:
            if getattr(r, "legend_label", None) and not getattr(r, "name", None):
                r.name = r.legend_label
        except Exception:
            pass

    for t in fig.tools:
        if isinstance(t, HoverTool):
            t.tooltips = [
                ("fecha", "@fecha{%F}"),
                ("valor", "$y{0,0}")
            ]
            t.formatters = {"@fecha": "datetime"}
            t.mode = "vline"
            t.point_policy = "snap_to_data"

# Widgets auxiliares
def series_selector(df: pd.DataFrame):
    """Checkbox de series numéricas (excluye 'fecha')."""
    if 'fecha' in df.columns:
        cols = [c for c in df.columns if c != 'fecha' and is_numeric_dtype(df[c])]
    else:
        cols = [c for c in df.columns if is_numeric_dtype(df[c])]
    # Valor inicial: la primera disponible 
    return pn.widgets.CheckBoxGroup(name="Series", options=cols, value=cols[:1])

def date_range_stream(df: pd.DataFrame):
    """DateRangeSlider en base a columna 'fecha' o índice datetime."""
    if 'fecha' in df.columns:
        f = pd.to_datetime(df['fecha'])
        start, end = f.min(), f.max()
    else:
        idx = pd.to_datetime(df.index)
        start, end = idx.min(), idx.max()
    return pn.widgets.DateRangeSlider(name="Rango de fechas", start=start, end=end, value=(start, end))

def freq_selector():
    return pn.widgets.RadioButtonGroup(
        name="Frecuencia", options=["Mensual","Trimestral","Anual"], value="Mensual"
    )

def epoch_toggle():
    # Dos toggles excluyentes vía RadioButtonGroup para simplicidad
    return pn.widgets.RadioButtonGroup(
        name="Corte temporal", options=["Todo","Pre-2020","Post-2020"], value="Todo"
    )

def _right_header(text: str):
    # título fuera del plot, alineado a la derecha
    return pn.pane.Markdown(f"### {text}", styles={'text-align': 'right', 'margin': '0 8px 6px 0'})

# Helpers de transformación
def _resample(df: pd.DataFrame, freq_label: str) -> pd.DataFrame:
    """Resample por suma (cambia a .mean() si lo prefieres)."""
    rule = {"Mensual":"MS", "Trimestral":"QS", "Anual":"AS"}[freq_label]
    x = df.copy()
    if 'fecha' in x.columns:
        x['fecha'] = pd.to_datetime(x['fecha'])
        x = x.set_index('fecha')
    # suma por periodo
    x = x.resample(rule).sum()
    x = x.reset_index()  # recupera 'fecha'
    return x

def _apply_epoch(df: pd.DataFrame, epoch_sel: str) -> pd.DataFrame:
    """Filtra por Todo / Pre-2020 / Post-2020 asegurando columna 'fecha'."""
    x = df.copy()
    if 'fecha' not in x.columns:
        x = x.reset_index().rename(columns={'index':'fecha'})
    x['fecha'] = pd.to_datetime(x['fecha'])
    if epoch_sel == "Pre-2020":
        x = x[x['fecha'] < pd.Timestamp('2020-01-01')]
    elif epoch_sel == "Post-2020":
        x = x[x['fecha'] >= pd.Timestamp('2020-01-01')]
    return x

# Vista principal
def panorama_view(df: pd.DataFrame, series_w, range_w, freq_w, epoch_w):
    @pn.depends(series_w.param.value, range_w.param.value_throttled,
                freq_w.param.value, epoch_w.param.value)
    def _view(series_sel, dr, freq_label, epoch_sel):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie.**")

        # Filtrado por corte temporal
        base = _apply_epoch(df, epoch_sel)

        # Resample (MS/QS/AS)
        agg = _resample(base, freq_label)  # tiene 'fecha' como columna

        # Rango del slider
        mask = (agg['fecha'] >= pd.to_datetime(dr[0])) & (agg['fecha'] <= pd.to_datetime(dr[1]))
        sub  = agg.loc[mask, ['fecha'] + list(series_sel)]

        # Plot principal
        main = sub.hvplot(
            x='fecha', y=series_sel, height=320, width=900,
            tools=['hover']
        ).opts(
            ylabel='Importación',
            yticks=6,
            yformatter=NumeralTickFormatter(format="0,0"),
            hooks=[_pretty_hover] 
        )

        return pn.Column(
            _right_header("1) Panorama temporal"),
            main
        )

    return pn.Column(_view)
