import json
from datetime import datetime
import numpy as np
import pandas as pd
import pytest
from src.common import constants, paths, seasons


def test_processed_mock_load_hourly():
    path = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
    assert path.exists()

    df = pd.read_parquet(path)
    expected_cols = [
        "ts",
        "load_mw",
        "is_imputed",
        "imputation_method",
        "is_outage_suspect",
    ]
    assert list(df.columns) == expected_cols

    assert df["ts"].dt.tz is not None
    assert str(df["ts"].dt.tz) == constants.TZ
    assert df["ts"].is_monotonic_increasing
    assert df["ts"].nunique() == len(df)

    diffs = df["ts"].diff().dropna()
    assert (diffs == pd.Timedelta(hours=1)).all()

    assert df["load_mw"].dtype in (np.float64, np.float32)
    assert df["is_imputed"].dtype == bool
    assert df["is_outage_suspect"].dtype == bool

    valid_imputations = {"linear", "hour_of_week"}
    for val in df["imputation_method"].dropna().unique():
        assert val in valid_imputations


def test_processed_mock_features_known():
    path = paths.repo_root() / "data" / "processed_mock" / "features_known.parquet"
    assert path.exists()

    df = pd.read_parquet(path)
    expected_cols = [
        "ts",
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
        "cal_holiday_name",
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
        "wx_is_noisy",
    ]
    assert list(df.columns) == expected_cols

    assert df["ts"].dt.tz is not None
    assert str(df["ts"].dt.tz) == constants.TZ
    assert df["ts"].is_monotonic_increasing

    assert (df["cal_days_to_diwali"] >= -30.0).all()
    assert (df["cal_days_to_diwali"] <= 30.0).all()
    assert set(df["evt_lockdown"].unique()).issubset({0, 1})
    assert set(df["evt_odd_even"].unique()).issubset({0, 1})


def test_predictions_backtest_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "predictions_backtest.parquet"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"predictions_backtest.parquet not yet present in {art_dir}")
            pytest.fail("predictions_backtest.parquet missing in artifacts_mock")

        df = pd.read_parquet(file_path)
        expected_cols = [
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
        ]
        assert list(df.columns) == expected_cols

        assert df["origin_ts"].dt.tz is not None
        assert str(df["origin_ts"].dt.tz) == constants.TZ
        assert df["target_ts"].dt.tz is not None
        assert str(df["target_ts"].dt.tz) == constants.TZ

        assert set(df["model"].unique()).issubset(set(constants.MODELS))

        assert (df["p05"] <= df["p10"]).all()
        assert (df["p10"] <= df["p50"]).all()
        assert (df["p50"] <= df["p90"]).all()
        assert (df["p90"] <= df["p95"]).all()

        assert (df["p05_raw"] <= df["p10_raw"]).all()
        assert (df["p10_raw"] <= df["p50_raw"]).all()
        assert (df["p50_raw"] <= df["p90_raw"]).all()
        assert (df["p90_raw"] <= df["p95_raw"]).all()

        assert df["horizon_h"].min() >= 14
        assert df["horizon_h"].max() <= 181
        assert set(df["horizon_day"].unique()) == set(constants.HORIZON_DAYS)


def test_peak_predictions_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "peak_predictions.parquet"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"peak_predictions.parquet not yet present in {art_dir}")
            pytest.fail("peak_predictions.parquet missing in artifacts_mock")

        df = pd.read_parquet(file_path)
        expected_cols = [
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
        ]
        assert list(df.columns) == expected_cols

        assert df["origin_ts"].dt.tz is not None
        assert str(df["origin_ts"].dt.tz) == constants.TZ
        assert df["pred_peak_ts"].dt.tz is not None
        assert str(df["pred_peak_ts"].dt.tz) == constants.TZ

        assert (df["pred_peak_mw_p10"] <= df["pred_peak_mw_p50"]).all()
        assert (df["pred_peak_mw_p50"] <= df["pred_peak_mw_p90"]).all()

        assert (df["peak_probability"] >= 0.0).all()
        assert (df["peak_probability"] <= 1.0).all()
        assert (df["pred_peak_hour"] >= 0).all()
        assert (df["pred_peak_hour"] <= 23).all()

        observed_outcomes = set(df["outcome"].dropna().unique())
        valid_outcomes = {"hit", "miss", "false_alarm", "correct_reject"}
        assert observed_outcomes.issubset(valid_outcomes)
        assert valid_outcomes.issubset(observed_outcomes)


