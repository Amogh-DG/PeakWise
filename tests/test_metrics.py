import numpy as np
import pandas as pd
import pytest
from src.common import constants
from src.metrics.accuracy_table import build_accuracy_table
from src.metrics.metrics import (
    bias,
    improvement_pct,
    mae,
    mape,
    mean_pinball,
    mpiw_80,
    picp_80,
    picp_90,
    pinball,
    rmse,
)
from src.metrics.segments import SEGMENTS, get_segment_mask


def test_mape_toy():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 330.0])
    expected = (10.0 / 100.0 + 10.0 / 200.0 + 30.0 / 300.0) / 3.0 * 100.0
    assert pytest.approx(mape(y_true, y_pred), rel=1e-4) == expected


def test_rmse_toy():
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([13.0, 16.0])
    expected = np.sqrt((3.0**2 + (-4.0)**2) / 2.0)
    assert pytest.approx(rmse(y_true, y_pred), rel=1e-4) == expected


def test_mae_toy():
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([13.0, 16.0])
    expected = (3.0 + 4.0) / 2.0
    assert pytest.approx(mae(y_true, y_pred), rel=1e-4) == expected


def test_bias_toy():
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([13.0, 16.0])
    expected = (3.0 - 4.0) / 2.0
    assert pytest.approx(bias(y_true, y_pred), rel=1e-4) == expected


def test_pinball_toy():
    y_true = np.array([100.0, 100.0])
    y_pred = np.array([90.0, 110.0])
    q = 0.9
    expected = (0.9 * 10.0 + 0.1 * 10.0) / 2.0
    assert pytest.approx(pinball(y_true, y_pred, q), rel=1e-4) == expected


def test_picp_toy():
    y_true = np.array([100.0, 200.0, 300.0, 400.0])
    lower = np.array([90.0, 210.0, 250.0, 400.0])
    upper = np.array([110.0, 250.0, 350.0, 450.0])
    assert picp_80(y_true, lower, upper) == 0.75
    assert picp_90(y_true, lower, upper) == 0.75


def test_mpiw_toy():
    lower = np.array([10.0, 20.0])
    upper = np.array([30.0, 50.0])
    expected = (20.0 + 30.0) / 2.0
    assert pytest.approx(mpiw_80(lower, upper), rel=1e-4) == expected


def test_improvement_pct_toy():
    baseline = 10.0
    model = 8.0
    assert pytest.approx(improvement_pct(baseline, model), rel=1e-4) == 20.0
    assert improvement_pct(baseline, baseline) == 0.0
    assert improvement_pct(None, model) is None


def test_segments_mask():
    ts = pd.date_range("2024-01-01 00:00:00", periods=24, freq="h", tz=constants.TZ)
    df = pd.DataFrame({"target_ts": ts})

    mask_all = get_segment_mask(df, "all")
    assert mask_all.all()

    mask_winter = get_segment_mask(df, "winter")
    assert mask_winter.all()

    mask_summer = get_segment_mask(df, "summer")
    assert not mask_summer.any()

    mask_peak = get_segment_mask(df, "peak_hours")
    assert mask_peak.sum() == len(constants.PEAK_HOURS)


def test_accuracy_table_baseline_improvement_is_null():
    ts = pd.date_range("2024-01-01 00:00:00", periods=24, freq="h", tz=constants.TZ)
    df = pd.DataFrame(
        {
            "model": [constants.BASELINE_MODEL] * 24,
            "target_ts": ts,
            "horizon_day": [1] * 24,
            "y_true": [3000.0] * 24,
            "p05": [2700.0] * 24,
            "p10": [2800.0] * 24,
            "p50": [3000.0] * 24,
            "p90": [3200.0] * 24,
            "p95": [3300.0] * 24,
            "is_outage_suspect": [False] * 24,
        }
    )
    result = build_accuracy_table(df)
    assert "rows" in result
    for row in result["rows"]:
        if row["model"] == constants.BASELINE_MODEL:
            assert row["improvement_mape_pct"] is None
            assert row["improvement_rmse_pct"] is None
