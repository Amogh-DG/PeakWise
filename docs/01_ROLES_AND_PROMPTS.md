# 01 — Stack, Team Split & Antigravity Prompts (v2: 2 backend + 2 frontend)

Project (working name): **PeakWise** — probabilistic, peak-aware load forecasting + procurement copilot for Delhi's DISCOM (CodeSpark 2026, PS 2).

Source-of-truth docs (put all three in `/docs` of the repo):
- `01_ROLES_AND_PROMPTS.md` (this file) — who does what
- `02_API_CONTRACT.md` — file schemas + REST API (frozen at Checkpoint 0)
- `03_PRD.md` — what we're building, definitions, metrics, deliverables
- `04_PROMPTS_BY_INCREMENT.md` — paste-ready Antigravity prompts, one per increment (33 total)

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

## 2. The four people

Two backend, two frontend. The backend pair carries the data/ML pipeline and the API. The frontend pair builds all six screens **and also owns the small Python pieces their screens visualise** (procurement advisor, error analysis). That's deliberate: the ML side is the heaviest part of the project, while frontend work is blocked on artifacts for the first stretch and has slack to absorb it.

| Person | Name it | Owns | Screens |
|---|---|---|---|
| **BE-1** | Data, Peak & Platform | Repo scaffold, mock data/artifacts, data cleaning, features, FastAPI, peak classifier, Docker/deploy, data-quality doc | — |
| **BE-2** | Modeling & Backtest | Backtest harness, baselines, LightGBM/XGB/Prophet/LSTM, ensemble, calibration, metrics library, feature importance | — |
| **FE-1** | Forecast & Procurement UI | UI shell + shared components + API client, procurement advisor, procurement memo, demo script | 1 Forecast, 5 Procurement |
| **FE-2** | Evaluation & Insights UI | Error analysis (heatmap, missed peaks), model card, why-peaks-are-hard write-up | 2 Accuracy, 3 Error heatmap, 4 Missed peaks, 6 Insights |

```
BE-1 ──► BE-2 ──► FE-2 (analysis needs predictions)
  │        │
  └──► API ◄── FE-1 (advisor)
         │
   FE-1 + FE-2 ──► dashboard
(Frontend works against MOCK=1 from the first block; swaps to real artifacts as they land.)
```

### Handoff artifacts (schemas in `02_API_CONTRACT.md` §1)

| File | Producer | Consumers |
|---|---|---|
| `data/processed/load_hourly.parquet` | BE-1 | BE-2, FE-2 |
| `data/processed/features_known.parquet` | BE-1 | BE-2, BE-1 (peak) |
| `src/features/ar_features.py` (`build_ar_features`) | BE-1 | BE-2, BE-1 (peak) |
| `artifacts/predictions_backtest.parquet` | BE-2 | BE-1 (peak, API), FE-1, FE-2 |
| `artifacts/metrics_accuracy.json` | BE-2 | API → FE-2 |
| `artifacts/feature_importance.json` | BE-2 | API → FE-2 |
| `artifacts/peak_predictions.parquet`, `metrics_peak.json` | BE-1 | API → FE-1, FE-2 |
| `artifacts/error_heatmap.json`, `missed_peaks.json` | FE-2 | API → FE-2 |
| `artifacts/procurement_defaults.json`, `src/procurement/advisor.py` | FE-1 | API → FE-1 |
| `artifacts/meta.json` | BE-1 (others contribute fields) | API → everyone |
| Mock data + mock artifacts (`scripts/`) | BE-1 | everyone (needed in the **first block**) |

### Folder ownership (don't edit other people's folders without a heads-up)

```
BE-1 : data/ , src/data/ , src/features/ , src/peak/ , api/ , scripts/ ,
       Makefile , docker-compose.yml , config.yaml (structure) , requirements.txt ,
       README.md (skeleton) , tests/test_contract.py , tests/test_artifact_schemas.py ,
       docs/DATA_QUALITY.md
BE-2 : src/models/ , src/backtest/ , src/metrics/ , models/
FE-1 : ui/ (shell, routing, theme, api client, shared components, pages Forecast + Procurement) ,
       src/procurement/ , docs/PROCUREMENT_MEMO.md , docs/DEMO_SCRIPT.md
FE-2 : ui/src/pages/{Accuracy,ErrorHeatmap,MissedPeaks,Insights} , ui/src/components/eval/ ,
       src/analysis/ , docs/MODEL_CARD.md , docs/WHY_PEAKS_ARE_HARD.md
Shared: artifacts/ (artifacts_mock/ is BE-1's) , docs/ASSUMPTIONS.md (append-only) , README.md "Progress log" (each person owns their own section)
```

