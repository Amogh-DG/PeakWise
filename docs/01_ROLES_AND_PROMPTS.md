# 01 — Stack, Team Split & Antigravity Prompts

Project (working name): **PeakWise** — probabilistic, peak-aware load forecasting + procurement copilot for Delhi's DISCOM (CodeSpark 2026, PS 2).

Source-of-truth docs (put all three in `/docs` of the repo):
- `01_ROLES_AND_PROMPTS.md` (this file) — who does what
- `02_API_CONTRACT.md` — file schemas + REST API (frozen at Checkpoint 0)
- `03_PRD.md` — what we're building, definitions, metrics, deliverables

---

## 1. Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 (data/ML/API), TypeScript (UI) | One ML language, typed UI |
| Data handling | pandas + pyarrow (Parquet) | Simple, fast enough; no DB needed |
| Weather | Open-Meteo historical API (free, no key) for Delhi (28.61, 77.21); NASA POWER as fallback | Hourly temp, humidity, dewpoint, wind, cloud. Verify coverage for your date range |
| Calendar | `holidays` package (India) + hand-built `festivals.csv` | Lunar festivals (Diwali, Holi, Eid) need exact dates; library coverage is patchy |
| Baselines | seasonal-naive (same hour last week), scikit-learn LinearRegression | Required by the PS |
| Main model | **LightGBM** with quantile objective (q = 0.05, 0.1, 0.5, 0.9, 0.95) | Fast, strong, native quantiles |
| Comparison models | XGBoost, `prophet` (holiday-aware), one deep model: LSTM (cheap) or TFT via `pytorch-forecasting` | PS asks for these; time-box the deep model |
| Ensemble | Weighted quantile averaging, weights fit on a validation window only | "Stacked/ensemble is a plus" |
| Calibration | Conformalized quantile regression (rolling calibration window) | Fixes PICP so intervals are honest |
| Peak classifier | LightGBM classifier + isotonic calibration | Separate model, precision/recall framing |
| Explainability | SHAP / gain importance | Feature-importance deliverable |
| Backend | **FastAPI + Pydantic v2**, serves precomputed artifacts (+ procurement function live) | Never train on request; API stays instant |
| Frontend | **Vite + React + TypeScript + Tailwind + Plotly.js** | Plotly gives shaded bands + heatmap natively. *Fallback:* Streamlit if UI is behind at Checkpoint 2 |
| Orchestration | `Makefile` + `config.yaml` | One-command reproducibility |
| Packaging | Docker Compose (`api` + `ui`) | One command to demo anywhere |
| Tests | pytest (schema checks, no-leakage checks, contract tests) | Catches vibe-code drift |

**Architecture in one line:** `raw data → clean → features → backtest/train → artifacts/ (parquet+json) → FastAPI → React dashboard`. Anything the dashboard shows is read from `artifacts/`.

---

## 2. The four roles

| Role | Owns | Hands off to |
|---|---|---|
| **A — Data & Feature Engineer** | Ingestion, cleaning, imputation, calendar/weather features, data-quality doc | B, C |
| **B — Forecasting Modeler** | Backtest harness, baselines, LightGBM/XGB/Prophet/LSTM, ensemble, calibration, metrics lib | C, D |
| **C — Peak, Procurement & Analysis Lead** | Peak classifier, procurement advisor, error decomposition, model card, memo, write-up | D |
| **D — Backend, Dashboard & Integration Lead** | Repo scaffold, FastAPI, React dashboard, Docker, demo, submission packaging | everyone (integrates) |

```
A ──► B ──► C ──► D
 └────────►┘      ▲
   (D builds against mocks from hour 0, swaps to real artifacts as they land)
```

### Handoff artifacts (schemas in `02_API_CONTRACT.md` §1)

