FEATURE_GROUPS = {
    "cal_hour": "calendar",
    "cal_dow": "calendar",
    "cal_month": "calendar",
    "cal_doy": "calendar",
    "cal_hour_sin": "calendar",
    "cal_hour_cos": "calendar",
    "cal_dow_sin": "calendar",
    "cal_dow_cos": "calendar",
    "cal_is_weekend": "calendar",
    "cal_is_holiday": "calendar",
    "cal_days_to_diwali": "festival",
    "cal_days_since_diwali": "festival",
    "cal_days_to_holi": "festival",
    "cal_days_since_holi": "festival",
    "cal_days_to_eid": "festival",
    "cal_days_since_eid": "festival",
    "cal_is_festival_window": "festival",
    "evt_lockdown": "event",
    "evt_odd_even": "event",
    "wx_temp_c": "weather",
    "wx_rh_pct": "weather",
    "wx_dewpoint_c": "weather",
    "wx_wind_ms": "weather",
    "wx_cloud_pct": "weather",
    "wx_heat_index_c": "weather",
    "wx_cdh": "weather",
    "wx_cdh_24": "weather",
    "wx_temp_lag_1": "thermal_inertia",
    "wx_temp_lag_3": "thermal_inertia",
    "wx_temp_lag_6": "thermal_inertia",
    "wx_temp_lag_12": "thermal_inertia",
    "wx_temp_lag_24": "thermal_inertia",
    "wx_temp_lag_48": "thermal_inertia",
    "wx_temp_lag_72": "thermal_inertia",
    "wx_temp_roll_24": "thermal_inertia",
    "wx_temp_roll_72": "thermal_inertia",
    "trend_t": "trend",
    "ar_same_hour_last_week": "autoregressive",
    "ar_same_hour_last_known_day": "autoregressive",
    "ar_mean_7d": "autoregressive",
    "ar_mean_30d": "autoregressive",
    "ar_level_365d": "autoregressive",
    "ar_last_known_load": "autoregressive",
    "ar_last_week_daily_peak": "autoregressive",
    "ar_hours_since_last_known": "autoregressive",
    "horizon_h": "horizon",
    "horizon_day": "horizon",
}


def group_of(feature: str) -> str:
    if feature in FEATURE_GROUPS:
        return FEATURE_GROUPS[feature]
    if "diwali" in feature or "holi" in feature or "eid" in feature or "festival" in feature:
        return "festival"
    if feature.startswith("cal_"):
        return "calendar"
    if feature.startswith("evt_"):
        return "event"
    if "lag" in feature or "roll" in feature:
        return "thermal_inertia"
    if feature.startswith("wx_"):
        return "weather"
    if feature.startswith("ar_") or "load" in feature:
        return "autoregressive"
    if "trend" in feature:
        return "trend"
    if "horizon" in feature:
        return "horizon"
    return "calendar"
