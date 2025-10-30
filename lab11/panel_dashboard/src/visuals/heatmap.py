# src/visuals/heatmap.py
import panel as pn, holoviews as hv
import pandas as pd

def heatmap_view(df):
    serie_sel = pn.widgets.Select(name="Serie activa", options=list(df.columns), value=df.columns[0])

    @pn.depends(serie_sel.param.value)
    def _make(s):
        tmp = df[[s]].copy()
        tmp["Año"] = tmp.index.year
        tmp["Mes"] = tmp.index.month
        pivot = tmp.pivot_table(index="Mes", columns="Año", values=s, aggfunc="mean")
        hm = hv.HeatMap((pivot.columns, pivot.index, pivot.values)).opts(
            height=300, width=900, colorbar=True, tools=["hover"], title="2) Estacionalidad Mes × Año"
        )
        return hm
    return pn.Column(serie_sel, _make, name="heatmap")
