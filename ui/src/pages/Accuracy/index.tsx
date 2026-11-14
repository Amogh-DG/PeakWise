import React, { useState, useEffect, useMemo } from 'react';
import { getBacktestMetrics, getBacktestPeakMetrics } from '../../api/client';
import { BacktestMetricsResponse, PeakMetricsResponse } from '../../api/types';
import { ChartCard } from '../../components/shared/ChartCard';
import { AccuracyTable, MetricType } from '../../components/eval/AccuracyTable';
import { CalibrationTable } from '../../components/eval/CalibrationTable';
import { PeakEventsCard } from '../../components/eval/PeakEventsCard';
import { MODEL_LABELS, ModelId } from '../../constants/models';

const SEGMENTS = [
  { id: 'all', label: 'All days' },
  { id: 'winter', label: 'Winter' },
  { id: 'summer', label: 'Summer' },
  { id: 'monsoon', label: 'Monsoon' },
  { id: 'post_monsoon', label: 'Post-monsoon' },
  { id: 'peak_hours', label: 'Peak hours' },
  { id: 'off_peak', label: 'Off-peak' },
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

  const metricLabel = selectedMetric === 'mape' ? 'MAPE %' : selectedMetric === 'rmse_mw' ? 'RMSE MW' : 'MAE MW';

  const improvementRows = useMemo(() => {
    if (!metricsData) return [];
    const models = ['xgboost', 'lgbm', 'ensemble'];
    const baselineRow = metricsData.rows.find(
      (r) => r.model === 'seasonal_naive' && r.segment === selectedSegment && String(r.horizon_day) === '1'
    );
    const baseVal = baselineRow ? baselineRow[selectedMetric] : 0;

    return models.map((m) => {
      const row = metricsData.rows.find(
        (r) => r.model === m && r.segment === selectedSegment && String(r.horizon_day) === '1'
      );
      const val = row ? row[selectedMetric] : 0;
      let imp = 0;
      if (baseVal > 0 && val > 0) {
        imp = ((val - baseVal) / baseVal) * 100;
      }
      return {
        model: m,
        label: MODEL_LABELS[m as ModelId] || m,
        improvement: `${imp > 0 ? '+' : ''}${Math.round(imp)}%`,
      };
    });
  }, [metricsData, selectedSegment, selectedMetric]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Accuracy
        </h1>

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Segment
            </label>
            <select
              value={selectedSegment}
              onChange={(e) => setSelectedSegment(e.target.value)}
              className="bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer min-w-[160px]"
            >
              {SEGMENTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setSelectedMetric('mape')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === 'mape'
                  ? 'bg-[#1d4ed8] text-white shadow-sm'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              MAPE
            </button>
            <button
              type="button"
              onClick={() => setSelectedMetric('mae_mw')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === 'mae_mw'
                  ? 'bg-[#1d4ed8] text-white shadow-sm'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              MAE
            </button>
            <button
              type="button"
              onClick={() => setSelectedMetric('rmse_mw')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedMetric === 'rmse_mw'
                  ? 'bg-[#1d4ed8] text-white shadow-sm'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              RMSE
            </button>
          </div>
        </div>
      </div>

      <ChartCard
        title={`Accuracy by horizon (${metricLabel})`}
        loading={loading}
        error={error}
        empty={!metricsData || metricsData.rows.length === 0}
      >
        {metricsData && (
          <AccuracyTable
            rows={metricsData.rows}
            metric={selectedMetric}
            selectedSegment={selectedSegment}
          />
        )}
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4">
            Improvement over seasonal-naive
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Model</th>
                  <th className="py-2.5 px-3 text-right">vs naive</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {improvementRows.map((row) => (
                  <tr key={row.model} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-medium text-slate-900">{row.label}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700 font-medium">
                      {row.improvement}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-4">Calibration</h3>
          {metricsData && <CalibrationTable rows={metricsData.rows} />}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-1">Peak events</h3>
          {peakMetricsData && <PeakEventsCard rows={peakMetricsData.rows} />}
        </div>
      </div>
    </div>
  );
};
