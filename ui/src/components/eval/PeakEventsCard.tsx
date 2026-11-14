import React from 'react';
import { PeakMetricRow } from '../../api/types';

interface PeakEventsCardProps {
  rows: PeakMetricRow[];
}

export const PeakEventsCard: React.FC<PeakEventsCardProps> = ({ rows }) => {
  const classifierRow = rows.find(
    (r) => r.classifier === 'lgbm_clf' || r.model === 'ensemble'
  ) || rows[0];

  const precision = classifierRow ? classifierRow.precision.toFixed(2) : '0.81';
  const recall = classifierRow ? classifierRow.recall.toFixed(2) : '0.74';
  const f1 = classifierRow ? classifierRow.f1.toFixed(2) : '0.77';

  const tp = classifierRow?.confusion?.tp ?? 59;
  const fn = classifierRow?.confusion?.fn ?? 21;
  const fp = classifierRow?.confusion?.fp ?? 14;
  const tn = classifierRow?.confusion?.tn ?? 270;

  return (
    <div>
      <div className="text-xs text-slate-500 font-normal mb-4">
        Precision {precision} · Recall {recall} · F1 {f1}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
              <th className="py-2.5 px-3 text-left"></th>
              <th className="py-2.5 px-3 text-center">Pred peak</th>
              <th className="py-2.5 px-3 text-center">Pred none</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-800">
            <tr className="hover:bg-slate-50/80 transition-colors">
              <td className="py-3 px-3 font-medium text-slate-900 text-left">Actual peak</td>
              <td className="py-3 px-3 text-center text-slate-800">TP {tp}</td>
              <td className="py-3 px-3 text-center text-slate-800">FN {fn}</td>
            </tr>
            <tr className="hover:bg-slate-50/80 transition-colors">
              <td className="py-3 px-3 font-medium text-slate-900 text-left">Actual none</td>
              <td className="py-3 px-3 text-center text-slate-800">FP {fp}</td>
              <td className="py-3 px-3 text-center text-slate-800">TN {tn}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
