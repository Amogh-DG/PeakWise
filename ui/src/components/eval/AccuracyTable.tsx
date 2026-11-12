import React, { useState, useMemo } from 'react';
import { AccuracyMetricRow } from '../../api/types';
import { BASELINE_MODEL, MODEL_LABELS, ModelId } from '../../constants/models';

export type MetricType = 'mape' | 'rmse_mw' | 'mae_mw' | 'bias_mw' | 'pinball';

interface AccuracyTableProps {
  rows: AccuracyMetricRow[];
  metric: MetricType;
  selectedSegment: string;
}

const HORIZONS: (number | string)[] = [1, 2, 3, 4, 5, 6, 7, 'all'];

export const AccuracyTable: React.FC<AccuracyTableProps> = ({
  rows,
  metric,
  selectedSegment,
}) => {
  const [sortHorizon, setSortHorizon] = useState<number | string>('all');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const filteredRows = useMemo(() => {
    return rows.filter((r) => r.segment === selectedSegment);
  }, [rows, selectedSegment]);

  const models = useMemo(() => {
    const set = new Set<string>();
    filteredRows.forEach((r) => set.add(r.model));
    return Array.from(set);
  }, [filteredRows]);

  const gridData = useMemo(() => {
    const map: Record<string, Record<string | number, AccuracyMetricRow>> = {};
    for (const row of filteredRows) {
      if (!map[row.model]) {
        map[row.model] = {};
      }
      map[row.model][row.horizon_day] = row;
    }
    return map;
  }, [filteredRows]);

  const bestPerColumn = useMemo(() => {
    const best: Record<string | number, number> = {};
    for (const h of HORIZONS) {
      let minVal: number | null = null;
      for (const m of models) {
        const row = gridData[m]?.[h];
        if (!row) continue;
        const val = row[metric];
        const compareVal = metric === 'bias_mw' ? Math.abs(val) : val;
        if (minVal === null || compareVal < minVal) {
          minVal = compareVal;
        }
      }
      if (minVal !== null) {
        best[h] = minVal;
      }
    }
    return best;
  }, [gridData, models, metric]);

  const sortedModels = useMemo(() => {
    return [...models].sort((a, b) => {
      const rowA = gridData[a]?.[sortHorizon];
      const rowB = gridData[b]?.[sortHorizon];

      if (!rowA && !rowB) return 0;
      if (!rowA) return 1;
      if (!rowB) return -1;

      const valA = metric === 'bias_mw' ? Math.abs(rowA[metric]) : rowA[metric];
      const valB = metric === 'bias_mw' ? Math.abs(rowB[metric]) : rowB[metric];

      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
  }, [models, gridData, sortHorizon, sortDirection, metric]);

  const handleHeaderClick = (h: number | string) => {
    if (sortHorizon === h) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortHorizon(h);
      setSortDirection('asc');
    }
  };

  const formatMetricValue = (val: number, met: MetricType) => {
    if (met === 'mape') return `${val.toFixed(2)}%`;
    if (met === 'rmse_mw' || met === 'mae_mw') return `${val.toFixed(1)} MW`;
    if (met === 'bias_mw') return `${val > 0 ? '+' : ''}${val.toFixed(1)} MW`;
    return val.toFixed(2);
  };

  const getImprovement = (
    row: AccuracyMetricRow | undefined,
    baselineRow: AccuracyMetricRow | undefined,
    met: MetricType
  ): { value: number | null; label: string; isPositive: boolean } => {
    if (!row) return { value: null, label: '—', isPositive: false };
    if (row.model === BASELINE_MODEL) {
      return { value: null, label: '—', isPositive: false };
    }

    if (met === 'mape' && row.improvement_mape_pct !== null && row.improvement_mape_pct !== undefined) {
      return {
        value: row.improvement_mape_pct,
        label: `${row.improvement_mape_pct > 0 ? '+' : ''}${row.improvement_mape_pct.toFixed(1)}%`,
        isPositive: row.improvement_mape_pct > 0,
      };
    }
    if (met === 'rmse_mw' && row.improvement_rmse_pct !== null && row.improvement_rmse_pct !== undefined) {
      return {
        value: row.improvement_rmse_pct,
        label: `${row.improvement_rmse_pct > 0 ? '+' : ''}${row.improvement_rmse_pct.toFixed(1)}%`,
        isPositive: row.improvement_rmse_pct > 0,
      };
    }

    if (baselineRow && baselineRow[met] !== 0) {
      const baseVal = metric === 'bias_mw' ? Math.abs(baselineRow[met]) : baselineRow[met];
      const modelVal = metric === 'bias_mw' ? Math.abs(row[met]) : row[met];
      const imp = ((baseVal - modelVal) / baseVal) * 100;
      return {
        value: imp,
        label: `${imp > 0 ? '+' : ''}${imp.toFixed(1)}%`,
        isPositive: imp > 0,
      };
    }

    return { value: null, label: '—', isPositive: false };
  };

  if (filteredRows.length === 0) {
    return (
      <div className="py-12 text-center text-xs text-brand-muted">
        No accuracy metrics found for the selected segment ({selectedSegment}).
      </div>
    );
  }

  return (
    <div className="relative overflow-x-auto border border-brand-border rounded-lg shadow-sm">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-brand-bg text-brand-muted uppercase tracking-wider text-[11px] font-semibold sticky top-0 z-20 border-b border-brand-border">
          <tr>
            <th className="py-3 px-4 sticky left-0 bg-brand-bg z-30 min-w-[180px] shadow-[2px_0_4px_rgba(0,0,0,0.15)]">
              Model
            </th>
            {HORIZONS.map((h) => {
              const isSorted = sortHorizon === h;
              return (
                <th
                  key={String(h)}
                  onClick={() => handleHeaderClick(h)}
                  className={`py-3 px-3 cursor-pointer select-none text-right transition-colors hover:text-brand-text min-w-[125px] ${
                    isSorted ? 'text-brand-accent font-bold bg-brand-surface/40' : ''
                  }`}
                >
                  <div className="flex items-center justify-end space-x-1">
                    <span>{h === 'all' ? 'Horizon All' : `D+${h}`}</span>
                    {isSorted && (
                      <span className="text-brand-accent">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-border/40 font-mono">
          {sortedModels.map((modelName) => {
            const isBaseline = modelName === BASELINE_MODEL;
            const modelLabel =
              MODEL_LABELS[modelName as ModelId] || modelName;

            return (
              <tr
                key={modelName}
                className={`transition-colors hover:bg-brand-surface/70 ${
                  isBaseline ? 'bg-brand-bg/30 text-brand-muted' : ''
                }`}
              >
                <td className="py-2.5 px-4 sticky left-0 bg-brand-surface z-10 font-sans font-medium text-brand-text whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.15)]">
                  <div className="flex items-center space-x-2">
                    <span className="truncate">{modelLabel}</span>
                    {isBaseline && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-bg border border-brand-border font-mono text-brand-muted uppercase">
                        Base
                      </span>
                    )}
                  </div>
                </td>
                {HORIZONS.map((h) => {
                  const cellRow = gridData[modelName]?.[h];
                  const baselineRow = gridData[BASELINE_MODEL]?.[h];
                  if (!cellRow) {
                    return (
                      <td key={String(h)} className="py-2.5 px-3 text-right text-brand-muted/40">
                        —
                      </td>
                    );
                  }

                  const rawVal = cellRow[metric];
                  const compareVal = metric === 'bias_mw' ? Math.abs(rawVal) : rawVal;
                  const isBest =
                    bestPerColumn[h] !== undefined &&
                    Math.abs(compareVal - bestPerColumn[h]) < 1e-4;

                  const imp = getImprovement(cellRow, baselineRow, metric);

                  return (
                    <td
                      key={String(h)}
                      className={`py-2.5 px-3 text-right ${
                        isBest ? 'bg-emerald-950/20' : ''
                      }`}
                    >
                      <div className="flex flex-col items-end">
                        <span
                          className={`font-semibold ${
                            isBest
                              ? 'text-emerald-400 font-bold'
                              : isBaseline
                              ? 'text-brand-muted'
                              : 'text-brand-text'
                          }`}
                        >
                          {formatMetricValue(rawVal, metric)}
                        </span>
                        {!isBaseline && imp.value !== null && (
                          <span
                            className={`text-[10px] font-medium ${
                              imp.isPositive
                                ? 'text-emerald-400/90'
                                : 'text-red-400/90'
                            }`}
                          >
                            {imp.label}
                          </span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

