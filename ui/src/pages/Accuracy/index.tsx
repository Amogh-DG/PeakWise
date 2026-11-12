import React, { useState, useEffect } from 'react';
import { getBacktestMetrics, getBacktestPeakMetrics } from '../../api/client';
import {
  BacktestMetricsResponse,
  PeakMetricsResponse,
} from '../../api/types';
import { StatTile } from '../../components/shared/StatTile';
import { ChartCard } from '../../components/shared/ChartCard';
import {
  AccuracyTable,
  MetricType,
} from '../../components/eval/AccuracyTable';
import { CalibrationTable } from '../../components/eval/CalibrationTable';
import { PeakEventsCard } from '../../components/eval/PeakEventsCard';

const SEGMENT_OPTIONS: { id: string; label: string }[] = [
  { id: 'all', label: 'All Segments' },
  { id: 'peak_hours', label: 'Peak Hours (06-10, 19-23)' },
  { id: 'off_peak', label: 'Off-Peak Hours' },
  { id: 'winter', label: 'Winter (Dec–Feb)' },
  { id: 'summer', label: 'Summer (Mar–Jun)' },
  { id: 'monsoon', label: 'Monsoon (Jul–Sep)' },
  { id: 'post_monsoon', label: 'Post-Monsoon (Oct–Nov)' },
];

const METRIC_OPTIONS: { id: MetricType; label: string; unit: string }[] = [
  { id: 'mape', label: 'MAPE', unit: '%' },
  { id: 'rmse_mw', label: 'RMSE', unit: 'MW' },
  { id: 'mae_mw', label: 'MAE', unit: 'MW' },
  { id: 'bias_mw', label: 'Bias', unit: 'MW' },
  { id: 'pinball', label: 'Pinball Loss', unit: 'MW' },
];

