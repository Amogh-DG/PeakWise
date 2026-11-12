# Assumptions — Person A

<<<<<<< Updated upstream
## A-8 baselines

### Seasonal naive step-back rule
For a forecast made at origin $O$ (10:00 IST on day $D_0$), target timestamps range from $D+1$ 00:00 to $D+7$ 23:00.
To predict target timestamp $T$, the seasonal naive model looks for the actual load at the identical hour-of-week 7 days earlier ($T - 7\text{ days}$).
If $T - 7\text{ days} < O$, that value is used directly.
If $T - 7\text{ days} \ge O$ (which occurs for targets beyond 7 days from the origin, such as day $D+7$ afternoon/evening), the model continues stepping back by additional 7-day multiples ($T - 14\text{ days}$, etc.) until the timestamp is strictly before the forecast origin ($< O$).
This guarantees that no future or unobserved information is used.
Residual quantiles are computed per hour-of-day strictly on the training window ($ts < \text{train\_end}$) to derive prediction intervals ($P_{05}, P_{10}, P_{50}, P_{90}, P_{95}$).
## 1. Weather Forecast Proxy in Backtesting

In production, day-ahead and week-ahead electricity demand forecasting models ingest numerical weather prediction (NWP) forecasts produced prior to the 10:00 IST origin (e.g. IMD, ECMWF, or GFS model cycles). For historical backtesting across multiple years (2023–2026), point-in-time archived NWP model runs for Delhi are neither publicly accessible in free historical archives nor economically viable to retain at hourly resolution.

### Methodology
To prevent artificially optimistic forecasts from "perfect weather foresight" while maintaining physically realistic atmospheric conditions, historical backtesting applies a horizon-scaled Gaussian noise perturbation to observed historical weather:

$$\sigma(h) = \text{base\_sd\_c} + \text{sd\_growth\_per\_day\_c} \times h$$

where:
- $h \in \{1, \dots, 7\}$ denotes the forecast horizon day (`horizon_day`).
- $\text{base\_sd\_c} = 0.5^\circ\text{C}$ represents the baseline observation / near-term NWP uncertainty on Day 1.
- $\text{sd\_growth\_per\_day\_c} = 0.4^\circ\text{C}$ per day models the progressive dispersion and error growth of NWP forecast ensembles over multi-day horizons.
- The resulting standard deviation $\sigma(h)$ scales linearly:
  - Day 1 ($h=1$): $\sigma = 0.9^\circ\text{C}$
  - Day 2 ($h=2$): $\sigma = 1.3^\circ\text{C}$
  - Day 3 ($h=3$): $\sigma = 1.7^\circ\text{C}$
  - Day 4 ($h=4$): $\sigma = 2.1^\circ\text{C}$
  - Day 5 ($h=5$): $\sigma = 2.5^\circ\text{C}$
  - Day 6 ($h=6$): $\sigma = 2.9^\circ\text{C}$
  - Day 7 ($h=7$): $\sigma = 3.3^\circ\text{C}$

### Atmospheric and Physical Consistency
1. **Dependent Variable Recomputation**: When noise is injected into temperature (`wx_temp_c`), all thermodynamic and temporal dependents (`wx_heat_index_c` via Rothfusz regression, `wx_cdh`, `wx_cdh_24`, rolling means, and temperature lags) are recomputed from the perturbed temperature series.
2. **Ground Truth Preservation**: The unperturbed observed weather series is strictly preserved for evaluation and actual demand comparisons; noisy weather is supplied exclusively to model feature matrices at inference time.
3. **Reproducibility**: Noise injection is completely deterministic for any given `(seed, origin_ts)` pair using a stable hash derivation.

## 2. Autoregressive Temporal Isolation & Leakage Prevention

1. **Origin Cutoff**: All autoregressive lag calculations, rolling statistics, and peak metrics generated at origin $O$ (10:00 IST on Day $D_0$) strictly filter input records to $\{t \mid t < O\}$. For standard 10:00 IST daily origins, the last observed hourly demand datum is 09:00 IST on $D_0$.
2. **Same-Hour Last Week Rule**: For any forecast target timestamp $T$, the lookup begins at $T - 7\text{ days}$. If $T - 7\text{ days} \ge O$, the lookup recursively steps back in 7-day increments ($T - 14\text{ days}$, etc.) until reaching a timestamp strictly prior to $O$.
3. **Same-Hour Last Known Day Rule**: For target hour $h$, if $D_0\ h:00 < O$ (hours 00:00 through 09:00), the observation from $D_0$ is used; if $D_0\ h:00 \ge O$ (hours 10:00 through 23:00), the observation from $D_0 - 1\text{ day}$ is used.
=======
## A-8 Seasonal Naive Step-back Rule
For seasonal naive predictions issued at origin $T_0$ (10:00 IST), target hours for horizon days D+1 through D+7 are predicted using historical actual loads. For each target hour $t$, we inspect $t - 7\text{ days}$. If $t - 7\text{ days} < T_0$, that historical load is already known and used directly. For farther horizons (D+2 to D+7), $t - 7\text{ days}$ falls at or after $T_0$, so the rule steps back by additional 7-day multiples ($t - 14\text{ days}$, $t - 21\text{ days}$, etc.) until reaching a strictly past timestamp before $T_0$, preventing future data leakage. Residual quantiles computed strictly from the training window by hour-of-day are added to produce quantile intervals.

## A-11 Conformal Quantile Calibration (CQR)
Interval calibration applies Conformalized Quantile Regression (CQR) per (horizon_day, peak/off-peak) group using rolling calibration windows of 90 days ending strictly before each fold's first test origin. The empirical conformity score quantile determines the symmetric interval expansion or contraction required to achieve nominal coverages (80% and 90%). The median forecast ($p50$) remains unchanged, and monotonic quantile ordering ($p05 \le p10 \le p50 \le p90 \le p95$) is enforced through clipping relative to the median.

## A-12 Daily Peak Summary
The daily forecast summary (`artifacts/daily_peak_summary.parquet`) aggregates the hourly forecast trajectories to daily level for each (model, origin_ts, date):
- `daily_max_p10`, `daily_max_p50`, `daily_max_p90`: computed as the maximum across the day's 24 hourly forecast values for each respective quantile trajectory. Note that `daily_max_p10` represents the maximum of the hourly P10 trajectory across the 24 hours, rather than the 10th percentile of the daily peak distribution.
- `argmax_hour_p50`: the hour-of-day (0–23) at which the hourly P50 load reaches its maximum.
- `daily_min_p50`: the minimum hourly P50 forecast across the day.
- `y_true_daily_max`: the actual observed maximum hourly load for that calendar date, set to null if unobserved.

>>>>>>> Stashed changes
