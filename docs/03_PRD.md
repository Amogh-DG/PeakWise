# 03 — Product Requirements Document (PRD)

**Product (working name):** PeakWise — Probabilistic Peak-Aware Load Forecasting & Procurement Copilot for Delhi's DISCOM
**Event:** CodeSpark 2026 — National Level Hackathon, Problem Statement 2
**Version:** 1.0 (draft for Checkpoint 0)

---

## 1. Overview

Delhi's DISCOM must buy power a day (and up to a week) ahead against demand that swings from ~2,000 MW in winter to ~8,300 MW in summer, with a sharp morning ramp (≈6–10 AM) and an evening peak (≈7–11 PM). A point forecast hides the thing planners actually fear: **how bad can the peak get, and which hours are at risk 24–72 hours out?**

PeakWise produces hourly **probabilistic forecasts** (P05/P10/P50/P90/P95), a dedicated **peak-event classifier** (will tomorrow's peak exceed the top-decile threshold, and when?), and a **procurement advisor** that converts the P90 forecast into a day-ahead schedule and prices under- vs over-procurement. Everything is evaluated with a strict **walk-forward backtest** and shown in a dashboard that makes the model's failure modes visible.

**Guiding principle (from the PS):** a model that's great on average but bad at peaks has failed. Peaks are the product.

## 2. Users & jobs-to-be-done

| User | Job | What they need from PeakWise |
|---|---|---|
| Power procurement planner | Decide tomorrow's and next week's purchase schedule | Recommended hourly schedule, cost vs naive, risk exposure |
| Load dispatch / control-room engineer | Know which hours may breach capacity | At-risk hours, peak probability and expected time |
| Planning head / regulator-facing analyst | Trust and audit the model | Accuracy vs baselines, calibration (PICP), failure drill-down, model card |
| Hackathon judge | Verify the system meets the PS | Reproducible pipeline, tables, dashboard, memo, write-up |

## 3. Goals and non-goals

### Goals
1. Hourly P10/P50/P90 (+P05/P95) forecasts for **D+1 (24h)** and **D+1…D+7 (168h)**.
2. A separate peak-event classifier with precision/recall, plus peak-timing and peak-magnitude errors.
3. Leak-safe feature engineering beyond raw weather (CDH, heat index, thermal inertia, festivals, events, trend).
4. Procurement recommendation + simulated cost vs naive flat schedule.
5. Walk-forward backtest, never random split; beat seasonal-naive and linear baselines and report the improvement.
6. A dashboard that answers: "where, when and why does the model miss?"

### Non-goals
- Real-time (sub-hour) dispatch or live SCADA integration.
- Real market bidding / exchange integration. Tariff numbers are illustrative.
- Retraining on request in the UI (retraining is an offline `make` step).
- Multi-DISCOM or state-level generalisation.
- User accounts / auth.

## 4. Success metrics (initial targets — revise once baselines are measured)

| Area | Metric | Target |
|---|---|---|
| Accuracy | RMSE and MAPE vs seasonal-naive, at every horizon-day | Beat baseline at **every** horizon-day; stretch: ≥ 20% RMSE improvement on D+1 |
| Peak accuracy | Same metrics restricted to `peak_hours` segment | Improvement vs baseline also holds in `peak_hours` (not only on average) |
| Calibration | PICP of 80% interval (P10–P90) | Within 76–84% |
| Calibration | PICP of 90% interval (P05–P95) | Within 86–94% |
| Peak events | Recall at tuned threshold | ≥ 0.80, with precision ≥ 0.60 (report whatever is achieved honestly) |
| Peak timing | Share of peak days with predicted peak hour within ±1 h | ≥ 70% |
| Decision value | Simulated cost vs naive flat schedule (sample week) | Lower cost, and P90 exposure quantified |
| Reproducibility | Fresh clone → `docker compose up` / `make all` | Works with no manual steps beyond data download |

Report actual numbers even if targets are missed; honesty about failure modes is part of the score.

## 5. Scope (MoSCoW)

| Priority | Item |
|---|---|
| **Must** | Cleaned hourly data + documented imputation; features per §7; seasonal-naive + linear baselines; LightGBM quantile; walk-forward backtest; metrics (MAPE per horizon, RMSE, pinball, PICP, peak timing & magnitude); peak classifier; procurement advisor + sample-week memo; dashboard with bands, peak markers, error heatmap, missed-peak drill-down; model card; "why peaks are hard" write-up |
| **Should** | Prophet; one deep model (LSTM/TFT); ensemble; conformal calibration; XGBoost; feature-importance view; deployed URL |
| **Could** | Weather what-if scenario endpoint (API §2.16); newsvendor quantile UI; SHAP per-day explanation |
| **Won't** | Live data feeds, auth, market integration, mobile app |

## 6. Functional requirements

### Data (Role A)
- **FR-D1** Ingest ≥ 2 years of hourly Delhi load (or finer, aggregated to hourly) and hourly weather.
- **FR-D2** Produce a complete hourly IST index; document every gap, imputation method and outlier rule in `DATA_QUALITY.md`.
- **FR-D3** Flag, don't delete, suspected outage drops (`is_outage_suspect`).
- **FR-D4** Check and document timestamp/clock issues (duplicates, shifts, missing hours) even though IST has no DST.
- **FR-D5** Provide synthetic mock data in the same schema on day 0.

### Features (Role A)
- **FR-F1** Calendar: hour, day-of-week, month, day-of-year, cyclic encodings, weekend, public holiday.
- **FR-F2** Festival windows (Diwali, Holi, Eid, plus others) as days-to/days-since features, with cited dates.
- **FR-F3** Event flags: lockdown and odd-even scheme periods (where covered by the data).
- **FR-F4** Weather-derived: heat index, cooling-degree-hours (hourly and rolling 24h), temperature lags 1–72 h, rolling temperature means (24h/72h).
- **FR-F5** Growth-trend term (`trend_t`) and trailing-level autoregressive features.
- **FR-F6** All autoregressive features are relative to the forecast origin (no leakage); enforced by test.

### Forecasting (Role B)
- **FR-M1** Seasonal-naive (same hour last week) and linear-regression baselines.
- **FR-M2** LightGBM with quantile objective for q ∈ {0.05, 0.1, 0.5, 0.9, 0.95}; no quantile crossing.
- **FR-M3** Prophet (holiday-aware) and one deep model (LSTM or TFT) for comparison; XGBoost optional.
- **FR-M4** Ensemble with weights fit only on a validation window preceding the test window.
- **FR-M5** Interval calibration (conformalized quantile regression); raw and calibrated outputs stored.
- **FR-M6** Day-ahead (24h) and week-ahead (168h) outputs from the same pipeline.

### Backtest & metrics (Role B, shared)
- **FR-B1** Rolling-origin expanding-window evaluation (§9); no random splits anywhere.
- **FR-B2** Metrics: MAPE (per horizon-day, with a documented caveat near low loads), RMSE, MAE, bias, pinball loss, PICP (80% and 90%), MPIW, % improvement vs seasonal-naive.
- **FR-B3** Segments: all, each season, peak_hours, off_peak.
- **FR-B4** Feature importance for the main model.

### Peak events (Role C)
- **FR-P1** Binary classifier: day's peak > threshold (top decile of daily peaks in the fold's training window).
- **FR-P2** Peak-hour prediction; report timing error (minutes) and magnitude error (MW).
- **FR-P3** Report precision, recall, F1, PR-AUC, confusion matrix; decision threshold tuned for recall with documented trade-off.
- **FR-P4** Compare against at least one rule-based baseline.
- **FR-P5** Per-day outcome label (`hit`, `miss`, `false_alarm`, `correct_reject`).

