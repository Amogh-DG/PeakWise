from datetime import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Query

from api.errors import ApiException
from api.models import (
    BacktestMetricsResponse,
    BacktestPredictionPoint,
    BacktestPredictionsResponse,
    ErrorHeatmapResponse,
    FeatureImportanceResponse,
    MissedPeaksResponse,
    PeakMetricsResponse,
)
from api.store import store

router = APIRouter(tags=["backtest"])


@router.get("/backtest/predictions", response_model=BacktestPredictionsResponse)
def get_backtest_predictions(
    from_date: Annotated[str, Query(alias="from")],
    to_date: Annotated[str, Query(alias="to")],
    model: Annotated[str, Query()] = "ensemble",
    horizon_day: Annotated[int, Query(ge=1, le=7)] = 1,
) -> BacktestPredictionsResponse:
    store.validate_model(model)
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ApiException(400, "BAD_DATE_RANGE", f"Invalid date format: {exc}") from exc

    if to_dt < from_dt:
        raise ApiException(400, "BAD_DATE_RANGE", "'to' must be on or after 'from'")

    if (to_dt - from_dt).days > 92:
        raise ApiException(400, "BAD_DATE_RANGE", "'to' must span at most 92 days from 'from'")

    start_ts = pd.Timestamp(from_date, tz="Asia/Kolkata")
    end_ts = pd.Timestamp(to_date, tz="Asia/Kolkata") + pd.Timedelta(days=1)

    df = store.predictions_df
    range_filtered = df[
        (df["model"] == model)
        & (df["horizon_day"] == horizon_day)
        & (df["target_ts"] >= start_ts)
        & (df["target_ts"] < end_ts)
    ].sort_values("target_ts")

    points = []
    for _, row in range_filtered.iterrows():
        y_true_val = float(row["y_true"]) if pd.notna(row["y_true"]) else None
        points.append(
            BacktestPredictionPoint(
                ts=row["target_ts"].isoformat(),
                origin_ts=row["origin_ts"].isoformat(),
                p05=float(row["p05"]),
                p10=float(row["p10"]),
                p50=float(row["p50"]),
                p90=float(row["p90"]),
                p95=float(row["p95"]),
                actual=y_true_val,
            )
        )

    return BacktestPredictionsResponse(
        model=model,
        horizon_day=horizon_day,
        points=points,
    )


@router.get("/backtest/metrics", response_model=BacktestMetricsResponse)
def get_backtest_metrics(
    model: Annotated[list[str] | None, Query()] = None,
    horizon_day: Annotated[str | None, Query()] = None,
    segment: Annotated[str | None, Query()] = None,
) -> BacktestMetricsResponse:
    raw_data = store.metrics_accuracy
    rows = raw_data.get("rows", [])

    if model:
        rows = [r for r in rows if r.get("model") in model]
    if horizon_day is not None:
        rows = [r for r in rows if str(r.get("horizon_day")) == str(horizon_day)]
    if segment:
        rows = [r for r in rows if r.get("segment") == segment]

    return BacktestMetricsResponse(
        generated_at=raw_data.get("generated_at", ""),
        rows=rows,
    )


@router.get("/backtest/peak-metrics", response_model=PeakMetricsResponse)
def get_backtest_peak_metrics(
    model: Annotated[str | None, Query()] = None,
) -> PeakMetricsResponse:
    raw_data = store.metrics_peak
    rows = raw_data.get("rows", [])

    if model:
        rows = [r for r in rows if r.get("model") == model or r.get("classifier") == "rule"]

    return PeakMetricsResponse(
        threshold_definition=raw_data.get("threshold_definition", ""),
        rows=rows,
    )


@router.get("/backtest/error-heatmap", response_model=ErrorHeatmapResponse)
def get_error_heatmap(
    model: Annotated[str, Query()] = "ensemble",
    metric: Annotated[str, Query()] = "mape",
    horizon_day: Annotated[str, Query()] = "1",
) -> ErrorHeatmapResponse:
    cells = store.error_heatmap.get("cells", [])
    for cell in cells:
        if (
            cell.get("model") == model
            and cell.get("metric") == metric
            and str(cell.get("horizon_day")) == str(horizon_day)
        ):
            return ErrorHeatmapResponse(**cell)

    raise ApiException(404, "NOT_FOUND", f"Error heatmap cell not found for model={model}, metric={metric}, horizon_day={horizon_day}")


@router.get("/backtest/missed-peaks", response_model=MissedPeaksResponse)
def get_missed_peaks(
    model: Annotated[str, Query()] = "ensemble",
    tag: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(le=200, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MissedPeaksResponse:
    items = store.missed_peaks.get("items", [])
    filtered = [item for item in items if item.get("model") == model]
    if tag:
        filtered = [item for item in filtered if tag in item.get("tags", [])]

    total = len(filtered)
    page_items = filtered[offset : offset + limit]
    return MissedPeaksResponse(total=total, items=page_items)


@router.get("/models/{model}/feature-importance", response_model=FeatureImportanceResponse)
def get_feature_importance(
    model: str,
    top: Annotated[int, Query(le=100, ge=1)] = 20,
) -> FeatureImportanceResponse:
    models_dict = store.feature_importance.get("models", {})
    if model not in models_dict:
        raise ApiException(404, "NOT_FOUND", f"Feature importance not available for model: {model}")

    features = models_dict[model][:top]
    return FeatureImportanceResponse(model=model, features=features)
