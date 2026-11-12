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
        fillcolor: 'rgba(56, 189, 248, 0.12)',
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
        fillcolor: 'rgba(14, 165, 233, 0.24)',
        line: { color: 'transparent', width: 0 },
        hoverinfo: 'skip',
      },
      {
        name: 'P50 Forecast',
        x: xVals,
        y: p50Vals,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#0284c7', width: 2.2, dash: 'dash' },
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
        line: { color: '#f8fafc', width: 2.5 },
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
          line: { color: '#38bdf8', width: 2 },
        },
        hovertemplate:
          '<b>Predicted Daily Peak (P50)</b><br>%{x|%H:%M} IST: <b>%{y:.1f} MW</b><extra></extra>',
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
            color: '#ea580c',
            line: { color: '#ffffff', width: 2 },
          },
          hovertemplate:
            '<b>Actual Daily Peak</b><br>%{x|%H:%M} IST: <b>%{y:.1f} MW</b><extra></extra>',
        });
      }
    } else if ('daily_peaks' in data && data.daily_peaks) {
      const predX: string[] = [];
      const predY: number[] = [];
      const actX: string[] = [];
      const actY: number[] = [];

      for (const dp of data.daily_peaks) {
        if (dp.predicted_peak_ts) {
          predX.push(dp.predicted_peak_ts);
          predY.push(dp.predicted_peak_mw.p50);
        }
        if (dp.actual_peak_ts && dp.actual_peak_mw !== null) {
          actX.push(dp.actual_peak_ts);
          actY.push(dp.actual_peak_mw);
        }
      }

      traces.push({
        name: 'Predicted Peaks',
        x: predX,
        y: predY,
        type: 'scatter',
        mode: 'markers',
        marker: {
          symbol: 'diamond',
          size: 10,
          color: '#0f172a',
          line: { color: '#38bdf8', width: 2 },
        },
        hovertemplate: '<b>Predicted Peak</b><br>%{x|%a %d %b %H:%M}: %{y:.1f} MW<extra></extra>',
      });

      if (actX.length > 0) {
        traces.push({
          name: 'Actual Peaks',
          x: actX,
          y: actY,
          type: 'scatter',
          mode: 'markers',
          marker: {
            symbol: 'circle',
            size: 10,
            color: '#ea580c',
            line: { color: '#ffffff', width: 2 },
          },
          hovertemplate: '<b>Actual Peak</b><br>%{x|%a %d %b %H:%M}: %{y:.1f} MW<extra></extra>',
        });
      }
    }

    return traces;
  }, [points, data]);

  const shapes = useMemo(() => {
    const list: any[] = [];

    list.push({
      type: 'line',
      xref: 'paper',
      x0: 0,
      x1: 1,
      y0: peakThreshold,
      y1: peakThreshold,
      line: {
        color: '#f59e0b',
        width: 1.5,
        dash: 'dashdot',
      },
    });

    let currentStart: string | null = null;
    let currentEnd: string | null = null;

    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      if (p.at_risk) {
        if (!currentStart) currentStart = p.ts;
        currentEnd = p.ts;
      } else if (currentStart && currentEnd) {
        list.push({
          type: 'rect',
          xref: 'x',
          yref: 'paper',
          x0: currentStart,
          x1: currentEnd,
          y0: 0,
          y1: 1,
          fillcolor: 'rgba(239, 68, 68, 0.12)',
          line: { width: 0 },
          layer: 'below',
        });
        currentStart = null;
        currentEnd = null;
      }
    }

    if (currentStart && currentEnd) {
      list.push({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: currentStart,
        x1: currentEnd,
        y0: 0,
        y1: 1,
        fillcolor: 'rgba(239, 68, 68, 0.12)',
        line: { width: 0 },
        layer: 'below',
      });
    }

    if (view === 'week') {
      for (const p of points) {
        if (p.ts.endsWith('T00:00:00+05:30')) {
          list.push({
            type: 'line',
            xref: 'x',
            yref: 'paper',
            x0: p.ts,
            x1: p.ts,
            y0: 0,
            y1: 1,
            line: {
              color: '#334155',
              width: 1,
              dash: 'dash',
            },
            layer: 'below',
          });
        }
      }
    }

    return list;
  }, [points, peakThreshold, view]);

  const annotations = useMemo(() => {
    const list: any[] = [
      {
        xref: 'paper',
        yref: 'y',
        x: 0.02,
        y: peakThreshold,
        text: `Peak threshold (${peakThreshold.toLocaleString()} MW)`,
        showarrow: false,
        font: { size: 10, color: '#f59e0b', family: 'JetBrains Mono, monospace' },
        yshift: 10,
      },
    ];

    const hasRisk = points.some((p) => p.at_risk);
    if (hasRisk) {
      const riskIndex = points.findIndex((p) => p.at_risk);
      if (riskIndex >= 0) {
        list.push({
          xref: 'x',
          yref: 'paper',
          x: points[riskIndex].ts,
          y: 0.95,
          text: 'At-risk hours',
          showarrow: false,
          font: { size: 11, color: '#f87171', family: 'Plus Jakarta Sans, sans-serif' },
          xanchor: 'left',
        });
      }
    }

    return list;
  }, [points, peakThreshold]);

  const layout = useMemo(() => {
    return {
      shapes,
      annotations,
      xaxis: {
        type: 'date',
        tickformat: view === 'day' ? '%H:%M' : '%d %b %H:%M',
        hoverformat: '%a %d %b %Y %H:%M',
        dtick: view === 'day' ? 4 * 3600 * 1000 : 24 * 3600 * 1000,
      },
      yaxis: {
        title: {
          text: 'Demand (MW)',
          font: { size: 12, color: '#9ca3af' },
        },
      },
      legend: {
        orientation: 'h',
        y: -0.18,
        x: 0.0,
        font: { size: 11, color: '#9ca3af' },
      },
    };
  }, [shapes, annotations, view]);

  return (
    <div className="w-full">
      <div className="h-[440px] w-full">
        <PlotlyChart data={chartData} layout={layout} />
      </div>
    </div>
  );
};
