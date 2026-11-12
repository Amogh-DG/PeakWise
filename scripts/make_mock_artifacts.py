import json
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
from src.common import config, constants, paths, seasons


def generate_mock_artifacts():
    cfg = config.load_config()
    seed = int(cfg.get("seed", 42))
    np.random.seed(seed)

    target_dir = paths.repo_root() / "artifacts_mock"
    target_dir.mkdir(parents=True, exist_ok=True)

    processed_dir = paths.repo_root() / "data" / "processed_mock"
    load_df = pd.read_parquet(processed_dir / "load_hourly.parquet")
    load_map = dict(zip(load_df["ts"].values, load_df["load_mw"].values))
    outage_map = dict(zip(load_df["ts"].values, load_df["is_outage_suspect"].values))

    origins = pd.date_range(
        start="2024-01-01 10:00:00",
        end="2024-12-24 10:00:00",
        freq="D",
        tz=constants.TZ,
    )

    models_list = constants.MODELS
    records = []

    model_scales = {
        "ensemble": 140.0,
        "lgbm": 160.0,
        "xgboost": 175.0,
        "lstm": 200.0,
        "linear": 260.0,
        "prophet": 280.0,
        "seasonal_naive": 360.0,
    }

    for orig_idx, origin_ts in enumerate(origins):
        fold_id = int(orig_idx // 30)
        start_target = (origin_ts + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(
            start=start_target,
            periods=168,
            freq="h",
            tz=constants.TZ,
        )

        for h_step, target_ts in enumerate(target_hours):
            horizon_h = int((target_ts - origin_ts).total_seconds() // 3600)
            horizon_day = int(h_step // 24 + 1)
            ts_key = target_ts.to_datetime64()
            y_true = float(load_map.get(ts_key, 4000.0))
            is_outage = bool(outage_map.get(ts_key, False))

            day_mult = 1.0 + 0.12 * (horizon_day - 1)

            for m in models_list:
                sd = model_scales[m] * day_mult
                err = float(np.random.normal(0, sd))
                p50 = round(y_true + err, 1)

                w80 = 2.56 * sd
                w90 = 3.29 * sd

                p10 = round(p50 - 0.5 * w80, 1)
                p90 = round(p50 + 0.5 * w80, 1)
                p05 = round(p50 - 0.5 * w90, 1)
                p95 = round(p50 + 0.5 * w90, 1)

                p05 = min(p05, p10)
                p10 = min(p10, p50)
                p90 = max(p90, p50)
                p95 = max(p95, p90)

                raw_shift = float(np.random.normal(0, 5.0))
                p50_raw = round(p50 + raw_shift, 1)
                p10_raw = round(p50_raw - 0.46 * w80, 1)
                p90_raw = round(p50_raw + 0.46 * w80, 1)
                p05_raw = round(p50_raw - 0.48 * w90, 1)
                p95_raw = round(p50_raw + 0.48 * w90, 1)

                p05_raw = min(p05_raw, p10_raw)
                p10_raw = min(p10_raw, p50_raw)
                p90_raw = max(p90_raw, p50_raw)
                p95_raw = max(p95_raw, p90_raw)

                records.append((
                    m,
                    fold_id,
                    origin_ts,
                    target_ts,
                    horizon_h,
                    horizon_day,
                    y_true,
                    p05,
                    p10,
                    p50,
                    p90,
                    p95,
                    p05_raw,
                    p10_raw,
                    p50_raw,
                    p90_raw,
                    p95_raw,
                    is_outage,
                ))

    pred_df = pd.DataFrame(
        records,
        columns=[
            "model",
            "fold_id",
            "origin_ts",
            "target_ts",
            "horizon_h",
            "horizon_day",
            "y_true",
            "p05",
            "p10",
            "p50",
            "p90",
            "p95",
            "p05_raw",
            "p10_raw",
            "p50_raw",
            "p90_raw",
            "p95_raw",
            "is_outage_suspect",
        ],
    )
    pred_df["model"] = pred_df["model"].astype(str)
    pred_df["fold_id"] = pred_df["fold_id"].astype(np.int32)
    pred_df["horizon_h"] = pred_df["horizon_h"].astype(np.int32)
    pred_df["horizon_day"] = pred_df["horizon_day"].astype(np.int32)
    pred_df.to_parquet(target_dir / "predictions_backtest.parquet", index=False, compression="snappy")

    threshold_mw = 7650.0
    unique_dates = sorted(list({ts.strftime("%Y-%m-%d") for ts in pred_df["target_ts"]}))
    peak_records = []
    ens_df = pred_df[pred_df["model"] == "ensemble"]

    for d_str in unique_dates:
        d_preds = ens_df[ens_df["target_ts"].dt.strftime("%Y-%m-%d") == d_str]
        if d_preds.empty:
            continue
        first_row = d_preds.iloc[0]
        fold_id = int(first_row["fold_id"])
        origin_ts = first_row["origin_ts"]

        actual_max_idx = d_preds["y_true"].idxmax()
        actual_max_row = d_preds.loc[actual_max_idx]
        actual_peak_mw = round(float(actual_max_row["y_true"]), 1)
        actual_peak_ts = actual_max_row["target_ts"]
        actual_is_peak = bool(actual_peak_mw >= threshold_mw)

        pred_max_idx = d_preds["p50"].idxmax()
        pred_max_row = d_preds.loc[pred_max_idx]
        pred_peak_ts = pred_max_row["target_ts"]
        pred_peak_hour = int(pred_peak_ts.hour)
        pred_peak_p10 = round(float(pred_max_row["p10"]), 1)
        pred_peak_p50 = round(float(pred_max_row["p50"]), 1)
        pred_peak_p90 = round(float(pred_max_row["p90"]), 1)

        decision_threshold = 0.35
        if actual_is_peak:
            peak_probability = round(float(np.random.uniform(0.36, 0.95)), 2)
        else:
            peak_probability = round(float(np.random.uniform(0.02, 0.40)), 2)

        pred_is_peak = bool(peak_probability >= decision_threshold)

        if pred_is_peak and actual_is_peak:
            outcome = "hit"
        elif not pred_is_peak and actual_is_peak:
            outcome = "miss"
        elif pred_is_peak and not actual_is_peak:
            outcome = "false_alarm"
        else:
            outcome = "correct_reject"

        timing_error_min = int((pred_peak_ts - actual_peak_ts).total_seconds() // 60)
        magnitude_error_mw = round(pred_peak_p50 - actual_peak_mw, 1)

        peak_records.append((
            "ensemble",
            fold_id,
            origin_ts,
            pd.to_datetime(d_str).date(),
            threshold_mw,
            peak_probability,
            decision_threshold,
            pred_is_peak,
            pred_peak_hour,
            pred_peak_ts,
            pred_peak_p10,
            pred_peak_p50,
            pred_peak_p90,
            actual_is_peak,
            actual_peak_ts,
            actual_peak_mw,
            timing_error_min,
            magnitude_error_mw,
            outcome,
        ))

    peak_df = pd.DataFrame(
        peak_records,
        columns=[
            "model",
            "fold_id",
            "origin_ts",
            "date",
            "threshold_mw",
            "peak_probability",
            "decision_threshold",
            "pred_is_peak",
            "pred_peak_hour",
            "pred_peak_ts",
            "pred_peak_mw_p10",
            "pred_peak_mw_p50",
            "pred_peak_mw_p90",
            "actual_is_peak",
            "actual_peak_ts",
            "actual_peak_mw",
            "timing_error_min",
            "magnitude_error_mw",
            "outcome",
        ],
    )
    outcomes = set(peak_df["outcome"])
    for missing_outcome in {"hit", "miss", "false_alarm", "correct_reject"} - outcomes:
        if missing_outcome == "miss":
            peak_df.loc[0, "outcome"] = "miss"
            peak_df.loc[0, "pred_is_peak"] = False
            peak_df.loc[0, "actual_is_peak"] = True
            peak_df.loc[0, "peak_probability"] = 0.20
        elif missing_outcome == "false_alarm":
            peak_df.loc[1, "outcome"] = "false_alarm"
            peak_df.loc[1, "pred_is_peak"] = True
            peak_df.loc[1, "actual_is_peak"] = False
            peak_df.loc[1, "peak_probability"] = 0.65

    peak_df.to_parquet(target_dir / "peak_predictions.parquet", index=False, compression="snappy")

    pred_df["month"] = pred_df["target_ts"].dt.month
    pred_df["hour"] = pred_df["target_ts"].dt.hour
    pred_df["season"] = pred_df["month"].apply(seasons.season_of)
    pred_df["is_peak_hour"] = pred_df["hour"].isin(constants.PEAK_HOURS)

    y_all = pred_df["y_true"].values
    p50_all = pred_df["p50"].values
    p10_all = pred_df["p10"].values
    p90_all = pred_df["p90"].values
    p05_all = pred_df["p05"].values
    p95_all = pred_df["p95"].values

    pred_df["err"] = y_all - p50_all
    pred_df["abs_err"] = np.abs(pred_df["err"])
    pred_df["ape"] = pred_df["abs_err"] / y_all
    pred_df["sq_err"] = pred_df["err"] ** 2
    pred_df["bias"] = p50_all - y_all

    pb05 = np.maximum(0.05 * (y_all - p05_all), 0.95 * (p05_all - y_all))
    pb10 = np.maximum(0.10 * (y_all - p10_all), 0.90 * (p10_all - y_all))
    pb50 = np.maximum(0.50 * (y_all - p50_all), 0.50 * (p50_all - y_all))
    pb90 = np.maximum(0.90 * (y_all - p90_all), 0.10 * (p90_all - y_all))
    pb95 = np.maximum(0.95 * (y_all - p95_all), 0.05 * (p95_all - y_all))
    pred_df["pinball"] = (pb05 + pb10 + pb50 + pb90 + pb95) / 5.0
    pred_df["in_80"] = ((y_all >= p10_all) & (y_all <= p90_all)).astype(float)
    pred_df["in_90"] = ((y_all >= p05_all) & (y_all <= p95_all)).astype(float)
    pred_df["width_80"] = p90_all - p10_all

    segments = ["all", "winter", "summer", "monsoon", "post_monsoon", "peak_hours", "off_peak"]
    horizons = [1, 2, 3, 4, 5, 6, 7, "all"]

    metric_lookup = {}
    accuracy_rows = []

    for m in models_list:
        m_df = pred_df[pred_df["model"] == m]
        for h in horizons:
            h_df = m_df if h == "all" else m_df[m_df["horizon_day"] == h]
            for seg in segments:
                if seg == "all":
                    s_df = h_df
                elif seg in seasons.SEASONS:
                    s_df = h_df[h_df["season"] == seg]
                elif seg == "peak_hours":
                    s_df = h_df[h_df["is_peak_hour"]]
                elif seg == "off_peak":
                    s_df = h_df[~h_df["is_peak_hour"]]

                n = len(s_df)
                if n == 0:
                    continue

                mape = float(s_df["ape"].mean() * 100.0)
                rmse = float(np.sqrt(s_df["sq_err"].mean()))
                mae = float(s_df["abs_err"].mean())
                bias = float(s_df["bias"].mean())
                pinball = float(s_df["pinball"].mean())
                picp_80 = float(s_df["in_80"].mean())
                picp_90 = float(s_df["in_90"].mean())
                mpiw_80 = float(s_df["width_80"].mean())

                metric_lookup[(m, h, seg)] = {
                    "n": int(n),
                    "mape": round(mape, 2),
                    "rmse_mw": round(rmse, 1),
                    "mae_mw": round(mae, 1),
                    "bias_mw": round(bias, 1),
                    "pinball": round(pinball, 1),
                    "picp_80": round(picp_80, 2),
                    "picp_90": round(picp_90, 2),
                    "mpiw_80_mw": round(mpiw_80, 1),
                }

    for m in models_list:
        for h in horizons:
            for seg in segments:
                key = (m, h, seg)
                if key not in metric_lookup:
                    continue
                vals = metric_lookup[key]
                row = {
                    "model": m,
                    "horizon_day": h,
                    "segment": seg,
                    "n": vals["n"],
                    "mape": vals["mape"],
                    "rmse_mw": vals["rmse_mw"],
                    "mae_mw": vals["mae_mw"],
                    "bias_mw": vals["bias_mw"],
                    "pinball": vals["pinball"],
                    "picp_80": vals["picp_80"],
                    "picp_90": vals["picp_90"],
                    "mpiw_80_mw": vals["mpiw_80_mw"],
                }
                if m == constants.BASELINE_MODEL:
                    row["improvement_mape_pct"] = None
                    row["improvement_rmse_pct"] = None
                else:
                    base_vals = metric_lookup.get((constants.BASELINE_MODEL, h, seg))
                    if base_vals:
                        row["improvement_mape_pct"] = round(
                            (base_vals["mape"] - vals["mape"]) / base_vals["mape"] * 100.0,
                            1,
                        )
                        row["improvement_rmse_pct"] = round(
                            (base_vals["rmse_mw"] - vals["rmse_mw"]) / base_vals["rmse_mw"] * 100.0,
                            1,
                        )
                    else:
                        row["improvement_mape_pct"] = None
                        row["improvement_rmse_pct"] = None
                accuracy_rows.append(row)

    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
    metrics_accuracy_data = {
        "generated_at": ist_now,
        "rows": accuracy_rows,
    }
    with open(target_dir / "metrics_accuracy.json", "w", encoding="utf-8") as f:
        json.dump(metrics_accuracy_data, f, indent=2)

    metrics_peak_data = {
        "threshold_definition": "90th percentile of daily peak MW in each fold's training window",
        "rows": [
            {
                "model": "ensemble",
                "classifier": "lgbm_clf",
                "n_days": int(len(peak_df)),
                "n_peak_days": int((peak_df["actual_is_peak"] == True).sum()),
                "precision": 0.74,
                "recall": 0.83,
                "f1": 0.78,
                "pr_auc": 0.81,
                "confusion": {"tp": 29, "fp": 10, "fn": 6, "tn": int(len(peak_df) - 45)},
                "decision_threshold": 0.35,
                "timing_mae_min": 74.0,
                "timing_within_1h_pct": 0.76,
                "magnitude_mae_mw": 265.0,
                "magnitude_bias_mw": -32.0,
            },
            {
                "model": "seasonal_naive",
                "classifier": "rule_same_weekday_last_week",
                "n_days": int(len(peak_df)),
                "n_peak_days": int((peak_df["actual_is_peak"] == True).sum()),
                "precision": 0.52,
                "recall": 0.58,
                "f1": 0.55,
                "pr_auc": 0.54,
                "confusion": {"tp": 20, "fp": 18, "fn": 15, "tn": int(len(peak_df) - 53)},
                "decision_threshold": 0.50,
                "timing_mae_min": 125.0,
                "timing_within_1h_pct": 0.52,
                "magnitude_mae_mw": 460.0,
                "magnitude_bias_mw": -85.0,
            },
        ],
    }
    with open(target_dir / "metrics_peak.json", "w", encoding="utf-8") as f:
        json.dump(metrics_peak_data, f, indent=2)

    heatmap_cells = []
    for hm_model in ["ensemble", "seasonal_naive"]:
        for metric_name in ["mape", "rmse", "bias"]:
            for h_opt in [1, "all"]:
                subset = pred_df[pred_df["model"] == hm_model]
                if h_opt != "all":
                    subset = subset[subset["horizon_day"] == h_opt]

                v_grid = []
                c_grid = []
                for s_name in seasons.SEASONS:
                    s_row_v = []
                    s_row_c = []
                    for h_int in range(24):
                        sh_df = subset[(subset["season"] == s_name) & (subset["hour"] == h_int)]
                        c_val = int(len(sh_df))
                        if c_val > 0:
                            if metric_name == "mape":
                                val = float(sh_df["ape"].mean() * 100.0)
                            elif metric_name == "rmse":
                                val = float(np.sqrt(sh_df["sq_err"].mean()))
                            else:
                                val = float(sh_df["bias"].mean())
                        else:
                            val = 0.0
                        s_row_v.append(round(val, 2))
                        s_row_c.append(c_val)
                    v_grid.append(s_row_v)
                    c_grid.append(s_row_c)

                heatmap_cells.append({
                    "model": hm_model,
                    "metric": metric_name,
                    "horizon_day": h_opt,
                    "hours": list(range(24)),
                    "seasons": list(seasons.SEASONS),
                    "values": v_grid,
                    "counts": c_grid,
                })

    with open(target_dir / "error_heatmap.json", "w", encoding="utf-8") as f:
        json.dump({"cells": heatmap_cells}, f, indent=2)

    missed_records = [
        {
            "model": "ensemble",
            "date": "2024-05-29",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.22,
            "pred_peak_ts": "2024-05-29T15:00:00+05:30",
            "pred_peak_mw_p50": 7410.0,
            "actual_peak_ts": "2024-05-29T22:00:00+05:30",
            "actual_peak_mw": 7890.0,
            "magnitude_error_mw": -480.0,
            "timing_error_min": -420,
            "tags": ["heatwave", "weather_miss"],
            "note": "Actual max temp 3.1 °C above weather proxy; peak shifted to night due to cooling thermal inertia.",
        },
        {
            "model": "ensemble",
            "date": "2024-06-18",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.28,
            "pred_peak_ts": "2024-06-18T16:00:00+05:30",
            "pred_peak_mw_p50": 7450.0,
            "actual_peak_ts": "2024-06-18T22:00:00+05:30",
            "actual_peak_mw": 7910.0,
            "magnitude_error_mw": -460.0,
            "timing_error_min": -360,
            "tags": ["heatwave"],
            "note": "Sustained high humidity in late afternoon drove continuous nighttime AC load.",
        },
        {
            "model": "ensemble",
            "date": "2024-06-12",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.31,
            "pred_peak_ts": "2024-06-12T15:00:00+05:30",
            "pred_peak_mw_p50": 7490.0,
            "actual_peak_ts": "2024-06-12T21:00:00+05:30",
            "actual_peak_mw": 7880.0,
            "magnitude_error_mw": -390.0,
            "timing_error_min": -360,
            "tags": ["heatwave", "weather_miss"],
            "note": "Heat index was severely underestimated leading to an under-forecasted evening peak.",
        },
        {
            "model": "ensemble",
            "date": "2024-07-08",
            "season": "monsoon",
            "threshold_mw": 7650.0,
            "peak_probability": 0.25,
            "pred_peak_ts": "2024-07-08T15:00:00+05:30",
            "pred_peak_mw_p50": 7380.0,
            "actual_peak_ts": "2024-07-08T22:00:00+05:30",
            "actual_peak_mw": 7740.0,
            "magnitude_error_mw": -360.0,
            "timing_error_min": -420,
            "tags": ["weather_miss", "other"],
            "note": "Monsoon rain break created sharp spike in humidity and cooling demand.",
        },
        {
            "model": "ensemble",
            "date": "2024-05-15",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.33,
            "pred_peak_ts": "2024-05-15T15:00:00+05:30",
            "pred_peak_mw_p50": 7420.0,
            "actual_peak_ts": "2024-05-15T21:00:00+05:30",
            "actual_peak_mw": 7760.0,
            "magnitude_error_mw": -340.0,
            "timing_error_min": -360,
            "tags": ["heatwave"],
            "note": "Early summer heatwave breached 44 °C peak temperatures.",
        },
        {
            "model": "ensemble",
            "date": "2024-11-01",
            "season": "post_monsoon",
            "threshold_mw": 7650.0,
            "peak_probability": 0.15,
            "pred_peak_ts": "2024-11-01T20:00:00+05:30",
            "pred_peak_mw_p50": 6800.0,
            "actual_peak_ts": "2024-11-01T21:00:00+05:30",
            "actual_peak_mw": 7110.0,
            "magnitude_error_mw": -310.0,
            "timing_error_min": -60,
            "tags": ["festival"],
            "note": "Diwali evening lighting load exceeded expected holiday reduction.",
        },
        {
            "model": "ensemble",
            "date": "2024-06-25",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.30,
            "pred_peak_ts": "2024-06-25T15:00:00+05:30",
            "pred_peak_mw_p50": 7460.0,
            "actual_peak_ts": "2024-06-25T19:00:00+05:30",
            "actual_peak_mw": 7750.0,
            "magnitude_error_mw": -290.0,
            "timing_error_min": -240,
            "tags": ["weather_miss"],
            "note": "Cloud cover forecast was delayed, causing early evening peak.",
        },
        {
            "model": "ensemble",
            "date": "2024-03-25",
            "season": "summer",
            "threshold_mw": 7650.0,
            "peak_probability": 0.10,
            "pred_peak_ts": "2024-03-25T19:00:00+05:30",
            "pred_peak_mw_p50": 5500.0,
            "actual_peak_ts": "2024-03-25T21:00:00+05:30",
            "actual_peak_mw": 5780.0,
            "magnitude_error_mw": -280.0,
            "timing_error_min": -120,
            "tags": ["holiday", "festival"],
            "note": "Holi celebration post-event evening ramp was sharper than modeled.",
        },
        {
            "model": "ensemble",
            "date": "2024-08-15",
            "season": "monsoon",
            "threshold_mw": 7650.0,
            "peak_probability": 0.18,
            "pred_peak_ts": "2024-08-15T15:00:00+05:30",
            "pred_peak_mw_p50": 6300.0,
            "actual_peak_ts": "2024-08-15T20:00:00+05:30",
            "actual_peak_mw": 6550.0,
            "magnitude_error_mw": -250.0,
            "timing_error_min": -300,
            "tags": ["holiday", "weekend"],
            "note": "Independence Day national holiday commercial dip pattern shifted into evening residential spike.",
        },
    ]
    missed_records.sort(key=lambda item: abs(item["magnitude_error_mw"]), reverse=True)
    with open(target_dir / "missed_peaks.json", "w", encoding="utf-8") as f:
        json.dump({"items": missed_records}, f, indent=2)

    feature_importance_data = {
        "models": {
            "lgbm": [
                {"feature": "wx_cdh_24", "importance": 0.182, "group": "weather"},
                {"feature": "ar_same_hour_last_week", "importance": 0.141, "group": "autoregressive"},
                {"feature": "wx_heat_index_c", "importance": 0.125, "group": "weather"},
                {"feature": "ar_same_hour_last_known_day", "importance": 0.110, "group": "autoregressive"},
                {"feature": "wx_temp_roll_24", "importance": 0.088, "group": "thermal_inertia"},
                {"feature": "cal_hour_sin", "importance": 0.075, "group": "calendar"},
                {"feature": "cal_hour_cos", "importance": 0.071, "group": "calendar"},
                {"feature": "wx_temp_c", "importance": 0.065, "group": "weather"},
                {"feature": "cal_dow", "importance": 0.048, "group": "calendar"},
                {"feature": "ar_last_week_daily_peak", "importance": 0.038, "group": "autoregressive"},
                {"feature": "trend_t", "importance": 0.032, "group": "trend"},
                {"feature": "cal_is_festival_window", "importance": 0.025, "group": "festival"},
            ],
            "xgboost": [
                {"feature": "wx_cdh_24", "importance": 0.190, "group": "weather"},
                {"feature": "ar_same_hour_last_week", "importance": 0.145, "group": "autoregressive"},
                {"feature": "wx_heat_index_c", "importance": 0.118, "group": "weather"},
                {"feature": "ar_same_hour_last_known_day", "importance": 0.108, "group": "autoregressive"},
                {"feature": "wx_temp_roll_24", "importance": 0.092, "group": "thermal_inertia"},
                {"feature": "cal_hour_sin", "importance": 0.072, "group": "calendar"},
                {"feature": "cal_hour_cos", "importance": 0.068, "group": "calendar"},
                {"feature": "wx_temp_c", "importance": 0.062, "group": "weather"},
                {"feature": "cal_dow", "importance": 0.050, "group": "calendar"},
                {"feature": "ar_last_week_daily_peak", "importance": 0.036, "group": "autoregressive"},
                {"feature": "trend_t", "importance": 0.034, "group": "trend"},
                {"feature": "cal_is_festival_window", "importance": 0.025, "group": "festival"},
            ],
        }
    }
    for m_name in ["lgbm", "xgboost"]:
        items = feature_importance_data["models"][m_name]
        total_imp = sum(item["importance"] for item in items)
        for item in items:
            item["importance"] = round(item["importance"] / total_imp, 4)

    with open(target_dir / "feature_importance.json", "w", encoding="utf-8") as f:
        json.dump(feature_importance_data, f, indent=2)

    procurement_defaults_data = {
        "tariff": {
            "da_price_inr_per_mwh": 5000,
            "under_price_inr_per_mwh": 12000,
            "resale_price_inr_per_mwh": 2500,
        },
        "disclaimer": "Illustrative placeholder values, not actual DISCOM tariffs. See docs/ASSUMPTIONS.md.",
        "default_risk_quantile": 0.9,
    }
    with open(target_dir / "procurement_defaults.json", "w", encoding="utf-8") as f:
        json.dump(procurement_defaults_data, f, indent=2)

    meta_data = {
        "version": "1.0.0",
        "timezone": constants.TZ,
        "origin_hour_local": int(cfg.get("origin_hour_local", 10)),
        "data_range": {
            "start": "2022-01-01T00:00:00+05:30",
            "end": "2024-12-31T23:00:00+05:30",
        },
        "backtest_range": {
            "start": "2024-01-01",
            "end": "2024-12-31",
        },
        "quantiles": constants.QUANTILES,
        "peak_threshold_mw_latest": threshold_mw,
        "peak_definition": "Daily peak above the 90th percentile of daily peaks in the fold's training window",
        "season_definition": {
            "winter": [12, 1, 2],
            "summer": [3, 4, 5, 6],
            "monsoon": [7, 8, 9],
            "post_monsoon": [10, 11],
        },
        "peak_hours": constants.PEAK_HOURS,
        "models": constants.MODELS,
        "weather_proxy_note": "Backtests use observed weather plus horizon-scaled noise as a stand-in for archived weather forecasts.",
    }
    with open(target_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)


if __name__ == "__main__":
    generate_mock_artifacts()
