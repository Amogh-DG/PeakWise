import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';

export const InsightsPage: React.FC = () => {
  const [model, setModel] = useState<string>('lgbm');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Insights & Interpretability</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Feature importance analysis, meteorological drivers, and executive memos.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Top Feature" value="wx_cdh_24" subtitle="Cooling Degree-Hours (24h)" />
        <StatTile label="Thermal Inertia Share" value="28.4%" subtitle="Lags 1h - 72h" />
        <StatTile label="Autoregressive Share" value="31.2%" subtitle="Lagged hourly load" />
        <StatTile label="Calendar / Festival" value="18.6%" subtitle="Diwali / Weekend effects" />
      </div>

      <ChartCard
        title="Normalized Feature Importance"
        subtitle={`Feature ranking by gain and split contribution for ${model.toUpperCase()}`}
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Feature importance ranking loaded in Increment B-11
        </div>
      </ChartCard>
    </div>
  );
};

export default InsightsPage;
