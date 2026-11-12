import numpy as np
import pandas as pd
from src.common import config, constants, paths


def generate_mock_data():
    cfg = config.load_config()
    seed = int(cfg.get("seed", 42))
    cdh_base = float(cfg.get("cdh_base_c", 24))
    np.random.seed(seed)

    target_dir = paths.repo_root() / "data" / "processed_mock"
    target_dir.mkdir(parents=True, exist_ok=True)

    ts = pd.date_range(
        start="2022-01-01 00:00:00",
        end="2024-12-31 23:00:00",
        freq="h",
        tz=constants.TZ,
    )
    n = len(ts)

    doy = getattr(ts, "day_of_year", getattr(ts, "dayofyear", None)).values
    hour = ts.hour.values
    dow = getattr(ts, "day_of_week", getattr(ts, "dayofweek", None)).values
    month = ts.month.values

    annual_temp = 25.0 - 11.0 * np.cos(2 * np.pi * (doy - 20) / 365.25)
    daily_temp = 5.5 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    weather_noise = np.random.normal(0, 1.2, size=n)
    temp_c = annual_temp + daily_temp + weather_noise

    is_summer = np.isin(month, [4, 5, 6])
    is_monsoon = np.isin(month, [7, 8, 9])
    base_rh = np.where(is_monsoon, 75.0, np.where(is_summer, 35.0, 55.0))
    daily_rh = -15.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    rh_pct = np.clip(base_rh + daily_rh + np.random.normal(0, 3.0, size=n), 10.0, 100.0)

    dewpoint_c = temp_c - ((100.0 - rh_pct) / 5.0)
    wind_ms = np.clip(2.5 + 1.0 * np.sin(2 * np.pi * (hour - 12) / 24.0) + np.random.normal(0, 0.5, size=n), 0.5, 15.0)
    cloud_pct = np.clip(np.where(is_monsoon, 65.0, 20.0) + np.random.normal(0, 10.0, size=n), 0.0, 100.0)

    heat_index_c = np.clip(
        np.where(
            temp_c >= 27.0,
            -8.78469475556
            + 1.61139411 * temp_c
            + 2.33854883889 * rh_pct
            - 0.14611605 * temp_c * rh_pct
            - 0.012308094 * (temp_c**2)
            - 0.0164248277778 * (rh_pct**2)
            + 0.002211732 * (temp_c**2) * rh_pct
            + 0.00072546 * temp_c * (rh_pct**2)
            - 0.000003582 * (temp_c**2) * (rh_pct**2),
            temp_c,
        ),
        -20.0,
        65.0,
    )

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

    trend_t = (ts - ts[0]).total_seconds().values / 86400.0

    holidays_delhi = {
        "2022-01-26": "Republic Day",
        "2022-03-18": "Holi",
        "2022-05-03": "Eid-ul-Fitr",
        "2022-08-15": "Independence Day",
        "2022-10-02": "Gandhi Jayanti",
        "2022-10-24": "Diwali",
        "2023-01-26": "Republic Day",
        "2023-03-08": "Holi",
        "2023-04-22": "Eid-ul-Fitr",
        "2023-08-15": "Independence Day",
        "2023-10-02": "Gandhi Jayanti",
        "2023-11-12": "Diwali",
        "2024-01-26": "Republic Day",
        "2024-03-25": "Holi",
        "2024-04-11": "Eid-ul-Fitr",
        "2024-08-15": "Independence Day",
        "2024-10-02": "Gandhi Jayanti",
        "2024-11-01": "Diwali",
    }
    date_strs = ts.strftime("%Y-%m-%d").values
    is_holiday = np.isin(date_strs, list(holidays_delhi.keys()))
    holiday_names = [holidays_delhi.get(d, None) for d in date_strs]

    diwali_dates = pd.to_datetime(["2022-10-24", "2023-11-12", "2024-11-01"]).tz_localize(constants.TZ)
    holi_dates = pd.to_datetime(["2022-03-18", "2023-03-08", "2024-03-25"]).tz_localize(constants.TZ)
    eid_dates = pd.to_datetime(["2022-05-03", "2023-04-22", "2024-04-11"]).tz_localize(constants.TZ)

    unique_dates = pd.date_range(start="2022-01-01", end="2024-12-31", freq="D", tz=constants.TZ)

    def calc_daily_distances(fest_dates):
        u_diffs = (fest_dates.values[:, None] - unique_dates.values[None, :]) / np.timedelta64(1, "D")
        upcoming = np.where(u_diffs >= 0, u_diffs, 999.0).min(axis=0)
        past = np.where(u_diffs <= 0, -u_diffs, 999.0).min(axis=0)
        return np.clip(upcoming, -30.0, 30.0), np.clip(past, -30.0, 30.0)

    u_to_diwali, u_since_diwali = calc_daily_distances(diwali_dates)
    u_to_holi, u_since_holi = calc_daily_distances(holi_dates)
    u_to_eid, u_since_eid = calc_daily_distances(eid_dates)

    days_to_diwali = np.repeat(u_to_diwali, 24)
    days_since_diwali = np.repeat(u_since_diwali, 24)
    days_to_holi = np.repeat(u_to_holi, 24)
    days_since_holi = np.repeat(u_since_holi, 24)
    days_to_eid = np.repeat(u_to_eid, 24)
    days_since_eid = np.repeat(u_since_eid, 24)

    min_festival_dist = np.minimum.reduce([
        np.abs(days_to_diwali),
        np.abs(days_since_diwali),
        np.abs(days_to_holi),
        np.abs(days_since_holi),
        np.abs(days_to_eid),
        np.abs(days_since_eid),
    ])
    is_festival_window = min_festival_dist <= 2.0

    evt_lockdown = np.zeros(n, dtype=np.int64)
    evt_odd_even = np.where(
        (ts >= "2023-11-13 00:00:00+05:30") & (ts <= "2023-11-20 23:00:00+05:30"),
        1,
        0,
    ).astype(np.int64)

    features_df = pd.DataFrame(
        {
            "ts": ts,
            "cal_hour": hour.astype(np.int64),
            "cal_dow": dow.astype(np.int64),
            "cal_month": month.astype(np.int64),
            "cal_doy": doy.astype(np.int64),
            "cal_hour_sin": np.sin(2 * np.pi * hour / 24.0).round(6),
            "cal_hour_cos": np.cos(2 * np.pi * hour / 24.0).round(6),
            "cal_dow_sin": np.sin(2 * np.pi * dow / 7.0).round(6),
            "cal_dow_cos": np.cos(2 * np.pi * dow / 7.0).round(6),
            "cal_is_weekend": (dow >= 5),
            "cal_is_holiday": is_holiday,
            "cal_holiday_name": holiday_names,
            "cal_days_to_diwali": days_to_diwali.round(1),
            "cal_days_since_diwali": days_since_diwali.round(1),
            "cal_days_to_holi": days_to_holi.round(1),
            "cal_days_since_holi": days_since_holi.round(1),
            "cal_days_to_eid": days_to_eid.round(1),
            "cal_days_since_eid": days_since_eid.round(1),
            "cal_is_festival_window": is_festival_window,
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
            "trend_t": trend_t.round(4),
            "wx_is_noisy": np.zeros(n, dtype=bool),
        }
    )

    base_mw = 2200.0 + trend_t * 0.4
    diurnal_curve = np.zeros(n, dtype=np.float64)
    for h in range(24):
        mask = (hour == h)
        if 6 <= h <= 10:
            val = 800.0 + 300.0 * np.sin(np.pi * (h - 6) / 4.0)
        elif 19 <= h <= 23:
            val = 1400.0 + 400.0 * np.sin(np.pi * (h - 19) / 4.0)
        elif 11 <= h <= 18:
            val = 900.0 + 200.0 * np.sin(np.pi * (h - 11) / 7.0)
        else:
            val = 200.0
        diurnal_curve[mask] = val

    cdh_load = cdh * 180.0 + (cdh_24 / 24.0) * 80.0
    winter_heating = np.maximum(0.0, 15.0 - temp_c) * 40.0
    weekend_factor = np.where(dow == 6, -400.0, np.where(dow == 5, -200.0, 0.0))
    festival_factor = np.where(is_holiday, -450.0, 0.0)
    random_fluctuation = np.random.normal(0, 70.0, size=n)

    simulated_load = (
        base_mw
        + diurnal_curve
        + cdh_load
        + winter_heating
        + weekend_factor
        + festival_factor
        + random_fluctuation
    )
    simulated_load = np.clip(simulated_load, 1800.0, 8400.0)

    is_imputed = np.zeros(n, dtype=bool)
    imputation_method = [None] * n
    is_outage_suspect = np.zeros(n, dtype=bool)

    gap_starts = [1200, 4500, 9200, 15400, 21800]
    for gs in gap_starts:
        gap_len = 2
        for offset in range(gap_len):
            idx = gs + offset
            if idx < n:
                is_imputed[idx] = True
                imputation_method[idx] = "linear" if offset == 0 else "hour_of_week"

    outage_indices = [2300, 5800, 8900, 12400, 16100, 19800, 23500, 25100]
    for oi in outage_indices:
        if oi < n:
            is_outage_suspect[oi] = True
            simulated_load[oi] = max(1000.0, simulated_load[oi] - 2200.0)

    load_df = pd.DataFrame(
        {
            "ts": ts,
            "load_mw": simulated_load.round(1),
            "is_imputed": is_imputed,
            "imputation_method": imputation_method,
            "is_outage_suspect": is_outage_suspect,
        }
    )

    load_df.to_parquet(target_dir / "load_hourly.parquet", index=False, compression="snappy")
    features_df.to_parquet(target_dir / "features_known.parquet", index=False, compression="snappy")


if __name__ == "__main__":
    generate_mock_data()