### Procurement (Role C)
- **FR-C1** Convert a chosen forecast quantile (default P90, or newsvendor quantile) into an hourly day-ahead schedule.
- **FR-C2** Cost model: `da_price·S + under_price·max(D−S,0) − resale_price·max(S−D,0)` with editable tariff; defaults flagged as illustrative.
- **FR-C3** Compare against naive flat schedules (previous week's mean; previous week's peak).
- **FR-C4** Report P90 risk exposure and at-risk hours.
- **FR-C5** Sample-week memo with schedule, exposure and simulated cost vs naive.

### Analysis (Role C)
- **FR-A1** Error decomposition by season, hour, peak vs off-peak.
- **FR-A2** Hour × season error heatmap (mape / rmse / bias).
- **FR-A3** Missed-peak list with auto-generated tags and notes.
- **FR-A4** Model card and "why peaks are hard" write-up with figures computed from data.

### API & UI (Role D)
- **FR-U1** API implements every endpoint in `02_API_CONTRACT.md` with contract tests.
- **FR-U2** Forecast screen: shaded P10–P90 band (lighter P05–P95), actual line, peak markers, at-risk hours, day/week toggle, model selector.
- **FR-U3** Accuracy screen: table vs baselines per horizon-day with improvement %; peak precision/recall card.
- **FR-U4** Error screen: hour × season heatmap with metric toggle.
- **FR-U5** Missed-peaks screen: list with tags → drill-down to that day's chart.
- **FR-U6** Procurement screen: week picker, risk-quantile control, editable tariff, schedule vs flat, cost comparison, P90 exposure.
- **FR-U7** Insights screen: feature importance and the "why peaks are hard" write-up.
- **FR-U8** One-command run (`docker compose up`); loading and error states on every screen.

