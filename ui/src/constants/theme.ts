import { ModelId } from './models';

export const MODEL_COLORS: Record<ModelId, string> = {
  seasonal_naive: '#64748b',
  linear: '#0284c7',
  lgbm: '#1d4ed8',
  xgboost: '#d97706',
  prophet: '#7c3aed',
  lstm: '#db2777',
  ensemble: '#2563eb',
};

export const CHART_THEME = {
  bandP10P90: 'rgba(147, 197, 253, 0.45)',
  bandP05P95: 'rgba(219, 234, 254, 0.45)',
  actualLine: '#0f172a',
  peakMarker: '#ea580c',
  atRiskArea: 'rgba(255, 237, 213, 0.75)',
  gridColor: '#f1f5f9',
  backgroundColor: '#ffffff',
  textColor: '#0f172a',
  mutedColor: '#64748b',
};
