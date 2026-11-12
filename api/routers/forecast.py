from datetime import timedelta

import pandas as pd
from fastapi import APIRouter, Query

from api.errors import ApiException
from api.models import (
    DailyPeakSummary,
    DayAheadForecastResponse,
    ForecastPoint,
    PeakSummary,
    ScenarioRequest,
    ScenarioResponse,
    WeekAheadForecastResponse,
)
from api.store import store

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/day-ahead", response_model=DayAheadForecastResponse)
def get_day_ahead(
    date: str = Query(...),
    model: str = Query("ensemble"),
) -> DayAheadForecastResponse:
    store.validate_model(model)
    target_dt = store.validate_date(date)

    start_ts = pd.Timestamp(date, tz="Asia/Kolkata")
    end_ts = start_ts + pd.Timedelta(days=1)

    df = store.predictions_df
    date_filtered = df[
        (df["model"] == model)
        & (df["horizon_day"] == 1)
        & (df["target_ts"] >= start_ts)
        & (df["target_ts"] < end_ts)
    ].sort_values("target_ts")

    if date_filtered.empty:
        raise ApiException(404, "DATE_OUT_OF_RANGE", f"No forecast data for date: {date}")

    peak_threshold_mw = float(store.meta.get("peak_threshold_mw_latest", 7650.0))
    origin_ts_str = date_filtered.iloc[0]["origin_ts"].isoformat()

    points = []
    for _, row in date_filtered.iterrows():
        y_true_val = float(row["y_true"]) if pd.notna(row["y_true"]) else None
        points.append(
            ForecastPoint(
                ts=row["target_ts"].isoformat(),
                horizon_h=int(row["horizon_h"]),
                p05=float(row["p05"]),
                p10=float(row["p10"]),
                p50=float(row["p50"]),
                p90=float(row["p90"]),
                p95=float(row["p95"]),
                actual=y_true_val,
                at_risk=bool(row["p90"] >= peak_threshold_mw),
            )
        )

    peak_df = store.peak_df
    target_date_obj = target_dt.date()
    peak_match = peak_df[(peak_df["model"] == model) & (peak_df["date"] == target_date_obj)]

    if not peak_match.empty:
        p_row = peak_match.iloc[0]
        peak_summary = PeakSummary(
            predicted_peak_ts=p_row["pred_peak_ts"].isoformat(),
            predicted_peak_mw={
                "p10": float(p_row["pred_peak_mw_p10"]),
                "p50": float(p_row["pred_peak_mw_p50"]),
                "p90": float(p_row["pred_peak_mw_p90"]),
            },
            actual_peak_ts=p_row["actual_peak_ts"].isoformat() if pd.notna(p_row["actual_peak_ts"]) else None,
            actual_peak_mw=float(p_row["actual_peak_mw"]) if pd.notna(p_row["actual_peak_mw"]) else None,
        )
    else:
        max_p50_row = date_filtered.loc[date_filtered["p50"].idxmax()]
        has_actuals = date_filtered["y_true"].notna().any()
        max_actual_row = date_filtered.loc[date_filtered["y_true"].idxmax()] if has_actuals else None

        peak_summary = PeakSummary(
            predicted_peak_ts=max_p50_row["target_ts"].isoformat(),
            predicted_peak_mw={
                "p10": float(max_p50_row["p10"]),
                "p50": float(max_p50_row["p50"]),
                "p90": float(max_p50_row["p90"]),
            },
            actual_peak_ts=max_actual_row["target_ts"].isoformat() if max_actual_row is not None else None,
            actual_peak_mw=float(max_actual_row["y_true"]) if max_actual_row is not None else None,
        )

    return DayAheadForecastResponse(
        date=date,
        model=model,
        origin_ts=origin_ts_str,
        unit="MW",
        peak_threshold_mw=peak_threshold_mw,
        points=points,
        peak=peak_summary,
    )


