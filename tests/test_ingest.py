import pandas as pd

from src.common import constants, paths


def test_ingest_load_output_exists_and_valid():
    proc_dir = paths.processed_dir()
    hourly_path = proc_dir / "load_raw_hourly.parquet"
    assert hourly_path.exists()

    df = pd.read_parquet(hourly_path)
    assert "ts" in df.columns
    assert "load_mw" in df.columns
    assert df["ts"].dt.tz is not None
    assert str(df["ts"].dt.tz) == constants.TZ
    assert len(df) > 0
    assert df["ts"].is_monotonic_increasing


def test_ingest_load_native_if_fine():
    proc_dir = paths.processed_dir()
    native_path = proc_dir / "load_native.parquet"
    if native_path.exists():
        df = pd.read_parquet(native_path)
        assert "ts" in df.columns
        assert "load_mw" in df.columns
        assert df["ts"].dt.tz is not None
        assert str(df["ts"].dt.tz) == constants.TZ
        assert len(df) > 0


def test_ingest_weather_output_exists_and_valid():
    proc_dir = paths.processed_dir()
    weather_path = proc_dir / "weather_hourly.parquet"
    assert weather_path.exists()

    df = pd.read_parquet(weather_path)
    expected_cols = [
        "ts",
        "wx_temp_c",
        "wx_rh_pct",
        "wx_dewpoint_c",
        "wx_wind_ms",
        "wx_cloud_pct",
    ]
    for col in expected_cols:
        assert col in df.columns

    assert df["ts"].dt.tz is not None
    assert str(df["ts"].dt.tz) == constants.TZ
    assert len(df) > 0
    assert df["ts"].is_monotonic_increasing
