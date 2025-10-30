# src/visuals/panorama.py
import panel as pn, holoviews as hv
import hvplot.pandas  # activa .hvplot en DataFrame

def series_selector(df):
    opts = [c for c in df.columns if df[c].dtype != "O"]
    return pn.widgets.CheckBoxGroup(name="Series", options=opts, value=[opts[0]])

def date_range_stream(df):
    return pn.widgets.DateRangeSlider(name="Rango de fechas", start=df.index.min(),
                                      end=df.index.max(), value=(df.index.min(), df.index.max()))

def panorama_view(df):
    series_w = series_selector(df)
    range_w  = date_range_stream(df)

    @pn.depends(series_w.param.value, range_w.param.value)
    def _view(series_sel, drange):
        sub = df.loc[drange[0]:drange[1], series_sel]
        overlay = hv.Overlay([sub[s].hvplot.line(height=300, width=900, title="Panorama temporal")
                              for s in series_sel]) if series_sel else hv.Curve([])
        return overlay.opts(legend_position="top_left")
    return pn.Column(pn.pane.Markdown("### 1) Panorama temporal"), _view, name="panorama")
