# Antigravity Prompts: Two People, One Per Increment

33 increments split across two people: Person A has 16 (A-1 to A-16), Person B has 17 (B-1 to B-17).

A: data, features, models, backtest, metrics, mock data, repo scaffold.
B: API, peak classifier, procurement, analysis, whole UI, deploy, docs.

## 1. How to use

1. Open a fresh Antigravity session. Paste the shared prompt (section 3) once, with your letter filled in.
2. Paste one increment prompt. The agent does only that increment, reports, and stops.
3. Review using the Review line under the prompt. If something is off, paste the error and fix it before moving on.
4. Merge to main yourself, tell the other person, then paste the next prompt.
5. New session mid-way: paste the shared prompt, then say "Read my Progress-log section in README.md, then continue with the next increment below" and paste the next prompt.

Each prompt names the files to write, the functions to expose and the contract sections to follow. Don't skip numbers; later prompts assume earlier ones are merged. "Needs" lists what must already be merged before you paste a prompt.

Ignore file: the agents are told nothing about version control. Create the repo-root ignore file yourself with these entries: data/raw/, data/processed/, models/, artifacts/ (see note), __pycache__/, node_modules/, .venv/, ui/dist/, .pytest_cache/, .ruff_cache/. Do NOT ignore artifacts_mock/ or data/processed_mock/ (they are committed). For artifacts/: ignore it while developing, and remove that entry when B-15 says the real artifacts are final, so the deploy has them.

## 2. Ownership and merge rules

Roles: A and B. Everything below is exact so the two halves merge without edits.

### 2.1 Folder and file ownership

A owns:
- src/common/, src/data/, src/features/, src/models/, src/backtest/, src/metrics/
- scripts/make_mock_data.py, scripts/make_mock_artifacts.py, scripts/__init__.py
- make/a.mk, requirements-a.txt, requirements-deep.txt, requirements.txt
- tests/conftest.py, tests/test_smoke.py, tests/test_artifact_schemas.py, and every test for A's code
- data/, models/, artifacts_mock/, data/processed_mock/
- docs/DATA_QUALITY.md, docs/ASSUMPTIONS_A.md
- the real-model artifacts: load_hourly.parquet, features_known.parquet, predictions_backtest.parquet, metrics_accuracy.json, feature_importance.json, feature_importance_by_segment.json, daily_peak_summary.parquet

B owns:
- api/, src/peak/, src/procurement/, src/analysis/, ui/
- scripts/make_procurement_memo.py, scripts/make_peak_analysis.py, scripts/sync_insights.sh
- make/b.mk, requirements-b.txt, docker-compose.yml (after A-1), api/Dockerfile, ui/Dockerfile, ui/nginx.conf
- tests for B's code: test_contract.py, test_peak_*.py, test_advisor.py, test_analysis_*.py
- docs/ASSUMPTIONS_B.md, docs/PROCUREMENT_MEMO.md, docs/DEMO_SCRIPT.md, docs/WHY_PEAKS_ARE_HARD.md, docs/MODEL_CARD.md, docs/figures/, docs/screenshots/
- the B artifacts: peak_predictions.parquet, metrics_peak.json, error_heatmap.json, missed_peaks.json, procurement_defaults.json, meta.json

Docs 02_API_CONTRACT.md and 03_PRD.md already exist in docs/. A may edit the contract only in A-12 (adds section 1.13 and a change-log row). B reports contract deviations to A instead of editing.

### 2.2 Shared files, merge-safe by design

- Makefile (root) is created by A-1 and never edited again. It only does `include make/a.mk` and `include make/b.mk` and defines `test` and `all`. A edits make/a.mk (targets: mock, data, features, backtest). B edits make/b.mk (targets: peak, analysis, api, ui).
- requirements.txt contains only `-r requirements-a.txt` and `-r requirements-b.txt`. Everyone installs from requirements.txt.
- config.yaml: A-1 writes the complete file with every key below. After that, nobody adds new top-level keys. A may change values only under data, cleaning, features, backtest, weather_noise, models, calibration. B may change values only under peak, procurement, api. If you need a new key, add it inside your own block.
- README.md: A-1 creates it with fixed headings. A edits only: top matter, "How to run", "How to resume", "Results", and the A subsection of the Progress log (between `<!-- A-PROGRESS-START -->` and `<!-- A-PROGRESS-END -->`). B edits only: "How to run the UI", "Deployment", "Submission checklist", and the B subsection (between `<!-- B-PROGRESS-START -->` and `<!-- B-PROGRESS-END -->`).
- Assumptions: docs/ASSUMPTIONS.md is an index created by A-1 linking docs/ASSUMPTIONS_A.md and docs/ASSUMPTIONS_B.md. A writes only to ASSUMPTIONS_A.md, B only to ASSUMPTIONS_B.md. Each entry is a heading with the increment id, for example "## A-6 weather noise".
- tests/: flat folder, unique file names, each file owned by the person who owns the code it tests.

### 2.3 Shared constants and paths (created in A-1, used by everyone)

- src/common/config.py: `load_config() -> dict` reads config.yaml (cached).
- src/common/paths.py: `is_mock() -> bool` (env MOCK == "1"), `artifacts_dir() -> Path` (env ARTIFACTS_DIR, else artifacts_mock if MOCK=1, else artifacts), `processed_dir() -> Path` (data/processed_mock if MOCK=1, else data/processed), `raw_dir()`, `external_dir()`. All code gets directories ONLY from here; no hardcoded paths anywhere.
- src/common/constants.py: `MODELS = ["seasonal_naive","linear","lgbm","xgboost","prophet","lstm","ensemble"]`, `BASELINE_MODEL = "seasonal_naive"`, `QUANTILES = [0.05,0.1,0.5,0.9,0.95]`, `QUANTILE_COLS = ["p05","p10","p50","p90","p95"]`, `PEAK_HOURS = [6,7,8,9,10,19,20,21,22,23]`, `HORIZON_DAYS = [1,2,3,4,5,6,7]`, `TZ = "Asia/Kolkata"`.
- src/common/seasons.py: `SEASONS = ["winter","summer","monsoon","post_monsoon"]` and `season_of(month: int) -> str`, using the month definitions in docs/02_API_CONTRACT.md section 0 (single source of truth).

### 2.4 Interfaces between A and B (exact names, do not rename)

- `src.backtest.folds.make_folds(index: pd.DatetimeIndex, cfg: dict) -> list[Fold]` with `Fold` a dataclass (fold_id: int, train_end: pd.Timestamp, origins: list[pd.Timestamp]). B-12 imports it.
- `src.backtest.registry`: `REGISTRY: dict[str, type]` and decorator `register(name)`; `get_forecaster(name: str, cfg: dict)`.
- `src.features.ar_features.build_ar_features(load_df, origin_ts, target_ts) -> pd.DataFrame`.
- `src.features.weather_noise.noisy_weather(features_df, origin_ts, horizon_day, seed) -> pd.DataFrame`.
- `src.metrics.metrics`: `mape, rmse, mae, bias, pinball, picp, mpiw`. `src.metrics.accuracy_table.build_accuracy_table(pred_df, exclude_outage=False) -> dict`. B-3 imports these.
- `src.procurement.advisor.recommend(start_date, days, model, risk_quantile, tariff) -> dict` (B only; stub in B-2, real in B-9).
- Artifact files: schemas are in docs/02_API_CONTRACT.md section 1. Producers are listed in 2.1.
- Mock data: A-2 writes mock artifacts to artifacts_mock/ and mock load/features to data/processed_mock/, both committed, so B can run everything with MOCK=1 straight after merging A-2.

### 2.5 Config keys (A-1 writes all of these)

timezone, origin_hour_local, quantiles, seed (42), peak_threshold_quantile, cdh_base_c, paths (data, artifacts, artifacts_mock, processed_mock), backtest (min_train_days 730, retrain_every_days 30, test_months 12), weather_noise (enabled true, base_sd_c 0.5, sd_growth_per_day_c 0.4), cleaning (linear_gap_max_hours 3, hour_of_week_weeks 4, outage_mad_z 6.0), models (lgbm: num_leaves 63, learning_rate 0.05, n_estimators 500, early_stopping_rounds 50, origin_stride 2; xgboost: same shape; prophet: origin_stride 7; lstm: epochs 30, hidden 64, max_minutes 10, retrain_every_n_folds 3), calibration (window_days 90, coverage_80 0.8, coverage_90 0.9), peak (threshold_scope "global", season_relative false, min_recall 0.8), procurement (da 5000, under 12000, resale 2500), api (cors_origins ["http://localhost:5173","http://127.0.0.1:5173"]).

## 3. Shared prompt (paste once per session)

