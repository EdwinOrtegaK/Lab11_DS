# src/metrics.py
import numpy as np
import pandas as pd

def mae(y_true, y_pred): return np.mean(np.abs(y_true - y_pred))
def rmse(y_true, y_pred): return np.sqrt(np.mean((y_true - y_pred)**2))
def mape(y_true, y_pred): 
    y = np.where(y_true==0, np.nan, y_true)
    return np.nanmean(np.abs((y - y_pred)/y))*100

def dummy_metrics_table(series):
    rows = []
    for s in series:
        for m in ["Naive","SNaive12","HoltWinters"]:
            rows.append(dict(Serie=s, Modelo=m, MAE=np.random.rand(),
                             RMSE=np.random.rand(), MAPE=np.random.rand()*10))
    return pd.DataFrame(rows)
