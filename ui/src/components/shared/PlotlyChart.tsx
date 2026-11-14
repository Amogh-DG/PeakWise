import React, { useMemo } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { CHART_THEME } from '../../constants/theme';

const Plot = createPlotlyComponent(Plotly);

interface PlotlyChartProps {
  data: any[];
  layout?: Record<string, any>;
  config?: Record<string, any>;
  className?: string;
  style?: React.CSSProperties;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
  className = '',
  style = {},
}) => {
  const mergedLayout = useMemo(() => {
    return {
      autosize: true,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        color: CHART_THEME.textColor,
        family: 'system-ui, -apple-system, sans-serif',
      },
      margin: {
        t: 20,
        r: 20,
        b: 40,
        l: 50,
        ...layout.margin,
      },
      xaxis: {
        gridcolor: CHART_THEME.gridColor,
        zerolinecolor: CHART_THEME.gridColor,
        tickfont: {
          family: 'system-ui, -apple-system, sans-serif',
          size: 11,
          color: CHART_THEME.mutedColor,
        },
        ...layout.xaxis,
      },
      yaxis: {
        gridcolor: CHART_THEME.gridColor,
        zerolinecolor: CHART_THEME.gridColor,
        tickfont: {
          family: 'system-ui, -apple-system, sans-serif',
          size: 11,
          color: CHART_THEME.mutedColor,
        },
        ...layout.yaxis,
      },
      ...layout,
    };
  }, [layout]);

  const mergedConfig = useMemo(() => {
    return {
      responsive: true,
      displayModeBar: false,
      ...config,
    };
  }, [config]);

  return (
    <div className={`w-full h-full min-h-[300px] ${className}`}>
      <Plot
        data={data}
        layout={mergedLayout}
        config={mergedConfig}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%', ...style }}
      />
    </div>
  );
};