```
I am Person <A or B> on a two-person team building a Delhi electricity-demand forecasting system for a hackathon: probabilistic 7-day-ahead hourly forecasts at a 10:00 IST daily origin, peak-event classification, procurement advisor, FastAPI backend and a React UI.

Read first: README.md (Progress log), docs/02_API_CONTRACT.md, docs/03_PRD.md, and docs/01_ROLES_AND_PROMPTS_2P.md sections 2 and 3.

Tech stack (fixed, do not substitute):
- Python 3.11, venv at .venv, pip, install via requirements.txt (which includes requirements-a.txt and requirements-b.txt; torch is separate in requirements-deep.txt).
- pandas, numpy, pyarrow (parquet), scikit-learn, LightGBM, XGBoost, Prophet, statsmodels, SHAP, scipy, tqdm, pyyaml, holidays, matplotlib, pytest, ruff.
- API: FastAPI, uvicorn, Pydantic v2, httpx for tests.
- UI: Node 20, npm, Vite 5, React 18, TypeScript (strict), react-router-dom 6, Tailwind 3, Plotly (plotly.js-dist-min with react-plotly.js factory), react-markdown with remark-gfm.
- Docker and docker-compose; Makefile; config.yaml; artifacts are parquet and JSON files.

Rules:
- Do only the single increment I paste, then stop.
- Write no comments in code (no inline comments, no docstrings, no commented-out code). Names and structure must be self-explanatory.
- Touch only files my letter owns (docs/01_ROLES_AND_PROMPTS_2P.md section 2.1). In shared files edit only my own sections or blocks (section 2.2). If I need a change in the other person's files, do not make it; tell me what to ask them.
- Get all directories via src/common/paths.py, constants via src/common/constants.py, settings via src/common/config.py. Never hardcode paths, model names, quantiles or seasons.
- Run Python as modules from the repo root (python -m src.x.y, python -m scripts.z). Every package folder has __init__.py. pytest runs from the repo root.
- Timestamps are tz-aware Asia/Kolkata, hour-beginning. No future leakage: anything used for a forecast made at origin O must have ts < O.
- Use only real data or clearly labelled mock data. Never invent numbers in docs.
- Follow the artifact schemas and endpoint shapes in docs/02_API_CONTRACT.md exactly. If the contract looks wrong, report it instead of changing it.
- Tests for new logic go in tests/, named after the increment's module.

Each prompt ends with a Finish line. Follow it exactly.
```

## 4. Suggested order and handoffs

Order for A:
1. A-1, A-2 first and fast; tell B when each is merged.
2. A-3 (ingest). If load data is missing, tell B and the team immediately.
3. A-4, A-5, A-6, A-7, A-8, A-9.
4. A-10, A-11, A-12 (tell B the daily summary file and columns).
5. A-13, A-14, A-15, A-16.

Order for B:
1. B-1 (UI shell) immediately, using the contract examples, while A does A-1 and A-2.
2. B-2 (API on mocks) once A-2 is merged. Announce Checkpoint 0.5 to A.
3. B-3, B-4 (analysis on mocks), B-5 (Forecast page), B-6, B-7, B-8 (evaluation pages), B-9, B-10 (procurement).
4. B-11 (Insights page, mock feature importance is fine).
5. B-12, B-13 (peak classifier and timing) once A-10 and A-11 are merged.
6. After A-15 and A-16 are merged and B-13 is done: rerun `make analysis` on real artifacts, then B-14 (real artifacts, Docker), B-15 (UI polish), B-16, B-17.

Dependencies between people:
- B-2 needs A-2. B-3, B-4, B-8 need A-2 (mock peak and prediction files).
- B-12 needs A-7 (folds), A-6 (AR features), A-10 (predictions). A-12 is preferred.
- B-11 gets real data after A-16. B-14 and later need A-15 and A-16.

---

# Person A: Data, Features, Models and Backtest

### A-1 · Increment 1 of 16 — Repo scaffold
**Needs:** docs/ contains 01_ROLES_AND_PROMPTS_2P.md, 02_API_CONTRACT.md, 03_PRD.md.

```
Increment 1 of 16 — repo scaffold. B is waiting on this, so keep it exact.

Create the monorepo exactly as follows.

Folders (with .gitkeep-free placeholder __init__.py for Python packages, and an empty README-less placeholder file only where a folder would otherwise be empty): data/raw, data/external, data/processed, data/processed_mock, src/common, src/data, src/features, src/peak, src/models, src/backtest, src/metrics, src/procurement, src/analysis, models, artifacts, artifacts_mock, scripts, api, ui, tests, docs/figures, docs/screenshots, make. Every Python folder under src/, plus src/ itself, scripts/, api/ and tests/, gets an __init__.py.

src/common (real code, not stubs):
- config.py: load_config() reading config.yaml at the repo root, cached.
- paths.py: is_mock(), artifacts_dir(), processed_dir(), raw_dir(), external_dir(). is_mock() is true when env MOCK == "1". artifacts_dir() returns env ARTIFACTS_DIR if set, else "artifacts_mock" when mock, else "artifacts". processed_dir() returns "data/processed_mock" when mock, else "data/processed". All return pathlib.Path relative to the repo root resolved absolutely.
- constants.py: MODELS = ["seasonal_naive","linear","lgbm","xgboost","prophet","lstm","ensemble"], BASELINE_MODEL = "seasonal_naive", QUANTILES = [0.05,0.1,0.5,0.9,0.95], QUANTILE_COLS = ["p05","p10","p50","p90","p95"], PEAK_HOURS = [6,7,8,9,10,19,20,21,22,23], HORIZON_DAYS = [1,2,3,4,5,6,7], TZ = "Asia/Kolkata".
- seasons.py: SEASONS = ["winter","summer","monsoon","post_monsoon"] and season_of(month:int)->str using the month definitions in docs/02_API_CONTRACT.md section 0.

config.yaml with these exact top-level keys and defaults: timezone Asia/Kolkata; origin_hour_local 10; quantiles [0.05,0.1,0.5,0.9,0.95]; seed 42; peak_threshold_quantile 0.9; cdh_base_c 24; paths {data: data, artifacts: artifacts, artifacts_mock: artifacts_mock, processed_mock: data/processed_mock}; backtest {min_train_days: 730, retrain_every_days: 30, test_months: 12}; weather_noise {enabled: true, base_sd_c: 0.5, sd_growth_per_day_c: 0.4}; cleaning {linear_gap_max_hours: 3, hour_of_week_weeks: 4, outage_mad_z: 6.0}; models {lgbm: {num_leaves: 63, learning_rate: 0.05, n_estimators: 500, early_stopping_rounds: 50, origin_stride: 2}, xgboost: {num_leaves: 63, learning_rate: 0.05, n_estimators: 500, early_stopping_rounds: 50, origin_stride: 2}, prophet: {origin_stride: 7}, lstm: {epochs: 30, hidden: 64, max_minutes: 10, retrain_every_n_folds: 3}}; calibration {window_days: 90, coverage_80: 0.8, coverage_90: 0.9}; peak {threshold_scope: global, season_relative: false, min_recall: 0.8}; procurement {da: 5000, under: 12000, resale: 2500}; api {cors_origins: ["http://localhost:5173","http://127.0.0.1:5173"]}.

Makefile (root, final, never edited again): `include make/a.mk` and `include make/b.mk`; .PHONY for all targets; `test` runs `python -m pytest -q`; `all` runs data, features, backtest, peak, analysis in that order.
make/a.mk: targets mock, data, features, backtest. Each prints "not implemented yet" and exits 0.
make/b.mk: targets peak, analysis, api, ui. api runs `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`. peak, analysis, ui print "not implemented yet" and exit 0.

pytest.ini: pythonpath = ., testpaths = tests.

requirements-a.txt, pinned to versions that install cleanly right now on Python 3.11: pandas, numpy, pyarrow, scikit-learn, lightgbm, xgboost, prophet, statsmodels, shap, scipy, tqdm, pyyaml, holidays, matplotlib, pytest, ruff. requirements-b.txt: fastapi, uvicorn[standard], pydantic>=2, httpx. requirements.txt containing exactly two lines: -r requirements-a.txt and -r requirements-b.txt. requirements-deep.txt: torch (CPU build).

docker-compose.yml: service `api` (image python:3.11-slim, command python -m http.server 8000, port 8000:8000) and service `ui` (image nginx:alpine, port 5173:80). Both are placeholders that B replaces.

README.md with these exact headings in order: title and one-line project description; "Architecture" (one line); "How to run"; "How to resume" (for a fresh AI session: read the README Progress log, then docs/); "How to run the UI"; "Results"; "Deployment"; "Submission checklist"; "Progress log" containing two subsections "A" and "B", each wrapped in HTML comment markers <!-- A-PROGRESS-START --> / <!-- A-PROGRESS-END --> and <!-- B-PROGRESS-START --> / <!-- B-PROGRESS-END -->. Headings "How to run the UI", "Deployment", "Submission checklist" are B's; leave them with a single "TODO (B)" line.

docs/ASSUMPTIONS.md as an index linking docs/ASSUMPTIONS_A.md and docs/ASSUMPTIONS_B.md; create both of those with a title line only.

tests/conftest.py with a pytest fixture `artifact_dirs` returning the list of directories to validate: artifacts_mock always, artifacts only if it contains any file. tests/test_smoke.py imports src.common.config, paths, constants, seasons and checks the constants and that season_of covers months 1 to 12.

Finish: run `make test`, update the A section of the README Progress log (between its markers), and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the tree matches; `make test` passes; `docker compose config` is valid; `MOCK=1 python -c "from src.common.paths import artifacts_dir; print(artifacts_dir())"` prints artifacts_mock. Add the ignore file (section 1), merge to main, tell B to pull.

### A-2 · Increment 2 of 16 — Mock data and mock artifacts
**Needs:** A-1 merged.

```
Increment 2 of 16 — mock data and mock artifacts. B and the UI are blocked on this.

