import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm
from src.backtest.folds import make_folds
from src.backtest.registry import REGISTRY, get_forecaster
import src.backtest.persistence
import src.models
from src.common import config, paths
from src.models.calibration import calibrate, generate_calibration_predictions


def get_load_path() -> Path:
    p = paths.processed_dir() / "load_hourly.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
        if mock_p.exists():
            return mock_p
    return p


def get_features_path() -> Path:
    p = paths.processed_dir() / "features_known.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "data" / "processed_mock" / "features_known.parquet"
        if mock_p.exists():
            return mock_p
    return p


def run_backtest(models: list[str] | None = None, keep_persistence: bool = False) -> pd.DataFrame:
    cfg = config.load_config()
    target_models = models or list(REGISTRY.keys())

    load_path = get_load_path()
    if not load_path.exists():
        raise FileNotFoundError(f"Missing load data at {load_path}")

    load_df = pd.read_parquet(load_path)
    load_index = pd.DatetimeIndex(load_df["ts"])
    load_map = dict(zip(load_df["ts"], load_df["load_mw"]))
    outage_map = dict(zip(load_df["ts"], load_df["is_outage_suspect"]))

    folds = make_folds(load_index, cfg)
    artifact_file = paths.artifacts_dir() / "predictions_backtest.parquet"

    existing_df = None
    existing_pairs = set()
    if artifact_file.exists():
        existing_df = pd.read_parquet(artifact_file)
        if not existing_df.empty and "model" in existing_df.columns and "fold_id" in existing_df.columns:
            existing_pairs = set(zip(existing_df["model"].astype(str), existing_df["fold_id"].astype(int)))

    new_dfs = []

    for model_name in target_models:
        forecaster_cls = REGISTRY[model_name]
        forecaster = get_forecaster(model_name, cfg)
        should_calibrate = getattr(forecaster_cls, "calibrate", False) or getattr(forecaster, "calibrate", False)

        for fold in tqdm(folds, desc=f"Backtest {model_name}"):
            if (model_name, fold.fold_id) in existing_pairs:
                continue

            calib_df = pd.DataFrame()
            if should_calibrate:
                calib_df = generate_calibration_predictions(
                    forecaster_cls, cfg, fold.origins[0], load_df
                )

            forecaster.fit(fold.train_end)
            fold_preds = []
            for origin in fold.origins:
                preds = forecaster.predict(origin).copy()
                targets = preds["target_ts"]

                preds["model"] = str(model_name)
                preds["fold_id"] = np.int32(fold.fold_id)
                preds["origin_ts"] = origin
                preds["horizon_h"] = preds["horizon_h"].astype(np.int32)
                preds["horizon_day"] = preds["horizon_day"].astype(np.int32)
                preds["y_true"] = [load_map.get(t, None) for t in targets]
                preds["p05_raw"] = preds["p05"].astype(float)
                preds["p10_raw"] = preds["p10"].astype(float)
                preds["p50_raw"] = preds["p50"].astype(float)
                preds["p90_raw"] = preds["p90"].astype(float)
                preds["p95_raw"] = preds["p95"].astype(float)
                preds["is_outage_suspect"] = [bool(outage_map.get(t, False)) for t in targets]

                fold_preds.append(preds)

            if fold_preds:
                concat_fold = pd.concat(fold_preds, ignore_index=True)
                if should_calibrate and not calib_df.empty:
                    concat_fold = calibrate(concat_fold, calib_df, cfg)
                new_dfs.append(concat_fold)

    cols = [
        "model",
        "fold_id",
        "origin_ts",
        "target_ts",
        "horizon_h",
        "horizon_day",
        "y_true",
        "p05",
        "p10",
        "p50",
        "p90",
        "p95",
        "p05_raw",
        "p10_raw",
        "p50_raw",
        "p90_raw",
        "p95_raw",
        "is_outage_suspect",
    ]

    if new_dfs:
        concatenated_new = pd.concat(new_dfs, ignore_index=True)[cols]
        if existing_df is not None and not existing_df.empty:
            final_df = pd.concat([existing_df, concatenated_new], ignore_index=True)
        else:
            final_df = concatenated_new
    else:
        final_df = existing_df if existing_df is not None else pd.DataFrame(columns=cols)

    if not keep_persistence and not final_df.empty:
        final_df = final_df[final_df["model"] != "persistence"].reset_index(drop=True)

    if not final_df.empty:
        final_df["model"] = final_df["model"].astype(str)
        final_df["fold_id"] = final_df["fold_id"].astype(np.int32)
        final_df["horizon_h"] = final_df["horizon_h"].astype(np.int32)
        final_df["horizon_day"] = final_df["horizon_day"].astype(np.int32)
        final_df["is_outage_suspect"] = final_df["is_outage_suspect"].astype(bool)
        paths.artifacts_dir().mkdir(parents=True, exist_ok=True)
        final_df.to_parquet(artifact_file, index=False, compression="snappy")

    return final_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=str, default=None)
    parser.add_argument("--keep-persistence", action="store_true", default=False)
    args = parser.parse_args()

    models_list = [m.strip() for m in args.models.split(",") if m.strip()] if args.models else None
    run_backtest(models=models_list, keep_persistence=args.keep_persistence)


if __name__ == "__main__":
    main()
