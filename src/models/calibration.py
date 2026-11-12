import numpy as np
import pandas as pd
from src.models.quantile_utils import sort_quantiles


def get_calibration_origins(first_test_origin: pd.Timestamp, window_days: int = 90) -> pd.DatetimeIndex:
    return pd.date_range(
        end=first_test_origin - pd.Timedelta(days=1),
        periods=window_days,
        freq="D",
        tz=first_test_origin.tz,
    )


def calibrate(raw_test_df: pd.DataFrame, calib_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    res = raw_test_df.copy()
    if calib_df.empty or "y_true" not in calib_df.columns:
        return res

    cal_cfg = cfg.get("calibration", {})
    cov_80 = float(cal_cfg.get("coverage_80", 0.8))
    cov_90 = float(cal_cfg.get("coverage_90", 0.9))

    valid = calib_df.dropna(subset=["y_true", "p50"])
    if valid.empty:
        return res

    scores = (valid["y_true"] - valid["p50"]).abs().to_numpy()
    n = len(scores)
    q80_level = min(1.0, np.ceil((n + 1) * cov_80) / n)
    q90_level = min(1.0, np.ceil((n + 1) * cov_90) / n)
    q80 = float(np.quantile(scores, q80_level))
    q90 = float(np.quantile(scores, q90_level))

    res["p10"] = res["p50"] - q80
    res["p90"] = res["p50"] + q80
    res["p05"] = res["p50"] - q90
    res["p95"] = res["p50"] + q90

    return sort_quantiles(res)


def generate_calibration_predictions(
    forecaster_cls, cfg: dict, first_test_origin: pd.Timestamp, load_df: pd.DataFrame
) -> pd.DataFrame:
    calib_cfg = cfg.get("calibration", {})
    window_days = int(calib_cfg.get("window_days", 90))
    origins = get_calibration_origins(first_test_origin, window_days)
    forecaster = forecaster_cls(cfg)
    forecaster.fit(origins[0])
    load_map = dict(zip(load_df["ts"], load_df["load_mw"]))
    preds_list = []
    for o in origins:
        p = forecaster.predict(o).copy()
        p["origin_ts"] = o
        p["y_true"] = [load_map.get(t, np.nan) for t in p["target_ts"]]
        preds_list.append(p)
    if preds_list:
        return pd.concat(preds_list, ignore_index=True)
    return pd.DataFrame()
