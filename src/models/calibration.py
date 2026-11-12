from pathlib import Path
import numpy as np
import pandas as pd
from src.common import constants


def compute_conformal_delta(scores: np.ndarray, coverage: float) -> float:
    n = len(scores)
    if n == 0:
        return 0.0
    q_level = min(1.0, float(np.ceil((n + 1) * coverage) / n))
    sorted_scores = np.sort(scores)
    idx = int(np.clip(np.ceil(q_level * n) - 1, 0, n - 1))
    return float(sorted_scores[idx])


def get_calibration_origins(first_test_origin: pd.Timestamp, window_days: int) -> list[pd.Timestamp]:
    calib_end = first_test_origin - pd.Timedelta(days=1)
    calib_start = first_test_origin - pd.Timedelta(days=window_days)
    origins = pd.date_range(start=calib_start, end=calib_end, freq="D", tz=first_test_origin.tz)
    return [pd.Timestamp(o) for o in origins]


def calibrate(raw_pred_df: pd.DataFrame, calib_pred_df: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    calib_cfg = (cfg or {}).get("calibration", {})
    coverage_80 = float(calib_cfg.get("coverage_80", 0.8))
    coverage_90 = float(calib_cfg.get("coverage_90", 0.9))

    out_df = raw_pred_df.copy()
    if calib_pred_df is None or calib_pred_df.empty or "y_true" not in calib_pred_df.columns:
        return out_df

    valid_calib = calib_pred_df.dropna(subset=["y_true"]).copy()
    if valid_calib.empty:
        return out_df

    peak_hours = set(constants.PEAK_HOURS)

    def is_peak_series(ts_series: pd.Series) -> pd.Series:
        dt = pd.to_datetime(ts_series)
        return dt.dt.hour.isin(peak_hours)

    valid_calib["is_peak"] = is_peak_series(valid_calib["target_ts"])
    out_df["is_peak"] = is_peak_series(out_df["target_ts"])

    calib_y = valid_calib["y_true"].to_numpy()
    calib_p10 = valid_calib["p10"].to_numpy()
    calib_p90 = valid_calib["p90"].to_numpy()
    calib_p05 = valid_calib["p05"].to_numpy()
    calib_p95 = valid_calib["p95"].to_numpy()

    valid_calib["score_80"] = np.maximum(calib_p10 - calib_y, calib_y - calib_p90)
    valid_calib["score_90"] = np.maximum(calib_p05 - calib_y, calib_y - calib_p95)

    delta_map: dict[tuple[int, bool], tuple[float, float]] = {}

    for (h_day, peak), group in valid_calib.groupby(["horizon_day", "is_peak"]):
        d80 = compute_conformal_delta(group["score_80"].to_numpy(), coverage_80)
        d90 = compute_conformal_delta(group["score_90"].to_numpy(), coverage_90)
        delta_map[(int(h_day), bool(peak))] = (d80, d90)

    fallback_80 = compute_conformal_delta(valid_calib["score_80"].to_numpy(), coverage_80)
    fallback_90 = compute_conformal_delta(valid_calib["score_90"].to_numpy(), coverage_90)

    d80_list = []
    d90_list = []
    for _, row in out_df.iterrows():
        key = (int(row["horizon_day"]), bool(row["is_peak"]))
        if key in delta_map:
            d80, d90 = delta_map[key]
        else:
            d80, d90 = fallback_80, fallback_90
        d80_list.append(d80)
        d90_list.append(d90)

    d80_arr = np.array(d80_list)
    d90_arr = np.array(d90_list)

    p05 = out_df["p05"].to_numpy() - d90_arr
    p10 = out_df["p10"].to_numpy() - d80_arr
    p50 = out_df["p50"].to_numpy()
    p90 = out_df["p90"].to_numpy() + d80_arr
    p95 = out_df["p95"].to_numpy() + d90_arr

    p10 = np.minimum(p10, p50)
    p05 = np.minimum(p05, p10)
    p90 = np.maximum(p90, p50)
    p95 = np.maximum(p95, p90)

    out_df["p05"] = p05
    out_df["p10"] = p10
    out_df["p50"] = p50
    out_df["p90"] = p90
    out_df["p95"] = p95

    out_df = out_df.drop(columns=["is_peak"], errors="ignore")
    return out_df


def generate_calibration_predictions(
    forecaster_cls,
    cfg: dict,
    first_test_origin: pd.Timestamp,
    load_df: pd.DataFrame,
) -> pd.DataFrame:
    calib_cfg = cfg.get("calibration", {})
    window_days = int(calib_cfg.get("window_days", 90))
    calib_origins = get_calibration_origins(first_test_origin, window_days)
    if not calib_origins:
        return pd.DataFrame()

    min_ts = load_df["ts"].min()
    valid_calib_origins = [o for o in calib_origins if o >= min_ts + pd.Timedelta(days=35)]
    if not valid_calib_origins:
        return pd.DataFrame()

    m_name = getattr(forecaster_cls, "name", "")
    calib_stride = int(cfg.get("models", {}).get(m_name, {}).get("origin_stride", 1))
    if calib_stride > 1:
        valid_calib_origins = valid_calib_origins[::calib_stride]

    calib_start = valid_calib_origins[0]
    fit_end = calib_start

    calib_forecaster = forecaster_cls(cfg)
    calib_forecaster.fit(fit_end)

    load_map = dict(zip(load_df["ts"], load_df["load_mw"]))
    calib_dfs = []
    for o in valid_calib_origins:
        p = calib_forecaster.predict(o).copy()
        p["y_true"] = [load_map.get(t, None) for t in p["target_ts"]]
        p["origin_ts"] = o
        calib_dfs.append(p)

    if not calib_dfs:
        return pd.DataFrame()
    return pd.concat(calib_dfs, ignore_index=True)


def calibrate_fold(
    raw_fold_preds: pd.DataFrame,
    forecaster_cls,
    cfg: dict,
    first_test_origin: pd.Timestamp,
    load_df: pd.DataFrame,
) -> pd.DataFrame:
    calib_df = generate_calibration_predictions(forecaster_cls, cfg, first_test_origin, load_df)
    return calibrate(raw_fold_preds, calib_df, cfg)
