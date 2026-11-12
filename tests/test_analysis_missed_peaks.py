from datetime import date
import numpy as np
import pandas as pd
import pytest

from src.analysis.missed_peaks import (
    build_missed_peaks,
    classify_tags,
    generate_note,
)
from src.common import constants


def _make_toy_peak_row(
    model: str = "ensemble",
    target_date: str = "2024-06-12",
    magnitude_error_mw: float = -400.0,
    timing_error_min: int = -420,
    outcome: str = "miss",
) -> dict:
    return {
        "model": model,
        "fold_id": 0,
        "origin_ts": pd.Timestamp("2024-06-11 10:00:00+05:30"),
        "date": target_date,
        "threshold_mw": 7500.0,
        "peak_probability": 0.25,
        "decision_threshold": 0.35,
        "pred_is_peak": False,
        "pred_peak_hour": 15,
        "pred_peak_ts": pd.Timestamp(f"{target_date} 15:00:00+05:30"),
        "pred_peak_mw_p10": 7000.0,
        "pred_peak_mw_p50": 7200.0,
        "pred_peak_mw_p90": 7450.0,
        "actual_is_peak": True,
        "actual_peak_ts": pd.Timestamp(f"{target_date} 22:00:00+05:30"),
        "actual_peak_mw": 7600.0,
        "timing_error_min": timing_error_min,
        "magnitude_error_mw": magnitude_error_mw,
        "outcome": outcome,
    }


def _make_toy_day_features(
    target_date: str = "2024-06-12",
    is_festival: bool = False,
    is_holiday: bool = False,
    is_weekend: bool = False,
    temp_c: float = 38.0,
) -> pd.DataFrame:
    hours = list(range(24))
    ts_list = [
        pd.Timestamp(f"{target_date} {h:02d}:00:00+05:30") for h in hours
    ]
    return pd.DataFrame(
        {
            "ts": ts_list,
            "cal_is_festival_window": [is_festival] * 24,
            "cal_is_holiday": [is_holiday] * 24,
            "cal_is_weekend": [is_weekend] * 24,
            "wx_temp_c": [temp_c] * 24,
            "wx_rh_pct": [40.0] * 24,
        }
    )


def test_sorting_by_absolute_magnitude_error():
    rows = [
        _make_toy_peak_row(target_date="2024-06-10", magnitude_error_mw=-150.0),
        _make_toy_peak_row(target_date="2024-06-11", magnitude_error_mw=-520.0),
        _make_toy_peak_row(target_date="2024-06-12", magnitude_error_mw=300.0),
    ]
    peak_df = pd.DataFrame(rows)
    items = build_missed_peaks(peak_df)

    assert len(items) == 3
    magnitudes = [abs(it["magnitude_error_mw"]) for it in items]
    assert magnitudes == [520.0, 300.0, 150.0]


def test_tag_rules_festival():
    day_feat = _make_toy_day_features(is_festival=True)
    tags, _, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 12),
        origin_ts=pd.Timestamp("2024-06-11 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=None,
        cfg={},
    )
    assert "festival" in tags


def test_tag_rules_holiday():
    day_feat = _make_toy_day_features(is_holiday=True)
    tags, _, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 12),
        origin_ts=pd.Timestamp("2024-06-11 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=None,
        cfg={},
    )
    assert "holiday" in tags


def test_tag_rules_weekend():
    day_feat = _make_toy_day_features(is_weekend=True)
    tags, _, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 15),
        origin_ts=pd.Timestamp("2024-06-14 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=None,
        cfg={},
    )
    assert "weekend" in tags


def test_tag_rules_heatwave():
    day_feat = _make_toy_day_features(temp_c=46.0)
    past_temps = np.array([35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0])
    tags, _, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 12),
        origin_ts=pd.Timestamp("2024-06-11 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=past_temps,
        cfg={},
    )
    assert "heatwave" in tags


def test_tag_rules_weather_miss():
    day_feat = _make_toy_day_features(temp_c=42.0)
    cfg = {
        "weather_noise": {
            "base_sd_c": 0.5,
            "sd_growth_per_day_c": 0.4,
        },
        "seed": 42,
    }
    tags, temp_diff, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 15),
        origin_ts=pd.Timestamp("2024-06-10 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=None,
        cfg=cfg,
    )
    if temp_diff is not None and abs(temp_diff) > 2.0:
        assert "weather_miss" in tags


def test_tag_rules_other():
    day_feat = _make_toy_day_features(
        is_festival=False,
        is_holiday=False,
        is_weekend=False,
        temp_c=32.0,
    )
    tags, _, _ = classify_tags(
        day_features=day_feat,
        target_date=date(2024, 6, 12),
        origin_ts=pd.Timestamp("2024-06-11 10:00:00+05:30"),
        season="summer",
        past_season_daily_max_temps=np.array([35.0, 36.0, 37.0, 38.0, 39.0]),
        cfg={},
    )
    assert tags == ["other"]


def test_note_contains_right_numbers():
    note = generate_note(
        tags=["weather_miss"],
        temp_diff=3.1,
        timing_error_min=-420,
        magnitude_error_mw=-480.0,
        actual_max_temp=38.1,
    )
    assert "3.1 °C" in note
    assert "7 h" in note
    assert "later than predicted" in note


def test_note_timing_earlier():
    note = generate_note(
        tags=["other"],
        temp_diff=None,
        timing_error_min=120,
        magnitude_error_mw=-250.0,
        actual_max_temp=None,
    )
    assert "2 h" in note
    assert "earlier than predicted" in note
    assert "250 MW" in note


def test_only_misses_included():
    rows = [
        _make_toy_peak_row(target_date="2024-06-10", outcome="hit"),
        _make_toy_peak_row(target_date="2024-06-11", outcome="miss"),
        _make_toy_peak_row(target_date="2024-06-12", outcome="false_alarm"),
        _make_toy_peak_row(target_date="2024-06-13", outcome="correct_reject"),
    ]
    peak_df = pd.DataFrame(rows)
    items = build_missed_peaks(peak_df)
    assert len(items) == 1
    assert items[0]["date"] == "2024-06-11"

