import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { DatePicker } from '../../components/shared/DatePicker';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { TariffForm } from './TariffForm';
import { ScheduleChart } from './ScheduleChart';
import { CostRiskChart } from './CostRiskChart';
import { formatINR, formatMW, formatMWh, formatPct } from './formatters';
import {
  getProcurementDefaults,
  getProcurementRecommendation,
} from '../../api/client';
import {
  ProcurementResponse,
  ProcurementTariff,
} from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

const RISK_CURVE_QUANTILES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99];

export const ProcurementPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [startDate, setStartDate] = useState<string>('2024-06-08');
  const [days, setDays] = useState<number>(7);
  const [riskQuantile, setRiskQuantile] = useState<number>(0.9);
  const [useNewsvendor, setUseNewsvendor] = useState<boolean>(false);
  const [formatUnit, setFormatUnit] = useState<'compact' | 'full'>('compact');

  const [tariff, setTariff] = useState<ProcurementTariff>({
    da_price_inr_per_mwh: 5000,
    under_price_inr_per_mwh: 12000,
    resale_price_inr_per_mwh: 2500,
  });
  const [defaultTariff, setDefaultTariff] = useState<ProcurementTariff | null>(null);
  const [disclaimer, setDisclaimer] = useState<string>('');

  const [recommendation, setRecommendation] = useState<ProcurementResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [riskCurvePoints, setRiskCurvePoints] = useState<
    Array<{ quantile: number; value: number; isExposure: boolean }>
  >([]);
  const [loadingCurve, setLoadingCurve] = useState<boolean>(false);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;
    getProcurementDefaults()
      .then((res) => {
        if (active) {
          setDefaultTariff(res.tariff);
          setTariff(res.tariff);
          setDisclaimer(res.disclaimer);
          if (res.default_risk_quantile) {
            setRiskQuantile(res.default_risk_quantile);
          }
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  const isTariffValid = useMemo(() => {
    return (
      tariff.under_price_inr_per_mwh > tariff.da_price_inr_per_mwh &&
      tariff.da_price_inr_per_mwh > tariff.resale_price_inr_per_mwh &&
      tariff.resale_price_inr_per_mwh >= 0
    );
  }, [tariff]);

  useEffect(() => {
    if (!isTariffValid) {
      setError(
        'Tariff configuration error: Shortfall Price must exceed Day-Ahead Price, which must exceed Resale Price (Shortfall > DA > Resale ≥ 0).'
      );
      setLoading(false);
      return;
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    setLoading(true);
    setError(null);

    debounceTimerRef.current = setTimeout(() => {
      const qParam: number | 'newsvendor' = useNewsvendor ? 'newsvendor' : riskQuantile;

      getProcurementRecommendation({
        start_date: startDate,
        days,
        model,
        risk_quantile: qParam,
        tariff,
      })
        .then((res) => {
          setRecommendation(res);
          setLoading(false);
          setError(null);
        })
        .catch((err) => {
          setRecommendation(null);
          setLoading(false);
          if (err.code === 'BAD_PARAMETER') {
            setError(`Invalid Parameter: ${err.message || 'Check days, risk quantile, or tariff values.'}`);
          } else if (err.code === 'DATE_OUT_OF_RANGE') {
            setError(`Date Out of Range: ${startDate} is outside the backtest evaluation range.`);
          } else {
            setError(err.message || 'Failed to calculate procurement recommendation.');
          }
        });

      setLoadingCurve(true);
      const curvePromises = RISK_CURVE_QUANTILES.map((q) =>
        getProcurementRecommendation({
          start_date: startDate,
          days,
          model,
          risk_quantile: q,
          tariff,
        })
          .then((res) => ({
            quantile: q,
            value:
              res.summary.cost_inr !== null && res.summary.cost_inr !== undefined
                ? res.summary.cost_inr
                : res.summary.p90_risk_exposure_inr,
            isExposure: res.summary.cost_inr === null || res.summary.cost_inr === undefined,
          }))
          .catch(() => null)
      );

      Promise.all(curvePromises)
        .then((pts) => {
          const valid = pts.filter((p): p is { quantile: number; value: number; isExposure: boolean } => p !== null);
          setRiskCurvePoints(valid);
          setLoadingCurve(false);
        })
        .catch(() => {
          setLoadingCurve(false);
        });
    }, 300);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [startDate, days, model, riskQuantile, useNewsvendor, tariff, isTariffValid]);

  const summary = recommendation?.summary;
  const isActualAvailable = summary?.cost_inr !== null && summary?.cost_inr !== undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-brand-text">
            Procurement Copilot
          </h1>
          <p className="text-xs text-brand-muted mt-1">
            Asymmetric loss optimization, newsvendor dispatch quantiles, and DISCOM cost hedging.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 bg-brand-surface border border-brand-border rounded-lg p-1">
            <span className="text-xs font-semibold text-brand-muted px-2">Display:</span>
            <button
              type="button"
              onClick={() => setFormatUnit('compact')}
              className={`text-xs px-2.5 py-1 rounded font-medium transition-colors ${
                formatUnit === 'compact'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-brand-muted hover:text-brand-text'
              }`}
            >
              Cr / L
            </button>
            <button
              type="button"
              onClick={() => setFormatUnit('full')}
              className={`text-xs px-2.5 py-1 rounded font-medium transition-colors ${
                formatUnit === 'full'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-brand-muted hover:text-brand-text'
              }`}
            >
              Full ₹
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm space-y-5">
          <h3 className="text-sm font-bold text-brand-text border-b border-brand-border pb-2">
            Schedule Parameters
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
                Start Date
              </label>
              <DatePicker value={startDate} onChange={setStartDate} />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
                Horizon Span
              </label>
              <select
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value, 10))}
                className="w-full bg-brand-bg text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-accent/50 cursor-pointer"
              >
                {[1, 2, 3, 4, 5, 6, 7].map((d) => (
                  <option key={d} value={d}>
                    {d} Day{d > 1 ? 's' : ''} ({d * 24} Hours)
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
                Forecast Model
              </label>
              <ModelSelect value={model} onChange={setModel} />
            </div>
          </div>

          <div className="pt-2 border-t border-brand-border/60 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
                Risk Quantile Selection: <span className="font-mono text-sky-400">P{Math.round(riskQuantile * 100)}</span> ({riskQuantile.toFixed(2)})
              </label>

              <label className="inline-flex items-center space-x-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useNewsvendor}
                  onChange={(e) => setUseNewsvendor(e.target.checked)}
                  className="rounded border-brand-border bg-brand-bg text-sky-600 focus:ring-sky-500 w-4 h-4 cursor-pointer"
                />
                <span className="text-xs font-medium text-brand-text">
                  Use Newsvendor Optimum
                  {recommendation?.newsvendor_quantile && (
                    <span className="font-mono text-emerald-400 ml-1">
                      (q = {recommendation.newsvendor_quantile.toFixed(3)})
                    </span>
                  )}
                </span>
              </label>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-xs font-mono text-brand-muted">0.50</span>
              <input
                type="range"
                min="0.50"
                max="0.99"
                step="0.01"
                value={riskQuantile}
                disabled={useNewsvendor}
                onChange={(e) => setRiskQuantile(parseFloat(e.target.value))}
                className="w-full accent-sky-500 cursor-pointer disabled:opacity-40"
              />
              <span className="text-xs font-mono text-brand-muted">0.99</span>
            </div>
            <div className="text-[11px] text-brand-muted flex justify-between">
              <span>Higher Risk (Under-procurement penalty)</span>
              <span>Conservative Hedge (Surplus salvage risk)</span>
            </div>
          </div>
        </div>

        <div>
          <TariffForm
            tariff={tariff}
            onChange={setTariff}
            defaultTariff={defaultTariff}
            disclaimer={disclaimer}
            disabled={loading}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatTile
          label="Realised Cost"
          value={formatINR(summary?.cost_inr, formatUnit)}
          subtitle={
            isActualAvailable
              ? `Scheduled: ${formatMWh(summary?.total_scheduled_mwh)}`
              : 'Actuals pending observation'
          }
        />
        <StatTile
          label="Flat Baseline Cost"
          value={formatINR(summary?.flat_cost_inr, formatUnit)}
          subtitle={
            recommendation?.baseline?.flat_mw
              ? `Ref: ${formatMW(recommendation.baseline.flat_mw)}`
              : 'Previous week average'
          }
        />
        <StatTile
          label="Estimated Savings"
          value={formatINR(summary?.savings_inr, formatUnit)}
          delta={formatPct(summary?.savings_pct)}
          deltaType={summary?.savings_inr && summary.savings_inr >= 0 ? 'positive' : 'negative'}
          subtitle="vs Fixed Flat Baseload"
        />
        <StatTile
          label="P90 Risk Exposure"
          value={formatINR(summary?.p90_risk_exposure_inr, formatUnit)}
          subtitle="Shortfall risk if P90 hits"
        />
        <StatTile
          label="Procurement Accuracy"
          value={
            summary?.under_procured_hours !== null && summary?.under_procured_hours !== undefined
              ? `${summary.under_procured_hours}h under / ${summary.over_procured_hours}h over`
              : 'Pending actual load'
          }
          subtitle={`Total: ${days * 24} Schedule Hours`}
        />
      </div>

      <ChartCard
        title="Optimal Day-Ahead Purchase Schedule vs Baselines"
        subtitle={`Hourly dispatch schedule for ${startDate} to ${recommendation?.end_date || '...'} (${days * 24} hours). Highlighted markers indicate at-risk peak hours.`}
        loading={loading}
        error={error}
        empty={!recommendation}
      >
        {recommendation && (
          <ScheduleChart
            schedule={recommendation.schedule}
            atRiskHours={recommendation.summary.at_risk_hours}
          />
        )}
      </ChartCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard
          title="Daily Dispatch & Cost Breakdown"
          subtitle="Aggregated daily volume, peak capacity, and cost comparison."
          empty={!recommendation || recommendation.by_day.length === 0}
        >
          {recommendation && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-brand-border text-brand-muted uppercase tracking-wider font-semibold">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Volume</th>
                    <th className="py-2.5 px-3">Peak Sched</th>
                    <th className="py-2.5 px-3 text-right">Realised Cost</th>
                    <th className="py-2.5 px-3 text-right">Flat Cost</th>
                    <th className="py-2.5 px-3 text-right">Savings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-border/60 font-mono">
                  {recommendation.by_day.map((d) => {
                    const dailySavings =
                      d.flat_cost_inr !== null && d.cost_inr !== null
                        ? d.flat_cost_inr - d.cost_inr
                        : null;
                    return (
                      <tr key={d.date} className="hover:bg-brand-surface-secondary/40 transition-colors">
                        <td className="py-2.5 px-3 font-sans font-medium text-brand-text">
                          {d.date}
                        </td>
                        <td className="py-2.5 px-3 text-brand-text">{formatMWh(d.scheduled_mwh)}</td>
                        <td className="py-2.5 px-3 text-amber-400">{formatMW(d.peak_scheduled_mw)}</td>
                        <td className="py-2.5 px-3 text-right text-brand-text">
                          {formatINR(d.cost_inr, formatUnit)}
                        </td>
                        <td className="py-2.5 px-3 text-right text-brand-muted">
                          {formatINR(d.flat_cost_inr, formatUnit)}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-semibold ${
                            dailySavings && dailySavings >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {formatINR(dailySavings, formatUnit)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Cost vs Risk Quantile Frontier"
          subtitle="Simulated cost curve evaluated across quantiles {0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99}."
          loading={loadingCurve}
          empty={riskCurvePoints.length === 0}
        >
          {riskCurvePoints.length > 0 && recommendation && (
            <CostRiskChart
              points={riskCurvePoints}
              currentQuantile={recommendation.risk_quantile}
              newsvendorQuantile={recommendation.newsvendor_quantile}
              isExposureOnly={!isActualAvailable}
              formatUnit={formatUnit}
            />
          )}
        </ChartCard>
      </div>
    </div>
  );
};

export default ProcurementPage;
