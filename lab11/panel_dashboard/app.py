# app.py
import panel as pn, holoviews as hv

pn.extension('tabulator')
hv.extension('bokeh')

from src.preprocess import load_combustibles
from src.visuals.panorama import panorama_view, date_range_stream, series_selector, freq_selector, epoch_toggle
from src.visuals.estacionalidad import estacionalidad_view
from src.visuals.barras import barras_apiladas_view
from src.visuals.tabla import metrics_table_view
from src.visuals.caja_violin import caja_violin_view          
from src.visuals.real_predicho import real_predicho_view
from src.visuals.anomalias import anomalias_view, ANOMALY_STATE
from src.visuals.desempeno import desempeno_view, MODELS_STATE


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
estacionalidad = estacionalidad_view(df, w_series, w_dates)       # V2
barras   = barras_apiladas_view(df, w_series, w_dates)            # V3
caja_violin = caja_violin_view(df, w_series, w_dates)             # V4
anomalias = anomalias_view(df, w_series, w_dates)                 # V5
real_predicho = real_predicho_view(df, w_series, w_dates)         # V6
desempeno = desempeno_view(df, w_series, w_dates)                 # V7
tabla    = metrics_table_view(df, w_series, w_dates)              # V8

template = pn.template.MaterialTemplate(
    title="Panel — Visualización Interactiva",
    sidebar=[widgets],
    main=[
        pn.Row(panorama), 
        pn.Row(estacionalidad), 
        pn.Row(barras), 
        pn.Row(caja_violin), 
        pn.Row(anomalias),
        pn.Row(real_predicho), 
        pn.Row(desempeno),
        pn.Row(tabla)
    ]
)
template.servable()
