import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { ProcurementSchedulePoint } from '../../api/types';

interface ScheduleChartProps {
  schedule: ProcurementSchedulePoint[];
  atRiskHours: string[];
}

export const ScheduleChart: React.FC<ScheduleChartProps> = ({
  schedule,
  atRiskHours,
}) => {
  const atRiskSet = useMemo(() => new Set(atRiskHours), [atRiskHours]);

  const {
    timestamps,
    scheduledMw,
    p50Mw,
    p90Mw,
    flatMw,
    actualMw,
    hasActual,
    atRiskX,
    atRiskY,
  } = useMemo(() => {
    const ts: string[] = [];
    const sched: number[] = [];
    const p50: number[] = [];
    const p90: number[] = [];
    const flat: number[] = [];
    const actual: (number | null)[] = [];
    const arX: string[] = [];
    const arY: number[] = [];
    let foundActual = false;

    for (const pt of schedule) {
      ts.push(pt.ts);
      sched.push(pt.scheduled_mw);
      p50.push(pt.p50_mw);
      p90.push(pt.p90_mw);
      flat.push(pt.flat_mw);
      actual.push(pt.actual_mw);
      if (pt.actual_mw !== null && pt.actual_mw !== undefined) {
        foundActual = true;
      }
      if (atRiskSet.has(pt.ts)) {
        arX.push(pt.ts);
        arY.push(pt.p90_mw);
      }
    }

    return {
      timestamps: ts,
      scheduledMw: sched,
      p50Mw: p50,
      p90Mw: p90,
      flatMw: flat,
      actualMw: actual,
      hasActual: foundActual,
      atRiskX: arX,
      atRiskY: arY,
    };
  }, [schedule, atRiskSet]);

  const plotData = useMemo(() => {
    const traces: any[] = [
      {
        type: 'scatter',
        mode: 'lines',
        name: 'P50 Forecast',
        x: timestamps,
        y: p50Mw,
        line: { color: '#38bdf8', width: 1.5, dash: 'dash' },
        hovertemplate: 'P50: <b>%{y:.1f} MW</b><extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'P90 Risk Upper',
        x: timestamps,
        y: p90Mw,
        line: { color: '#f59e0b', width: 1.5, dash: 'dash' },
        hovertemplate: 'P90: <b>%{y:.1f} MW</b><extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Flat Baseline',
        x: timestamps,
        y: flatMw,
        line: { color: '#a855f7', width: 1.5, dash: 'dot' },
        hovertemplate: 'Flat Baseline: <b>%{y:.1f} MW</b><extra></extra>',
      },
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Scheduled MW',
        x: timestamps,
        y: scheduledMw,
        line: { color: '#3b82f6', width: 2.5 },
        hovertemplate: 'Scheduled: <b>%{y:.1f} MW</b><extra></extra>',
      },
    ];

    if (hasActual) {
      traces.push({
        type: 'scatter',
        mode: 'lines',
        name: 'Actual Demand',
        x: timestamps,
        y: actualMw,
        line: { color: '#10b981', width: 2 },
        connectgaps: false,
        hovertemplate: 'Actual: <b>%{y:.1f} MW</b><extra></extra>',
      });
    }

    if (atRiskX.length > 0) {
      traces.push({
        type: 'scatter',
        mode: 'markers',
        name: 'At-Risk Peak (P90 ≥ Peak)',
        x: atRiskX,
        y: atRiskY,
        marker: { symbol: 'triangle-up', size: 9, color: '#ef4444' },
        hovertemplate: 'At-Risk Hour: <b>%{x}</b><br>P90: <b>%{y:.1f} MW</b><extra></extra>',
      });
    }

    return traces;
  }, [timestamps, scheduledMw, p50Mw, p90Mw, flatMw, actualMw, hasActual, atRiskX, atRiskY]);

  const layout = useMemo(() => {
    return {
      xaxis: {
        title: { text: 'Time (IST)', font: { size: 12, color: '#9ca3af' } },
        showgrid: true,
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      yaxis: {
        title: { text: 'Power (MW)', font: { size: 12, color: '#9ca3af' } },
        showgrid: true,
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      legend: {
        orientation: 'h',
        y: 1.15,
        x: 0,
        font: { family: 'Plus Jakarta Sans, sans-serif', size: 11, color: '#9ca3af' },
      },
      margin: { t: 40, r: 20, b: 45, l: 60 },
      hovermode: 'x unified',
    };
  }, []);

  return (
    <div className="w-full h-[400px]">
      <PlotlyChart data={plotData} layout={layout} />
    </div>
  );
};
