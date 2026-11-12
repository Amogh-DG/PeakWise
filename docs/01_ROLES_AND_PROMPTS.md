# 04 — Antigravity Prompts, One Per Increment

33 prompts across four people: **BE-1 (10), BE-2 (10), FE-1 (6), FE-2 (7)**.

## How to use

1. Open a fresh Antigravity session. Paste the **shared prompt** (`01_ROLES_AND_PROMPTS.md` §3) once, filling in who you are.
2. Paste **one increment prompt**. The agent does only that increment, reports, and stops.
3. Review using the **Review** line under the prompt. If something's off, paste the error or describe the problem and fix it before moving on.
4. Commit and push on your own branch (`be1/…`, `be2/…`, `fe1/…`, `fe2/…`), open a small PR, then paste the next prompt.
5. If you start a new session mid-way: paste the shared prompt, then tell it *"Read my Progress-log section in README.md, then continue with the next increment below"* and paste the next prompt.

Each prompt is self-contained: it names the files to write and the contract sections to follow. Don't skip numbers; later prompts assume earlier ones are merged. Each one ends with the same **finish line** so the agent stops cleanly:

> When finished: run the tests, update my section of the README Progress log, commit on my branch, and list the files that changed. Then stop — do not start the next increment.

**Needs** = what must already exist (merged to `main`) before you paste that prompt.

---

# BE-1 — Data, Peak & Platform

> Increments 1–3 unblock everyone else. Do them first, keep them simple, and tell the team when each is merged.

### BE-1 · Increment 1 of 10 — Repo scaffold
**Needs:** the three docs in `/docs`.

```
Increment 1 of 10 — repo scaffold.

Create the monorepo structure described in "Folder ownership" and "Repo layout" in docs/01_ROLES_AND_PROMPTS.md. Create:
- All folders (data/raw, data/external, data/processed, src/{data,features,peak,models,backtest,metrics,procurement,analysis}, models, artifacts, artifacts_mock, scripts, api, ui, tests) with .gitkeep where empty.
- Makefile with targets: data, features, backtest, peak, analysis, api, ui, test, all. Targets for things that don't exist yet should print "not implemented yet" and exit 0. `make test` runs pytest. `make api` runs uvicorn on port 8000.
- docker-compose.yml with an `api` service (port 8000) and a `ui` service (port 5173, placeholder for now).
- config.yaml with: timezone Asia/Kolkata, origin_hour_local 10, quantiles [0.05,0.1,0.5,0.9,0.95], peak_threshold_quantile 0.9, backtest {min_train_days: 730, retrain_every_days: 30, test_months: 12}, weather_noise {enabled: true, base_sd_c: 0.5, sd_growth_per_day_c: 0.4}, paths for data/artifacts/artifacts_mock, cdh_base_c 24.
- requirements.txt with pinned versions that install cleanly right now: pandas, numpy, pyarrow, scikit-learn, lightgbm, xgboost, prophet, statsmodels, shap, fastapi, uvicorn, pydantic>=2, pytest, ruff, httpx. Add torch (CPU) as a separate requirements-deep.txt so a heavy install failure doesn't block anyone.
- .gitignore (ignore data/raw, data/processed, models, __pycache__, node_modules, .venv; DO commit artifacts_mock/).
- README.md with: project one-liner, architecture one-liner, "How to run", "How to resume" (for a fresh AI session: read the README Progress log, then docs/), and a "Progress log" with four empty sections: BE-1, BE-2, FE-1, FE-2.
- tests/test_smoke.py that imports the main packages.

Finish: run `make test`, update the BE-1 section of the README Progress log, commit on branch be1/scaffold, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** folder tree matches the layout; `make test` passes; `docker compose config` is valid. Merge to `main` and tell everyone to clone.

### BE-1 · Increment 2 of 10 — Mock data + mock artifacts
**Needs:** Increment 1 merged.

```
Increment 2 of 10 — mock data and mock artifacts. BE-2 and the frontend are blocked on this.

(a) scripts/make_mock_data.py → writes data/processed/load_hourly.parquet and data/processed/features_known.parquet in the EXACT schema of docs/02_API_CONTRACT.md sections 1.1 and 1.2.
Synthetic Delhi-like load, 3 years hourly in Asia/Kolkata, hour-beginning timestamps, complete index:
- winter ~2,000 MW lows, summer peaks up to ~8,300 MW
- morning ramp 6–10, evening peak 19–23
- driven by a synthetic temperature series (annual cycle + daily cycle + noise); load rises with cooling-degree-hours
- weekday/weekend effect, a few festival dips, slow growth trend, a few outage drops flagged is_outage_suspect, a few short gaps imputed with is_imputed=True
Fill every column in contract 1.2 (calendar, festival, event, weather, thermal-inertia, trend).

(b) scripts/make_mock_artifacts.py → writes EVERY artifact in contract section 1.4–1.12 into artifacts_mock/ (NOT artifacts/): predictions_backtest.parquet, peak_predictions.parquet, metrics_accuracy.json, metrics_peak.json, error_heatmap.json, missed_peaks.json, feature_importance.json, procurement_defaults.json, meta.json.
- predictions_backtest: last 12 months of daily origins at 10:00 IST, targets D+1..D+7 (168 hours), models seasonal_naive, linear, lgbm, xgboost, prophet, lstm, ensemble; ensemble best, seasonal_naive worst; error grows with horizon_day; always p05<=p10<=p50<=p90<=p95; include *_raw columns and is_outage_suspect.
- peak_predictions: one row per date per model(at least ensemble), with outcomes covering hit/miss/false_alarm/correct_reject.
- metrics_accuracy: every model × horizon_day (1–7 and "all") × segment (all, 4 seasons, peak_hours, off_peak), computed from the mock predictions, not invented separately.
- metrics_peak: ensemble + one rule baseline; error_heatmap: at least ensemble and seasonal_naive, metrics mape/rmse/bias, horizon_day 1 and "all"; missed_peaks: at least 8 items with tags; feature_importance: lgbm and xgboost; procurement_defaults: da 5000, under 12000, resale 2500 INR/MWh with the disclaimer text from the contract; meta.json per 1.12.
Keep artifacts_mock/ small enough to commit.

(c) tests/test_artifact_schemas.py that validates every file against contract section 1: column names, dtypes, tz-aware timestamps, quantile ordering, enum values, point counts. It must run against artifacts_mock/ now and against artifacts/ later (parametrize by directory).

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/mocks, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** open a parquet in pandas and eyeball it (peaks in the evening, summer > winter); schema tests pass. Merge and tell BE-2 and the frontend pair.

### BE-1 · Increment 3 of 10 — FastAPI on mocks
**Needs:** Increment 2 merged.

```
Increment 3 of 10 — FastAPI backend running on mock artifacts.

Build api/ implementing EVERY endpoint in docs/02_API_CONTRACT.md section 2 (2.1 to 2.16; 2.16 may return 501 for now), prefix /api/v1.
- Pydantic v2 response models that mirror the contract's JSON exactly (field names, nullability, enums).
- Loads artifacts at startup from the directory given by env ARTIFACTS_DIR (default "artifacts"); MOCK=1 makes it use "artifacts_mock" instead. GET /health must report "mock": true/false.
- Derive day-ahead/week-ahead responses from predictions_backtest.parquet (24 or 168 points, at_risk = p90 >= peak_threshold_mw, actual null when missing), peak endpoints from peak_predictions.parquet, and pass-through JSON for metrics, error-heatmap, missed-peaks, feature-importance, meta, procurement defaults.
- POST /procurement/recommend must call src/procurement/advisor.py:recommend(start_date, days, model, risk_quantile, tariff). That module doesn't exist yet: create a stub in src/procurement/advisor.py that returns a contract-shaped response with placeholder numbers, and clearly mark it STUB (FE-1 will replace it).
- Error handling per contract section 3: a unified {"error": {"code","message","details"}} format, including wrapping FastAPI's 422 validation errors.
- CORS enabled for http://localhost:5173.
- tests/test_contract.py: call every endpoint with valid and invalid inputs (bad date, unknown model, out-of-range date, bad risk_quantile) and validate responses against the Pydantic models. It must pass with MOCK=1.
- `make api` starts the server; document the commands in the README.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/api, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** run `MOCK=1 make api`, open `/docs` (Swagger), click through 5 endpoints; contract tests pass. Merge and announce **Checkpoint 0.5**.

### BE-1 · Increment 4 of 10 — Ingest real data
**Needs:** Increment 1 merged. (Can run in parallel with 2–3 if you hit data trouble.)

```
Increment 4 of 10 — ingest real data.

1) src/data/ingest_load.py: load Delhi hourly (or finer) electricity demand from whatever source I provide in data/raw/. I will tell you the source/file. If the data is finer than hourly (e.g. 15-min/5-min), aggregate to hourly mean MW with hour-beginning timestamps in Asia/Kolkata and ALSO save the native-resolution file to data/processed/load_native.parquet for peak-timing analysis. If I haven't provided any load data yet, STOP and give me a short list of exactly where to look (organizer dataset, Delhi SLDC historical demand reports, Grid-India/POSOCO reports, Kaggle) and what columns/format to look for. Do not invent data.
2) src/data/ingest_weather.py: pull hourly weather for Delhi (28.61, 77.21) from the Open-Meteo historical archive API for the same date range: temperature_2m, relative_humidity_2m, dew_point_2m, wind_speed_10m, cloud_cover. Cache raw responses in data/raw/weather/ so reruns don't hit the network. Convert to Asia/Kolkata hour-beginning. If the sandbox can't reach the API, tell me and write the exact curl/python snippet I should run locally.
3) data/raw/README.md recording source, URL, licence, date downloaded, and column meanings.
4) Print a short summary: date range, row counts, % missing, min/max load.
Make target: `make data` runs ingest only for now.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/ingest, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the printed summary looks sane (≥ 2 years, load range plausible). If load data is missing, escalate to the team **now**.

### BE-1 · Increment 5 of 10 — Clean + impute
**Needs:** Increment 4 merged.

```
Increment 5 of 10 — cleaning and imputation.

src/data/clean.py producing data/processed/load_hourly.parquet exactly per docs/02_API_CONTRACT.md section 1.1:
- Reindex to a complete hourly Asia/Kolkata index. IST has no DST, but still detect and report duplicate timestamps, missing hours, and apparent clock shifts in the source; document what you find and how you resolved each.
- Impute gaps: gaps <= 3 hours → linear interpolation (imputation_method="linear"); longer gaps → fill from the same hour-of-week averaged over the nearest 4 non-missing weeks (imputation_method="hour_of_week"). Set is_imputed accordingly.
- Flag suspected outage drops / outliers as is_outage_suspect using a robust z-score (MAD) of the residual versus the hour-of-week median profile; threshold configurable in config.yaml. Do NOT delete or alter these values.
- No NaNs may remain in load_mw.
- Write docs/DATA_QUALITY.md with REAL numbers: total hours, number and length distribution of gaps, % imputed per method, number of flagged outliers with 3 examples, duplicate/clock issues found, and the decisions taken.
- Tests: index complete+unique+monotonic, no NaNs, schema matches contract, imputed flags consistent with method.
`make data` should now run ingest + clean.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/clean, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read `DATA_QUALITY.md` — do the numbers match what you expect from the raw data? Tell BE-2 real data is available.

### BE-1 · Increment 6 of 10 — Known features
**Needs:** Increment 5 merged.

```
Increment 6 of 10 — "known-in-advance" features.

src/features/build_known.py producing data/processed/features_known.parquet with exactly the columns in docs/02_API_CONTRACT.md section 1.2:
- Calendar: hour, dow, month, doy, sin/cos of hour and dow, is_weekend, is_holiday + holiday name (use the `holidays` package for India).
- Festivals: create data/external/festivals.csv with columns date,festival,source_url for Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Independence Day (and others if useful) covering my data range. Use web search to get correct dates and CITE the source URL per row; if you cannot verify a date, flag it in the CSV instead of guessing. Build cal_days_to_*/cal_days_since_* (clipped to ±30) and cal_is_festival_window (±2 days) from it.
- Events: evt_lockdown and evt_odd_even flags. Research the actual date ranges (COVID lockdown phases; Delhi odd-even scheme rounds) with web search, cite sources in data/external/events.csv, and only populate flags for periods inside my data range.
- Weather-derived: wx_* columns from the Open-Meteo data. Heat index via the Rothfusz regression (document the validity range and what you do outside it); wx_cdh = max(temp - cdh_base_c, 0) with base from config.yaml (default 24); wx_cdh_24 = rolling 24h sum; temperature lags 1,3,6,12,24,48,72; rolling mean temp 24h and 72h.
- trend_t = days since first timestamp.
- wx_is_noisy = False for now (noise is added in a later increment).
- Tests: schema matches contract, no NaNs except the first rows lost to lags (drop or document), festival windows look right for Diwali in a known year.
`make features` runs this.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/features, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** spot-check Diwali dates against a calendar; check the odd-even/lockdown dates the agent cited.

### BE-1 · Increment 7 of 10 — AR features + weather noise
**Needs:** Increment 6 merged.

