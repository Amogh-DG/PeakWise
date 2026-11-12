# PeakWise: Delhi Electricity-Demand Forecasting & Procurement System

Probabilistic 7-day-ahead hourly electricity demand forecasting, peak-event classification, and procurement copilot for Delhi.

## Architecture

FastAPI backend serving probabilistic forecasts and peak-classification analytics to a React dashboard, driven by a walk-forward model backtesting pipeline.

## How to run

Run `make all` to execute the end-to-end pipeline. Run `make test` to execute test suites.

## How to resume

For a fresh AI session: read the README Progress log, then docs/.

## How to run the UI

TODO (B)

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
- A-3: Ingested real Delhi electricity demand and Open-Meteo weather data, produced raw-ingested parquet files with caching, data documentation, and ingest test suite.
- A-4: Cleaned and imputed load data (load_hourly.parquet): complete hourly IST index, 455 gaps imputed (239 linear, 216 hour-of-week), 0 outage suspects at MAD-z threshold 6.0 (max z=4.20), wrote docs/DATA_QUALITY.md with real numbers.
- A-5: Built known-in-advance features (features_known.parquet) covering calendar, verified festival distances/windows, historical event flags, and weather-derived thermal/CDH/heat-index metrics.
- A-6: Implemented strictly leak-free origin-relative autoregressive features (ar_features.py with mandatory 50-origin leakage test), horizon-scaled deterministic weather noise simulation (weather_noise.py), and documented NWP proxy in docs/ASSUMPTIONS_A.md.
<!-- A-PROGRESS-END -->

### B

<!-- B-PROGRESS-START -->
<!-- B-PROGRESS-END -->
