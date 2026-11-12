import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { formatINR } from './formatters';

interface CostRiskPoint {
  quantile: number;
  value: number;
  isExposure: boolean;
}

interface CostRiskChartProps {
  points: CostRiskPoint[];
  currentQuantile: number;
  newsvendorQuantile: number;
  isExposureOnly: boolean;
  formatUnit: 'compact' | 'full';
}

export const CostRiskChart: React.FC<CostRiskChartProps> = ({
  points,
  currentQuantile,
  newsvendorQuantile,
  isExposureOnly,
  formatUnit,
}) => {
  const sortedPoints = useMemo(() => {
    return [...points].sort((a, b) => a.quantile - b.quantile);
  }, [points]);

  const currentVal = useMemo(() => {
    if (sortedPoints.length === 0) return null;
    let closest = sortedPoints[0];
    let minDiff = Math.abs(sortedPoints[0].quantile - currentQuantile);
    for (const pt of sortedPoints) {
      const diff = Math.abs(pt.quantile - currentQuantile);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }
    return closest.value;
  }, [sortedPoints, currentQuantile]);

  const newsvendorVal = useMemo(() => {
    if (sortedPoints.length === 0) return null;
    let closest = sortedPoints[0];
    let minDiff = Math.abs(sortedPoints[0].quantile - newsvendorQuantile);
    for (const pt of sortedPoints) {
      const diff = Math.abs(pt.quantile - newsvendorQuantile);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }
    return closest.value;
  }, [sortedPoints, newsvendorQuantile]);

  const plotData = useMemo(() => {
    const x = sortedPoints.map((p) => p.quantile);
    const y = sortedPoints.map((p) => p.value);
    const text = y.map((v) => formatINR(v, formatUnit));

    const traces: any[] = [
      {
        type: 'scatter',
        mode: 'lines+markers',
        name: isExposureOnly ? 'P90 Risk Exposure' : 'Realised Cost',
        x,
        y,
        text,
        line: { color: '#0284c7', width: 2.5 },
        marker: { size: 6, color: '#0284c7' },
        hovertemplate: 'Quantile %{x:.2f}<br>Amount: <b>%{text}</b><extra></extra>',
      },
    ];

    if (currentVal !== null) {
      traces.push({
        type: 'scatter',
        mode: 'markers',
        name: `Current (q=${currentQuantile.toFixed(2)})`,
        x: [currentQuantile],
        y: [currentVal],
        marker: { size: 12, color: '#f59e0b', symbol: 'circle', line: { color: '#ffffff', width: 1.5 } },
        hovertemplate: `Current q=${currentQuantile.toFixed(2)}<br>Amount: <b>${formatINR(currentVal, formatUnit)}</b><extra></extra>`,
      });
    }

    if (newsvendorVal !== null) {
      traces.push({
        type: 'scatter',
        mode: 'markers',
        name: `Newsvendor (q=${newsvendorQuantile.toFixed(3)})`,
        x: [newsvendorQuantile],
        y: [newsvendorVal],
        marker: { size: 12, color: '#10b981', symbol: 'diamond', line: { color: '#ffffff', width: 1.5 } },
        hovertemplate: `Newsvendor q=${newsvendorQuantile.toFixed(3)}<br>Amount: <b>${formatINR(newsvendorVal, formatUnit)}</b><extra></extra>`,
      });
    }

    return traces;
  }, [
    sortedPoints,
    isExposureOnly,
    formatUnit,
    currentQuantile,
    currentVal,
    newsvendorQuantile,
    newsvendorVal,
  ]);

  const layout = useMemo(() => {
    return {
      xaxis: {
        title: { text: 'Procurement Risk Quantile', font: { size: 12, color: '#9ca3af' } },
        tickmode: 'linear',
        tick0: 0.5,
        dtick: 0.1,
        showgrid: true,
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      yaxis: {
        title: {
          text: isExposureOnly ? 'P90 Exposure (INR)' : 'Realised Cost (INR)',
          font: { size: 12, color: '#9ca3af' },
        },
        showgrid: true,
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      legend: {
        orientation: 'h',
        y: 1.15,
        x: 0,
        font: { family: 'Plus Jakarta Sans, sans-serif', size: 11, color: '#9ca3af' },
      },
      margin: { t: 40, r: 20, b: 45, l: 70 },
      hovermode: 'closest',
    };
  }, [isExposureOnly]);

  return (
    <div className="w-full h-[320px]">
      <PlotlyChart data={plotData} layout={layout} />
    </div>
  );
};