```
Increment 7 of 10 — origin-relative autoregressive features and weather-noise option.

1) src/features/ar_features.py with
   build_ar_features(load_df, origin_ts, target_ts) -> DataFrame
exactly as specified in docs/02_API_CONTRACT.md section 1.3. It must use ONLY load rows with ts < origin_ts. The forecast origin is 10:00 IST on D0, so the last known load is 09:00 D0 and targets start at D+1 00:00. Columns: ar_same_hour_last_week (the value at target_ts minus 7 days *as long as that timestamp is before the origin; otherwise the same hour one more week earlier — document the rule), ar_same_hour_last_known_day, ar_mean_7d, ar_mean_30d, ar_level_365d, ar_last_known_load, ar_last_week_daily_peak, ar_hours_since_last_known.
2) tests/test_leakage.py: for 50 random origins, assert every input timestamp used is < origin_ts (build the function so you can introspect which rows it touched, or test by perturbing load values at/after the origin and asserting outputs don't change). This test is mandatory.
3) Weather noise for day-ahead realism: src/features/weather_noise.py adds Gaussian noise to wx_temp_c (and recomputes dependent wx_* features) whose sd grows with horizon: sd = base_sd_c + sd_growth_per_day_c * horizon_day (values from config.yaml). Provide a function that returns noisy weather features for a given origin and horizon, deterministic given a seed, and sets wx_is_noisy=True. Note that the true weather is still used for the "actual" side of the comparison.
4) Append to docs/ASSUMPTIONS.md: that backtests use observed weather plus horizon-scaled noise as a proxy for archived forecasts, the sd values used, and why.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/ar-features, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** leakage test passes **and** you've read the test to confirm it's meaningful. Tell BE-2 the AR function is ready.

### BE-1 · Increment 8 of 10 — Peak classifier (binary)
**Needs:** Increment 7 merged; BE-2 Increment 4 (LightGBM predictions) preferred, but you can start with BE-2's baselines.

```
Increment 8 of 10 — peak-event classifier (binary), evaluated walk-forward.

src/peak/ — a model that predicts whether a day's peak exceeds the threshold.
- Label: day's max hourly load > threshold, where threshold = the 90th percentile (config peak_threshold_quantile) of DAILY peaks in that fold's TRAINING window only. Add a config flag for a season-relative variant (threshold per season) but default to the global one.
- Use the SAME folds and origins as BE-2's backtest harness (src/backtest/) — import its fold definitions rather than inventing new ones. Walk-forward only.
- Features per target date, all available at the 10:00 IST origin: known features at the daily level (max temp, max CDH, day-of-week, holiday/festival flags, trend), AR features from build_ar_features, and — when available — BE-2's daily forecast summaries from artifacts/predictions_backtest.parquet (daily max of p50 and p90 for the best model).
- Model: LightGBM classifier + isotonic calibration of the probability (calibrate on a held-out window before the test window).
- Decision threshold tuned for RECALL (missing a peak costs more than a false alarm): choose the threshold on a validation window to maximise precision subject to recall >= 0.8 (fallback: maximise F2). Document the trade-off in docs/ASSUMPTIONS.md.
- Rule baseline: "same weekday last week exceeded its threshold".
- Output a first version of artifacts/peak_predictions.parquet per contract section 1.5 (fill pred_peak_hour with argmax of the p50 forecast for now; timing/magnitude fields can come from that) and artifacts/metrics_peak.json per section 1.7 with precision, recall, F1, PR-AUC, confusion matrix for classifier and rule baseline.
- Tests: no threshold computed with test-fold data; label/threshold logic on a toy example.
`make peak` runs this.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/peak-binary, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** precision/recall for classifier vs rule baseline — is the classifier clearly better? Is the threshold per fold only from training data?

### BE-1 · Increment 9 of 10 — Peak hour + timing/magnitude
**Needs:** Increment 8 merged.

```
Increment 9 of 10 — peak hour prediction, timing error and magnitude error.

Extend src/peak/:
- Peak-hour model: LightGBM multiclass over 24 hours (predict which hour-beginning holds the daily max). Baseline: argmax of the best forecaster's p50 by hour. Use the classifier's probabilities/top-1 and also report top-2 hit rate.
- Fill the remaining fields of artifacts/peak_predictions.parquet per contract section 1.5: pred_peak_hour, pred_peak_ts, pred_peak_mw_p10/p50/p90 (daily max from the forecast quantiles — document how you combine hourly quantiles into a daily max, e.g. max of each quantile series), actual_peak_ts, actual_peak_mw, actual_is_peak, timing_error_min (signed, predicted minus actual; if data/processed/load_native.parquet exists, measure the actual peak time at native resolution), magnitude_error_mw (predicted p50 daily max minus actual), and outcome (hit/miss/false_alarm/correct_reject).
- Extend artifacts/metrics_peak.json with timing_mae_min, timing_within_1h_pct, magnitude_mae_mw, magnitude_bias_mw for classifier and baselines.
- Tests: outcome labels on a toy confusion example; timing error sign convention.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/peak-hour, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** timing error distribution (most days within ±1 h?); `outcome` counts add up to the number of days. Tell FE-2 the peak file is final.

### BE-1 · Increment 10 of 10 — Real artifacts, meta, Docker, deploy
**Needs:** Increments 1–9 merged; BE-2 and FE-2 artifacts present in `artifacts/`.

```
Increment 10 of 10 — switch to real artifacts, assemble meta, containerize and prepare for deploy.

1) Assemble artifacts/meta.json per docs/02_API_CONTRACT.md section 1.12 from the real data and backtest (data_range, backtest_range, latest peak threshold, models actually present, season/peak-hour definitions, weather_proxy_note).
2) Run the API with MOCK unset against artifacts/. Fix any mismatch between real artifacts and the Pydantic models by fixing the PRODUCER side where possible: report schema deviations to me instead of loosening the models. Make tests/test_contract.py and tests/test_artifact_schemas.py pass against BOTH artifacts_mock/ and artifacts/.
3) Dockerfiles for api and ui; docker-compose up must serve API on 8000 and UI on 5173 (serve the built UI). Include artifacts/ via a volume or copy. Add a healthcheck on /api/v1/health.
4) `make all` runs data → features → backtest → peak → analysis in order (skip steps whose target is not implemented, with a clear message).
5) Prepare deployment notes in README.md for Render/Railway (or similar): build/start commands, env vars, how to upload artifacts. Do not deploy without me.
6) Fresh-clone test: in a clean directory, clone, install, run `make test` and `docker compose up`, and report what failed.
7) Add the final submission checklist from docs/03_PRD.md section 12 to the README with checkboxes.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/finalize, and list the files that changed. Then stop.
```
**Review:** `docker compose up` on a machine that has never seen the repo.

---

# BE-2 — Modeling & Backtest

> Start as soon as BE-1's Increment 2 (mock data) is merged. Switch to real data after BE-1's Increment 5.

### BE-2 · Increment 1 of 10 — Backtest harness
**Needs:** BE-1 Increments 1–2 merged.

```
Increment 1 of 10 — rolling-origin backtest harness.

