# src/visuals/heatmap.py
import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
from bokeh.models import HoverTool, NumeralTickFormatter, ColorBar

hv.extension('bokeh')

def _right_header(text: str):
    return pn.pane.Markdown(f"### {text}", styles={'text-align': 'right', 'margin': '0 8px 6px 0'})

def _ensure_fecha(df: pd.DataFrame):
    """
    Devuelve (fechas, es_serie):
      - fechas: Serie datetime si la columna 'fecha' existe; de lo contrario, DatetimeIndex.
      - es_serie: True si 'fechas' es una Serie (tiene .dt), False si es un DatetimeIndex.
    """
    if 'fecha' in df.columns:
        return pd.to_datetime(df['fecha']), True  # Serie
    return pd.to_datetime(df.index), False        # DatetimeIndex


def _pretty_heatmap(plot, element):
    """
    Hook para:
      1) Formatear el HoverTool con separador de miles.
      2) Quitar notación científica en la barra de colores.
    """
    vdim_name = element.vdims[0].name if element.vdims else "valor"
    for t in plot.state.tools:
        if isinstance(t, HoverTool):
            t.tooltips = [
                ("Año", "@Año"),
                ("Mes", "@Mes"),
                (vdim_name, f"@{{{vdim_name}}}{{0,0}}"),
            ]
            t.mode = "mouse"

    try:
        for r in list(getattr(plot.state, "right", [])):
            if isinstance(r, ColorBar):
                r.formatter = NumeralTickFormatter(format="0,0")
    except Exception:
        pass


def heatmap_view(df: pd.DataFrame, series_w, range_w, shared_scale: bool = True):
    """
    Renderiza 1 heatmap (Mes × Año) por cada serie seleccionada en el checkbox.
    Usa escala compartida si shared_scale=True.
    """
    @pn.depends(series_w.param.value, range_w.param.value_throttled)
    def _view(series_sel, drange):
        if not series_sel:
            return pn.pane.Markdown("**Selecciona al menos una serie para el heatmap.**")

        # Fechas y máscara de filtrado
        fechas, es_serie = _ensure_fecha(df)
        mask = (fechas >= pd.to_datetime(drange[0])) & (fechas <= pd.to_datetime(drange[1]))
        dff = df[mask].copy()
        if dff.empty:
            return pn.pane.Markdown("**No hay datos en el rango seleccionado.**")

        # Extraer Año/Mes
        fechas_f = fechas[mask]
        if es_serie:
            años   = fechas_f.dt.year
            meses  = fechas_f.dt.month
        else:
            años   = fechas_f.year
            meses  = fechas_f.month

        dff['Año'] = np.array(años, dtype=int)
        dff['Mes'] = np.array(meses, dtype=int)

        # Escala de color compartida
        vmin = vmax = None
        if shared_scale:
            vals = [dff[s].to_numpy(dtype='float64') for s in series_sel if s in dff.columns]
            if vals:
                cat = np.concatenate(vals)
                cat = cat[~np.isnan(cat)]
                if cat.size:
                    vmin, vmax = float(np.nanmin(cat)), float(np.nanmax(cat))

        # Un heatmap por serie
        blocks = []
        for s in series_sel:
            if s not in dff.columns:
                continue

            piv = dff.pivot_table(index='Mes', columns='Año', values=s, aggfunc='mean')
            if np.isnan(piv.to_numpy(dtype='float64')).all():
                blocks.append(pn.pane.Markdown(f"*Sin datos para* **{s}** en el rango."))
                continue

            hm = hv.HeatMap(
                (piv.columns, piv.index, piv.values),
                kdims=['Año', 'Mes'],
                vdims=[s]
            ).opts(
                width=900, height=300,
                tools=['hover'],
                colorbar=True,
                clim=(vmin, vmax) if shared_scale else None,
                hooks=[_pretty_heatmap],
            )

            # Subtítulo
            sub = pn.pane.Markdown(
                f"**{s}**",
                styles={'text-align': 'right', 'margin': '4px 8px 0 0', 'color': '#444'}
            )

            # Subtítulo + heatmap como un bloque
            blocks.append(pn.Column(sub, hm, sizing_mode="stretch_width"))

        if not blocks:
            return pn.pane.Markdown("**No hay datos para las series seleccionadas.**")

        # Encabezado
        return pn.Column(
            _right_header("2) Estacionalidad Mes × Año"),
            *blocks
        )

    return pn.Column(_view)
