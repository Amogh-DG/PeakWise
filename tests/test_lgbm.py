import pandas as pd
import pytest

import src.models
from src.backtest.registry import get_forecaster
from src.common import config, constants, paths


@pytest.fixture(scope="module")
def real_or_mock_load():
    p = paths.processed_dir() / "load_hourly.parquet"
    if not p.exists():
        p = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
    if not p.exists():
        pytest.skip("No load data available")
    return pd.read_parquet(p)


def test_lgbm_fit_and_quantile_ordering(real_or_mock_load):
    cfg = config.load_config()
    test_cfg = dict(cfg)
    test_cfg["models"] = dict(cfg.get("models", {}))
    test_cfg["models"]["lgbm"] = dict(cfg.get("models", {}).get("lgbm", {}))
    test_cfg["models"]["lgbm"]["n_estimators"] = 20
    test_cfg["models"]["lgbm"]["early_stopping_rounds"] = 5
    test_cfg["models"]["lgbm"]["origin_stride"] = 7

    forecaster = get_forecaster("lgbm", test_cfg)
    train_end = pd.Timestamp("2024-06-01 10:00:00", tz=constants.TZ)
    forecaster.fit(train_end)

    origin = pd.Timestamp("2024-06-05 10:00:00", tz=constants.TZ)
    preds = forecaster.predict(origin)

    assert len(preds) == 168
    assert "p05" in preds.columns
    assert "p10" in preds.columns
    assert "p50" in preds.columns
    assert "p90" in preds.columns
    assert "p95" in preds.columns

    p05 = preds["p05"].to_numpy()
    p10 = preds["p10"].to_numpy()
    p50 = preds["p50"].to_numpy()
    p90 = preds["p90"].to_numpy()
    p95 = preds["p95"].to_numpy()

    assert (p05 <= p10 + 1e-4).all()
    assert (p10 <= p50 + 1e-4).all()
    assert (p50 <= p90 + 1e-4).all()
    assert (p90 <= p95 + 1e-4).all()


def test_lgbm_no_future_leakage(real_or_mock_load):
    cfg = config.load_config()
    test_cfg = dict(cfg)
    test_cfg["models"] = dict(cfg.get("models", {}))
    test_cfg["models"]["lgbm"] = dict(cfg.get("models", {}).get("lgbm", {}))
    test_cfg["models"]["lgbm"]["n_estimators"] = 15
    test_cfg["models"]["lgbm"]["early_stopping_rounds"] = 5
    test_cfg["models"]["lgbm"]["origin_stride"] = 7

    forecaster = get_forecaster("lgbm", test_cfg)
    train_end = pd.Timestamp("2024-06-01 10:00:00", tz=constants.TZ)
    forecaster.fit(train_end)

    origin = pd.Timestamp("2024-06-05 10:00:00", tz=constants.TZ)
    preds_clean = forecaster.predict(origin)

    perturbed_load = forecaster.load_df.copy()
    mask = perturbed_load["ts"] >= origin
    perturbed_load.loc[mask, "load_mw"] = perturbed_load.loc[mask, "load_mw"] * 10.0

    forecaster.load_df = perturbed_load
    preds_perturbed = forecaster.predict(origin)

    pd.testing.assert_frame_equal(preds_clean, preds_perturbed)


def test_lgbm_deterministic_with_fixed_seed(real_or_mock_load):
    cfg = config.load_config()
    test_cfg = dict(cfg)
    test_cfg["models"] = dict(cfg.get("models", {}))
    test_cfg["models"]["lgbm"] = dict(cfg.get("models", {}).get("lgbm", {}))
    test_cfg["models"]["lgbm"]["n_estimators"] = 15
    test_cfg["models"]["lgbm"]["early_stopping_rounds"] = 5
    test_cfg["models"]["lgbm"]["origin_stride"] = 7
    test_cfg["seed"] = 42

    train_end = pd.Timestamp("2024-06-01 10:00:00", tz=constants.TZ)
    origin = pd.Timestamp("2024-06-05 10:00:00", tz=constants.TZ)

    m1 = get_forecaster("lgbm", test_cfg)
    m1.fit(train_end)
    p1 = m1.predict(origin)

    m2 = get_forecaster("lgbm", test_cfg)
    m2.fit(train_end)
    p2 = m2.predict(origin)

    pd.testing.assert_frame_equal(p1, p2)