Build src/backtest/ using data/processed/load_hourly.parquet and features_known.parquet (BE-1's mock data is fine for now).
- Protocol (frozen, see docs/03_PRD.md section 9): origin = 10:00 IST every day; targets D+1 00:00 … D+7 23:00 (horizon_h 14–181; horizon_day 1–7); expanding training window; min train = config backtest.min_train_days; retrain every config backtest.retrain_every_days (a fold = one retrain period of consecutive origins); test = last config backtest.test_months months (or all remaining data after min-train).
- A Forecaster Protocol:
    class Forecaster(Protocol):
        name: str
        def fit(self, train_end: pd.Timestamp) -> None: ...
        def predict(self, origin: pd.Timestamp) -> pd.DataFrame  # columns: target_ts, horizon_h, horizon_day, p05, p10, p50, p90, p95
  predict may only use data with ts < origin (autoregressive via src/features/ar_features.build_ar_features when it exists; until then use a simple stand-in and mark it TODO).
- A runner that, for each fold, fits a forecaster at train_end, predicts all origins in the fold, joins y_true and is_outage_suspect, and appends to artifacts/predictions_backtest.parquet with the exact columns of docs/02_API_CONTRACT.md section 1.4 (fill *_raw = same as final for now; fold_id; model name).
- Make the runner skip models/folds already computed (resume) and show a progress bar.
- A trivial "persistence" forecaster to prove the harness end to end.
- Tests: no training row at or after train_end; no feature row at or after origin; output schema matches contract; 100% of targets covered once per model/origin.
`make backtest` runs the registered models.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/harness, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** row counts = origins × 168 per model; walk through one fold's train_end vs first origin.

### BE-2 · Increment 2 of 10 — Baselines
**Needs:** Increment 1 merged.

```
Increment 2 of 10 — baselines. Register both in the harness.

1) src/models/seasonal_naive.py: for each target hour, use the actual load at the same hour-of-week 7 days earlier if that timestamp is before the origin; otherwise step back by additional 7-day multiples until it is (document this rule — for D+2..D+7 targets it will step back further). Quantiles: add residual quantiles by hour-of-day computed ONLY from the training window (residual = actual − naive prediction), so p05..p95 are naive + residual quantiles.
2) src/models/linear.py: scikit-learn LinearRegression on known features (calendar one-hots/sin-cos, wx_cdh_24, wx_heat_index_c, temperature lags/rolling means, festival/event flags, trend_t) plus AR features and horizon_h. Quantiles via residual quantiles by hour-of-day from the training window.
3) Run both through the harness and write predictions for names "seasonal_naive" and "linear". Print mean RMSE and MAPE per horizon_day for each.
4) Sort quantiles per row so p05<=p10<=p50<=p90<=p95.
5) Tests: seasonal-naive never uses data at or after the origin; quantile ordering.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/baselines, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** baseline RMSE by horizon-day — seasonal-naive should degrade as horizon grows; linear should beat it.

### BE-2 · Increment 3 of 10 — Metrics library
**Needs:** Increment 2 merged.

```
Increment 3 of 10 — metrics library and accuracy table.

src/metrics/ with pure functions plus a table builder:
- mape (percent; document the weakness at low loads and guard against zero), rmse, mae, bias (mean of prediction − actual), pinball loss per quantile and mean over the five quantiles, picp for the 80% interval (p10–p90) and the 90% interval (p05–p95), mpiw_80, and % improvement vs seasonal_naive for mape and rmse.
- Segments: all, winter, summer, monsoon, post_monsoon (month definitions in docs/02_API_CONTRACT.md section 0), peak_hours (hour-beginning 6,7,8,9,10,19,20,21,22,23) and off_peak.
- build_accuracy_table(predictions_df) → rows for every model × horizon_day (1–7 and "all") × segment, written to artifacts/metrics_accuracy.json exactly per contract section 1.6 (mape in percent, picp as fraction, improvement null for the baseline itself).
- Exclude nothing silently: report is_outage_suspect rows as part of "all" but also expose a flag to compute metrics without them.
- Tests: hand-computed toy examples for each metric; improvement of the baseline vs itself is null.
- Print a compact table (model × horizon_day for segment=all, plus peak_hours) to the console.
`make backtest` ends by writing metrics.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/metrics, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** FE-2 can now build the Accuracy page on real baseline numbers.

### BE-2 · Increment 4 of 10 — LightGBM quantile
**Needs:** Increment 3 merged; BE-1 Increment 7 (AR features) merged.

```
Increment 4 of 10 — LightGBM quantile forecaster (main model).

src/models/lgbm_quantile.py registered as "lgbm":
- One LightGBM model per quantile q ∈ {0.05, 0.1, 0.5, 0.9, 0.95} with objective="quantile".
- Training table: for each training origin and each target hour in D+1..D+7, features = known features at target_ts (with weather noise via BE-1's weather_noise when enabled) + build_ar_features(load_df, origin, target) + horizon_h (as a feature). Subsample origins if training is too slow (e.g., every 2nd origin) and note it in config.
- Zero sample weight for is_outage_suspect rows in training; they stay in evaluation.
- Sort the five quantile predictions per row to prevent crossing.
- Fixed seeds; hyperparameters in config.yaml (modest defaults: num_leaves 63, learning_rate 0.05, n_estimators ~500 with early stopping on a validation slice taken from the END of the training window).
- Register in the harness, run the backtest, and print the accuracy table including improvement vs seasonal_naive for segment=all and peak_hours.
- Tests: no future leakage via the existing harness tests; quantile ordering; deterministic with a fixed seed.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/lgbm, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** does lgbm beat seasonal_naive and linear **at peak_hours**, not just on average? If not, tell the team before continuing.

### BE-2 · Increment 5 of 10 — Conformal calibration
**Needs:** Increment 4 merged.

```
Increment 5 of 10 — interval calibration with conformalized quantile regression (CQR).

Implement src/models/calibration.py:
- For each fold, use a rolling calibration window that ENDS BEFORE the fold's first test origin (e.g., the last 90 days of the training period, predicted out-of-sample by a model fit before that window). Compute conformity scores per (horizon_day, hour-of-day group or peak/off-peak) and adjust the 80% interval (p10, p90) and the 90% interval (p05, p95) so the coverage targets are 0.80 and 0.90. Keep the median unchanged.
- Preserve quantile ordering after adjustment.
- Update the harness output so p05..p95 are the CALIBRATED values and p05_raw..p95_raw keep the pre-calibration values, per contract section 1.4.
- Apply it to "lgbm" (and make it reusable for other models).
- Extend metrics output: keep picp_80, picp_90, mpiw_80 on the calibrated values and ADD a small extra table to artifacts/metrics_accuracy.json under key "calibration_comparison" with picp/mpiw before vs after for each calibrated model and horizon_day.
- Tests: calibration window never overlaps test origins; ordering preserved; coverage on a synthetic example moves toward target.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/calibration, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** PICP for 80% should be ~0.80 and 90% ~0.90 (within a few points); intervals shouldn't have exploded in width (check MPIW).

### BE-2 · Increment 6 of 10 — Daily-peak summaries for BE-1
**Needs:** Increment 5 merged.

```
Increment 6 of 10 — export daily forecast summaries for the peak classifier.

1) Propose and implement artifacts/daily_peak_summary.parquet, one row per (model, origin_ts, date): columns model, origin_ts, date, horizon_day, daily_max_p10, daily_max_p50, daily_max_p90 (max over the day's 24 hourly values of each quantile series — document this choice), argmax_hour_p50, daily_min_p50, y_true_daily_max (null if unobserved).
2) Add this as a new section 1.13 in docs/02_API_CONTRACT.md (producer BE-2, consumer BE-1) and add a row to the change log. Make it a minimal additive change; do not touch other sections.
3) Add a schema test to tests/test_artifact_schemas.py (BE-1 owns that file: add the test in a new file tests/test_daily_peak_summary.py instead).
4) Generate it for all models in the backtest and print the first 5 rows for "lgbm".
Tell me the exact path and columns so I can message BE-1.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/daily-summary, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** message BE-1 the path and columns.

### BE-2 · Increment 7 of 10 — Prophet + XGBoost
**Needs:** Increment 5 merged.

```
Increment 7 of 10 — Prophet and XGBoost comparison models.

1) src/models/prophet_model.py registered as "prophet": holiday-aware (build the holidays dataframe from data/external/festivals.csv plus the India public holidays), temperature (wx_temp_c or wx_cdh_24) as an extra regressor using noisy weather for future targets when enabled, daily/weekly/yearly seasonality. Prophet is slow: train one model per fold on hourly data or on a reduced set if needed, document how. Quantiles from Prophet's uncertainty interval where reasonable (interval_width 0.9 → p05/p95, 0.8 → p10/p90), otherwise from residual quantiles by hour; document which.
2) src/models/xgboost_model.py registered as "xgboost": same training table and design as lgbm but with XGBoost quantile objective (reg:quantileerror). 
3) Apply the same CQR calibration to both; keep raw columns.
4) Run the backtest for both and print the updated accuracy table. Time-box: if Prophet is too slow to backtest at the full fold count, backtest it on every 7th origin and state this clearly in the README and docs/ASSUMPTIONS.md.
5) Tests: registration works, output schema valid, quantile ordering.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/prophet-xgb, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** Prophet runtime acceptable; results plausible (Prophet typically weaker on peaks — that's a fine finding).

### BE-2 · Increment 8 of 10 — LSTM (deep model)
**Needs:** Increment 5 merged; `pip install -r requirements-deep.txt` works.

```
Increment 8 of 10 — one deep model, time-boxed. Keep it simple.

src/models/lstm_model.py registered as "lstm" (PyTorch, CPU is fine):
- Input: last 168 hours of [load_mw, wx_temp_c, wx_cdh, cal_hour_sin/cos, cal_dow_sin/cos, cal_is_holiday] up to the origin; plus known future features for the target horizon (temperature with noise, calendar, festival flags) as a decoder-side input, OR a simpler design: LSTM encoder → MLP head that outputs all 168 horizons × 5 quantiles at once. Choose the simpler one that trains fast.
- Loss: pinball (quantile) loss summed over the five quantiles; scale inputs/targets using training-window statistics only.
- Retrain per fold (or fewer folds, e.g. every 3rd retrain period, reusing the last model in between — document it), early stopping on the END of the training window, fixed seeds, max ~10 minutes total backtest budget.
- Sort quantiles to avoid crossing; apply CQR calibration; keep raw columns.
- Print the updated accuracy table. If it doesn't beat lgbm, keep it anyway as a documented comparison.
- Tests: forward-pass shapes; quantile ordering; no future data in an input window.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/lstm, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** training finished within budget; loss curve not diverging.

### BE-2 · Increment 9 of 10 — Ensemble
**Needs:** Increments 4, 7, 8 merged.

```
Increment 9 of 10 — ensemble.

src/models/ensemble.py registered as "ensemble":
- Combine the available base models (lgbm, xgboost, prophet, lstm, and optionally linear) by a weighted average of each quantile series (quantile averaging / Vincentization).
- Fit the weights per horizon_day on a VALIDATION window that ends before the test window of each fold (e.g., minimise pinball loss, weights ≥ 0 summing to 1, via scipy.optimize or a simple grid). Never fit weights on test origins.
- Because base models are calibrated individually, recalibrate the ensemble with CQR at the end and keep raw columns.
- Write predictions for model "ensemble" and print the complete accuracy table: every model × horizon_day for segment=all and peak_hours, with improvement vs seasonal_naive; also print the learned weights.
- Tests: weights non-negative and sum to 1; validation window precedes test window; ordering preserved.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/ensemble, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** ensemble ≥ best single model on pinball; PICP still on target. Tell BE-1 and FE-2 `ensemble` is available.

### BE-2 · Increment 10 of 10 — Feature importance
**Needs:** Increment 4 merged.

```
Increment 10 of 10 — feature importance.

- Compute SHAP values (TreeExplainer) for the p50 LightGBM model on a sample of the latest fold's test rows (e.g. 5,000 rows) and mean(|SHAP|) per feature; also compute LightGBM gain importance as a cross-check. Do the same for XGBoost if time allows.
- Write artifacts/feature_importance.json per docs/02_API_CONTRACT.md section 1.10: importance normalised to sum to 1 per model, group in {calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon}. Map each feature name to its group with a single mapping dict in src/models/feature_groups.py.
- Also write artifacts/feature_importance_by_segment.json with the top 10 features for peak_hours vs off_peak (extra, not in the contract: put it under a clearly named key and tell me so I can add it to the contract if useful).
- Tests: normalisation sums to 1; every feature has a group.
- Update README: a short "Results" table (model × D+1 and D+7, RMSE and MAPE, segment all and peak_hours, % improvement vs seasonal-naive, PICP 80/90) copied from the real artifacts.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/importance, and list the files that changed. Then stop.
```
**Review:** top features look physically sensible (CDH/temperature, same-hour-last-week, hour). Tell FE-2 the file is ready.

---

# FE-1 — Forecast & Procurement UI

### FE-1 · Increment 1 of 6 — UI shell
**Needs:** BE-1 Increments 1–3 merged (mock API running). Until then use the response examples in `02_API_CONTRACT.md`.

```
Increment 1 of 6 — UI shell. FE-2 builds on this, so keep it clean and merge it early.

In ui/, create a Vite + React + TypeScript (strict) + Tailwind + Plotly.js (react-plotly.js or plotly.js-dist-min via a thin wrapper) app.
- Routing for six pages with placeholder content: /forecast, /accuracy, /errors, /missed-peaks, /procurement, /insights; a top nav; a default redirect to /forecast.
- Theme: colour-blind-safe palette defined once as CSS variables/Tailwind tokens (one colour per model, band colours for P10–P90 and P05–P95, actual line, peak marker, at-risk shading); light and dark ok but not required.
- ui/src/api/: a typed client matching docs/02_API_CONTRACT.md section 2 — TypeScript types for every response, one function per endpoint, base URL from VITE_API_BASE (default http://localhost:8000/api/v1), and a uniform error type from the contract's error format.
- ui/src/components/shared/: ChartCard (title, subtitle, units, loading/error/empty states), ModelSelect (models from GET /models; default "ensemble"), DatePicker (constrained to meta.backtest_range), StatTile, and a Plotly wrapper that handles resize and theme.
- A global "mock mode" banner when GET /health says mock=true.
- Add a tiny README section "How to run the UI" and a `make ui` target that runs the dev server. Update the Dockerfile placeholder if BE-1 created one, but don't deploy.
- Only use files under ui/; FE-2 owns ui/src/pages/{Accuracy,ErrorHeatmap,MissedPeaks,Insights} and ui/src/components/eval/, so create those placeholder page files and leave them minimal.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/shell, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** `npm run dev`, click all six nav links; no console errors. Merge immediately and tell FE-2.

### FE-1 · Increment 2 of 6 — Forecast page
**Needs:** Increment 1 merged; mock API running.

```
Increment 2 of 6 — Forecast page (ui/src/pages/Forecast).

- Controls: DatePicker, a Day-ahead / Week-ahead toggle, ModelSelect. Support URL query ?date=YYYY-MM-DD&model=...&view=day|week so other pages can deep-link here (FE-2's missed-peak drill-down will link with ?date=).
- Data: GET /forecast/day-ahead or /forecast/week-ahead, and GET /peak/day for the peak card.
- Chart (Plotly): actual line; shaded P10–P90 band; lighter P05–P95 band; P50 line; predicted peak marker (from the response's peak.predicted_peak_ts / mw) and actual peak marker; horizontal dashed line at peak_threshold_mw; at-risk hours (at_risk=true) shaded as vertical bands. In week view show all 168 hours with day separators.
- Peak card beside the chart: peak probability badge, predicted peak hour and MW range (p10/p50/p90), actual peak if known, outcome (hit / miss / false alarm / correct reject) with a colour and plain-language text, timing error in minutes and magnitude error in MW.
- A short legend explaining: P10–P90 is an 80% interval, P05–P95 a 90% interval.
- Handle loading/empty/error states (e.g. DATE_OUT_OF_RANGE → friendly message).
- Hover tooltip shows ts, p05..p95, actual.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/forecast, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** switch date, day↔week, model; check the legend wording; check the peak card for a "miss" day.

### FE-1 · Increment 3 of 6 — Procurement advisor (Python)
**Needs:** BE-1 Increment 3 merged (stub exists); BE-2 baselines/lgbm predictions available (mock is fine).

```
Increment 3 of 6 — procurement advisor logic. Replace the STUB BE-1 created.

Implement src/procurement/advisor.py: recommend(start_date, days, model, risk_quantile, tariff) -> dict, returning EXACTLY the response shape in docs/02_API_CONTRACT.md section 2.12.
- Load forecasts from artifacts/predictions_backtest.parquet (directory from env ARTIFACTS_DIR, default "artifacts"; MOCK=1 → "artifacts_mock"), horizon_day=1 forecasts for each target date in [start_date, start_date+days) so the schedule is a true day-ahead schedule (origin 10:00 on D−1), and also the p50/p90 columns.
- risk_quantile: a number in [0.5, 0.99] or "newsvendor". newsvendor quantile = (under_price − da_price) / (under_price − resale_price); set risk_quantile_source accordingly. Use the nearest available quantile column (p50, p90, p95) by linear interpolation between available quantiles; document it.
- scheduled_mw per hour = the chosen quantile of the forecast.
- Cost per hour = da_price·S + under_price·max(D−S,0) − resale_price·max(S−D,0) with D = actual load when available.
- Baselines: flat at the previous week's mean MW; also flat at the previous week's peak MW (flat_peak_cost_inr). If there is no previous week in the data, say so in a clear error.
- p90_risk_exposure_inr = cost with D = p90 path minus cost with D = p50 path, same schedule.
- at_risk_hours = hours where p90 >= the latest peak threshold from meta.json (or peak_predictions.parquet).
- If actuals are missing for some hours, set the realised cost fields to null per the contract and still return p90_risk_exposure_inr.
- by_day breakdown per the contract.
- artifacts/procurement_defaults.json per section 1.11 with da 5000, under 12000, resale 2500 INR/MWh and the disclaimer; append the reasoning and the "illustrative placeholder" caveat to docs/ASSUMPTIONS.md.
- Validate inputs (days 1–7, tariff ordering under > da > resale, risk_quantile range) and raise clear ValueErrors that BE-1's API maps to BAD_PARAMETER.
- Unit tests with hand-computed numbers: a 3-hour toy example for cost, newsvendor quantile = 0.7368 for the defaults, exposure sign.
Tell me when it's importable so I can ask BE-1 to remove the stub.

Finish: run `make test`, update the FE-1 Progress log, commit on branch fe1/advisor, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** hand-check one hour of cost; newsvendor ≈ 0.737 for the default tariff. Tell BE-1.

### FE-1 · Increment 4 of 6 — Procurement page
**Needs:** Increments 2–3 merged; BE-1 API using the real advisor.

```
Increment 4 of 6 — Procurement page (ui/src/pages/Procurement).

- Controls: week picker (start date, days 1–7), ModelSelect, risk-quantile slider (0.50–0.99, step 0.01) with a checkbox/preset "Use newsvendor" (shows the computed quantile from the response), and an editable tariff form (da_price, under_price, resale_price) prefilled from GET /procurement/defaults with a visible "illustrative placeholder" note and a Reset button. Validate under > da > resale before submitting.
- Call POST /procurement/recommend on change (debounced) and show results:
  1) schedule chart: scheduled MW vs p50, p90, flat baseline and actual (if present); at-risk hours shaded;
  2) KPI tiles: cost, flat cost, savings (INR and %), P90 risk exposure, under/over-procured hours;
  3) per-day table from by_day;
  4) a "cost vs risk quantile" curve: call the endpoint for q ∈ {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99} (in parallel) and plot realised cost (or exposure when cost is null) with the current q and the newsvendor q marked.
- Format INR with Indian digit grouping and units (₹ crore/lakh with a toggle to full numbers).
- Loading/empty/error states, including BAD_PARAMETER messages.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/procurement, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** move the slider — does the cost curve have a sensible minimum? Try an extreme tariff.