| File | Producer | Consumers |
|---|---|---|
| `data/processed/load_hourly.parquet` | A | B, C |
| `data/processed/features_known.parquet` | A | B, C |
| `src/features/ar_features.py` (`build_ar_features`) | A | B, C |
| `artifacts/predictions_backtest.parquet` | B | C, D |
| `artifacts/metrics_accuracy.json` | B | D |
| `artifacts/feature_importance.json` | B | D |
| `artifacts/peak_predictions.parquet`, `metrics_peak.json` | C | D |
| `artifacts/error_heatmap.json`, `missed_peaks.json` | C | D |
| `artifacts/procurement_defaults.json`, `src/procurement/advisor.py` | C | D |
| `artifacts/meta.json` | D assembles (A/B/C contribute fields) | D |

### Folder ownership (don't edit other people's folders without a heads-up)

```
data/ , src/data/ , src/features/ , docs/DATA_QUALITY.md     → A
src/models/ , src/backtest/ , src/metrics/ , models/          → B
src/peak/ , src/procurement/ , src/analysis/ , docs/MODEL_CARD.md,
docs/PROCUREMENT_MEMO.md , docs/WHY_PEAKS_ARE_HARD.md         → C
api/ , ui/ , docker-compose.yml , Makefile , README.md,
docs/DEMO_SCRIPT.md , scripts/make_mock_artifacts.py          → D
artifacts/ , config.yaml , docs/ASSUMPTIONS.md                → shared (append-only for assumptions)
```

---

## 3. Shared prompt — everyone pastes this FIRST into Antigravity

```
You are helping build "PeakWise" — a probabilistic, peak-aware load forecasting and procurement copilot for Delhi's DISCOM (hackathon problem statement PS 2).

Before doing anything, read docs/03_PRD.md, docs/02_API_CONTRACT.md and docs/01_ROLES_AND_PROMPTS.md. They are the source of truth. Do NOT change the API contract, file schemas, column names, or definitions without telling me first — teammates are building against them.

I own role: <A | B | C | D>. Only edit the folders my role owns (see "Folder ownership" in the roles doc) unless I say otherwise.

Working rules:
1. Work in small increments. After EACH increment: run it, run the tests, update the "Progress log" section in README.md (what works, how to run it, what's next, known issues) so a fresh session can resume from the README alone, then tell me which files changed and where to download them. Keep code out of the chat — put it in files.
2. Don't stop to ask whether to continue. Move to the next increment in the plan unless you are blocked by a decision only I can make; if so, state the decision and your recommended default.
3. Time-series integrity: never random-split. Every feature must be computable at the forecast origin time (10:00 IST on D0 for targets D+1 00:00 onward). No leakage from the future.
4. Python 3.11, type hints, pytest, config in config.yaml, no hardcoded paths, fixed random seeds.
5. Any assumption or invented number goes into docs/ASSUMPTIONS.md with a one-line reason. Never silently make up data.
6. Prefer simple and working over clever. A working end-to-end slice beats a perfect component.
```

---

## 4. Role A — Data & Feature Engineer

**Mission:** Give everyone clean, gap-free hourly load + a leak-safe feature set, and document every data-quality decision.

### Tasks
1. **Mock data first (first 1–2 hours):** `scripts/make_mock_data.py` generates a synthetic Delhi-like hourly load (≈2,000 MW winter → 8,300 MW summer, morning ramp 6–10, evening peak 19–23, weather-sensitive) in the exact `load_hourly` + `features_known` schema, so B/C aren't blocked.
2. **Source real data:** hourly (or finer) Delhi demand, 2+ years. Try the dataset the organizers gave, Delhi SLDC historical demand reports, Grid-India (POSOCO) reports, Kaggle. **If only daily peaks exist, tell the team immediately** (changes the plan). Record source + licence in `data/raw/README.md`.
3. **Weather:** Open-Meteo archive for Delhi — temperature, relative humidity, dewpoint, wind, cloud cover, hourly. Keep raw pulls in `data/raw/`.
4. **Clean:**
   - Reindex to a complete hourly `Asia/Kolkata` index (hour-beginning). India has no DST, but still check for duplicate/missing/shifted timestamps from the source and document what you found.
   - Gaps ≤ 3h: linear interpolation. Longer gaps: fill from the same hour-of-week in neighbouring weeks (seasonal profile). Always set `is_imputed` and `imputation_method`.
   - Outliers/outage drops: flag with a robust z-score (MAD) on residuals vs the hour-of-week profile → `is_outage_suspect`. Don't delete. B will zero-weight them in training and still report them in evaluation.
   - Write `docs/DATA_QUALITY.md`: gap counts, % imputed, methods, outlier rules, examples.
