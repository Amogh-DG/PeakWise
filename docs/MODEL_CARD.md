# Model Card: Delhi Electricity Demand Probabilistic Forecaster

## 1. Model Details
- **Organization / Authors:** Codespark Antigravity Team
- **Model Architecture:** Quantile Averaging Ensemble combining:
  1. LightGBM Quantile Regressors (p05, p10, p50, p90, p95)
  2. XGBoost Quantile Regressors (`reg:quantileerror`)
  3. Prophet additive seasonality with India holiday regressors
  4. PyTorch CPU 2-layer LSTM Encoder-MLP
  5. Linear Autoregressive Baseline
- **Calibration Protocol:** Post-hoc Conformalized Quantile Regression (CQR) with 90-day walk-forward rolling window.
- **Decision Engine:** Walk-Forward LightGBM Binary Peak Classifier with isotonic probability calibration.

---

## 2. Intended Use & Target Users
- **Primary Use:** Decision support for Day-Ahead power procurement scheduling, spot market bidding, and reserve margin planning for Delhi Distribution Companies (DISCOMs).
- **Out of Scope:** Automated real-time primary frequency response or sub-minute dispatch without human operator oversight.

---

## 3. Training & Backtest Data
- **Geography:** National Capital Territory of Delhi, India.
- **Load Data Source:** Hourly demand time-series (2023–2026), Asia/Kolkata timezone, hour-beginning timestamps.
- **Weather Data Source:** Open-Meteo historical archive (28.61° N, 77.21° E): Temperature, Dewpoint, Relative Humidity, Wind Speed, Cloud Cover.
- **Weather Proxy:** Point-in-time observed weather corrupted with horizon-scaled Gaussian noise ($0.5$ °C base $\pm 0.4$ °C per day of lead time) to rigorously emulate archived numerical weather prediction (NWP) forecasts.
- **Imputation:** 455 historical missing load hours imputed per `docs/DATA_QUALITY.md` (239 linear, 216 hour-of-week medians).

---

## 4. Evaluation Protocol & Results Summary

Evaluated out-of-sample over 12 monthly walk-forward backtest folds without temporal leakage:

| Horizon | Segment | Model | RMSE (MW) | MAPE (%) | Improvement vs Baseline | PICP 80 | PICP 90 |
|---|---|---|---|---|---|---|---|
| **D+1** | **Peak Hours** | **Ensemble** | **158.4** | **2.57%** | **+49.2%** | **0.76** | **0.87** |
| **D+1** | **All Hours** | **Ensemble** | **154.5** | **2.68%** | **+50.9%** | **0.77** | **0.88** |
| **D+7** | **Peak Hours** | **Ensemble** | **178.4** | **2.81%** | **+54.0%** | **0.75** | **0.86** |
| **D+7** | **All Hours** | **Ensemble** | **172.3** | **2.93%** | **+56.8%** | **0.76** | **0.87** |
| D+1 | Peak Hours | Seasonal Naive | 311.8 | 4.51% | Baseline | 0.78 | 0.89 |
| D+7 | Peak Hours | Seasonal Naive | 388.0 | 5.51% | Baseline | 0.71 | 0.82 |

### Peak Classifier Performance:
- **Precision:** 0.81 | **Recall:** 0.74 (tuned for $\ge 0.80$ operational safety) | **F1 Score:** 0.77
- **Timing MAE:** 42 minutes | **Timing within $\pm 1$ hour:** 74.2%

---

## 5. Key Limitations & Operational Caveats
1. **Weather Forecast Noise Proxy:** Real operational deployment requires streaming live ECMWF / IMD numerical weather feeds.
2. **Sparse Festival Observations:** Annual festivals (Diwali, Holi) occur once yearly, creating small-sample statistical uncertainty.
3. **Tariff Benchmark Caveat:** Procurement savings are computed against illustrative DSM penalty values (₹5,000 DA, ₹12,000 shortfall, ₹2,500 surplus); live deployment must ingest actual bilateral PPA contracts.
4. **Structural Grid Shifts:** Sudden policy shocks (such as government EV charging subsidies or solar rooftop net-metering expansions) alter diurnal load shapes over multi-year horizons.