(a) scripts/make_mock_data.py (run as python -m scripts.make_mock_data) writes load_hourly.parquet and features_known.parquet into processed_dir() forced to data/processed_mock (the script always writes the mock location regardless of MOCK), in the EXACT schema of docs/02_API_CONTRACT.md sections 1.1 and 1.2.
Synthetic Delhi-like load, 3 years hourly, Asia/Kolkata, hour-beginning timestamps, complete index, ending at least 400 days before today's date is NOT required; use a fixed range 2022-01-01 to 2024-12-31:
- winter lows about 2,000 MW, summer peaks up to about 8,300 MW
- morning ramp 6 to 10, evening peak 19 to 23
- driven by a synthetic temperature series (annual cycle plus daily cycle plus noise); load rises with cooling-degree-hours
- weekday/weekend effect, a few festival dips, slow growth trend, a few outage drops flagged is_outage_suspect, a few short gaps imputed with is_imputed=True
Fill every column in contract 1.2 (calendar, festival, event, weather, thermal-inertia, trend). Use seed from config.

(b) scripts/make_mock_artifacts.py (python -m scripts.make_mock_artifacts) writes EVERY artifact of contract sections 1.4 to 1.12 into artifacts_mock/: predictions_backtest.parquet, peak_predictions.parquet, metrics_accuracy.json, metrics_peak.json, error_heatmap.json, missed_peaks.json, feature_importance.json, procurement_defaults.json, meta.json.
- predictions_backtest: the last 12 months of daily origins at 10:00 IST, targets D+1 to D+7 (168 hours), models = constants.MODELS; ensemble best, seasonal_naive worst; error grows with horizon_day; always p05<=p10<=p50<=p90<=p95; include the *_raw columns, fold_id and is_outage_suspect.
- peak_predictions: one row per date per model (at least ensemble) with outcomes covering hit, miss, false_alarm, correct_reject.
- metrics_accuracy: every model by horizon_day (1 to 7 and "all") by segment (all, 4 seasons, peak_hours, off_peak), computed from the mock predictions, not invented separately.
- metrics_peak: ensemble plus one rule baseline. error_heatmap: at least ensemble and seasonal_naive, metrics mape, rmse, bias, horizon_day 1 and "all". missed_peaks: at least 8 items with tags. feature_importance: lgbm and xgboost. procurement_defaults: da 5000, under 12000, resale 2500 INR/MWh with the disclaimer text from the contract. meta.json per 1.12 with a plausible peak threshold, backtest_range matching the mock predictions, models list, weather_proxy_note.
Keep artifacts_mock/ and data/processed_mock/ small enough to commit (round floats sensibly, snappy or zstd compression).

(c) tests/test_artifact_schemas.py validating every file against contract section 1: column names, dtypes, tz-aware timestamps, quantile ordering, enum values, point counts. Use the `artifact_dirs` fixture from conftest so it runs against artifacts_mock now and artifacts later. Files that do not exist yet in a non-mock directory are skipped with a clear reason only for artifacts/ and never for artifacts_mock/.

(d) Add make target `mock` in make/a.mk that runs both scripts in order.

Finish: run `make mock` then `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** open a parquet in pandas (evening peaks, summer greater than winter); schema tests pass. Merge and tell B.

### A-3 · Increment 3 of 16 — Ingest real data
**Needs:** A-1 merged. Can run in parallel with A-2 if data is hard to find.

```
Increment 3 of 16 — ingest real data.

1) src/data/ingest_load.py (python -m src.data.ingest_load): load Delhi hourly (or finer) electricity demand from whatever source I provide in data/raw/. I will tell you the source/file. If finer than hourly (15-min, 5-min), aggregate to hourly mean MW with hour-beginning timestamps in Asia/Kolkata and ALSO save the native-resolution series to processed_dir()/load_native.parquet for peak-timing analysis. Write the raw-ingested hourly result to processed_dir()/load_raw_hourly.parquet (columns ts, load_mw, NaN allowed). If I have not provided any load data, STOP and give me a short list of where to look (organizer dataset, Delhi SLDC historical demand reports, Grid-India/POSOCO reports, Kaggle) and the columns/format to look for. Do not invent data.
2) src/data/ingest_weather.py (python -m src.data.ingest_weather): pull hourly weather for Delhi (28.61, 77.21) from the Open-Meteo historical archive API for the same date range: temperature_2m, relative_humidity_2m, dew_point_2m, wind_speed_10m, cloud_cover. Cache raw responses in raw_dir()/weather/ so reruns do not hit the network. Convert to Asia/Kolkata hour-beginning and write processed_dir()/weather_hourly.parquet. If the sandbox cannot reach the API, tell me and write the exact curl/python snippet I should run locally.
3) data/raw/README.md recording source, URL, licence, date downloaded and column meanings.
4) Print a short summary: date range, row counts, percent missing, min and max load.
Make target: `make data` in make/a.mk runs both ingest modules only for now.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the summary looks sane (2 years or more, plausible load range). If load data is missing, escalate to B and the team now.

### A-4 · Increment 4 of 16 — Clean and impute
**Needs:** A-3 merged.

```
Increment 4 of 16 — cleaning and imputation.

src/data/clean.py (python -m src.data.clean) reads processed_dir()/load_raw_hourly.parquet and writes processed_dir()/load_hourly.parquet exactly per docs/02_API_CONTRACT.md section 1.1:
- Reindex to a complete hourly Asia/Kolkata index. IST has no DST, but still detect and report duplicate timestamps, missing hours and apparent clock shifts in the source; document what you find and how you resolved each.
- Impute gaps: gaps up to cleaning.linear_gap_max_hours hours by linear interpolation (imputation_method="linear"); longer gaps from the same hour-of-week averaged over the nearest cleaning.hour_of_week_weeks non-missing weeks (imputation_method="hour_of_week"). Set is_imputed accordingly.
- Flag suspected outage drops and outliers as is_outage_suspect using a robust z-score (MAD) of the residual versus the hour-of-week median profile; threshold cleaning.outage_mad_z. Do NOT delete or alter these values.
- No NaNs may remain in load_mw.
- Write docs/DATA_QUALITY.md with REAL numbers: total hours, number and length distribution of gaps, percent imputed per method, number of flagged outliers with 3 examples, duplicate and clock issues found, decisions taken.
- Tests (tests/test_clean.py): index complete, unique and monotonic; no NaNs; schema matches contract; imputed flags consistent with method.
`make data` now runs ingest then clean.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read DATA_QUALITY.md; do the numbers match the raw data? Tell B real data exists.

### A-5 · Increment 5 of 16 — Known features
**Needs:** A-4 merged.

```
Increment 5 of 16 — "known-in-advance" features.

src/features/build_known.py (python -m src.features.build_known) writes processed_dir()/features_known.parquet with exactly the columns in docs/02_API_CONTRACT.md section 1.2:
- Calendar: hour, dow, month, doy, sin/cos of hour and dow, is_weekend, is_holiday plus holiday name (use the `holidays` package for India).
- Festivals: create data/external/festivals.csv with columns date,festival,source_url for Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Independence Day (and others if useful) covering my data range. Use web search for correct dates and CITE the source URL per row; if a date cannot be verified, flag it in the CSV instead of guessing. Build cal_days_to_* and cal_days_since_* (clipped to plus or minus 30) and cal_is_festival_window (plus or minus 2 days) from it.
- Events: evt_lockdown and evt_odd_even flags. Research the actual date ranges (COVID lockdown phases; Delhi odd-even rounds) with web search, cite sources in data/external/events.csv, and populate flags only inside my data range.
- Weather-derived wx_* columns from processed_dir()/weather_hourly.parquet. Heat index via the Rothfusz regression (document the validity range and what you do outside it); wx_cdh = max(temp - cdh_base_c, 0) with cdh_base_c from config; wx_cdh_24 = rolling 24h sum; temperature lags 1,3,6,12,24,48,72; rolling mean temperature 24h and 72h.
- trend_t = days since the first timestamp.
- wx_is_noisy = False for now.
- Tests (tests/test_build_known.py): schema matches contract; no NaNs except the first rows lost to lags (drop or document); festival window correct for Diwali in a known year.
`make features` runs this.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** spot-check Diwali dates against a calendar; check the odd-even and lockdown dates the agent cited.

