# src/visuals/tabla.py
import panel as pn
from src.metrics import dummy_metrics_table

def metrics_table_view(df):
    table = pn.widgets.Tabulator(dummy_metrics_table(df.columns), pagination='remote', page_size=10)
    return pn.Column(pn.pane.Markdown("### 8) Tabla comparativa de métricas (placeholder)"), table)
