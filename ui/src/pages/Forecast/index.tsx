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
    searchParams.get('date') || '2024-05-15'
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
  const [weatherProxyNote, setWeatherProxyNote] = useState<string>('');

  useEffect(() => {
    let mounted = true;
    getMeta()
      .then((meta) => {
        if (mounted && meta) {
          if (meta.backtest_range) setBacktestRange(meta.backtest_range);
          if (meta.weather_proxy_note) setWeatherProxyNote(meta.weather_proxy_note);
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
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Forecast
        </h1>

        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Date
            </label>
            <DatePicker
              value={date}
              onChange={handleDateChange}
              minDate={backtestRange?.start}
              maxDate={backtestRange?.end}
            />
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => handleViewChange('day')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                view === 'day'
                  ? 'bg-[#1d4ed8] text-white shadow-sm'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              Day-ahead
            </button>
            <button
              type="button"
              onClick={() => handleViewChange('week')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                view === 'week'
                  ? 'bg-[#1d4ed8] text-white shadow-sm'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
              }`}
            >
              Week-ahead
            </button>
          </div>

          <div className="flex flex-col">
            <label className="text-xs text-slate-600 mb-1.5 font-normal">
              Model
            </label>
            <ModelSelect value={model} onChange={handleModelChange} />
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
            <p className="text-slate-900 font-semibold">
              Forecast Bands & Operational Caveats
            </p>
            <p>
              {weatherProxyNote ||
                'Backtests use observed weather plus horizon-scaled noise as a stand-in for archived weather forecasts.'}
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-600">
              <li>
                <strong className="text-slate-800">P10 to P90:</strong> 80% conformal coverage interval.
              </li>
              <li>
                <strong className="text-slate-800">P05 to P95:</strong> 90% conformal coverage interval for tail hedging.
              </li>
              <li>
                <strong className="text-slate-800">Peak threshold:</strong> 90th percentile daily peak load in the training window.
              </li>
            </ul>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-8">
          <ChartCard
            title="Actual vs P50, with uncertainty bands"
            units="MW"
            loading={loadingForecast}
            error={
              errorCode === 'DATE_OUT_OF_RANGE'
                ? `Date ${date} is outside the backtest range (${backtestRange?.start || '2024-01-01'} to ${backtestRange?.end || '2024-12-31'}).`
                : error
            }
            empty={!forecastData || forecastData.points.length === 0}
            className="h-full"
          >
            {forecastData && <ForecastChart data={forecastData} view={view} />}
          </ChartCard>
        </div>

        <div className="lg:col-span-4">
          <PeakCard data={peakData} loading={loadingPeak} />
        </div>
      </div>
    </div>
  );
};