### A-6 · Increment 6 of 16 — AR features and weather noise
**Needs:** A-5 merged.

```
Increment 6 of 16 — origin-relative autoregressive features and weather-noise option.

1) src/features/ar_features.py with
   build_ar_features(load_df, origin_ts, target_ts) -> DataFrame
exactly as in docs/02_API_CONTRACT.md section 1.3. It uses ONLY load rows with ts < origin_ts. The origin is 10:00 IST on D0, so the last known load is 09:00 D0 and targets start at D+1 00:00. target_ts may be a single timestamp or a DatetimeIndex; the output is indexed by target_ts. Columns: ar_same_hour_last_week (target_ts minus 7 days if that timestamp is before the origin, otherwise step back further in 7-day multiples until it is; document the rule), ar_same_hour_last_known_day, ar_mean_7d, ar_mean_30d, ar_level_365d, ar_last_known_load, ar_last_week_daily_peak, ar_hours_since_last_known.
2) tests/test_leakage.py: for 50 random origins, perturb load values at and after origin_ts (multiply by 10) and assert the output is identical to the unperturbed output. This test is mandatory.
3) src/features/weather_noise.py: noisy_weather(features_df, origin_ts, horizon_day, seed) -> DataFrame adds Gaussian noise to wx_temp_c and recomputes the dependent wx_* columns (heat index, cdh, cdh_24, lags and rolling means where derivable) with sd = weather_noise.base_sd_c + weather_noise.sd_growth_per_day_c * horizon_day. Deterministic given the seed (derive a per-origin seed from seed and origin_ts), sets wx_is_noisy=True. The true weather stays on the actual side of any comparison.
4) Append to docs/ASSUMPTIONS_A.md: backtests use observed weather plus horizon-scaled noise as a proxy for archived forecasts, the sd values, and why.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the leakage test passes and you have read it to confirm it is meaningful. Tell B the AR function is ready.

### A-7 · Increment 7 of 16 — Backtest harness
**Needs:** A-1 and A-2 merged (A-6 preferred for real AR features; until then use a simple stand-in).

```
Increment 7 of 16 — rolling-origin backtest harness.

Build src/backtest/ reading load_hourly.parquet and features_known.parquet from processed_dir() (mock data is fine for now).
- Protocol (frozen, docs/03_PRD.md section 9): origin = 10:00 IST every day; targets D+1 00:00 to D+7 23:00 (horizon_h 14 to 181; horizon_day 1 to 7); expanding training window; min train = backtest.min_train_days; retrain every backtest.retrain_every_days (a fold is one retrain period of consecutive origins); test = last backtest.test_months months (or all data after min-train if shorter).
- src/backtest/folds.py: @dataclass Fold(fold_id: int, train_end: pd.Timestamp, origins: list[pd.Timestamp]) and make_folds(index: pd.DatetimeIndex, cfg: dict) -> list[Fold]. B imports this exact function.
- src/backtest/registry.py: REGISTRY: dict[str, type], decorator register(name), get_forecaster(name, cfg).
- src/backtest/base.py: Forecaster Protocol: name: str; fit(train_end: pd.Timestamp) -> None; predict(origin: pd.Timestamp) -> pd.DataFrame with columns target_ts, horizon_h, horizon_day, p05, p10, p50, p90, p95. predict may only use data with ts < origin (autoregressive via build_ar_features when it exists; otherwise a simple marked stand-in).
- src/backtest/runner.py (python -m src.backtest.runner --models name1,name2): for each fold, fit at train_end, predict all origins, join y_true and is_outage_suspect, append to artifacts_dir()/predictions_backtest.parquet with the exact columns of docs/02_API_CONTRACT.md section 1.4 (*_raw equal to final for now; fold_id; model). Skips model/fold pairs already present (resume) and shows a tqdm progress bar. Defaults to all registered models when --models is omitted.
- A trivial "persistence" forecaster registered as "persistence" to prove the harness. It is excluded from constants.MODELS and from the final artifact (runner flag --keep-persistence off by default; delete its rows after the proof run).
- Tests (tests/test_backtest_harness.py): no training row at or after train_end; no feature row at or after origin; output schema matches contract; every target covered exactly once per model/origin.
`make backtest` runs the runner for the registered models.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** row count = origins x 168 per model; walk through one fold's train_end against its first origin. Tell B the make_folds signature is final.

### A-8 · Increment 8 of 16 — Baselines
**Needs:** A-7 merged.

```
Increment 8 of 16 — baselines. Register both with @register.

1) src/models/seasonal_naive.py registered as "seasonal_naive": for each target hour use the actual load at the same hour-of-week 7 days earlier if that timestamp is before the origin; otherwise step back by further 7-day multiples until it is (document the rule in docs/ASSUMPTIONS_A.md; for D+2 to D+7 it steps back further). Quantiles: naive prediction plus residual quantiles by hour-of-day computed ONLY from the training window (residual = actual minus naive prediction).
2) src/models/linear.py registered as "linear": scikit-learn LinearRegression on known features (calendar one-hots or sin/cos, wx_cdh_24, wx_heat_index_c, temperature lags and rolling means, festival/event flags, trend_t) plus AR features and horizon_h. Quantiles via residual quantiles by hour-of-day from the training window.
3) Sort quantiles per row so p05<=p10<=p50<=p90<=p95 (shared helper src/models/quantile_utils.py: sort_quantiles(df)).
4) Run both through the harness and write predictions. Print mean RMSE and MAPE per horizon_day for each.
5) Tests (tests/test_baselines.py): seasonal_naive never uses data at or after the origin; quantile ordering.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** seasonal-naive RMSE should degrade with horizon; linear should beat it.

### A-9 · Increment 9 of 16 — Metrics library
**Needs:** A-8 merged.

```
Increment 9 of 16 — metrics library and accuracy table.

src/metrics/metrics.py with pure functions: mape (percent; document the weakness at low loads and guard against zero), rmse, mae, bias (mean of prediction minus actual), pinball (per quantile and mean over the five), picp for the 80% interval (p10 to p90) and 90% interval (p05 to p95), mpiw (mean width of the 80% interval, MW), and improvement_pct vs seasonal_naive for mape and rmse.
src/metrics/segments.py: segment masks for all, winter, summer, monsoon, post_monsoon (via src.common.seasons.season_of), peak_hours (constants.PEAK_HOURS, by hour-beginning) and off_peak.
src/metrics/accuracy_table.py: build_accuracy_table(pred_df, exclude_outage=False) -> dict giving rows for every model x horizon_day (1 to 7 and "all") x segment, plus a main (python -m src.metrics.accuracy_table) that writes artifacts_dir()/metrics_accuracy.json exactly per contract section 1.6 (mape in percent, picp as fraction, improvement null for the baseline itself). Report is_outage_suspect rows as part of "all" and expose exclude_outage and a CLI flag --exclude-outage.
- Tests (tests/test_metrics.py): hand-computed toy examples for each metric; baseline improvement vs itself is null.
- Print a compact table (model x horizon_day for segment=all, plus peak_hours) to the console.
`make backtest` ends by writing metrics.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** tell B the metric function names (section 2.4) are final so the analysis code can import them.

### A-10 · Increment 10 of 16 — LightGBM quantile
**Needs:** A-6 and A-9 merged.

```
Increment 10 of 16 — LightGBM quantile forecaster (main model).

src/models/lgbm_quantile.py registered as "lgbm":
- One LightGBM model per quantile q in {0.05, 0.1, 0.5, 0.9, 0.95} with objective="quantile".
- Training table: for each training origin (every models.lgbm.origin_stride-th origin) and each target hour D+1 to D+7, features = known features at target_ts (with noisy_weather from src.features.weather_noise when weather_noise.enabled) + build_ar_features(load_df, origin, target) + horizon_h. Shared builder src/models/training_table.py: build_training_table(load_df, features_df, origins, cfg) so XGBoost and others reuse it.
- Zero sample weight for is_outage_suspect rows in training; they stay in evaluation.
- Sort the five quantile predictions per row (quantile_utils.sort_quantiles).
- Fixed seed from config; hyperparameters from models.lgbm in config.yaml; early stopping on a validation slice taken from the END of the training window.
- Run the backtest for "lgbm" and print the accuracy table including improvement vs seasonal_naive for segment=all and peak_hours.
- Tests (tests/test_lgbm.py): no future leakage; quantile ordering; deterministic with a fixed seed.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** does lgbm beat seasonal_naive and linear at peak_hours, not only on average? If not, tell B before they build on it.

### A-11 · Increment 11 of 16 — Conformal calibration
**Needs:** A-10 merged.

```
Increment 11 of 16 — interval calibration with conformalized quantile regression (CQR).

