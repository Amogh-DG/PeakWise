import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import {
  DayAheadForecastResponse,
  WeekAheadForecastResponse,
  ForecastPoint,
} from '../../api/types';

interface ForecastChartProps {
  data: DayAheadForecastResponse | WeekAheadForecastResponse;
  view: 'day' | 'week';
}

export const ForecastChart: React.FC<ForecastChartProps> = ({ data, view }) => {
  const points = data.points;
  const peakThreshold = data.peak_threshold_mw;

  const chartData = useMemo(() => {
    if (!points || points.length === 0) return [];

    const xVals = points.map((p) => p.ts);
    const p05Vals = points.map((p) => p.p05);
    const p10Vals = points.map((p) => p.p10);
    const p50Vals = points.map((p) => p.p50);
    const p90Vals = points.map((p) => p.p90);
    const p95Vals = points.map((p) => p.p95);

    const customHoverData = points.map((p: ForecastPoint) => [
      p.actual !== null ? `${p.actual.toFixed(1)} MW` : 'Unobserved',
      p.p50.toFixed(1),
      p.p10.toFixed(1),
      p.p90.toFixed(1),
      p.p05.toFixed(1),
      p.p95.toFixed(1),
    ]);

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
        name: 'P10–P90 (80% Interval)',
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
        line: { color: '#2563eb', width: 2.2, dash: 'dash' },
        customdata: customHoverData,
        hovertemplate:
          '<b>%{x|%a %d %b, %H:%M} IST</b><br>' +
          'Actual: <b>%{customdata[0]}</b><br>' +
          'P50 Forecast: <b>%{customdata[1]} MW</b><br>' +
          'P10–P90 (80%): <b>[%{customdata[2]}, %{customdata[3]}] MW</b><br>' +
          'P05–P95 (90%): <b>[%{customdata[4]}, %{customdata[5]}] MW</b><extra></extra>',
      },
    ];

    const actualPoints = points.filter((p) => p.actual !== null);
    if (actualPoints.length > 0) {
      traces.push({
        name: 'Actual Demand',
        x: actualPoints.map((p) => p.ts),
        y: actualPoints.map((p) => p.actual),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#0f172a', width: 2.5 },
        hovertemplate: '<b>Actual: %{y:.1f} MW</b><br>%{x|%a %d %b, %H:%M} IST<extra></extra>',
      });
    }

    if ('peak' in data && data.peak) {
      traces.push({
        name: 'Predicted Peak',
        x: [data.peak.predicted_peak_ts],
        y: [data.peak.predicted_peak_mw.p50],
        type: 'scatter',
        mode: 'markers',
        marker: {
          symbol: 'diamond',
          size: 11,
          color: '#0f172a',
        },
        hovertemplate: '<b>Predicted Peak: %{y:.1f} MW</b><br>%{x|%H:%M} IST<extra></extra>',
      });

      if (data.peak.actual_peak_ts && data.peak.actual_peak_mw !== null) {
        traces.push({
          name: 'Actual Peak',
          x: [data.peak.actual_peak_ts],
          y: [data.peak.actual_peak_mw],
          type: 'scatter',
          mode: 'markers',
          marker: {
            symbol: 'circle',
            size: 11,
            color: '#c2410c',
          },
          hovertemplate: '<b>Actual Peak: %{y:.1f} MW</b><br>%{x|%H:%M} IST<extra></extra>',
        });
      }
    }

    return traces;
  }, [points, data]);

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
          font: { size: 11, color: '#9a3412', family: 'system-ui, sans-serif' },
          xanchor: 'left',
        });
      }
    });

    if (peakThreshold && points && points.length > 0) {
      shapes.push({
        type: 'line',
        xref: 'paper',
        yref: 'y',
        x0: 0,
        x1: 1,
        y0: peakThreshold,
        y1: peakThreshold,
        line: {
          color: '#c2410c',
          width: 1.5,
          dash: 'dot',
        },
      });

      annotations.push({
        xref: 'paper',
        yref: 'y',
        x: 0.01,
        y: peakThreshold,
        text: 'Peak threshold',
        showarrow: false,
        font: { size: 11, color: '#c2410c', family: 'system-ui, sans-serif' },
        yshift: 10,
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
      font: { size: 12, color: '#64748b', family: 'system-ui, sans-serif' },
      xanchor: 'right',
      yanchor: 'middle',
    });

    return {
      shapes,
      annotations,
      showlegend: false,
      margin: { t: 25, r: 25, b: 40, l: 45 },
      xaxis: {
        type: 'date',
        tickformat: view === 'day' ? '%H:%M' : '%a %d',
        dtick: view === 'day' ? 4 * 3600 * 1000 : 24 * 3600 * 1000,
        gridcolor: '#f1f5f9',
        zerolinecolor: '#f1f5f9',
        tickfont: { size: 11, color: '#64748b' },
      },
      yaxis: {
        gridcolor: '#f1f5f9',
        zerolinecolor: '#f1f5f9',
        tickfont: { size: 11, color: '#64748b' },
      },
    };
  }, [atRiskRanges, peakThreshold, points, view]);

  return (
    <div className="w-full h-[400px]">
      <PlotlyChart data={chartData} layout={layout} />
    </div>
  );
};
