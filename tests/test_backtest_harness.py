import numpy as np
import pandas as pd
import pytest
from src.backtest.folds import Fold, make_folds
from src.backtest.persistence import get_load_path
from src.backtest.registry import REGISTRY, get_forecaster, register
from src.backtest.runner import run_backtest
from src.common import config, constants, paths


def test_make_folds_structure():
    cfg = config.load_config()
    load_path = get_load_path()
    assert load_path.exists()
    load_df = pd.read_parquet(load_path)
    index = pd.DatetimeIndex(load_df["ts"])

    folds = make_folds(index, cfg)
    assert len(folds) > 0

    prev_end = None
    for i, fold in enumerate(folds):
        assert isinstance(fold, Fold)
        assert fold.fold_id == i
        assert isinstance(fold.train_end, pd.Timestamp)
        assert len(fold.origins) > 0
        assert fold.train_end <= fold.origins[0]

        for orig in fold.origins:
            assert orig.hour == cfg.get("origin_hour_local", 10)
            assert str(orig.tz) == constants.TZ

        if prev_end is not None:
            assert fold.train_end > prev_end
        prev_end = fold.train_end


def test_no_training_row_at_or_after_train_end(tmp_path, monkeypatch):
    cfg = config.load_config()
    load_path = get_load_path()
    load_df = pd.read_parquet(load_path)

    train_end = pd.Timestamp("2024-01-01 10:00:00", tz=constants.TZ)

    fake_load = load_df.copy()
    future_mask = fake_load["ts"] >= train_end
    fake_load.loc[future_mask, "load_mw"] = 999999.0

    mock_dir = tmp_path / "mock_proc"
    mock_dir.mkdir(parents=True, exist_ok=True)
    fake_load.to_parquet(mock_dir / "load_hourly.parquet", index=False)

    monkeypatch.setattr(paths, "processed_dir", lambda: mock_dir)

    forecaster = get_forecaster("persistence", cfg)
    forecaster.fit(train_end)

    assert forecaster.last_train_load < 999990.0


def test_no_feature_row_at_or_after_origin(tmp_path, monkeypatch):
    cfg = config.load_config()
    load_path = get_load_path()
    load_df = pd.read_parquet(load_path)

    origin = pd.Timestamp("2024-06-01 10:00:00", tz=constants.TZ)

    mock_dir = tmp_path / "mock_proc"
    mock_dir.mkdir(parents=True, exist_ok=True)
    load_df.to_parquet(mock_dir / "load_hourly.parquet", index=False)
    monkeypatch.setattr(paths, "processed_dir", lambda: mock_dir)

    forecaster = get_forecaster("persistence", cfg)
    forecaster.fit(origin)
    preds1 = forecaster.predict(origin)

    perturbed_load = load_df.copy()
    perturbed_mask = perturbed_load["ts"] >= origin
    perturbed_load.loc[perturbed_mask, "load_mw"] = 888888.0
    perturbed_load.to_parquet(mock_dir / "load_hourly.parquet", index=False)

    preds2 = forecaster.predict(origin)

    pd.testing.assert_frame_equal(preds1, preds2)


def test_target_coverage_and_schema():
    cfg = config.load_config()
    forecaster = get_forecaster("persistence", cfg)
    origin = pd.Timestamp("2024-03-15 10:00:00", tz=constants.TZ)

    forecaster.fit(origin)
    preds = forecaster.predict(origin)

    assert len(preds) == 168
    assert preds["target_ts"].nunique() == 168

    expected_cols = [
        "target_ts",
        "horizon_h",
        "horizon_day",
        "p05",
        "p10",
        "p50",
        "p90",
        "p95",
    ]
    assert list(preds.columns) == expected_cols

    assert list(preds["horizon_h"]) == list(range(14, 182))
    assert list(preds["horizon_day"]) == [int(h // 24 + 1) for h in range(168)]

    first_target = preds["target_ts"].iloc[0]
    expected_start = pd.Timestamp("2024-03-16 00:00:00", tz=constants.TZ)
    assert first_target == expected_start

    last_target = preds["target_ts"].iloc[-1]
    expected_end = pd.Timestamp("2024-03-22 23:00:00", tz=constants.TZ)
    assert last_target == expected_end

    assert (preds["p05"] <= preds["p10"]).all()
    assert (preds["p10"] <= preds["p50"]).all()
    assert (preds["p50"] <= preds["p90"]).all()
    assert (preds["p90"] <= preds["p95"]).all()


def test_runner_output_schema(tmp_path, monkeypatch):
    art_dir = tmp_path / "mock_artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths, "artifacts_dir", lambda: art_dir)

    result_df = run_backtest(models=["persistence"], keep_persistence=True)
    assert not result_df.empty

    expected_contract_cols = [
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
    assert list(result_df.columns) == expected_contract_cols

    assert (result_df["model"] == "persistence").all()
    assert result_df["origin_ts"].dt.tz is not None
    assert str(result_df["origin_ts"].dt.tz) == constants.TZ
    assert result_df["target_ts"].dt.tz is not None
    assert str(result_df["target_ts"].dt.tz) == constants.TZ

    assert (result_df["p05"] <= result_df["p10"]).all()
    assert (result_df["p10"] <= result_df["p50"]).all()
    assert (result_df["p50"] <= result_df["p90"]).all()
    assert (result_df["p90"] <= result_df["p95"]).all()

    first_origin = result_df["origin_ts"].iloc[0]
    slice_df = result_df[result_df["origin_ts"] == first_origin]
    assert len(slice_df) == 168
    assert slice_df["target_ts"].nunique() == 168
