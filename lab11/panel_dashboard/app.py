# app.py
import panel as pn, holoviews as hv
pn.extension('tabulator')
hv.extension('bokeh')

from src.preprocess import load_combustibles
from src.visuals.panorama import panorama_view, date_range_stream, series_selector, freq_selector, epoch_toggle
from src.visuals.heatmap import heatmap_view
from src.visuals.barras import barras_apiladas_view
from src.visuals.tabla import metrics_table_view

df = load_combustibles()

header = pn.pane.Markdown("## Dashboard — Combustibles Guatemala (LSTM)")

w_series = series_selector(df)
w_dates  = date_range_stream(df)
w_freq   = freq_selector()
w_epoch  = epoch_toggle() 

# Widgets en la barra lateral
widgets = pn.Column(w_series, w_dates)

# Vistas 
panorama = panorama_view(df, w_series, w_dates, w_freq, w_epoch)  # V1
heatmap  = heatmap_view(df, w_series, w_dates, shared_scale=True) # V2
barras   = barras_apiladas_view(df, w_series, w_dates) # V3
tabla    = metrics_table_view(df, w_series, w_dates)  # V8

template = pn.template.MaterialTemplate(
    title="Panel — Visualización Interactiva",
    sidebar=[widgets],
    main=[pn.Row(panorama), pn.Row(heatmap), pn.Row(barras), pn.Row(tabla)]
)
template.servable()
