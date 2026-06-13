import pandas as pd
import numpy as np
from datetime import datetime

# ------------------------------------------------------------
# 1. Load and clean tipping bucket data (ORIGINAL, UNCHANGED)
# ------------------------------------------------------------
def load_bucket_data(filepath="TippingBucket.xlsx"):
    all_sheets = pd.read_excel(filepath, sheet_name=None, header=None)
    dfs = []
    for location, df in all_sheets.items():
        df.columns = df.iloc[0].str.strip()
        df = df.iloc[1:].reset_index(drop=True)

        time_col = next(c for c in df.columns if isinstance(c, str) and "time" in c.lower())
        event_col = next(c for c in df.columns if isinstance(c, str) and "event" in c.lower())

        df = df[[time_col, event_col]].copy()
        df.columns = ["time", "tips"]
        df["location"] = location

        df = df[~df["time"].astype(str).str.lower().str.contains("time")]
        df = df.dropna(subset=["time", "tips"])

        df["time"] = pd.to_datetime(df["time"], dayfirst=True, errors="coerce")
        df["tips"] = pd.to_numeric(df["tips"], errors="coerce").astype("Int64")

        dfs.append(df)

    bucket = pd.concat(dfs, ignore_index=True)[["location", "time", "tips"]]
    bucket = bucket[bucket['tips'] == 1]
    bucket['time'] = bucket['time'].dt.tz_localize('UTC')
    bucket['location'] = bucket['location'].str.upper()
    
    return bucket

# ------------------------------------------------------------
# 2. Load cup gauge data (ORIGINAL, UNCHANGED)
# ------------------------------------------------------------
def load_cup_data(filepath="TEMBO_Rainfall_Observatory.csv"):
    cup = pd.read_csv(filepath)
    
    location_renaming = {
        'Kpaligu': 'KPALIGA', 'uds_wacwisa': 'KPASOLGU', 'Tuunaayili': 'TUUNAAYILI',
        'Tingoli': 'TINGOLI', 'Kpalsogu': 'KPASOLGU', 'Kpaliga': 'KPALIGA',
        'Golinga': 'GOLINGA', 'Sanga': 'SANGA', 'Gbullung': 'GBULLUNG',
        'Garizegu': 'GARIZEGU', 'Galinkpegu': 'GALINKPEGU'
    }
    
    cup['location'] = cup['location'].replace(location_renaming)
    cup['location'] = cup['location'].str.upper()
    
    cup['sub_date'] = pd.to_datetime(cup['SubmissionDate'], utc=True)
    cup['read_date'] = cup['sub_date'].dt.normalize()
    cup['time_str'] = cup['time_recorded'].str.replace('Z', '')
    
    cup['read_time'] = pd.to_datetime(cup['time_str'], format='%H:%M:%S.%f', errors='coerce').dt.time
    if cup['read_time'].isna().any():
        cup['read_time'] = pd.to_datetime(cup['time_str'], format='%H:%M:%S', errors='coerce').dt.time
    
    cup['read_datetime'] = pd.to_datetime(
        cup['read_date'].dt.strftime('%Y-%m-%d') + ' ' + cup['read_time'].astype(str)
    )
    cup['read_datetime'] = cup['read_datetime'].dt.tz_localize('UTC')
    cup = cup.dropna(subset=['read_datetime'])
    # Keep the earliest reading per day (cup is read in the morning)
    cup = cup.sort_values('read_datetime').groupby(['location', 'read_date'], as_index=False).last()
    
    return cup[['location', 'read_datetime']].rename(columns={'read_datetime': 'read_time'})

# ------------------------------------------------------------
# 3. Fill missing days: use 07:00 UTC default
# ------------------------------------------------------------
def fill_missing_cup_days(cup_raw, min_date, max_date):
    # Build a row for every day between min_date and max_date for each location.
    # - If a reading exists for a day, use it.
    # - If a day is missing, impute strict 07:00 UTC.
    all_dates = pd.date_range(pd.to_datetime(min_date).normalize(), pd.to_datetime(max_date).normalize(), freq='D', tz='UTC')
    filled = []
    DEFAULT_HOUR = 7

    for loc, group in cup_raw.groupby('location'):
        date_map = {dt.normalize(): dt for dt in group['read_time']}
        for day in all_dates:
            if day in date_map:
                rt = date_map[day]
            else:
                rt = day.replace(hour=DEFAULT_HOUR, minute=0, second=0)
            filled.append({"location": loc, "read_time": rt})
    return pd.DataFrame(filled)