5. **Features (`features_known.parquet`, names in contract §1.2):**
   - Calendar: hour, day-of-week, month, day-of-year, sin/cos encodings, weekend, public holiday.
   - Festivals: `data/external/festivals.csv` (Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Independence Day, etc.) → `days_to_*` / `days_since_*` windows. Cite where the dates came from.
   - Event flags: lockdown periods and Delhi odd-even scheme rounds (research the dates, cite sources, only matters if your data covers them).
   - Weather-derived: heat index (Rothfusz regression), cooling-degree-hours (configurable base, default 24 °C, plus a rolling 24h sum), temperature lags (1, 3, 6, 12, 24, 48, 72 h), rolling mean temperature (24h, 72h) for thermal inertia.
   - Growth trend: `trend_t` (days since start).
6. **Autoregressive features:** `build_ar_features(load_df, origin_ts, target_ts)` in `src/features/ar_features.py`. **Lags are relative to the forecast origin**, not the target: at 10:00 D0 the latest known load is 09:00 D0. Provide same-hour-last-week, same-hour-yesterday-if-known, trailing 7-day mean, trailing 365-day mean level. B and C call this.
7. **Weather-forecast leakage:** day-ahead forecasts using *actual* weather are optimistic. Default plan: use actuals as a proxy and add horizon-scaled Gaussian noise (`config.yaml: weather_noise`, on by default). If the Open-Meteo historical-forecast API covers your range, use that instead. Document the choice in `ASSUMPTIONS.md` and the model card.
8. **Tests:** index complete + unique + monotonic; no NaNs after imputation; schema matches contract; a leakage test proving AR features at origin T use only data < T.

### Definition of done
`make data` and `make features` run from scratch; both parquet files match the contract; `DATA_QUALITY.md` exists; leakage test passes.

### Antigravity kickoff prompt (after the shared prompt)

```
I am Role A (Data & Feature Engineer). Build the data and feature pipeline for PeakWise.

Increment 1: scripts/make_mock_data.py that writes data/processed/load_hourly.parquet and data/processed/features_known.parquet in the exact schema from docs/02_API_CONTRACT.md section 1, with realistic synthetic Delhi load (winter ~2,000 MW, summer ~8,300 MW peak, morning ramp 6-10, evening peak 19-23, temperature-driven, weekday/weekend effect, a few festival dips). 3 years hourly, Asia/Kolkata index. Add pytest schema tests.
Increment 2: src/data/ingest_load.py and ingest_weather.py (Open-Meteo archive for Delhi 28.61, 77.21; cache raw pulls in data/raw/). If real load data is unavailable, stop and tell me exactly what I need to download.
Increment 3: src/data/clean.py — complete hourly index, gap imputation (<=3h linear; longer = same hour-of-week neighbours), is_imputed / imputation_method / is_outage_suspect (MAD z-score on residual vs hour-of-week profile). Write docs/DATA_QUALITY.md with real numbers.
Increment 4: src/features/build_known.py — all calendar, festival (data/external/festivals.csv with cited dates), event-flag, heat-index, cooling-degree-hour, temperature-lag, rolling-temperature and trend features, using the column names in the contract.
Increment 5: src/features/ar_features.py with build_ar_features(load_df, origin_ts, target_ts) where lags are relative to the forecast origin (10:00 IST on D0), plus a pytest leakage test.
Increment 6: weather-noise option for day-ahead realism (config.yaml: weather_noise) and document it in docs/ASSUMPTIONS.md.
Wire everything to `make data` and `make features`.
```

