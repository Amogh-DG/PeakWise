import datetime
import pandas as pd
import pytest
from src.common import paths
from src.models.daily_summary import export_daily_peak_summary


@pytest.fixture(scope="module")
def summary_df() -> pd.DataFrame:
    p = paths.artifacts_dir() / "daily_peak_summary.parquet"
    if not p.exists():
        return export_daily_peak_summary()
    return pd.read_parquet(p)


def test_daily_peak_summary_schema(summary_df: pd.DataFrame):
    expected_cols = [
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
    assert list(summary_df.columns) == expected_cols


def test_daily_peak_summary_types_and_invariants(summary_df: pd.DataFrame):
    assert len(summary_df) > 0
    assert summary_df["origin_ts"].dt.tz is not None
    assert str(summary_df["origin_ts"].dt.tz) == "Asia/Kolkata"

    assert isinstance(summary_df["date"].iloc[0], datetime.date)
    assert not summary_df.duplicated(subset=["model", "origin_ts", "date"]).any()

    assert (summary_df["argmax_hour_p50"] >= 0).all()
    assert (summary_df["argmax_hour_p50"] <= 23).all()

    assert (summary_df["daily_min_p50"] <= summary_df["daily_max_p50"]).all()
    assert (summary_df["daily_max_p10"] <= summary_df["daily_max_p50"] + 1e-4).all()
    assert (summary_df["daily_max_p50"] <= summary_df["daily_max_p90"] + 1e-4).all()

    non_null_cols = [
        "model",
        "origin_ts",
        "date",
        "horizon_day",
        "daily_max_p10",
        "daily_max_p50",
        "daily_max_p90",
        "argmax_hour_p50",
        "daily_min_p50",
    ]
    assert not summary_df[non_null_cols].isna().any().any()
