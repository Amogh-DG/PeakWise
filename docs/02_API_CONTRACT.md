# 02 — API & Data Contract

**Status:** DRAFT → frozen at Checkpoint 0. After freeze, any change = edit this file + tell the whole team (version bump in §5).
**Version:** `1.1.0`

Two layers are specified here:
1. **§1 Data artifacts** — the Parquet/JSON files roles A/B/C produce. This is how the roles talk to each other.
2. **§2 REST API** — what the FastAPI backend (D) serves to the React UI.

---

## 0. Conventions

| Topic | Rule |
|---|---|
| Timezone | `Asia/Kolkata` (IST, UTC+05:30, no DST). All timestamps are ISO 8601 **with offset**, e.g. `2026-06-12T19:00:00+05:30` |
| Timestamp meaning | **Hour-beginning**: `19:00` = demand during 19:00–19:59 |
| Units | Power in **MW**, energy in **MWh**, money in **INR**, temperature in **°C** |
| Forecast origin | **10:00 IST on day D0**. Targets run from D+1 00:00 to D+7 23:00 (horizons 14–181 h) |
| Day-ahead | `horizon_day = 1` (D+1, 24 hourly points) |
| Week-ahead | `horizon_day = 1..7` (D+1…D+7, 168 hourly points) |
| Quantile columns | `p05, p10, p50, p90, p95`. Invariant: `p05 ≤ p10 ≤ p50 ≤ p90 ≤ p95`. **P10–P90 = 80% interval; P05–P95 = 90% interval** |
| Missing values | JSON `null` (never `NaN`, never `-1`). `actual` is `null` when not yet observed |
| Case | `snake_case` for all JSON keys and columns |
| Dates | `YYYY-MM-DD` (IST calendar date). A date always refers to the **target** date |

### Enums

