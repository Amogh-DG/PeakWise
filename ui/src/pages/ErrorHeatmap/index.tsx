import React, { useEffect, useMemo, useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { HeatmapPlot } from './HeatmapPlot';
import { getErrorHeatmap } from '../../api/client';
import { ErrorHeatmapResponse } from '../../api/types';
import { DEFAULT_MODEL, BASELINE_MODEL } from '../../constants/models';

const PEAK_HOURS = [6, 7, 8, 9, 10, 19, 20, 21, 22, 23];

const HORIZON_OPTIONS: Array<{ label: string; value: string }> = [
  { label: 'D+1', value: '1' },
  { label: 'D+2', value: '2' },
  { label: 'D+3', value: '3' },
  { label: 'D+4', value: '4' },
  { label: 'D+5', value: '5' },
  { label: 'D+6', value: '6' },
  { label: 'D+7', value: '7' },
  { label: 'All Horizons', value: 'all' },
];

export const ErrorHeatmapPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [compareModel, setCompareModel] = useState<string>(BASELINE_MODEL);
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
          setError(
            err.code === 'NOT_FOUND'
              ? `Error heatmap not found for model '${model}', metric '${metric.toUpperCase()}', and horizon '${horizonDay}'. Try choosing Horizon D+1 or All Horizons.`
              : err.message || 'Failed to load heatmap data'
          );
          setHeatmapData(null);
          setCompareData(null);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [model, compareModel, isCompareMode, metric, horizonDay]);

  const { sharedMin, sharedMax } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    const scanData = (d: ErrorHeatmapResponse | null) => {
      if (!d) return;
      for (const row of d.values) {
        for (const val of row) {
          if (val !== null && val !== undefined) {
            if (val < min) min = val;
            if (val > max) max = val;
          }
        }
      }
    };

    scanData(heatmapData);
    if (isCompareMode) {
      scanData(compareData);
    }

    return {
      sharedMin: min === Infinity ? 0 : min,
      sharedMax: max === -Infinity ? 10 : max,
    };
  }, [heatmapData, compareData, isCompareMode]);

  const callouts = useMemo(() => {
    if (!heatmapData || !heatmapData.values.length) return null;

    let worst = {
      val: -Infinity,
      absVal: -Infinity,
      season: '',
      hour: 0,
      count: 0,
    };
    let best = {
      val: Infinity,
      absVal: Infinity,
      season: '',
      hour: 0,
      count: 0,
    };

    let peakSum = 0;
    let peakCount = 0;
    let offPeakSum = 0;
    let offPeakCount = 0;

    for (let r = 0; r < heatmapData.values.length; r++) {
      const season = heatmapData.seasons[r];
      for (let c = 0; c < heatmapData.values[r].length; c++) {
        const val = heatmapData.values[r][c];
        const count = heatmapData.counts[r]?.[c] ?? 0;
        const hour = heatmapData.hours[c];

        if (val !== null && val !== undefined) {
          const absVal = Math.abs(val);

          if (metric === 'bias') {
            if (absVal > worst.absVal) {
              worst = { val, absVal, season, hour, count };
            }
            if (absVal < best.absVal) {
              best = { val, absVal, season, hour, count };
            }
          } else {
            if (val > worst.val) {
              worst = { val, absVal, season, hour, count };
            }
            if (val < best.val) {
              best = { val, absVal, season, hour, count };
            }
          }

          const targetMetricVal = metric === 'bias' ? absVal : val;
          if (PEAK_HOURS.includes(hour)) {
            peakSum += targetMetricVal;
            peakCount += 1;
          } else {
            offPeakSum += targetMetricVal;
            offPeakCount += 1;
          }
        }
      }
    }

    const peakAvg = peakCount > 0 ? peakSum / peakCount : 0;
    const offPeakAvg = offPeakCount > 0 ? offPeakSum / offPeakCount : 0;
    const peakDiffPct = offPeakAvg > 0 ? ((peakAvg - offPeakAvg) / offPeakAvg) * 100 : 0;

    const unit = metric === 'mape' ? '%' : 'MW';
    const seasonCapitalized = (s: string) =>
      s.charAt(0).toUpperCase() + s.slice(1).replace('_', '-');

    const worstText =
      worst.season === 'summer' && worst.hour >= 18
        ? `Summer evenings (${worst.hour}:00 IST) are the hardest to forecast (${worst.val.toFixed(1)} ${unit}), mostly because of cooling demand that swings rapidly with weather spikes.`
        : `${seasonCapitalized(worst.season)} at hour ${worst.hour}:00 IST exhibits the highest error (${worst.val.toFixed(1)} ${unit}) across ${worst.count} observations.`;

    const bestText =
      best.season === 'winter' && best.hour <= 5
        ? `Winter early mornings (${best.hour}:00 IST) are the easiest (${best.val.toFixed(1)} ${unit}): base load demand is low, steady, and less sensitive to temperature.`
        : `${seasonCapitalized(best.season)} at hour ${best.hour}:00 IST achieves the lowest error (${best.val.toFixed(1)} ${unit}), showing predictable load patterns.`;

    return {
      worst,
      best,
      worstText,
      bestText,
      peakAvg,
      offPeakAvg,
      peakDiffPct,
      unit,
      worstSeason: seasonCapitalized(worst.season),
      bestSeason: seasonCapitalized(best.season),
    };
  }, [heatmapData, metric]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 pb-4 border-b border-brand-border">
        <h1 className="text-3xl font-extrabold tracking-tight text-brand-text">
          Error Heatmap
        </h1>

        <div className="flex flex-wrap items-end gap-5">
          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              Metric
            </label>
            <div className="inline-flex rounded-lg border border-brand-border bg-brand-surface p-0.5">
              {(['mape', 'rmse', 'bias'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMetric(m)}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold font-mono uppercase tracking-wider transition-all ${
                    metric === m
                      ? 'bg-sky-600 text-white shadow-sm'
                      : 'text-brand-muted hover:text-brand-text'
                  }`}
                >
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              Horizon
            </label>
            <select
              value={horizonDay}
              onChange={(e) => setHorizonDay(e.target.value)}
              className="bg-brand-surface text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-accent/50 cursor-pointer"
            >
              {HORIZON_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              {isCompareMode ? 'Model 1' : 'Model'}
            </label>
            <ModelSelect value={model} onChange={setModel} />
          </div>

          {isCompareMode && (
            <div className="flex flex-col space-y-1.5">
              <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
                Model 2
              </label>
              <ModelSelect value={compareModel} onChange={setCompareModel} />
            </div>
          )}

          <div className="flex items-center space-x-2 pb-2">
            <label className="inline-flex items-center space-x-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isCompareMode}
                onChange={(e) => setIsCompareMode(e.target.checked)}
                className="rounded border-brand-border bg-brand-surface text-sky-600 focus:ring-sky-500 w-4 h-4 cursor-pointer"
              />
              <span className="text-xs font-medium text-brand-text">
                Compare two models
              </span>
            </label>
          </div>
        </div>
      </div>

      {callouts && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            label="Worst Segment"
            value={`${callouts.worstSeason} ${callouts.worst.hour}:00`}
            delta={`${callouts.worst.val.toFixed(1)} ${callouts.unit}`}
            deltaType="negative"
            subtitle="Highest observed forecast error"
          />
          <StatTile
            label="Best Segment"
            value={`${callouts.bestSeason} ${callouts.best.hour}:00`}
            delta={`${callouts.best.val.toFixed(1)} ${callouts.unit}`}
            deltaType="positive"
            subtitle="Lowest observed forecast error"
          />
          <StatTile
            label="Peak Hours Avg"
            value={`${callouts.peakAvg.toFixed(1)}`}
            unit={callouts.unit}
            subtitle="Hours 06–10 and 19–23"
          />
          <StatTile
            label="Peak vs Off-Peak"
            value={`${callouts.peakDiffPct >= 0 ? '+' : ''}${callouts.peakDiffPct.toFixed(1)}%`}
            delta={callouts.peakDiffPct >= 0 ? 'Higher peak error' : 'Lower peak error'}
            deltaType={callouts.peakDiffPct >= 0 ? 'negative' : 'positive'}
            subtitle={`Off-peak avg: ${callouts.offPeakAvg.toFixed(1)} ${callouts.unit}`}
          />
        </div>
      )}

      <ChartCard
        title="Error by hour of day and season"
        subtitle={`Decomposition across hours (0 to 23) and seasons. Columns 6–10 and 19–23 highlighted as peak hours.`}
        loading={loading}
        error={error}
        empty={!heatmapData}
      >
        {heatmapData && (
          <div className="space-y-6">
            {isCompareMode && compareData ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <HeatmapPlot
                  data={heatmapData}
                  title={`Model: ${model}`}
                  sharedZMin={sharedMin}
                  sharedZMax={sharedMax}
                />
                <HeatmapPlot
                  data={compareData}
                  title={`Model: ${compareModel}`}
                  sharedZMin={sharedMin}
                  sharedZMax={sharedMax}
                />
              </div>
            ) : (
              <HeatmapPlot data={heatmapData} />
            )}

            <div className="text-xs text-brand-muted flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-brand-border/60">
              <div className="flex items-center space-x-2">
                <span className="inline-block w-3 h-3 rounded-sm border-2 border-amber-500 bg-amber-500/10"></span>
                <span>
                  Outlined columns (06–10 and 19–23) are statutory Delhi peak hours.
                </span>
              </div>
              <span className="font-mono text-[11px]">
                Cells with fewer than 5 observations are rendered as null (—).
              </span>
            </div>
          </div>
        )}
      </ChartCard>

      {callouts && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-brand-text">Worst Cell</h3>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-rose-500/10 text-rose-400 border border-rose-500/30">
                {callouts.worst.val.toFixed(1)} {callouts.unit}
              </span>
            </div>
            <p className="text-xs text-brand-muted leading-relaxed">
              {callouts.worstText}
            </p>
          </div>

          <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-brand-text">Best Cell</h3>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {callouts.best.val.toFixed(1)} {callouts.unit}
              </span>
            </div>
            <p className="text-xs text-brand-muted leading-relaxed">
              {callouts.bestText}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ErrorHeatmapPage;
