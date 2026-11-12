# Assumptions — Person A

<<<<<<< Updated upstream
## A-6 Weather Noise and Autoregressive Isolation

### Weather Forecast Proxy in Backtesting
In production, day-ahead and week-ahead electricity demand forecasting models ingest numerical weather prediction (NWP) forecasts produced prior to the 10:00 IST origin (e.g. IMD, ECMWF, or GFS model cycles). For historical backtesting across multiple years (2023–2026), point-in-time archived NWP model runs for Delhi are neither publicly accessible in free historical archives nor economically viable to retain at hourly resolution.

To prevent artificially optimistic forecasts from "perfect weather foresight" while maintaining physically realistic atmospheric conditions, historical backtesting applies a horizon-scaled Gaussian noise perturbation to observed historical weather:

$$\sigma(h) = \text{base\_sd\_c} + \text{sd\_growth\_per\_day\_c} \times h$$

where $h \in \{1, \dots, 7\}$ denotes the forecast horizon day (`horizon_day`). When noise is injected into temperature (`wx_temp_c`), all thermodynamic and temporal dependents (`wx_heat_index_c` via Rothfusz regression, `wx_cdh`, `wx_cdh_24`, rolling means, and temperature lags) are recomputed from the perturbed temperature series. The unperturbed observed weather series is strictly preserved for evaluation and actual demand comparisons.

### Autoregressive Temporal Isolation & Leakage Prevention
1. **Origin Cutoff**: All autoregressive lag calculations, rolling statistics, and peak metrics generated at origin $O$ (10:00 IST on Day $D_0$) strictly filter input records to $\{t \mid t < O\}$. For standard 10:00 IST daily origins, the last observed hourly demand datum is 09:00 IST on $D_0$.
2. **Same-Hour Last Week Rule**: For any forecast target timestamp $T$, the lookup begins at $T - 7\text{ days}$. If $T - 7\text{ days} \ge O$, the lookup recursively steps back in 7-day increments ($T - 14\text{ days}$, etc.) until reaching a timestamp strictly prior to $O$.
3. **Same-Hour Last Known Day Rule**: For target hour $h$, if $D_0\ h:00 < O$ (hours 00:00 through 09:00), the observation from $D_0$ is used; if $D_0\ h:00 \ge O$ (hours 10:00 through 23:00), the observation from $D_0 - 1\text{ day}$ is used.

=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
