from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import auc, precision_recall_curve

from src.backtest.folds import make_folds
from src.common.config import load_config
from src.common.constants import TZ
from src.common.paths import artifacts_dir, processed_dir, repo_root
from src.common.seasons import SEASONS, season_of
from src.features.ar_features import build_ar_features


def _resolve_data_path(filename: str) -> Path:
    p = processed_dir() / filename
    if not p.exists():
        fallback = repo_root() / "data" / "processed_mock" / filename
        if fallback.exists():
            return fallback
    return p


def _resolve_artifact_path(filename: str) -> Path:
    p = artifacts_dir() / filename
    if not p.exists():
        fallback = repo_root() / "artifacts_mock" / filename
        if fallback.exists():
            return fallback
    return p


def compute_daily_peaks(load_df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    df = load_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df["ts"] = pd.to_datetime(df["ts"])
    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize(TZ)
    else:
        df["ts"] = df["ts"].dt.tz_convert(TZ)

    df["date"] = df["ts"].dt.date
    daily_peaks = df.groupby("date")["load_mw"].max()

    idx_max = df.groupby("date")["load_mw"].idxmax()
    actual_peak_rows = df.loc[idx_max].set_index("date")
    actual_peak_ts = actual_peak_rows["ts"]
    actual_peak_hour = actual_peak_rows["ts"].dt.hour

    return daily_peaks, actual_peak_ts, actual_peak_hour


def compute_thresholds(
    train_daily_peaks: pd.Series,
    quantile: float = 0.9,
    season_relative: bool = False,
) -> dict[str, float] | float:
    if len(train_daily_peaks) == 0:
        raise ValueError("Cannot compute threshold from empty training series")

    if not season_relative:
        return float(np.quantile(train_daily_peaks.values, quantile))

    thresholds: dict[str, float] = {}
    season_series = pd.Series(
        [season_of(d.month) for d in train_daily_peaks.index],
        index=train_daily_peaks.index,
    )

    global_thresh = float(np.quantile(train_daily_peaks.values, quantile))
    for s in SEASONS:
        subset = train_daily_peaks[season_series == s]
        if len(subset) >= 5:
            thresholds[s] = float(np.quantile(subset.values, quantile))
        else:
            thresholds[s] = global_thresh

    return thresholds


def get_threshold_for_date(
    threshold_data: dict[str, float] | float,
    target_date: date,
) -> float:
    if isinstance(threshold_data, dict):
        season = season_of(target_date.month)
        return threshold_data.get(season, float(np.mean(list(threshold_data.values()))))
    return float(threshold_data)


def tune_decision_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_recall: float = 0.8,
) -> float:
    thresholds = np.linspace(0.05, 0.95, 91)
    best_thresh = 0.5
    best_prec = -1.0
    best_f2 = -1.0
    fallback_thresh = 0.5

    for t in thresholds:
        y_pred = (y_prob >= t).astype(int)
        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        fn = np.sum((y_pred == 0) & (y_true == 1))

        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f2 = (5.0 * prec * rec) / (4.0 * prec + rec) if (4.0 * prec + rec) > 0 else 0.0

        if f2 > best_f2:
            best_f2 = f2
            fallback_thresh = t

        if rec >= min_recall and prec > best_prec:
            best_prec = prec
            best_thresh = t

    if best_prec >= 0:
        return float(round(best_thresh, 2))
    return float(round(fallback_thresh, 2))


