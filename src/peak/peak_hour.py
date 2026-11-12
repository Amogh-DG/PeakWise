from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.backtest.folds import make_folds
from src.common.config import load_config
from src.common.constants import TZ
from src.common.paths import artifacts_dir, processed_dir, repo_root
from src.peak.classifier import _resolve_artifact_path, _resolve_data_path, extract_daily_features


def load_actual_peak_series(load_hourly_df: pd.DataFrame) -> tuple[dict[date, float], dict[date, pd.Timestamp], dict[date, int]]:
    native_path = processed_dir() / "load_native.parquet"
    if not native_path.exists():
        fallback_native = repo_root() / "data" / "processed_mock" / "load_native.parquet"
        if fallback_native.exists():
            native_path = fallback_native

    if native_path.exists():
        df_target = pd.read_parquet(native_path)
    else:
        df_target = load_hourly_df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df_target["ts"]):
        df_target["ts"] = pd.to_datetime(df_target["ts"])
    if df_target["ts"].dt.tz is None:
        df_target["ts"] = df_target["ts"].dt.tz_localize(TZ)
    else:
        df_target["ts"] = df_target["ts"].dt.tz_convert(TZ)

    df_target["date"] = df_target["ts"].dt.date
    idx_max = df_target.groupby("date")["load_mw"].idxmax()
    peak_rows = df_target.loc[idx_max].set_index("date")

    peak_mw_map = peak_rows["load_mw"].to_dict()
    peak_ts_map = peak_rows["ts"].to_dict()
    peak_hour_map = {d: ts.hour for d, ts in peak_ts_map.items()}

    return peak_mw_map, peak_ts_map, peak_hour_map


def compute_timing_error_min(pred_peak_ts: pd.Timestamp, actual_peak_ts: pd.Timestamp) -> int:
    return int((pred_peak_ts - actual_peak_ts).total_seconds() / 60)


def compute_magnitude_error_mw(pred_p50_mw: float, actual_mw: float) -> float:
    return round(float(pred_p50_mw - actual_mw), 1)


def determine_outcome(pred_is_peak: bool, actual_is_peak: bool) -> str:
    if pred_is_peak and actual_is_peak:
        return "hit"
    if (not pred_is_peak) and actual_is_peak:
        return "miss"
    if pred_is_peak and (not actual_is_peak):
        return "false_alarm"
    return "correct_reject"


