import sys

import holidays
import numpy as np
import pandas as pd

from src.common import constants
from src.common.config import load_config
from src.common.paths import external_dir, processed_dir


def _calculate_daily_distances(fest_dates: pd.DatetimeIndex, target_dates: pd.DatetimeIndex):
    f_vals = fest_dates.values[:, None]
    t_vals = target_dates.values[None, :]
    diffs = (f_vals - t_vals) / np.timedelta64(1, "D")

    upcoming = np.where(diffs >= 0, diffs, 999.0).min(axis=0)
    past = np.where(diffs <= 0, -diffs, 999.0).min(axis=0)

    upcoming_clipped = np.clip(upcoming, -30.0, 30.0)
    past_clipped = np.clip(past, -30.0, 30.0)
    return upcoming_clipped, past_clipped


def _compute_heat_index(temp_c: np.ndarray, rh_pct: np.ndarray) -> np.ndarray:
    rothfusz = (
        -8.78469475556
        + 1.61139411 * temp_c
        + 2.33854883889 * rh_pct
        - 0.14611605 * temp_c * rh_pct
        - 0.012308094 * (temp_c**2)
        - 0.0164248277778 * (rh_pct**2)
        + 0.002211732 * (temp_c**2) * rh_pct
        + 0.00072546 * temp_c * (rh_pct**2)
        - 0.000003582 * (temp_c**2) * (rh_pct**2)
    )
    return np.where(temp_c >= 27.0, rothfusz, temp_c)