### FE-1 · Increment 5 of 6 — Real artifacts + polish
**Needs:** BE-1 Increment 10 (real artifacts served) or at least real predictions in `artifacts/`.

```
Increment 5 of 6 — switch to real artifacts and polish.

- Point the UI at the API running WITHOUT MOCK (real artifacts). Fix any crashes caused by real data differences (missing actuals at the edges, date ranges, models absent). Don't change the contract: if the API's output deviates from docs/02_API_CONTRACT.md, tell me so I can raise it with the owner.
- Polish: responsive layout (laptop and a phone-width sanity check), consistent chart heights, axis units on every chart (MW, ₹), keyboard-focusable controls, aria-labels on icon buttons, meaningful chart titles/subtitles, no layout jump while loading (skeletons).
- Add a small "About these numbers" popover on Forecast and Procurement: weather-proxy caveat and tariff-placeholder caveat (read the text from meta.weather_proxy_note and procurement defaults).
- Production build works via `npm run build` and the nginx/static serve used by BE-1's docker setup; fix any base-path issues.
- Take screenshots of the Forecast and Procurement pages (desktop) into docs/screenshots/ for the README and submission.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/polish, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** use the app like a judge would for 5 minutes; fix anything confusing.

### FE-1 · Increment 6 of 6 — Procurement memo + demo script
**Needs:** Increment 5 merged; real procurement results available.

```
Increment 6 of 6 — documents.

1) docs/PROCUREMENT_MEMO.md: pick a sample week from the backtest that includes at least one peak-risk day (explain why you picked it). Use src/procurement/advisor.py with the real ensemble forecasts to produce: the recommended hourly day-ahead schedule (include a compact daily summary table and a chart image saved to docs/figures/), P90 risk exposure, at-risk hours, simulated cost vs both naive flat schedules, savings in INR and %, and sensitivity to the risk quantile (a small table for q = 0.5, 0.7, 0.9, 0.99 and the newsvendor q). State clearly that tariffs are illustrative placeholders. Use REAL numbers only; write a script scripts/make_procurement_memo.py that regenerates the figures and the numbers section so it is reproducible.
2) docs/DEMO_SCRIPT.md: a 3-minute demo story: (1) the problem (tail risk at peaks, not just the average); (2) Forecast page on a hot day with the P90 band and at-risk hours; (3) peak classifier outcome; (4) Accuracy table vs baselines at peak hours; (5) a missed peak and why; (6) Procurement: schedule, exposure, savings; (7) one-sentence limitations (weather proxy, placeholder tariffs). Include exact URLs/clicks, what to say, and a fallback if the live demo fails (screenshots in docs/screenshots/).

Finish: update the FE-1 Progress log, commit on branch fe1/docs, and list the files that changed. Then stop.
```
**Review:** read the memo as if you were the planner — would you trust it? Time the demo script out loud.

---

# FE-2 — Evaluation & Insights UI

> Start with the Python analysis (Increments 1–2) while FE-1 builds the shell; then build pages on the merged shell.

### FE-2 · Increment 1 of 7 — Error decomposition + heatmap JSON
**Needs:** BE-1 Increments 1–2 merged (mock artifacts). Later runs on real predictions after BE-2 Increment 4+.

```
Increment 1 of 7 — error decomposition and heatmap artifact.

src/analysis/ (read BE-2's metric functions from src/metrics/ if they exist; otherwise write small local versions and switch later):
- error_decomposition.py: from artifacts/predictions_backtest.parquet compute error metrics by season × hour-of-day, peak vs off-peak, and horizon_day, per model.
- artifacts/error_heatmap.json exactly per docs/02_API_CONTRACT.md section 1.8: one entry per model × metric (mape, rmse, bias) × horizon_day (1 and "all" at minimum, 1–7 if cheap), with hours [0..23], seasons ["winter","summer","monsoon","post_monsoon"], values[season][hour], counts[season][hour]. Cells with fewer than 5 observations should be null.
- Support reading from artifacts_mock/ via env MOCK=1 (default ARTIFACTS_DIR=artifacts) so it works on mock data now and on real data later.
- Tests: hand-computed toy example; shape of values/counts is 4×24; season mapping per the contract.
- `make analysis` runs this.

Finish: run `make test`, update the FE-2 Progress log, commit on branch fe2/error-decomp, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** heatmap values higher at peak hours/summer for the mock? (Real data later.)

### FE-2 · Increment 2 of 7 — Missed-peak analysis
**Needs:** Increment 1 merged; `peak_predictions.parquet` exists (mock now; real after BE-1 Increment 9).

```
Increment 2 of 7 — missed-peak analysis.

src/analysis/missed_peaks.py reading artifacts/peak_predictions.parquet (+ load_hourly.parquet and features_known.parquet) and writing artifacts/missed_peaks.json exactly per docs/02_API_CONTRACT.md section 1.9.
- Include every day with outcome == "miss" for each model (default focus: ensemble), sorted by absolute magnitude_error_mw descending.
- Auto-tag each day with rules (document thresholds in docs/ASSUMPTIONS.md): "festival" (cal_is_festival_window), "holiday" (cal_is_holiday), "heatwave" (max wx_temp_c that day above the 95th percentile of that season's daily max temps from the training period), "weather_miss" (actual daily max temperature differs from the weather proxy used for the forecast by > 2 °C; if not computable, omit this tag), "weekend", else "other".
- Write a one-line "note" per item generated from the tags and numbers (e.g. "Actual max temp 3.1 °C above the weather proxy; peak shifted 7 h later than predicted"). Notes must come from the data, never invented.
- Tests: sorting, tag rules on toy rows, note contains the right numbers.
`make analysis` now runs Increments 1 and 2.

Finish: run `make test`, update the FE-2 Progress log, commit on branch fe2/missed-peaks, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read five notes — do they make sense given the numbers?

### FE-2 · Increment 3 of 7 — Accuracy page
**Needs:** FE-1 Increment 1 (shell) merged; mock API running.

```
Increment 3 of 7 — Accuracy page (ui/src/pages/Accuracy). Only edit ui/src/pages/Accuracy and ui/src/components/eval/.

- Data: GET /backtest/metrics (all rows) and GET /backtest/peak-metrics.
- Controls: segment dropdown (all, winter, summer, monsoon, post_monsoon, peak_hours, off_peak) and a metric toggle (MAPE / RMSE / MAE / bias / pinball).
- Main table: rows = models, columns = horizon_day 1…7 and "all", cell = chosen metric; below each cell (or in a second table) the % improvement vs seasonal-naive with green/red colouring (baseline row shows "—"). Highlight the best model per column. Sticky header and first column; sortable.
- Calibration table: picp_80 and picp_90 per model and horizon_day with a visual marker against the 0.80 / 0.90 targets, plus mpiw_80_mw. Label clearly: P10–P90 = 80% interval, P05–P95 = 90% interval. If calibration_comparison exists in the metrics JSON, show before vs after.
- Peak events card: precision, recall, F1, PR-AUC, confusion matrix (2×2), timing MAE, % within ±1 h, magnitude MAE/bias — for the classifier vs the rule baseline side by side.
- A small note about MAPE's weakness at low loads (winter nights) near the MAPE toggle.
- Loading/empty/error states.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/accuracy, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** numbers match what BE-2 printed in the console for the same segment.

### FE-2 · Increment 4 of 7 — Error heatmap page
**Needs:** Increments 1 and 3 merged.

```
Increment 4 of 7 — Error heatmap page (ui/src/pages/ErrorHeatmap). Only edit ui/src/pages/ErrorHeatmap and ui/src/components/eval/.

- Data: GET /backtest/error-heatmap?model=&metric=&horizon_day=.
- Controls: ModelSelect, metric toggle (MAPE / RMSE / bias), horizon-day select (1 … 7, All).
- Plotly heatmap: x = hour of day (0–23), y = season (winter, summer, monsoon, post_monsoon); colour scale sequential for mape/rmse, diverging centred at 0 for bias; colour bar with units; hover shows value, observation count and the hour range; null cells shown as hatched/grey with "too few observations".
- Highlight the peak-hour columns (6–10 and 19–23) with subtle outlines or a band above the plot.
- Under the chart, auto-generated plain-language callouts computed from the data: "worst cell", "best cell", and whether peak hours are worse than off-peak on average (percentage difference).
- Optional compare mode: show two models side by side (e.g. ensemble vs seasonal_naive) with a shared colour scale.
- Loading/empty/error states (NOT_FOUND → friendly message).

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/heatmap, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** diverging bias colours centred on 0; callouts match the grid.

### FE-2 · Increment 5 of 7 — Missed peaks page
**Needs:** Increments 2 and 3 merged; FE-1 Increment 2 (Forecast page with ?date=) merged.

```
Increment 5 of 7 — Missed peaks page (ui/src/pages/MissedPeaks). Only edit ui/src/pages/MissedPeaks and ui/src/components/eval/.

- Data: GET /backtest/missed-peaks (paginate with limit/offset) and GET /peak/events?outcome=false_alarm for a secondary tab.
- Controls: ModelSelect, tag filter chips (festival, holiday, heatwave, weather_miss, weekend, other; multi-select), and a toggle "Misses / False alarms".
- Table: date, season, peak probability, predicted vs actual peak time, predicted p50 vs actual MW, magnitude error (MW, coloured), timing error (minutes), tag chips, note. Sort by magnitude error by default; sortable columns.
- Summary strip above the table: number of missed peaks, share by tag, mean magnitude error.
- Row click → drill-down panel (drawer or inline) that embeds a compact version of the day chart (call GET /forecast/day-ahead?date=… and plot actual line + P10–P90 + P05–P95 + predicted vs actual peak marker) and a "Open in Forecast page" button linking to /forecast?date=YYYY-MM-DD&model=…
- Empty state for "no misses" and for filters with no results.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/missed-peaks-ui, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** click three rows including one with `null` actuals; the Forecast link opens the right day.

### FE-2 · Increment 6 of 7 — Insights page
**Needs:** BE-2 Increment 10 (feature importance) merged or mock available; Increment 7 can run after.

```
Increment 6 of 7 — Insights page (ui/src/pages/Insights). Only edit ui/src/pages/Insights and ui/src/components/eval/.

- Data: GET /models, GET /models/{model}/feature-importance?top=20, GET /meta.
- Section 1 — "What drives the forecast": horizontal bar chart of the top 20 features for the selected model (ModelSelect limited to models with importances), bars coloured by feature group (calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon) with a legend, plus a grouped summary (share of total importance per group).
- Section 2 — "Why peaks are hard": render docs/WHY_PEAKS_ARE_HARD.md as formatted text with its figures. Since the UI can't read repo files directly, copy the markdown and figure PNGs at build time into ui/public/insights/ via a small script (scripts/sync_insights.sh) and fetch them as static assets; show a friendly placeholder if the file doesn't exist yet.
- Section 3 — "Model card summary": render the first sections (assumptions, known limits) from docs/MODEL_CARD.md the same way, plus key facts from /meta (data range, backtest range, weather_proxy_note).
- Loading/empty/error states.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/insights, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the page doesn't crash when the markdown files don't exist yet.

### FE-2 · Increment 7 of 7 — Model card + "why peaks are hard"
**Needs:** BE-2 Increment 9 (ensemble) and BE-1 Increment 9 (final peak file) merged; real artifacts available.

```
Increment 7 of 7 — the two analysis documents, with REAL numbers from the backtest.

1) docs/WHY_PEAKS_ARE_HARD.md. Add scripts/make_peak_analysis.py that produces reproducible figures into docs/figures/ and prints the numbers used:
 - Weather sensitivity: MW change per +1 °C in daily max temperature (or CDH) on peak-hour load, by season, estimated from the data (e.g. a simple regression with calendar controls); show a scatter with fit.
 - Thermal inertia: correlation of evening-peak load with temperature at lags 0, 3, 6, 12, 24, 48, 72 h (and rolling 24h/72h means), shown as a bar chart; explain what it means for peaks shifting late on hot days.
 - Festival/holiday effects: average load deviation (vs a same-weekday, same-month baseline) in Diwali/Holi/Eid windows compared with normal days, with sample sizes and a caution when n is small.
 - Error evidence: how forecast error at peak_hours compares with off_peak for the ensemble and the baseline (use metrics_accuracy.json) and 2–3 missed-peak case studies from missed_peaks.json.
 Keep it to ~1.5 pages. Every number and figure must be generated by the script; no invented claims; state limits (weather proxy, short samples).
2) docs/MODEL_CARD.md: intended use; data (source, range, imputation summary from docs/DATA_QUALITY.md); features; models and how they were trained; backtest protocol (frozen, from docs/03_PRD.md section 9); results summary table (ensemble vs baselines at D+1 and D+7, all vs peak_hours, PICP 80/90); peak classifier results; limitations and known failure modes (weather proxy, festival data sparsity, structural changes, outage effects, tariff placeholders); ethical/operational notes (decision support, not automated dispatch). Link to the generated figures and artifacts.
3) Run scripts/sync_insights.sh if it exists so the UI picks up the new files.

