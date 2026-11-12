import numpy as np
import pandas as pd

from src.common import constants
from src.features.ar_features import build_ar_features
from src.features.weather_noise import noisy_weather

FEATURE_COLS = [
    "cal_hour",
    "cal_dow",
    "cal_month",
    "cal_doy",
    "cal_hour_sin",
    "cal_hour_cos",
    "cal_dow_sin",
    "cal_dow_cos",
    "cal_is_weekend",
    "cal_is_holiday",
    "cal_days_to_diwali",
    "cal_days_since_diwali",
    "cal_days_to_holi",
    "cal_days_since_holi",
    "cal_days_to_eid",
    "cal_days_since_eid",
    "cal_is_festival_window",
    "evt_lockdown",
    "evt_odd_even",
    "wx_temp_c",
    "wx_rh_pct",
    "wx_dewpoint_c",
    "wx_wind_ms",
    "wx_cloud_pct",
    "wx_heat_index_c",
    "wx_cdh",
    "wx_cdh_24",
    "wx_temp_lag_1",
    "wx_temp_lag_3",
    "wx_temp_lag_6",
    "wx_temp_lag_12",
    "wx_temp_lag_24",
    "wx_temp_lag_48",
    "wx_temp_lag_72",
    "wx_temp_roll_24",
    "wx_temp_roll_72",
    "trend_t",
    "ar_same_hour_last_week",
    "ar_same_hour_last_known_day",
    "ar_mean_7d",
    "ar_mean_30d",
    "ar_level_365d",
    "ar_last_known_load",
    "ar_last_week_daily_peak",
    "ar_hours_since_last_known",
    "horizon_h",
]


def build_features_for_origin(
    load_df: pd.DataFrame,
    features_df: pd.DataFrame,
    origin: pd.Timestamp,
    cfg: dict,
) -> pd.DataFrame:
    start_target = (origin + pd.Timedelta(days=1)).floor("D")
    targets = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

    feat_indexed = features_df.set_index("ts") if "ts" in features_df.columns else features_df
    common_targets = [t for t in targets if t in feat_indexed.index]

    if len(common_targets) != len(targets):
        missing_ts = [t for t in targets if t not in feat_indexed.index]
        filler = pd.DataFrame(index=missing_ts, columns=feat_indexed.columns)
        for col in filler.columns:
            filler[col] = 0.0
        feat_sub = pd.concat([feat_indexed.loc[common_targets], filler]).loc[targets]
    else:
        feat_sub = feat_indexed.loc[targets].copy()

    weather_noise_cfg = cfg.get("weather_noise", {})
    noise_enabled = bool(weather_noise_cfg.get("enabled", False))
    seed = int(cfg.get("seed", 42))

    if noise_enabled:
        day_slices = []
        for d in range(1, 8):
            day_targets = targets[(d - 1) * 24 : d * 24]
            sub = feat_sub.loc[day_targets].reset_index()
            if "index" in sub.columns:
                sub = sub.rename(columns={"index": "ts"})
            noisy_sub = noisy_weather(sub, origin_ts=origin, horizon_day=d, seed=seed)
            day_slices.append(noisy_sub)
        feat_combined = pd.concat(day_slices, ignore_index=True)
    else:
        feat_combined = feat_sub.reset_index()
        if "index" in feat_combined.columns:
            feat_combined = feat_combined.rename(columns={"index": "ts"})

    ar_df = build_ar_features(load_df, origin_ts=origin, target_ts=targets).reset_index(drop=True)

    horizon_h_vals = [(t - origin).total_seconds() // 3600 for t in targets]

    merged = pd.concat([feat_combined, ar_df], axis=1)
    merged["horizon_h"] = horizon_h_vals

    for col in FEATURE_COLS:
        if col not in merged.columns:
            merged[col] = 0.0
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    result = merged[FEATURE_COLS].copy()
    result.index = targets
    return result


def build_training_table(
    load_df: pd.DataFrame,
    features_df: pd.DataFrame,
    origins: list[pd.Timestamp],
    cfg: dict,
) -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    load_map = dict(zip(load_df["ts"], load_df["load_mw"]))
    outage_map = dict(zip(load_df["ts"], load_df["is_outage_suspect"]))

    x_list = []
    y_list = []
    weight_list = []

    for origin in origins:
        x_origin = build_features_for_origin(load_df, features_df, origin, cfg)
        targets = x_origin.index

        y_vals = [load_map.get(t, np.nan) for t in targets]
        outage_vals = [bool(outage_map.get(t, False)) for t in targets]

        valid_mask = [pd.notna(y) for y in y_vals]
        if not any(valid_mask):
            continue

        valid_indices = [i for i, v in enumerate(valid_mask) if v]
        x_valid = x_origin.iloc[valid_indices]
        y_valid = [y_vals[i] for i in valid_indices]
        w_valid = [0.0 if outage_vals[i] else 1.0 for i in valid_indices]

        x_list.append(x_valid)
        y_list.extend(y_valid)
        weight_list.extend(w_valid)

    if x_list:
        full_x = pd.concat(x_list, ignore_index=True)
        full_y = pd.Series(y_list, name="load_mw", dtype=float)
        full_weights = np.array(weight_list, dtype=float)
    else:
        full_x = pd.DataFrame(columns=FEATURE_COLS, dtype=float)
        full_y = pd.Series([], name="load_mw", dtype=float)
        full_weights = np.array([], dtype=float)

    return full_x, full_y, full_weights
