import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { DatePicker } from '../../components/shared/DatePicker';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DEFAULT_MODEL } from '../../constants/models';

export const ForecastPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [date, setDate] = useState<string>('2026-06-12');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Demand Forecast</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Hourly probabilistic electricity demand forecasts for Delhi at 10:00 IST origin.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
          <DatePicker value={date} onChange={setDate} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Target Date" value={date} subtitle="D+1 Horizon" />
        <StatTile label="Selected Model" value={model} subtitle="Probabilistic Quantiles" />
        <StatTile label="Peak Threshold" value="7,650" unit="MW" subtitle="90th percentile threshold" />
        <StatTile label="Peak Risk Status" value="At Risk" delta="P90 breach" deltaType="negative" subtitle="Hours 19:00 - 23:00" />
      </div>

      <ChartCard
        title="Day-Ahead Hourly Load Profile"
        subtitle="P05, P10, P50, P90, P95 prediction intervals vs Actual demand"
        units="MW"
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Forecast visualization loaded in Increment B-5
        </div>
      </ChartCard>
    </div>
  );
};

export default ForecastPage;
