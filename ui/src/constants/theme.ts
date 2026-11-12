import { ModelId } from './models';

export const MODEL_COLORS: Record<ModelId, string> = {
  seasonal_naive: '#94a3b8',
  linear: '#0ea5e9',
  lgbm: '#10b981',
  xgboost: '#f59e0b',
  prophet: '#a855f7',
  lstm: '#ec4899',
  ensemble: '#06b6d4',
};

export const CHART_THEME = {
  bandP10P90: 'rgba(6, 182, 212, 0.28)',
  bandP05P95: 'rgba(6, 182, 212, 0.12)',
  actualLine: '#f8fafc',
  peakMarker: '#ef4444',
  atRiskArea: 'rgba(239, 68, 68, 0.25)',
  gridColor: '#1f2937',
  backgroundColor: '#111827',
  textColor: '#f3f4f6',
  mutedColor: '#9ca3af',
};
