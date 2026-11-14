import React, { useEffect, useRef, useState } from 'react';
import { ChartCard } from '../../components/shared/ChartCard';
import { TariffForm } from './TariffForm';
import { ScheduleChart } from './ScheduleChart';
import { CostRiskChart } from './CostRiskChart';
import { formatINR } from './formatters';
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
  const model = DEFAULT_MODEL;
  const [weekInput, setWeekInput] = useState<string>('2026-W46');
  const startDate = '2024-06-08';
  const days = 7;
  const [riskQuantile, setRiskQuantile] = useState<number>(0.9);
  const [useNewsvendor, setUseNewsvendor] = useState<boolean>(false);
  const [showAbout, setShowAbout] = useState<boolean>(false);

  const [tariff, setTariff] = useState<ProcurementTariff>({
    da_price_inr_per_mwh: 5000,
    under_price_inr_per_mwh: 12000,
    resale_price_inr_per_mwh: 2500,
  });
  const [disclaimer, setDisclaimer] = useState<string>('');

  const [recommendation, setRecommendation] = useState<ProcurementResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [riskCurvePoints, setRiskCurvePoints] = useState<
    Array<{ quantile: number; value: number; isExposure: boolean }>
  >([]);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;
    getProcurementDefaults()
      .then((res) => {
        if (active) {
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

  useEffect(() => {
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
          setError(err.message || 'Failed to calculate procurement recommendation.');
        });

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
        })
        .catch(() => {});
    }, 300);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [startDate, days, model, riskQuantile, useNewsvendor, tariff]);

  const summary = recommendation?.summary;

  const costDisplay = summary?.cost_inr !== null && summary?.cost_inr !== undefined
    ? formatINR(summary.cost_inr, 'compact')
    : '[COST]';

  const savingsDisplay = summary?.savings_inr !== null && summary?.savings_inr !== undefined
    ? formatINR(summary.savings_inr, 'compact')
    : '[SAVED]';

  const exposureDisplay = summary?.p90_risk_exposure_inr !== null && summary?.p90_risk_exposure_inr !== undefined
    ? formatINR(summary.p90_risk_exposure_inr, 'compact')
    : '[EXPOSURE]';

  const daysLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const byDayList = daysLabels.map((dayName, idx) => {
    const dayData = recommendation?.by_day?.[idx];
    const daySavings =
      dayData && dayData.flat_cost_inr !== null && dayData.cost_inr !== null
        ? formatINR(dayData.flat_cost_inr - dayData.cost_inr, 'compact')
        : '[SAVED]';

    return {
      day: dayName,
      volume: dayData?.scheduled_mwh ? `${Math.round(dayData.scheduled_mwh).toLocaleString()} MWh` : '[MWh]',
      cost: dayData?.cost_inr !== null && dayData?.cost_inr !== undefined ? formatINR(dayData.cost_inr, 'compact') : '[COST]',
      savings: daySavings,
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Procurement
        </h1>

        <div className="flex flex-wrap items-end gap-6">
          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Week
            </label>
            <input
              type="text"
              value={weekInput}
              onChange={(e) => setWeekInput(e.target.value)}
              className="bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[160px]"
            />
          </div>

          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Risk quantile: P{Math.round(riskQuantile * 100)}
            </label>
            <div className="flex items-center h-10 px-3 bg-white border border-slate-300 rounded-lg min-w-[160px]">
              <input
                type="range"
                min="0.5"
                max="0.99"
                step="0.01"
                value={riskQuantile}
                disabled={useNewsvendor}
                onChange={(e) => setRiskQuantile(parseFloat(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
            </div>
          </div>

          <div className="flex items-center pb-2.5 space-x-2">
            <button
              type="button"
              role="switch"
              aria-checked={useNewsvendor}
              onClick={() => setUseNewsvendor(!useNewsvendor)}
              className={`w-9 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                useNewsvendor ? 'bg-[#1d4ed8]' : 'bg-slate-300'
              }`}
            >
              <span
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  useNewsvendor ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
            <span className="text-sm text-slate-700 font-normal">
              Newsvendor optimum
            </span>
          </div>

          <div className="flex items-center pb-2">
            <button
              type="button"
              onClick={() => setShowAbout(!showAbout)}
              className="text-sm text-[#1d4ed8] hover:underline flex items-center gap-1 cursor-pointer font-normal"
            >
              <span>{showAbout ? '▼' : '►'}</span>
              <span>About these numbers</span>
            </button>
          </div>
        </div>

        {showAbout && (
          <div className="mt-4 p-5 rounded-2xl bg-white border border-slate-200 text-xs text-slate-600 shadow-sm space-y-2">
            <p className="text-slate-900 font-semibold">Tariff Caveats & Newsvendor Dispatch</p>
            <p>
              {disclaimer ||
                'Illustrative placeholder values, not actual DISCOM tariffs. See docs/ASSUMPTIONS.md.'}
            </p>
            <p>
              Newsvendor quantile = (under - da) / (under - resale). Optimal economic dispatch under asymmetric shortage penalty.
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <span className="text-xs text-slate-500 font-normal block mb-2">Expected cost</span>
          <div className="text-3xl font-bold tracking-tight text-slate-900">{costDisplay}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <span className="text-xs text-slate-500 font-normal block mb-2">Savings</span>
          <div className="text-3xl font-bold tracking-tight text-slate-900">{savingsDisplay}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <span className="text-xs text-slate-500 font-normal block mb-2">P90 exposure</span>
          <div className="text-3xl font-bold tracking-tight text-slate-900">{exposureDisplay}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7">
          <ChartCard
            title="Schedule"
            loading={loading}
            error={error}
            empty={!recommendation}
            className="h-full"
          >
            {recommendation && <ScheduleChart schedule={recommendation.schedule} />}
          </ChartCard>
        </div>

        <div className="lg:col-span-5">
          <TariffForm
            tariff={tariff}
            onChange={setTariff}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm h-full">
            <h3 className="text-base font-bold text-slate-900 mb-4">Per day</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Day</th>
                    <th className="py-2.5 px-3">Volume</th>
                    <th className="py-2.5 px-3">Cost</th>
                    <th className="py-2.5 px-3 text-right">Savings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {byDayList.map((row) => (
                    <tr key={row.day} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-slate-900">{row.day}</td>
                      <td className="py-2.5 px-3 text-slate-700">{row.volume}</td>
                      <td className="py-2.5 px-3 text-slate-700">{row.cost}</td>
                      <td className="py-2.5 px-3 text-right text-slate-700 font-medium">
                        {row.savings}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="lg:col-span-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm h-full flex flex-col justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 mb-2">Cost against risk</h3>
              <CostRiskChart
                points={riskCurvePoints}
                currentQuantile={riskQuantile}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