Finish: update the FE-2 Progress log, commit on branch fe2/docs, and list the files that changed. Then stop.
```
**Review:** every number in the docs traces to a file in `artifacts/` or a printed script output. Run the script again and confirm the figures regenerate identically.# 04 — Antigravity Prompts, One Per Increment

33 prompts across four people: **BE-1 (10), BE-2 (10), FE-1 (6), FE-2 (7)**.

## How to use

1. Open a fresh Antigravity session. Paste the **shared prompt** (`01_ROLES_AND_PROMPTS.md` §3) once, filling in who you are.
2. Paste **one increment prompt**. The agent does only that increment, reports, and stops.
3. Review using the **Review** line under the prompt. If something's off, paste the error or describe the problem and fix it before moving on.
4. Commit and push on your own branch (`be1/…`, `be2/…`, `fe1/…`, `fe2/…`), open a small PR, then paste the next prompt.
5. If you start a new session mid-way: paste the shared prompt, then tell it *"Read my Progress-log section in README.md, then continue with the next increment below"* and paste the next prompt.

Each prompt is self-contained: it names the files to write and the contract sections to follow. Don't skip numbers; later prompts assume earlier ones are merged. Each one ends with the same **finish line** so the agent stops cleanly:

> When finished: run the tests, update my section of the README Progress log, commit on my branch, and list the files that changed. Then stop — do not start the next increment.

**Needs** = what must already exist (merged to `main`) before you paste that prompt.

---

# BE-1 — Data, Peak & Platform

> Increments 1–3 unblock everyone else. Do them first, keep them simple, and tell the team when each is merged.

### BE-1 · Increment 1 of 10 — Repo scaffold
**Needs:** the three docs in `/docs`.

```
Increment 1 of 10 — repo scaffold.

Create the monorepo structure described in "Folder ownership" and "Repo layout" in docs/01_ROLES_AND_PROMPTS.md. Create:
- All folders (data/raw, data/external, data/processed, src/{data,features,peak,models,backtest,metrics,procurement,analysis}, models, artifacts, artifacts_mock, scripts, api, ui, tests) with .gitkeep where empty.
- Makefile with targets: data, features, backtest, peak, analysis, api, ui, test, all. Targets for things that don't exist yet should print "not implemented yet" and exit 0. `make test` runs pytest. `make api` runs uvicorn on port 8000.
- docker-compose.yml with an `api` service (port 8000) and a `ui` service (port 5173, placeholder for now).
- config.yaml with: timezone Asia/Kolkata, origin_hour_local 10, quantiles [0.05,0.1,0.5,0.9,0.95], peak_threshold_quantile 0.9, backtest {min_train_days: 730, retrain_every_days: 30, test_months: 12}, weather_noise {enabled: true, base_sd_c: 0.5, sd_growth_per_day_c: 0.4}, paths for data/artifacts/artifacts_mock, cdh_base_c 24.
- requirements.txt with pinned versions that install cleanly right now: pandas, numpy, pyarrow, scikit-learn, lightgbm, xgboost, prophet, statsmodels, shap, fastapi, uvicorn, pydantic>=2, pytest, ruff, httpx. Add torch (CPU) as a separate requirements-deep.txt so a heavy install failure doesn't block anyone.
- .gitignore (ignore data/raw, data/processed, models, __pycache__, node_modules, .venv; DO commit artifacts_mock/).
- README.md with: project one-liner, architecture one-liner, "How to run", "How to resume" (for a fresh AI session: read the README Progress log, then docs/), and a "Progress log" with four empty sections: BE-1, BE-2, FE-1, FE-2.
- tests/test_smoke.py that imports the main packages.

Finish: run `make test`, update the BE-1 section of the README Progress log, commit on branch be1/scaffold, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** folder tree matches the layout; `make test` passes; `docker compose config` is valid. Merge to `main` and tell everyone to clone.

### BE-1 · Increment 2 of 10 — Mock data + mock artifacts
**Needs:** Increment 1 merged.

```
Increment 2 of 10 — mock data and mock artifacts. BE-2 and the frontend are blocked on this.

(a) scripts/make_mock_data.py → writes data/processed/load_hourly.parquet and data/processed/features_known.parquet in the EXACT schema of docs/02_API_CONTRACT.md sections 1.1 and 1.2.
Synthetic Delhi-like load, 3 years hourly in Asia/Kolkata, hour-beginning timestamps, complete index:
- winter ~2,000 MW lows, summer peaks up to ~8,300 MW
- morning ramp 6–10, evening peak 19–23
- driven by a synthetic temperature series (annual cycle + daily cycle + noise); load rises with cooling-degree-hours
- weekday/weekend effect, a few festival dips, slow growth trend, a few outage drops flagged is_outage_suspect, a few short gaps imputed with is_imputed=True
Fill every column in contract 1.2 (calendar, festival, event, weather, thermal-inertia, trend).

(b) scripts/make_mock_artifacts.py → writes EVERY artifact in contract section 1.4–1.12 into artifacts_mock/ (NOT artifacts/): predictions_backtest.parquet, peak_predictions.parquet, metrics_accuracy.json, metrics_peak.json, error_heatmap.json, missed_peaks.json, feature_importance.json, procurement_defaults.json, meta.json.
- predictions_backtest: last 12 months of daily origins at 10:00 IST, targets D+1..D+7 (168 hours), models seasonal_naive, linear, lgbm, xgboost, prophet, lstm, ensemble; ensemble best, seasonal_naive worst; error grows with horizon_day; always p05<=p10<=p50<=p90<=p95; include *_raw columns and is_outage_suspect.
- peak_predictions: one row per date per model(at least ensemble), with outcomes covering hit/miss/false_alarm/correct_reject.
- metrics_accuracy: every model × horizon_day (1–7 and "all") × segment (all, 4 seasons, peak_hours, off_peak), computed from the mock predictions, not invented separately.
- metrics_peak: ensemble + one rule baseline; error_heatmap: at least ensemble and seasonal_naive, metrics mape/rmse/bias, horizon_day 1 and "all"; missed_peaks: at least 8 items with tags; feature_importance: lgbm and xgboost; procurement_defaults: da 5000, under 12000, resale 2500 INR/MWh with the disclaimer text from the contract; meta.json per 1.12.
Keep artifacts_mock/ small enough to commit.

(c) tests/test_artifact_schemas.py that validates every file against contract section 1: column names, dtypes, tz-aware timestamps, quantile ordering, enum values, point counts. It must run against artifacts_mock/ now and against artifacts/ later (parametrize by directory).

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/mocks, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** open a parquet in pandas and eyeball it (peaks in the evening, summer > winter); schema tests pass. Merge and tell BE-2 and the frontend pair.

### BE-1 · Increment 3 of 10 — FastAPI on mocks
**Needs:** Increment 2 merged.

```
Increment 3 of 10 — FastAPI backend running on mock artifacts.

Build api/ implementing EVERY endpoint in docs/02_API_CONTRACT.md section 2 (2.1 to 2.16; 2.16 may return 501 for now), prefix /api/v1.
- Pydantic v2 response models that mirror the contract's JSON exactly (field names, nullability, enums).
- Loads artifacts at startup from the directory given by env ARTIFACTS_DIR (default "artifacts"); MOCK=1 makes it use "artifacts_mock" instead. GET /health must report "mock": true/false.
- Derive day-ahead/week-ahead responses from predictions_backtest.parquet (24 or 168 points, at_risk = p90 >= peak_threshold_mw, actual null when missing), peak endpoints from peak_predictions.parquet, and pass-through JSON for metrics, error-heatmap, missed-peaks, feature-importance, meta, procurement defaults.
- POST /procurement/recommend must call src/procurement/advisor.py:recommend(start_date, days, model, risk_quantile, tariff). That module doesn't exist yet: create a stub in src/procurement/advisor.py that returns a contract-shaped response with placeholder numbers, and clearly mark it STUB (FE-1 will replace it).
- Error handling per contract section 3: a unified {"error": {"code","message","details"}} format, including wrapping FastAPI's 422 validation errors.
- CORS enabled for http://localhost:5173.
- tests/test_contract.py: call every endpoint with valid and invalid inputs (bad date, unknown model, out-of-range date, bad risk_quantile) and validate responses against the Pydantic models. It must pass with MOCK=1.
- `make api` starts the server; document the commands in the README.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/api, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** run `MOCK=1 make api`, open `/docs` (Swagger), click through 5 endpoints; contract tests pass. Merge and announce **Checkpoint 0.5**.

### BE-1 · Increment 4 of 10 — Ingest real data
**Needs:** Increment 1 merged. (Can run in parallel with 2–3 if you hit data trouble.)

```
Increment 4 of 10 — ingest real data.

1) src/data/ingest_load.py: load Delhi hourly (or finer) electricity demand from whatever source I provide in data/raw/. I will tell you the source/file. If the data is finer than hourly (e.g. 15-min/5-min), aggregate to hourly mean MW with hour-beginning timestamps in Asia/Kolkata and ALSO save the native-resolution file to data/processed/load_native.parquet for peak-timing analysis. If I haven't provided any load data yet, STOP and give me a short list of exactly where to look (organizer dataset, Delhi SLDC historical demand reports, Grid-India/POSOCO reports, Kaggle) and what columns/format to look for. Do not invent data.
2) src/data/ingest_weather.py: pull hourly weather for Delhi (28.61, 77.21) from the Open-Meteo historical archive API for the same date range: temperature_2m, relative_humidity_2m, dew_point_2m, wind_speed_10m, cloud_cover. Cache raw responses in data/raw/weather/ so reruns don't hit the network. Convert to Asia/Kolkata hour-beginning. If the sandbox can't reach the API, tell me and write the exact curl/python snippet I should run locally.
3) data/raw/README.md recording source, URL, licence, date downloaded, and column meanings.
4) Print a short summary: date range, row counts, % missing, min/max load.
Make target: `make data` runs ingest only for now.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/ingest, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the printed summary looks sane (≥ 2 years, load range plausible). If load data is missing, escalate to the team **now**.

### BE-1 · Increment 5 of 10 — Clean + impute
**Needs:** Increment 4 merged.

```
Increment 5 of 10 — cleaning and imputation.

src/data/clean.py producing data/processed/load_hourly.parquet exactly per docs/02_API_CONTRACT.md section 1.1:
- Reindex to a complete hourly Asia/Kolkata index. IST has no DST, but still detect and report duplicate timestamps, missing hours, and apparent clock shifts in the source; document what you find and how you resolved each.
- Impute gaps: gaps <= 3 hours → linear interpolation (imputation_method="linear"); longer gaps → fill from the same hour-of-week averaged over the nearest 4 non-missing weeks (imputation_method="hour_of_week"). Set is_imputed accordingly.
- Flag suspected outage drops / outliers as is_outage_suspect using a robust z-score (MAD) of the residual versus the hour-of-week median profile; threshold configurable in config.yaml. Do NOT delete or alter these values.
- No NaNs may remain in load_mw.
- Write docs/DATA_QUALITY.md with REAL numbers: total hours, number and length distribution of gaps, % imputed per method, number of flagged outliers with 3 examples, duplicate/clock issues found, and the decisions taken.
- Tests: index complete+unique+monotonic, no NaNs, schema matches contract, imputed flags consistent with method.
`make data` should now run ingest + clean.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/clean, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read `DATA_QUALITY.md` — do the numbers match what you expect from the raw data? Tell BE-2 real data is available.

### BE-1 · Increment 6 of 10 — Known features
**Needs:** Increment 5 merged.

```
Increment 6 of 10 — "known-in-advance" features.

src/features/build_known.py producing data/processed/features_known.parquet with exactly the columns in docs/02_API_CONTRACT.md section 1.2:
- Calendar: hour, dow, month, doy, sin/cos of hour and dow, is_weekend, is_holiday + holiday name (use the `holidays` package for India).
- Festivals: create data/external/festivals.csv with columns date,festival,source_url for Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Independence Day (and others if useful) covering my data range. Use web search to get correct dates and CITE the source URL per row; if you cannot verify a date, flag it in the CSV instead of guessing. Build cal_days_to_*/cal_days_since_* (clipped to ±30) and cal_is_festival_window (±2 days) from it.
- Events: evt_lockdown and evt_odd_even flags. Research the actual date ranges (COVID lockdown phases; Delhi odd-even scheme rounds) with web search, cite sources in data/external/events.csv, and only populate flags for periods inside my data range.
- Weather-derived: wx_* columns from the Open-Meteo data. Heat index via the Rothfusz regression (document the validity range and what you do outside it); wx_cdh = max(temp - cdh_base_c, 0) with base from config.yaml (default 24); wx_cdh_24 = rolling 24h sum; temperature lags 1,3,6,12,24,48,72; rolling mean temp 24h and 72h.
- trend_t = days since first timestamp.
- wx_is_noisy = False for now (noise is added in a later increment).
- Tests: schema matches contract, no NaNs except the first rows lost to lags (drop or document), festival windows look right for Diwali in a known year.
`make features` runs this.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/features, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** spot-check Diwali dates against a calendar; check the odd-even/lockdown dates the agent cited.

### BE-1 · Increment 7 of 10 — AR features + weather noise
**Needs:** Increment 6 merged.

```
Increment 7 of 10 — origin-relative autoregressive features and weather-noise option.

1) src/features/ar_features.py with
   build_ar_features(load_df, origin_ts, target_ts) -> DataFrame
