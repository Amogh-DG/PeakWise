import json
import math

import numpy as np
import pandas as pd

from src.common.constants import HORIZON_DAYS
from src.common.paths import artifacts_dir
from src.common.seasons import SEASONS, season_of
from src.metrics.metrics import bias, mape, rmse

_METRICS = ["mape", "rmse", "bias"]
_MIN_OBS = 5


def _metric_value(metric: str, y_true: np.ndarray, y_pred: np.ndarray) -> float | None:
    if len(y_true) < _MIN_OBS:
        return None
    if metric == "mape":
        return round(mape(y_true, y_pred), 4)
    if metric == "rmse":
        return round(rmse(y_true, y_pred), 4)
    if metric == "bias":
        return round(bias(y_true, y_pred), 4)
    raise ValueError(f"Unknown metric: {metric}")


def _build_cell(
    df: pd.DataFrame,
    model: str,
    metric: str,
    horizon_day: int | str,
) -> dict:
    if horizon_day == "all":
        sub = df[df["model"] == model].copy()
    else:
        sub = df[(df["model"] == model) & (df["horizon_day"] == horizon_day)].copy()

    sub = sub.dropna(subset=["y_true"])

    values = []
    counts = []
    for season in SEASONS:
        season_values = []
        season_counts = []
        for hour in range(24):
            mask = (sub["_season"] == season) & (sub["_hour"] == hour)
            grp = sub[mask]
            n = len(grp)
            season_counts.append(n)
            if n < _MIN_OBS:
                season_values.append(None)
            else:
                v = _metric_value(metric, grp["y_true"].to_numpy(), grp["p50"].to_numpy())
                season_values.append(v)
        values.append(season_values)
        counts.append(season_counts)

    return {
        "model": model,
        "metric": metric,
        "horizon_day": horizon_day,
        "hours": list(range(24)),
        "seasons": SEASONS,
        "values": values,
        "counts": counts,
    }


def build_heatmap(pred_df: pd.DataFrame) -> list[dict]:
    pred_df = pred_df.copy()
    pred_df["_hour"] = pred_df["target_ts"].dt.hour
    pred_df["_season"] = pred_df["target_ts"].dt.month.map(season_of)

    models = pred_df["model"].unique().tolist()
    horizon_days_to_use: list[int | str] = [1, "all"]

    cells = []
    for model in models:
        for metric in _METRICS:
            for hd in horizon_days_to_use:
                cells.append(_build_cell(pred_df, model, metric, hd))
    return cells


def main() -> None:
    pred_path = artifacts_dir() / "predictions_backtest.parquet"
    pred_df = pd.read_parquet(pred_path)

    cells = build_heatmap(pred_df)
    out = {"cells": cells}

    out_path = artifacts_dir() / "error_heatmap.json"
    with open(out_path, "w") as f:
        json.dump(out, f, allow_nan=False)

    print(f"Wrote {len(cells)} cells to {out_path}")


if __name__ == "__main__":
    main()