src/models/calibration.py:
- calibrate(raw_pred_df, calib_pred_df, cfg) -> DataFrame and a helper that the runner calls per fold. For each fold use a rolling calibration window of calibration.window_days days that ENDS BEFORE the fold's first test origin, predicted out-of-sample by a model fit before that window. Compute conformity scores per (horizon_day, peak/off-peak group) and adjust the 80% interval (p10, p90) and the 90% interval (p05, p95) to hit calibration.coverage_80 and calibration.coverage_90. Keep the median unchanged. Preserve quantile ordering.
- Update the runner so p05..p95 in predictions_backtest.parquet are the CALIBRATED values and p05_raw..p95_raw keep the pre-calibration values, per contract section 1.4.
- Apply to "lgbm"; make it reusable for every model via a flag on the registered class (calibrate = True).
- Extend metrics: keep picp_80, picp_90, mpiw_80 on the calibrated values and ADD "calibration_comparison" to metrics_accuracy.json with picp and mpiw before vs after per calibrated model and horizon_day.
- Tests (tests/test_calibration.py): the calibration window never overlaps test origins; ordering preserved; coverage on a synthetic example moves toward target.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** PICP for the 80% interval is about 0.80 and about 0.90 for the 90% interval (within a few points); MPIW has not exploded. Tell B calibrated predictions are in.

### A-12 · Increment 12 of 16 — Daily-peak summaries for B
**Needs:** A-11 merged.

```
Increment 12 of 16 — export daily forecast summaries for the peak classifier.

1) src/models/daily_summary.py (python -m src.models.daily_summary) writes artifacts_dir()/daily_peak_summary.parquet, one row per (model, origin_ts, date): columns model, origin_ts, date, horizon_day, daily_max_p10, daily_max_p50, daily_max_p90 (max over the day's 24 hourly values of each quantile series; document this), argmax_hour_p50, daily_min_p50, y_true_daily_max (null if unobserved). tz-aware origin_ts; date as a date type.
2) Add this as section 1.13 in docs/02_API_CONTRACT.md (producer A, consumer B) and a change-log row. Minimal additive change; do not touch other sections. This is the only contract edit A makes.
3) Schema test in tests/test_daily_peak_summary.py (do not edit test_artifact_schemas.py).
4) Generate it for all models in the backtest, print the first 5 rows for "lgbm", and run it as the last step of `make backtest`.
Tell me the exact path and columns so I can message B.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** message B the path and columns.

### A-13 · Increment 13 of 16 — Prophet and XGBoost
**Needs:** A-11 merged.

```
Increment 13 of 16 — Prophet and XGBoost comparison models.

1) src/models/prophet_model.py registered as "prophet": holiday-aware (holidays dataframe from data/external/festivals.csv plus India public holidays), wx_temp_c or wx_cdh_24 as an extra regressor using noisy weather for future targets when weather_noise.enabled, daily, weekly and yearly seasonality. Prophet is slow: train one model per fold on hourly data (or a reduced set if needed; document how). Quantiles from Prophet's uncertainty interval where reasonable (interval_width 0.9 gives p05/p95, 0.8 gives p10/p90), otherwise residual quantiles by hour; document which.
2) src/models/xgboost_model.py registered as "xgboost": same training table (src.models.training_table) and design as lgbm but with objective reg:quantileerror and hyperparameters from models.xgboost.
3) Apply the same CQR calibration to both; keep raw columns.
4) Run the backtest for both and print the updated accuracy table. Time-box: if Prophet is too slow at the full fold count, backtest it on every models.prophet.origin_stride-th origin and state this in README Results and docs/ASSUMPTIONS_A.md.
5) Tests (tests/test_prophet_xgb.py): registration works; output schema valid; quantile ordering.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** Prophet runtime acceptable; results plausible (Prophet is usually weaker on peaks, which is a fine finding).

### A-14 · Increment 14 of 16 — LSTM
**Needs:** A-11 merged; `pip install -r requirements-deep.txt` works.

```
Increment 14 of 16 — one deep model, time-boxed. Keep it simple.

src/models/lstm_model.py registered as "lstm" (PyTorch, CPU):
- Design: LSTM encoder over the last 168 hours of [load_mw, wx_temp_c, wx_cdh, cal_hour_sin/cos, cal_dow_sin/cos, cal_is_holiday] up to the origin, then an MLP head that outputs all 168 horizons x 5 quantiles at once.
- Loss: pinball loss summed over the five quantiles; scale inputs and targets using training-window statistics only.
- Retrain every models.lstm.retrain_every_n_folds folds (reuse the last model in between; document it); early stopping on the END of the training window; seed from config; total backtest budget models.lstm.max_minutes minutes; epochs and hidden size from models.lstm.
- Sort quantiles; apply CQR calibration; keep raw columns.
- Print the updated accuracy table. If it does not beat lgbm, keep it anyway as a documented comparison.
- Tests (tests/test_lstm.py): forward-pass shapes; quantile ordering; no future data in an input window.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** training finished within budget; the loss curve is not diverging.

### A-15 · Increment 15 of 16 — Ensemble
**Needs:** A-10, A-13, A-14 merged.

```
Increment 15 of 16 — ensemble.

src/models/ensemble.py registered as "ensemble":
- Combine the available base models (lgbm, xgboost, prophet, lstm, optionally linear) by a weighted average of each quantile series (quantile averaging).
- Fit the weights per horizon_day on a VALIDATION window that ends before the test window of each fold (minimise pinball loss, weights >= 0 summing to 1, via scipy.optimize or a simple grid). Never fit weights on test origins.
- Recalibrate the ensemble with CQR at the end and keep raw columns.
- Write predictions for "ensemble", rerun the accuracy table and daily summary (so "ensemble" appears in metrics_accuracy.json and daily_peak_summary.parquet), and print the complete accuracy table: every model x horizon_day for segment=all and peak_hours with improvement vs seasonal_naive, plus the learned weights.
- Tests (tests/test_ensemble.py): weights non-negative and sum to 1; validation window precedes test window; ordering preserved.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the ensemble is at least as good as the best single model on pinball, and PICP stays on target. Tell B `ensemble` is available in the real artifacts.

### A-16 · Increment 16 of 16 — Feature importance and results
**Needs:** A-10 merged (A-15 for the final results table).

```
Increment 16 of 16 — feature importance and README results.

- src/models/feature_groups.py: a single dict FEATURE_GROUPS mapping every feature name to one of calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon, and a function group_of(feature).
- src/models/importance.py (python -m src.models.importance): SHAP (TreeExplainer) for the p50 LightGBM model on a sample of the latest fold's test rows (about 5,000) giving mean(|SHAP|) per feature, plus LightGBM gain importance as a cross-check. Same for XGBoost if time allows. Write artifacts_dir()/feature_importance.json per contract section 1.10: importance normalised to sum to 1 per model, with group.
- Also write artifacts_dir()/feature_importance_by_segment.json with the top 10 features for peak_hours vs off_peak (extra, not in the contract; tell me so it can be added to the contract if useful).
- Fill the README "Results" section: model x D+1 and D+7, RMSE and MAPE for segment all and peak_hours, improvement vs seasonal_naive, PICP 80 and 90, copied from the real artifacts.
- Tests (tests/test_importance.py): normalisation sums to 1; every feature has a group.

Finish: run `make test`, update the A section of the README Progress log, and list the files that changed. Then stop.
```
**Review:** the top features look physically sensible (CDH or temperature, same-hour-last-week, hour). Tell B the file is ready and that all real artifacts from A are final.

---

# Person B: API, Peak, Procurement, Analysis and UI

### B-1 · Increment 1 of 17 — UI shell
**Needs:** A-1 merged. Use the contract examples until the mock API runs.

