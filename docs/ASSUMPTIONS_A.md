# Assumptions — Person A

## A-8 baselines

### Seasonal naive step-back rule
For a forecast made at origin $O$ (10:00 IST on day $D_0$), target timestamps range from $D+1$ 00:00 to $D+7$ 23:00.
To predict target timestamp $T$, the seasonal naive model looks for the actual load at the identical hour-of-week 7 days earlier ($T - 7\text{ days}$).
If $T - 7\text{ days} < O$, that value is used directly.
If $T - 7\text{ days} \ge O$ (which occurs for targets beyond 7 days from the origin, such as day $D+7$ afternoon/evening), the model continues stepping back by additional 7-day multiples ($T - 14\text{ days}$, etc.) until the timestamp is strictly before the forecast origin ($< O$).
This guarantees that no future or unobserved information is used.
Residual quantiles are computed per hour-of-day strictly on the training window ($ts < \text{train\_end}$) to derive prediction intervals ($P_{05}, P_{10}, P_{50}, P_{90}, P_{95}$).