| Name | Values |
|---|---|
| `model` | `seasonal_naive`, `linear`, `lgbm`, `xgboost`, `prophet`, `lstm`, `ensemble` |
| `season` | `winter` (Dec–Feb), `summer` (Mar–Jun), `monsoon` (Jul–Sep), `post_monsoon` (Oct–Nov) |
| `segment` (metrics) | `all`, `winter`, `summer`, `monsoon`, `post_monsoon`, `peak_hours`, `off_peak` |
| `peak_hours` (hour-beginning) | `6,7,8,9,10` (morning ramp) and `19,20,21,22,23` (evening peak). Everything else = `off_peak` |
| `outcome` (peak events) | `hit` (predicted peak & was peak), `miss` (not predicted, was peak), `false_alarm` (predicted, wasn't), `correct_reject` |
| `error_metric` | `mape`, `rmse`, `bias` |
| `tag` (missed peaks) | `festival`, `holiday`, `heatwave`, `weather_miss`, `weekend`, `other` |

Default model for UI = `ensemble`. Default baseline = `seasonal_naive`.

---

## 1. Data artifacts

### 1.1 `data/processed/load_hourly.parquet` — producer A

One row per hour; index complete, unique, sorted.

| Column | Type | Notes |
|---|---|---|
| `ts` | `datetime64[ns, Asia/Kolkata]` | hour-beginning, unique, no gaps |
| `load_mw` | float | after imputation |
| `is_imputed` | bool | |
| `imputation_method` | string \| null | `linear`, `hour_of_week`, or null |
| `is_outage_suspect` | bool | flagged by MAD z-score; kept in data |

### 1.2 `data/processed/features_known.parquet` — producer A

Features knowable **in advance** for any target hour (calendar, events, weather proxy, trend). Same `ts` index as 1.1. Autoregressive features come from §1.3, not this file.

| Group | Columns |
|---|---|
| Calendar | `cal_hour`, `cal_dow`, `cal_month`, `cal_doy`, `cal_hour_sin`, `cal_hour_cos`, `cal_dow_sin`, `cal_dow_cos`, `cal_is_weekend`, `cal_is_holiday`, `cal_holiday_name` |
| Festivals | `cal_days_to_diwali`, `cal_days_since_diwali`, `cal_days_to_holi`, `cal_days_since_holi`, `cal_days_to_eid`, `cal_days_since_eid`, `cal_is_festival_window` (any festival within ±2 days) — values clipped to ±30 |
| Events | `evt_lockdown` (0/1), `evt_odd_even` (0/1) |
| Weather | `wx_temp_c`, `wx_rh_pct`, `wx_dewpoint_c`, `wx_wind_ms`, `wx_cloud_pct`, `wx_heat_index_c`, `wx_cdh` (hourly cooling degree-hours above base), `wx_cdh_24` (rolling 24h sum) |
| Thermal inertia | `wx_temp_lag_1`, `wx_temp_lag_3`, `wx_temp_lag_6`, `wx_temp_lag_12`, `wx_temp_lag_24`, `wx_temp_lag_48`, `wx_temp_lag_72`, `wx_temp_roll_24`, `wx_temp_roll_72` |
| Trend | `trend_t` (days since first timestamp, float) |
| Flags | `wx_is_noisy` (bool: weather noise injected per `config.yaml: weather_noise`) |

### 1.3 `src/features/ar_features.py` — producer A

```python
def build_ar_features(load_df: pd.DataFrame, origin_ts: pd.Timestamp,
                      target_ts: pd.DatetimeIndex) -> pd.DataFrame:
    """Return one row per target_ts. Uses ONLY load_df rows with ts < origin_ts.
    Columns: ar_same_hour_last_week, ar_same_hour_last_known_day,
             ar_mean_7d, ar_mean_30d, ar_level_365d, ar_last_known_load,
             ar_last_week_daily_peak, ar_hours_since_last_known (= horizon proxy).
    """
```
Test: for every origin, no input row has `ts >= origin_ts`.

### 1.4 `artifacts/predictions_backtest.parquet` — producer B

Long format; one row per (model, origin, target hour).

| Column | Type | Notes |
|---|---|---|
| `model` | string | enum above |
| `fold_id` | int | retrain fold |
| `origin_ts` | datetime tz | 10:00 IST on D0 |
| `target_ts` | datetime tz | hour-beginning |
| `horizon_h` | int | hours from origin to target (14–181) |
| `horizon_day` | int | 1..7 |
| `y_true` | float \| null | actual MW |
| `p05`,`p10`,`p50`,`p90`,`p95` | float | **final** (post-calibration) |
| `p05_raw`,`p10_raw`,`p50_raw`,`p90_raw`,`p95_raw` | float | pre-calibration |
| `is_outage_suspect` | bool | copied from 1.1 |

### 1.5 `artifacts/peak_predictions.parquet` — producer C

One row per (model, target date).

| Column | Type | Notes |
|---|---|---|
| `model` | string | forecaster whose summaries fed the classifier (`ensemble` default) |
| `fold_id` | int | |
| `origin_ts` | datetime tz | |
| `date` | date | target date |
| `threshold_mw` | float | per-fold top-decile daily-peak threshold |
| `peak_probability` | float | calibrated, 0–1 |
| `decision_threshold` | float | probability cut-off tuned for recall |
| `pred_is_peak` | bool | `peak_probability ≥ decision_threshold` |
| `pred_peak_hour` | int | 0–23 |
| `pred_peak_ts` | datetime tz | |
| `pred_peak_mw_p10`,`pred_peak_mw_p50`,`pred_peak_mw_p90` | float | daily max forecast |
| `actual_is_peak` | bool \| null | |
| `actual_peak_ts` | datetime tz \| null | |
| `actual_peak_mw` | float \| null | |
| `timing_error_min` | int \| null | signed, predicted − actual (multiples of 60 if hourly) |
| `magnitude_error_mw` | float \| null | signed, predicted P50 − actual |
| `outcome` | string \| null | enum above |

### 1.6 `artifacts/metrics_accuracy.json` — producer B

```json
{
  "generated_at": "2026-11-12T10:00:00+05:30",
  "rows": [
    {
      "model": "lgbm",
      "horizon_day": 1,
      "segment": "peak_hours",
      "n": 3650,
      "mape": 4.8,
      "rmse_mw": 312.4,
      "mae_mw": 241.0,
      "bias_mw": -35.2,
      "pinball": 61.3,
      "picp_80": 0.79,
      "picp_90": 0.89,
      "mpiw_80_mw": 780.0,
      "improvement_mape_pct": 31.2,
      "improvement_rmse_pct": 28.7
    }
  ]
}
```
- `horizon_day`: `1..7` or `"all"`.
- `mape` in **percent**; `picp_*` as **fraction 0–1**; `improvement_*` vs `seasonal_naive` in the same `horizon_day` + `segment` (null for the baseline itself).
- `pinball` = mean over the five quantiles.
- Rows exist for every model × horizon_day (1–7 + `"all"`) × segment.

### 1.7 `artifacts/metrics_peak.json` — producer C

```json
{
  "threshold_definition": "90th percentile of daily peak MW in each fold's training window",
  "rows": [
    {
      "model": "ensemble",
      "classifier": "lgbm_clf",
      "n_days": 365, "n_peak_days": 37,
      "precision": 0.72, "recall": 0.84, "f1": 0.78, "pr_auc": 0.81,
      "confusion": {"tp": 31, "fp": 12, "fn": 6, "tn": 316},
      "decision_threshold": 0.35,
      "timing_mae_min": 78, "timing_within_1h_pct": 0.74,
      "magnitude_mae_mw": 285.0, "magnitude_bias_mw": -40.0
    },
    {"model": "rule_same_weekday_last_week", "classifier": "rule", "precision": 0.55, "recall": 0.60, "...": "..."}
  ]
}
```

### 1.8 `artifacts/error_heatmap.json` — producer C

```json
{
  "cells": [
    {
      "model": "ensemble", "metric": "mape", "horizon_day": 1,
      "hours": [0,1,2,"...",23],
      "seasons": ["winter","summer","monsoon","post_monsoon"],
      "values": [[4.1,3.9,"...24 values"], ["...4 rows total"]],
      "counts": [[90,90,"..."], ["..."]]
    }
  ]
}
```
`values[i][j]` = metric for `seasons[i]`, `hours[j]`. One entry per model × metric × horizon_day (1 and `"all"` at minimum).

### 1.9 `artifacts/missed_peaks.json` — producer C

```json
{
  "items": [
    {
      "model": "ensemble",
      "date": "2026-05-29",
      "season": "summer",
      "threshold_mw": 7650.0,
      "peak_probability": 0.22,
      "pred_peak_ts": "2026-05-29T15:00:00+05:30",
      "pred_peak_mw_p50": 7410.0,
      "actual_peak_ts": "2026-05-29T22:00:00+05:30",
      "actual_peak_mw": 7890.0,
      "magnitude_error_mw": -480.0,
      "timing_error_min": -420,
      "tags": ["heatwave", "weather_miss"],
      "note": "Actual max temp 3.1 °C above the weather proxy; peak shifted to night (thermal inertia)."
    }
  ]
}
```
Sorted by `abs(magnitude_error_mw)` descending. Includes every `miss` for each model.

### 1.10 `artifacts/feature_importance.json` — producer B

```json
{
  "models": {
    "lgbm": [
      {"feature": "wx_cdh_24", "importance": 0.182, "group": "weather"},
      {"feature": "ar_same_hour_last_week", "importance": 0.141, "group": "autoregressive"}
    ]
  }
}
```
`importance` normalised to sum to 1 per model. `group` ∈ `calendar`, `festival`, `event`, `weather`, `thermal_inertia`, `trend`, `autoregressive`, `horizon`.

### 1.11 `artifacts/procurement_defaults.json` — producer C

```json
{
  "tariff": {
    "da_price_inr_per_mwh": 5000,
    "under_price_inr_per_mwh": 12000,
    "resale_price_inr_per_mwh": 2500
  },
  "disclaimer": "Illustrative placeholder values, not actual DISCOM tariffs. See docs/ASSUMPTIONS.md.",
  "default_risk_quantile": 0.9
}
```
Definitions: `da_price` = price paid per MWh scheduled day-ahead; `under_price` = price paid per MWh of shortfall bought real-time/DSM; `resale_price` = recovery per MWh of unused surplus. Newsvendor quantile = `(under − da) / (under − resale)`.

### 1.12 `artifacts/meta.json` — assembled by D

```json
{
  "version": "1.0.0",
  "timezone": "Asia/Kolkata",
  "origin_hour_local": 10,
  "data_range": {"start": "2023-01-01T00:00:00+05:30", "end": "2026-10-31T23:00:00+05:30"},
  "backtest_range": {"start": "2025-11-01", "end": "2026-10-31"},
  "quantiles": [0.05, 0.1, 0.5, 0.9, 0.95],
  "peak_threshold_mw_latest": 7650.0,
  "peak_definition": "Daily peak above the 90th percentile of daily peaks in the fold's training window",
  "season_definition": {"winter": [12,1,2], "summer": [3,4,5,6], "monsoon": [7,8,9], "post_monsoon": [10,11]},
  "peak_hours": [6,7,8,9,10,19,20,21,22,23],
  "models": ["seasonal_naive","linear","lgbm","xgboost","prophet","lstm","ensemble"],
  "weather_proxy_note": "Backtests use observed weather plus horizon-scaled noise as a stand-in for archived weather forecasts."
}
```

### 1.13 `artifacts/daily_peak_summary.parquet` — producer A, consumer B

One row per `(model, origin_ts, date)`. Summary of daily forecast peaks and extremes across the 24 hourly values of each target day for peak event classification and evaluation.

| Column | Type | Notes |
|---|---|---|
| `model` | string | forecaster model enum |
| `origin_ts` | datetime tz | 10:00 IST on D0, tz-aware (`Asia/Kolkata`) |
| `date` | date | target calendar date (`date32` / `YYYY-MM-DD`) |
| `horizon_day` | int | 1..7 |
| `daily_max_p10` | float | maximum over the day's 24 hourly values of p10 |
| `daily_max_p50` | float | maximum over the day's 24 hourly values of p50 |
| `daily_max_p90` | float | maximum over the day's 24 hourly values of p90 |
| `argmax_hour_p50` | int | hour of day (0..23) where p50 reaches its daily maximum |
| `daily_min_p50` | float | minimum over the day's 24 hourly values of p50 |
| `y_true_daily_max` | float \| null | maximum over the day's 24 hourly values of y_true (null if unobserved) |

---

## 2. REST API (FastAPI, prefix `/api/v1`)

Base URL local: `http://localhost:8000/api/v1`. All endpoints are `GET` unless stated. All responses `application/json`. CORS open for the UI origin.

### 2.1 `GET /health`
```json
{"status": "ok", "version": "1.0.0", "mock": false, "artifacts_loaded": true}
```

### 2.2 `GET /meta`
Returns `artifacts/meta.json` (§1.12) as is.

### 2.3 `GET /models`
```json
{"models": [
  {"id": "ensemble", "label": "Ensemble", "kind": "ensemble", "is_baseline": false},
  {"id": "seasonal_naive", "label": "Seasonal naive (same hour last week)", "kind": "baseline", "is_baseline": true}
]}
```

### 2.4 `GET /forecast/day-ahead`
Query: `date` (required, target date D+1), `model` (default `ensemble`).

```json
{
  "date": "2026-06-12",
  "model": "ensemble",
  "origin_ts": "2026-06-11T10:00:00+05:30",
  "unit": "MW",
  "peak_threshold_mw": 7650.0,
  "points": [
    {
      "ts": "2026-06-12T00:00:00+05:30",
      "horizon_h": 14,
      "p05": 5100.2, "p10": 5230.0, "p50": 5480.5, "p90": 5760.3, "p95": 5890.1,
      "actual": 5455.0,
      "at_risk": false
    }
  ],
  "peak": {
    "predicted_peak_ts": "2026-06-12T22:00:00+05:30",
    "predicted_peak_mw": {"p10": 7400.0, "p50": 7720.0, "p90": 8050.0},
    "actual_peak_ts": "2026-06-12T22:00:00+05:30",
    "actual_peak_mw": 7810.0
  }
}
```
- 24 points. `at_risk` = `p90 ≥ peak_threshold_mw`. `actual*` fields are `null` if unobserved.
- Errors: `DATE_OUT_OF_RANGE` (404), `UNKNOWN_MODEL` (400).

### 2.5 `GET /forecast/week-ahead`
Query: `start_date` (required, first target date), `model` (default `ensemble`).
Same shape as 2.4 with: `start_date`, `end_date`, 168 `points`, an added `horizon_day` on each point, and `daily_peaks`: array of 7 objects shaped like the `peak` object above plus `date`.

### 2.6 `GET /peak/day`
Query: `date` (required), `model` (default `ensemble`).
```json
{
  "date": "2026-06-12",
  "model": "ensemble",
  "threshold_mw": 7650.0,
  "peak_probability": 0.81,
  "decision_threshold": 0.35,
  "is_peak_day_pred": true,
  "predicted_peak_hour": 22,
  "predicted_peak_ts": "2026-06-12T22:00:00+05:30",
  "predicted_peak_mw": {"p10": 7400.0, "p50": 7720.0, "p90": 8050.0},
  "actual": {"is_peak_day": true, "peak_ts": "2026-06-12T22:00:00+05:30", "peak_mw": 7810.0},
  "timing_error_min": 0,
  "magnitude_error_mw": -90.0,
  "outcome": "hit"
}
```
`actual`, `timing_error_min`, `magnitude_error_mw`, `outcome` are `null` if unobserved.

### 2.7 `GET /peak/events`
Query: `from`, `to` (dates, required), `model` (default `ensemble`), `outcome` (optional enum filter), `limit` (default 100, max 500), `offset` (default 0).
```json
{"total": 37, "items": [ { "...same shape as 2.6, without the model field..." } ]}
```

### 2.8 `GET /backtest/predictions`
Query: `from`, `to` (dates, **max span 92 days**), `model` (default `ensemble`), `horizon_day` (default 1; 1–7).
```json
{
  "model": "ensemble", "horizon_day": 1,
  "points": [
    {"ts": "...", "origin_ts": "...", "p05": 0, "p10": 0, "p50": 0, "p90": 0, "p95": 0, "actual": 0.0}
  ]
}
```
Errors: `BAD_DATE_RANGE` (400) when `to < from` or span > 92 days.

### 2.9 `GET /backtest/metrics`
Query (all optional): `model` (repeatable), `horizon_day` (`1`–`7` or `all`), `segment` (enum).
```json
{"generated_at": "...", "rows": [ { "...rows exactly as in §1.6..." } ]}
```
With no filters, returns every row (the UI builds the accuracy table client-side).

### 2.10 `GET /backtest/peak-metrics`
Query: `model` (optional).
Returns `artifacts/metrics_peak.json` (§1.7), filtered when `model` is given. Rule-based baselines are always included.

### 2.11 `GET /backtest/error-heatmap`
Query: `model` (default `ensemble`), `metric` (default `mape`), `horizon_day` (default `1`, or `all`).
Returns a single cell object from §1.8:
```json
{"model": "ensemble", "metric": "mape", "horizon_day": 1, "hours": [0,"..."], "seasons": ["winter","summer","monsoon","post_monsoon"], "values": [[...]], "counts": [[...]]}
```
Error: `NOT_FOUND` (404) if the combination wasn't produced.

### 2.12 `POST /procurement/recommend`
Request:
```json
{
  "start_date": "2026-06-08",
  "days": 7,
  "model": "ensemble",
  "risk_quantile": 0.9,
  "tariff": {
    "da_price_inr_per_mwh": 5000,
    "under_price_inr_per_mwh": 12000,
    "resale_price_inr_per_mwh": 2500
  }
}
```
- `days`: 1–7. `risk_quantile`: number in `[0.5, 0.99]` **or** the string `"newsvendor"`. `tariff` is optional (defaults from §1.11); when given, all three fields are required.
- Backed by `src/procurement/advisor.py::recommend(start_date, days, model, risk_quantile, tariff) -> dict` returning exactly the response below. D must call that function directly, not reimplement it.

Cost definitions (hour *h*, scheduled `S`, demand `D`, `U = max(D−S, 0)`, `O = max(S−D, 0)`):
`cost = da_price·S + under_price·U − resale_price·O`.
Newsvendor quantile = `(under_price − da_price) / (under_price − resale_price)`.

Response:
```json
{
  "start_date": "2026-06-08", "end_date": "2026-06-14", "model": "ensemble",
  "risk_quantile": 0.9,
  "risk_quantile_source": "user",
  "newsvendor_quantile": 0.737,
  "tariff_used": {"da_price_inr_per_mwh": 5000, "under_price_inr_per_mwh": 12000, "resale_price_inr_per_mwh": 2500},
  "baseline": {"type": "flat_prev_week_mean", "flat_mw": 5420.0, "alt_flat_prev_week_peak_mw": 7600.0},
  "schedule": [
    {"ts": "2026-06-08T00:00:00+05:30", "scheduled_mw": 5900.0, "p50_mw": 5480.5, "p90_mw": 5900.0, "flat_mw": 5420.0, "actual_mw": 5455.0}
  ],
  "summary": {
    "total_scheduled_mwh": 1100000.0,
    "cost_inr": 5.62e9,
    "flat_cost_inr": 5.91e9,
    "flat_peak_cost_inr": 6.30e9,
    "savings_inr": 2.9e8,
    "savings_pct": 4.9,
    "p90_risk_exposure_inr": 3.1e8,
    "under_procured_hours": 9,
    "over_procured_hours": 159,
    "at_risk_hours": ["2026-06-12T21:00:00+05:30"]
  },
  "by_day": [
    {"date": "2026-06-08", "scheduled_mwh": 150000.0, "cost_inr": 7.9e8, "flat_cost_inr": 8.4e8, "peak_scheduled_mw": 7900.0}
  ]
}
```
- `schedule` has `24 × days` entries. `actual_mw` is `null` for hours without observations; in that case `cost_inr`, `flat_cost_inr`, `flat_peak_cost_inr`, `savings_*`, `under/over_procured_hours` are `null` and only `p90_risk_exposure_inr` is returned.
- `p90_risk_exposure_inr` = cost if demand followed the P90 path − cost if demand followed the P50 path, for the same schedule.
- `risk_quantile_source`: `"user"` or `"newsvendor"`.
- Numbers above are format examples, not expected values.

### 2.13 `GET /procurement/defaults`
Returns `artifacts/procurement_defaults.json` (§1.11).

### 2.14 `GET /backtest/missed-peaks`
Query: `model` (default `ensemble`), `tag` (optional enum), `limit` (default 50, max 200), `offset` (default 0).
```json
{"total": 6, "items": [ { "...items as in §1.9..." } ]}
```

### 2.15 `GET /models/{model}/feature-importance`
Query: `top` (default 20, max 100).
```json
{"model": "lgbm", "features": [{"feature": "wx_cdh_24", "importance": 0.182, "group": "weather"}]}
```
Models without importances (e.g. `seasonal_naive`) → `NOT_FOUND` (404).

### 2.16 `POST /forecast/scenario` — **STRETCH, optional**
What-if on weather for one target date.
Request: `{"date": "2026-06-12", "model": "lgbm", "temp_delta_c": 2.0}`.
Response: same shape as 2.4 with `scenario: {"temp_delta_c": 2.0}` and no `actual`. Only for models D/B can re-run cheaply (`lgbm`, `linear`). Skip if time-short.

---

## 3. Error format

All errors:
```json
{"error": {"code": "BAD_DATE_RANGE", "message": "'to' must be on or after 'from' and span ≤ 92 days.", "details": {"from": "2026-06-10", "to": "2026-05-01"}}}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `BAD_DATE_RANGE` | Invalid/too-long range, malformed date |
| 400 | `UNKNOWN_MODEL` | Model not in enum or not available |
| 400 | `BAD_PARAMETER` | Invalid enum/number (`risk_quantile`, `horizon_day`, `days`, …) |
| 404 | `DATE_OUT_OF_RANGE` | Date outside the backtest range |
| 404 | `NOT_FOUND` | Valid request, no such artifact/combination |
| 422 | `VALIDATION_ERROR` | Request body failed schema validation (FastAPI default, wrapped in this format) |
| 500 | `INTERNAL_ERROR` | Anything else |

---

## 4. Mock mode & contract tests

- `MOCK=1` makes the API read from a mock artifacts directory (generated by `scripts/make_mock_artifacts.py`) so the UI can be built before real artifacts exist. `GET /health` reports `"mock": true`.
- Mock data must obey every invariant here (quantile ordering, 24/168 point counts, enum values).
- `tests/test_contract.py` calls every endpoint with valid and invalid inputs and validates against the Pydantic models. It must pass with both mock and real artifacts.
- Schema tests for each §1 file live in `tests/test_artifact_schemas.py` and run in `make test`.

---

## 5. Change process

1. Open the change in this file (bump `Version`: patch = clarification, minor = additive, major = breaking).
2. Post it to the team chat with the exact diff.
3. Affected roles update code + tests; D updates mocks.
4. Never change a column/key name silently.

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-11-12 | Initial draft |
| 1.1.0 | 2026-11-12 | Add §1.13 daily_peak_summary.parquet (producer A, consumer B) |
