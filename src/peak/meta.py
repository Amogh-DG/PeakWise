from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from src.common import constants
from src.common.config import load_config
from src.common.paths import artifacts_dir, processed_dir


def generate_meta() -> dict:
    cfg = load_config()
    art_dir = artifacts_dir()
    proc_dir = processed_dir()

    load_path = proc_dir / "load_hourly.parquet"
    if load_path.exists():
        df_load = pd.read_parquet(load_path, columns=["ts"])
        data_start = df_load["ts"].min().isoformat()
        data_end = df_load["ts"].max().isoformat()
    else:
        data_start = "2023-01-01T00:00:00+05:30"
        data_end = "2026-10-31T23:00:00+05:30"

    backtest_path = art_dir / "predictions_backtest.parquet"
    if backtest_path.exists():
        df_bt = pd.read_parquet(backtest_path, columns=["target_ts", "model"])
        target_dates = df_bt["target_ts"].dt.date
        bt_start = str(target_dates.min())
        bt_end = str(target_dates.max())
        present_models = sorted(list(df_bt["model"].unique()))
    else:
        bt_start = "2024-01-01"
        bt_end = "2024-12-31"
        present_models = list(constants.MODELS)

    peak_path = art_dir / "peak_predictions.parquet"
    if peak_path.exists():
        df_peak = pd.read_parquet(peak_path)
        if "threshold_mw" in df_peak.columns:
            latest_threshold = float(df_peak["threshold_mw"].iloc[-1])
        elif "pred_peak_mw_p90" in df_peak.columns:
            latest_threshold = float(df_peak["pred_peak_mw_p90"].quantile(0.9))
        else:
            latest_threshold = 7650.0
    else:
        latest_threshold = 7650.0

    models_list = [m for m in constants.MODELS if m in present_models]
    if not models_list:
        models_list = list(constants.MODELS)

    season_definition = {
        "winter": [12, 1, 2],
        "summer": [3, 4, 5, 6],
        "monsoon": [7, 8, 9],
        "post_monsoon": [10, 11],
    }

    meta = {
        "version": "1.0.0",
        "timezone": constants.TZ,
        "origin_hour_local": int(cfg.get("origin_hour_local", 10)),
        "data_range": {
            "start": data_start,
            "end": data_end,
        },
        "backtest_range": {
            "start": bt_start,
            "end": bt_end,
        },
        "quantiles": list(constants.QUANTILES),
        "peak_threshold_mw_latest": round(latest_threshold, 1),
        "peak_definition": "Daily peak above the 90th percentile of daily peaks in the fold's training window",
        "season_definition": season_definition,
        "peak_hours": list(constants.PEAK_HOURS),
        "models": list(constants.MODELS),
        "weather_proxy_note": "Backtests use observed weather plus horizon-scaled noise as a stand-in for archived weather forecasts.",
    }

    out_file = art_dir / "meta.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


def main() -> None:
    meta = generate_meta()
    print(f"Wrote meta.json to {artifacts_dir() / 'meta.json'}")


if __name__ == "__main__":
    main()
