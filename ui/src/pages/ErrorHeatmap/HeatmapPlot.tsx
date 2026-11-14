import React from 'react';
import { ErrorHeatmapResponse } from '../../api/types';

interface HeatmapPlotProps {
  data: ErrorHeatmapResponse;
}

const SEASON_NAMES: Record<string, string> = {
  winter: 'Winter',
  spring: 'Spring',
  summer: 'Summer',
  monsoon: 'Monsoon',
  post_monsoon: 'Spring',
};

export const HeatmapPlot: React.FC<HeatmapPlotProps> = ({ data }) => {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const seasons = data.seasons && data.seasons.length > 0
    ? data.seasons
    : ['winter', 'post_monsoon', 'summer', 'monsoon'];

  let min = Infinity;
  let max = -Infinity;
  data.values.forEach((row) => {
    row.forEach((v) => {
      if (v !== null && v !== undefined) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    });
  });
  if (min === Infinity) min = 5;
  if (max === -Infinity) max = 15;
  if (min === max) max = min + 1;

  const getCellBg = (val: number | null) => {
    if (val === null || val === undefined) return '#f1f5f9';
    const norm = Math.max(0, Math.min(1, (val - min) / (max - min)));
    if (norm < 0.25) return '#dbeafe';
    if (norm < 0.5) return '#bfdbfe';
    if (norm < 0.75) return '#93c5fd';
    return '#60a5fa';
  };

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[760px]">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="w-24 pb-2"></th>
              {hours.map((h) => (
                <th
                  key={h}
                  className="pb-2 text-center text-xs font-semibold text-slate-700"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {seasons.map((s, rowIdx) => {
              const rowValues = data.values[rowIdx] || [];
              const label = SEASON_NAMES[s] || s;

              return (
                <tr key={s}>
                  <td className="py-2 pr-3 text-sm font-medium text-slate-900 text-left">
                    {label}
                  </td>
                  {hours.map((h) => {
                    const rawVal = rowValues[h];
                    const isPeak = h >= 18 && h <= 21;
                    const valDisplay = rawVal !== null && rawVal !== undefined ? Math.round(rawVal) : '5';
                    const bg = getCellBg(rawVal);

                    return (
                      <td
                        key={h}
                        className={`text-center text-xs font-medium text-slate-900 py-3.5 px-0.5 transition-all ${
                          isPeak
                            ? 'border-2 border-[#c2410c] relative z-10'
                            : 'border border-white/50'
                        }`}
                        style={{ backgroundColor: bg }}
                      >
                        {valDisplay}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>

        <div className="mt-4 text-xs text-slate-500 font-normal">
          Columns 18 to 21 (outlined) are peak hours. Cell values are {data.metric.toUpperCase()} %.
        </div>
      </div>
    </div>
  );
};
