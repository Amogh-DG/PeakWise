# Assumptions — Person A

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
