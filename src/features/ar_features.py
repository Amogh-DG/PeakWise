import numpy as np
import pandas as pd


def build_ar_features(
    load_df: pd.DataFrame,
    origin_ts: pd.Timestamp,
    target_ts: pd.DatetimeIndex | pd.Timestamp,
) -> pd.DataFrame:
    if isinstance(target_ts, pd.Timestamp):
        targets = pd.DatetimeIndex([target_ts])
    else:
        targets = pd.DatetimeIndex(target_ts)

    if "ts" in load_df.columns:
        valid_load = load_df[load_df["ts"] < origin_ts]
        series = valid_load.set_index("ts")["load_mw"].sort_index()
    else:
        valid_load = load_df[load_df.index < origin_ts]
        series = valid_load["load_mw"].sort_index()

    last_known_ts = series.index.max()
    last_known_load = float(series.loc[last_known_ts]) if len(series) > 0 else np.nan

    cutoff_7d = origin_ts - pd.Timedelta(days=7)
    mean_7d_slice = series[series.index >= cutoff_7d]
    ar_mean_7d = float(mean_7d_slice.mean()) if len(mean_7d_slice) > 0 else np.nan
    ar_last_week_daily_peak = float(mean_7d_slice.max()) if len(mean_7d_slice) > 0 else np.nan

    cutoff_30d = origin_ts - pd.Timedelta(days=30)
    mean_30d_slice = series[series.index >= cutoff_30d]
    ar_mean_30d = float(mean_30d_slice.mean()) if len(mean_30d_slice) > 0 else np.nan

    cutoff_365d = origin_ts - pd.Timedelta(days=365)
    mean_365d_slice = series[series.index >= cutoff_365d]
    ar_level_365d = float(mean_365d_slice.mean()) if len(mean_365d_slice) > 0 else np.nan

    same_hour_last_week = []
    same_hour_last_known_day = []
    hours_since_last_known = []

    for tgt in targets:
        cand_week = tgt - pd.Timedelta(days=7)
        while cand_week >= origin_ts:
            cand_week -= pd.Timedelta(days=7)
        val_week = series.get(cand_week, np.nan)
        same_hour_last_week.append(float(val_week) if pd.notna(val_week) else np.nan)

        cand_day = tgt.floor("D") + pd.Timedelta(hours=tgt.hour)
        while cand_day >= origin_ts:
            cand_day -= pd.Timedelta(days=1)
        val_day = series.get(cand_day, np.nan)
        same_hour_last_known_day.append(float(val_day) if pd.notna(val_day) else np.nan)

        delta_h = (tgt - last_known_ts).total_seconds() / 3600.0
        hours_since_last_known.append(round(delta_h, 2))

    df = pd.DataFrame(
        {
            "ar_same_hour_last_week": same_hour_last_week,
            "ar_same_hour_last_known_day": same_hour_last_known_day,
            "ar_mean_7d": ar_mean_7d,
            "ar_mean_30d": ar_mean_30d,
            "ar_level_365d": ar_level_365d,
            "ar_last_known_load": last_known_load,
            "ar_last_week_daily_peak": ar_last_week_daily_peak,
            "ar_hours_since_last_known": hours_since_last_known,
        },
        index=targets,
    )
    return df