## 7. Feature specification (summary)

| Group | Features |
|---|---|
| Calendar | hour, dow, month, doy, sin/cos, weekend, holiday |
| Festivals/events | days to/since Diwali, Holi, Eid; festival window flag; lockdown; odd-even |
| Weather | temp, RH, dewpoint, wind, cloud, heat index, CDH (base default 24 °C, configurable) |
| Thermal inertia | temp lags 1/3/6/12/24/48/72 h; rolling mean 24h/72h; rolling CDH 24h |
| Trend | `trend_t`; trailing 365-day mean level |
| Autoregressive (origin-relative) | same hour last week, last known day, 7d/30d means, last-week daily peak |
| Horizon | `horizon_h` (for the global quantile models) |

Exact column names: `02_API_CONTRACT.md` §1.2–1.3.

## 8. Definitions

| Term | Definition |
|---|---|
| Forecast origin | 10:00 IST on day D0 |
| Day-ahead | Hourly forecast for D+1 (24 h) |
| Week-ahead | Hourly forecast for D+1…D+7 (168 h) |
| Peak day | Day whose maximum hourly load exceeds the 90th percentile of daily peaks in the training window of that backtest fold (variant: season-relative, behind a config flag) |
| Peak hours | Hour-beginning 6–10 (morning ramp) and 19–23 (evening peak) |
| Seasons | winter Dec–Feb; summer Mar–Jun; monsoon Jul–Sep; post-monsoon Oct–Nov |
| At-risk hour | Hour where P90 ≥ peak threshold MW |
| PICP | Share of actuals inside the interval. Nominal 80% for P10–P90, 90% for P05–P95 |
| MPIW | Mean prediction-interval width (MW) — guards against "wide intervals are trivially calibrated" |
| Peak-timing error | Predicted peak time − actual peak time, in minutes (hourly data → multiples of 60 unless native resolution is finer) |
| Peak-magnitude error | Predicted daily max (P50) − actual daily max, in MW |
| P90 risk exposure | Cost if demand follows the P90 path minus cost if it follows the P50 path, same schedule |
| MAPE caveat | Inflated at low load (winter nights); always report alongside RMSE/MAE and the segment view |

> **Note on intervals:** the PS names P10/P50/P90 but also asks whether "90% intervals contain 90% of actuals." P10–P90 is an **80%** interval, so we also train P05/P95 and report PICP for both. Don't conflate them in the write-up.

