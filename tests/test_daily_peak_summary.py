from datetime import date
import numpy as np
import pandas as pd
import pytest
from src.common import constants, paths
from src.models.daily_summary import build_daily_peak_summary, save_daily_peak_summary


EXPECTED_COLUMNS = [
    "model",
    "origin_ts",
    "date",
    "horizon_day",
    "daily_max_p10",
    "daily_max_p50",
    "daily_max_p90",
    "argmax_hour_p50",
    "daily_min_p50",
    "y_true_daily_max",
]


def test_daily_peak_summary_schema_and_types():
    art_file = paths.artifacts_dir() / "daily_peak_summary.parquet"
    if not art_file.exists():
        mock_file = paths.repo_root() / "artifacts_mock" / "daily_peak_summary.parquet"
        if mock_file.exists():
            art_file = mock_file
        else:
            summary = build_daily_peak_summary()
            art_file = save_daily_peak_summary(summary)

    df = pd.read_parquet(art_file)
    assert not df.empty
    assert list(df.columns) == EXPECTED_COLUMNS

    assert df["origin_ts"].dt.tz is not None
    assert str(df["origin_ts"].dt.tz) == constants.TZ

    assert all(isinstance(d, date) for d in df["date"].dropna())
    assert df["horizon_day"].between(1, 7).all()
    assert df["argmax_hour_p50"].between(0, 23).all()

    assert (df["daily_max_p10"] <= df["daily_max_p50"] + 1e-4).all()
    assert (df["daily_max_p50"] <= df["daily_max_p90"] + 1e-4).all()
    assert (df["daily_min_p50"] <= df["daily_max_p50"] + 1e-4).all()


def test_daily_peak_summary_toy_computation():
    tz = constants.TZ
    origin = pd.Timestamp("2024-06-01 10:00:00", tz=tz)
    targets = pd.date_range("2024-06-02 00:00:00", periods=24, freq="h", tz=tz)

    p50_vals = np.linspace(3000.0, 5000.0, 24)
    p50_vals[15] = 5500.0
    p10_vals = p50_vals - 200.0
    p90_vals = p50_vals + 200.0
    y_vals = p50_vals + 50.0

    toy_preds = pd.DataFrame(
        {
            "model": "toy_model",
            "origin_ts": origin,
            "target_ts": targets,
            "horizon_day": 1,
            "p10": p10_vals,
            "p50": p50_vals,
            "p90": p90_vals,
            "y_true": y_vals,
        }
    )

    summary = build_daily_peak_summary(toy_preds)
    assert len(summary) == 1
    row = summary.iloc[0]

    assert row["model"] == "toy_model"
    assert row["origin_ts"] == origin
    assert row["date"] == date(2024, 6, 2)
    assert row["horizon_day"] == 1
    assert row["daily_max_p50"] == 5500.0
    assert row["daily_max_p10"] == 5300.0
    assert row["daily_max_p90"] == 5700.0
    assert row["daily_min_p50"] == 3000.0
    assert row["argmax_hour_p50"] == 15
    assert row["y_true_daily_max"] == 5550.0
