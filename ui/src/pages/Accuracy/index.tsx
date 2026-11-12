import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DEFAULT_MODEL } from '../../constants/models';

export const AccuracyPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Model Accuracy & Backtest</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Walk-forward backtest evaluation across seasons, peak hours, and horizons.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="D+1 MAPE" value="4.8%" delta="-31.2% vs Naive" deltaType="positive" subtitle="Peak Hours Segment" />
        <StatTile label="D+1 RMSE" value="312.4" unit="MW" delta="-28.7%" deltaType="positive" subtitle="Ensemble Model" />
        <StatTile label="PICP 80%" value="79.0%" subtitle="Target: 80% coverage" />
        <StatTile label="PICP 90%" value="89.0%" subtitle="Target: 90% coverage" />
      </div>

      <ChartCard
        title="Accuracy Metrics by Horizon and Segment"
        subtitle="Comparing MAPE, RMSE, Pinball Loss and Coverage vs Baselines"
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Accuracy comparison table loaded in Increment B-6
        </div>
      </ChartCard>
    </div>
  );
};

export default AccuracyPage;
