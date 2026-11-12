from __future__ import annotations

import pandas as pd
import pytest

from src.common.constants import TZ
from src.peak.peak_hour import (
    compute_magnitude_error_mw,
    compute_timing_error_min,
    determine_outcome,
)


def test_determine_outcome_confusion_toy():
    assert determine_outcome(pred_is_peak=True, actual_is_peak=True) == "hit"
    assert determine_outcome(pred_is_peak=False, actual_is_peak=True) == "miss"
    assert determine_outcome(pred_is_peak=True, actual_is_peak=False) == "false_alarm"
    assert determine_outcome(pred_is_peak=False, actual_is_peak=False) == "correct_reject"


def test_timing_error_min_sign_convention():
    pred_ts = pd.Timestamp("2026-06-15 21:00:00", tz=TZ)
    actual_ts_earlier = pd.Timestamp("2026-06-15 19:30:00", tz=TZ)
    actual_ts_later = pd.Timestamp("2026-06-15 22:15:00", tz=TZ)
    actual_ts_exact = pd.Timestamp("2026-06-15 21:00:00", tz=TZ)

    diff_positive = compute_timing_error_min(pred_ts, actual_ts_earlier)
    assert diff_positive == 90

    diff_negative = compute_timing_error_min(pred_ts, actual_ts_later)
    assert diff_negative == -75

    diff_zero = compute_timing_error_min(pred_ts, actual_ts_exact)
    assert diff_zero == 0


def test_magnitude_error_mw_sign_convention():
    pred_p50 = 7500.0
    actual_high = 8000.0
    actual_low = 7100.0

    mag_err_under = compute_magnitude_error_mw(pred_p50, actual_high)
    assert mag_err_under == -500.0

    mag_err_over = compute_magnitude_error_mw(pred_p50, actual_low)
    assert mag_err_over == 400.0
