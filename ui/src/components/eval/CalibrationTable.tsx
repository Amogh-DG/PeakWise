import React, { useState, useMemo } from 'react';
import { AccuracyMetricRow } from '../../api/types';
import { MODEL_LABELS, ModelId } from '../../constants/models';

interface CalibrationTableProps {
  rows: AccuracyMetricRow[];
  calibrationComparison?: unknown;
}

export const CalibrationTable: React.FC<CalibrationTableProps> = ({
  rows,
  calibrationComparison,
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<number | string>('1');

  const horizonRows = useMemo(() => {
    return rows.filter(
      (r) =>
        r.segment === 'all' &&
        String(r.horizon_day) === String(selectedHorizon)
    );
  }, [rows, selectedHorizon]);

  const renderCoverageBar = (val: number, target: number) => {
    const pct = Math.min(Math.max(val * 100, 0), 100);
    const targetPct = target * 100;
    const diff = Math.abs(val - target);
    const isGood = diff <= 0.04;
    const isUnder = val < target - 0.04;

    const barColor = isGood
      ? 'bg-emerald-500'
      : isUnder
      ? 'bg-amber-500'
      : 'bg-blue-500';

    return (
      <div className="flex items-center space-x-2 min-w-[140px]">
        <div className="flex-1 bg-brand-bg rounded-full h-2 relative border border-brand-border/60 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-brand-text z-10 opacity-70"
            style={{ left: `${targetPct}%` }}
            title={`Target: ${targetPct}%`}
          />
        </div>
        <span
          className={`font-mono text-xs w-12 text-right ${
            isGood ? 'text-emerald-400 font-semibold' : 'text-brand-text'
          }`}
        >
          {(val * 100).toFixed(1)}%
        </span>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-brand-bg/40 p-3.5 rounded-lg border border-brand-border">
        <div className="flex items-center space-x-4 text-xs text-brand-muted">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-band-p10_p90 border border-brand-accent/50 inline-block" />
            <span className="text-brand-text font-medium">P10 to P90 = 80% interval</span>
            <span className="text-[11px] font-mono text-brand-muted">(Nominal target: 80.0%)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-band-p05_p95 border border-brand-accent/30 inline-block" />
            <span className="text-brand-text font-medium">P05 to P95 = 90% interval</span>
            <span className="text-[11px] font-mono text-brand-muted">(Nominal target: 90.0%)</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-brand-muted">Horizon:</span>
          <div className="flex bg-brand-surface border border-brand-border rounded-lg p-0.5">
            {['1', '2', '3', '4', '5', '6', '7', 'all'].map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => setSelectedHorizon(h)}
                className={`px-2 py-1 text-xs rounded font-mono transition-colors ${
                  String(selectedHorizon) === h
                    ? 'bg-brand-accent text-brand-bg font-bold'
                    : 'text-brand-muted hover:text-brand-text'
                }`}
              >
                {h === 'all' ? 'All' : `D+${h}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto border border-brand-border rounded-lg shadow-sm">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-brand-bg text-brand-muted uppercase tracking-wider text-[11px] font-semibold border-b border-brand-border">
            <tr>
              <th className="py-3 px-4">Model</th>
              <th className="py-3 px-4 text-left">
                <span>PICP 80% (P10–P90)</span>
                <span className="block text-[10px] lowercase font-normal text-brand-muted">
                  target = 80.0%
                </span>
              </th>
              <th className="py-3 px-4 text-left">
                <span>PICP 90% (P05–P95)</span>
                <span className="block text-[10px] lowercase font-normal text-brand-muted">
                  target = 90.0%
                </span>
              </th>
              <th className="py-3 px-4 text-right">
                <span>MPIW 80%</span>
                <span className="block text-[10px] lowercase font-normal text-brand-muted">
                  mean interval width (MW)
                </span>
              </th>
              <th className="py-3 px-4 text-right">Sample Count</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-border/40 font-mono">
            {horizonRows.map((row) => {
              const label =
                MODEL_LABELS[row.model as ModelId] || row.model;

              return (
                <tr
                  key={`${row.model}-${row.horizon_day}`}
                  className="hover:bg-brand-surface/60 transition-colors"
                >
                  <td className="py-3 px-4 font-sans font-medium text-brand-text whitespace-nowrap">
                    {label}
                  </td>
                  <td className="py-3 px-4">
                    {renderCoverageBar(row.picp_80, 0.8)}
                  </td>
                  <td className="py-3 px-4">
                    {renderCoverageBar(row.picp_90, 0.9)}
                  </td>
                  <td className="py-3 px-4 text-right text-brand-text font-semibold">
                    {row.mpiw_80_mw.toFixed(1)} MW
                  </td>
                  <td className="py-3 px-4 text-right text-brand-muted">
                    {row.n.toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {calibrationComparison !== undefined && calibrationComparison !== null && (
        <div className="mt-4 bg-brand-surface border border-brand-border rounded-xl p-4">
          <h4 className="text-xs font-semibold text-brand-text uppercase tracking-wider mb-2">
            Calibration Adjustment Comparison (Raw vs Conformalized)
          </h4>
          <pre className="text-[11px] font-mono bg-brand-bg p-3 rounded text-brand-muted overflow-x-auto">
            {JSON.stringify(calibrationComparison, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

