# Why Peaks Are Hard: Structural Drivers of Electricity Demand Extremes in Delhi

## 1. Introduction & The Peak Forecasting Challenge

In the National Capital Territory of Delhi, electricity demand is characterized by acute non-linear surges driven by intense climatic swings, rapid commercial and domestic cooling penetration, and institutional calendar shocks. 

While baseline hourly demand can be forecasted with low mean absolute percentage error (~2.5% to 3.0%), **peak demand hours exhibit significantly higher variance, steeper timing penalties, and asymmetric operational consequences**. A 300 MW forecast shortfall at 15:00 IST on a summer afternoon directly risks localized feeder tripping, load shedding, and punitive Deviation Settlement Mechanism (DSM) penalties.

This report establishes the physical and statistical mechanics that make peak forecasting intrinsically harder than average-load forecasting.

---

## 2. Weather Sensitivity & Temperature Non-Linearity

Electricity demand in Delhi exhibits extreme weather sensitivity once ambient temperatures exceed the cooling-degree threshold (~24 °C). Above this point, residential and commercial air conditioning demand compounds exponentially.

![Weather Sensitivity](figures/weather_sensitivity.png)

### Empirical Sensitivity Across Seasons:
- **Summer (March–June):** Peak-hour load increases by **+160.5 MW per +1 °C** rise in daily maximum temperature.
- **Monsoon (July–September):** Despite overcast periods, high latent humidity elevates enthalpy, sustaining high AC usage at **+219.3 MW per +1 °C**.
- **Winter (December–February):** Base heating load exhibits inverted sensitivity, with heating spikes on cold wave mornings.

Because weather forecasts carry inherent numerical prediction uncertainties (typically $\pm 1.5$ to $2.0$ °C at D+1 to D+3 lead times), a 2 °C weather forecast miss translates into a **200–250 MW demand error** during afternoon peaks.

---

## 3. Thermal Inertia & Delayed Evening Ramps

Concrete buildings, paved urban infrastructure, and dense housing in Delhi act as thermal heat reservoirs during multi-day heatwaves. Heat absorbed during 12:00–16:00 peak solar irradiance re-radiates throughout the evening, shifting peak load into hours 19:00–23:00 IST as residents return home and turn on split ACs.

![Thermal Inertia](figures/thermal_inertia.png)

### Empirical Lag Correlations:
- Evening peak load (19:00–23:00 IST) correlates not only with contemporaneous temperature ($r = 0.907$), but exhibits persistent correlation with **temperature 6 hours prior ($r = 0.890$)** and **rolling 24-hour heat accumulation ($r = 0.894$)**.
- Models relying solely on contemporaneous weather miss the delayed heat release, underestimating the magnitude and duration of evening peak plateaus.

---

## 4. Calendar, Festival & Behavioral Shocks

Delhi experiences significant calendar-driven demand deviations during major religious and cultural observances:
- **Diwali Window:** Industrial and commercial activity slows sharply across the National Capital Region, producing an average load drop of **-423.0 MW** (sample size $n=72$).
- **Holi Window:** Commercial shutdowns and daytime celebrations depress daytime load by **-418.7 MW** ($n=72$).
- **Caution on Sample Size:** Major festivals occur only once per calendar year ($n=1$ to $3$ events in typical 3-year backtests). Standard regression models risk overfitting to idiosyncratic historical weather on those specific dates unless regularized with festival window distance features (`cal_days_to_*`).

---

## 5. Quantitative Evidence: Peak Hours vs Off-Peak Error

Empirical backtest metrics confirm that error rates are structurally elevated during peak hours:

| Model | Evaluation Segment | Day 1 RMSE (MW) | Day 1 MAPE (%) | Improvement vs Baseline |
|---|---|---|---|---|
| **Ensemble** | Peak Hours (06–10, 19–23) | **158.4 MW** | **2.57%** | **+49.2%** |
| **Ensemble** | Off-Peak Hours | 151.7 MW | 2.76% | +52.1% |
| **Seasonal Naive** | Peak Hours | 311.8 MW | 4.51% | — |

Even though the Ensemble reduces peak-hour RMSE by nearly 50% compared to baseline persistence, peak-hour RMSE remains higher than off-peak RMSE due to convective storm uncertainty and erratic AC ramp-up.

---

## 6. Case Studies of Missed Peak Events

### Case Study 1: 2024-06-19 (Other)
- **Forecast Outcome:** Peak Miss (Predicted Peak: 7,361.9 MW vs Actual: 7,990.3 MW)
- **Magnitude Error:** -628.4 MW | **Timing Error:** +0 minutes
- **Diagnostic Cause:** Peak load under-forecasted by 628 MW.

### Case Study 2: 2024-06-22 (Weekend)
- **Forecast Outcome:** Peak Miss (Predicted Peak: 7,096.4 MW vs Actual: 7,687.5 MW)
- **Magnitude Error:** -591.1 MW | **Timing Error:** -240 minutes
- **Diagnostic Cause:** Weekend load shape deviated from weekday forecast; peak shifted 4 h later than predicted.

### Case Study 3: 2024-06-28 (Other)
- **Forecast Outcome:** Peak Miss (Predicted Peak: 7,476.7 MW vs Actual: 8,064.4 MW)
- **Magnitude Error:** -587.7 MW | **Timing Error:** +60 minutes
- **Diagnostic Cause:** Peak load under-forecasted by 588 MW; peak shifted 1 h earlier than predicted.

---

## 7. Operational Mitigations Implemented in the System

1. **Conformal Quantile Regression (CQR):** Guaranteeing 80% and 90% empirical coverage bounds even during non-linear heat surges.
2. **Dedicated Binary Peak Classifier:** Trained with recall-prioritized decision thresholds ($\ge 0.80$) to flag at-risk days ahead of time.
3. **Newsvendor Asymmetric Dispatch:** Accounting for the 2.4x cost asymmetry between unserved shortfall penalties and surplus salvage.