## 9. Backtest protocol (frozen)

| Parameter | Value |
|---|---|
| Scheme | Rolling-origin, expanding training window |
| Origin | 10:00 IST every day |
| Targets | D+1 00:00 … D+7 23:00 (horizons 14–181 h) |
| Min training span | 2 years (adjust to available data; document) |
| Retraining | Monthly (fold = one month of origins) |
| Test span | Last ≥ 12 months after min-train (all remaining data if shorter) |
| Peak threshold | Recomputed per fold from training data only |
| Calibration window | Rolling, ends before the fold's test origins |
| Ensemble weights | Fit on a validation window ending before test |
| Forbidden | Random splits, features using data at or after the origin, tuning on test folds |

**Weather proxy caveat:** true day-ahead weather *forecasts* aren't available historically. Default = observed weather plus horizon-scaled Gaussian noise (`config.yaml: weather_noise`). If the archived-forecast API covers the range, use it. State this in the model card; it is the main optimism risk in the results.

## 10. Dashboard spec

| # | Screen | Key elements |
|---|---|---|
| 1 | Forecast | Date/week picker, model dropdown, actual line, P10–P90 band, P05–P95 lighter band, predicted vs actual peak markers, at-risk hours shaded, peak probability badge |
| 2 | Accuracy | Table (model × horizon-day × segment) with % improvement vs seasonal-naive, PICP/MPIW columns, peak precision/recall/timing card |
| 3 | Error heatmap | Hour × season grid, metric toggle (mape/rmse/bias), horizon-day toggle |
| 4 | Missed peaks | Table sorted by magnitude error with tags; click opens the day on the Forecast chart |
| 5 | Procurement | Week picker, risk-quantile slider + "newsvendor" option, tariff editor, schedule vs flat chart, cost KPIs, P90 exposure, at-risk hours |
| 6 | Insights | Top features by group, rendered "why peaks are hard" write-up, model-card summary |

Design notes: colour-blind-safe palette; light/dark ok; every chart has units and a legend; no screen without an empty/error state.

## 11. Procurement model

- Inputs: forecast quantiles (from API/artifacts), tariff triple (`da_price`, `under_price`, `resale_price`).
- Schedule: `S_h = q-th quantile forecast`, `q` = user risk quantile (default 0.9) or `(under − da)/(under − resale)` (newsvendor).
- Evaluation: realised cost against actuals for backtest weeks; P90 exposure for any week.
- Defaults (illustrative, **not real tariffs**): `da_price` 5,000, `under_price` 12,000, `resale_price` 2,500 INR/MWh → newsvendor q ≈ 0.74.
- Insight to surface: when blackout / real-time penalty risk is high, the optimal quantile rises; the dashboard should show cost as a function of `q` so the planner sees the trade-off.

## 12. Deliverables checklist (maps to "What you must submit")

| PS requirement | Where it lives | Owner |
|---|---|---|
| Reproducible pipeline (data → features → train → backtest) + model card | `Makefile`, `src/`, `docs/MODEL_CARD.md` | A/B/D, C |
| Accuracy table vs baselines across all horizons + peak precision/recall | `artifacts/metrics_accuracy.json`, `metrics_peak.json`, UI screen 2 | B, C |
| Dashboard: shaded bands, peak markers, error heatmap (hour × season), "days the model missed the peak" drill-down | UI screens 1, 3, 4 | D (data from B, C) |
| Procurement memo: sample week schedule, P90 exposure, simulated cost vs naive flat | `docs/PROCUREMENT_MEMO.md`, UI screen 5 | C, D |
| Short write-up on why peaks are hard | `docs/WHY_PEAKS_ARE_HARD.md`, UI screen 6 | C |
| Imputation documentation (data quality) | `docs/DATA_QUALITY.md` | A |
| Baselines beaten, improvement reported | UI screen 2, README summary table | B |

