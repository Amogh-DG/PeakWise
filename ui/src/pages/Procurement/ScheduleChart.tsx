import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { ProcurementSchedulePoint } from '../../api/types';

interface ScheduleChartProps {
  schedule: ProcurementSchedulePoint[];
}

const DAYS_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const ScheduleChart: React.FC<ScheduleChartProps> = ({ schedule }) => {
  const { baseVals, peakVals } = useMemo(() => {
    const dayMap: Record<string, { base: number; peak: number }> = {
      Mon: { base: 260, peak: 40 },
      Tue: { base: 280, peak: 45 },
      Wed: { base: 270, peak: 38 },
      Thu: { base: 295, peak: 48 },
      Fri: { base: 285, peak: 42 },
      Sat: { base: 230, peak: 32 },
      Sun: { base: 215, peak: 35 },
    };

    if (schedule && schedule.length > 0) {
      const counts: Record<string, { baseSum: number; peakSum: number; count: number }> = {};
      schedule.forEach((pt) => {
        const dt = new Date(pt.ts);
        const dayName = dt.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'Asia/Kolkata' });
        if (!counts[dayName]) counts[dayName] = { baseSum: 0, peakSum: 0, count: 0 };
        const hour = dt.getHours();
        const isPeak = (hour >= 6 && hour <= 10) || (hour >= 18 && hour <= 23);
        if (isPeak) {
          counts[dayName].peakSum += pt.scheduled_mw;
        } else {
          counts[dayName].baseSum += pt.scheduled_mw;
        }
        counts[dayName].count += 1;
      });

      DAYS_ORDER.forEach((d) => {
        if (counts[d] && counts[d].count > 0) {
          dayMap[d] = {
            base: Math.round(counts[d].baseSum / (counts[d].count / 24)),
            peak: Math.round(counts[d].peakSum / (counts[d].count / 24)),
          };
        }
      });
    }

    return {
      baseVals: DAYS_ORDER.map((d) => dayMap[d].base),
      peakVals: DAYS_ORDER.map((d) => dayMap[d].peak),
    };
  }, [schedule]);

  const plotData = useMemo(() => {
    return [
      {
        x: DAYS_ORDER,
        y: baseVals,
        name: 'Off-Peak Volume',
        type: 'bar',
        marker: { color: '#4a7cd0' },
      },
      {
        x: DAYS_ORDER,
        y: peakVals,
        name: 'Peak Volume',
        type: 'bar',
        marker: { color: '#bd5e2d' },
      },
    ];
  }, [baseVals, peakVals]);

  const layout = useMemo(() => {
    return {
      barmode: 'stack',
      showlegend: false,
      margin: { t: 20, r: 20, b: 35, l: 30 },
      xaxis: {
        gridcolor: 'transparent',
        tickfont: { size: 11, color: '#64748b' },
      },
      yaxis: {
        showticklabels: false,
        showgrid: false,
        zeroline: false,
      },
    };
  }, []);

  return (
    <div className="w-full h-[260px]">
      <PlotlyChart data={plotData} layout={layout} />
    </div>
  );
};
