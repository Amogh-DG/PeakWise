import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { DayAheadForecastResponse } from '../../api/types';
import { CHART_THEME } from '../../constants/theme';

interface CompactDayChartProps {
  data: DayAheadForecastResponse;
}

export const CompactDayChart: React.FC<CompactDayChartProps> = ({ data }) => {
  const { points, peak, peak_threshold_mw } = data;

  const chartTraces = useMemo(() => {
    if (!points || points.length === 0) return [];

    const xVals = points.map((p) => p.ts);
    const p05Vals = points.map((p) => p.p05);
    const p10Vals = points.map((p) => p.p10);
    const p50Vals = points.map((p) => p.p50);
    const p90Vals = points.map((p) => p.p90);
    const p95Vals = points.map((p) => p.p95);
    const actualVals = points.map((p) => p.actual);

    const traces: any[] = [
      {
        name: 'P95 Upper',
        x: xVals,
        y: p95Vals,
        type: 'scatter',
        mode: 'lines',
        line: { color: 'transparent', width: 0 },
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        name: 'P05–P95 (90% Interval)',
        x: xVals,
        y: p05Vals,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: CHART_THEME.bandP05P95,
        line: { color: 'transparent', width: 0 },
        hoverinfo: 'skip',
      },
      {
        name: 'P90 Upper',
        x: xVals,
        y: p90Vals,
        type: 'scatter',
        mode: 'lines',
        line: { color: 'transparent', width: 0 },
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        name: 'P10–P90 (80% Interval)',
        x: xVals,
        y: p10Vals,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: CHART_THEME.bandP10P90,
        line: { color: 'transparent', width: 0 },
        hoverinfo: 'skip',
      },
      {
        name: 'P50 Forecast',
        x: xVals,
        y: p50Vals,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#38bdf8', width: 2 },
      },
    ];

    const hasActuals = points.some((p) => p.actual !== null);
    if (hasActuals) {
      traces.push({
        name: 'Actual Demand',
        x: xVals,
        y: actualVals,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#f8fafc', width: 2 },
        marker: { size: 4, color: '#f8fafc' },
      });
    }

    if (peak_threshold_mw) {
      traces.push({
        name: 'Peak Threshold',
        x: xVals,
        y: xVals.map(() => peak_threshold_mw),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#ef4444', width: 1.5, dash: 'dot' },
      });
    }

    if (peak?.predicted_peak_ts && peak.predicted_peak_mw?.p50) {
      traces.push({
        name: 'Pred Peak',
        x: [peak.predicted_peak_ts],
        y: [peak.predicted_peak_mw.p50],
        type: 'scatter',
        mode: 'markers',
        marker: {
          symbol: 'diamond',
          size: 11,
          color: '#38bdf8',
          line: { color: '#ffffff', width: 1.5 },
        },
      });
    }

    if (peak?.actual_peak_ts && peak.actual_peak_mw) {
      traces.push({
        name: 'Actual Peak',
        x: [peak.actual_peak_ts],
        y: [peak.actual_peak_mw],
        type: 'scatter',
        mode: 'markers',
        marker: {
          symbol: 'star',
          size: 13,
          color: '#f59e0b',
          line: { color: '#ffffff', width: 1.5 },
        },
      });
    }

    return traces;
  }, [points, peak, peak_threshold_mw]);

  const layout = useMemo(() => {
    return {
      margin: { t: 15, r: 15, b: 35, l: 45 },
      legend: {
        orientation: 'h',
        x: 0,
        y: 1.15,
        font: { size: 10, color: CHART_THEME.mutedColor },
      },
      xaxis: {
        tickformat: '%H:%M',
        dtick: 3 * 3600 * 1000,
      },
      yaxis: {
        title: { text: 'MW', font: { size: 10 } },
      },
    };
  }, []);

  return (
    <div className="w-full h-64">
      <PlotlyChart data={chartTraces} layout={layout} />
    </div>
  );
};

