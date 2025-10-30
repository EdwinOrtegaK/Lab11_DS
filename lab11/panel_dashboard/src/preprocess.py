# src/preprocess.py
import pandas as pd
from pathlib import Path

SERIES = ["Regular_Imp","Superior_Imp","Diesel_Imp","Regular_Con","Superior_Con","Diesel_Con"]

def load_combustibles():
    # preproces.py -> src -> panel_dashboard -> lab11 -> (sube a) raíz del repo
    repo_root = Path(__file__).resolve().parents[3]  # <-- antes estaba [2]
    csv_path = repo_root / "lab2" / "data" / "clean" / "Series_de_Tiempo_Combustibles.csv"

    # (opcional) fallback si decides poner un symlink o copia en panel_dashboard/data/
    if not csv_path.exists():
        alt = Path(__file__).resolve().parents[1] / "data" / "combustibles.csv"
        if alt.exists():
            csv_path = alt

    # Debug útil si vuelve a fallar
    print(f"[load_combustibles] Leyendo CSV desde: {csv_path}")

    df = pd.read_csv(csv_path, parse_dates=["fecha"])
    df = df.set_index("fecha").sort_index()
    return df
