from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    mock: bool
    artifacts_loaded: bool


class MetaResponse(BaseModel):
    version: str
    timezone: str
    origin_hour_local: int
    data_range: dict[str, str]
    backtest_range: dict[str, str]
    quantiles: list[float]
    peak_threshold_mw_latest: float
    peak_definition: str
    season_definition: dict[str, list[int]]
    peak_hours: list[int]
    models: list[str]
    weather_proxy_note: str


class ModelItem(BaseModel):
    id: str
    label: str
    kind: str
    is_baseline: bool


class ModelsResponse(BaseModel):
    models: list[ModelItem]


class ForecastPoint(BaseModel):
    ts: str
    horizon_h: int
    horizon_day: int | None = None
    p05: float
    p10: float
    p50: float
    p90: float
    p95: float
    actual: float | None = None
    at_risk: bool


class PeakSummary(BaseModel):
    predicted_peak_ts: str
    predicted_peak_mw: dict[str, float]
    actual_peak_ts: str | None = None
    actual_peak_mw: float | None = None


class DayAheadForecastResponse(BaseModel):
    date: str
    model: str
    origin_ts: str
    unit: str
    peak_threshold_mw: float
    points: list[ForecastPoint]
    peak: PeakSummary


class DailyPeakSummary(BaseModel):
    date: str
    predicted_peak_ts: str
    predicted_peak_mw: dict[str, float]
    actual_peak_ts: str | None = None
    actual_peak_mw: float | None = None


class WeekAheadForecastResponse(BaseModel):
    start_date: str
    end_date: str
    model: str
    origin_ts: str
    unit: str
    peak_threshold_mw: float
    points: list[ForecastPoint]
    daily_peaks: list[DailyPeakSummary]


class PeakActual(BaseModel):
    is_peak_day: bool
    peak_ts: str
    peak_mw: float


class PeakDayResponse(BaseModel):
    date: str
    model: str
    threshold_mw: float
    peak_probability: float
    decision_threshold: float
    is_peak_day_pred: bool
    predicted_peak_hour: int
    predicted_peak_ts: str
    predicted_peak_mw: dict[str, float]
    actual: PeakActual | None = None
    timing_error_min: int | None = None
    magnitude_error_mw: float | None = None
    outcome: str | None = None


class PeakEventsResponse(BaseModel):
    total: int
    items: list[dict[str, Any]]


class BacktestPredictionPoint(BaseModel):
    ts: str
    origin_ts: str
    p05: float
    p10: float
    p50: float
    p90: float
    p95: float
    actual: float | None = None


class BacktestPredictionsResponse(BaseModel):
    model: str
    horizon_day: int
    points: list[BacktestPredictionPoint]


class AccuracyMetricRow(BaseModel):
    model: str
    horizon_day: int | str
    segment: str
    n: int
    mape: float
    rmse_mw: float
    mae_mw: float
    bias_mw: float
    pinball: float
    picp_80: float
    picp_90: float
    mpiw_80_mw: float
    improvement_mape_pct: float | None = None
    improvement_rmse_pct: float | None = None


class BacktestMetricsResponse(BaseModel):
    generated_at: str
    rows: list[AccuracyMetricRow]


class PeakMetricConfusion(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int


class PeakMetricRow(BaseModel):
    model: str
    classifier: str
    n_days: int
    n_peak_days: int
    precision: float
    recall: float
    f1: float
    pr_auc: float
    confusion: PeakMetricConfusion
    decision_threshold: float
    timing_mae_min: float
    timing_within_1h_pct: float
    magnitude_mae_mw: float
    magnitude_bias_mw: float


class PeakMetricsResponse(BaseModel):
    threshold_definition: str
    rows: list[PeakMetricRow]


class ErrorHeatmapResponse(BaseModel):
    model: str
    metric: str
    horizon_day: int | str
    hours: list[int]
    seasons: list[str]
    values: list[list[float | None]]
    counts: list[list[int]]


class Tariff(BaseModel):
    da_price_inr_per_mwh: float
    under_price_inr_per_mwh: float
    resale_price_inr_per_mwh: float


class ProcurementRequest(BaseModel):
    start_date: str
    days: int
    model: str = "ensemble"
    risk_quantile: float | str = 0.9
    tariff: Tariff | None = None


class ProcurementSchedulePoint(BaseModel):
    ts: str
    scheduled_mw: float
    p50_mw: float
    p90_mw: float
    flat_mw: float
    actual_mw: float | None = None


class ProcurementSummary(BaseModel):
    total_scheduled_mwh: float
    cost_inr: float | None = None
    flat_cost_inr: float | None = None
    flat_peak_cost_inr: float | None = None
    savings_inr: float | None = None
    savings_pct: float | None = None
    p90_risk_exposure_inr: float
    under_procured_hours: int | None = None
    over_procured_hours: int | None = None
    at_risk_hours: list[str]


class ProcurementDay(BaseModel):
    date: str
    scheduled_mwh: float
    cost_inr: float | None = None
    flat_cost_inr: float | None = None
    peak_scheduled_mw: float


class ProcurementResponse(BaseModel):
    start_date: str
    end_date: str
    model: str
    risk_quantile: float
    risk_quantile_source: str
    newsvendor_quantile: float
    tariff_used: Tariff
    baseline: dict[str, Any]
    schedule: list[ProcurementSchedulePoint]
    summary: ProcurementSummary
    by_day: list[ProcurementDay]


class ProcurementDefaultsResponse(BaseModel):
    tariff: Tariff
    disclaimer: str
    default_risk_quantile: float


class MissedPeakItem(BaseModel):
    model: str
    date: str
    season: str
    threshold_mw: float
    peak_probability: float
    pred_peak_ts: str
    pred_peak_mw_p50: float
    actual_peak_ts: str
    actual_peak_mw: float
    magnitude_error_mw: float
    timing_error_min: int
    tags: list[str]
    note: str


class MissedPeaksResponse(BaseModel):
    total: int
    items: list[MissedPeakItem]


class FeatureItem(BaseModel):
    feature: str
    importance: float
    group: str


class FeatureImportanceResponse(BaseModel):
    model: str
    features: list[FeatureItem]


class ScenarioRequest(BaseModel):
    date: str
    model: str = "lgbm"
    temp_delta_c: float


class ScenarioResponse(DayAheadForecastResponse):
    scenario: dict[str, float]