### Git workflow (4 people, vibe-coded — keep it boring)
- `main` always runs. Each person works on branches named `be1/...`, `be2/...`, `fe1/...`, `fe2/...`.
- One small PR per increment; another teammate skims it before merge (or merge yourself if it only touches your folders).
- `git pull --rebase origin main` before you start each increment.
- Never edit another person's folders; ask them in chat (or open a PR to their folder and tag them).
- Contract/schema change = PR to `docs/02_API_CONTRACT.md` + message to the whole team first.
- Commit after every increment with a message like `be2: lightgbm quantile + pinball metrics`.

---

## 3. Shared prompt — everyone pastes this FIRST into Antigravity

**How it works:** paste this once per new Antigravity session. Then paste **one increment prompt** from `04_PROMPTS_BY_INCREMENT.md`. The agent does only that increment, reports, and stops. You review, commit, and paste the next one.

```
You are helping build "PeakWise" — a probabilistic, peak-aware load forecasting and procurement copilot for Delhi's DISCOM (hackathon problem statement PS 2).

Before doing anything, read docs/03_PRD.md, docs/02_API_CONTRACT.md and docs/01_ROLES_AND_PROMPTS.md. They are the source of truth. Do NOT change the API contract, file schemas, column names, or definitions without telling me first — teammates are building against them.

I am: <BE-1 | BE-2 | FE-1 | FE-2>. Only edit the folders my role owns (see "Folder ownership" in the roles doc) unless I say otherwise.

Working rules:
1. Work in small increments. After EACH increment: run it, run the tests, update MY section of the "Progress log" in README.md (what works, how to run it, what's next, known issues) so a fresh session can resume from the README alone, then tell me which files changed and where to download them. Keep code out of the chat — put it in files.
2. Do ONLY the increment in the prompt I paste. When it's done, report and stop — don't ask whether to continue and don't start the next increment; I'll paste the next prompt. If you're blocked by a decision only I can make, state the decision and your recommended default.
3. Time-series integrity: never random-split. Every feature must be computable at the forecast origin time (10:00 IST on D0 for targets D+1 00:00 onward). No leakage from the future.
4. Python 3.11 / TypeScript strict, type hints, tests, config in config.yaml, no hardcoded paths, fixed random seeds.
5. Any assumption or invented number goes into docs/ASSUMPTIONS.md with a one-line reason. Never silently make up data.
6. Prefer simple and working over clever. A working end-to-end slice beats a perfect component.
7. Git: work on my own branch (be1/, be2/, fe1/, fe2/ prefix), commit after each increment.
```

---

## 4. BE-1 — Data, Peak & Platform

**Mission:** Unblock everyone in the first block (scaffold + mocks + mock API), then deliver clean data, leak-safe features, the real API and the peak-event classifier.

### Tasks
**Phase 0 — first 1–2 hours (everyone is waiting on this):**
1. **Scaffold:** monorepo folders, `Makefile` (`data features backtest peak analysis api ui test all`), `docker-compose.yml`, `config.yaml`, pinned `requirements.txt`, README with a Progress log section per person and a "How to resume" section.
2. **Mock data:** `scripts/make_mock_data.py` → synthetic Delhi-like hourly load (≈2,000 MW winter → 8,300 MW summer, morning ramp 6–10, evening peak 19–23, weather-sensitive) in the exact `load_hourly` + `features_known` schema. BE-2 needs it immediately.
3. **Mock artifacts:** `scripts/make_mock_artifacts.py` writes every file into `artifacts_mock/` (committed) in contract shape (quantiles ordered, enums valid).
4. **FastAPI on mocks:** every endpoint in contract §2, Pydantic models mirroring the contract, `MOCK=1` mode, error format from §3, CORS, contract tests. `/procurement/recommend` calls `src/procurement/advisor.py::recommend` (stub until FE-1 lands it). Frontend builds against this.

