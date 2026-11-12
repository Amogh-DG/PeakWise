import math
import pandas as pd
import numpy as np
import pytest

from src.analysis.error_decomposition import build_heatmap
from src.common.seasons import SEASONS


def _make_toy_df() -> pd.DataFrame:
    tz = "Asia/Kolkata"
    rows = []
    rng = np.random.default_rng(42)
    base = pd.Timestamp("2024-01-01 00:00:00", tz=tz)
    for day_offset in range(60):
        for hour in range(24):
            ts = base + pd.Timedelta(days=day_offset, hours=hour)
            y_true = 3000.0 + rng.normal(0, 100)
            p50 = y_true + rng.normal(0, 50)
            rows.append({
                "model": "ensemble",
                "origin_ts": base + pd.Timedelta(days=day_offset),
                "target_ts": ts,
                "horizon_h": 14 + hour,
                "horizon_day": 1,
                "y_true": y_true,
                "p05": p50 - 200,
                "p10": p50 - 100,
                "p50": p50,
                "p90": p50 + 100,
                "p95": p50 + 200,
                "p05_raw": p50 - 200,
                "p10_raw": p50 - 100,
                "p50_raw": p50,
                "p90_raw": p50 + 100,
                "p95_raw": p50 + 200,
                "fold_id": 0,
                "is_outage_suspect": False,
            })
    return pd.DataFrame(rows)


def test_cell_shape():
    df = _make_toy_df()
    cells = build_heatmap(df)
    assert len(cells) > 0
    for cell in cells:
        assert len(cell["hours"]) == 24
        assert len(cell["seasons"]) == 4
        assert len(cell["values"]) == 4
        assert len(cell["counts"]) == 4
        for row_v in cell["values"]:
            assert len(row_v) == 24
        for row_c in cell["counts"]:
            assert len(row_c) == 24


def test_seasons_order():
    df = _make_toy_df()
    cells = build_heatmap(df)
    for cell in cells:
        assert cell["seasons"] == SEASONS


def test_hours_list():
    df = _make_toy_df()
    cells = build_heatmap(df)
    for cell in cells:
        assert cell["hours"] == list(range(24))


def test_counts_nonnegative():
    df = _make_toy_df()
    cells = build_heatmap(df)
    for cell in cells:
        for row in cell["counts"]:
            for c in row:
                assert c >= 0


def test_min_obs_null():
    tz = "Asia/Kolkata"
    rows = []
    base = pd.Timestamp("2024-01-01 00:00:00", tz=tz)
    for i in range(3):
        ts = base + pd.Timedelta(hours=i)
        rows.append({
            "model": "ensemble",
            "origin_ts": base,
            "target_ts": ts,
            "horizon_h": 14 + i,
            "horizon_day": 1,
            "y_true": 3000.0,
            "p05": 2800.0,
            "p10": 2900.0,
            "p50": 3000.0,
            "p90": 3100.0,
            "p95": 3200.0,
            "p05_raw": 2800.0,
            "p10_raw": 2900.0,
            "p50_raw": 3000.0,
            "p90_raw": 3100.0,
            "p95_raw": 3200.0,
            "fold_id": 0,
            "is_outage_suspect": False,
        })
    df = pd.DataFrame(rows)
    cells = build_heatmap(df)
    for cell in cells:
        for row_v in cell["values"]:
            for v in row_v:
                assert v is None


def test_known_mape_value():
    tz = "Asia/Kolkata"
    rows = []
    base = pd.Timestamp("2024-01-15 00:00:00", tz=tz)
    for i in range(10):
        ts = base + pd.Timedelta(days=i, hours=0)
        rows.append({
            "model": "ensemble",
            "origin_ts": base,
            "target_ts": ts,
            "horizon_h": 14,
            "horizon_day": 1,
            "y_true": 1000.0,
            "p05": 900.0,
            "p10": 950.0,
            "p50": 1100.0,
            "p90": 1150.0,
            "p95": 1200.0,
            "p05_raw": 900.0,
            "p10_raw": 950.0,
            "p50_raw": 1100.0,
            "p90_raw": 1150.0,
            "p95_raw": 1200.0,
            "fold_id": 0,
            "is_outage_suspect": False,
        })
    df = pd.DataFrame(rows)
    cells = build_heatmap(df)
    mape_cell = next(c for c in cells if c["metric"] == "mape" and c["horizon_day"] == 1)
    winter_idx = SEASONS.index("winter")
    hour0_val = mape_cell["values"][winter_idx][0]
    assert hour0_val is not None
    assert abs(hour0_val - 10.0) < 0.01


def test_season_mapping_contract():
    assert SEASONS == ["winter", "summer", "monsoon", "post_monsoon"]

