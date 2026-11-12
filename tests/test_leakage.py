import numpy as np
import pandas as pd
import pytest

from src.common import constants, paths
from src.features.ar_features import build_ar_features
from src.features.weather_noise import noisy_weather


@pytest.fixture(scope="module")
def load_df():
    path = paths.processed_dir() / "load_hourly.parquet"
    if not path.exists():
        pytest.skip("load_hourly.parquet not available")
    return pd.read_parquet(path)


def test_leakage_50_origins(load_df):
    min_date = load_df["ts"].min() + pd.Timedelta(days=400)
    max_date = load_df["ts"].max() - pd.Timedelta(days=8)

    eligible_origins = pd.date_range(
        start=min_date.floor("D") + pd.Timedelta(hours=10),
        end=max_date.floor("D") + pd.Timedelta(hours=10),
        freq="D",
        tz=constants.TZ,
    )

    rng = np.random.default_rng(42)
    selected_indices = rng.choice(len(eligible_origins), size=50, replace=False)
    origins = [eligible_origins[i] for i in selected_indices]

    for origin in origins:
        targets = pd.date_range(
            start=origin.floor("D") + pd.Timedelta(days=1),
            end=origin.floor("D") + pd.Timedelta(days=7, hours=23),
            freq="h",
            tz=constants.TZ,
        )

        clean_out = build_ar_features(load_df, origin, targets)

        perturbed_df = load_df.copy()
        mask = perturbed_df["ts"] >= origin
        perturbed_df.loc[mask, "load_mw"] = perturbed_df.loc[mask, "load_mw"] * 10.0

        perturbed_out = build_ar_features(perturbed_df, origin, targets)

        pd.testing.assert_frame_equal(clean_out, perturbed_out)


def test_weather_noise_deterministic():
    origin = pd.Timestamp("2024-06-01 10:00:00", tz=constants.TZ)
    dates = pd.date_range(origin, periods=24, freq="h", tz=constants.TZ)
    df = pd.DataFrame(
        {
            "ts": dates,
            "wx_temp_c": np.linspace(25.0, 35.0, 24),
            "wx_rh_pct": np.linspace(40.0, 70.0, 24),
            "wx_is_noisy": np.zeros(24, dtype=bool),
        }
    )

    out1 = noisy_weather(df, origin, horizon_day=1, seed=42)
    out2 = noisy_weather(df, origin, horizon_day=1, seed=42)
    pd.testing.assert_frame_equal(out1, out2)

    assert bool(out1["wx_is_noisy"].all()) is True
    assert not np.allclose(out1["wx_temp_c"].values, df["wx_temp_c"].values)
