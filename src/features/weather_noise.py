import numpy as np
import pandas as pd

from src.common.config import load_config


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


def noisy_weather(
    features_df: pd.DataFrame,
    origin_ts: pd.Timestamp,
    horizon_day: int,
    seed: int,
) -> pd.DataFrame:
    cfg = load_config()
    wn_cfg = cfg.get("weather_noise", {})
    base_sd = float(wn_cfg.get("base_sd_c", 0.5))
    growth_sd = float(wn_cfg.get("sd_growth_per_day_c", 0.4))
    cdh_base = float(cfg.get("cdh_base_c", 24))

    sd = base_sd + growth_sd * float(horizon_day)

    origin_hash = int(origin_ts.timestamp()) % (2**31 - 1)
    derived_seed = (int(seed) + origin_hash) % (2**31 - 1)
    rng = np.random.default_rng(derived_seed)

    df = features_df.copy()
    n = len(df)
    noise = rng.normal(loc=0.0, scale=sd, size=n)

    noisy_temp = (df["wx_temp_c"].values + noise).round(2)
    rh_pct = df["wx_rh_pct"].values

    heat_index = _compute_heat_index(noisy_temp, rh_pct).round(2)
    cdh = np.maximum(0.0, noisy_temp - cdh_base).round(2)
    cdh_24 = pd.Series(cdh).rolling(24, min_periods=1).sum().values.round(2)

    temp_s = pd.Series(noisy_temp)
    temp_lag_1 = temp_s.shift(1).bfill().values.round(2)
    temp_lag_3 = temp_s.shift(3).bfill().values.round(2)
    temp_lag_6 = temp_s.shift(6).bfill().values.round(2)
    temp_lag_12 = temp_s.shift(12).bfill().values.round(2)
    temp_lag_24 = temp_s.shift(24).bfill().values.round(2)
    temp_lag_48 = temp_s.shift(48).bfill().values.round(2)
    temp_lag_72 = temp_s.shift(72).bfill().values.round(2)
    temp_roll_24 = temp_s.rolling(24, min_periods=1).mean().values.round(2)
    temp_roll_72 = temp_s.rolling(72, min_periods=1).mean().values.round(2)

    df["wx_temp_c"] = noisy_temp
    df["wx_heat_index_c"] = heat_index
    df["wx_cdh"] = cdh
    df["wx_cdh_24"] = cdh_24
    df["wx_temp_lag_1"] = temp_lag_1
    df["wx_temp_lag_3"] = temp_lag_3
    df["wx_temp_lag_6"] = temp_lag_6
    df["wx_temp_lag_12"] = temp_lag_12
    df["wx_temp_lag_24"] = temp_lag_24
    df["wx_temp_lag_48"] = temp_lag_48
    df["wx_temp_lag_72"] = temp_lag_72
    df["wx_temp_roll_24"] = temp_roll_24
    df["wx_temp_roll_72"] = temp_roll_72
    df["wx_is_noisy"] = True

    return df