```
Increment 1 of 17 — UI shell. Everything else in ui/ builds on this, so keep it clean.

In ui/, create a Vite 5 + React 18 + TypeScript (strict) + Tailwind 3 app with react-router-dom 6 and Plotly (plotly.js-dist-min wrapped with react-plotly.js/factory), plus react-markdown and remark-gfm installed for later use. Node 20, npm.
- Routing for six pages with placeholder content, one folder each with an index.tsx: ui/src/pages/Forecast, Accuracy, ErrorHeatmap, MissedPeaks, Procurement, Insights. Routes: /forecast, /accuracy, /errors, /missed-peaks, /procurement, /insights; a top nav; "/" redirects to /forecast.
- Theme: colour-blind-safe palette defined once as CSS variables and Tailwind tokens: one colour per model (constants list matching src/common/constants.MODELS), band colours for P10 to P90 and P05 to P95, actual line, peak marker, at-risk shading. Dark mode default with a distinctive look; light optional.
- ui/src/api/: a typed client matching docs/02_API_CONTRACT.md section 2 — TypeScript types for every response, one function per endpoint, base URL from import.meta.env.VITE_API_BASE (default http://localhost:8000/api/v1), and a uniform ApiError type from the contract's error format.
- ui/src/components/shared/: ChartCard (title, subtitle, units, loading/error/empty states), ModelSelect (models from GET /models; default "ensemble"), DatePicker (constrained to meta.backtest_range), StatTile, PlotlyChart wrapper handling resize and theme.
- A global "mock mode" banner when GET /health reports mock=true.
- ui/Dockerfile (multi-stage: node:20 build, nginx:alpine serve) and ui/nginx.conf (SPA fallback to index.html, listen 80).
- make/b.mk: `ui` target runs `cd ui && npm install && npm run dev -- --host --port 5173`.
- README "How to run the UI" section.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** `make ui`, click all six nav links, no console errors. Merge early.

### B-2 · Increment 2 of 17 — FastAPI on mocks
**Needs:** A-2 merged.

```
Increment 2 of 17 — FastAPI backend running on mock artifacts.

