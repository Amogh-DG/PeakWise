# PeakWise: Delhi Electricity-Demand Forecasting & Procurement System

Probabilistic 7-day-ahead hourly electricity demand forecasting, peak-event classification, and procurement copilot for Delhi.

## Architecture

FastAPI backend serving probabilistic forecasts and peak-classification analytics to a React dashboard, driven by a walk-forward model backtesting pipeline.

## How to run

Run `make all` to execute the end-to-end pipeline. Run `make test` to execute test suites.

## How to resume

For a fresh AI session: read the README Progress log, then docs/.

## How to run the UI

1. Install dependencies:
   ```bash
   cd ui && npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   # or from repo root:
   make ui
   ```
   Open `http://localhost:5173` in your browser.
3. Configure backend API URL via `VITE_API_BASE` (defaults to `http://localhost:8000/api/v1`).
4. Build for production:
   ```bash
   npm run build
   ```

## Results

Model accuracy and backtest evaluation metrics will be recorded here after backtest runs.

## Deployment

TODO (B)

## Submission checklist

TODO (B)

## Progress log

### A

<!-- A-PROGRESS-START -->
- A-1: Repo scaffold created (directory structure, src/common config/paths/constants/seasons, Makefile, docker-compose, pytest setup).
- A-2: Generated synthetic Delhi mock load and features (data/processed_mock/) and mock contract artifacts (artifacts_mock/), added schema test suite and make mock target.
- A-7: Built rolling-origin backtest harness (folds generation, forecaster registry and protocol, persistence baseline, runner with resume and progress bar, test suite, make backtest target).
- A-8: Implemented and registered baselines (seasonal_naive with 7-day step-back rule and training residual quantiles, linear regression on known features and AR terms, quantile sorting utility, ran both through backtest harness).
- A-9: Built metrics library (mape, rmse, mae, bias, pinball, picp, mpiw, improvement_pct), segments masking, and accuracy table generator writing contract artifacts/metrics_accuracy.json; updated make backtest.
- A-3: Ingested real Delhi electricity demand and Open-Meteo weather data, produced raw-ingested parquet files with caching, data documentation, and ingest test suite.
- A-4: Cleaned and imputed load data (load_hourly.parquet): complete hourly IST index, 455 gaps imputed (239 linear, 216 hour-of-week), 0 outage suspects at MAD-z threshold 6.0 (max z=4.20), wrote docs/DATA_QUALITY.md with real numbers.
- A-5: Built known-in-advance features (features_known.parquet) covering calendar, verified festival distances/windows, historical event flags, and weather-derived thermal/CDH/heat-index metrics.
- A-6: Implemented strictly leak-free origin-relative autoregressive features (ar_features.py with mandatory 50-origin leakage test), horizon-scaled deterministic weather noise simulation (weather_noise.py), and documented NWP proxy in docs/ASSUMPTIONS_A.md.
<!-- A-PROGRESS-END -->

### B

<!-- B-PROGRESS-START -->
<<<<<<< HEAD
- B-3: Error decomposition and heatmap artifact — src/analysis/error_decomposition.py computes mape/rmse/bias by season×hour, peak/off-peak, and horizon_day per model; writes artifacts_dir()/error_heatmap.json per contract §1.8; make/b.mk analysis target wired; tests/test_analysis_heatmap.py covers shape, season order, min-obs null, and hand-computed mape example.
=======
- B-1: UI shell scaffolded with Vite 5 + React 18 + TypeScript strict + Tailwind 3, 6-page routing (/forecast, /accuracy, /errors, /missed-peaks, /procurement, /insights), colour-blind-safe theme tokens, typed API client for contract §2, shared components (ChartCard, ModelSelect, DatePicker, StatTile, PlotlyChart), mock mode banner, multi-stage Dockerfile and nginx SPA config.
- B-2: Built FastAPI backend (api/main.py, api/models.py, api/store.py, api/errors.py, api/routers/) implementing contract endpoints §2.1–§2.16 on mock artifacts with MOCK=1. Added procurement advisor stub in src/procurement/advisor.py and full contract test suite (tests/test_contract.py). Run backend on mocks with `MOCK=1 make api` or `MOCK=1 python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`.
<!-- B-PROGRESS-END -->
