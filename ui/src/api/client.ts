import {
  ApiErrorDetail,
  ApiErrorPayload,
  HealthResponse,
  MetaResponse,
  ModelsResponse,
  DayAheadForecastResponse,
  WeekAheadForecastResponse,
  PeakDayResponse,
  PeakEventsResponse,
  BacktestPredictionsResponse,
  BacktestMetricsResponse,
  PeakMetricsResponse,
  ErrorHeatmapResponse,
  ProcurementRequest,
  ProcurementResponse,
  ProcurementDefaultsResponse,
  MissedPeaksResponse,
  FeatureImportanceResponse,
  ScenarioRequest,
  ScenarioResponse,
} from './types';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(status: number, error: ApiErrorDetail) {
    super(error.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code;
    this.details = error.details;
  }
}

const BASE_URL = (import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1').replace(/\/+$/, '');

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail: ApiErrorDetail = {
      code: 'HTTP_ERROR',
      message: response.statusText || `Request failed with status ${response.status}`,
    };
    try {
      const payload = (await response.json()) as ApiErrorPayload;
      if (payload && payload.error) {
        errorDetail = payload.error;
      }
    } catch {
    }
    throw new ApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export function getMeta(): Promise<MetaResponse> {
  return request<MetaResponse>('/meta');
}

export function getModels(): Promise<ModelsResponse> {
  return request<ModelsResponse>('/models');
}

export function getDayAheadForecast(date: string, model: string = 'ensemble'): Promise<DayAheadForecastResponse> {
  const query = new URLSearchParams({ date, model });
  return request<DayAheadForecastResponse>(`/forecast/day-ahead?${query.toString()}`);
}

export function getWeekAheadForecast(startDate: string, model: string = 'ensemble'): Promise<WeekAheadForecastResponse> {
  const query = new URLSearchParams({ start_date: startDate, model });
  return request<WeekAheadForecastResponse>(`/forecast/week-ahead?${query.toString()}`);
}

export function getPeakDay(date: string, model: string = 'ensemble'): Promise<PeakDayResponse> {
  const query = new URLSearchParams({ date, model });
  return request<PeakDayResponse>(`/peak/day?${query.toString()}`);
}

export function getPeakEvents(params: {
  from: string;
  to: string;
  model?: string;
  outcome?: string;
  limit?: number;
  offset?: number;
}): Promise<PeakEventsResponse> {
  const query = new URLSearchParams({
    from: params.from,
    to: params.to,
  });
  if (params.model) query.set('model', params.model);
  if (params.outcome) query.set('outcome', params.outcome);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.offset !== undefined) query.set('offset', String(params.offset));
  return request<PeakEventsResponse>(`/peak/events?${query.toString()}`);
}

export function getBacktestPredictions(params: {
  from: string;
  to: string;
  model?: string;
  horizon_day?: number;
}): Promise<BacktestPredictionsResponse> {
  const query = new URLSearchParams({
    from: params.from,
    to: params.to,
  });
  if (params.model) query.set('model', params.model);
  if (params.horizon_day !== undefined) query.set('horizon_day', String(params.horizon_day));
  return request<BacktestPredictionsResponse>(`/backtest/predictions?${query.toString()}`);
}

export function getBacktestMetrics(params?: {
  model?: string | string[];
  horizon_day?: number | string;
  segment?: string;
}): Promise<BacktestMetricsResponse> {
  const query = new URLSearchParams();
  if (params?.model) {
    if (Array.isArray(params.model)) {
      for (const m of params.model) {
        query.append('model', m);
      }
    } else {
      query.set('model', params.model);
    }
  }
  if (params?.horizon_day !== undefined) query.set('horizon_day', String(params.horizon_day));
  if (params?.segment) query.set('segment', params.segment);
  const qStr = query.toString();
  return request<BacktestMetricsResponse>(`/backtest/metrics${qStr ? `?${qStr}` : ''}`);
}

export function getBacktestPeakMetrics(model?: string): Promise<PeakMetricsResponse> {
  const query = new URLSearchParams();
  if (model) query.set('model', model);
  const qStr = query.toString();
  return request<PeakMetricsResponse>(`/backtest/peak-metrics${qStr ? `?${qStr}` : ''}`);
}

export function getErrorHeatmap(params?: {
  model?: string;
  metric?: string;
  horizon_day?: number | string;
}): Promise<ErrorHeatmapResponse> {
  const query = new URLSearchParams();
  if (params?.model) query.set('model', params.model);
  if (params?.metric) query.set('metric', params.metric);
  if (params?.horizon_day !== undefined) query.set('horizon_day', String(params.horizon_day));
  const qStr = query.toString();
  return request<ErrorHeatmapResponse>(`/backtest/error-heatmap${qStr ? `?${qStr}` : ''}`);
}

export function getProcurementRecommendation(payload: ProcurementRequest): Promise<ProcurementResponse> {
  return request<ProcurementResponse>('/procurement/recommend', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getProcurementDefaults(): Promise<ProcurementDefaultsResponse> {
  return request<ProcurementDefaultsResponse>('/procurement/defaults');
}

export function getMissedPeaks(params?: {
  model?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}): Promise<MissedPeaksResponse> {
  const query = new URLSearchParams();
  if (params?.model) query.set('model', params.model);
  if (params?.tag) query.set('tag', params.tag);
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  const qStr = query.toString();
  return request<MissedPeaksResponse>(`/backtest/missed-peaks${qStr ? `?${qStr}` : ''}`);
}

export function getFeatureImportance(model: string, top: number = 20): Promise<FeatureImportanceResponse> {
  const query = new URLSearchParams({ top: String(top) });
  return request<FeatureImportanceResponse>(`/models/${encodeURIComponent(model)}/feature-importance?${query.toString()}`);
}

export function postForecastScenario(payload: ScenarioRequest): Promise<ScenarioResponse> {
  return request<ScenarioResponse>('/forecast/scenario', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
