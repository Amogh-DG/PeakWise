import numpy as np
import pandas as pd
import pytest

from src.backtest.registry import REGISTRY, get_forecaster
from src.common import constants
from src.models.ensemble import (
    EnsembleForecaster,
    combine_quantile_predictions,
    get_validation_origins,
    optimize_weights_for_horizon,
)


def test_ensemble_registration():
    assert "ensemble" in REGISTRY
    forecaster = get_forecaster("ensemble", {})
    assert isinstance(forecaster, EnsembleForecaster)
    assert forecaster.calibrate is True


def test_ensemble_weights_non_negative_and_sum_to_one():
    rng = np.random.default_rng(42)
    n_samples = 200
    y_true = rng.normal(5000, 500, size=n_samples)

    m1_p50 = y_true + rng.normal(0, 100, size=n_samples)
    m1 = np.column_stack([m1_p50 - 200, m1_p50 - 100, m1_p50, m1_p50 + 100, m1_p50 + 200])

    m2_p50 = y_true + rng.normal(0, 50, size=n_samples)
    m2 = np.column_stack([m2_p50 - 150, m2_p50 - 80, m2_p50, m2_p50 + 80, m2_p50 + 150])

    m3_p50 = y_true + rng.normal(0, 200, size=n_samples)
    m3 = np.column_stack([m3_p50 - 300, m3_p50 - 150, m3_p50, m3_p50 + 150, m3_p50 + 300])

    preds_list = [m1, m2, m3]
    quantiles = [0.05, 0.10, 0.50, 0.90, 0.95]

    weights = optimize_weights_for_horizon(preds_list, y_true, quantiles)

    assert len(weights) == 3
    assert (weights >= -1e-6).all()
    assert pytest.approx(float(np.sum(weights)), rel=1e-5) == 1.0
    assert weights[1] > weights[2]


def test_ensemble_validation_window_precedes_test_window():
    tz = constants.TZ
    train_end = pd.Timestamp("2024-06-01 10:00:00", tz=tz)
    val_origins = get_validation_origins(train_end, val_days=30)

    assert len(val_origins) == 30
    first_test_origin = train_end
    last_val_origin = max(val_origins)

    assert last_val_origin < first_test_origin
    assert last_val_origin + pd.Timedelta(days=7) <= train_end
    assert set(val_origins).isdisjoint({first_test_origin})


def test_ensemble_ordering_preserved():
    tz = constants.TZ
    target_ts = pd.date_range("2024-06-02 00:00:00", periods=168, freq="h", tz=tz)
    h_h = range(14, 182)
    h_day = [int(i // 24 + 1) for i in range(168)]

    df_base1 = pd.DataFrame(
        {
            "target_ts": target_ts,
            "horizon_h": h_h,
            "horizon_day": h_day,
            "p05": np.full(168, 3000.0),
            "p10": np.full(168, 3500.0),
            "p50": np.full(168, 4500.0),
            "p90": np.full(168, 5500.0),
            "p95": np.full(168, 6000.0),
        }
    )

    df_base2 = pd.DataFrame(
        {
            "target_ts": target_ts,
            "horizon_h": h_h,
            "horizon_day": h_day,
            "p05": np.full(168, 3200.0),
            "p10": np.full(168, 3700.0),
            "p50": np.full(168, 4600.0),
            "p90": np.full(168, 5400.0),
            "p95": np.full(168, 5900.0),
        }
    )

    base_preds = {"m1": df_base1, "m2": df_base2}
    weights = {h: {"m1": 0.4, "m2": 0.6} for h in range(1, 8)}
    quantiles = [0.05, 0.10, 0.50, 0.90, 0.95]

    combined = combine_quantile_predictions(base_preds, weights, quantiles)

    assert len(combined) == 168
    p05 = combined["p05"].to_numpy()
    p10 = combined["p10"].to_numpy()
    p50 = combined["p50"].to_numpy()
    p90 = combined["p90"].to_numpy()
    p95 = combined["p95"].to_numpy()

    assert (p05 <= p10 + 1e-4).all()
    assert (p10 <= p50 + 1e-4).all()
    assert (p50 <= p90 + 1e-4).all()
    assert (p90 <= p95 + 1e-4).all()
