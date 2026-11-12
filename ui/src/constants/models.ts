export const MODELS = [
  'seasonal_naive',
  'linear',
  'lgbm',
  'xgboost',
  'prophet',
  'lstm',
  'ensemble',
] as const;

export type ModelId = (typeof MODELS)[number];

export const BASELINE_MODEL: ModelId = 'seasonal_naive';
export const DEFAULT_MODEL: ModelId = 'ensemble';

export const MODEL_LABELS: Record<ModelId, string> = {
  ensemble: 'Ensemble',
  lgbm: 'LightGBM',
  xgboost: 'XGBoost',
  prophet: 'Prophet',
  lstm: 'LSTM',
  linear: 'Linear Regression',
  seasonal_naive: 'Seasonal Naive (Baseline)',
};
