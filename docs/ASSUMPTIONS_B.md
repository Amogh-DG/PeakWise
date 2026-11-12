# Assumptions — Person B

## B-4 missed peaks

- Heatwave threshold: target day maximum temperature (`wx_temp_c`) exceeds the 95th percentile of daily maximum temperatures observed for that season in the training period (historical data before forecast origin).
- Weather miss threshold: absolute difference between actual daily maximum temperature and forecast weather proxy maximum temperature exceeds 2.0 °C.
- Festival window: `cal_is_festival_window` flag active (target day within ±2 days of a festival).
- Holiday: `cal_is_holiday` flag active on the target date.
- Weekend: `cal_is_weekend` flag active (Saturday or Sunday).
- Default tag: "other" applied when none of the specific event or weather conditions are triggered.

## B-9 Procurement advisor

### Quantile interpolation

`predictions_backtest.parquet` stores five calibrated quantile columns: `p05`, `p10`, `p50`, `p90`, `p95` (corresponding to 0.05, 0.10, 0.50, 0.90, 0.95). When the requested `risk_quantile` does not exactly coincide with one of these levels, `advisor.py` uses `numpy.interp` to linearly interpolate between the two adjacent stored quantile values. For example, risk_quantile=0.80 is linearly interpolated between p50 (0.50) and p90 (0.90). Values outside [0.05, 0.95] are extrapolated by NumPy's default (clamped to boundary values). This approximation introduces a small scheduling error for mid-range quantiles; it is acceptable because the five available levels cover the practically relevant procurement range.

### Newsvendor quantile

The theoretically optimal procurement quantile under the given loss structure is `(under_price − da_price) / (under_price − resale_price)`. With the default illustrative tariffs (da=5000, under=12000, resale=2500 INR/MWh) this yields `(12000−5000)/(12000−2500) = 7000/9500 ≈ 0.7368`.

### Baselines

Both baselines are derived from the horizon-1 P50 forecast column for the same model in the seven calendar days immediately preceding `start_date`. The mean of those 168 hourly P50 values defines `flat_mw` (flat_prev_week_mean); the maximum defines `alt_flat_prev_week_peak_mw`. Actual load values (`y_true`) are not used for baselines to avoid leakage into the scheduling decision. If the previous week is not present in the parquet file a `ValueError` is raised.

### Default tariff values

The illustrative placeholder tariffs stored in `artifacts/procurement_defaults.json` are:

| Tariff | Value (INR/MWh) |
|---|---|
| `da_price_inr_per_mwh` | 5,000 |
| `under_price_inr_per_mwh` | 12,000 |
| `resale_price_inr_per_mwh` | 2,500 |

These values are sourced from `config.yaml` (`procurement.da`, `procurement.under`, `procurement.resale`) and written by `src/procurement/defaults.py`. **They are illustrative placeholders, not actual DISCOM or IEX tariffs**, and are labelled as such in the `disclaimer` field. See `docs/ASSUMPTIONS.md` for the full caveat.

## B-12 Peak-event classifier

### Decision threshold and recall trade-off

The binary peak-event classifier predicts whether daily maximum load will exceed the fold-specific 90th percentile threshold. Grid reliability and DSM penalties penalize missed peaks heavily: under-procurement during grid stress events carries severe financial and operational exposure (DSM penalty rates up to 12,000 INR/MWh vs. surplus salvage resale discount). Consequently, the decision threshold is explicitly tuned for recall:
- The probability threshold is chosen on the held-out validation segment of each fold's training history to maximize precision subject to achieving `recall >= peak.min_recall` (default 0.80).
- If no threshold achieves the target minimum recall of 0.80, the optimizer falls back to maximizing $F_2$, weighting recall twice as heavily as precision.
- This asymmetry guarantees grid operators receive early warning on at least 80% of true high-demand days while suppressing unnecessary false alarms on standard operating days.

### Walk-forward threshold evaluation

The peak threshold definition strictly respects walk-forward temporal order:
- Thresholds are computed solely from the historical daily peaks within that fold's training window (`train_end`), either globally (90th percentile across all training days) or per-season when `peak.season_relative = true`.
- Test-fold data is never seen during threshold calculation, model fitting, or isotonic probability calibration, preventing any lookahead leakage into peak detection.

## B-13 Peak hour and error decomposition

### Quantile daily maximum series
`pred_peak_mw_p10`, `pred_peak_mw_p50`, and `pred_peak_mw_p90` represent the daily maximum value of each respective calibrated quantile forecast series across the 24 hours of that target day (`daily_max_p10`, `daily_max_p50`, `daily_max_p90` from `daily_peak_summary.parquet`). This provides conservative interval bounds on peak day load level under uncertainty.

### Timing error sign convention
`timing_error_min` is signed: `predicted_peak_ts - actual_peak_ts` in minutes. A positive value indicates the model predicted the peak later than it actually occurred; a negative value indicates the predicted peak occurred earlier than the actual peak. When `load_native.parquet` is available, sub-hourly native timestamps are used for `actual_peak_ts`.

### Magnitude error sign convention
`magnitude_error_mw` is signed: `predicted_p50_daily_max_mw - actual_peak_mw`. A positive value indicates over-prediction (predicted peak higher than actual); a negative value indicates under-prediction (shortfall).


