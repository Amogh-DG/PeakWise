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
- A-7: Built rolling-origin backtest harness (folds generation, forecaster registry and protocol, persistence baseline, runner with resume and progress bar, test suite, make backtest target).
- A-8: Implemented and registered baselines (seasonal_naive with 7-day step-back rule and training residual quantiles, linear regression on known features and AR terms, quantile sorting utility, ran both through backtest harness).
- A-9: Built metrics library (mape, rmse, mae, bias, pinball, picp, mpiw, improvement_pct), segments masking, and accuracy table generator writing contract artifacts/metrics_accuracy.json; updated make backtest.
<!-- A-PROGRESS-END -->

### B

<!-- B-PROGRESS-START -->
<!-- B-PROGRESS-END -->
