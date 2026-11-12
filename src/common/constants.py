MODELS = [
    "seasonal_naive",
    "linear",
    "lgbm",
    "xgboost",
    "prophet",
    "lstm",
    "ensemble",
]
BASELINE_MODEL = "seasonal_naive"
QUANTILES = [0.05, 0.1, 0.5, 0.9, 0.95]
QUANTILE_COLS = ["p05", "p10", "p50", "p90", "p95"]
PEAK_HOURS = [6, 7, 8, 9, 10, 19, 20, 21, 22, 23]
HORIZON_DAYS = [1, 2, 3, 4, 5, 6, 7]
TZ = "Asia/Kolkata"
