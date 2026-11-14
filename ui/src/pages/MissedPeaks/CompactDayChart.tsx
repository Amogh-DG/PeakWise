import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { DayAheadForecastResponse } from '../../api/types';

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
    const actualPoints = points.filter((p) => p.actual !== null);

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
        name: 'P05–P95',
        x: xVals,
        y: p05Vals,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: 'rgba(219, 234, 254, 0.45)',
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
        name: 'P10–P90',
        x: xVals,
        y: p10Vals,
        type: 'scatter',
        mode: 'lines',
        fill: 'tonexty',
        fillcolor: 'rgba(147, 197, 253, 0.55)',
        line: { color: 'transparent', width: 0 },
        hoverinfo: 'skip',
      },
      {
        name: 'P50 Forecast',
        x: xVals,
        y: p50Vals,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#2563eb', width: 2, dash: 'dash' },
      },
    ];

    if (actualPoints.length > 0) {
      traces.push({
        name: 'Actual Demand',
        x: actualPoints.map((p) => p.ts),
        y: actualPoints.map((p) => p.actual),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#0f172a', width: 2.2 },
      });
    }

    if (peak) {
      traces.push({
        name: 'Predicted Peak',
        x: [peak.predicted_peak_ts],
        y: [peak.predicted_peak_mw.p50],
        type: 'scatter',
        mode: 'markers',
        marker: { symbol: 'diamond', size: 9, color: '#0f172a' },
      });

      if (peak.actual_peak_ts && peak.actual_peak_mw !== null) {
        traces.push({
          name: 'Actual Peak',
          x: [peak.actual_peak_ts],
          y: [peak.actual_peak_mw],
          type: 'scatter',
          mode: 'markers',
          marker: { symbol: 'circle', size: 9, color: '#c2410c' },
        });
      }
    }

    return traces;
  }, [points, peak]);

  const atRiskRanges = useMemo(() => {
    if (!points || points.length === 0) return [];
    const ranges: Array<{ start: string; end: string }> = [];
    let currentStart: string | null = null;
    let prevTs: string | null = null;

    points.forEach((p) => {
      if (p.at_risk) {
        if (!currentStart) currentStart = p.ts;
        prevTs = p.ts;
      } else {
        if (currentStart && prevTs) {
          ranges.push({ start: currentStart, end: prevTs });
          currentStart = null;
          prevTs = null;
        }
      }
    });

    if (currentStart && prevTs) {
      ranges.push({ start: currentStart, end: prevTs });
    }

    return ranges;
  }, [points]);

  const layout = useMemo(() => {
    const shapes: any[] = [];
    const annotations: any[] = [];

    atRiskRanges.forEach((range, idx) => {
      shapes.push({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: range.start,
        x1: range.end,
        y0: 0,
        y1: 1,
        fillcolor: 'rgba(255, 237, 213, 0.7)',
        line: { width: 0 },
        layer: 'below',
      });

      if (idx === 0) {
        annotations.push({
          x: range.start,
          y: 0.95,
          xref: 'x',
          yref: 'paper',
          text: 'At-risk hours',
          showarrow: false,
          font: { size: 9, color: '#9a3412', family: 'system-ui, sans-serif' },
          xanchor: 'left',
        });
      }
    });

    if (peak_threshold_mw && points && points.length > 0) {
      shapes.push({
        type: 'line',
        xref: 'paper',
        yref: 'y',
        x0: 0,
        x1: 1,
        y0: peak_threshold_mw,
        y1: peak_threshold_mw,
        line: { color: '#c2410c', width: 1.5, dash: 'dot' },
      });

      annotations.push({
        xref: 'paper',
        yref: 'y',
        x: 0.01,
        y: peak_threshold_mw,
        text: 'Peak threshold',
        showarrow: false,
        font: { size: 9, color: '#c2410c', family: 'system-ui, sans-serif' },
        yshift: 8,
        xanchor: 'left',
      });
    }

    annotations.push({
      xref: 'paper',
      yref: 'paper',
      x: -0.01,
      y: 0.5,
      text: 'MW',
      showarrow: false,
      font: { size: 10, color: '#64748b', family: 'system-ui, sans-serif' },
      xanchor: 'right',
      yanchor: 'middle',
    });

    return {
      shapes,
      annotations,
      showlegend: false,
      margin: { t: 20, r: 20, b: 35, l: 35 },
      xaxis: {
        type: 'date',
        tickformat: '%H:%M',
        dtick: 4 * 3600 * 1000,
        gridcolor: '#f1f5f9',
        zerolinecolor: '#f1f5f9',
        tickfont: { size: 10, color: '#64748b' },
      },
      yaxis: {
        gridcolor: '#f1f5f9',
        zerolinecolor: '#f1f5f9',
        tickfont: { size: 10, color: '#64748b' },
      },
    };
  }, [atRiskRanges, peak_threshold_mw, points]);

  return (
    <div className="w-full h-[280px]">
      <PlotlyChart data={chartTraces} layout={layout} />
    </div>
  );
};
