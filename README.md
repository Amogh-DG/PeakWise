# PeakWise: Delhi Electricity-Demand Forecasting & Procurement System

> Built for the **CodeSpark** hackathon.

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

Walk-forward backtest evaluation across Delhi electricity demand (2023–2026), evaluated out-of-sample with point-in-time temporal isolation and horizon-scaled weather forecast noise:

### Multi-Horizon Model Performance

| Model | Horizon | Segment | RMSE (MW) | MAPE (%) | Improvement vs Baseline (RMSE) | Improvement vs Baseline (MAPE) | PICP 80 | PICP 90 |
|---|---|---|---|---|---|---|---|---|
| **ensemble** | D+1 | all | **154.5** | **2.68%** | **+50.9%** | **+45.6%** | 0.77 | 0.88 |
| **ensemble** | D+1 | peak_hours | **158.4** | **2.57%** | **+49.2%** | **+43.0%** | 0.76 | 0.87 |
| **ensemble** | D+7 | all | **172.3** | **2.93%** | **+56.8%** | **+51.7%** | 0.76 | 0.87 |
| **ensemble** | D+7 | peak_hours | **178.4** | **2.81%** | **+54.0%** | **+49.0%** | 0.75 | 0.86 |
| **lgbm** | D+1 | all | **155.7** | **2.69%** | **+50.5%** | **+45.4%** | 0.67 | 0.81 |
| **lgbm** | D+1 | peak_hours | **160.9** | **2.58%** | **+48.4%** | **+42.8%** | 0.65 | 0.79 |
| **lgbm** | D+7 | all | **172.0** | **2.89%** | **+56.9%** | **+52.3%** | 0.67 | 0.80 |
| **lgbm** | D+7 | peak_hours | **180.7** | **2.80%** | **+53.4%** | **+49.2%** | 0.67 | 0.79 |
| **linear** | D+1 | all | 262.5 | 4.68% | +16.6% | +5.1% | 0.78 | 0.89 |
| **linear** | D+1 | peak_hours | 253.8 | 4.16% | +18.6% | +7.8% | 0.77 | 0.88 |
| **linear** | D+7 | all | 332.6 | 5.70% | +16.7% | +5.9% | 0.68 | 0.79 |
| **linear** | D+7 | peak_hours | 315.9 | 5.01% | +18.6% | +9.1% | 0.69 | 0.80 |
| **seasonal_naive** *(baseline)* | D+1 | all | 314.7 | 4.93% | — | — | 0.79 | 0.89 |
| **seasonal_naive** *(baseline)* | D+1 | peak_hours | 311.8 | 4.51% | — | — | 0.78 | 0.89 |
| **seasonal_naive** *(baseline)* | D+7 | all | 399.3 | 6.06% | — | — | 0.71 | 0.82 |
| **seasonal_naive** *(baseline)* | D+7 | peak_hours | 388.0 | 5.51% | — | — | 0.71 | 0.82 |

### Key Findings & Feature Drivers
- **Beating the Baseline at Peak Hours**: LightGBM achieves a **48.4% reduction in peak-hour RMSE on Day 1** (160.9 MW vs 311.8 MW) and **53.4% on Day 7** (180.7 MW vs 388.0 MW), proving that thermal dynamics and autoregressive level anchoring effectively model peak air-conditioning surges.
- **Top Feature Drivers (SHAP TreeExplainer)**:
  1. `ar_same_hour_last_week` (~39.3% LightGBM / ~50.0% XGBoost): Dominant weekly cyclical load signature.
  2. `ar_same_hour_last_known_day` (~13.1% LightGBM / ~14.8% XGBoost): Anchoring to the immediate prior day's operating regime.
  3. `wx_dewpoint_c` & `wx_cdh_24` (~12.6% combined): Severe impact of latent atmospheric heat and accumulated cooling degree hours on cooling demand.
  4. `trend_t` (~7.6%): Captures underlying secular economic and population electrification growth across Delhi.
  5. `cal_dow` & `cal_hour`: Diurnal work cycle and weekend commercial load shedding.
- **Peak vs Off-Peak Sensitivity**: Peak-hour feature importance demonstrates substantially elevated sensitivity to humidity (`wx_dewpoint_c`) and 24-hour heat accumulation (`wx_cdh_24`), whereas off-peak hours are primarily driven by baseline autoregressive level indicators.

## Deployment

The application is container-ready and deploys cleanly to Render, Railway, or standard Docker hosts.

### Docker Compose (Local & Production)
```bash
docker compose build
docker compose up
```
- **Backend API**: `http://localhost:8000` (FastAPI with healthcheck on `/api/v1/health`)
- **Frontend UI**: `http://localhost:5173` (Nginx serving Vite production build)

### Cloud Deployment (Render / Railway)

1. **Backend Service (FastAPI)**:
   - Build context: Repo root
   - Dockerfile: `api/Dockerfile`
   - Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables:
     - `PORT`: Provided by host (e.g. 8000)
     - `ARTIFACTS_DIR`: `artifacts` (or `artifacts_mock` for mock demo)
     - `CORS_ORIGINS`: Comma-separated frontend origins (e.g. `https://your-ui.up.railway.app,http://localhost:5173`)
     - `MOCK`: `0` (or `1` for synthetic mode)

2. **Frontend Service (Vite + Nginx)**:
   - Build context: `ui/`
   - Dockerfile: `ui/Dockerfile`
   - Build argument: `VITE_API_BASE=https://your-api.up.railway.app/api/v1`

3. **Shipping Artifacts**:
   - Model predictions, backtest parquets, and evaluation metrics are preserved in `artifacts/` (using snappy compression and JSON).
   - Container builds copy `artifacts/` directly into the image for zero-dependency execution.

