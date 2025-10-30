# app.py
import panel as pn, holoviews as hv
pn.extension('tabulator')
hv.extension('bokeh')

from src.preprocess import load_combustibles
from src.visuals.panorama import panorama_view, date_range_stream, series_selector
from src.visuals.heatmap import heatmap_view
from src.visuals.tabla import metrics_table_view

df = load_combustibles()

header = pn.pane.Markdown("## Dashboard — Combustibles Guatemala (LSTM)")

# Widgets globales
widgets = pn.Column(
    series_selector(df),
    date_range_stream(df)
)

# Vistas
panorama = panorama_view(df)              # V1
heatmap  = heatmap_view(df)               # V2 (enlazada a selección temporal/serie)
tabla    = metrics_table_view(df)         # V8 (placeholder)

template = pn.template.MaterialTemplate(
    title="Panel — Visualización Interactiva",
    sidebar=[widgets],
    main=[pn.Row(panorama), pn.Row(heatmap), pn.Row(tabla)]
)
template.servable()