exactly as specified in docs/02_API_CONTRACT.md section 1.3. It must use ONLY load rows with ts < origin_ts. The forecast origin is 10:00 IST on D0, so the last known load is 09:00 D0 and targets start at D+1 00:00. Columns: ar_same_hour_last_week (the value at target_ts minus 7 days *as long as that timestamp is before the origin; otherwise the same hour one more week earlier — document the rule), ar_same_hour_last_known_day, ar_mean_7d, ar_mean_30d, ar_level_365d, ar_last_known_load, ar_last_week_daily_peak, ar_hours_since_last_known.
2) tests/test_leakage.py: for 50 random origins, assert every input timestamp used is < origin_ts (build the function so you can introspect which rows it touched, or test by perturbing load values at/after the origin and asserting outputs don't change). This test is mandatory.
3) Weather noise for day-ahead realism: src/features/weather_noise.py adds Gaussian noise to wx_temp_c (and recomputes dependent wx_* features) whose sd grows with horizon: sd = base_sd_c + sd_growth_per_day_c * horizon_day (values from config.yaml). Provide a function that returns noisy weather features for a given origin and horizon, deterministic given a seed, and sets wx_is_noisy=True. Note that the true weather is still used for the "actual" side of the comparison.
4) Append to docs/ASSUMPTIONS.md: that backtests use observed weather plus horizon-scaled noise as a proxy for archived forecasts, the sd values used, and why.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/ar-features, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** leakage test passes **and** you've read the test to confirm it's meaningful. Tell BE-2 the AR function is ready.

### BE-1 · Increment 8 of 10 — Peak classifier (binary)
**Needs:** Increment 7 merged; BE-2 Increment 4 (LightGBM predictions) preferred, but you can start with BE-2's baselines.

```
Increment 8 of 10 — peak-event classifier (binary), evaluated walk-forward.

src/peak/ — a model that predicts whether a day's peak exceeds the threshold.
- Label: day's max hourly load > threshold, where threshold = the 90th percentile (config peak_threshold_quantile) of DAILY peaks in that fold's TRAINING window only. Add a config flag for a season-relative variant (threshold per season) but default to the global one.
- Use the SAME folds and origins as BE-2's backtest harness (src/backtest/) — import its fold definitions rather than inventing new ones. Walk-forward only.
- Features per target date, all available at the 10:00 IST origin: known features at the daily level (max temp, max CDH, day-of-week, holiday/festival flags, trend), AR features from build_ar_features, and — when available — BE-2's daily forecast summaries from artifacts/predictions_backtest.parquet (daily max of p50 and p90 for the best model).
- Model: LightGBM classifier + isotonic calibration of the probability (calibrate on a held-out window before the test window).
- Decision threshold tuned for RECALL (missing a peak costs more than a false alarm): choose the threshold on a validation window to maximise precision subject to recall >= 0.8 (fallback: maximise F2). Document the trade-off in docs/ASSUMPTIONS.md.
- Rule baseline: "same weekday last week exceeded its threshold".
- Output a first version of artifacts/peak_predictions.parquet per contract section 1.5 (fill pred_peak_hour with argmax of the p50 forecast for now; timing/magnitude fields can come from that) and artifacts/metrics_peak.json per section 1.7 with precision, recall, F1, PR-AUC, confusion matrix for classifier and rule baseline.
- Tests: no threshold computed with test-fold data; label/threshold logic on a toy example.
`make peak` runs this.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/peak-binary, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** precision/recall for classifier vs rule baseline — is the classifier clearly better? Is the threshold per fold only from training data?

### BE-1 · Increment 9 of 10 — Peak hour + timing/magnitude
**Needs:** Increment 8 merged.

```
Increment 9 of 10 — peak hour prediction, timing error and magnitude error.

Extend src/peak/:
- Peak-hour model: LightGBM multiclass over 24 hours (predict which hour-beginning holds the daily max). Baseline: argmax of the best forecaster's p50 by hour. Use the classifier's probabilities/top-1 and also report top-2 hit rate.
- Fill the remaining fields of artifacts/peak_predictions.parquet per contract section 1.5: pred_peak_hour, pred_peak_ts, pred_peak_mw_p10/p50/p90 (daily max from the forecast quantiles — document how you combine hourly quantiles into a daily max, e.g. max of each quantile series), actual_peak_ts, actual_peak_mw, actual_is_peak, timing_error_min (signed, predicted minus actual; if data/processed/load_native.parquet exists, measure the actual peak time at native resolution), magnitude_error_mw (predicted p50 daily max minus actual), and outcome (hit/miss/false_alarm/correct_reject).
- Extend artifacts/metrics_peak.json with timing_mae_min, timing_within_1h_pct, magnitude_mae_mw, magnitude_bias_mw for classifier and baselines.
- Tests: outcome labels on a toy confusion example; timing error sign convention.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/peak-hour, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** timing error distribution (most days within ±1 h?); `outcome` counts add up to the number of days. Tell FE-2 the peak file is final.

### BE-1 · Increment 10 of 10 — Real artifacts, meta, Docker, deploy
**Needs:** Increments 1–9 merged; BE-2 and FE-2 artifacts present in `artifacts/`.

```
Increment 10 of 10 — switch to real artifacts, assemble meta, containerize and prepare for deploy.

1) Assemble artifacts/meta.json per docs/02_API_CONTRACT.md section 1.12 from the real data and backtest (data_range, backtest_range, latest peak threshold, models actually present, season/peak-hour definitions, weather_proxy_note).
2) Run the API with MOCK unset against artifacts/. Fix any mismatch between real artifacts and the Pydantic models by fixing the PRODUCER side where possible: report schema deviations to me instead of loosening the models. Make tests/test_contract.py and tests/test_artifact_schemas.py pass against BOTH artifacts_mock/ and artifacts/.
3) Dockerfiles for api and ui; docker-compose up must serve API on 8000 and UI on 5173 (serve the built UI). Include artifacts/ via a volume or copy. Add a healthcheck on /api/v1/health.
4) `make all` runs data → features → backtest → peak → analysis in order (skip steps whose target is not implemented, with a clear message).
5) Prepare deployment notes in README.md for Render/Railway (or similar): build/start commands, env vars, how to upload artifacts. Do not deploy without me.
6) Fresh-clone test: in a clean directory, clone, install, run `make test` and `docker compose up`, and report what failed.
7) Add the final submission checklist from docs/03_PRD.md section 12 to the README with checkboxes.

Finish: run `make test`, update the BE-1 Progress log, commit on branch be1/finalize, and list the files that changed. Then stop.
```
**Review:** `docker compose up` on a machine that has never seen the repo.

---

# BE-2 — Modeling & Backtest

> Start as soon as BE-1's Increment 2 (mock data) is merged. Switch to real data after BE-1's Increment 5.

### BE-2 · Increment 1 of 10 — Backtest harness
**Needs:** BE-1 Increments 1–2 merged.

```
Increment 1 of 10 — rolling-origin backtest harness.

Build src/backtest/ using data/processed/load_hourly.parquet and features_known.parquet (BE-1's mock data is fine for now).
- Protocol (frozen, see docs/03_PRD.md section 9): origin = 10:00 IST every day; targets D+1 00:00 … D+7 23:00 (horizon_h 14–181; horizon_day 1–7); expanding training window; min train = config backtest.min_train_days; retrain every config backtest.retrain_every_days (a fold = one retrain period of consecutive origins); test = last config backtest.test_months months (or all remaining data after min-train).
- A Forecaster Protocol:
    class Forecaster(Protocol):
        name: str
        def fit(self, train_end: pd.Timestamp) -> None: ...
        def predict(self, origin: pd.Timestamp) -> pd.DataFrame  # columns: target_ts, horizon_h, horizon_day, p05, p10, p50, p90, p95
  predict may only use data with ts < origin (autoregressive via src/features/ar_features.build_ar_features when it exists; until then use a simple stand-in and mark it TODO).
- A runner that, for each fold, fits a forecaster at train_end, predicts all origins in the fold, joins y_true and is_outage_suspect, and appends to artifacts/predictions_backtest.parquet with the exact columns of docs/02_API_CONTRACT.md section 1.4 (fill *_raw = same as final for now; fold_id; model name).
- Make the runner skip models/folds already computed (resume) and show a progress bar.
- A trivial "persistence" forecaster to prove the harness end to end.
- Tests: no training row at or after train_end; no feature row at or after origin; output schema matches contract; 100% of targets covered once per model/origin.
`make backtest` runs the registered models.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/harness, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** row counts = origins × 168 per model; walk through one fold's train_end vs first origin.

### BE-2 · Increment 2 of 10 — Baselines
**Needs:** Increment 1 merged.

```
Increment 2 of 10 — baselines. Register both in the harness.

1) src/models/seasonal_naive.py: for each target hour, use the actual load at the same hour-of-week 7 days earlier if that timestamp is before the origin; otherwise step back by additional 7-day multiples until it is (document this rule — for D+2..D+7 targets it will step back further). Quantiles: add residual quantiles by hour-of-day computed ONLY from the training window (residual = actual − naive prediction), so p05..p95 are naive + residual quantiles.
2) src/models/linear.py: scikit-learn LinearRegression on known features (calendar one-hots/sin-cos, wx_cdh_24, wx_heat_index_c, temperature lags/rolling means, festival/event flags, trend_t) plus AR features and horizon_h. Quantiles via residual quantiles by hour-of-day from the training window.
3) Run both through the harness and write predictions for names "seasonal_naive" and "linear". Print mean RMSE and MAPE per horizon_day for each.
4) Sort quantiles per row so p05<=p10<=p50<=p90<=p95.
5) Tests: seasonal-naive never uses data at or after the origin; quantile ordering.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/baselines, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** baseline RMSE by horizon-day — seasonal-naive should degrade as horizon grows; linear should beat it.

### BE-2 · Increment 3 of 10 — Metrics library
**Needs:** Increment 2 merged.

```
Increment 3 of 10 — metrics library and accuracy table.

src/metrics/ with pure functions plus a table builder:
- mape (percent; document the weakness at low loads and guard against zero), rmse, mae, bias (mean of prediction − actual), pinball loss per quantile and mean over the five quantiles, picp for the 80% interval (p10–p90) and the 90% interval (p05–p95), mpiw_80, and % improvement vs seasonal_naive for mape and rmse.
- Segments: all, winter, summer, monsoon, post_monsoon (month definitions in docs/02_API_CONTRACT.md section 0), peak_hours (hour-beginning 6,7,8,9,10,19,20,21,22,23) and off_peak.
- build_accuracy_table(predictions_df) → rows for every model × horizon_day (1–7 and "all") × segment, written to artifacts/metrics_accuracy.json exactly per contract section 1.6 (mape in percent, picp as fraction, improvement null for the baseline itself).
- Exclude nothing silently: report is_outage_suspect rows as part of "all" but also expose a flag to compute metrics without them.
- Tests: hand-computed toy examples for each metric; improvement of the baseline vs itself is null.
- Print a compact table (model × horizon_day for segment=all, plus peak_hours) to the console.
`make backtest` ends by writing metrics.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/metrics, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** FE-2 can now build the Accuracy page on real baseline numbers.

### BE-2 · Increment 4 of 10 — LightGBM quantile
**Needs:** Increment 3 merged; BE-1 Increment 7 (AR features) merged.

```
Increment 4 of 10 — LightGBM quantile forecaster (main model).

src/models/lgbm_quantile.py registered as "lgbm":
- One LightGBM model per quantile q ∈ {0.05, 0.1, 0.5, 0.9, 0.95} with objective="quantile".
- Training table: for each training origin and each target hour in D+1..D+7, features = known features at target_ts (with weather noise via BE-1's weather_noise when enabled) + build_ar_features(load_df, origin, target) + horizon_h (as a feature). Subsample origins if training is too slow (e.g., every 2nd origin) and note it in config.
- Zero sample weight for is_outage_suspect rows in training; they stay in evaluation.
- Sort the five quantile predictions per row to prevent crossing.
- Fixed seeds; hyperparameters in config.yaml (modest defaults: num_leaves 63, learning_rate 0.05, n_estimators ~500 with early stopping on a validation slice taken from the END of the training window).
- Register in the harness, run the backtest, and print the accuracy table including improvement vs seasonal_naive for segment=all and peak_hours.
- Tests: no future leakage via the existing harness tests; quantile ordering; deterministic with a fixed seed.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/lgbm, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** does lgbm beat seasonal_naive and linear **at peak_hours**, not just on average? If not, tell the team before continuing.

### BE-2 · Increment 5 of 10 — Conformal calibration
**Needs:** Increment 4 merged.

```
Increment 5 of 10 — interval calibration with conformalized quantile regression (CQR).

Implement src/models/calibration.py:
- For each fold, use a rolling calibration window that ENDS BEFORE the fold's first test origin (e.g., the last 90 days of the training period, predicted out-of-sample by a model fit before that window). Compute conformity scores per (horizon_day, hour-of-day group or peak/off-peak) and adjust the 80% interval (p10, p90) and the 90% interval (p05, p95) so the coverage targets are 0.80 and 0.90. Keep the median unchanged.
- Preserve quantile ordering after adjustment.
- Update the harness output so p05..p95 are the CALIBRATED values and p05_raw..p95_raw keep the pre-calibration values, per contract section 1.4.
- Apply it to "lgbm" (and make it reusable for other models).
- Extend metrics output: keep picp_80, picp_90, mpiw_80 on the calibrated values and ADD a small extra table to artifacts/metrics_accuracy.json under key "calibration_comparison" with picp/mpiw before vs after for each calibrated model and horizon_day.
- Tests: calibration window never overlaps test origins; ordering preserved; coverage on a synthetic example moves toward target.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/calibration, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** PICP for 80% should be ~0.80 and 90% ~0.90 (within a few points); intervals shouldn't have exploded in width (check MPIW).

### BE-2 · Increment 6 of 10 — Daily-peak summaries for BE-1
**Needs:** Increment 5 merged.

```
Increment 6 of 10 — export daily forecast summaries for the peak classifier.

1) Propose and implement artifacts/daily_peak_summary.parquet, one row per (model, origin_ts, date): columns model, origin_ts, date, horizon_day, daily_max_p10, daily_max_p50, daily_max_p90 (max over the day's 24 hourly values of each quantile series — document this choice), argmax_hour_p50, daily_min_p50, y_true_daily_max (null if unobserved).
2) Add this as a new section 1.13 in docs/02_API_CONTRACT.md (producer BE-2, consumer BE-1) and add a row to the change log. Make it a minimal additive change; do not touch other sections.
3) Add a schema test to tests/test_artifact_schemas.py (BE-1 owns that file: add the test in a new file tests/test_daily_peak_summary.py instead).
4) Generate it for all models in the backtest and print the first 5 rows for "lgbm".
Tell me the exact path and columns so I can message BE-1.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/daily-summary, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** message BE-1 the path and columns.

