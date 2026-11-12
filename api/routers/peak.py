from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Query

from api.errors import ApiException
from api.models import PeakActual, PeakDayResponse, PeakEventsResponse
from api.store import store

router = APIRouter(prefix="/peak", tags=["peak"])


@router.get("/day", response_model=PeakDayResponse)
def get_peak_day(
    date: str = Query(...),
    model: str = Query("ensemble"),
) -> PeakDayResponse:
    store.validate_model(model)
    target_dt = store.validate_date(date)
    target_date_obj = target_dt.date()

    df = store.peak_df
    matches = df[(df["model"] == model) & (df["date"] == target_date_obj)]
    if matches.empty:
        raise ApiException(404, "DATE_OUT_OF_RANGE", f"No peak prediction data for date: {date}")

    row = matches.iloc[0]

    actual = None
    if pd.notna(row.get("actual_is_peak")):
        actual = PeakActual(
            is_peak_day=bool(row["actual_is_peak"]),
            peak_ts=row["actual_peak_ts"].isoformat() if pd.notna(row["actual_peak_ts"]) else "",
            peak_mw=float(row["actual_peak_mw"]) if pd.notna(row["actual_peak_mw"]) else 0.0,
        )

    return PeakDayResponse(
        date=date,
        model=model,
        threshold_mw=float(row["threshold_mw"]),
        peak_probability=float(row["peak_probability"]),
        decision_threshold=float(row["decision_threshold"]),
        is_peak_day_pred=bool(row["pred_is_peak"]),
        predicted_peak_hour=int(row["pred_peak_hour"]),
        predicted_peak_ts=row["pred_peak_ts"].isoformat(),
        predicted_peak_mw={
            "p10": float(row["pred_peak_mw_p10"]),
            "p50": float(row["pred_peak_mw_p50"]),
            "p90": float(row["pred_peak_mw_p90"]),
        },
        actual=actual,
        timing_error_min=int(row["timing_error_min"]) if pd.notna(row.get("timing_error_min")) else None,
        magnitude_error_mw=float(row["magnitude_error_mw"]) if pd.notna(row.get("magnitude_error_mw")) else None,
        outcome=str(row["outcome"]) if pd.notna(row.get("outcome")) else None,
    )


@router.get("/events", response_model=PeakEventsResponse)
def get_peak_events(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    model: str = Query("ensemble"),
    outcome: str | None = Query(None),
    limit: int = Query(100, le=500, ge=1),
    offset: int = Query(0, ge=0),
) -> PeakEventsResponse:
    store.validate_model(model)
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ApiException(400, "BAD_DATE_RANGE", f"Invalid date format: {exc}") from exc

    if to_dt < from_dt:
        raise ApiException(400, "BAD_DATE_RANGE", "'to' must be on or after 'from'")

    df = store.peak_df
    filtered = df[(df["model"] == model) & (df["date"] >= from_dt) & (df["date"] <= to_dt)]
    if outcome:
        filtered = filtered[filtered["outcome"] == outcome]

    filtered = filtered.sort_values("date")
    total = len(filtered)
    page_df = filtered.iloc[offset : offset + limit]

    items = []
    for _, row in page_df.iterrows():
        actual = None
        if pd.notna(row.get("actual_is_peak")):
            actual = {
                "is_peak_day": bool(row["actual_is_peak"]),
                "peak_ts": row["actual_peak_ts"].isoformat() if pd.notna(row["actual_peak_ts"]) else "",
                "peak_mw": float(row["actual_peak_mw"]) if pd.notna(row["actual_peak_mw"]) else 0.0,
            }

        items.append({
            "date": str(row["date"]),
            "threshold_mw": float(row["threshold_mw"]),
            "peak_probability": float(row["peak_probability"]),
            "decision_threshold": float(row["decision_threshold"]),
            "is_peak_day_pred": bool(row["pred_is_peak"]),
            "predicted_peak_hour": int(row["pred_peak_hour"]),
            "predicted_peak_ts": row["pred_peak_ts"].isoformat(),
            "predicted_peak_mw": {
                "p10": float(row["pred_peak_mw_p10"]),
                "p50": float(row["pred_peak_mw_p50"]),
                "p90": float(row["pred_peak_mw_p90"]),
            },
            "actual": actual,
            "timing_error_min": int(row["timing_error_min"]) if pd.notna(row.get("timing_error_min")) else None,
            "magnitude_error_mw": float(row["magnitude_error_mw"]) if pd.notna(row.get("magnitude_error_mw")) else None,
            "outcome": str(row["outcome"]) if pd.notna(row.get("outcome")) else None,
        })

    return PeakEventsResponse(total=total, items=items)
