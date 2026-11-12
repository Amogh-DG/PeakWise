import pytest
from src.common import config, constants, paths, seasons


def test_constants():
    assert constants.BASELINE_MODEL == "seasonal_naive"
    assert constants.MODELS == [
        "seasonal_naive",
        "linear",
        "lgbm",
        "xgboost",
        "prophet",
        "lstm",
        "ensemble",
    ]
    assert constants.QUANTILES == [0.05, 0.1, 0.5, 0.9, 0.95]
    assert constants.QUANTILE_COLS == ["p05", "p10", "p50", "p90", "p95"]
    assert constants.PEAK_HOURS == [6, 7, 8, 9, 10, 19, 20, 21, 22, 23]
    assert constants.HORIZON_DAYS == [1, 2, 3, 4, 5, 6, 7]
    assert constants.TZ == "Asia/Kolkata"


def test_seasons():
    assert seasons.SEASONS == ["winter", "summer", "monsoon", "post_monsoon"]
    covered = {seasons.season_of(month) for month in range(1, 13)}
    assert covered == set(seasons.SEASONS)

    assert seasons.season_of(12) == "winter"
    assert seasons.season_of(1) == "winter"
    assert seasons.season_of(2) == "winter"
    assert seasons.season_of(3) == "summer"
    assert seasons.season_of(6) == "summer"
    assert seasons.season_of(7) == "monsoon"
    assert seasons.season_of(9) == "monsoon"
    assert seasons.season_of(10) == "post_monsoon"
    assert seasons.season_of(11) == "post_monsoon"

    with pytest.raises(ValueError):
        seasons.season_of(0)

    with pytest.raises(ValueError):
        seasons.season_of(13)


def test_config():
    cfg = config.load_config()
    assert isinstance(cfg, dict)
    assert cfg["timezone"] == "Asia/Kolkata"
    assert cfg["origin_hour_local"] == 10
    assert cfg["quantiles"] == [0.05, 0.1, 0.5, 0.9, 0.95]
    assert cfg["seed"] == 42
    assert "paths" in cfg
    assert "backtest" in cfg
    assert "models" in cfg


def test_paths():
    assert isinstance(paths.is_mock(), bool)
    assert paths.raw_dir().exists()
    assert paths.external_dir().exists()
    assert paths.processed_dir().exists()
    assert paths.artifacts_dir().exists()