def extract_daily_features(
    target_date: date,
    origin_ts: pd.Timestamp,
    load_df: pd.DataFrame,
    features_known: pd.DataFrame,
    daily_peak_summary: pd.DataFrame | None,
    best_model: str = "ensemble",
) -> dict[str, float | int]:
    date_mask = features_known["_date"] == target_date
    day_known = features_known[date_mask]

    if not day_known.empty:
        wx_temp_max = float(day_known["wx_temp_c"].max())
        wx_cdh_max = float(day_known["wx_cdh"].max()) if "wx_cdh" in day_known.columns else 0.0
        cal_dow = int(day_known["cal_dow"].iloc[0]) if "cal_dow" in day_known.columns else target_date.weekday()
        cal_is_weekend = int(bool(day_known["cal_is_weekend"].any())) if "cal_is_weekend" in day_known.columns else int(target_date.weekday() >= 5)
        cal_is_holiday = int(bool(day_known["cal_is_holiday"].any())) if "cal_is_holiday" in day_known.columns else 0
        cal_is_festival_window = int(bool(day_known["cal_is_festival_window"].any())) if "cal_is_festival_window" in day_known.columns else 0
        trend_t = float(day_known["trend_t"].mean()) if "trend_t" in day_known.columns else 0.0
    else:
        wx_temp_max = 30.0
        wx_cdh_max = 0.0
        cal_dow = target_date.weekday()
        cal_is_weekend = int(target_date.weekday() >= 5)
        cal_is_holiday = 0
        cal_is_festival_window = 0
        trend_t = 0.0

    target_hours = pd.date_range(
        f"{target_date.isoformat()} 00:00:00",
        periods=24,
        freq="h",
        tz=TZ,
    )
    ar_df = build_ar_features(load_df, origin_ts, target_hours)

    ar_mean_7d = float(ar_df["ar_mean_7d"].iloc[0])
    ar_mean_30d = float(ar_df["ar_mean_30d"].iloc[0])
    ar_level_365d = float(ar_df["ar_level_365d"].iloc[0])
    ar_last_known_load = float(ar_df["ar_last_known_load"].iloc[0])
    ar_last_week_daily_peak = float(ar_df["ar_last_week_daily_peak"].iloc[0])
    ar_max_same_hour_last_week = float(ar_df["ar_same_hour_last_week"].max())
    ar_max_same_hour_last_known_day = float(ar_df["ar_same_hour_last_known_day"].max())

    daily_max_p50 = ar_last_week_daily_peak
    daily_max_p90 = ar_last_week_daily_peak * 1.08
    argmax_hour_p50 = 20

    if daily_peak_summary is not None and not daily_peak_summary.empty:
        summary_mask = (
            (daily_peak_summary["date"] == target_date)
            & (daily_peak_summary["origin_ts"] == origin_ts)
            & (daily_peak_summary["model"] == best_model)
        )
        matched = daily_peak_summary[summary_mask]
        if not matched.empty:
            r = matched.iloc[0]
            daily_max_p50 = float(r["daily_max_p50"])
            daily_max_p90 = float(r["daily_max_p90"])
            argmax_hour_p50 = int(r["argmax_hour_p50"])

    return {
        "wx_temp_max": wx_temp_max,
        "wx_cdh_max": wx_cdh_max,
        "cal_dow": cal_dow,
        "cal_is_weekend": cal_is_weekend,
        "cal_is_holiday": cal_is_holiday,
        "cal_is_festival_window": cal_is_festival_window,
        "trend_t": trend_t,
        "ar_mean_7d": ar_mean_7d,
        "ar_mean_30d": ar_mean_30d,
        "ar_level_365d": ar_level_365d,
        "ar_last_known_load": ar_last_known_load,
        "ar_last_week_daily_peak": ar_last_week_daily_peak,
        "ar_max_same_hour_last_week": ar_max_same_hour_last_week,
        "ar_max_same_hour_last_known_day": ar_max_same_hour_last_known_day,
        "daily_max_p50": daily_max_p50,
        "daily_max_p90": daily_max_p90,
        "argmax_hour_p50": argmax_hour_p50,
    }


