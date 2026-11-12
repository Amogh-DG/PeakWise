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