---

## 5. Role B — Forecasting Modeler

**Mission:** Produce honest, calibrated P05–P95 hourly forecasts for D+1 (24h) and D+1…D+7 (168h) that demonstrably beat the baselines — especially at peak hours.

### Tasks
1. **Backtest harness first** (`src/backtest/`): rolling-origin, expanding window. Origin = 10:00 IST every day; targets = D+1 00:00 … D+7 23:00 (horizons 14–181 h). Min train 2 years (adjust to your data), retrain monthly, test on the last ≥ 12 months (or all that's available after the min-train window). Model-agnostic interface:
   ```python
   class Forecaster(Protocol):
       name: str
       def fit(self, train_end: Timestamp) -> None: ...
       def predict(self, origin: Timestamp) -> DataFrame  # target_ts, horizon_h, p05,p10,p50,p90,p95
   ```
   Writes `artifacts/predictions_backtest.parquet` (contract §1.4).
2. **Baselines:** seasonal-naive (same hour last week) and linear regression (quantiles from residual quantiles by hour). Run these end-to-end *before* anything else.
3. **LightGBM quantile:** one model per quantile with `horizon_h` as a feature; sort quantiles to prevent crossing. Zero-weight `is_outage_suspect` rows in training.
4. **XGBoost** (comparison, optional), **Prophet** (holidays + temperature regressor), **one deep model** (LSTM or TFT, quantile loss). Time-box the deep model; if it isn't beating LightGBM, ship it as a documented comparison anyway.
5. **Ensemble:** weighted quantile average; weights fit on a validation window that ends before the test window.
6. **Calibration:** conformalized quantile regression on a rolling calibration window; keep raw (`*_raw`) and calibrated columns; report PICP before/after for the 80% interval (P10–P90) and the 90% interval (P05–P95).
7. **Metrics library** (`src/metrics/`, C reuses it): MAPE (per horizon-day, note low-load weakness), RMSE, MAE, bias, pinball loss, PICP, MPIW, % improvement vs seasonal-naive. Output `metrics_accuracy.json` per contract §1.6 (rows by model × horizon_day × segment).
8. **Feature importance:** SHAP/gain for LightGBM → `feature_importance.json`.

### Definition of done
`make backtest` regenerates predictions + metrics for all models; accuracy table covers every model × horizon-day × segment (all, 4 seasons, peak_hours, off_peak); every model beats or is explicitly flagged against seasonal-naive; PICP reported.

### Antigravity kickoff prompt

```
I am Role B (Forecasting Modeler). Build the backtest harness and models for PeakWise. Use data/processed/*.parquet (mock data from Role A is fine until real data lands).

Increment 1: src/backtest/ — rolling-origin expanding-window harness (origin 10:00 IST daily, targets D+1 00:00 to D+7 23:00, retrain monthly, min train 2 years configurable), a Forecaster protocol (fit(train_end), predict(origin) -> target_ts, horizon_h, p05, p10, p50, p90, p95), and a writer for artifacts/predictions_backtest.parquet exactly per docs/02_API_CONTRACT.md section 1.4.
Increment 2: baselines — seasonal-naive (same hour last week) and linear regression with residual-quantile intervals. Run through the harness.
Increment 3: src/metrics/ — MAPE, RMSE, MAE, bias, pinball, PICP (80% and 90%), MPIW, % improvement vs seasonal-naive, segmented by horizon_day (1..7), season, peak_hours, off_peak. Write artifacts/metrics_accuracy.json per contract 1.6. Print the table.
Increment 4: LightGBM quantile models (q 0.05, 0.1, 0.5, 0.9, 0.95; horizon_h as a feature; sort to avoid quantile crossing; zero weight on is_outage_suspect rows in training). Add to the table.
Increment 5: conformalized quantile regression calibration on a rolling calibration window; save raw and calibrated columns; report PICP before/after.
Increment 6: Prophet (holidays + temperature regressor) and XGBoost comparison.
Increment 7: one deep model (LSTM with quantile loss), time-boxed to a simple version.
Increment 8: ensemble (weighted quantile average, weights fit on a validation window ending before the test window).
Increment 9: SHAP/gain feature importance -> artifacts/feature_importance.json.
Wire to `make backtest`. Report the accuracy table after each increment.
```

---

## 6. Role C — Peak, Procurement & Analysis Lead

**Mission:** Turn forecasts into decisions: flag peak days and timing, price the risk, and explain where/why the model fails.

### Tasks
1. **Peak-event classifier** (`src/peak/`): label = day's peak MW > threshold, where threshold = 90th percentile of daily peaks **in the training window of each fold** (config option for season-relative threshold as a variant). Model: LightGBM classifier on origin-safe features + forecast summaries (P50/P90 daily max from B), isotonic-calibrated probability. Peak *hour*: LightGBM multiclass over 24 hours, with `argmax(P50 hourly forecast)` as a baseline. Tune the decision threshold for recall (missing a peak is costlier than a false alarm) and document the precision/recall trade-off. Compare against a rule baseline (e.g. "same weekday last week exceeded threshold"). Output `peak_predictions.parquet` + `metrics_peak.json` (precision, recall, F1, PR-AUC, confusion, timing MAE in minutes, % within ±1h, magnitude MAE/bias in MW). If data is finer than hourly, use the native resolution for timing error.
2. **Procurement advisor** (`src/procurement/advisor.py`): implements `recommend(start_date, days, model, risk_quantile, tariff)` per contract §2.12.
   - Schedule = forecast quantile `risk_quantile` (default 0.9, or `"newsvendor"` = critical ratio `c_u/(c_u+c_o)`).
   - Cost per hour = `da_price·S + under_price·max(D−S,0) − resale_price·max(S−D,0)`.
   - Compare against a naive flat schedule (previous week's mean MW; also report "flat at previous week's peak").
   - `p90_risk_exposure_inr` = extra cost if demand follows the P90 path vs the P50 path.
   - Tariff numbers are **illustrative placeholders** — label them as such in the memo and `ASSUMPTIONS.md`.
3. **Error decomposition** (`src/analysis/`): by season, hour, peak vs off-peak; `error_heatmap.json` (hour × season, metrics: mape, rmse, bias); `missed_peaks.json` with auto-tags (festival, holiday, heatwave, weather-miss, weekend) via simple rules.
4. **Docs:**
   - `docs/MODEL_CARD.md` — assumptions, data, limits, known failure modes, weather-proxy caveat.
   - `docs/PROCUREMENT_MEMO.md` — sample week: recommended schedule, P90 exposure, simulated cost vs flat.
   - `docs/WHY_PEAKS_ARE_HARD.md` — weather sensitivity (MW per °C at peak hours), festival effects, thermal inertia (lagged-temperature correlation), with figures computed from the data.

### Definition of done
Peak metrics + baseline comparison exist; `recommend()` matches the contract and has unit tests; heatmap/missed-peak JSONs exist; all three docs written with real numbers from the backtest.

### Antigravity kickoff prompt

```
I am Role C (Peak, Procurement & Analysis). Build against artifacts/predictions_backtest.parquet (mock from Role B is fine until real predictions land) and the schemas in docs/02_API_CONTRACT.md.

Increment 1: src/peak/ — daily peak labels with a per-fold threshold (90th percentile of daily peaks in that fold's training window), a LightGBM classifier with isotonic-calibrated probability, evaluated walk-forward with the same fold structure as Role B. Add the rule baseline (same weekday last week exceeded threshold). Output artifacts/peak_predictions.parquet and artifacts/metrics_peak.json per the contract. Report precision, recall, F1, PR-AUC, confusion matrix; tune the decision threshold for recall and document the trade-off.
Increment 2: peak-hour prediction (multiclass over 24 hours + argmax-of-P50 baseline), timing error in minutes and % within +-1h, magnitude error in MW.
Increment 3: src/procurement/advisor.py implementing recommend(start_date, days, model, risk_quantile, tariff) exactly per contract section 2.12, including the newsvendor quantile option, flat-schedule baselines, and p90_risk_exposure_inr. Unit tests with hand-computed numbers. Write artifacts/procurement_defaults.json (illustrative tariff placeholders, flagged in docs/ASSUMPTIONS.md).
Increment 4: src/analysis/ — error decomposition by season, hour, peak vs off-peak; artifacts/error_heatmap.json (hour x season for mape, rmse, bias per model and horizon_day) and artifacts/missed_peaks.json with rule-based tags (festival, holiday, heatwave, weather-miss, weekend).
Increment 5: docs/MODEL_CARD.md, docs/PROCUREMENT_MEMO.md (sample week, schedule, P90 exposure, cost vs flat), docs/WHY_PEAKS_ARE_HARD.md (weather sensitivity MW per degree C at peak hours, festival effects, thermal inertia with lagged-temperature evidence). Use real numbers from the artifacts and generate the figures with scripts so they are reproducible.
Wire to `make peak`, `make analysis`, `make docs`.
```

---

## 7. Role D — Backend, Dashboard & Integration Lead

**Mission:** Make everything runnable with one command and presentable; keep the team integrated.

### Tasks
1. **Scaffold (hour 0):** monorepo layout, `Makefile` (`make data features backtest peak analysis api ui all`), `docker-compose.yml`, `config.yaml`, `requirements.txt` (pinned), README with a **Progress log** + "how to resume" section, CI-lite (pytest + lint).
2. **Mock artifacts:** `scripts/make_mock_artifacts.py` writes every file in `artifacts/` in contract shape so the API and UI work from day one.
3. **FastAPI (`api/`):** Pydantic models mirror the contract exactly; reads `artifacts/` at startup; `MOCK=1` mode; calls `src/procurement/advisor.py` for `/procurement/recommend`; contract tests validate every response against the models.
4. **Dashboard (`ui/`)** — six screens:
   1. **Forecast:** date picker, day/week toggle, model selector; actual line, P10–P90 shaded band (+ lighter P05–P95), peak markers (predicted vs actual), at-risk hours highlighted.
   2. **Accuracy:** table vs baselines per horizon-day with % improvement; peak precision/recall card.
   3. **Error heatmap:** hour × season, toggle mape/rmse/bias.
   4. **Missed peaks drill-down:** list with tags → click → that day's chart.
   5. **Procurement:** week picker, risk-quantile slider (or newsvendor), editable tariff, schedule vs flat chart, cost comparison, P90 exposure.
   6. **Insights:** feature importance + "why peaks are hard" write-up.
5. **Integration:** weekly end-to-end smoke test; deployed URL (Render/Railway or similar) plus local docker-compose fallback; `docs/DEMO_SCRIPT.md` (3-minute story: problem → tail risk → peak flag → procurement savings); submission checklist (PRD §12).

### Definition of done
`docker compose up` serves API + UI; all six screens run on real artifacts; contract tests pass; demo script rehearsed.

### Antigravity kickoff prompt

```
I am Role D (Backend, Dashboard & Integration). I also scaffold the repo.

Increment 1: monorepo scaffold — folders per the "Folder ownership" section of docs/01_ROLES_AND_PROMPTS.md, Makefile (data, features, backtest, peak, analysis, api, ui, all), docker-compose.yml (api + ui), config.yaml, pinned requirements.txt, README.md with a Progress log and "How to resume" section, a pytest + lint CI-lite script.
Increment 2: scripts/make_mock_artifacts.py generating every file in artifacts/ in the exact shapes from docs/02_API_CONTRACT.md section 1 (realistic synthetic numbers; 3 seasons of backtest; P05<P10<P50<P90<P95 always).
Increment 3: FastAPI app in api/ implementing EVERY endpoint in contract section 2 with Pydantic v2 response models mirroring the contract, reading artifacts/ at startup, MOCK=1 mode, error format from contract section 3, CORS for the UI. /procurement/recommend calls src/procurement/advisor.py:recommend (stub it until Role C lands it). Add contract tests (pytest) that hit every endpoint and validate against the models.
Increment 4: Vite + React + TypeScript + Tailwind + Plotly.js app in ui/ with the typed API client generated from the contract. Screen 1 (Forecast): date picker, day/week toggle, model selector, actual line, shaded P10-P90 band plus lighter P05-P95, peak markers, at-risk hours highlighted.
Increment 5: Screen 2 (Accuracy table vs baselines + peak precision/recall card) and Screen 3 (hour x season error heatmap with metric toggle).
Increment 6: Screen 4 (missed-peaks list with tags and click-through drill-down) and Screen 5 (procurement: week picker, risk-quantile slider with newsvendor option, editable tariff, schedule vs flat chart, cost comparison, P90 exposure).
Increment 7: Screen 6 (feature importance + render docs/WHY_PEAKS_ARE_HARD.md), loading/error states, responsive polish, dark mode optional.
Increment 8: Dockerize, deploy, write docs/DEMO_SCRIPT.md, run the submission checklist in docs/03_PRD.md section 12.
If the UI falls behind at Checkpoint 2, tell me and we switch to a Streamlit fallback that calls the same API.
```

---

## 8. Sync checkpoints

| # | When | Everyone confirms |
|---|---|---|
| **0** | First 1–2 hours | Read all 3 docs; contract frozen; repo scaffolded; mock data + mock artifacts exist; open decisions (PRD §13) settled |
| **1** | End of Phase 1 | Real data cleaned; baselines + backtest harness run; API serves mock → real baselines; first dashboard screen live |
| **2** | End of Phase 2 | LightGBM quantile + calibration done; peak classifier v1; UI screens 1–3 on real artifacts. **Streamlit-fallback decision here** |
| **3** | End of Phase 3 | Prophet/LSTM/ensemble in; procurement + heatmap + drill-down live |
| **4** | ~80% of time | **Feature freeze.** Only docs, bug fixes, demo polish |
| **5** | Last block | Fresh-clone test (`docker compose up` on a clean machine), demo rehearsal, submission packaged |

**Phases:** 0 = contract + scaffold + mocks → 1 = data + baselines + API-on-mocks → 2 = GBM + calibration + peak v1 + core UI → 3 = extra models + procurement + analysis UI → 4 = docs, memo, write-up, polish → 5 = rehearse + submit.

---

## 9. Repo layout

```
peakwise/
├─ README.md                  # Progress log + how to resume (D keeps it current)
├─ Makefile  config.yaml  docker-compose.yml  requirements.txt
├─ docs/    01_ROLES_AND_PROMPTS.md  02_API_CONTRACT.md  03_PRD.md
│           ASSUMPTIONS.md  DATA_QUALITY.md  MODEL_CARD.md
│           PROCUREMENT_MEMO.md  WHY_PEAKS_ARE_HARD.md  DEMO_SCRIPT.md
├─ data/    raw/  external/festivals.csv  processed/
├─ src/     data/  features/  models/  backtest/  metrics/
│           peak/  procurement/  analysis/
├─ models/                    # saved model files
├─ artifacts/                 # everything the API serves (parquet + json)
├─ scripts/ make_mock_data.py  make_mock_artifacts.py
├─ api/                       # FastAPI
├─ ui/                        # Vite + React + TS
└─ tests/
```