def test_metrics_accuracy_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "metrics_accuracy.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"metrics_accuracy.json not yet present in {art_dir}")
            pytest.fail("metrics_accuracy.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "generated_at" in data
        assert "rows" in data
        assert len(data["rows"]) > 0

        valid_segments = {"all", "winter", "summer", "monsoon", "post_monsoon", "peak_hours", "off_peak"}
        valid_horizons = {1, 2, 3, 4, 5, 6, 7, "all"}

        for row in data["rows"]:
            assert row["model"] in constants.MODELS
            assert row["horizon_day"] in valid_horizons
            assert row["segment"] in valid_segments
            assert row["n"] > 0
            assert row["mape"] >= 0.0
            assert row["rmse_mw"] >= 0.0
            assert row["mae_mw"] >= 0.0
            assert 0.0 <= row["picp_80"] <= 1.0
            assert 0.0 <= row["picp_90"] <= 1.0
            assert row["mpiw_80_mw"] >= 0.0

            if row["model"] == constants.BASELINE_MODEL:
                assert row["improvement_mape_pct"] is None
                assert row["improvement_rmse_pct"] is None


def test_metrics_peak_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "metrics_peak.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"metrics_peak.json not yet present in {art_dir}")
            pytest.fail("metrics_peak.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "threshold_definition" in data
        assert "rows" in data
        assert len(data["rows"]) >= 2

        models = [r["model"] for r in data["rows"]]
        assert "ensemble" in models

        for row in data["rows"]:
            assert "classifier" in row
            assert "n_days" in row
            assert "n_peak_days" in row
            assert 0.0 <= row["precision"] <= 1.0
            assert 0.0 <= row["recall"] <= 1.0
            assert 0.0 <= row["f1"] <= 1.0
            assert "confusion" in row
            conf = row["confusion"]
            assert set(conf.keys()) == {"tp", "fp", "fn", "tn"}


def test_error_heatmap_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "error_heatmap.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"error_heatmap.json not yet present in {art_dir}")
            pytest.fail("error_heatmap.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "cells" in data
        cells = data["cells"]
        assert len(cells) >= 6

        models = {c["model"] for c in cells}
        assert "ensemble" in models
        assert "seasonal_naive" in models

        for cell in cells:
            assert cell["metric"] in {"mape", "rmse", "bias"}
            assert cell["horizon_day"] in {1, "all"}
            assert cell["hours"] == list(range(24))
            assert cell["seasons"] == list(seasons.SEASONS)
            assert len(cell["values"]) == 4
            assert len(cell["counts"]) == 4
            for s_idx in range(4):
                assert len(cell["values"][s_idx]) == 24
                assert len(cell["counts"][s_idx]) == 24


def test_missed_peaks_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "missed_peaks.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"missed_peaks.json not yet present in {art_dir}")
            pytest.fail("missed_peaks.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "items" in data
        items = data["items"]
        assert len(items) >= 8

        valid_tags = {"festival", "holiday", "heatwave", "weather_miss", "weekend", "other"}
        prev_err = float("inf")

        for item in items:
            assert item["model"] in constants.MODELS
            assert item["season"] in seasons.SEASONS
            assert 0.0 <= item["peak_probability"] <= 1.0
            assert set(item["tags"]).issubset(valid_tags)
            curr_err = abs(item["magnitude_error_mw"])
            assert curr_err <= prev_err
            prev_err = curr_err


def test_feature_importance_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "feature_importance.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"feature_importance.json not yet present in {art_dir}")
            pytest.fail("feature_importance.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "models" in data
        assert "lgbm" in data["models"]
        assert "xgboost" in data["models"]

        valid_groups = {
            "calendar",
            "festival",
            "event",
            "weather",
            "thermal_inertia",
            "trend",
            "autoregressive",
            "horizon",
        }

        for model_name in ["lgbm", "xgboost"]:
            features = data["models"][model_name]
            assert len(features) > 0
            total_imp = sum(f["importance"] for f in features)
            assert pytest.approx(total_imp, rel=1e-2) == 1.0
            for f in features:
                assert f["group"] in valid_groups


def test_procurement_defaults_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "procurement_defaults.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"procurement_defaults.json not yet present in {art_dir}")
            pytest.fail("procurement_defaults.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "tariff" in data
        assert data["tariff"]["da_price_inr_per_mwh"] == 5000
        assert data["tariff"]["under_price_inr_per_mwh"] == 12000
        assert data["tariff"]["resale_price_inr_per_mwh"] == 2500
        assert "disclaimer" in data
        assert data["default_risk_quantile"] == 0.9


def test_meta_schema(artifact_dirs):
    for art_dir in artifact_dirs:
        file_path = art_dir / "meta.json"
        if not file_path.exists():
            if art_dir.name != "artifacts_mock":
                pytest.skip(f"meta.json not yet present in {art_dir}")
            pytest.fail("meta.json missing in artifacts_mock")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["version"] == "1.0.0"
        assert data["timezone"] == constants.TZ
        assert data["quantiles"] == constants.QUANTILES
        assert data["models"] == constants.MODELS
        assert data["peak_hours"] == constants.PEAK_HOURS
        assert "data_range" in data
        assert "backtest_range" in data
        assert "peak_threshold_mw_latest" in data
        assert "weather_proxy_note" in data
