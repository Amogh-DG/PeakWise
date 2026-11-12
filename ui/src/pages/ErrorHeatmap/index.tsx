import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DEFAULT_MODEL } from '../../constants/models';

export const ErrorHeatmapPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [metric, setMetric] = useState<string>('mape');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Error Heatmap</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Error decomposition across season and hour-of-day.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="bg-brand-surface text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-accent/50 cursor-pointer"
          >
            <option value="mape">MAPE (%)</option>
            <option value="rmse">RMSE (MW)</option>
            <option value="bias">Bias (MW)</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Worst Season" value="Summer" subtitle="Peak air conditioning load" />
        <StatTile label="Highest Error Hour" value="21:00 IST" subtitle="Evening peak ramp" />
        <StatTile label="Summer Peak MAPE" value="6.4%" deltaType="negative" subtitle="Hour 21" />
        <StatTile label="Winter Off-peak MAPE" value="2.9%" deltaType="positive" subtitle="Hour 03" />
      </div>

      <ChartCard
        title="Season × Hour-of-Day Error Matrix"
        subtitle={`Heatmap matrix showing ${metric.toUpperCase()} distribution`}
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Interactive heatmap matrix loaded in Increment B-7
        </div>
      </ChartCard>
    </div>
  );
};

export default ErrorHeatmapPage;
