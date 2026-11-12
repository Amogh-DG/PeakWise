from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
from src.common import constants, paths


def get_predictions_path() -> Path:
    p = paths.artifacts_dir() / "predictions_backtest.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "artifacts_mock" / "predictions_backtest.parquet"
        if mock_p.exists():
            return mock_p
    return p


def build_daily_peak_summary(pred_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if pred_df is None:
        p = get_predictions_path()
        if not p.exists():
            raise FileNotFoundError(f"Missing predictions file at {p}")
        df = pd.read_parquet(p)
    else:
        df = pred_df.copy()

    required_cols = [
        "model",
        "origin_ts",
        "target_ts",
        "horizon_day",
        "p10",
        "p50",
        "p90",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column {col} in predictions")

    df["target_ts"] = pd.to_datetime(df["target_ts"])
    df["date"] = df["target_ts"].dt.date
    df["target_hour"] = df["target_ts"].dt.hour

    if "y_true" not in df.columns:
        df["y_true"] = np.nan

    rows = []
    grouped = df.groupby(["model", "origin_ts", "date"], sort=False)

    for (model, origin_ts, target_date), group in grouped:
        h_day = int(group["horizon_day"].iloc[0])
        max_p10 = float(group["p10"].max())
        max_p50 = float(group["p50"].max())
        max_p90 = float(group["p90"].max())
        min_p50 = float(group["p50"].min())

        argmax_idx = group["p50"].idxmax()
        argmax_hour = int(group.loc[argmax_idx, "target_hour"])

        valid_y = group["y_true"].dropna()
        y_max = float(valid_y.max()) if len(valid_y) > 0 else None

        rows.append(
            {
                "model": str(model),
                "origin_ts": origin_ts,
                "date": target_date,
                "horizon_day": h_day,
                "daily_max_p10": round(max_p10, 1),
                "daily_max_p50": round(max_p50, 1),
                "daily_max_p90": round(max_p90, 1),
                "argmax_hour_p50": argmax_hour,
                "daily_min_p50": round(min_p50, 1),
                "y_true_daily_max": round(y_max, 1) if y_max is not None else None,
            }
        )

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
    result_df = pd.DataFrame(rows, columns=cols)
    if not result_df.empty:
        result_df["model"] = result_df["model"].astype(str)
        result_df["horizon_day"] = result_df["horizon_day"].astype(np.int32)
        result_df["argmax_hour_p50"] = result_df["argmax_hour_p50"].astype(np.int32)

    return result_df


def save_daily_peak_summary(summary_df: pd.DataFrame) -> Path:
    out_dir = paths.artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "daily_peak_summary.parquet"
    summary_df.to_parquet(out_path, index=False, compression="snappy")

    mock_dir = paths.repo_root() / "artifacts_mock"
    if mock_dir.exists() and out_dir != mock_dir:
        mock_path = mock_dir / "daily_peak_summary.parquet"
        if not mock_path.exists():
            summary_df.to_parquet(mock_path, index=False, compression="snappy")

    return out_path


def export_daily_peak_summary() -> pd.DataFrame:
    summary_df = build_daily_peak_summary()
    save_daily_peak_summary(summary_df)
    return summary_df


def main():
    summary_df = export_daily_peak_summary()

    lgbm_df = summary_df[summary_df["model"] == "lgbm"]
    if not lgbm_df.empty:
        print("First 5 rows for model 'lgbm':")
        print(lgbm_df.head(5).to_string(index=False))
    elif not summary_df.empty:
        first_model = summary_df["model"].iloc[0]
        print(f"First 5 rows for model '{first_model}':")
        print(summary_df.head(5).to_string(index=False))

    out_path = paths.artifacts_dir() / "daily_peak_summary.parquet"
    print(f"Wrote daily peak summary to {out_path} ({len(summary_df)} rows)")


if __name__ == "__main__":
    main()
