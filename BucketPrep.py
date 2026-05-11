import pandas as pd
import os
import scipy.stats as stats
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import timedelta
import xarray as xr
import matplotlib.dates as mdates

### Tipping bucket data
all_sheets = pd.read_excel("TippingBucket.xlsx", sheet_name=None, header=None)

dfs = []
for location, df in all_sheets.items():
    # Row 0 contains headers; set them, then drop that row
    df.columns = df.iloc[0].str.strip()
    df = df.iloc[1:].reset_index(drop=True)
    #df.columns.values[0] = "index"

    # Find time and event columns dynamically
    time_col = next(c for c in df.columns if isinstance(c, str) and "time" in c.lower())
    event_col = next(c for c in df.columns if isinstance(c, str) and "event" in c.lower())

    df = df[[time_col, event_col]].copy()
    df.columns = ["time", "tips"]

    df["location"] = location

    # Drop any rows where time is a string like "Time" or "Time/Date" (stray headers)
    df = df[~df["time"].astype(str).str.lower().str.contains("time")]

    # Drop rows with null time or tips
    df = df.dropna(subset=["time", "tips"])

    df["time"] = pd.to_datetime(df["time"], dayfirst=True, errors="coerce")
    df["tips"] = pd.to_numeric(df["tips"], errors="coerce").astype("Int64")

    dfs.append(df)

bucket = pd.concat(dfs, ignore_index=True)[["location", "time", "tips"]]

tips_daily = (
    bucket[bucket['tips'] == 1]
    .assign(date=lambda x: (x['time'] + pd.Timedelta(hours=17)).dt.floor('D'))
    .groupby(['location', 'date'])
    .size()
    .reset_index(name='tips')
)
tips_daily['bucket_mm'] = tips_daily['tips'] * 0.2
tips_daily.to_csv('bucket_input.csv', index = False)


