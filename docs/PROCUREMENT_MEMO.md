# DISCOM Day-Ahead Power Procurement Recommendation & Risk Analysis

**To:** System Operations & Power Procurement Committee, Delhi DISCOM  
**From:** Antigravity Load Forecasting & Copilot System  
**Date:** 2024-07-08 (Evaluation Period: 2024-07-08 to 2024-07-14, 168 Hours)  
**Subject:** Optimal Day-Ahead Scheduling Under Asymmetric Shortage Penalties and Peak Heatwave Exposure  

---

> [!NOTE]
> **Tariff Disclaimer:** The power purchase tariffs applied in this evaluation (Day-Ahead Base = ₹5,000/MWh, Shortfall Real-Time Penalty = ₹12,000/MWh, Surplus Resale Salvage = ₹2,500/MWh) are illustrative benchmark placeholders reflecting asymmetric Deviation Settlement Mechanism (DSM) exposure, not actual Bilateral/PPA contract tariffs.

---

## 1. Executive Summary & Sample Week Rationale

The week of **July 8 to July 14, 2024** was selected for operational review because it represents Delhi's highest power demand surge of 2024. Sustained 42 °C+ ambient temperatures drove aggregate air-conditioning load, culminating in Delhi's record peak of **8,264.8 MW on July 12, 2024 at 15:00 IST**.

Conventional DISCOM procurement relies on static rule-based baselines (e.g., matching the previous week's flat mean or peak load). Under extreme peak heatwaves, naive baselines lead to catastrophic real-time shortfall penalties when demand surges, or massive stranded surplus costs when temperatures drop.

By deploying the **calibrated probabilistic Ensemble forecast** with an asymmetric loss risk quantile of **P90** ($q=0.90$), the DISCOM secures:
- **Total Scheduled Volume:** 1,116,232.3 MWh across 168 hours.
- **Simulated Realized Cost:** **₹ 551.64 Crore**.
- **Net Cost Savings vs Flat Mean Baseline:** **₹ 74.38 Crore (+11.88% savings)**.
- **Net Cost Savings vs Flat Peak Baseline:** **₹ 46.22 Crore (+7.73%)**.
- **Tail Risk Hedging:** P90 risk exposure is contained to **₹ 11.97 Crore**, with **31 statutory peak hours** proactively sheltered against real-time grid penalties.

---

## 2. Dispatch Schedule & Load Profile

![Procurement Schedule](figures/procurement_schedule.png)

### Key Operational Observations:
1. **Dynamic Hourly Tracking:** The recommended day-ahead schedule closely tracks diurnal ramp-up, escalating from early morning baselines (~5,400 MW) to evening peak thresholds exceeding 7,800 MW.
2. **At-Risk Hour Shielding (Orange Shading):** 31 hours across the 7-day period breached the 90th percentile peak threshold (7,650 MW). By procuring at the P90 quantile during these windows, real-time unserved energy purchases at the penal ₹12,000/MWh DSM rate were limited to just 21 hours out of 168.

---

## 3. Daily Breakdown & Financial Performance

| Day | Date | Scheduled Volume (MWh) | Realized Cost (₹ Cr) | Baseline Flat Cost (₹ Cr) | Net Savings (₹ Cr) |
|---|---|---|---|---|---|
| Mon | 2024-07-08 | 160,698.6 | ₹ 79.82 | ₹ 91.44 | **+₹ 11.61** |
| Tue | 2024-07-09 | 162,230.4 | ₹ 80.04 | ₹ 92.12 | **+₹ 12.08** |
| Wed | 2024-07-10 | 160,910.1 | ₹ 79.82 | ₹ 91.60 | **+₹ 11.78** |
| Thu | 2024-07-11 | 160,227.5 | ₹ 79.08 | ₹ 89.57 | **+₹ 10.49** |
| Fri | 2024-07-12 | 162,434.1 | ₹ 80.21 | ₹ 91.28 | **+₹ 11.07** |
| Sat | 2024-07-13 | 155,654.9 | ₹ 76.92 | ₹ 85.69 | **+₹ 8.77** |
| Sun | 2024-07-14 | 154,076.7 | ₹ 75.75 | ₹ 84.33 | **+₹ 8.58** |

---

## 4. Sensitivity to Risk Quantile ($q$) & Newsvendor Optimum

Under asymmetric shortage pricing, the theoretical optimal dispatch quantile is governed by the Newsvendor ratio:
$$q^* = \frac{\text{under\_price} - \text{da\_price}}{\text{under\_price} - \text{resale\_price}} = \frac{12000 - 5000}{12000 - 2500} = \frac{7000}{9500} \approx 0.737$$

The table below contrasts realized procurement cost across alternative risk tolerances:

| Strategy | Risk Quantile | Cost (₹ Cr) | Savings vs Flat (₹ Cr) | Savings (%) | P90 Exposure (₹ Cr) | Shortfall Hours |
|---|---|---|---|---|---|---|
| q=0.50 | q=0.50 | ₹ 556.54 | +₹ 69.48 | +11.10% | ₹ 57.44 | 119 / 168 |
| q=0.70 | q=0.70 | ₹ 550.71 | +₹ 75.31 | +12.03% | ₹ 34.70 | 66 / 168 |
| Newsvendor (q=0.737) | Newsvendor (q=0.737) | ₹ 550.37 | +₹ 75.65 | +12.08% | ₹ 30.52 | 57 / 168 |
| q=0.90 | q=0.90 | ₹ 551.64 | +₹ 74.38 | +11.88% | ₹ 11.97 | 21 / 168 |
| q=0.99 | q=0.99 | ₹ 554.72 | +₹ 71.30 | +11.39% | ₹ 11.97 | 11 / 168 |

### Analysis:
- Setting $q=0.50$ (scheduling purely at median demand) exposes the utility to frequent real-time shortages during afternoon heatwaves, yielding higher penalty costs.
- The Newsvendor quantile ($q=0.737$) mathematically minimizes expected cash outflow under symmetric statistical errors.
- The P90 quantile ($q=0.90$) deliberately purchases insurance against tail load events, slightly increasing surplus resale volumes in exchange for near-zero operational grid disruption during severe transmission congestion.

---

## 5. Implementation Roadmap for Operations

1. **Gate Closure Automation:** Integrate `POST /procurement/recommend` directly into the day-ahead bidding desk API by 10:30 IST daily.
2. **Dynamic Risk Setting:** Apply $q=0.74$ during benign weather conditions (winter, monsoon) and elevate to $q=0.90$ whenever heatwave alerts or festival windows are active.
3. **Continuous Conformal Monitoring:** Monitor empirical PICP coverage on the Accuracy dashboard; if PICP 90 drops below 88%, trigger automatic rolling-origin conformal recalibration.