### BE-2 · Increment 7 of 10 — Prophet + XGBoost
**Needs:** Increment 5 merged.

```
Increment 7 of 10 — Prophet and XGBoost comparison models.

1) src/models/prophet_model.py registered as "prophet": holiday-aware (build the holidays dataframe from data/external/festivals.csv plus the India public holidays), temperature (wx_temp_c or wx_cdh_24) as an extra regressor using noisy weather for future targets when enabled, daily/weekly/yearly seasonality. Prophet is slow: train one model per fold on hourly data or on a reduced set if needed, document how. Quantiles from Prophet's uncertainty interval where reasonable (interval_width 0.9 → p05/p95, 0.8 → p10/p90), otherwise from residual quantiles by hour; document which.
2) src/models/xgboost_model.py registered as "xgboost": same training table and design as lgbm but with XGBoost quantile objective (reg:quantileerror). 
3) Apply the same CQR calibration to both; keep raw columns.
4) Run the backtest for both and print the updated accuracy table. Time-box: if Prophet is too slow to backtest at the full fold count, backtest it on every 7th origin and state this clearly in the README and docs/ASSUMPTIONS.md.
5) Tests: registration works, output schema valid, quantile ordering.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/prophet-xgb, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** Prophet runtime acceptable; results plausible (Prophet typically weaker on peaks — that's a fine finding).

### BE-2 · Increment 8 of 10 — LSTM (deep model)
**Needs:** Increment 5 merged; `pip install -r requirements-deep.txt` works.

```
Increment 8 of 10 — one deep model, time-boxed. Keep it simple.

src/models/lstm_model.py registered as "lstm" (PyTorch, CPU is fine):
- Input: last 168 hours of [load_mw, wx_temp_c, wx_cdh, cal_hour_sin/cos, cal_dow_sin/cos, cal_is_holiday] up to the origin; plus known future features for the target horizon (temperature with noise, calendar, festival flags) as a decoder-side input, OR a simpler design: LSTM encoder → MLP head that outputs all 168 horizons × 5 quantiles at once. Choose the simpler one that trains fast.
- Loss: pinball (quantile) loss summed over the five quantiles; scale inputs/targets using training-window statistics only.
- Retrain per fold (or fewer folds, e.g. every 3rd retrain period, reusing the last model in between — document it), early stopping on the END of the training window, fixed seeds, max ~10 minutes total backtest budget.
- Sort quantiles to avoid crossing; apply CQR calibration; keep raw columns.
- Print the updated accuracy table. If it doesn't beat lgbm, keep it anyway as a documented comparison.
- Tests: forward-pass shapes; quantile ordering; no future data in an input window.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/lstm, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** training finished within budget; loss curve not diverging.

### BE-2 · Increment 9 of 10 — Ensemble
**Needs:** Increments 4, 7, 8 merged.

```
Increment 9 of 10 — ensemble.

src/models/ensemble.py registered as "ensemble":
- Combine the available base models (lgbm, xgboost, prophet, lstm, and optionally linear) by a weighted average of each quantile series (quantile averaging / Vincentization).
- Fit the weights per horizon_day on a VALIDATION window that ends before the test window of each fold (e.g., minimise pinball loss, weights ≥ 0 summing to 1, via scipy.optimize or a simple grid). Never fit weights on test origins.
- Because base models are calibrated individually, recalibrate the ensemble with CQR at the end and keep raw columns.
- Write predictions for model "ensemble" and print the complete accuracy table: every model × horizon_day for segment=all and peak_hours, with improvement vs seasonal_naive; also print the learned weights.
- Tests: weights non-negative and sum to 1; validation window precedes test window; ordering preserved.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/ensemble, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** ensemble ≥ best single model on pinball; PICP still on target. Tell BE-1 and FE-2 `ensemble` is available.

### BE-2 · Increment 10 of 10 — Feature importance
**Needs:** Increment 4 merged.

```
Increment 10 of 10 — feature importance.

- Compute SHAP values (TreeExplainer) for the p50 LightGBM model on a sample of the latest fold's test rows (e.g. 5,000 rows) and mean(|SHAP|) per feature; also compute LightGBM gain importance as a cross-check. Do the same for XGBoost if time allows.
- Write artifacts/feature_importance.json per docs/02_API_CONTRACT.md section 1.10: importance normalised to sum to 1 per model, group in {calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon}. Map each feature name to its group with a single mapping dict in src/models/feature_groups.py.
- Also write artifacts/feature_importance_by_segment.json with the top 10 features for peak_hours vs off_peak (extra, not in the contract: put it under a clearly named key and tell me so I can add it to the contract if useful).
- Tests: normalisation sums to 1; every feature has a group.
- Update README: a short "Results" table (model × D+1 and D+7, RMSE and MAPE, segment all and peak_hours, % improvement vs seasonal-naive, PICP 80/90) copied from the real artifacts.

Finish: run `make test`, update the BE-2 Progress log, commit on branch be2/importance, and list the files that changed. Then stop.
```
**Review:** top features look physically sensible (CDH/temperature, same-hour-last-week, hour). Tell FE-2 the file is ready.

---

# FE-1 — Forecast & Procurement UI

### FE-1 · Increment 1 of 6 — UI shell
**Needs:** BE-1 Increments 1–3 merged (mock API running). Until then use the response examples in `02_API_CONTRACT.md`.

```
Increment 1 of 6 — UI shell. FE-2 builds on this, so keep it clean and merge it early.

