import pandas as pd
import pytest

from src.common import constants, paths


@pytest.fixture(scope="module")
def features_df():
    path = paths.processed_dir() / "features_known.parquet"
    if not path.exists():
        pytest.skip("features_known.parquet not yet generated")
    return pd.read_parquet(path)


def test_schema_matches_contract(features_df):
    expected_cols = [
        "ts",
        "cal_hour",
        "cal_dow",
        "cal_month",
        "cal_doy",
        "cal_hour_sin",
        "cal_hour_cos",
        "cal_dow_sin",
        "cal_dow_cos",
        "cal_is_weekend",
        "cal_is_holiday",
        "cal_holiday_name",
        "cal_days_to_diwali",
        "cal_days_since_diwali",
        "cal_days_to_holi",
        "cal_days_since_holi",
        "cal_days_to_eid",
        "cal_days_since_eid",
        "cal_is_festival_window",
        "evt_lockdown",
        "evt_odd_even",
        "wx_temp_c",
        "wx_rh_pct",
        "wx_dewpoint_c",
        "wx_wind_ms",
        "wx_cloud_pct",
        "wx_heat_index_c",
        "wx_cdh",
        "wx_cdh_24",
        "wx_temp_lag_1",
        "wx_temp_lag_3",
        "wx_temp_lag_6",
        "wx_temp_lag_12",
        "wx_temp_lag_24",
        "wx_temp_lag_48",
        "wx_temp_lag_72",
        "wx_temp_roll_24",
        "wx_temp_roll_72",
        "trend_t",
        "wx_is_noisy",
    ]
    assert list(features_df.columns) == expected_cols
    assert str(features_df["ts"].dt.tz) == constants.TZ
    assert features_df["ts"].is_monotonic_increasing
    assert features_df["ts"].is_unique


def test_no_nans_in_features(features_df):
    cols_to_check = [col for col in features_df.columns if col != "cal_holiday_name"]
    for col in cols_to_check:
        assert features_df[col].isna().sum() == 0


def test_festival_window_diwali_2024(features_df):
    diwali_exact = pd.Timestamp("2024-11-01 12:00:00", tz=constants.TZ)
    exact_row = features_df[features_df["ts"] == diwali_exact]
    assert not exact_row.empty
    assert bool(exact_row["cal_is_festival_window"].iloc[0]) is True

    window_sample = pd.Timestamp("2024-10-31 18:00:00", tz=constants.TZ)
    window_row = features_df[features_df["ts"] == window_sample]
    assert not window_row.empty
    assert bool(window_row["cal_is_festival_window"].iloc[0]) is True

    non_window_sample = pd.Timestamp("2024-10-20 12:00:00", tz=constants.TZ)
    non_window_row = features_df[features_df["ts"] == non_window_sample]
    assert not non_window_row.empty
    assert bool(non_window_row["cal_is_festival_window"].iloc[0]) is False


def test_festival_distances_bounded(features_df):
    for col in [
        "cal_days_to_diwali",
        "cal_days_since_diwali",
        "cal_days_to_holi",
        "cal_days_since_holi",
        "cal_days_to_eid",
        "cal_days_since_eid",
    ]:
        assert (features_df[col] >= -30.0).all()
        assert (features_df[col] <= 30.0).all()


def test_event_flags_binary(features_df):
    assert set(features_df["evt_lockdown"].unique()).issubset({0, 1})
    assert set(features_df["evt_odd_even"].unique()).issubset({0, 1})


def test_weather_derived_physics(features_df):
    assert (features_df["wx_cdh"] >= 0.0).all()
    assert (features_df["wx_cdh_24"] >= 0.0).all()
    assert (features_df["wx_heat_index_c"] >= -20.0).all()
    assert (features_df["wx_heat_index_c"] <= 70.0).all()