@router.get("/week-ahead", response_model=WeekAheadForecastResponse)
def get_week_ahead(
    start_date: str = Query(...),
    model: str = Query("ensemble"),
) -> WeekAheadForecastResponse:
    store.validate_model(model)
    start_dt = store.validate_date(start_date)

    start_ts = pd.Timestamp(start_date, tz="Asia/Kolkata")
    origin_ts = (start_ts - pd.Timedelta(days=1)).replace(hour=10, minute=0, second=0)

    df = store.predictions_df
    df_filtered = df[(df["model"] == model) & (df["origin_ts"] == origin_ts)].sort_values("target_ts")

    if df_filtered.empty:
        raise ApiException(404, "DATE_OUT_OF_RANGE", f"No forecast data originating for start date: {start_date}")

    peak_threshold_mw = float(store.meta.get("peak_threshold_mw_latest", 7650.0))
    origin_ts_str = df_filtered.iloc[0]["origin_ts"].isoformat()
    end_date = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")

    points = []
    for _, row in df_filtered.iterrows():
        y_true_val = float(row["y_true"]) if pd.notna(row["y_true"]) else None
        points.append(
            ForecastPoint(
                ts=row["target_ts"].isoformat(),
                horizon_h=int(row["horizon_h"]),
                horizon_day=int(row["horizon_day"]),
                p05=float(row["p05"]),
                p10=float(row["p10"]),
                p50=float(row["p50"]),
                p90=float(row["p90"]),
                p95=float(row["p95"]),
                actual=y_true_val,
                at_risk=bool(row["p90"] >= peak_threshold_mw),
            )
        )

    daily_peaks = []
    peak_df = store.peak_df

    for day_idx in range(7):
        cur_date_dt = start_dt + timedelta(days=day_idx)
        cur_date_str = cur_date_dt.strftime("%Y-%m-%d")
        cur_date_obj = cur_date_dt.date()

        day_start_ts = start_ts + pd.Timedelta(days=day_idx)
        day_end_ts = day_start_ts + pd.Timedelta(days=1)
        day_points = df_filtered[(df_filtered["target_ts"] >= day_start_ts) & (df_filtered["target_ts"] < day_end_ts)]
        peak_match = peak_df[(peak_df["model"] == model) & (peak_df["date"] == cur_date_obj)]

        if not peak_match.empty:
            p_row = peak_match.iloc[0]
            daily_peaks.append(
                DailyPeakSummary(
                    date=cur_date_str,
                    predicted_peak_ts=p_row["pred_peak_ts"].isoformat(),
                    predicted_peak_mw={
                        "p10": float(p_row["pred_peak_mw_p10"]),
                        "p50": float(p_row["pred_peak_mw_p50"]),
                        "p90": float(p_row["pred_peak_mw_p90"]),
                    },
                    actual_peak_ts=p_row["actual_peak_ts"].isoformat() if pd.notna(p_row["actual_peak_ts"]) else None,
                    actual_peak_mw=float(p_row["actual_peak_mw"]) if pd.notna(p_row["actual_peak_mw"]) else None,
                )
            )
        elif not day_points.empty:
            max_p50 = day_points.loc[day_points["p50"].idxmax()]
            has_actuals = day_points["y_true"].notna().any()
            max_act = day_points.loc[day_points["y_true"].idxmax()] if has_actuals else None
            daily_peaks.append(
                DailyPeakSummary(
                    date=cur_date_str,
                    predicted_peak_ts=max_p50["target_ts"].isoformat(),
                    predicted_peak_mw={
                        "p10": float(max_p50["p10"]),
                        "p50": float(max_p50["p50"]),
                        "p90": float(max_p50["p90"]),
                    },
                    actual_peak_ts=max_act["target_ts"].isoformat() if max_act is not None else None,
                    actual_peak_mw=float(max_act["y_true"]) if max_act is not None else None,
                )
            )

    return WeekAheadForecastResponse(
        start_date=start_date,
        end_date=end_date,
        model=model,
        origin_ts=origin_ts_str,
        unit="MW",
        peak_threshold_mw=peak_threshold_mw,
        points=points,
        daily_peaks=daily_peaks,
    )


@router.post("/scenario", response_model=ScenarioResponse)
def post_scenario(_: ScenarioRequest) -> ScenarioResponse:
    raise ApiException(501, "NOT_IMPLEMENTED", "Scenario analysis not implemented yet")