**Final submission checklist (D drives):**
- [ ] Fresh clone → `docker compose up` works on a clean machine
- [ ] `make all` reproduces artifacts from raw data
- [ ] README: overview, architecture diagram, how to run, results table, Progress log
- [ ] All five docs in `/docs` contain real numbers (no placeholders)
- [ ] Accuracy table has every model × horizon-day, baselines included
- [ ] PICP reported for 80% and 90% intervals, before and after calibration
- [ ] Peak-event precision/recall + rule baseline
- [ ] Dashboard URL (or demo video) + screenshots in README
- [ ] Known limitations stated (weather proxy, tariff placeholders, data span)
- [ ] 3-minute demo rehearsed (`docs/DEMO_SCRIPT.md`)

## 13. Open decisions (settle at Checkpoint 0)

| # | Decision | Recommended default |
|---|---|---|
| 1 | Where does real load data come from? (If only daily peaks exist, the whole plan shifts.) | Organizer dataset → Delhi SLDC → Grid-India → Kaggle |
| 2 | Weather in backtests: archived forecasts vs actuals + noise | Actuals + horizon-scaled noise, documented |
| 3 | Peak threshold: global top-decile vs season-relative | Global top-decile (matches PS), season-relative as a reported variant |
| 4 | Deep model: LSTM vs TFT | LSTM (cheaper); TFT only if time remains |
| 5 | UI: React vs Streamlit | React + Plotly; switch to Streamlit at Checkpoint 2 if behind |
| 6 | Hosting | Render/Railway + docker-compose fallback |
| 7 | Team names ↔ roles A/B/C/D | Assign now, write in README |

## 14. Non-functional requirements

- **Reproducibility:** pinned dependencies, fixed seeds, config-driven paths, one-command run.
- **Time-series integrity:** leakage tests in CI; every feature documents its availability time.
- **Performance:** API p95 < 500 ms for artifact-backed endpoints; procurement recommend < 2 s.
- **Transparency:** every assumption in `docs/ASSUMPTIONS.md`; every imputed or noised value traceable.
- **Maintainability:** typed Python, Pydantic models mirror the contract, tests for schemas and contract.
- **Accessibility:** colour-blind-safe charts, keyboard-reachable controls, labelled axes with units.

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Real hourly Delhi load data hard to find or short | Blocks everything | Role A spends the first block on this; mock data keeps others moving; escalate at Checkpoint 0 |
| Weather leakage inflates accuracy | Misleading results, judges notice | Noise injection + explicit caveat in model card and UI |
| Great average accuracy, poor peaks | Fails the PS's core test | Always report `peak_hours` segment; peak-weighted analysis; missed-peak drill-down |
| Intervals miscalibrated | Tail-risk claims untrustworthy | Conformal calibration; report PICP raw vs calibrated; report MPIW |
| Deep model eats time | Schedule slip | Time-box; ship as documented comparison |
| Contract drift between AI-assisted roles | Integration failures at the end | Contract tests, schema tests, change process in contract §5, weekly integration smoke test |
| Few festival/event samples | Weak festival effect estimates | Short windows (±2 days), report uncertainty, discuss in write-up |
| Tariff numbers look made-up | Credibility of procurement memo | Label as illustrative; make editable; show sensitivity to `q` |
| UI falls behind | Weak demo | Streamlit fallback calling the same API |

## 16. Timeline (phases; map to your actual hours)

| Phase | Content |
|---|---|
| 0 | Contract + PRD frozen, repo scaffold, mock data + mock artifacts, role assignments |
| 1 | Real data cleaned, baselines through the harness, API on mocks → baselines, first dashboard screen |
| 2 | LightGBM quantile + calibration, peak classifier v1, UI screens 1–3 on real artifacts |
| 3 | Prophet / LSTM / ensemble, procurement advisor, heatmap + missed-peak drill-down |
| 4 | **Feature freeze (~80%)**; model card, memo, write-up, bug-fixes, deployment |
| 5 | Fresh-clone test, demo rehearsal, submission |