Build api/ with entry point api/main.py exposing `app`, implementing EVERY endpoint in docs/02_API_CONTRACT.md section 2 (2.1 to 2.16; 2.16 may return 501 for now), prefix /api/v1. Suggested modules: api/main.py, api/models.py (Pydantic), api/store.py (artifact loading), api/routers/*.py, api/errors.py.
- Pydantic v2 response models mirroring the contract JSON exactly (field names, nullability, enums).
- Load artifacts at startup from src.common.paths.artifacts_dir() (so MOCK=1 uses artifacts_mock; ARTIFACTS_DIR overrides). GET /health reports "mock": true or false.
- Derive day-ahead and week-ahead responses from predictions_backtest.parquet (24 or 168 points, at_risk = p90 >= peak_threshold_mw, actual null when missing), peak endpoints from peak_predictions.parquet, pass-through JSON for metrics, error-heatmap, missed-peaks, feature-importance, meta and procurement defaults.
- POST /procurement/recommend calls src.procurement.advisor.recommend(start_date, days, model, risk_quantile, tariff). Create a stub in src/procurement/advisor.py returning a contract-shaped response with placeholder numbers, with a module-level constant IS_STUB = True (B-9 replaces it).
- Error handling per contract section 3: unified {"error": {"code","message","details"}} format, including wrapping FastAPI's 422 validation errors; ValueError from the advisor maps to BAD_PARAMETER.
- CORS from config api.cors_origins plus optional env CORS_ORIGINS (comma-separated).
- tests/test_contract.py: call every endpoint with valid and invalid inputs (bad date, unknown model, out-of-range date, bad risk_quantile) and validate responses against the Pydantic models, parametrized over the `artifact_dirs` fixture; must pass with MOCK=1.
- make/b.mk `api` target stays as defined in A-1; document `MOCK=1 make api` in README "How to run" only by telling me what to add (that section belongs to A), and put the API commands in the B Progress log.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** `MOCK=1 make api`, open /docs, click through five endpoints; contract tests pass. Merge and tell A: Checkpoint 0.5.

### B-3 · Increment 3 of 17 — Error decomposition and heatmap JSON
**Needs:** A-2 merged.

```
Increment 3 of 17 — error decomposition and heatmap artifact.

src/analysis/error_decomposition.py (python -m src.analysis.error_decomposition):
- Read predictions_backtest.parquet from artifacts_dir(). Use metric functions from src.metrics.metrics if the module exists, otherwise small local versions in src/analysis/_local_metrics.py that you delete once A-9 is merged.
- Compute error metrics by season x hour-of-day, peak vs off-peak, and horizon_day, per model.
- Write artifacts_dir()/error_heatmap.json exactly per contract section 1.8: one entry per model x metric (mape, rmse, bias) x horizon_day (1 and "all" at minimum, 1 to 7 if cheap), with hours [0..23], seasons from src.common.seasons.SEASONS, values[season][hour], counts[season][hour]; cells with fewer than 5 observations are null.
- Tests (tests/test_analysis_heatmap.py): hand-computed toy example; values and counts are 4x24; season mapping per the contract.
make/b.mk `analysis` target runs this module.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** with MOCK=1, values are higher at peak hours and in summer.

### B-4 · Increment 4 of 17 — Missed-peak analysis
**Needs:** B-3 merged; peak_predictions.parquet exists (mock now).

```
Increment 4 of 17 — missed-peak analysis.

src/analysis/missed_peaks.py (python -m src.analysis.missed_peaks) reads peak_predictions.parquet, load_hourly.parquet and features_known.parquet (processed_dir()) and writes artifacts_dir()/missed_peaks.json exactly per contract section 1.9.
- Include every day with outcome == "miss" for each model (default focus: ensemble), sorted by absolute magnitude_error_mw descending.
- Auto-tag each day: "festival" (cal_is_festival_window), "holiday" (cal_is_holiday), "heatwave" (max wx_temp_c that day above the 95th percentile of that season's daily max temperatures in the training period), "weather_miss" (actual daily max temperature differs from the weather proxy used for the forecast by more than 2 degrees C; omit the tag if not computable), "weekend", else "other". Put the thresholds in docs/ASSUMPTIONS_B.md.
- Write a one-line "note" per item generated from the tags and numbers (for example "Actual max temp 3.1 °C above the weather proxy; peak shifted 7 h later than predicted"). Notes come from the data, never invented.
- Tests (tests/test_analysis_missed_peaks.py): sorting, tag rules on toy rows, note contains the right numbers.
`make analysis` now runs B-3 then B-4 modules.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** read five notes; do they make sense given the numbers?

### B-5 · Increment 5 of 17 — Forecast page
**Needs:** B-1 and B-2 merged.

```
Increment 5 of 17 — Forecast page (ui/src/pages/Forecast).

- Controls: DatePicker, a Day-ahead / Week-ahead toggle, ModelSelect. URL query ?date=YYYY-MM-DD&model=...&view=day|week is the source of truth (reads on load, updates on change) so other pages can deep-link here.
- Data: GET /forecast/day-ahead or /forecast/week-ahead, and GET /peak/day for the peak card.
- Chart (Plotly): actual line; shaded P10 to P90 band; lighter P05 to P95 band; P50 line; predicted peak marker (from the response's peak.predicted_peak_ts / mw) and actual peak marker; horizontal dashed line at peak_threshold_mw; at-risk hours (at_risk=true) shaded as vertical bands. Week view shows all 168 hours with day separators.
- Peak card beside the chart: peak probability badge, predicted peak hour and MW range (p10/p50/p90), actual peak if known, outcome (hit / miss / false alarm / correct reject) with a colour and plain-language text, timing error in minutes and magnitude error in MW.
- A short legend: P10 to P90 is an 80% interval, P05 to P95 a 90% interval.
- Loading, empty and error states (for example DATE_OUT_OF_RANGE gives a friendly message).
- Hover tooltip shows ts, p05..p95, actual.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** switch date, day and week, and model; check the legend wording; check the peak card on a "miss" day.

### B-6 · Increment 6 of 17 — Accuracy page
**Needs:** B-1 and B-2 merged.

```
Increment 6 of 17 — Accuracy page (ui/src/pages/Accuracy; shared pieces in ui/src/components/eval/).

- Data: GET /backtest/metrics (all rows) and GET /backtest/peak-metrics.
- Controls: segment dropdown (all, winter, summer, monsoon, post_monsoon, peak_hours, off_peak) and metric toggle (MAPE / RMSE / MAE / bias / pinball).
- Main table: rows = models, columns = horizon_day 1 to 7 and "all", cell = chosen metric; the % improvement vs seasonal_naive with green/red colouring (baseline row shows "—"). Highlight the best model per column. Sticky header and first column; sortable.
- Calibration table: picp_80 and picp_90 per model and horizon_day with a visual marker against the 0.80 and 0.90 targets, plus mpiw_80_mw. Label clearly: P10 to P90 = 80% interval, P05 to P95 = 90% interval. If calibration_comparison exists in the metrics JSON, show before vs after.
- Peak events card: precision, recall, F1, PR-AUC, 2x2 confusion matrix, timing MAE, % within plus or minus 1 h, magnitude MAE and bias, classifier vs rule baseline side by side.
- A small note about MAPE's weakness at low loads (winter nights) next to the MAPE toggle.
- Loading, empty and error states.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** numbers match what A printed in the console for the same segment (once real).

### B-7 · Increment 7 of 17 — Error heatmap page
**Needs:** B-3 and B-6 merged.

```
Increment 7 of 17 — Error heatmap page (ui/src/pages/ErrorHeatmap).

- Data: GET /backtest/error-heatmap?model=&metric=&horizon_day=.
- Controls: ModelSelect, metric toggle (MAPE / RMSE / bias), horizon-day select (1 to 7, All).
- Plotly heatmap: x = hour of day (0 to 23), y = season (winter, summer, monsoon, post_monsoon); sequential colour scale for mape and rmse, diverging centred at 0 for bias; colour bar with units; hover shows value, observation count and the hour range; null cells hatched or grey with "too few observations".
- Highlight the peak-hour columns (6 to 10 and 19 to 23) with a band above the plot.
- Under the chart, auto-generated plain-language callouts computed from the data: worst cell, best cell, and whether peak hours are worse than off-peak on average (percentage difference).
- Optional compare mode: two models side by side (for example ensemble vs seasonal_naive) with a shared colour scale.
- Loading, empty and error states (NOT_FOUND gives a friendly message).

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the diverging bias colours centre on 0; callouts match the grid.

### B-8 · Increment 8 of 17 — Missed peaks page
**Needs:** B-4, B-5, B-6 merged.

```
Increment 8 of 17 — Missed peaks page (ui/src/pages/MissedPeaks).

- Data: GET /backtest/missed-peaks (paginate with limit/offset) and GET /peak/events?outcome=false_alarm for a secondary tab.
- Controls: ModelSelect, tag filter chips (festival, holiday, heatwave, weather_miss, weekend, other; multi-select), toggle "Misses / False alarms".
- Table: date, season, peak probability, predicted vs actual peak time, predicted p50 vs actual MW, magnitude error (MW, coloured), timing error (minutes), tag chips, note. Default sort by magnitude error; sortable columns.
- Summary strip above the table: number of missed peaks, share by tag, mean magnitude error.
- Row click opens a drill-down panel (drawer or inline) with a compact day chart (GET /forecast/day-ahead?date=… : actual line, P10 to P90, P05 to P95, predicted vs actual peak marker) and an "Open in Forecast page" button linking to /forecast?date=YYYY-MM-DD&model=…
- Empty state for "no misses" and for filters with no results.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** click three rows including one with null actuals; the Forecast link opens the right day.

### B-9 · Increment 9 of 17 — Procurement advisor
**Needs:** B-2 merged (stub exists); mock predictions are fine.

```
Increment 9 of 17 — procurement advisor logic. Replace the stub from B-2.

src/procurement/advisor.py: recommend(start_date, days, model, risk_quantile, tariff) -> dict, returning EXACTLY the shape in docs/02_API_CONTRACT.md section 2.12. Remove IS_STUB.
- Load forecasts from artifacts_dir()/predictions_backtest.parquet: horizon_day=1 forecasts for each target date in [start_date, start_date+days) so the schedule is a true day-ahead schedule (origin 10:00 on D-1); also the p50 and p90 columns.
- risk_quantile: a number in [0.5, 0.99] or "newsvendor". newsvendor quantile = (under_price - da_price) / (under_price - resale_price); set risk_quantile_source accordingly. Use the nearest available quantile column (p50, p90, p95) by linear interpolation between available quantiles; document it in docs/ASSUMPTIONS_B.md.
- scheduled_mw per hour = the chosen quantile of the forecast.
- Cost per hour = da_price*S + under_price*max(D-S,0) - resale_price*max(S-D,0) with D = actual load when available.
- Baselines: flat at the previous week's mean MW, and flat at the previous week's peak MW (flat_peak_cost_inr). If there is no previous week in the data, raise a clear ValueError.
- p90_risk_exposure_inr = cost with D = the p90 path minus cost with D = the p50 path, same schedule.
- at_risk_hours = hours where p90 >= the latest peak threshold from meta.json (or peak_predictions.parquet).
- If actuals are missing for some hours, set the realised cost fields to null per the contract and still return p90_risk_exposure_inr.
- by_day breakdown per the contract.
- src/procurement/defaults.py writes artifacts_dir()/procurement_defaults.json per section 1.11 using config procurement values (da 5000, under 12000, resale 2500 INR/MWh) with the disclaimer; append the reasoning and the "illustrative placeholder" caveat to docs/ASSUMPTIONS_B.md.
- Validate inputs (days 1 to 7, tariff ordering under > da > resale, risk_quantile range) and raise clear ValueErrors that the API maps to BAD_PARAMETER.
- Tests (tests/test_advisor.py) with hand-computed numbers: a 3-hour toy example for cost, newsvendor quantile = 0.7368 for the defaults, exposure sign.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** hand-check one hour of cost; newsvendor is about 0.737 for the default tariff.

### B-10 · Increment 10 of 17 — Procurement page
**Needs:** B-5 and B-9 merged.

```
Increment 10 of 17 — Procurement page (ui/src/pages/Procurement).

- Controls: week picker (start date, days 1 to 7), ModelSelect, risk-quantile slider (0.50 to 0.99, step 0.01) with a "Use newsvendor" checkbox (shows the computed quantile from the response), and an editable tariff form (da_price, under_price, resale_price) prefilled from GET /procurement/defaults with a visible "illustrative placeholder" note and a Reset button. Validate under > da > resale before submitting.
- Call POST /procurement/recommend on change (debounced) and show:
  1) schedule chart: scheduled MW vs p50, p90, flat baseline and actual (if present); at-risk hours shaded;
  2) KPI tiles: cost, flat cost, savings (INR and %), P90 risk exposure, under and over-procured hours;
  3) per-day table from by_day;
  4) a "cost vs risk quantile" curve: call the endpoint for q in {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99} in parallel and plot realised cost (or exposure when cost is null) with the current q and the newsvendor q marked.
- Format INR with Indian digit grouping and units (crore and lakh with a toggle to full numbers).
- Loading, empty and error states, including BAD_PARAMETER messages.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** move the slider; the cost curve should have a sensible minimum. Try an extreme tariff.

### B-11 · Increment 11 of 17 — Insights page
**Needs:** B-6 merged; mock feature importance is fine.

```
Increment 11 of 17 — Insights page (ui/src/pages/Insights).

- Data: GET /models, GET /models/{model}/feature-importance?top=20, GET /meta.
- Section 1 "What drives the forecast": horizontal bar chart of the top 20 features for the selected model (ModelSelect limited to models with importances), bars coloured by feature group (calendar, festival, event, weather, thermal_inertia, trend, autoregressive, horizon) with a legend, plus a grouped summary (share of total importance per group).
- Section 2 "Why peaks are hard": render docs/WHY_PEAKS_ARE_HARD.md (react-markdown + remark-gfm) with its figures. Add scripts/sync_insights.sh that copies docs/WHY_PEAKS_ARE_HARD.md, docs/MODEL_CARD.md and docs/figures/*.png into ui/public/insights/ (skipping missing files without error); the page fetches them from /insights/... and shows a friendly placeholder if a file does not exist. Add an npm script "sync:insights" that runs it and call it from the "prebuild" script.
- Section 3 "Model card summary": render the first sections (assumptions, known limits) from MODEL_CARD.md the same way, plus key facts from /meta (data range, backtest range, weather_proxy_note).
- Loading, empty and error states.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** the page does not crash when the markdown files do not exist yet.

### B-12 · Increment 12 of 17 — Peak classifier (binary)
**Needs:** A-6, A-7 and A-10 merged (A-11 and A-12 preferred, A-12 gives daily summaries).

```
Increment 12 of 17 — peak-event classifier (binary), evaluated walk-forward.

src/peak/classifier.py (python -m src.peak.classifier) predicts whether a day's peak exceeds the threshold.
- Label: the day's max hourly load > threshold, where threshold = the peak_threshold_quantile (0.9) quantile of DAILY peaks in that fold's TRAINING window only. peak.season_relative (default false) switches to a per-season threshold; peak.threshold_scope defaults to "global".
- Use the SAME folds and origins as A's backtest: `from src.backtest.folds import make_folds`. Walk-forward only.
- Features per target date, all available at the 10:00 IST origin: daily-level known features (max temp, max CDH, day-of-week, holiday and festival flags, trend_t), AR features via src.features.ar_features.build_ar_features, and, when artifacts_dir()/daily_peak_summary.parquet exists, the daily_max_p50 and daily_max_p90 of the best model for that origin and date.
- Model: LightGBM classifier plus isotonic calibration of the probability (calibrate on a held-out window before the test window).
- Decision threshold tuned for RECALL: choose it on a validation window to maximise precision subject to recall >= peak.min_recall (fallback: maximise F2). Document the trade-off in docs/ASSUMPTIONS_B.md.
- Rule baseline: "same weekday last week exceeded its threshold".
- Write a first version of artifacts_dir()/peak_predictions.parquet per contract section 1.5 (pred_peak_hour from the argmax of the p50 forecast for now) and artifacts_dir()/metrics_peak.json per section 1.7 with precision, recall, F1, PR-AUC and confusion matrix for classifier and rule baseline.
- Tests (tests/test_peak_classifier.py): no threshold computed with test-fold data; label and threshold logic on a toy example.
make/b.mk `peak` target runs this.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** classifier vs rule baseline precision and recall — clearly better? Threshold per fold only from training data?

### B-13 · Increment 13 of 17 — Peak hour, timing and magnitude
**Needs:** B-12 merged.

```
Increment 13 of 17 — peak hour prediction, timing error and magnitude error.

Extend src/peak/ (new module src/peak/peak_hour.py, orchestrated by python -m src.peak.run_all which runs classifier then peak_hour; `make peak` calls run_all):
- Peak-hour model: LightGBM multiclass over 24 hours (which hour-beginning holds the daily max). Baseline: argmax of the best forecaster's p50 by hour. Report top-1 and top-2 hit rate.
- Fill the remaining fields of artifacts_dir()/peak_predictions.parquet per contract section 1.5: pred_peak_hour, pred_peak_ts, pred_peak_mw_p10/p50/p90 (daily max of each quantile series; document it), actual_peak_ts, actual_peak_mw, actual_is_peak, timing_error_min (signed, predicted minus actual; use processed_dir()/load_native.parquet for the actual peak time when it exists), magnitude_error_mw (predicted p50 daily max minus actual), and outcome (hit / miss / false_alarm / correct_reject).
- Extend metrics_peak.json with timing_mae_min, timing_within_1h_pct, magnitude_mae_mw, magnitude_bias_mw for classifier and baselines.
- Tests (tests/test_peak_hour.py): outcome labels on a toy confusion example; timing error sign convention.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** most days within plus or minus 1 h on timing; `outcome` counts add up to the number of days. Tell A the peak file is final.

### B-14 · Increment 14 of 17 — Real artifacts, meta, Docker
**Needs:** A-15, A-16, B-9, B-12 and B-13 merged; real artifacts exist in artifacts/. Rerun `make analysis` and `python -m src.procurement.defaults` against real artifacts first.

```
Increment 14 of 17 — switch to real artifacts, assemble meta, containerize.

1) src/peak/meta.py (python -m src.peak.meta) writes artifacts_dir()/meta.json per docs/02_API_CONTRACT.md section 1.12 from the real data and backtest (data_range, backtest_range, latest peak threshold, models actually present, season and peak-hour definitions from src.common, weather_proxy_note). Add it as the last step of `make peak`.
2) Run the API with MOCK unset against artifacts/. Fix any mismatch between the real artifacts and the Pydantic models on the PRODUCER side where it is B's file; for A's files, report the deviation to me instead of loosening the models. Make tests/test_contract.py and tests/test_artifact_schemas.py pass against BOTH artifacts_mock/ and artifacts/.
3) api/Dockerfile (python:3.11-slim, installs requirements.txt without torch, copies src/, api/, config.yaml, artifacts/) and replace the placeholder services in docker-compose.yml: `api` on 8000 with a healthcheck on /api/v1/health and env CORS_ORIGINS=http://localhost:5173, and `ui` built from ui/ on 5173:80 with VITE_API_BASE=http://localhost:8000/api/v1 passed as a build arg.
4) Confirm `make all` runs data, features, backtest, peak, analysis in order and that every target prints a clear message when something is skipped.
5) Write the README "Deployment" section: Render/Railway build and start commands, env vars (ARTIFACTS_DIR, CORS_ORIGINS, VITE_API_BASE), and how to ship artifacts/.
6) Fresh-clone test: in a clean directory, clone, install, run `make test`, then `docker compose up`, and report what failed.
7) Add the final submission checklist from docs/03_PRD.md section 12 to the README "Submission checklist" section with checkboxes.

Finish: run `make test`, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** `docker compose up` on a machine that has never seen the repo. Then remove the artifacts/ entry from the ignore file.

### B-15 · Increment 15 of 17 — UI on real artifacts and polish
**Needs:** B-14 merged.

```
Increment 15 of 17 — switch the UI to real artifacts and polish.

- Point the UI at the API running WITHOUT MOCK. Fix any crashes caused by real-data differences (missing actuals at the edges, date ranges, absent models). Do not change the contract: if the API output deviates from docs/02_API_CONTRACT.md, tell me.
- Polish: responsive layout (laptop and a phone-width sanity check), consistent chart heights, axis units on every chart (MW, ₹), keyboard-focusable controls, aria-labels on icon buttons, meaningful chart titles and subtitles, skeleton loaders so the layout does not jump.
- Add an "About these numbers" popover on Forecast and Procurement: weather-proxy caveat and tariff-placeholder caveat (text read from meta.weather_proxy_note and the procurement defaults).
- Production build works via `npm run build` and the nginx container from B-14; fix any base-path issues.
- Screenshots of Forecast and Procurement (desktop) into docs/screenshots/.

Finish: run `npx tsc --noEmit` and `npm run build` in ui/, update the B section of the README Progress log, and list the files that changed. Then stop — do not start the next increment.
```
**Review:** use the app like a judge would for five minutes; fix anything confusing.

### B-16 · Increment 16 of 17 — Procurement memo and demo script
**Needs:** B-15 merged.

```
Increment 16 of 17 — documents.

1) scripts/make_procurement_memo.py (python -m scripts.make_procurement_memo) regenerates figures into docs/figures/ and the numbers section of docs/PROCUREMENT_MEMO.md. Pick a sample week from the backtest that includes at least one peak-risk day (explain why). Use src.procurement.advisor with the real ensemble forecasts to produce: the recommended hourly day-ahead schedule (compact daily summary table and a chart image), P90 risk exposure, at-risk hours, simulated cost vs both naive flat schedules, savings in INR and %, and sensitivity to the risk quantile (a small table for q = 0.5, 0.7, 0.9, 0.99 and the newsvendor q). State clearly that tariffs are illustrative placeholders. REAL numbers only.
2) docs/DEMO_SCRIPT.md: a 3-minute demo story: (1) the problem (tail risk at peaks, not only the average); (2) Forecast page on a hot day with the P90 band and at-risk hours; (3) the peak classifier outcome; (4) the Accuracy table vs baselines at peak hours; (5) a missed peak and why; (6) Procurement: schedule, exposure, savings; (7) one sentence of limitations (weather proxy, placeholder tariffs). Include exact URLs and clicks, what to say, and a fallback if the live demo fails (screenshots in docs/screenshots/).

Finish: update the B section of the README Progress log, and list the files that changed. Then stop.
```
**Review:** read the memo as the planner would; time the demo script out loud.

### B-17 · Increment 17 of 17 — Model card and "why peaks are hard"
**Needs:** A-15, B-13 and B-14 merged; real artifacts available.

```
Increment 17 of 17 — the two analysis documents, with REAL numbers from the backtest.

1) scripts/make_peak_analysis.py (python -m scripts.make_peak_analysis) produces reproducible figures into docs/figures/ and prints the numbers used, and docs/WHY_PEAKS_ARE_HARD.md uses them:
 - Weather sensitivity: MW change per +1 °C in daily max temperature (or CDH) on peak-hour load, by season, estimated from the data (for example a regression with calendar controls); scatter with fit.
 - Thermal inertia: correlation of evening-peak load with temperature at lags 0, 3, 6, 12, 24, 48, 72 h (and rolling 24h and 72h means) as a bar chart; explain what it means for peaks shifting late on hot days.
 - Festival and holiday effects: average load deviation (vs a same-weekday, same-month baseline) in Diwali, Holi and Eid windows vs normal days, with sample sizes and a caution when n is small.
 - Error evidence: forecast error at peak_hours vs off_peak for the ensemble and the baseline (metrics_accuracy.json) and 2 to 3 missed-peak case studies from missed_peaks.json.
 About 1.5 pages. Every number and figure comes from the script; no invented claims; state limits (weather proxy, short samples).
2) docs/MODEL_CARD.md: intended use; data (source, range, imputation summary from docs/DATA_QUALITY.md); features; models and how they were trained; backtest protocol (frozen, docs/03_PRD.md section 9); results summary (ensemble vs baselines at D+1 and D+7, all vs peak_hours, PICP 80 and 90); peak classifier results; limitations and failure modes (weather proxy, festival data sparsity, structural changes, outage effects, tariff placeholders); ethical and operational notes (decision support, not automated dispatch). Link the generated figures and artifacts.
3) Run scripts/sync_insights.sh so the UI picks up the new files.

Finish: update the B section of the README Progress log, and list the files that changed. Then stop.
```
**Review:** every number in the docs traces to a file in artifacts/ or printed script output; rerun the script and confirm the figures regenerate identically.