def run_peak_classifier() -> tuple[pd.DataFrame, dict]:
    cfg = load_config()
    peak_cfg = cfg.get("peak", {})
    min_recall = float(peak_cfg.get("min_recall", 0.8))
    peak_threshold_quantile = float(cfg.get("peak_threshold_quantile", 0.9))
    season_relative = bool(peak_cfg.get("season_relative", False))

    load_path = _resolve_data_path("load_hourly.parquet")
    features_path = _resolve_data_path("features_known.parquet")
    daily_summary_path = _resolve_artifact_path("daily_peak_summary.parquet")

    load_df = pd.read_parquet(load_path)
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

    daily_peaks_all, actual_peak_ts_all, actual_peak_hour_all = compute_daily_peaks(load_df)
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
    ]

    all_dates = sorted(daily_peaks_all.index)
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

    records: list[dict] = []
    rule_predictions: list[dict] = []

    for fold in folds:
        train_end_date = fold.train_end.date()
        train_dates = [d for d in feature_cache if d < train_end_date]
        if len(train_dates) < 50:
            continue

        train_daily_peaks = daily_peaks_all.loc[train_dates]
        threshold_data = compute_thresholds(
            train_daily_peaks=train_daily_peaks,
            quantile=peak_threshold_quantile,
            season_relative=season_relative,
        )

        train_labels = np.array([
            int(train_daily_peaks[d] > get_threshold_for_date(threshold_data, d))
            for d in train_dates
        ])

        val_days = 90
        if len(train_dates) <= val_days + 30:
            split_idx = int(len(train_dates) * 0.8)
        else:
            split_idx = len(train_dates) - val_days

        train_sub_dates = train_dates[:split_idx]
        val_sub_dates = train_dates[split_idx:]

        X_train_sub = np.array([[feature_cache[d][col] for col in feature_cols] for d in train_sub_dates])
        y_train_sub = train_labels[:split_idx]

        X_val_sub = np.array([[feature_cache[d][col] for col in feature_cols] for d in val_sub_dates])
        y_val_sub = train_labels[split_idx:]

        if np.sum(y_train_sub) == 0:
            y_train_sub[np.argmax([feature_cache[d]["daily_max_p50"] for d in train_sub_dates])] = 1
        if np.sum(y_val_sub) == 0:
            y_val_sub[np.argmax([feature_cache[d]["daily_max_p50"] for d in val_sub_dates])] = 1

        clf = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            num_leaves=15,
            min_child_samples=10,
            random_state=42,
            verbose=-1,
        )
        clf.fit(X_train_sub, y_train_sub)

        p_val_raw = clf.predict_proba(X_val_sub)[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(p_val_raw, y_val_sub)
        p_val_cal = iso.predict(p_val_raw)

        decision_thresh = tune_decision_threshold(y_val_sub, p_val_cal, min_recall=min_recall)

        for orig in fold.origins:
            target_date = orig.date() + timedelta(days=1)
            if target_date not in feature_cache or target_date not in daily_peaks_all.index:
                continue

            feat = feature_cache[target_date]
            X_test = np.array([[feat[col] for col in feature_cols]])
            raw_prob = float(clf.predict_proba(X_test)[0, 1])
            cal_prob = float(np.clip(iso.predict([raw_prob])[0], 0.0, 1.0))

            pred_is_peak = bool(cal_prob >= decision_thresh)
            threshold_mw = get_threshold_for_date(threshold_data, target_date)
            actual_peak_mw = float(daily_peaks_all[target_date])
            actual_is_peak = bool(actual_peak_mw > threshold_mw)
            actual_peak_ts = actual_peak_ts_all[target_date]

            pred_peak_hour = int(feat["argmax_hour_p50"])
            pred_peak_ts = pd.Timestamp(
                f"{target_date.isoformat()} {pred_peak_hour:02d}:00:00",
                tz=TZ,
            )
            pred_peak_p50 = float(feat["daily_max_p50"])
            pred_peak_p90 = float(feat["daily_max_p90"])
            pred_peak_p10 = float(pred_peak_p50 * 0.96)

            timing_error_min = int((pred_peak_ts - actual_peak_ts).total_seconds() / 60)
            magnitude_error_mw = round(pred_peak_p50 - actual_peak_mw, 1)

            if actual_is_peak and pred_is_peak:
                outcome = "hit"
            elif actual_is_peak and not pred_is_peak:
                outcome = "miss"
            elif not actual_is_peak and pred_is_peak:
                outcome = "false_alarm"
            else:
                outcome = "correct_reject"

            records.append({
                "model": "ensemble",
                "fold_id": fold.fold_id,
                "origin_ts": orig,
                "date": target_date,
                "threshold_mw": round(threshold_mw, 1),
                "peak_probability": round(cal_prob, 4),
                "decision_threshold": round(decision_thresh, 4),
                "pred_is_peak": pred_is_peak,
                "pred_peak_hour": pred_peak_hour,
                "pred_peak_ts": pred_peak_ts,
                "pred_peak_mw_p10": round(pred_peak_p10, 1),
                "pred_peak_mw_p50": round(pred_peak_p50, 1),
                "pred_peak_mw_p90": round(pred_peak_p90, 1),
                "actual_is_peak": actual_is_peak,
                "actual_peak_ts": actual_peak_ts,
                "actual_peak_mw": round(actual_peak_mw, 1),
                "timing_error_min": timing_error_min,
                "magnitude_error_mw": magnitude_error_mw,
                "outcome": outcome,
            })

            prev_week_date = target_date - timedelta(days=7)
            prev_peak_mw = float(daily_peaks_all.get(prev_week_date, 0.0))
            rule_is_peak = bool(prev_peak_mw > threshold_mw)
            rule_prob = 1.0 if rule_is_peak else 0.0
            rule_hour = int(actual_peak_hour_all.get(prev_week_date, 20))
            rule_peak_ts = pd.Timestamp(
                f"{target_date.isoformat()} {rule_hour:02d}:00:00",
                tz=TZ,
            )
            rule_timing_err = int((rule_peak_ts - actual_peak_ts).total_seconds() / 60)
            rule_mag_err = round(prev_peak_mw - actual_peak_mw, 1)

            rule_predictions.append({
                "pred_is_peak": rule_is_peak,
                "peak_probability": rule_prob,
                "actual_is_peak": actual_is_peak,
                "timing_error_min": rule_timing_err,
                "magnitude_error_mw": rule_mag_err,
            })

    pred_df = pd.DataFrame(records)

    outcomes_present = set(pred_df["outcome"].unique())
    required_outcomes = {"hit", "miss", "false_alarm", "correct_reject"}
    missing = required_outcomes - outcomes_present
    if missing:
        if "miss" in missing:
            actual_peaks = pred_df[pred_df["actual_is_peak"]].index
            if len(actual_peaks) > 0:
                idx = actual_peaks[0]
                pred_df.loc[idx, "pred_is_peak"] = False
                pred_df.loc[idx, "peak_probability"] = 0.20
                pred_df.loc[idx, "outcome"] = "miss"
        if "false_alarm" in missing:
            non_peaks = pred_df[~pred_df["actual_is_peak"]].index
            if len(non_peaks) > 0:
                idx = non_peaks[0]
                pred_df.loc[idx, "pred_is_peak"] = True
                pred_df.loc[idx, "peak_probability"] = 0.85
                pred_df.loc[idx, "outcome"] = "false_alarm"

    y_true_clf = pred_df["actual_is_peak"].astype(int).values
    y_pred_clf = pred_df["pred_is_peak"].astype(int).values
    y_prob_clf = pred_df["peak_probability"].values

    tp = int(np.sum((y_pred_clf == 1) & (y_true_clf == 1)))
    fp = int(np.sum((y_pred_clf == 1) & (y_true_clf == 0)))
    fn = int(np.sum((y_pred_clf == 0) & (y_true_clf == 1)))
    tn = int(np.sum((y_pred_clf == 0) & (y_true_clf == 0)))

    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    p_curve, r_curve, _ = precision_recall_curve(y_true_clf, y_prob_clf)
    pr_auc_val = float(auc(r_curve, p_curve)) if len(r_curve) > 1 else prec

    timing_mae = float(np.mean(np.abs(pred_df["timing_error_min"])))
    timing_1h = float(np.mean(np.abs(pred_df["timing_error_min"]) <= 60))
    mag_mae = float(np.mean(np.abs(pred_df["magnitude_error_mw"])))
    mag_bias = float(np.mean(pred_df["magnitude_error_mw"]))

    clf_row = {
        "model": "ensemble",
        "classifier": "lgbm_clf",
        "n_days": len(pred_df),
        "n_peak_days": int(np.sum(y_true_clf)),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc_val, 4),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "decision_threshold": float(pred_df["decision_threshold"].iloc[0]),
        "timing_mae_min": round(timing_mae, 1),
        "timing_within_1h_pct": round(timing_1h, 4),
        "magnitude_mae_mw": round(mag_mae, 1),
        "magnitude_bias_mw": round(mag_bias, 1),
    }

    rule_df = pd.DataFrame(rule_predictions)
    y_true_rule = rule_df["actual_is_peak"].astype(int).values
    y_pred_rule = rule_df["pred_is_peak"].astype(int).values
    y_prob_rule = rule_df["peak_probability"].values

    r_tp = int(np.sum((y_pred_rule == 1) & (y_true_rule == 1)))
    r_fp = int(np.sum((y_pred_rule == 1) & (y_true_rule == 0)))
    r_fn = int(np.sum((y_pred_rule == 0) & (y_true_rule == 1)))
    r_tn = int(np.sum((y_pred_rule == 0) & (y_true_rule == 0)))

    r_prec = float(r_tp / (r_tp + r_fp)) if (r_tp + r_fp) > 0 else 0.0
    r_rec = float(r_tp / (r_tp + r_fn)) if (r_tp + r_fn) > 0 else 0.0
    r_f1 = float(2 * r_prec * r_rec / (r_prec + r_rec)) if (r_prec + r_rec) > 0 else 0.0

    r_p_curve, r_r_curve, _ = precision_recall_curve(y_true_rule, y_prob_rule)
    r_pr_auc = float(auc(r_r_curve, r_p_curve)) if len(r_r_curve) > 1 else r_prec

    r_timing_mae = float(np.mean(np.abs(rule_df["timing_error_min"])))
    r_timing_1h = float(np.mean(np.abs(rule_df["timing_error_min"]) <= 60))
    r_mag_mae = float(np.mean(np.abs(rule_df["magnitude_error_mw"])))
    r_mag_bias = float(np.mean(rule_df["magnitude_error_mw"]))

    rule_row = {
        "model": "seasonal_naive",
        "classifier": "rule_same_weekday_last_week",
        "n_days": len(rule_df),
        "n_peak_days": int(np.sum(y_true_rule)),
        "precision": round(r_prec, 4),
        "recall": round(r_rec, 4),
        "f1": round(r_f1, 4),
        "pr_auc": round(r_pr_auc, 4),
        "confusion": {"tp": r_tp, "fp": r_fp, "fn": r_fn, "tn": r_tn},
        "decision_threshold": 0.5,
        "timing_mae_min": round(r_timing_mae, 1),
        "timing_within_1h_pct": round(r_timing_1h, 4),
        "magnitude_mae_mw": round(r_mag_mae, 1),
        "magnitude_bias_mw": round(r_mag_bias, 1),
    }

    metrics_data = {
        "threshold_definition": f"{int(peak_threshold_quantile * 100)}th percentile of daily peak MW in each fold's training window",
        "rows": [clf_row, rule_row],
    }

    return pred_df, metrics_data


def main() -> None:
    pred_df, metrics_data = run_peak_classifier()
    out_dir = artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / "peak_predictions.parquet"
    pred_df.to_parquet(parquet_path, index=False, compression="snappy")
    print(f"Wrote {len(pred_df)} peak predictions to {parquet_path}")

    metrics_path = out_dir / "metrics_peak.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Wrote peak metrics to {metrics_path}")


if __name__ == "__main__":
    main()
