# src/visuals/tabla.py
import panel as pn
from src.metrics import dummy_metrics_table

def metrics_table_view(df, series_w, range_w):
    @pn.depends(series_w.param.value, range_w.param.value_throttled)
    def _make(series_sel, drange):
        data = dummy_metrics_table(series_sel if series_sel else df.columns)
        return pn.widgets.Tabulator(data, pagination='local', page_size=10, height=300)

    return pn.Column(pn.pane.Markdown("### 8) Tabla comparativa de métricas (placeholder)"), _make)
