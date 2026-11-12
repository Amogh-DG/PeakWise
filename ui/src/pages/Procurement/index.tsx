import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { DatePicker } from '../../components/shared/DatePicker';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DEFAULT_MODEL } from '../../constants/models';

export const ProcurementPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [startDate, setStartDate] = useState<string>('2026-06-08');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Procurement Copilot</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Day-ahead schedule optimization, newsvendor risk quantiles, and cost simulations.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
          <DatePicker value={startDate} onChange={setStartDate} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Simulated Savings" value="₹29.0 Cr" delta="+4.9%" deltaType="positive" subtitle="vs Naive Flat Schedule" />
        <StatTile label="P90 Risk Exposure" value="₹31.0 Cr" subtitle="Shortfall cost risk" />
        <StatTile label="Newsvendor Quantile" value="0.737" subtitle="(Under - DA) / (Under - Resale)" />
        <StatTile label="Selected Risk Quantile" value="P90" subtitle="Conservative peak hedge" />
      </div>

      <ChartCard
        title="Optimal Day-Ahead Purchase Schedule vs Flat Baseline"
        subtitle="Hourly scheduled dispatch MW against P50 and P90 demand trajectories"
        units="MW"
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Procurement schedule and cost comparison loaded in Increment B-10
        </div>
      </ChartCard>
    </div>
  );
};

export default ProcurementPage;
