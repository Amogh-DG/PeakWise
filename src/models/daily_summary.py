from pathlib import Path
import numpy as np
import pandas as pd
from src.common import paths


def get_predictions_path() -> Path:
    p = paths.artifacts_dir() / "predictions_backtest.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "artifacts_mock" / "predictions_backtest.parquet"
        if mock_p.exists():
            return mock_p
    return p


def build_daily_peak_summary(preds_df: pd.DataFrame) -> pd.DataFrame:
    df = preds_df.copy()
    df["date"] = df["target_ts"].dt.date
    df["hour"] = df["target_ts"].dt.hour

    df_sorted = df.sort_values(["p50", "hour"], ascending=[False, True])
    argmax_df = df_sorted.drop_duplicates(subset=["model", "origin_ts", "date"])[
        ["model", "origin_ts", "date", "hour"]
    ].rename(columns={"hour": "argmax_hour_p50"})

    agg_df = df.groupby(["model", "origin_ts", "date"], as_index=False).agg(
        horizon_day=("horizon_day", "first"),
        daily_max_p10=("p10", "max"),
        daily_max_p50=("p50", "max"),
        daily_max_p90=("p90", "max"),
        daily_min_p50=("p50", "min"),
        y_true_daily_max=("y_true", lambda s: s.max() if s.notna().any() else np.nan),
    )

    merged = pd.merge(agg_df, argmax_df, on=["model", "origin_ts", "date"])
    cols = [
        "model",
        "origin_ts",
        "date",
        "horizon_day",
        "daily_max_p10",
        "daily_max_p50",
        "daily_max_p90",
        "argmax_hour_p50",
        "daily_min_p50",
        "y_true_daily_max",
    ]
    merged = merged[cols].sort_values(["model", "origin_ts", "date"]).reset_index(drop=True)
    merged["model"] = merged["model"].astype(str)
    merged["horizon_day"] = merged["horizon_day"].astype(np.int32)
    merged["argmax_hour_p50"] = merged["argmax_hour_p50"].astype(np.int32)
    return merged


def export_daily_peak_summary() -> pd.DataFrame:
    preds_path = get_predictions_path()
    if not preds_path.exists():
        raise FileNotFoundError(f"Missing predictions at {preds_path}")

    preds_df = pd.read_parquet(preds_path)
    summary_df = build_daily_peak_summary(preds_df)

    out_path = paths.artifacts_dir() / "daily_peak_summary.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_parquet(out_path, index=False, compression="snappy")
    return summary_df


def main():
    df = export_daily_peak_summary()
    lgbm_df = df[df["model"] == "lgbm"]
    if not lgbm_df.empty:
        print(lgbm_df.head(5).to_string())
    else:
        print(df.head(5).to_string())


if __name__ == "__main__":
    main()
