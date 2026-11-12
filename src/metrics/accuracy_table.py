import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pandas as pd
from src.common import constants, paths
from src.metrics.metrics import (
    bias,
    improvement_pct,
    mae,
    mape,
    mean_pinball,
    mpiw_80,
    picp_80,
    picp_90,
    rmse,
)
from src.metrics.segments import SEGMENTS, get_segment_mask


def build_accuracy_table(pred_df: pd.DataFrame, exclude_outage: bool = False) -> dict:
    df = pred_df.copy()
    if exclude_outage and "is_outage_suspect" in df.columns:
        df = df[~df["is_outage_suspect"]].copy()

    df = df.dropna(subset=["y_true"]).copy()
    if df.empty:
        return {"generated_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(), "rows": []}

    models = sorted(df["model"].unique().tolist())
    horizons: list[int | str] = [1, 2, 3, 4, 5, 6, 7, "all"]

    metric_lookup: dict[tuple[str, int | str, str], dict] = {}

    for m in models:
        m_df = df[df["model"] == m]
        for h in horizons:
            h_df = m_df if h == "all" else m_df[m_df["horizon_day"] == h]
            for seg in SEGMENTS:
                mask = get_segment_mask(h_df, seg)
                sub_df = h_df[mask]

                n = len(sub_df)
                if n == 0:
                    continue

                y_true = sub_df["y_true"].to_numpy()
                p50 = sub_df["p50"].to_numpy()
                p10 = sub_df["p10"].to_numpy()
                p90 = sub_df["p90"].to_numpy()
                p05 = sub_df["p05"].to_numpy()
                p95 = sub_df["p95"].to_numpy()

                q_preds = [
                    (0.05, p05),
                    (0.10, p10),
                    (0.50, p50),
                    (0.90, p90),
                    (0.95, p95),
                ]

                metric_lookup[(m, h, seg)] = {
                    "n": int(n),
                    "mape": round(mape(y_true, p50), 2),
                    "rmse_mw": round(rmse(y_true, p50), 1),
                    "mae_mw": round(mae(y_true, p50), 1),
                    "bias_mw": round(bias(y_true, p50), 1),
                    "pinball": round(mean_pinball(y_true, q_preds), 1),
                    "picp_80": round(picp_80(y_true, p10, p90), 2),
                    "picp_90": round(picp_90(y_true, p05, p95), 2),
                    "mpiw_80_mw": round(mpiw_80(p10, p90), 1),
                }

    rows = []
    baseline_model = constants.BASELINE_MODEL

    for m in models:
        for h in horizons:
            for seg in SEGMENTS:
                key = (m, h, seg)
                if key not in metric_lookup:
                    continue
                vals = metric_lookup[key]

                row = {
                    "model": m,
                    "horizon_day": h,
                    "segment": seg,
                    "n": vals["n"],
                    "mape": vals["mape"],
                    "rmse_mw": vals["rmse_mw"],
                    "mae_mw": vals["mae_mw"],
                    "bias_mw": vals["bias_mw"],
                    "pinball": vals["pinball"],
                    "picp_80": vals["picp_80"],
                    "picp_90": vals["picp_90"],
                    "mpiw_80_mw": vals["mpiw_80_mw"],
                }

                if m == baseline_model:
                    row["improvement_mape_pct"] = None
                    row["improvement_rmse_pct"] = None
                else:
                    base_key = (baseline_model, h, seg)
                    if base_key in metric_lookup:
                        base_vals = metric_lookup[base_key]
                        imp_mape = improvement_pct(base_vals["mape"], vals["mape"])
                        imp_rmse = improvement_pct(base_vals["rmse_mw"], vals["rmse_mw"])
                        row["improvement_mape_pct"] = round(imp_mape, 1) if imp_mape is not None else None
                        row["improvement_rmse_pct"] = round(imp_rmse, 1) if imp_rmse is not None else None
                    else:
                        row["improvement_mape_pct"] = None
                        row["improvement_rmse_pct"] = None

                rows.append(row)

    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
    calib_comparison = []
    has_raw = all(c in df.columns for c in ["p05_raw", "p10_raw", "p90_raw", "p95_raw"])
    if has_raw:
        for m in models:
            m_df = df[df["model"] == m]
            is_calibrated = (
                not (m_df["p10"] == m_df["p10_raw"]).all()
                or not (m_df["p90"] == m_df["p90_raw"]).all()
                or not (m_df["p05"] == m_df["p05_raw"]).all()
                or not (m_df["p95"] == m_df["p95_raw"]).all()
            )
            if not is_calibrated:
                continue

            for h in horizons:
                h_df = m_df if h == "all" else m_df[m_df["horizon_day"] == h]
                if h_df.empty:
                    continue
                y = h_df["y_true"].to_numpy()
                p10_raw = h_df["p10_raw"].to_numpy()
                p90_raw = h_df["p90_raw"].to_numpy()
                p05_raw = h_df["p05_raw"].to_numpy()
                p95_raw = h_df["p95_raw"].to_numpy()

                p10_cal = h_df["p10"].to_numpy()
                p90_cal = h_df["p90"].to_numpy()
                p05_cal = h_df["p05"].to_numpy()
                p95_cal = h_df["p95"].to_numpy()

                calib_comparison.append({
                    "model": m,
                    "horizon_day": h,
                    "picp_80_before": round(picp_80(y, p10_raw, p90_raw), 2),
                    "picp_80_after": round(picp_80(y, p10_cal, p90_cal), 2),
                    "picp_90_before": round(picp_90(y, p05_raw, p95_raw), 2),
                    "picp_90_after": round(picp_90(y, p05_cal, p95_cal), 2),
                    "mpiw_80_before": round(mpiw_80(p10_raw, p90_raw), 1),
                    "mpiw_80_after": round(mpiw_80(p10_cal, p90_cal), 1),
                })

    return {
        "generated_at": ist_now,
        "rows": rows,
        "calibration_comparison": calib_comparison,
    }


def print_compact_table(table_data: dict) -> None:
    rows = table_data.get("rows", [])
    if not rows:
        return

    filter_rows = [
        r for r in rows if r["segment"] in ("all", "peak_hours")
    ]
    if not filter_rows:
        return

    df_view = pd.DataFrame(filter_rows)
    display_cols = [
        "model",
        "horizon_day",
        "segment",
        "mape",
        "rmse_mw",
        "bias_mw",
        "picp_80",
        "improvement_mape_pct",
        "improvement_rmse_pct",
    ]
    sub_view = df_view[display_cols].sort_values(by=["segment", "model", "horizon_day"], key=lambda col: col.astype(str))
    print(sub_view.to_string(index=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude-outage", action="store_true", default=False)
    args = parser.parse_args()

    pred_path = paths.artifacts_dir() / "predictions_backtest.parquet"
    if not pred_path.exists():
        mock_pred_path = paths.repo_root() / "artifacts_mock" / "predictions_backtest.parquet"
        if mock_pred_path.exists():
            pred_path = mock_pred_path
        else:
            raise FileNotFoundError(f"predictions_backtest.parquet not found in {paths.artifacts_dir()}")

    pred_df = pd.read_parquet(pred_path)
    table_data = build_accuracy_table(pred_df, exclude_outage=args.exclude_outage)

    out_file = paths.artifacts_dir() / "metrics_accuracy.json"
    paths.artifacts_dir().mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(table_data, f, indent=2)

    print_compact_table(table_data)


if __name__ == "__main__":
    main()
