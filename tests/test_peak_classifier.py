from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.peak.classifier import (
    compute_thresholds,
    get_threshold_for_date,
    tune_decision_threshold,
)


def test_global_threshold_toy():
    peaks = pd.Series([1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0],
                      index=[date(2023, 1, i + 1) for i in range(10)])
    threshold = compute_thresholds(peaks, quantile=0.9, season_relative=False)
    assert isinstance(threshold, float)
    assert threshold == pytest.approx(9100.0)


def test_seasonal_threshold_toy():
    dates = []
    values = []
    for day in range(1, 15):
        dates.append(date(2023, 1, day))
        values.append(3000.0 + day * 100)
    for day in range(1, 15):
        dates.append(date(2023, 5, day))
        values.append(7000.0 + day * 100)
    peaks = pd.Series(values, index=dates)

    thresholds = compute_thresholds(peaks, quantile=0.9, season_relative=True)
    assert isinstance(thresholds, dict)
    assert "winter" in thresholds
    assert "summer" in thresholds
    assert thresholds["summer"] > thresholds["winter"]


def test_no_threshold_leakage_from_test_window():
    train_dates = [date(2023, 1, 1) + timedelta(days=i) for i in range(100)]
    train_values = [4000.0 + (i % 20) * 100 for i in range(100)]
    train_peaks = pd.Series(train_values, index=train_dates)

    threshold_before = compute_thresholds(train_peaks, quantile=0.9, season_relative=False)

    test_dates = [date(2023, 4, 15) + timedelta(days=i) for i in range(10)]
    corrupted_test_values = [999999.0] * 10
    test_peaks = pd.Series(corrupted_test_values, index=test_dates)

    combined_leaked_peaks = pd.concat([train_peaks, test_peaks])
    leaked_threshold = compute_thresholds(combined_leaked_peaks, quantile=0.9, season_relative=False)

    assert threshold_before != leaked_threshold
    clean_applied_threshold = compute_thresholds(train_peaks, quantile=0.9, season_relative=False)
    assert clean_applied_threshold == threshold_before


def test_label_and_get_threshold_logic():
    thresh_data = {"winter": 4500.0, "summer": 7500.0}
    winter_date = date(2023, 1, 15)
    summer_date = date(2023, 6, 15)

    w_thresh = get_threshold_for_date(thresh_data, winter_date)
    s_thresh = get_threshold_for_date(thresh_data, summer_date)

    assert w_thresh == 4500.0
    assert s_thresh == 7500.0

    load_winter_hit = 4600.0
    load_winter_miss = 4400.0
    assert int(load_winter_hit > w_thresh) == 1
    assert int(load_winter_miss > w_thresh) == 0


def test_tune_decision_threshold_satisfies_min_recall():
    y_true = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    y_prob = np.array([0.9, 0.85, 0.8, 0.75, 0.6, 0.65, 0.4, 0.3, 0.2, 0.1])

    t = tune_decision_threshold(y_true, y_prob, min_recall=0.8)
    preds = (y_prob >= t).astype(int)
    rec = np.sum((preds == 1) & (y_true == 1)) / np.sum(y_true == 1)
    assert rec >= 0.8


def test_tune_decision_threshold_fallback_f2():
    y_true = np.array([1, 0, 0, 0, 0])
    y_prob = np.array([0.2, 0.1, 0.1, 0.1, 0.1])

    t = tune_decision_threshold(y_true, y_prob, min_recall=0.99)
    assert 0.05 <= t <= 0.95


def test_empty_train_peaks_raises_value_error():
    empty_peaks = pd.Series([], dtype=float)
    with pytest.raises(ValueError, match="Cannot compute threshold from empty"):
        compute_thresholds(empty_peaks)
