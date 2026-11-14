import React, { useMemo } from 'react';
import { AccuracyMetricRow } from '../../api/types';
import { MODEL_LABELS, ModelId } from '../../constants/models';

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
  const filteredRows = useMemo(() => {
    return rows.filter((r) => r.segment === selectedSegment);
  }, [rows, selectedSegment]);

  const models = useMemo(() => {
    const list: string[] = ['seasonal_naive', 'xgboost', 'lgbm', 'ensemble'];
    const available = new Set(filteredRows.map((r) => r.model));
    const sorted = list.filter((m) => available.has(m));
    available.forEach((m) => {
      if (!sorted.includes(m)) sorted.push(m);
    });
    return sorted;
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

  const formatValue = (val: number | undefined) => {
    if (val === undefined || val === null) return '—';
    return val.toFixed(1);
  };

  if (filteredRows.length === 0) {
    return (
      <div className="py-12 text-center text-xs text-slate-500">
        No accuracy metrics found for the selected segment ({selectedSegment}).
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm border-collapse">
        <thead className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
          <tr>
            <th className="py-3 px-3 min-w-[160px]">Model</th>
            <th className="py-3 px-3 text-right">D+1</th>
            <th className="py-3 px-3 text-right">D+2</th>
            <th className="py-3 px-3 text-right">D+3</th>
            <th className="py-3 px-3 text-right">D+4</th>
            <th className="py-3 px-3 text-right">D+5</th>
            <th className="py-3 px-3 text-right">D+6</th>
            <th className="py-3 px-3 text-right">D+7</th>
            <th className="py-3 px-3 text-right">Overall</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-slate-800">
          {models.map((modelName) => {
            const label = MODEL_LABELS[modelName as ModelId] || modelName;
            return (
              <tr key={modelName} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 px-3 font-medium text-slate-900">{label}</td>
                {HORIZONS.map((h) => {
                  const cell = gridData[modelName]?.[h];
                  const val = cell ? cell[metric] : undefined;
                  return (
                    <td key={String(h)} className="py-3 px-3 text-right text-slate-700 font-normal">
                      {formatValue(val)}
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
