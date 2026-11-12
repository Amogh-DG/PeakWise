export interface HealthResponse {
  status: string;
  version: string;
  mock: boolean;
  artifacts_loaded: boolean;
}

export interface MetaResponse {
  version: string;
  timezone: string;
  origin_hour_local: number;
  data_range: {
    start: string;
    end: string;
  };
  backtest_range: {
    start: string;
    end: string;
  };
  quantiles: number[];
  peak_threshold_mw_latest: number;
  peak_definition: string;
  season_definition: Record<string, number[]>;
  peak_hours: number[];
  models: string[];
  weather_proxy_note: string;
}

export interface ModelItem {
  id: string;
  label: string;
  kind: string;
  is_baseline: boolean;
}

export interface ModelsResponse {
  models: ModelItem[];
}

export interface ForecastPoint {
  ts: string;
  horizon_h: number;
  horizon_day?: number;
  p05: number;
  p10: number;
  p50: number;
  p90: number;
  p95: number;
  actual: number | null;
  at_risk: boolean;
}

export interface PeakForecast {
  predicted_peak_ts: string;
  predicted_peak_mw: {
    p10: number;
    p50: number;
    p90: number;
  };
  actual_peak_ts: string | null;
  actual_peak_mw: number | null;
}

export interface DayAheadForecastResponse {
  date: string;
  model: string;
  origin_ts: string;
  unit: string;
  peak_threshold_mw: number;
  points: ForecastPoint[];
  peak: PeakForecast;
}

export interface DailyPeakForecast extends PeakForecast {
  date: string;
}

export interface WeekAheadForecastResponse {
  start_date: string;
  end_date: string;
  model: string;
  origin_ts: string;
  unit: string;
  peak_threshold_mw: number;
  points: ForecastPoint[];
  daily_peaks: DailyPeakForecast[];
}

export type PeakOutcome = 'hit' | 'miss' | 'false_alarm' | 'correct_reject';

export interface PeakDayResponse {
  date: string;
  model: string;
  threshold_mw: number;
  peak_probability: number;
  decision_threshold: number;
  is_peak_day_pred: boolean;
  predicted_peak_hour: number;
  predicted_peak_ts: string;
  predicted_peak_mw: {
    p10: number;
    p50: number;
    p90: number;
  };
  actual: {
    is_peak_day: boolean;
    peak_ts: string;
    peak_mw: number;
  } | null;
  timing_error_min: number | null;
  magnitude_error_mw: number | null;
  outcome: PeakOutcome | null;
}

export interface PeakEventsResponse {
  total: number;
  items: Array<Omit<PeakDayResponse, 'model'>>;
}

export interface BacktestPredictionPoint {
  ts: string;
  origin_ts: string;
  p05: number;
  p10: number;
  p50: number;
  p90: number;
  p95: number;
  actual: number | null;
}

export interface BacktestPredictionsResponse {
  model: string;
  horizon_day: number;
  points: BacktestPredictionPoint[];
}

export interface AccuracyMetricRow {
  model: string;
  horizon_day: number | string;
  segment: string;
  n: number;
  mape: number;
  rmse_mw: number;
  mae_mw: number;
  bias_mw: number;
  pinball: number;
  picp_80: number;
  picp_90: number;
  mpiw_80_mw: number;
  improvement_mape_pct: number | null;
  improvement_rmse_pct: number | null;
}

export interface BacktestMetricsResponse {
  generated_at: string;
  rows: AccuracyMetricRow[];
}

export interface PeakMetricRow {
  model: string;
  classifier: string;
  n_days: number;
  n_peak_days: number;
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  confusion: {
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
  decision_threshold: number;
  timing_mae_min: number;
  timing_within_1h_pct: number;
  magnitude_mae_mw: number;
  magnitude_bias_mw: number;
}

export interface PeakMetricsResponse {
  threshold_definition: string;
  rows: PeakMetricRow[];
}

export interface ErrorHeatmapResponse {
  model: string;
  metric: 'mape' | 'rmse' | 'bias';
  horizon_day: number | string;
  hours: number[];
  seasons: string[];
  values: (number | null)[][];
  counts: number[][];
}

export interface ProcurementTariff {
  da_price_inr_per_mwh: number;
  under_price_inr_per_mwh: number;
  resale_price_inr_per_mwh: number;
}

export interface ProcurementRequest {
  start_date: string;
  days: number;
  model?: string;
  risk_quantile: number | 'newsvendor';
  tariff?: ProcurementTariff;
}

export interface ProcurementSchedulePoint {
  ts: string;
  scheduled_mw: number;
  p50_mw: number;
  p90_mw: number;
  flat_mw: number;
  actual_mw: number | null;
}

export interface ProcurementSummary {
  total_scheduled_mwh: number;
  cost_inr: number | null;
  flat_cost_inr: number | null;
  flat_peak_cost_inr: number | null;
  savings_inr: number | null;
  savings_pct: number | null;
  p90_risk_exposure_inr: number;
  under_procured_hours: number | null;
  over_procured_hours: number | null;
  at_risk_hours: string[];
}

export interface ProcurementDaySummary {
  date: string;
  scheduled_mwh: number;
  cost_inr: number | null;
  flat_cost_inr: number | null;
  peak_scheduled_mw: number;
}

export interface ProcurementResponse {
  start_date: string;
  end_date: string;
  model: string;
  risk_quantile: number;
  risk_quantile_source: 'user' | 'newsvendor';
  newsvendor_quantile: number;
  tariff_used: ProcurementTariff;
  baseline: {
    type: string;
    flat_mw: number;
    alt_flat_prev_week_peak_mw: number;
  };
  schedule: ProcurementSchedulePoint[];
  summary: ProcurementSummary;
  by_day: ProcurementDaySummary[];
}

export interface ProcurementDefaultsResponse {
  tariff: ProcurementTariff;
  disclaimer: string;
  default_risk_quantile: number;
}

export interface MissedPeakItem {
  model: string;
  date: string;
  season: string;
  threshold_mw: number;
  peak_probability: number;
  pred_peak_ts: string;
  pred_peak_mw_p50: number;
  actual_peak_ts: string;
  actual_peak_mw: number;
  magnitude_error_mw: number;
  timing_error_min: number;
  tags: string[];
  note: string;
}

export interface MissedPeaksResponse {
  total: number;
  items: MissedPeakItem[];
}

export interface FeatureImportanceItem {
  feature: string;
  importance: number;
  group: string;
}

export interface FeatureImportanceResponse {
  model: string;
  features: FeatureImportanceItem[];
}

export interface ScenarioRequest {
  date: string;
  model?: string;
  temp_delta_c: number;
}

export interface ScenarioResponse extends DayAheadForecastResponse {
  scenario: {
    temp_delta_c: number;
  };
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorPayload {
  error: ApiErrorDetail;
}