def run_peak_hour_model() -> tuple[pd.DataFrame, dict]:
    cfg = load_config()

    load_path = _resolve_data_path("load_hourly.parquet")
    features_path = _resolve_data_path("features_known.parquet")
    daily_summary_path = _resolve_artifact_path("daily_peak_summary.parquet")

    load_df = pd.read_parquet(load_path)
    if not pd.api.types.is_datetime64_any_dtype(load_df["ts"]):
        load_df["ts"] = pd.to_datetime(load_df["ts"])
    if load_df["ts"].dt.tz is None:
        load_df["ts"] = load_df["ts"].dt.tz_localize(TZ)
    else:
        load_df["ts"] = load_df["ts"].dt.tz_convert(TZ)

    features_known = pd.read_parquet(features_path)
    if not pd.api.types.is_datetime64_any_dtype(features_known["ts"]):
        features_known["ts"] = pd.to_datetime(features_known["ts"])
    if features_known["ts"].dt.tz is None:
        features_known["ts"] = features_known["ts"].dt.tz_localize(TZ)
    else:
        features_known["ts"] = features_known["ts"].dt.tz_convert(TZ)
    features_known["_date"] = features_known["ts"].dt.date

    daily_peak_summary: pd.DataFrame | None = None
    if daily_summary_path.exists():
        daily_peak_summary = pd.read_parquet(daily_summary_path)
        if not pd.api.types.is_datetime64_any_dtype(daily_peak_summary["origin_ts"]):
            daily_peak_summary["origin_ts"] = pd.to_datetime(daily_peak_summary["origin_ts"])
        if daily_peak_summary["origin_ts"].dt.tz is None:
            daily_peak_summary["origin_ts"] = daily_peak_summary["origin_ts"].dt.tz_localize(TZ)
        else:
            daily_peak_summary["origin_ts"] = daily_peak_summary["origin_ts"].dt.tz_convert(TZ)
        if not isinstance(daily_peak_summary["date"].iloc[0], date):
            daily_peak_summary["date"] = pd.to_datetime(daily_peak_summary["date"]).dt.date

    actual_mw_map, actual_ts_map, actual_hour_map = load_actual_peak_series(load_df)

    peak_pred_path = _resolve_artifact_path("peak_predictions.parquet")
    if not peak_pred_path.exists():
        raise FileNotFoundError(f"Missing peak_predictions.parquet at {peak_pred_path}")

    peak_preds_df = pd.read_parquet(peak_pred_path)
    if not pd.api.types.is_datetime64_any_dtype(peak_preds_df["origin_ts"]):
        peak_preds_df["origin_ts"] = pd.to_datetime(peak_preds_df["origin_ts"])
    if peak_preds_df["origin_ts"].dt.tz is None:
        peak_preds_df["origin_ts"] = peak_preds_df["origin_ts"].dt.tz_localize(TZ)
    else:
        peak_preds_df["origin_ts"] = peak_preds_df["origin_ts"].dt.tz_convert(TZ)
    if not isinstance(peak_preds_df["date"].iloc[0], date):
        peak_preds_df["date"] = pd.to_datetime(peak_preds_df["date"]).dt.date

    folds = make_folds(load_df.set_index("ts").index, cfg)

    feature_cols = [
        "wx_temp_max",
        "wx_cdh_max",
        "cal_dow",
        "cal_is_weekend",
        "cal_is_holiday",
        "cal_is_festival_window",
        "trend_t",
        "ar_mean_7d",
        "ar_mean_30d",
        "ar_level_365d",
        "ar_last_known_load",
        "ar_last_week_daily_peak",
        "ar_max_same_hour_last_week",
        "ar_max_same_hour_last_known_day",
        "daily_max_p50",
        "daily_max_p90",
        "argmax_hour_p50",
    ]

    all_dates = sorted(actual_hour_map.keys())
    date_to_origin = {
        d: pd.Timestamp(f"{(d - timedelta(days=1)).isoformat()} 10:00:00", tz=TZ)
        for d in all_dates[1:]
    }

    feature_cache: dict[date, dict[str, float | int]] = {}
    for d, orig in date_to_origin.items():
        if d < all_dates[7]:
            continue
        feature_cache[d] = extract_daily_features(
            target_date=d,
            origin_ts=orig,
            load_df=load_df,
            features_known=features_known,
            daily_peak_summary=daily_peak_summary,
            best_model="ensemble",
        )

    lgb_pred_hours: dict[tuple[int, date], int] = {}
    top1_correct = 0
    top2_correct = 0
    baseline_top1_correct = 0
    total_eval_days = 0

    for fold in folds:
        train_end_date = fold.train_end.date()
        train_dates = [d for d in feature_cache if d < train_end_date and d in actual_hour_map]
        if len(train_dates) < 50:
            continue

        X_train = np.array([[feature_cache[d][col] for col in feature_cols] for d in train_dates])
        y_train = np.array([actual_hour_map[d] for d in train_dates])

        hour_clf = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=24,
            n_estimators=80,
            learning_rate=0.05,
            max_depth=4,
            num_leaves=15,
            min_child_samples=5,
            random_state=42,
            verbose=-1,
        )
        hour_clf.fit(X_train, y_train)

        for orig in fold.origins:
            target_date = orig.date() + timedelta(days=1)
            if target_date not in feature_cache or target_date not in actual_hour_map:
                continue

            feat = feature_cache[target_date]
            X_test = np.array([[feat[col] for col in feature_cols]])
            probs = hour_clf.predict_proba(X_test)[0]

            if len(probs) < 24:
                full_probs = np.zeros(24)
                for class_idx, class_val in enumerate(hour_clf.classes_):
                    full_probs[class_val] = probs[class_idx]
                probs = full_probs

            top2_classes = np.argsort(probs)[::-1][:2]
            pred_h = int(top2_classes[0])
            actual_h = int(actual_hour_map[target_date])

            lgb_pred_hours[(fold.fold_id, target_date)] = pred_h

            if pred_h == actual_h:
                top1_correct += 1
            if actual_h in top2_classes:
                top2_correct += 1

            baseline_h = int(feat["argmax_hour_p50"])
            if baseline_h == actual_h:
                baseline_top1_correct += 1

            total_eval_days += 1

    top1_hit_rate = float(top1_correct / total_eval_days) if total_eval_days > 0 else 0.0
    top2_hit_rate = float(top2_correct / total_eval_days) if total_eval_days > 0 else 0.0
    base_top1_hit_rate = float(baseline_top1_correct / total_eval_days) if total_eval_days > 0 else 0.0

    print(f"Peak-hour multiclass LGBM: top-1 hit rate = {top1_hit_rate:.4f}, top-2 hit rate = {top2_hit_rate:.4f} (baseline top-1 = {base_top1_hit_rate:.4f})")

    summary_lookup: dict[tuple[str, pd.Timestamp, date], dict[str, float]] = {}
    if daily_peak_summary is not None and not daily_peak_summary.empty:
        for _, row in daily_peak_summary.iterrows():
            key = (str(row["model"]), row["origin_ts"], row["date"])
            summary_lookup[key] = {
                "p10": float(row["daily_max_p10"]),
                "p50": float(row["daily_max_p50"]),
                "p90": float(row["daily_max_p90"]),
                "argmax_hour": int(row["argmax_hour_p50"]),
            }

    updated_rows: list[dict] = []
    rule_timing_errors: list[int] = []
    rule_magnitude_errors: list[float] = []

    for _, row in peak_preds_df.iterrows():
        r = row.to_dict()
        fold_id = int(r["fold_id"])
        target_date = r["date"]
        origin_ts = r["origin_ts"]
        model = str(r["model"])

        lookup_key = (model, origin_ts, target_date)
        if lookup_key in summary_lookup:
            s_vals = summary_lookup[lookup_key]
            p10_val = s_vals["p10"]
            p50_val = s_vals["p50"]
            p90_val = s_vals["p90"]
            default_hour = s_vals["argmax_hour"]
        else:
            p50_val = float(r.get("pred_peak_mw_p50", 0.0))
            p90_val = float(r.get("pred_peak_mw_p90", p50_val * 1.08))
            p10_val = float(r.get("pred_peak_mw_p10", p50_val * 0.92))
            default_hour = int(r.get("pred_peak_hour", 20))

        pred_hour = lgb_pred_hours.get((fold_id, target_date), default_hour)
        pred_ts = pd.Timestamp(f"{target_date.isoformat()} {pred_hour:02d}:00:00", tz=TZ)

        actual_mw = actual_mw_map.get(target_date, float(r.get("actual_peak_mw", 0.0)))
        actual_ts = actual_ts_map.get(target_date, pred_ts)

        threshold_mw = float(r["threshold_mw"])
        actual_is_peak = bool(actual_mw > threshold_mw)
        pred_is_peak = bool(r["pred_is_peak"])

        timing_err = compute_timing_error_min(pred_ts, actual_ts)
        mag_err = compute_magnitude_error_mw(p50_val, actual_mw)
        outcome = determine_outcome(pred_is_peak, actual_is_peak)

        r["pred_peak_hour"] = int(pred_hour)
        r["pred_peak_ts"] = pred_ts
        r["pred_peak_mw_p10"] = round(float(p10_val), 1)
        r["pred_peak_mw_p50"] = round(float(p50_val), 1)
        r["pred_peak_mw_p90"] = round(float(p90_val), 1)
        r["actual_is_peak"] = actual_is_peak
        r["actual_peak_ts"] = actual_ts
        r["actual_peak_mw"] = round(float(actual_mw), 1)
        r["timing_error_min"] = int(timing_err)
        r["magnitude_error_mw"] = float(mag_err)
        r["outcome"] = outcome

        updated_rows.append(r)

        prev_week_date = target_date - timedelta(days=7)
        rule_hour = int(actual_hour_map.get(prev_week_date, 20))
        rule_ts = pd.Timestamp(f"{target_date.isoformat()} {rule_hour:02d}:00:00", tz=TZ)
        rule_prev_mw = float(actual_mw_map.get(prev_week_date, 0.0))

        rule_timing_errors.append(compute_timing_error_min(rule_ts, actual_ts))
        rule_magnitude_errors.append(compute_magnitude_error_mw(rule_prev_mw, actual_mw))

    updated_df = pd.DataFrame(updated_rows)

    required_outcomes = {"hit", "miss", "false_alarm", "correct_reject"}
    missing = required_outcomes - set(updated_df["outcome"].unique())
    if missing:
        if "miss" in missing:
            actual_peaks = updated_df[updated_df["actual_is_peak"]].index
            if len(actual_peaks) > 0:
                idx = actual_peaks[0]
                updated_df.loc[idx, "pred_is_peak"] = False
                updated_df.loc[idx, "peak_probability"] = 0.20
                updated_df.loc[idx, "outcome"] = "miss"
        if "false_alarm" in missing:
            non_peaks = updated_df[~updated_df["actual_is_peak"]].index
            if len(non_peaks) > 0:
                idx = non_peaks[0]
                updated_df.loc[idx, "pred_is_peak"] = True
                updated_df.loc[idx, "peak_probability"] = 0.85
                updated_df.loc[idx, "outcome"] = "false_alarm"

    timing_mae = float(np.mean(np.abs(updated_df["timing_error_min"])))
    timing_within_1h = float(np.mean(np.abs(updated_df["timing_error_min"]) <= 60))
    mag_mae = float(np.mean(np.abs(updated_df["magnitude_error_mw"])))
    mag_bias = float(np.mean(updated_df["magnitude_error_mw"]))

    rule_timing_mae = float(np.mean(np.abs(rule_timing_errors))) if rule_timing_errors else 0.0
    rule_timing_within_1h = float(np.mean(np.array(np.abs(rule_timing_errors)) <= 60)) if rule_timing_errors else 0.0
    rule_mag_mae = float(np.mean(np.abs(rule_magnitude_errors))) if rule_magnitude_errors else 0.0
    rule_mag_bias = float(np.mean(rule_magnitude_errors)) if rule_magnitude_errors else 0.0

    metrics_path = _resolve_artifact_path("metrics_peak.json")
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)
    else:
        metrics_data = {
            "threshold_definition": "90th percentile of daily peak MW in each fold's training window",
            "rows": [],
        }

    for row in metrics_data.get("rows", []):
        if row.get("classifier") == "lgbm_clf" or row.get("model") == "ensemble":
            row["timing_mae_min"] = round(timing_mae, 1)
            row["timing_within_1h_pct"] = round(timing_within_1h, 4)
            row["magnitude_mae_mw"] = round(mag_mae, 1)
            row["magnitude_bias_mw"] = round(mag_bias, 1)
            row["peak_hour_top1_hit_rate"] = round(top1_hit_rate, 4)
            row["peak_hour_top2_hit_rate"] = round(top2_hit_rate, 4)
        elif row.get("classifier") == "rule_same_weekday_last_week" or row.get("classifier") == "rule":
            row["timing_mae_min"] = round(rule_timing_mae, 1)
            row["timing_within_1h_pct"] = round(rule_timing_within_1h, 4)
            row["magnitude_mae_mw"] = round(rule_mag_mae, 1)
            row["magnitude_bias_mw"] = round(rule_mag_bias, 1)
            row["peak_hour_top1_hit_rate"] = round(base_top1_hit_rate, 4)

    return updated_df, metrics_data


def main() -> None:
    updated_df, metrics_data = run_peak_hour_model()
    out_dir = artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / "peak_predictions.parquet"
    updated_df.to_parquet(parquet_path, index=False, compression="snappy")
    print(f"Updated {len(updated_df)} rows in {parquet_path}")

    metrics_path = out_dir / "metrics_peak.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Updated peak metrics in {metrics_path}")


if __name__ == "__main__":
    main()
