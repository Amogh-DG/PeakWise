import sys
from pathlib import Path

import pandas as pd

from src.common import constants, paths


def find_raw_load_file() -> Path | None:
    raw_dir = paths.raw_dir()
    candidates = list(raw_dir.glob("*.csv")) + list(raw_dir.glob("*.parquet"))
    for cand in candidates:
        if cand.name.startswith("."):
            continue
        return cand
    return None


def print_missing_data_guidance() -> None:
    print("NO LOAD DATA FOUND in data/raw/")
    print("Please provide Delhi electricity demand data in data/raw/ (e.g. data/raw/load_data.csv).")
    print("Where to find real Delhi load data:")
    print("  1. Organizer dataset (hackathon problem statement attachments/portal)")
    print("  2. Delhi SLDC (State Load Despatch Centre) historical reports (https://www.delhisldc.org)")
    print("  3. Grid-India / POSOCO National/Regional load dispatch reports (https://grid-india.in)")
    print("  4. Kaggle Delhi power consumption / electricity demand datasets")
    print("Expected format:")
    print("  - CSV or Parquet format")
    print("  - Timestamp column (e.g. 'timestamp', 'datetime', 'ts') at 5-min, 15-min, or 1-hour resolution")
    print("  - Electricity demand column (e.g. 'load_MW', 'demand_mw', 'load_mw') in MW")


def ingest_load() -> pd.DataFrame:
    raw_file = find_raw_load_file()
    if raw_file is None:
        print_missing_data_guidance()
        sys.exit(1)

    print(f"Loading raw demand data from: {raw_file}")
    if raw_file.suffix.lower() == ".csv":
        df = pd.read_csv(raw_file)
    elif raw_file.suffix.lower() == ".parquet":
        df = pd.read_parquet(raw_file)
    else:
        raise ValueError(f"Unsupported file format: {raw_file.suffix}")

    ts_col = None
    for col in ["timestamp", "datetime", "ts", "Time", "Timestamp", "Date"]:
        if col in df.columns:
            ts_col = col
            break
    if ts_col is None:
        ts_col = df.columns[0]

    load_col = None
    for col in ["load_MW", "load_mw", "demand_mw", "demand_MW", "Load", "load", "demand"]:
        if col in df.columns:
            load_col = col
            break
    if load_col is None:
        load_col = df.columns[1]

    df = df[[ts_col, load_col]].rename(columns={ts_col: "ts", load_col: "load_mw"})
    df["load_mw"] = pd.to_numeric(df["load_mw"], errors="coerce")
    df["ts"] = pd.to_datetime(df["ts"])

    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize(constants.TZ)
    else:
        df["ts"] = df["ts"].dt.tz_convert(constants.TZ)

    df = df.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)

    proc_dir = paths.processed_dir()
    proc_dir.mkdir(parents=True, exist_ok=True)

    native_diffs = df["ts"].diff().dropna()
    is_finer = False
    if not native_diffs.empty:
        median_diff = native_diffs.median()
        if median_diff < pd.Timedelta(hours=1):
            is_finer = True

    if is_finer:
        native_path = proc_dir / "load_native.parquet"
        df.to_parquet(native_path, index=False)
        print(f"Saved native resolution load data to: {native_path}")

    hourly_df = (
        df.set_index("ts")
        .resample("1h")
        .mean()
        .reset_index()
    )

    hourly_path = proc_dir / "load_raw_hourly.parquet"
    hourly_df.to_parquet(hourly_path, index=False)
    print(f"Saved raw-ingested hourly load data to: {hourly_path}")

    total_rows = len(hourly_df)
    missing_count = int(hourly_df["load_mw"].isna().sum())
    pct_missing = (missing_count / total_rows * 100.0) if total_rows > 0 else 0.0
    min_load = float(hourly_df["load_mw"].min())
    max_load = float(hourly_df["load_mw"].max())
    start_ts = hourly_df["ts"].min()
    end_ts = hourly_df["ts"].max()

    print("\n--- Load Ingestion Summary ---")
    print(f"Date range: {start_ts} to {end_ts}")
    print(f"Total hourly rows: {total_rows}")
    print(f"Missing count: {missing_count} ({pct_missing:.2f}%)")
    print(f"Min load: {min_load:.2f} MW, Max load: {max_load:.2f} MW")

    return hourly_df


if __name__ == "__main__":
    ingest_load()
