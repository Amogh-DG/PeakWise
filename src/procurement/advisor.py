from __future__ import annotations

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.common.constants import QUANTILE_COLS, QUANTILES
from src.common.paths import artifacts_dir

_QUANTILE_MAP: dict[float, str] = dict(zip(QUANTILES, QUANTILE_COLS))


def _load_predictions(model: str) -> pd.DataFrame:
    path = artifacts_dir() / "predictions_backtest.parquet"
    df = pd.read_parquet(path)
    df = df[(df["model"] == model) & (df["horizon_day"] == 1)].copy()
    df["target_ts"] = pd.to_datetime(df["target_ts"], utc=False)
    df["target_date"] = df["target_ts"].dt.date
    return df


def _load_peak_threshold() -> float:
    meta_path = artifacts_dir() / "meta.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        val = meta.get("peak_threshold_mw_latest") or meta.get("peak_threshold_mw")
        if val is not None:
            return float(val)
    pk_path = artifacts_dir() / "peak_predictions.parquet"
    if pk_path.exists():
        pk = pd.read_parquet(pk_path)
        if "threshold_mw" in pk.columns and not pk["threshold_mw"].dropna().empty:
            return float(pk["threshold_mw"].dropna().iloc[-1])
    return 7650.0


def _interpolate_quantile(q: float, row: pd.Series) -> float:
    qs = sorted(_QUANTILE_MAP.keys())
    cols = [_QUANTILE_MAP[qv] for qv in qs]
    vals = [float(row[c]) for c in cols]
    return float(np.interp(q, qs, vals))


def _hour_cost(s: float, d: float | None, da: float, under: float, resale: float) -> float | None:
    if d is None:
        return None
    u = max(d - s, 0.0)
    o = max(s - d, 0.0)
    return da * s + under * u - resale * o


def _validate_inputs(
    start_date: str,
    days: int,
    model: str,
    risk_quantile: float | str,
    tariff: dict | None,
) -> tuple[date, float, str, float, float, float, float]:
    if not (1 <= days <= 7):
        raise ValueError("days must be between 1 and 7")

    try:
        start_dt = date.fromisoformat(start_date)
    except ValueError as exc:
        raise ValueError(f"start_date is not a valid ISO date: {start_date!r}") from exc

    from src.common.config import load_config
    cfg = load_config()
    proc_cfg = cfg.get("procurement", {})
    da_default = float(proc_cfg.get("da", 5000))
    under_default = float(proc_cfg.get("under", 12000))
    resale_default = float(proc_cfg.get("resale", 2500))

    if tariff is not None:
        for key in ("da_price_inr_per_mwh", "under_price_inr_per_mwh", "resale_price_inr_per_mwh"):
            if key not in tariff:
                raise ValueError(f"tariff missing required field: {key}")
        da = float(tariff["da_price_inr_per_mwh"])
        under = float(tariff["under_price_inr_per_mwh"])
        resale = float(tariff["resale_price_inr_per_mwh"])
    else:
        da, under, resale = da_default, under_default, resale_default

    if not (under > da > resale):
        raise ValueError(
            "tariff ordering must satisfy: under_price > da_price > resale_price"
        )

    newsvendor_q = (under - da) / (under - resale)

    if isinstance(risk_quantile, str) and risk_quantile.lower() == "newsvendor":
        effective_q = newsvendor_q
        source = "newsvendor"
    else:
        try:
            effective_q = float(risk_quantile)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "risk_quantile must be a number in [0.5, 0.99] or the string 'newsvendor'"
            ) from exc
        if not (0.5 <= effective_q <= 0.99):
            raise ValueError("risk_quantile must be between 0.5 and 0.99")
        source = "user"

    return start_dt, newsvendor_q, source, effective_q, da, under, resale