# ------------------------------------------------------------
# 4. FIXED INTERVAL BUILDER (align with rainfall observation standards)
# ------------------------------------------------------------
def build_standard_intervals(cup_full):
    intervals = []
    for loc, group in cup_full.groupby("location"):
        valid = group.sort_values("read_time").reset_index(drop=True)
        for i in range(len(valid)):
            curr_end = valid.at[i, "read_time"]
            curr_date = curr_end.normalize()

            if i > 0:
                # Use previous available reading as start
                int_start = valid.at[i - 1, "read_time"]
            else:
                # No previous available reading: default to 24 hours prior
                int_start = curr_end - pd.Timedelta(days=1)

            intervals.append({
                "location": loc,
                "interval_start": int_start,
                "interval_end": curr_end,
                "obs_date": curr_date
            })
    return pd.DataFrame(intervals)

# ------------------------------------------------------------
# 5. Aggregate bucket tips (strict half-open window)
# ------------------------------------------------------------
def aggregate_rain(bucket_df, intervals_df):
    results = []
    common_locs = set(bucket_df["location"]) & set(intervals_df["location"])

    for loc in common_locs:
        b_sub = bucket_df[bucket_df["location"] == loc]
        int_sub = intervals_df[intervals_df["location"] == loc]

        for _, row in int_sub.iterrows():
            s = row["interval_start"]
            e = row["interval_end"]
            d = row["obs_date"].date()

            # Strict half-open window (consistent across all runs)
            mask = (b_sub["time"] >= s) & (b_sub["time"] < e)
            tip_count = mask.sum()
            
            # If no tips, write NaN instead of 0
            if tip_count == 0:
                rain_mm = np.nan
            else:
                rain_mm = round(tip_count * 0.2, 2)  # 0.2 mm per tip

            results.append({
                "location": loc,
                "date": d,
                "bucket_mm": rain_mm
            })
    return pd.DataFrame(results)

# ------------------------------------------------------------
# MAIN WORKFLOW
# ------------------------------------------------------------
def main():
    print("=== Loading Data ===")
    bucket = load_bucket_data()
    cup_raw = load_cup_data()

    # Global date range
    min_dt = min(bucket["time"].min(), cup_raw["read_time"].min())
    max_dt = max(bucket["time"].max(), cup_raw["read_time"].max())

    print("=== Filling missing cup days with 07:00 UTC ===")
    cup_full = fill_missing_cup_days(cup_raw, min_dt, max_dt)

    print("=== Building standardized time intervals ===")
    intervals = build_standard_intervals(cup_full)

    # Print interval lengths in descending order for QA
    intervals_debug = intervals.copy()
    intervals_debug["interval_hours"] = (
        intervals_debug["interval_end"] - intervals_debug["interval_start"]
    ).dt.total_seconds() / 3600
    intervals_debug = intervals_debug.sort_values("interval_hours", ascending=False)
    print("\n=== Interval lengths (hours) descending ===")
    print(intervals_debug[["location", "obs_date", "interval_start", "interval_end", "interval_hours"]].to_string(index=False))

    # Debug: print first 5 intervals to verify windows
    print("\n=== Debug: First 5 Intervals ===")
    print(intervals[["location","interval_start","interval_end","obs_date"]].head())

    # EXPORT INTERVALS TO CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    intervals_export = intervals.copy()
    # Add interval duration in hours
    intervals_export["interval_hours"] = (
        intervals_export["interval_end"] - intervals_export["interval_start"]
    ).dt.total_seconds() / 3600
    # Add interval duration in days
    intervals_export["interval_days"] = intervals_export["interval_hours"] / 24
    # Add start time as time only
    intervals_export["start_time"] = intervals_export["interval_start"].dt.time
    # Add end time as time only
    intervals_export["end_time"] = intervals_export["interval_end"].dt.time
    
    intervals_export.to_csv(f"intervals_export_{timestamp}.csv", index=False)
    print(f"\n✅ Intervals exported to 'intervals_export_{timestamp}.csv'")
    print(f"   Total intervals: {len(intervals_export)}")
    print(f"   Columns: {intervals_export.columns.tolist()}")
    
    # Show sample of exported intervals
    print("\n=== Sample of exported intervals (first 10) ===")
    print(intervals_export[["location", "obs_date", "interval_start", "interval_end", "interval_hours"]].head(10))

    print("\n=== Calculating daily rainfall ===")
    daily_rain = aggregate_rain(bucket, intervals)

    daily_rain.to_csv(f"bucket_aligned_{timestamp}.csv", index=False)
    print(f"\n✅ Complete. Output saved to bucket_aligned_{timestamp}.csv")
    print("\nSample results:")
    print(daily_rain.head(10))

    return daily_rain

if __name__ == "__main__":
    daily_output = main()