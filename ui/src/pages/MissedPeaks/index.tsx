import React, { useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DEFAULT_MODEL } from '../../constants/models';

export const MissedPeaksPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Missed-Peak Drill-Down</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Detailed post-mortem of peak events where the classifier or forecaster under-predicted.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile label="Total Peak Days" value="37" subtitle="Top decile events" />
        <StatTile label="Detected Peaks" value="31" delta="83.8% Recall" deltaType="positive" subtitle="True Positives" />
        <StatTile label="Missed Peaks" value="6" delta="16.2% Miss Rate" deltaType="negative" subtitle="False Negatives" />
        <StatTile label="False Alarms" value="12" subtitle="Precautionary alerts" />
      </div>

      <ChartCard
        title="Missed-Peak Diagnostic Table"
        subtitle="Ranked by absolute magnitude error with diagnostic tags and meteorological drivers"
      >
        <div className="flex items-center justify-center h-64 border border-dashed border-brand-border rounded-lg text-brand-muted text-sm font-mono">
          Missed-peaks diagnostic table loaded in Increment B-8
        </div>
      </ChartCard>
    </div>
  );
};

export default MissedPeaksPage;
