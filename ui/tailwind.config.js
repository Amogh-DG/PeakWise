export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          bg: 'var(--color-bg)',
          surface: 'var(--color-surface)',
          border: 'var(--color-border)',
          text: 'var(--color-text)',
          muted: 'var(--color-muted)',
          accent: 'var(--color-accent)',
        },
        model: {
          seasonal_naive: 'var(--color-model-seasonal-naive)',
          linear: 'var(--color-model-linear)',
          lgbm: 'var(--color-model-lgbm)',
          xgboost: 'var(--color-model-xgboost)',
          prophet: 'var(--color-model-prophet)',
          lstm: 'var(--color-model-lstm)',
          ensemble: 'var(--color-model-ensemble)',
        },
        band: {
          p10_p90: 'var(--color-band-p10-p90)',
          p05_p95: 'var(--color-band-p05-p95)',
        },
        chart: {
          actual: 'var(--color-chart-actual)',
          peak: 'var(--color-chart-peak)',
          at_risk: 'var(--color-chart-at-risk)',
        },
      },
    },
  },
  plugins: [],
};
