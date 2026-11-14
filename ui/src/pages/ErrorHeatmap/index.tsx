import React, { useEffect, useState } from 'react';
import { ChartCard } from '../../components/shared/ChartCard';
import { HeatmapPlot } from './HeatmapPlot';
import { getErrorHeatmap } from '../../api/client';
import { ErrorHeatmapResponse } from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

export const ErrorHeatmapPage: React.FC = () => {
  const model = DEFAULT_MODEL;
  const compareModel = 'seasonal_naive';
  const [isCompareMode, setIsCompareMode] = useState<boolean>(false);
  const [metric, setMetric] = useState<'mape' | 'rmse' | 'bias'>('mape');
  const [horizonDay, setHorizonDay] = useState<string>('1');

  const [heatmapData, setHeatmapData] = useState<ErrorHeatmapResponse | null>(null);
  const [compareData, setCompareData] = useState<ErrorHeatmapResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const p1 = getErrorHeatmap({
      model,
      metric,
      horizon_day: horizonDay,
    });

    const p2 = isCompareMode
      ? getErrorHeatmap({
          model: compareModel,
          metric,
          horizon_day: horizonDay,
        })
      : Promise.resolve(null);

    Promise.all([p1, p2])
      .then(([res1, res2]) => {
        if (active) {
          setHeatmapData(res1);
          setCompareData(res2);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || 'Failed to load heatmap data');
          setHeatmapData(null);
          setCompareData(null);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [model, compareModel, isCompareMode, metric, horizonDay]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Error heatmap
        </h1>

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Metric
            </label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value as 'mape' | 'rmse' | 'bias')}
              className="bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer min-w-[120px]"
            >
              <option value="mape">MAPE</option>
              <option value="rmse">RMSE</option>
              <option value="bias">Bias</option>
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Horizon
            </label>
            <select
              value={horizonDay}
              onChange={(e) => setHorizonDay(e.target.value)}
              className="bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer min-w-[120px]"
            >
              <option value="1">D+1</option>
              <option value="2">D+2</option>
              <option value="3">D+3</option>
              <option value="4">D+4</option>
              <option value="5">D+5</option>
              <option value="6">D+6</option>
              <option value="7">D+7</option>
              <option value="all">All</option>
            </select>
          </div>

          <div className="flex items-center pb-2.5 space-x-2">
            <button
              type="button"
              role="switch"
              aria-checked={isCompareMode}
              onClick={() => setIsCompareMode(!isCompareMode)}
              className={`w-9 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                isCompareMode ? 'bg-[#1d4ed8]' : 'bg-slate-300'
              }`}
            >
              <span
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  isCompareMode ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
            <span className="text-sm text-slate-700 font-normal">
              Compare two models
            </span>
          </div>
        </div>
      </div>

      <ChartCard
        title="Error by hour of day and season"
        loading={loading}
        error={error}
        empty={!heatmapData}
      >
        {heatmapData && (
          <div className="space-y-6">
            <HeatmapPlot data={heatmapData} />
            {isCompareMode && compareData && (
              <div className="pt-6 border-t border-slate-200">
                <div className="text-sm font-semibold text-slate-800 mb-3">
                  Baseline (Seasonal-naive) Comparison
                </div>
                <HeatmapPlot data={compareData} />
              </div>
            )}
          </div>
        )}
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-3">Worst cell</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Summer evenings (19:00) are the hardest to forecast, mostly because of cooling demand that swings with the weather.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h3 className="text-base font-bold text-slate-900 mb-3">Best cell</h3>
          <p className="text-sm text-slate-600 leading-relaxed">
            Winter early mornings (03:00) are the easiest: demand is low and steady.
          </p>
        </div>
      </div>
    </div>
  );
};