In ui/, create a Vite + React + TypeScript (strict) + Tailwind + Plotly.js (react-plotly.js or plotly.js-dist-min via a thin wrapper) app.
- Routing for six pages with placeholder content: /forecast, /accuracy, /errors, /missed-peaks, /procurement, /insights; a top nav; a default redirect to /forecast.
- Theme: colour-blind-safe palette defined once as CSS variables/Tailwind tokens (one colour per model, band colours for P10–P90 and P05–P95, actual line, peak marker, at-risk shading); light and dark ok but not required.
- ui/src/api/: a typed client matching docs/02_API_CONTRACT.md section 2 — TypeScript types for every response, one function per endpoint, base URL from VITE_API_BASE (default http://localhost:8000/api/v1), and a uniform error type from the contract's error format.
- ui/src/components/shared/: ChartCard (title, subtitle, units, loading/error/empty states), ModelSelect (models from GET /models; default "ensemble"), DatePicker (constrained to meta.backtest_range), StatTile, and a Plotly wrapper that handles resize and theme.
- A global "mock mode" banner when GET /health says mock=true.
- Add a tiny README section "How to run the UI" and a `make ui` target that runs the dev server. Update the Dockerfile placeholder if BE-1 created one, but don't deploy.
- Only use files under ui/; FE-2 owns ui/src/pages/{Accuracy,ErrorHeatmap,MissedPeaks,Insights} and ui/src/components/eval/, so create those placeholder page files and leave them minimal.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/shell, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** `npm run dev`, click all six nav links; no console errors. Merge immediately and tell FE-2.

### FE-1 · Increment 2 of 6 — Forecast page
**Needs:** Increment 1 merged; mock API running.

```
Increment 2 of 6 — Forecast page (ui/src/pages/Forecast).

- Controls: DatePicker, a Day-ahead / Week-ahead toggle, ModelSelect. Support URL query ?date=YYYY-MM-DD&model=...&view=day|week so other pages can deep-link here (FE-2's missed-peak drill-down will link with ?date=).
- Data: GET /forecast/day-ahead or /forecast/week-ahead, and GET /peak/day for the peak card.
- Chart (Plotly): actual line; shaded P10–P90 band; lighter P05–P95 band; P50 line; predicted peak marker (from the response's peak.predicted_peak_ts / mw) and actual peak marker; horizontal dashed line at peak_threshold_mw; at-risk hours (at_risk=true) shaded as vertical bands. In week view show all 168 hours with day separators.
- Peak card beside the chart: peak probability badge, predicted peak hour and MW range (p10/p50/p90), actual peak if known, outcome (hit / miss / false alarm / correct reject) with a colour and plain-language text, timing error in minutes and magnitude error in MW.
- A short legend explaining: P10–P90 is an 80% interval, P05–P95 a 90% interval.
- Handle loading/empty/error states (e.g. DATE_OUT_OF_RANGE → friendly message).
- Hover tooltip shows ts, p05..p95, actual.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/forecast, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** switch date, day↔week, model; check the legend wording; check the peak card for a "miss" day.

### FE-1 · Increment 3 of 6 — Procurement advisor (Python)
**Needs:** BE-1 Increment 3 merged (stub exists); BE-2 baselines/lgbm predictions available (mock is fine).

```
Increment 3 of 6 — procurement advisor logic. Replace the STUB BE-1 created.

Implement src/procurement/advisor.py: recommend(start_date, days, model, risk_quantile, tariff) -> dict, returning EXACTLY the response shape in docs/02_API_CONTRACT.md section 2.12.
- Load forecasts from artifacts/predictions_backtest.parquet (directory from env ARTIFACTS_DIR, default "artifacts"; MOCK=1 → "artifacts_mock"), horizon_day=1 forecasts for each target date in [start_date, start_date+days) so the schedule is a true day-ahead schedule (origin 10:00 on D−1), and also the p50/p90 columns.
- risk_quantile: a number in [0.5, 0.99] or "newsvendor". newsvendor quantile = (under_price − da_price) / (under_price − resale_price); set risk_quantile_source accordingly. Use the nearest available quantile column (p50, p90, p95) by linear interpolation between available quantiles; document it.
- scheduled_mw per hour = the chosen quantile of the forecast.
- Cost per hour = da_price·S + under_price·max(D−S,0) − resale_price·max(S−D,0) with D = actual load when available.
- Baselines: flat at the previous week's mean MW; also flat at the previous week's peak MW (flat_peak_cost_inr). If there is no previous week in the data, say so in a clear error.
- p90_risk_exposure_inr = cost with D = p90 path minus cost with D = p50 path, same schedule.
- at_risk_hours = hours where p90 >= the latest peak threshold from meta.json (or peak_predictions.parquet).
- If actuals are missing for some hours, set the realised cost fields to null per the contract and still return p90_risk_exposure_inr.
- by_day breakdown per the contract.
- artifacts/procurement_defaults.json per section 1.11 with da 5000, under 12000, resale 2500 INR/MWh and the disclaimer; append the reasoning and the "illustrative placeholder" caveat to docs/ASSUMPTIONS.md.
- Validate inputs (days 1–7, tariff ordering under > da > resale, risk_quantile range) and raise clear ValueErrors that BE-1's API maps to BAD_PARAMETER.
- Unit tests with hand-computed numbers: a 3-hour toy example for cost, newsvendor quantile = 0.7368 for the defaults, exposure sign.
Tell me when it's importable so I can ask BE-1 to remove the stub.

Finish: run `make test`, update the FE-1 Progress log, commit on branch fe1/advisor, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** hand-check one hour of cost; newsvendor ≈ 0.737 for the default tariff. Tell BE-1.

### FE-1 · Increment 4 of 6 — Procurement page
**Needs:** Increments 2–3 merged; BE-1 API using the real advisor.

```
Increment 4 of 6 — Procurement page (ui/src/pages/Procurement).

- Controls: week picker (start date, days 1–7), ModelSelect, risk-quantile slider (0.50–0.99, step 0.01) with a checkbox/preset "Use newsvendor" (shows the computed quantile from the response), and an editable tariff form (da_price, under_price, resale_price) prefilled from GET /procurement/defaults with a visible "illustrative placeholder" note and a Reset button. Validate under > da > resale before submitting.
- Call POST /procurement/recommend on change (debounced) and show results:
  1) schedule chart: scheduled MW vs p50, p90, flat baseline and actual (if present); at-risk hours shaded;
  2) KPI tiles: cost, flat cost, savings (INR and %), P90 risk exposure, under/over-procured hours;
  3) per-day table from by_day;
  4) a "cost vs risk quantile" curve: call the endpoint for q ∈ {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99} (in parallel) and plot realised cost (or exposure when cost is null) with the current q and the newsvendor q marked.
- Format INR with Indian digit grouping and units (₹ crore/lakh with a toggle to full numbers).
- Loading/empty/error states, including BAD_PARAMETER messages.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/procurement, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** move the slider — does the cost curve have a sensible minimum? Try an extreme tariff.

### FE-1 · Increment 5 of 6 — Real artifacts + polish
**Needs:** BE-1 Increment 10 (real artifacts served) or at least real predictions in `artifacts/`.

```
Increment 5 of 6 — switch to real artifacts and polish.

- Point the UI at the API running WITHOUT MOCK (real artifacts). Fix any crashes caused by real data differences (missing actuals at the edges, date ranges, models absent). Don't change the contract: if the API's output deviates from docs/02_API_CONTRACT.md, tell me so I can raise it with the owner.
- Polish: responsive layout (laptop and a phone-width sanity check), consistent chart heights, axis units on every chart (MW, ₹), keyboard-focusable controls, aria-labels on icon buttons, meaningful chart titles/subtitles, no layout jump while loading (skeletons).
- Add a small "About these numbers" popover on Forecast and Procurement: weather-proxy caveat and tariff-placeholder caveat (read the text from meta.weather_proxy_note and procurement defaults).
- Production build works via `npm run build` and the nginx/static serve used by BE-1's docker setup; fix any base-path issues.
- Take screenshots of the Forecast and Procurement pages (desktop) into docs/screenshots/ for the README and submission.

Finish: run the type check and build, update the FE-1 Progress log, commit on branch fe1/polish, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** use the app like a judge would for 5 minutes; fix anything confusing.

### FE-1 · Increment 6 of 6 — Procurement memo + demo script
**Needs:** Increment 5 merged; real procurement results available.

```
Increment 6 of 6 — documents.

1) docs/PROCUREMENT_MEMO.md: pick a sample week from the backtest that includes at least one peak-risk day (explain why you picked it). Use src/procurement/advisor.py with the real ensemble forecasts to produce: the recommended hourly day-ahead schedule (include a compact daily summary table and a chart image saved to docs/figures/), P90 risk exposure, at-risk hours, simulated cost vs both naive flat schedules, savings in INR and %, and sensitivity to the risk quantile (a small table for q = 0.5, 0.7, 0.9, 0.99 and the newsvendor q). State clearly that tariffs are illustrative placeholders. Use REAL numbers only; write a script scripts/make_procurement_memo.py that regenerates the figures and the numbers section so it is reproducible.
2) docs/DEMO_SCRIPT.md: a 3-minute demo story: (1) the problem (tail risk at peaks, not just the average); (2) Forecast page on a hot day with the P90 band and at-risk hours; (3) peak classifier outcome; (4) Accuracy table vs baselines at peak hours; (5) a missed peak and why; (6) Procurement: schedule, exposure, savings; (7) one-sentence limitations (weather proxy, placeholder tariffs). Include exact URLs/clicks, what to say, and a fallback if the live demo fails (screenshots in docs/screenshots/).

Finish: update the FE-1 Progress log, commit on branch fe1/docs, and list the files that changed. Then stop.
```
**Review:** read the memo as if you were the planner — would you trust it? Time the demo script out loud.

---

# FE-2 — Evaluation & Insights UI

> Start with the Python analysis (Increments 1–2) while FE-1 builds the shell; then build pages on the merged shell.

### FE-2 · Increment 1 of 7 — Error decomposition + heatmap JSON
**Needs:** BE-1 Increments 1–2 merged (mock artifacts). Later runs on real predictions after BE-2 Increment 4+.

```
Increment 1 of 7 — error decomposition and heatmap artifact.

src/analysis/ (read BE-2's metric functions from src/metrics/ if they exist; otherwise write small local versions and switch later):
- error_decomposition.py: from artifacts/predictions_backtest.parquet compute error metrics by season × hour-of-day, peak vs off-peak, and horizon_day, per model.
- artifacts/error_heatmap.json exactly per docs/02_API_CONTRACT.md section 1.8: one entry per model × metric (mape, rmse, bias) × horizon_day (1 and "all" at minimum, 1–7 if cheap), with hours [0..23], seasons ["winter","summer","monsoon","post_monsoon"], values[season][hour], counts[season][hour]. Cells with fewer than 5 observations should be null.
- Support reading from artifacts_mock/ via env MOCK=1 (default ARTIFACTS_DIR=artifacts) so it works on mock data now and on real data later.
- Tests: hand-computed toy example; shape of values/counts is 4×24; season mapping per the contract.
- `make analysis` runs this.

Finish: run `make test`, update the FE-2 Progress log, commit on branch fe2/error-decomp, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** heatmap values higher at peak hours/summer for the mock? (Real data later.)

### FE-2 · Increment 2 of 7 — Missed-peak analysis
**Needs:** Increment 1 merged; `peak_predictions.parquet` exists (mock now; real after BE-1 Increment 9).

```
Increment 2 of 7 — missed-peak analysis.

src/analysis/missed_peaks.py reading artifacts/peak_predictions.parquet (+ load_hourly.parquet and features_known.parquet) and writing artifacts/missed_peaks.json exactly per docs/02_API_CONTRACT.md section 1.9.
- Include every day with outcome == "miss" for each model (default focus: ensemble), sorted by absolute magnitude_error_mw descending.
- Auto-tag each day with rules (document thresholds in docs/ASSUMPTIONS.md): "festival" (cal_is_festival_window), "holiday" (cal_is_holiday), "heatwave" (max wx_temp_c that day above the 95th percentile of that season's daily max temps from the training period), "weather_miss" (actual daily max temperature differs from the weather proxy used for the forecast by > 2 °C; if not computable, omit this tag), "weekend", else "other".
- Write a one-line "note" per item generated from the tags and numbers (e.g. "Actual max temp 3.1 °C above the weather proxy; peak shifted 7 h later than predicted"). Notes must come from the data, never invented.
- Tests: sorting, tag rules on toy rows, note contains the right numbers.
`make analysis` now runs Increments 1 and 2.

Finish: run `make test`, update the FE-2 Progress log, commit on branch fe2/missed-peaks, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read five notes — do they make sense given the numbers?

### FE-2 · Increment 3 of 7 — Accuracy page
**Needs:** FE-1 Increment 1 (shell) merged; mock API running.

```
Increment 3 of 7 — Accuracy page (ui/src/pages/Accuracy). Only edit ui/src/pages/Accuracy and ui/src/components/eval/.

- Data: GET /backtest/metrics (all rows) and GET /backtest/peak-metrics.
- Controls: segment dropdown (all, winter, summer, monsoon, post_monsoon, peak_hours, off_peak) and a metric toggle (MAPE / RMSE / MAE / bias / pinball).
- Main table: rows = models, columns = horizon_day 1…7 and "all", cell = chosen metric; below each cell (or in a second table) the % improvement vs seasonal-naive with green/red colouring (baseline row shows "—"). Highlight the best model per column. Sticky header and first column; sortable.
- Calibration table: picp_80 and picp_90 per model and horizon_day with a visual marker against the 0.80 / 0.90 targets, plus mpiw_80_mw. Label clearly: P10–P90 = 80% interval, P05–P95 = 90% interval. If calibration_comparison exists in the metrics JSON, show before vs after.
- Peak events card: precision, recall, F1, PR-AUC, confusion matrix (2×2), timing MAE, % within ±1 h, magnitude MAE/bias — for the classifier vs the rule baseline side by side.
- A small note about MAPE's weakness at low loads (winter nights) near the MAPE toggle.
- Loading/empty/error states.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/accuracy, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** numbers match what BE-2 printed in the console for the same segment.

### FE-2 · Increment 4 of 7 — Error heatmap page
**Needs:** Increments 1 and 3 merged.

```
Increment 4 of 7 — Error heatmap page (ui/src/pages/ErrorHeatmap). Only edit ui/src/pages/ErrorHeatmap and ui/src/components/eval/.

- Data: GET /backtest/error-heatmap?model=&metric=&horizon_day=.
- Controls: ModelSelect, metric toggle (MAPE / RMSE / bias), horizon-day select (1 … 7, All).
- Plotly heatmap: x = hour of day (0–23), y = season (winter, summer, monsoon, post_monsoon); colour scale sequential for mape/rmse, diverging centred at 0 for bias; colour bar with units; hover shows value, observation count and the hour range; null cells shown as hatched/grey with "too few observations".
- Highlight the peak-hour columns (6–10 and 19–23) with subtle outlines or a band above the plot.
- Under the chart, auto-generated plain-language callouts computed from the data: "worst cell", "best cell", and whether peak hours are worse than off-peak on average (percentage difference).
- Optional compare mode: show two models side by side (e.g. ensemble vs seasonal_naive) with a shared colour scale.
- Loading/empty/error states (NOT_FOUND → friendly message).

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/heatmap, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** diverging bias colours centred on 0; callouts match the grid.

### FE-2 · Increment 5 of 7 — Missed peaks page
**Needs:** Increments 2 and 3 merged; FE-1 Increment 2 (Forecast page with ?date=) merged.

```
Increment 5 of 7 — Missed peaks page (ui/src/pages/MissedPeaks). Only edit ui/src/pages/MissedPeaks and ui/src/components/eval/.

- Data: GET /backtest/missed-peaks (paginate with limit/offset) and GET /peak/events?outcome=false_alarm for a secondary tab.
- Controls: ModelSelect, tag filter chips (festival, holiday, heatwave, weather_miss, weekend, other; multi-select), and a toggle "Misses / False alarms".
- Table: date, season, peak probability, predicted vs actual peak time, predicted p50 vs actual MW, magnitude error (MW, coloured), timing error (minutes), tag chips, note. Sort by magnitude error by default; sortable columns.
- Summary strip above the table: number of missed peaks, share by tag, mean magnitude error.
- Row click → drill-down panel (drawer or inline) that embeds a compact version of the day chart (call GET /forecast/day-ahead?date=… and plot actual line + P10–P90 + P05–P95 + predicted vs actual peak marker) and a "Open in Forecast page" button linking to /forecast?date=YYYY-MM-DD&model=…
- Empty state for "no misses" and for filters with no results.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/missed-peaks-ui, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** click three rows including one with `null` actuals; the Forecast link opens the right day.

### FE-2 · Increment 6 of 7 — Insights page
**Needs:** BE-2 Increment 10 (feature importance) merged or mock available; Increment 7 can run after.

```
Increment 6 of 7 — Insights page (ui/src/pages/Insights). Only edit ui/src/pages/Insights and ui/src/components/eval/.

- Data: GET /models, GET /models/{model}/feature-importance?top=20, GET /meta.
- Section 1 — "What drives the forecast": horizontal bar chart of the top 20 features for the selected model (ModelSelect limited to models with importances), bars coloured by feature group (calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon) with a legend, plus a grouped summary (share of total importance per group).
- Section 2 — "Why peaks are hard": render docs/WHY_PEAKS_ARE_HARD.md as formatted text with its figures. Since the UI can't read repo files directly, copy the markdown and figure PNGs at build time into ui/public/insights/ via a small script (scripts/sync_insights.sh) and fetch them as static assets; show a friendly placeholder if the file doesn't exist yet.
- Section 3 — "Model card summary": render the first sections (assumptions, known limits) from docs/MODEL_CARD.md the same way, plus key facts from /meta (data range, backtest range, weather_proxy_note).
- Loading/empty/error states.

Finish: run the type check and build, update the FE-2 Progress log, commit on branch fe2/insights, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the page doesn't crash when the markdown files don't exist yet.

### FE-2 · Increment 7 of 7 — Model card + "why peaks are hard"
**Needs:** BE-2 Increment 9 (ensemble) and BE-1 Increment 9 (final peak file) merged; real artifacts available.

```
Increment 7 of 7 — the two analysis documents, with REAL numbers from the backtest.

1) docs/WHY_PEAKS_ARE_HARD.md. Add scripts/make_peak_analysis.py that produces reproducible figures into docs/figures/ and prints the numbers used:
 - Weather sensitivity: MW change per +1 °C in daily max temperature (or CDH) on peak-hour load, by season, estimated from the data (e.g. a simple regression with calendar controls); show a scatter with fit.
 - Thermal inertia: correlation of evening-peak load with temperature at lags 0, 3, 6, 12, 24, 48, 72 h (and rolling 24h/72h means), shown as a bar chart; explain what it means for peaks shifting late on hot days.
 - Festival/holiday effects: average load deviation (vs a same-weekday, same-month baseline) in Diwali/Holi/Eid windows compared with normal days, with sample sizes and a caution when n is small.
 - Error evidence: how forecast error at peak_hours compares with off_peak for the ensemble and the baseline (use metrics_accuracy.json) and 2–3 missed-peak case studies from missed_peaks.json.
 Keep it to ~1.5 pages. Every number and figure must be generated by the script; no invented claims; state limits (weather proxy, short samples).
2) docs/MODEL_CARD.md: intended use; data (source, range, imputation summary from docs/DATA_QUALITY.md); features; models and how they were trained; backtest protocol (frozen, from docs/03_PRD.md section 9); results summary table (ensemble vs baselines at D+1 and D+7, all vs peak_hours, PICP 80/90); peak classifier results; limitations and known failure modes (weather proxy, festival data sparsity, structural changes, outage effects, tariff placeholders); ethical/operational notes (decision support, not automated dispatch). Link to the generated figures and artifacts.
3) Run scripts/sync_insights.sh if it exists so the UI picks up the new files.

Finish: update the FE-2 Progress log, commit on branch fe2/docs, and list the files that changed. Then stop.
```
**Review:** every number in the docs traces to a file in `artifacts/` or a printed script output. Run the script again and confirm the figures regenerate identically.