export const AccuracyPage: React.FC = () => {
  const [metricsData, setMetricsData] = useState<BacktestMetricsResponse | null>(null);
  const [peakMetricsData, setPeakMetricsData] = useState<PeakMetricsResponse | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<string>('all');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('mape');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [accMetrics, peakMetrics] = await Promise.all([
          getBacktestMetrics(),
          getBacktestPeakMetrics(),
        ]);
        if (isMounted) {
          setMetricsData(accMetrics);
          setPeakMetricsData(peakMetrics);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load evaluation metrics');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  const d1EnsembleMape = metricsData?.rows.find(
    (r) =>
      r.model === 'ensemble' &&
      r.segment === selectedSegment &&
      String(r.horizon_day) === '1'
  );

  const d1EnsembleRmse = metricsData?.rows.find(
    (r) =>
      r.model === 'ensemble' &&
      r.segment === selectedSegment &&
      String(r.horizon_day) === '1'
  );

  const classifierPeakRow = peakMetricsData?.rows.find(
    (r) => r.classifier === 'lgbm_clf' || r.model === 'ensemble'
  ) || peakMetricsData?.rows[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">
            Model Accuracy & Evaluation
          </h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Walk-forward backtest evaluation across seasons, peak hours, and horizons.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2">
            <label htmlFor="segment-select" className="text-xs text-brand-muted font-medium">
              Segment:
            </label>
            <select
              id="segment-select"
              value={selectedSegment}
              onChange={(e) => setSelectedSegment(e.target.value)}
              className="bg-brand-surface border border-brand-border text-brand-text text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-brand-accent cursor-pointer"
            >
              {SEGMENT_OPTIONS.map((seg) => (
                <option key={seg.id} value={seg.id}>
                  {seg.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center bg-brand-surface border border-brand-border rounded-lg p-0.5">
            {METRIC_OPTIONS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setSelectedMetric(m.id)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                  selectedMetric === m.id
                    ? 'bg-brand-accent text-brand-bg font-semibold'
                    : 'text-brand-muted hover:text-brand-text'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {selectedMetric === 'mape' && (
        <div className="flex items-center space-x-2 bg-amber-950/20 border border-amber-900/30 rounded-lg px-3.5 py-2 text-xs text-amber-300">
          <span className="font-semibold uppercase tracking-wider text-[10px] bg-amber-900/40 px-1.5 py-0.5 rounded border border-amber-800/40">
            MAPE Caveat
          </span>
          <span>
            MAPE is vulnerable to small load denominators during winter nights (~2,000 MW);
            evaluate alongside RMSE, MAE, and the peak-hours segment.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="D+1 Ensemble MAPE"
          value={
            d1EnsembleMape ? `${d1EnsembleMape.mape.toFixed(2)}%` : '—'
          }
          delta={
            d1EnsembleMape?.improvement_mape_pct !== null &&
            d1EnsembleMape?.improvement_mape_pct !== undefined
              ? `${d1EnsembleMape.improvement_mape_pct > 0 ? '+' : ''}${d1EnsembleMape.improvement_mape_pct.toFixed(1)}% vs Base`
              : undefined
          }
          deltaType={
            (d1EnsembleMape?.improvement_mape_pct ?? 0) > 0 ? 'positive' : 'negative'
          }
          subtitle={`Segment: ${
            SEGMENT_OPTIONS.find((s) => s.id === selectedSegment)?.label || selectedSegment
          }`}
        />
        <StatTile
          label="D+1 Ensemble RMSE"
          value={
            d1EnsembleRmse ? d1EnsembleRmse.rmse_mw.toFixed(1) : '—'
          }
          unit="MW"
          delta={
            d1EnsembleRmse?.improvement_rmse_pct !== null &&
            d1EnsembleRmse?.improvement_rmse_pct !== undefined
              ? `${d1EnsembleRmse.improvement_rmse_pct > 0 ? '+' : ''}${d1EnsembleRmse.improvement_rmse_pct.toFixed(1)}% vs Base`
              : undefined
          }
          deltaType={
            (d1EnsembleRmse?.improvement_rmse_pct ?? 0) > 0 ? 'positive' : 'negative'
          }
          subtitle="Ensemble vs Seasonal Naive"
        />
        <StatTile
          label="Peak Event Recall"
          value={
            classifierPeakRow
              ? `${(classifierPeakRow.recall * 100).toFixed(1)}%`
              : '—'
          }
          delta={
            classifierPeakRow
              ? `F1: ${classifierPeakRow.f1.toFixed(3)}`
              : undefined
          }
          deltaType="positive"
          subtitle={
            classifierPeakRow
              ? `Precision: ${(classifierPeakRow.precision * 100).toFixed(1)}%`
              : 'Target: ≥ 80.0%'
          }
        />
        <StatTile
          label="Peak Timing Precision"
          value={
            classifierPeakRow
              ? `${(classifierPeakRow.timing_within_1h_pct * 100).toFixed(1)}%`
              : '—'
          }
          subtitle={
            classifierPeakRow
              ? `MAE: ${Math.round(classifierPeakRow.timing_mae_min)} min`
              : 'Within ±1 hour'
          }
        />
      </div>

      <ChartCard
        title={`Accuracy Matrix: ${
          METRIC_OPTIONS.find((m) => m.id === selectedMetric)?.label
        } by Horizon`}
        subtitle={`Comparing model performance across horizons (D+1 to D+7 and All) on ${
          SEGMENT_OPTIONS.find((s) => s.id === selectedSegment)?.label
        }. Values indicate metric magnitude with relative improvement vs Seasonal Naive.`}
        loading={loading}
        error={error}
        empty={!metricsData || metricsData.rows.length === 0}
        emptyMessage="No accuracy metrics available"
      >
        {metricsData && (
          <AccuracyTable
            rows={metricsData.rows}
            metric={selectedMetric}
            selectedSegment={selectedSegment}
          />
        )}
      </ChartCard>

      <ChartCard
        title="Interval Calibration & Coverage (PICP)"
        subtitle="Empirical coverage evaluation of probabilistic intervals (P10–P90 nominal 80%, P05–P95 nominal 90%) and sharpness (MPIW)."
        loading={loading}
        error={error}
        empty={!metricsData || metricsData.rows.length === 0}
        emptyMessage="No calibration data available"
      >
        {metricsData && (
          <CalibrationTable
            rows={metricsData.rows}
            calibrationComparison={
              (metricsData as unknown as { calibration_comparison?: unknown })
                .calibration_comparison
            }
          />
        )}
      </ChartCard>

      <ChartCard
        title="Peak Event Classification & Timing Evaluation"
        subtitle="Dedicated classification performance for top-decile peak day detection and peak hour timing error."
        loading={loading}
        error={error}
        empty={!peakMetricsData || peakMetricsData.rows.length === 0}
        emptyMessage="No peak metrics available"
      >
        {peakMetricsData && (
          <PeakEventsCard
            rows={peakMetricsData.rows}
            thresholdDefinition={peakMetricsData.threshold_definition}
          />
        )}
      </ChartCard>
    </div>
  );
};

export default AccuracyPage;
