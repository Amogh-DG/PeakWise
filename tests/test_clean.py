import pandas as pd
import pytest

from src.common import constants, paths


@pytest.fixture(scope="module")
def clean_df():
    path = paths.processed_dir() / "load_hourly.parquet"
    if not path.exists():
        pytest.skip("load_hourly.parquet not yet generated")
    return pd.read_parquet(path)


def test_index_complete(clean_df):
    expected = pd.date_range(
        start=clean_df["ts"].min(),
        end=clean_df["ts"].max(),
        freq="h",
        tz=constants.TZ,
    )
    assert len(clean_df) == len(expected)
    diff = (clean_df["ts"] - expected).abs().max()
    assert diff == pd.Timedelta(0)


def test_index_unique_and_monotonic(clean_df):
    assert clean_df["ts"].is_unique
    assert clean_df["ts"].is_monotonic_increasing


def test_no_nans_in_load_mw(clean_df):
    assert clean_df["load_mw"].isna().sum() == 0


def test_schema_matches_contract(clean_df):
    expected_cols = ["ts", "load_mw", "is_imputed", "imputation_method", "is_outage_suspect"]
    assert list(clean_df.columns) == expected_cols
    assert str(clean_df["ts"].dt.tz) == constants.TZ
    assert clean_df["load_mw"].dtype in ("float64", "float32")
    assert clean_df["is_imputed"].dtype == bool
    assert clean_df["is_outage_suspect"].dtype == bool
    valid_methods = {"linear", "hour_of_week"}
    for val in clean_df["imputation_method"].dropna().unique():
        assert val in valid_methods


def test_imputed_flags_consistent(clean_df):
    not_imputed = clean_df[~clean_df["is_imputed"]]
    assert not_imputed["imputation_method"].isna().all()

    imputed = clean_df[clean_df["is_imputed"]]
    assert imputed["imputation_method"].notna().all()
    valid_methods = {"linear", "hour_of_week"}
    assert set(imputed["imputation_method"].unique()).issubset(valid_methods)