**Phase 1+ — real data and features:**
5. **Source real data:** hourly (or finer) Delhi demand, 2+ years. Try the organizer dataset, Delhi SLDC historical demand reports, Grid-India (POSOCO) reports, Kaggle. **If only daily peaks exist, tell the team immediately.** Record source + licence in `data/raw/README.md`. Weather: Open-Meteo archive for Delhi — temperature, humidity, dewpoint, wind, cloud cover.
6. **Clean:** complete hourly `Asia/Kolkata` index (India has no DST, but still check for duplicate/missing/shifted timestamps); gaps ≤ 3h linear, longer gaps from same hour-of-week neighbours; set `is_imputed`, `imputation_method`; flag outage drops with a MAD z-score on residuals vs hour-of-week profile (`is_outage_suspect`, don't delete). Write `docs/DATA_QUALITY.md` with real numbers.
7. **Known features** (`features_known.parquet`, names in contract §1.2): calendar; festival windows from `data/external/festivals.csv` (Diwali, Holi, Eid-ul-Fitr, Eid-ul-Adha, Dussehra, Raksha Bandhan, Independence Day… cite sources); lockdown and odd-even flags (research and cite dates, only if covered by data); heat index (Rothfusz), cooling-degree-hours (base 24 °C configurable, plus rolling 24h), temperature lags 1/3/6/12/24/48/72 h, rolling mean temp 24h/72h; `trend_t`.
8. **Autoregressive features:** `build_ar_features(load_df, origin_ts, target_ts)` — lags relative to the forecast **origin** (at 10:00 D0 the last known load is 09:00 D0). Leakage test required.
9. **Weather-forecast leakage:** default = actuals + horizon-scaled Gaussian noise (`config.yaml: weather_noise`); use archived forecasts if the Open-Meteo historical-forecast API covers the range. Document in `ASSUMPTIONS.md`.

**Phase 2–3 — peak classifier (`src/peak/`):**
10. Label = day's peak MW > threshold, threshold = 90th percentile of daily peaks **in each fold's training window** (config variant: season-relative). LightGBM classifier on origin-safe features + BE-2's daily P50/P90 max, isotonic-calibrated probability. Peak *hour*: multiclass over 24 hours, with `argmax(P50)` as a baseline. Tune the decision threshold for recall; document the trade-off. Rule baseline: "same weekday last week exceeded threshold". Outputs: `peak_predictions.parquet`, `metrics_peak.json` (contract §1.5, §1.7).

**Phase 3–4 — finish:**
11. Switch API from mock to real artifacts, assemble `artifacts/meta.json`, run contract tests on both. Docker Compose one-command run, deploy, fresh-clone test. You drive the final submission checklist (PRD §12).

### Definition of done
`docker compose up` serves the API with real artifacts; `make data features peak` run from scratch; leakage + contract + schema tests pass; `DATA_QUALITY.md` written.

### Antigravity prompts

See `04_PROMPTS_BY_INCREMENT.md` → **BE-1**. Paste one increment at a time, review, commit, then paste the next.

---

## 5. BE-2 — Modeling & Backtest

**Mission:** Produce honest, calibrated P05–P95 hourly forecasts for D+1 (24h) and D+1…D+7 (168h) that demonstrably beat the baselines — especially at peak hours.

### Tasks
1. **Backtest harness first** (`src/backtest/`): rolling-origin, expanding window. Origin = 10:00 IST every day; targets D+1 00:00 … D+7 23:00 (horizons 14–181 h). Min train 2 years (adjust to your data), retrain monthly, test on the last ≥ 12 months. Model-agnostic interface:
   ```python
   class Forecaster(Protocol):
       name: str
       def fit(self, train_end: Timestamp) -> None: ...
       def predict(self, origin: Timestamp) -> DataFrame  # target_ts, horizon_h, p05,p10,p50,p90,p95
   ```
   Writes `artifacts/predictions_backtest.parquet` (contract §1.4). Start on BE-1's mock data (delivered in the first block).
2. **Baselines:** seasonal-naive (same hour last week) and linear regression (quantiles from residual quantiles by hour). Run end-to-end before anything else.
3. **LightGBM quantile:** one model per quantile with `horizon_h` as a feature; sort to prevent crossing; zero-weight `is_outage_suspect` rows in training.
4. **XGBoost** (optional), **Prophet** (holidays + temperature regressor), **one deep model** (LSTM or TFT, quantile loss), time-boxed.
5. **Ensemble:** weighted quantile average; weights fit on a validation window ending before the test window.
6. **Calibration:** conformalized quantile regression on a rolling calibration window; keep raw (`*_raw`) and calibrated columns; PICP before/after for 80% (P10–P90) and 90% (P05–P95).
7. **Metrics library** (`src/metrics/`; FE-2 and BE-1 reuse it): MAPE (per horizon-day), RMSE, MAE, bias, pinball, PICP, MPIW, % improvement vs seasonal-naive. Output `metrics_accuracy.json` (contract §1.6) for every model × horizon-day × segment.
8. **Feature importance:** SHAP/gain for LightGBM → `feature_importance.json`.
9. **Daily-peak summaries for BE-1:** export per-origin daily P10/P50/P90 max (and argmax hour) so the peak classifier can use them. Agree the exact columns with BE-1 on day one and add them to the contract by PR.

### Definition of done
`make backtest` regenerates predictions + metrics for all models; accuracy table covers every model × horizon-day × segment; every model beats or is explicitly flagged against seasonal-naive; PICP reported.

### Antigravity prompts

See `04_PROMPTS_BY_INCREMENT.md` → **BE-2**. Paste one increment at a time, review, commit, then paste the next.

---

## 6. FE-1 — Forecast & Procurement UI

**Mission:** Build the app shell and the two decision-facing screens — the forecast view (the star of the demo) and the procurement view — plus the procurement logic behind it.

### Tasks
1. **UI shell (first block):** Vite + React + TypeScript + Tailwind + Plotly.js in `ui/`; routing for all six pages (FE-2 fills four of them); theme (colour-blind-safe, light/dark optional); typed API client generated from the contract; shared components (`ChartCard`, `ModelSelect`, `DatePicker`, `StatTile`, loading/error/empty states). Merge the shell **early** — FE-2 builds on it.
2. **Screen 1 — Forecast:** date picker, day/week toggle, model selector; actual line; P10–P90 shaded band plus lighter P05–P95; predicted vs actual peak markers; at-risk hours shaded; peak-probability badge. Accepts `?date=` so FE-2's missed-peak drill-down can link to it.
3. **Procurement advisor** (`src/procurement/advisor.py`): `recommend(start_date, days, model, risk_quantile, tariff)` exactly per contract §2.12.
   - Schedule = forecast quantile `risk_quantile` (default 0.9, or `"newsvendor"` = `(under − da)/(under − resale)`).
   - Cost per hour = `da_price·S + under_price·max(D−S,0) − resale_price·max(S−D,0)`.
   - Baselines: flat at previous week's mean MW; also report flat at previous week's peak.
   - `p90_risk_exposure_inr` = cost if demand follows the P90 path − cost if it follows the P50 path.
   - Tariff defaults are **illustrative placeholders** — label them clearly (`procurement_defaults.json`, `ASSUMPTIONS.md`).
   - Unit tests with hand-computed numbers. Deliver a working version early so BE-1 can replace the API stub.
4. **Screen 5 — Procurement:** week picker; risk-quantile slider with a "newsvendor" option; editable tariff; schedule vs flat chart; cost KPIs; P90 exposure; at-risk hours; a small "cost vs quantile" curve so the planner sees the trade-off.
5. **Docs:** `docs/PROCUREMENT_MEMO.md` (sample week: recommended schedule, P90 exposure, simulated cost vs naive flat, using real numbers) and `docs/DEMO_SCRIPT.md` (3-minute story: problem → tail risk → peak flag → procurement savings).

### Definition of done
Screens 1 and 5 work on real artifacts; `recommend()` matches the contract and passes tests; memo and demo script written with real numbers.

### Antigravity prompts

See `04_PROMPTS_BY_INCREMENT.md` → **FE-1**. Paste one increment at a time, review, commit, then paste the next.

---

## 7. FE-2 — Evaluation & Insights UI

**Mission:** Make the model's honesty visible — accuracy vs baselines, where errors concentrate, which peaks were missed and why — and write the analysis docs.

### Tasks
1. **Error analysis** (`src/analysis/`) — start on mock `predictions_backtest.parquet`:
   - Error decomposition by season, hour, peak vs off-peak.
   - `artifacts/error_heatmap.json` (hour × season for `mape`, `rmse`, `bias`, per model and horizon-day; contract §1.8).
   - `artifacts/missed_peaks.json` with rule-based tags (`festival`, `holiday`, `heatwave`, `weather_miss`, `weekend`) and a one-line note each (contract §1.9). Reads `peak_predictions.parquet` from BE-1.
2. **Screen 2 — Accuracy:** table (model × horizon-day × segment) with % improvement vs seasonal-naive, PICP/MPIW columns, 80% vs 90% interval labelled clearly; peak precision/recall/timing card including the rule baseline.
3. **Screen 3 — Error heatmap:** hour × season grid, metric toggle (mape/rmse/bias), horizon-day toggle, counts on hover.
4. **Screen 4 — Missed peaks:** table sorted by magnitude error with tag filters; click-through opens FE-1's Forecast page with `?date=`.
5. **Screen 6 — Insights:** feature importance by group, rendered "why peaks are hard" write-up, model-card summary.
6. **Docs:**
   - `docs/MODEL_CARD.md` — assumptions, data, limits, known failure modes, weather-proxy caveat, interval-calibration results.
   - `docs/WHY_PEAKS_ARE_HARD.md` — weather sensitivity (MW per °C at peak hours), festival effects, thermal inertia (lagged-temperature evidence), with reproducible figures computed from the data.

### Definition of done
`make analysis` regenerates the JSONs; screens 2, 3, 4, 6 work on real artifacts; model card and write-up contain real numbers.

### Antigravity prompts

See `04_PROMPTS_BY_INCREMENT.md` → **FE-2**. Paste one increment at a time, review, commit, then paste the next.

---

## 8. Sync checkpoints

| # | When | Everyone confirms |
|---|---|---|
| **0** | First 1–2 hours | Read all 3 docs; contract frozen; names ↔ BE-1/BE-2/FE-1/FE-2 assigned; open decisions (PRD §13) settled |
| **0.5** | End of BE-1's Increments 1–3 | Scaffold merged; mock data + mock artifacts + mock API usable; FE-1 shell merged; BE-2 and FE-2 can start |
| **1** | End of Phase 1 | Real data cleaned; baselines + harness run; API serving real baselines; Forecast page live |
| **2** | End of Phase 2 | LightGBM quantile + calibration done; peak classifier v1; screens 1–3 on real artifacts. **Streamlit-fallback decision here** |
| **3** | End of Phase 3 | Prophet/LSTM/ensemble in; procurement + heatmap + missed-peak drill-down live |
| **4** | ~80% of time | **Feature freeze.** Only docs, bug fixes, demo polish |
| **5** | Last block | Fresh-clone test (`docker compose up` on a clean machine), demo rehearsal, submission packaged |

**Phases:** 0 = contract + scaffold + mocks → 1 = data + baselines + API-on-mocks → 2 = GBM + calibration + peak v1 + core UI → 3 = extra models + procurement + analysis UI → 4 = docs, memo, write-up, polish → 5 = rehearse + submit.

**Pairs that should talk daily:** BE-1 ↔ BE-2 (data schema, peak-summary columns), FE-1 ↔ FE-2 (shared components, `?date=` drill-down link), BE-1 ↔ FE-1 (API stub → advisor).

---

## 9. Repo layout

```
peakwise/
├─ README.md                  # Progress log per person + how to resume
├─ Makefile  config.yaml  docker-compose.yml  requirements.txt
├─ docs/    01_ROLES_AND_PROMPTS.md  02_API_CONTRACT.md  03_PRD.md
│           ASSUMPTIONS.md  DATA_QUALITY.md  MODEL_CARD.md
│           PROCUREMENT_MEMO.md  WHY_PEAKS_ARE_HARD.md  DEMO_SCRIPT.md
├─ data/    raw/  external/festivals.csv  processed/
├─ src/     data/  features/  peak/            # BE-1
│           models/  backtest/  metrics/       # BE-2
│           procurement/                       # FE-1
│           analysis/                          # FE-2
├─ models/                    # saved model files (BE-2)
├─ artifacts/                 # everything the API serves (parquet + json)
├─ artifacts_mock/            # committed mock artifacts for MOCK=1 (BE-1)
├─ scripts/ make_mock_data.py  make_mock_artifacts.py   # BE-1
├─ api/                       # FastAPI (BE-1)
├─ ui/                        # Vite + React + TS (FE-1 shell; FE-2 pages)
└─ tests/
```