def build_known_features() -> pd.DataFrame:
    cfg = load_config()
    cdh_base = float(cfg.get("cdh_base_c", 24))

    weather_path = processed_dir() / "weather_hourly.parquet"
    weather_df = pd.read_parquet(weather_path)
    weather_df = weather_df.sort_values("ts").reset_index(drop=True)

    ts = weather_df["ts"]
    n = len(ts)

    hour = ts.dt.hour.values
    dow = ts.dt.dayofweek.values
    month = ts.dt.month.values
    doy = ts.dt.dayofyear.values

    cal_hour_sin = np.sin(2 * np.pi * hour / 24.0).round(6)
    cal_hour_cos = np.cos(2 * np.pi * hour / 24.0).round(6)
    cal_dow_sin = np.sin(2 * np.pi * dow / 7.0).round(6)
    cal_dow_cos = np.cos(2 * np.pi * dow / 7.0).round(6)
    cal_is_weekend = (dow >= 5)

    years = sorted(ts.dt.year.unique().tolist())
    in_holidays = holidays.India(years=years, subdiv="DL")

    date_strs = ts.dt.strftime("%Y-%m-%d").values
    cal_is_holiday = np.array([d in in_holidays for d in date_strs], dtype=bool)
    cal_holiday_name = [in_holidays.get(d) for d in date_strs]

    festivals_path = external_dir() / "festivals.csv"
    festivals_df = pd.read_csv(festivals_path)
    festivals_df["date"] = pd.to_datetime(festivals_df["date"]).dt.tz_localize(constants.TZ)

    unique_dates = pd.date_range(
        start=ts.min().floor("D"),
        end=ts.max().ceil("D"),
        freq="D",
        tz=constants.TZ,
    )
    date_to_idx = {d: i for i, d in enumerate(unique_dates)}
    ts_day_idx = np.array([date_to_idx[t.floor("D")] for t in ts])

    diwali_dates = festivals_df[festivals_df["festival"] == "Diwali"]["date"]
    holi_dates = festivals_df[festivals_df["festival"] == "Holi"]["date"]
    eid_dates = festivals_df[festivals_df["festival"].str.contains("Eid")]["date"]

    u_to_diwali, u_since_diwali = _calculate_daily_distances(diwali_dates, unique_dates)
    u_to_holi, u_since_holi = _calculate_daily_distances(holi_dates, unique_dates)
    u_to_eid, u_since_eid = _calculate_daily_distances(eid_dates, unique_dates)

    cal_days_to_diwali = u_to_diwali[ts_day_idx].round(1)
    cal_days_since_diwali = u_since_diwali[ts_day_idx].round(1)
    cal_days_to_holi = u_to_holi[ts_day_idx].round(1)
    cal_days_since_holi = u_since_holi[ts_day_idx].round(1)
    cal_days_to_eid = u_to_eid[ts_day_idx].round(1)
    cal_days_since_eid = u_since_eid[ts_day_idx].round(1)

    all_fest_vals = festivals_df["date"].values[:, None]
    u_vals = unique_dates.values[None, :]
    all_diffs_days = np.abs((all_fest_vals - u_vals) / np.timedelta64(1, "D"))
    min_dist_to_any_fest = all_diffs_days.min(axis=0)
    u_is_fest_window = min_dist_to_any_fest <= 2.0
    cal_is_festival_window = u_is_fest_window[ts_day_idx]

    events_path = external_dir() / "events.csv"
    events_df = pd.read_csv(events_path)
    evt_lockdown = np.zeros(n, dtype=np.int64)
    evt_odd_even = np.zeros(n, dtype=np.int64)

    for _, row in events_df.iterrows():
        notes = str(row.get("notes", "")).lower()
        if "deferred" in notes or "withdrawn" in notes or "proposed" in notes:
            continue
        start_ts = pd.to_datetime(row["start_date"]).tz_localize(constants.TZ)
        end_ts = pd.to_datetime(row["end_date"]).tz_localize(constants.TZ) + pd.Timedelta(days=1, microseconds=-1)
        event_name = str(row["event"]).lower()
        mask = (ts >= start_ts) & (ts <= end_ts)
        if "lockdown" in event_name:
            evt_lockdown = np.where(mask, 1, evt_lockdown)
        if "odd_even" in event_name:
            evt_odd_even = np.where(mask, 1, evt_odd_even)

    temp_c = weather_df["wx_temp_c"].values
    rh_pct = weather_df["wx_rh_pct"].values
    dewpoint_c = weather_df["wx_dewpoint_c"].values
    wind_ms = weather_df["wx_wind_ms"].values
    cloud_pct = weather_df["wx_cloud_pct"].values

    heat_index_c = _compute_heat_index(temp_c, rh_pct)
    cdh = np.maximum(0.0, temp_c - cdh_base)
    cdh_24 = pd.Series(cdh).rolling(24, min_periods=1).sum().values

    temp_s = pd.Series(temp_c)
    temp_lag_1 = temp_s.shift(1).bfill().values
    temp_lag_3 = temp_s.shift(3).bfill().values
    temp_lag_6 = temp_s.shift(6).bfill().values
    temp_lag_12 = temp_s.shift(12).bfill().values
    temp_lag_24 = temp_s.shift(24).bfill().values
    temp_lag_48 = temp_s.shift(48).bfill().values
    temp_lag_72 = temp_s.shift(72).bfill().values
    temp_roll_24 = temp_s.rolling(24, min_periods=1).mean().values
    temp_roll_72 = temp_s.rolling(72, min_periods=1).mean().values

    trend_t = ((ts - ts.iloc[0]).dt.total_seconds().values / 86400.0).round(4)
    wx_is_noisy = np.zeros(n, dtype=bool)

    features_df = pd.DataFrame(
        {
            "ts": ts,
            "cal_hour": hour.astype(np.int64),
            "cal_dow": dow.astype(np.int64),
            "cal_month": month.astype(np.int64),
            "cal_doy": doy.astype(np.int64),
            "cal_hour_sin": cal_hour_sin,
            "cal_hour_cos": cal_hour_cos,
            "cal_dow_sin": cal_dow_sin,
            "cal_dow_cos": cal_dow_cos,
            "cal_is_weekend": cal_is_weekend,
            "cal_is_holiday": cal_is_holiday,
            "cal_holiday_name": cal_holiday_name,
            "cal_days_to_diwali": cal_days_to_diwali,
            "cal_days_since_diwali": cal_days_since_diwali,
            "cal_days_to_holi": cal_days_to_holi,
            "cal_days_since_holi": cal_days_since_holi,
            "cal_days_to_eid": cal_days_to_eid,
            "cal_days_since_eid": cal_days_since_eid,
            "cal_is_festival_window": cal_is_festival_window,
            "evt_lockdown": evt_lockdown,
            "evt_odd_even": evt_odd_even,
            "wx_temp_c": temp_c.round(2),
            "wx_rh_pct": rh_pct.round(2),
            "wx_dewpoint_c": dewpoint_c.round(2),
            "wx_wind_ms": wind_ms.round(2),
            "wx_cloud_pct": cloud_pct.round(2),
            "wx_heat_index_c": heat_index_c.round(2),
            "wx_cdh": cdh.round(2),
            "wx_cdh_24": cdh_24.round(2),
            "wx_temp_lag_1": temp_lag_1.round(2),
            "wx_temp_lag_3": temp_lag_3.round(2),
            "wx_temp_lag_6": temp_lag_6.round(2),
            "wx_temp_lag_12": temp_lag_12.round(2),
            "wx_temp_lag_24": temp_lag_24.round(2),
            "wx_temp_lag_48": temp_lag_48.round(2),
            "wx_temp_lag_72": temp_lag_72.round(2),
            "wx_temp_roll_24": temp_roll_24.round(2),
            "wx_temp_roll_72": temp_roll_72.round(2),
            "trend_t": trend_t,
            "wx_is_noisy": wx_is_noisy,
        }
    )

    out_path = processed_dir() / "features_known.parquet"
    features_df.to_parquet(out_path, index=False, compression="snappy")
    print(f"Features shape: {features_df.shape}")
    print(f"Written: {out_path}")
    return features_df


if __name__ == "__main__":
    build_known_features()
    sys.exit(0)
