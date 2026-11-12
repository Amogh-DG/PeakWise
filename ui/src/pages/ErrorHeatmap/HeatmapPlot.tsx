import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { ErrorHeatmapResponse } from '../../api/types';

interface HeatmapPlotProps {
  data: ErrorHeatmapResponse;
  title?: string;
  sharedZMin?: number;
  sharedZMax?: number;
}

const SEASON_LABELS: Record<string, string> = {
  winter: 'Winter',
  summer: 'Summer',
  monsoon: 'Monsoon',
  post_monsoon: 'Post-Monsoon',
};

export const HeatmapPlot: React.FC<HeatmapPlotProps> = ({
  data,
  title,
  sharedZMin,
  sharedZMax,
}) => {
  const metric = data.metric;
  const unit = metric === 'mape' ? '%' : 'MW';

  const seasonNames = useMemo(() => {
    return data.seasons.map((s) => SEASON_LABELS[s] || s);
  }, [data.seasons]);

  const { zValues, cellText, customHover, minVal, maxVal } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    const z: (number | null)[][] = [];
    const text: string[][] = [];
    const custom: any[][] = [];

    for (let r = 0; r < data.values.length; r++) {
      const rowZ: (number | null)[] = [];
      const rowText: string[] = [];
      const rowCustom: any[] = [];

      for (let c = 0; c < data.values[r].length; c++) {
        const val = data.values[r][c];
        const count = data.counts[r]?.[c] ?? 0;
        const hour = data.hours[c];
        const season = seasonNames[r];

        if (val !== null && val !== undefined) {
          rowZ.push(val);
          rowText.push(val.toFixed(1));
          if (val < min) min = val;
          if (val > max) max = val;
        } else {
          rowZ.push(null);
          rowText.push('—');
        }

        rowCustom.push({
          hour,
          season,
          count,
          isNull: val === null || val === undefined,
        });
      }

      z.push(rowZ);
      text.push(rowText);
      custom.push(rowCustom);
    }

    return {
      zValues: z,
      cellText: text,
      customHover: custom,
      minVal: min === Infinity ? 0 : min,
      maxVal: max === -Infinity ? 10 : max,
    };
  }, [data.values, data.counts, data.hours, seasonNames]);

  const colorScale = useMemo(() => {
    if (metric === 'bias') {
      return [
        [0.0, '#3b82f6'],
        [0.35, '#93c5fd'],
        [0.5, '#1e293b'],
        [0.65, '#fca5a5'],
        [1.0, '#ef4444'],
      ];
    }

    if (metric === 'rmse') {
      return [
        [0.0, '#0f172a'],
        [0.2, '#1e3a8a'],
        [0.5, '#0284c7'],
        [0.8, '#38bdf8'],
        [1.0, '#e0f2fe'],
      ];
    }

    return [
      [0.0, '#0f172a'],
      [0.25, '#1e3a8a'],
      [0.55, '#0284c7'],
      [0.8, '#38bdf8'],
      [1.0, '#bae6fd'],
    ];
  }, [metric]);

  const plotData = useMemo(() => {
    let effectiveZMin = sharedZMin !== undefined ? sharedZMin : minVal;
    let effectiveZMax = sharedZMax !== undefined ? sharedZMax : maxVal;

    if (metric === 'bias') {
      const absBound = Math.max(Math.abs(effectiveZMin), Math.abs(effectiveZMax));
      effectiveZMin = -absBound;
      effectiveZMax = absBound;
    }

    const hoverTemplate =
      '<b>%{customdata.season}</b> — Hour %{customdata.hour}:00–%{customdata.hour}:59 IST<br>' +
      'Value: <b>%{z:.2f} ' +
      unit +
      '</b><br>' +
      'Sample: <b>%{customdata.count} hours</b><extra></extra>';

    return [
      {
        type: 'heatmap',
        x: data.hours.map((h) => String(h)),
        y: seasonNames,
        z: zValues,
        text: cellText,
        texttemplate: '%{text}',
        textfont: {
          family: 'JetBrains Mono, monospace',
          size: 11,
          color: '#f8fafc',
        },
        colorscale: colorScale,
        zmin: effectiveZMin,
        zmax: effectiveZMax,
        zmid: metric === 'bias' ? 0 : undefined,
        customdata: customHover,
        hovertemplate: hoverTemplate,
        xgap: 2,
        ygap: 2,
        colorbar: {
          title: {
            text: unit,
            font: { family: 'JetBrains Mono, monospace', size: 11, color: '#9ca3af' },
          },
          tickfont: { family: 'JetBrains Mono, monospace', size: 10, color: '#9ca3af' },
          thickness: 14,
          len: 0.9,
        },
      },
    ];
  }, [
    data.hours,
    seasonNames,
    zValues,
    cellText,
    customHover,
    colorScale,
    metric,
    unit,
    sharedZMin,
    sharedZMax,
    minVal,
    maxVal,
  ]);

  const layout = useMemo(() => {
    const numSeasons = seasonNames.length;

    const shapes: any[] = [
      {
        type: 'rect',
        xref: 'x',
        yref: 'y',
        x0: 5.5,
        x1: 10.5,
        y0: -0.5,
        y1: numSeasons - 0.5,
        line: { color: '#f59e0b', width: 2 },
        fillcolor: 'rgba(245, 158, 11, 0.05)',
      },
      {
        type: 'rect',
        xref: 'x',
        yref: 'y',
        x0: 18.5,
        x1: 23.5,
        y0: -0.5,
        y1: numSeasons - 0.5,
        line: { color: '#f97316', width: 2 },
        fillcolor: 'rgba(249, 115, 22, 0.05)',
      },
    ];

    const annotations: any[] = [
      {
        xref: 'x',
        yref: 'paper',
        x: 8,
        y: 1.12,
        text: 'Morning Peak (06–10)',
        showarrow: false,
        font: { size: 10, color: '#f59e0b', family: 'Plus Jakarta Sans, sans-serif' },
      },
      {
        xref: 'x',
        yref: 'paper',
        x: 21,
        y: 1.12,
        text: 'Evening Peak (19–23)',
        showarrow: false,
        font: { size: 10, color: '#f97316', family: 'Plus Jakarta Sans, sans-serif' },
      },
    ];

    return {
      shapes,
      annotations,
      xaxis: {
        title: {
          text: 'Hour of Day (IST)',
          font: { size: 12, color: '#9ca3af' },
          standoff: 10,
        },
        tickmode: 'linear',
        tick0: 0,
        dtick: 1,
        side: 'top',
      },
      yaxis: {
        autorange: 'reversed',
        tickfont: {
          family: 'Plus Jakarta Sans, sans-serif',
          size: 12,
          color: '#f8fafc',
        },
      },
      margin: {
        t: 60,
        r: 30,
        b: 50,
        l: 110,
      },
    };
  }, [seasonNames]);

  return (
    <div className="w-full">
      {title && (
        <div className="mb-2 font-semibold text-sm text-brand-text flex items-center justify-between">
          <span>{title}</span>
          <span className="text-xs font-mono text-brand-muted">
            {metric.toUpperCase()} ({unit})
          </span>
        </div>
      )}
      <div className="h-[380px] w-full">
        <PlotlyChart data={plotData} layout={layout} />
      </div>
    </div>
  );
};
