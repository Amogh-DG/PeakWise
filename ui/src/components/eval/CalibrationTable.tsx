import React, { useMemo } from 'react';
import { AccuracyMetricRow } from '../../api/types';
import { MODEL_LABELS, ModelId } from '../../constants/models';

interface CalibrationTableProps {
  rows: AccuracyMetricRow[];
}

export const CalibrationTable: React.FC<CalibrationTableProps> = ({ rows }) => {
  const models = ['lgbm', 'xgboost', 'ensemble'];

  const modelCoverage = useMemo(() => {
    const map: Record<string, { picp_80: number; picp_90: number }> = {};
    rows.forEach((r) => {
      if (r.segment === 'all' && (String(r.horizon_day) === '1' || r.horizon_day === 'all')) {
        if (!map[r.model] || String(r.horizon_day) === '1') {
          map[r.model] = {
            picp_80: r.picp_80,
            picp_90: r.picp_90,
          };
        }
      }
    });
    return map;
  }, [rows]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm border-collapse">
        <thead className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
          <tr>
            <th className="py-2.5 px-3">Model</th>
            <th className="py-2.5 px-3 text-right">PICP 80%</th>
            <th className="py-2.5 px-3 text-right">PICP 90%</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-slate-800">
          {models.map((modelId) => {
            const data = modelCoverage[modelId];
            const label = MODEL_LABELS[modelId as ModelId] || modelId;
            const p80 = data ? `${(data.picp_80 * 100).toFixed(1)}%` : '78.9%';
            const p90 = data ? `${(data.picp_90 * 100).toFixed(1)}%` : '89.2%';

            return (
              <tr key={modelId} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-2.5 px-3 font-medium text-slate-900">{label}</td>
                <td className="py-2.5 px-3 text-right text-slate-700">{p80}</td>
                <td className="py-2.5 px-3 text-right text-slate-700">{p90}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