def recommend(
    start_date: str,
    days: int,
    model: str = "ensemble",
    risk_quantile: float | str = 0.9,
    tariff: dict | None = None,
) -> dict:
    start_dt, newsvendor_q, source, effective_q, da, under, resale = _validate_inputs(
        start_date, days, model, risk_quantile, tariff
    )

    pred_df = _load_predictions(model)
    peak_threshold = _load_peak_threshold()

    target_dates = [start_dt + timedelta(days=i) for i in range(days)]
    end_dt = start_dt + timedelta(days=days - 1)

    prev_week_start = start_dt - timedelta(days=7)
    prev_week_end = start_dt
    prev_mask = (pred_df["target_date"] >= prev_week_start) & (pred_df["target_date"] < prev_week_end)
    prev_week_df = pred_df[prev_mask]

    if prev_week_df.empty:
        raise ValueError(
            f"No forecast data for the previous week ({prev_week_start} to {prev_week_end}). "
            "Cannot compute flat baselines."
        )

    prev_week_p50 = prev_week_df["p50"].values
    flat_mean_mw = float(np.mean(prev_week_p50))
    flat_peak_mw = float(np.max(prev_week_p50))

    schedule_rows: list[dict] = []
    by_day_rows: list[dict] = []
    at_risk_hours: list[str] = []

    total_scheduled_mwh = 0.0
    total_cost: float | None = 0.0
    total_flat_cost: float | None = 0.0
    total_flat_peak_cost: float | None = 0.0
    cost_has_null = False

    p90_cost_sum = 0.0
    p50_cost_sum = 0.0

    for target_date in target_dates:
        day_mask = pred_df["target_date"] == target_date
        day_df = pred_df[day_mask].sort_values("target_ts").reset_index(drop=True)

        if day_df.empty:
            raise ValueError(
                f"No horizon-1 forecast data found for {target_date} with model '{model}'. "
                "Date may be outside the backtest range."
            )

        day_scheduled_mwh = 0.0
        day_cost: float | None = 0.0
        day_flat_cost: float | None = 0.0
        day_peak_scheduled = 0.0

        for _, row in day_df.iterrows():
            ts_str = row["target_ts"].isoformat()
            scheduled = _interpolate_quantile(effective_q, row)
            p50_val = float(row["p50"])
            p90_val = float(row["p90"])
            actual_raw = row.get("y_true")
            actual: float | None = None if pd.isna(actual_raw) else float(actual_raw)

            flat_cost_hr = _hour_cost(flat_mean_mw, actual, da, under, resale)
            hour_cost = _hour_cost(scheduled, actual, da, under, resale)

            p90_cost_hr = _hour_cost(scheduled, p90_val, da, under, resale) or 0.0
            p50_cost_hr = _hour_cost(scheduled, p50_val, da, under, resale) or 0.0
            p90_cost_sum += p90_cost_hr
            p50_cost_sum += p50_cost_hr

            if actual is None:
                cost_has_null = True

            day_scheduled_mwh += scheduled
            if hour_cost is not None and day_cost is not None:
                day_cost += hour_cost
            else:
                day_cost = None
            if flat_cost_hr is not None and day_flat_cost is not None:
                day_flat_cost += flat_cost_hr
            else:
                day_flat_cost = None

            if p90_val >= peak_threshold:
                at_risk_hours.append(ts_str)

            day_peak_scheduled = max(day_peak_scheduled, scheduled)

            schedule_rows.append({
                "ts": ts_str,
                "scheduled_mw": round(scheduled, 2),
                "p50_mw": round(p50_val, 2),
                "p90_mw": round(p90_val, 2),
                "flat_mw": round(flat_mean_mw, 2),
                "actual_mw": actual,
            })

        total_scheduled_mwh += day_scheduled_mwh
        if day_cost is not None and total_cost is not None:
            total_cost += day_cost
        else:
            total_cost = None
        if day_flat_cost is not None and total_flat_cost is not None:
            total_flat_cost += day_flat_cost
        else:
            total_flat_cost = None

        flat_peak_day_cost: float | None = 0.0
        for _, row in day_df.iterrows():
            actual_raw = row.get("y_true")
            actual = None if pd.isna(actual_raw) else float(actual_raw)
            fp_hr = _hour_cost(flat_peak_mw, actual, da, under, resale)
            if fp_hr is not None and flat_peak_day_cost is not None:
                flat_peak_day_cost += fp_hr
            else:
                flat_peak_day_cost = None
        if flat_peak_day_cost is not None and total_flat_peak_cost is not None:
            total_flat_peak_cost += flat_peak_day_cost
        else:
            total_flat_peak_cost = None

        by_day_rows.append({
            "date": target_date.isoformat(),
            "scheduled_mwh": round(day_scheduled_mwh, 2),
            "cost_inr": round(day_cost, 2) if day_cost is not None else None,
            "flat_cost_inr": round(day_flat_cost, 2) if day_flat_cost is not None else None,
            "peak_scheduled_mw": round(day_peak_scheduled, 2),
        })

    p90_risk_exposure = p90_cost_sum - p50_cost_sum

    if cost_has_null:
        savings_inr = None
        savings_pct = None
        under_procured_hours = None
        over_procured_hours = None
        total_cost_out = None
        total_flat_cost_out = None
        total_flat_peak_cost_out = None
    else:
        total_cost_out = round(total_cost, 2) if total_cost is not None else None
        total_flat_cost_out = round(total_flat_cost, 2) if total_flat_cost is not None else None
        total_flat_peak_cost_out = round(total_flat_peak_cost, 2) if total_flat_peak_cost is not None else None
        savings_inr = round(total_flat_cost - total_cost, 2) if (total_flat_cost is not None and total_cost is not None) else None
        savings_pct = round((savings_inr / total_flat_cost) * 100.0, 4) if (savings_inr is not None and total_flat_cost and total_flat_cost > 0) else None

        under_procured_hours = sum(
            1 for r in schedule_rows
            if r["actual_mw"] is not None and r["actual_mw"] > r["scheduled_mw"]
        )
        over_procured_hours = sum(
            1 for r in schedule_rows
            if r["actual_mw"] is not None and r["actual_mw"] <= r["scheduled_mw"]
        )

    return {
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "model": model,
        "risk_quantile": round(effective_q, 6),
        "risk_quantile_source": source,
        "newsvendor_quantile": round(newsvendor_q, 6),
        "tariff_used": {
            "da_price_inr_per_mwh": da,
            "under_price_inr_per_mwh": under,
            "resale_price_inr_per_mwh": resale,
        },
        "baseline": {
            "type": "flat_prev_week_mean",
            "flat_mw": round(flat_mean_mw, 2),
            "alt_flat_prev_week_peak_mw": round(flat_peak_mw, 2),
        },
        "schedule": schedule_rows,
        "summary": {
            "total_scheduled_mwh": round(total_scheduled_mwh, 2),
            "cost_inr": total_cost_out,
            "flat_cost_inr": total_flat_cost_out,
            "flat_peak_cost_inr": total_flat_peak_cost_out,
            "savings_inr": savings_inr,
            "savings_pct": savings_pct,
            "p90_risk_exposure_inr": round(p90_risk_exposure, 2),
            "under_procured_hours": under_procured_hours,
            "over_procured_hours": over_procured_hours,
            "at_risk_hours": at_risk_hours,
        },
        "by_day": by_day_rows,
    }
