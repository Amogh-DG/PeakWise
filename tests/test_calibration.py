import numpy as np
import pandas as pd
import pytest
from src.common import constants
from src.metrics.metrics import picp_80, picp_90
from src.models.calibration import calibrate, get_calibration_origins


def test_calibration_window_never_overlaps_test_origins():
    tz = constants.TZ
    first_test_origin = pd.Timestamp("2024-06-01 10:00:00", tz=tz)
    test_origins = pd.date_range(start=first_test_origin, periods=30, freq="D", tz=tz)

    calib_origins = get_calibration_origins(first_test_origin, window_days=90)

    assert len(calib_origins) == 90
    assert max(calib_origins) < min(test_origins)
    assert set(calib_origins).isdisjoint(set(test_origins))


def test_quantile_ordering_preserved():
    tz = constants.TZ
    np.random.seed(42)
    n = 100
    origins = pd.date_range("2024-01-01 10:00:00", periods=n, freq="D", tz=tz)

    calib_dfs = []
    for i, o in enumerate(origins):
        targets = pd.date_range(o + pd.Timedelta(hours=14), periods=24, freq="h", tz=tz)
        y = np.random.normal(5000, 500, size=24)
        p50 = y + np.random.normal(0, 50, size=24)
        p10 = p50 - 100
        p90 = p50 + 100
        p05 = p10 - 50
        p95 = p90 + 50
        df_o = pd.DataFrame(
            {
                "origin_ts": o,
                "target_ts": targets,
                "horizon_h": range(14, 38),
                "horizon_day": 1,
                "y_true": y,
                "p05": p05,
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "p95": p95,
            }
        )
        calib_dfs.append(df_o)

    calib_df = pd.concat(calib_dfs, ignore_index=True)

    test_origins = pd.date_range("2024-05-01 10:00:00", periods=5, freq="D", tz=tz)
    test_dfs = []
    for o in test_origins:
        targets = pd.date_range(o + pd.Timedelta(hours=14), periods=24, freq="h", tz=tz)
        y = np.random.normal(5000, 500, size=24)
        p50 = y + 20.0
        p10 = p50 - 30.0
        p90 = p50 + 30.0
        p05 = p10 - 10.0
        p95 = p90 + 10.0
        df_test = pd.DataFrame(
            {
                "origin_ts": o,
                "target_ts": targets,
                "horizon_h": range(14, 38),
                "horizon_day": 1,
                "y_true": y,
                "p05": p05,
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "p95": p95,
            }
        )
        test_dfs.append(df_test)

    raw_test_df = pd.concat(test_dfs, ignore_index=True)

    cfg = {"calibration": {"window_days": 90, "coverage_80": 0.8, "coverage_90": 0.9}}
    calibrated_df = calibrate(raw_test_df, calib_df, cfg)

    assert len(calibrated_df) == len(raw_test_df)
    np.testing.assert_allclose(calibrated_df["p50"], raw_test_df["p50"])

    p05 = calibrated_df["p05"].to_numpy()
    p10 = calibrated_df["p10"].to_numpy()
    p50 = calibrated_df["p50"].to_numpy()
    p90 = calibrated_df["p90"].to_numpy()
    p95 = calibrated_df["p95"].to_numpy()

    assert (p05 <= p10 + 1e-6).all()
    assert (p10 <= p50 + 1e-6).all()
    assert (p50 <= p90 + 1e-6).all()
    assert (p90 <= p95 + 1e-6).all()


def test_coverage_moves_toward_target_on_synthetic_example():
    tz = constants.TZ
    rng = np.random.default_rng(123)

    n_cal = 1000
    p50_cal = np.full(n_cal, 4000.0)
    y_cal = p50_cal + rng.normal(0, 100.0, size=n_cal)
    p10_cal = p50_cal - 30.0
    p90_cal = p50_cal + 30.0
    p05_cal = p50_cal - 50.0
    p95_cal = p50_cal + 50.0

    cal_targets = pd.date_range("2024-01-01", periods=n_cal, freq="h", tz=tz)
    cal_df = pd.DataFrame(
        {
            "target_ts": cal_targets,
            "horizon_day": 1,
            "y_true": y_cal,
            "p05": p05_cal,
            "p10": p10_cal,
            "p50": p50_cal,
            "p90": p90_cal,
            "p95": p95_cal,
        }
    )

    n_test = 1000
    p50_test = np.full(n_test, 4000.0)
    y_test = p50_test + rng.normal(0, 100.0, size=n_test)
    p10_test = p50_test - 30.0
    p90_test = p50_test + 30.0
    p05_test = p50_test - 50.0
    p95_test = p50_test + 50.0

    test_targets = pd.date_range("2024-02-01", periods=n_test, freq="h", tz=tz)
    raw_test_df = pd.DataFrame(
        {
            "target_ts": test_targets,
            "horizon_day": 1,
            "y_true": y_test,
            "p05": p05_test,
            "p10": p10_test,
            "p50": p50_test,
            "p90": p90_test,
            "p95": p95_test,
        }
    )

    raw_picp_80 = picp_80(y_test, p10_test, p90_test)
    raw_picp_90 = picp_90(y_test, p05_test, p95_test)
    assert raw_picp_80 < 0.35
    assert raw_picp_90 < 0.50

    cfg = {"calibration": {"window_days": 90, "coverage_80": 0.8, "coverage_90": 0.9}}
    cal_res = calibrate(raw_test_df, cal_df, cfg)

    cal_picp_80 = picp_80(y_test, cal_res["p10"].to_numpy(), cal_res["p90"].to_numpy())
    cal_picp_90 = picp_90(y_test, cal_res["p05"].to_numpy(), cal_res["p95"].to_numpy())

    assert abs(cal_picp_80 - 0.80) < abs(raw_picp_80 - 0.80)
    assert abs(cal_picp_90 - 0.90) < abs(raw_picp_90 - 0.90)
    assert 0.75 <= cal_picp_80 <= 0.85
    assert 0.85 <= cal_picp_90 <= 0.95
