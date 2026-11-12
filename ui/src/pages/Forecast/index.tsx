import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DatePicker } from '../../components/shared/DatePicker';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { ForecastChart } from './ForecastChart';
import { PeakCard } from './PeakCard';
import {
  getDayAheadForecast,
  getWeekAheadForecast,
  getPeakDay,
  getMeta,
} from '../../api/client';
import {
  DayAheadForecastResponse,
  WeekAheadForecastResponse,
  PeakDayResponse,
} from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

export const ForecastPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [date, setDate] = useState<string>(
    searchParams.get('date') || '2024-06-12'
  );
  const [model, setModel] = useState<string>(
    searchParams.get('model') || DEFAULT_MODEL
  );
  const [view, setView] = useState<'day' | 'week'>(
    (searchParams.get('view') as 'day' | 'week') || 'day'
  );

  const [showAbout, setShowAbout] = useState<boolean>(false);
  const [forecastData, setForecastData] = useState<
    DayAheadForecastResponse | WeekAheadForecastResponse | null
  >(null);
  const [peakData, setPeakData] = useState<PeakDayResponse | null>(null);

  const [loadingForecast, setLoadingForecast] = useState<boolean>(true);
  const [loadingPeak, setLoadingPeak] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [backtestRange, setBacktestRange] = useState<{ start: string; end: string } | null>(null);

  useEffect(() => {
    let mounted = true;
    getMeta()
      .then((meta) => {
        if (mounted && meta?.backtest_range) {
          setBacktestRange(meta.backtest_range);
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const urlDate = searchParams.get('date');
    const urlModel = searchParams.get('model');
    const urlView = searchParams.get('view');

    if (urlDate && urlDate !== date) setDate(urlDate);
    if (urlModel && urlModel !== model) setModel(urlModel);
    if (urlView && (urlView === 'day' || urlView === 'week') && urlView !== view) {
      setView(urlView);
    }
  }, [searchParams]);

  const updateUrl = (newDate: string, newModel: string, newView: 'day' | 'week') => {
    const params = new URLSearchParams(searchParams);
    params.set('date', newDate);
    params.set('model', newModel);
    params.set('view', newView);
    setSearchParams(params);
  };

  const handleDateChange = (newDate: string) => {
    setDate(newDate);
    updateUrl(newDate, model, view);
  };

  const handleModelChange = (newModel: string) => {
    setModel(newModel);
    updateUrl(date, newModel, view);
  };

  const handleViewChange = (newView: 'day' | 'week') => {
    setView(newView);
    updateUrl(date, model, newView);
  };

  useEffect(() => {
    let active = true;
    setLoadingForecast(true);
    setLoadingPeak(true);
    setError(null);
    setErrorCode(null);

    const forecastPromise =
      view === 'day'
        ? getDayAheadForecast(date, model)
        : getWeekAheadForecast(date, model);

    forecastPromise
      .then((data) => {
        if (active) {
          setForecastData(data);
          setLoadingForecast(false);
        }
      })
      .catch((err) => {
        if (active) {
          setErrorCode(err.code || 'ERROR');
          setError(err.message || 'Failed to fetch forecast');
          setForecastData(null);
          setLoadingForecast(false);
        }
      });

    getPeakDay(date, model)
      .then((data) => {
        if (active) {
          setPeakData(data);
          setLoadingPeak(false);
        }
      })
      .catch(() => {
        if (active) {
          setPeakData(null);
          setLoadingPeak(false);
        }
      });

    return () => {
      active = false;
    };
  }, [date, model, view]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-extrabold tracking-tight text-brand-text">
          Forecast
        </h1>

        <div className="flex flex-wrap items-end gap-5">
          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              Date
            </label>
            <DatePicker
              value={date}
              onChange={handleDateChange}
              minDate={backtestRange?.start}
              maxDate={backtestRange?.end}
            />
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              Horizon
            </label>
            <div className="inline-flex rounded-lg border border-brand-border bg-brand-surface p-0.5">
              <button
                type="button"
                onClick={() => handleViewChange('day')}
                className={`px-3.5 py-1.5 rounded-md text-sm font-semibold transition-all ${
                  view === 'day'
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-brand-muted hover:text-brand-text'
                }`}
              >
                Day-ahead
              </button>
              <button
                type="button"
                onClick={() => handleViewChange('week')}
                className={`px-3.5 py-1.5 rounded-md text-sm font-semibold transition-all ${
                  view === 'week'
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-brand-muted hover:text-brand-text'
                }`}
              >
                Week-ahead
              </button>
            </div>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider">
              Model
            </label>
            <ModelSelect value={model} onChange={handleModelChange} />
          </div>

          <div className="flex items-center pb-2">
            <button
              type="button"
              onClick={() => setShowAbout(!showAbout)}
              className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center space-x-1"
            >
              <span>{showAbout ? '▾' : '▸'}</span>
              <span>About these numbers</span>
            </button>
          </div>
        </div>

        {showAbout && (
          <div className="p-4 rounded-xl bg-brand-surface/60 border border-brand-border text-xs text-brand-muted space-y-2">
            <p className="text-brand-text font-medium">
              Probabilistic 7-day-ahead hourly load forecast at 10:00 IST daily origin:
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong className="text-sky-400">P10 to P90 (80% Interval):</strong> Shaded medium blue band. Expected 80% coverage under calibrated uncertainty.
              </li>
              <li>
                <strong className="text-sky-400">P05 to P95 (90% Interval):</strong> Lighter shaded outer band. Tail-risk envelope covering 90% of expected realizations.
              </li>
              <li>
                <strong className="text-amber-400">Peak Threshold:</strong> 90th percentile daily peak load threshold evaluated in the training window.
              </li>
              <li>
                <strong className="text-rose-400">At-Risk Hours:</strong> Hours where P90 forecast equals or exceeds the peak threshold.
              </li>
            </ul>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        <div className="lg:col-span-3">
          <ChartCard
            title="Actual vs P50, with uncertainty bands"
            subtitle={
              view === 'day'
                ? `Day-ahead hourly forecast for ${date}`
                : `Week-ahead hourly profile (168h) starting ${date}`
            }
            units="MW"
            loading={loadingForecast}
            error={
              errorCode === 'DATE_OUT_OF_RANGE'
                ? `Date ${date} is outside the backtest range (${backtestRange?.start || '2024-01-01'} to ${backtestRange?.end || '2024-12-31'}). Please choose a valid backtest date.`
                : error
            }
            empty={!forecastData || forecastData.points.length === 0}
          >
            {forecastData && (
              <ForecastChart data={forecastData} view={view} />
            )}

            <div className="mt-4 pt-3 border-t border-brand-border/60 flex flex-wrap items-center justify-between text-xs text-brand-muted gap-3">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 bg-slate-100"></span>
                  <span>Actual Demand</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 border-t border-dashed border-sky-400"></span>
                  <span>P50 Forecast</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-2 bg-sky-500/30 border border-sky-500/50 rounded-sm"></span>
                  <span>P10–P90 (80% interval)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-2 bg-sky-400/15 border border-sky-400/30 rounded-sm"></span>
                  <span>P05–P95 (90% interval)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className="w-3 h-0.5 border-t border-dotted border-amber-400"></span>
                  <span>Peak Threshold</span>
                </div>
              </div>

              <div className="font-mono text-[11px] text-brand-muted">
                Origin: 10:00 IST
              </div>
            </div>
          </ChartCard>
        </div>

        <div className="lg:col-span-1">
          <PeakCard data={peakData} loading={loadingPeak} />
        </div>
      </div>
    </div>
  );
};

export default ForecastPage;
