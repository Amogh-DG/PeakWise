import numpy as np
import pandas as pd
import pytest
from src.backtest.registry import get_forecaster
from src.common import config, constants, paths
from src.models.quantile_utils import sort_quantiles
import src.models


def test_sort_quantiles_helper():
    df = pd.DataFrame(
        {
            "p05": [500.0, 100.0],
            "p10": [400.0, 200.0],
            "p50": [300.0, 300.0],
            "p90": [200.0, 400.0],
            "p95": [100.0, 500.0],
        }
    )
    sorted_df = sort_quantiles(df)
    assert (sorted_df["p05"] <= sorted_df["p10"]).all()
    assert (sorted_df["p10"] <= sorted_df["p50"]).all()
    assert (sorted_df["p50"] <= sorted_df["p90"]).all()
    assert (sorted_df["p90"] <= sorted_df["p95"]).all()


def test_seasonal_naive_never_uses_data_at_or_after_origin(tmp_path, monkeypatch):
    cfg = config.load_config()
    load_path = paths.processed_dir() / "load_hourly.parquet"
    if not load_path.exists():
        load_path = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
    load_df = pd.read_parquet(load_path)

    origin = pd.Timestamp("2024-05-15 10:00:00", tz=constants.TZ)

    mock_dir = tmp_path / "mock_proc"
    mock_dir.mkdir(parents=True, exist_ok=True)
    load_df.to_parquet(mock_dir / "load_hourly.parquet", index=False)
    monkeypatch.setattr(paths, "processed_dir", lambda: mock_dir)

    forecaster = get_forecaster("seasonal_naive", cfg)
    forecaster.fit(origin)
    preds1 = forecaster.predict(origin)

    perturbed_load = load_df.copy()
    perturbed_mask = perturbed_load["ts"] >= origin
    perturbed_load.loc[perturbed_mask, "load_mw"] = 999999.0
    perturbed_load.to_parquet(mock_dir / "load_hourly.parquet", index=False)

    preds2 = forecaster.predict(origin)

    pd.testing.assert_frame_equal(preds1, preds2)


def test_seasonal_naive_quantile_ordering():
    cfg = config.load_config()
    forecaster = get_forecaster("seasonal_naive", cfg)
    origin = pd.Timestamp("2024-04-10 10:00:00", tz=constants.TZ)

    forecaster.fit(origin)
    preds = forecaster.predict(origin)

    assert len(preds) == 168
    assert (preds["p05"] <= preds["p10"]).all()
    assert (preds["p10"] <= preds["p50"]).all()
    assert (preds["p50"] <= preds["p90"]).all()
    assert (preds["p90"] <= preds["p95"]).all()


def test_linear_never_uses_data_at_or_after_origin(tmp_path, monkeypatch):
    cfg = config.load_config()
    load_path = paths.processed_dir() / "load_hourly.parquet"
    if not load_path.exists():
        load_path = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
    load_df = pd.read_parquet(load_path)

    feat_path = paths.processed_dir() / "features_known.parquet"
    if not feat_path.exists():
        feat_path = paths.repo_root() / "data" / "processed_mock" / "features_known.parquet"
    feat_df = pd.read_parquet(feat_path)

    origin = pd.Timestamp("2024-05-15 10:00:00", tz=constants.TZ)

    mock_dir = tmp_path / "mock_proc"
    mock_dir.mkdir(parents=True, exist_ok=True)
    load_df.to_parquet(mock_dir / "load_hourly.parquet", index=False)
    feat_df.to_parquet(mock_dir / "features_known.parquet", index=False)
    monkeypatch.setattr(paths, "processed_dir", lambda: mock_dir)

    forecaster = get_forecaster("linear", cfg)
    forecaster.fit(origin)
    preds1 = forecaster.predict(origin)

    perturbed_load = load_df.copy()
    perturbed_mask = perturbed_load["ts"] >= origin
    perturbed_load.loc[perturbed_mask, "load_mw"] = 888888.0
    perturbed_load.to_parquet(mock_dir / "load_hourly.parquet", index=False)

    preds2 = forecaster.predict(origin)

    pd.testing.assert_frame_equal(preds1, preds2)


def test_linear_quantile_ordering():
    cfg = config.load_config()
    forecaster = get_forecaster("linear", cfg)
    origin = pd.Timestamp("2024-04-10 10:00:00", tz=constants.TZ)

    forecaster.fit(origin)
    preds = forecaster.predict(origin)

    assert len(preds) == 168
    assert (preds["p05"] <= preds["p10"]).all()
    assert (preds["p10"] <= preds["p50"]).all()
    assert (preds["p50"] <= preds["p90"]).all()
    assert (preds["p90"] <= preds["p95"]).all()
