import React, { useMemo } from 'react';
import { PlotlyChart } from '../../components/shared/PlotlyChart';

interface CostRiskPoint {
  quantile: number;
  value: number;
  isExposure: boolean;
}

interface CostRiskChartProps {
  points: CostRiskPoint[];
  currentQuantile: number;
}

export const CostRiskChart: React.FC<CostRiskChartProps> = ({
  points,
  currentQuantile,
}) => {
  const { xVals, yVals, currentPoint } = useMemo(() => {
    let pts = [...points].sort((a, b) => a.quantile - b.quantile);
    if (pts.length === 0) {
      pts = [
        { quantile: 0.5, value: 120, isExposure: false },
        { quantile: 0.6, value: 95, isExposure: false },
        { quantile: 0.7, value: 75, isExposure: false },
        { quantile: 0.8, value: 60, isExposure: false },
        { quantile: 0.9, value: 45, isExposure: false },
        { quantile: 0.95, value: 40, isExposure: false },
        { quantile: 0.99, value: 38, isExposure: false },
      ];
    }

    const x = pts.map((p) => p.quantile);
    const y = pts.map((p) => p.value);

    let closest = pts[0];
    let minDiff = Math.abs(pts[0].quantile - currentQuantile);
    for (const p of pts) {
      const diff = Math.abs(p.quantile - currentQuantile);
      if (diff < minDiff) {
        minDiff = diff;
        closest = p;
      }
    }

    return {
      xVals: x,
      yVals: y,
      currentPoint: closest,
    };
  }, [points, currentQuantile]);

  const plotData = useMemo(() => {
    const traces: any[] = [
      {
        type: 'scatter',
        mode: 'lines',
        name: 'Cost against risk',
        x: xVals,
        y: yVals,
        line: { color: '#1d4ed8', width: 2.2, shape: 'spline' },
        hoverinfo: 'skip',
      },
    ];

    if (currentPoint) {
      traces.push({
        type: 'scatter',
        mode: 'markers',
        name: 'Selected',
        x: [currentPoint.quantile],
        y: [currentPoint.value],
        marker: { size: 9, color: '#c2410c' },
        hoverinfo: 'skip',
      });
    }

    return traces;
  }, [xVals, yVals, currentPoint]);

  const layout = useMemo(() => {
    return {
      showlegend: false,
      margin: { t: 25, r: 25, b: 35, l: 35 },
      annotations: [
        {
          xref: 'paper',
          yref: 'paper',
          x: 0,
          y: 1.05,
          text: 'Cost',
          showarrow: false,
          font: { size: 10, color: '#64748b' },
          xanchor: 'left',
        },
        {
          xref: 'paper',
          yref: 'paper',
          x: 0.02,
          y: -0.15,
          text: 'Lower risk',
          showarrow: false,
          font: { size: 9, color: '#64748b' },
          xanchor: 'left',
        },
        {
          xref: 'paper',
          yref: 'paper',
          x: 0.98,
          y: -0.15,
          text: 'Higher risk',
          showarrow: false,
          font: { size: 9, color: '#64748b' },
          xanchor: 'right',
        },
      ],
      xaxis: {
        showticklabels: false,
        showgrid: false,
        zeroline: false,
      },
      yaxis: {
        showticklabels: false,
        showgrid: false,
        zeroline: false,
      },
    };
  }, []);

  return (
    <div className="w-full h-[220px]">
      <PlotlyChart data={plotData} layout={layout} />
    </div>
  );
};
