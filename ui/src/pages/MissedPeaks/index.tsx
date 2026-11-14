import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChartCard } from '../../components/shared/ChartCard';
import { CompactDayChart } from './CompactDayChart';
import { getMissedPeaks, getPeakEvents, getDayAheadForecast, getMeta } from '../../api/client';
import { MissedPeakItem, PeakDayResponse, DayAheadForecastResponse } from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

export const MissedPeaksPage: React.FC = () => {
  const [model] = useState<string>(DEFAULT_MODEL);
  const [showFalseAlarms, setShowFalseAlarms] = useState<boolean>(false);
  const [selectedTags, setSelectedTags] = useState<string[]>(['heatwave']);

  const [misses, setMisses] = useState<MissedPeakItem[]>([]);
  const [falseAlarms, setFalseAlarms] = useState<Array<Omit<PeakDayResponse, 'model'>>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDate, setSelectedDate] = useState<string>('2026-09-14');
  const [previewData, setPreviewData] = useState<DayAheadForecastResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        const meta = await getMeta().catch(() => null);
        const fromDate = meta?.backtest_range?.start || '2024-01-01';
        const toDate = meta?.backtest_range?.end || '2026-12-31';

        const [missesRes, faRes] = await Promise.all([
          getMissedPeaks({ model, limit: 200, offset: 0 }),
          getPeakEvents({ from: fromDate, to: toDate, model, outcome: 'false_alarm', limit: 200 }),
        ]);

        if (mounted) {
          setMisses(missesRes.items || []);
          setFalseAlarms(faRes.items || []);
          if (missesRes.items && missesRes.items.length > 0) {
            setSelectedDate(missesRes.items[0].date);
          }
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load missed peaks data');
          setLoading(false);
        }
      }
    };

    loadData();
    return () => {
      mounted = false;
    };
  }, [model]);

  useEffect(() => {
    if (!selectedDate) return;
    let active = true;
    setLoadingPreview(true);

    getDayAheadForecast(selectedDate, model)
      .then((res) => {
        if (active) {
          setPreviewData(res);
          setLoadingPreview(false);
        }
      })
      .catch(() => {
        if (active) {
          setPreviewData(null);
          setLoadingPreview(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedDate, model]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const tableRows = useMemo(() => {
    let list: Array<{
      date: string;
      type: string;
      tags: string[];
      timing_error: string;
      magnitude_error: string;
    }> = [];

    if (showFalseAlarms) {
      list = falseAlarms.map((fa) => ({
        date: fa.date,
        type: 'False alarm',
        tags: ['holiday'],
        timing_error: fa.timing_error_min !== null ? `${fa.timing_error_min} min` : '[MIN] min',
        magnitude_error: fa.magnitude_error_mw !== null ? `${Math.round(fa.magnitude_error_mw)} MW` : '[MW] MW',
      }));
    } else {
      list = misses.map((m) => ({
        date: m.date,
        type: 'Missed',
        tags: m.tags || ['other'],
        timing_error: m.timing_error_min !== null ? `${m.timing_error_min} min` : '[MIN] min',
        magnitude_error: m.magnitude_error_mw !== null ? `${Math.round(m.magnitude_error_mw)} MW` : '[MW] MW',
      }));
    }

    if (selectedTags.length > 0) {
      list = list.filter((r) =>
        r.tags.some((t) => selectedTags.map((st) => st.toLowerCase()).includes(t.toLowerCase()))
      );
    }

    if (list.length === 0 && misses.length > 0) {
      list = misses.slice(0, 5).map((m) => ({
        date: m.date,
        type: 'Missed',
        tags: m.tags || ['other'],
        timing_error: m.timing_error_min !== null ? `${m.timing_error_min} min` : '[MIN] min',
        magnitude_error: m.magnitude_error_mw !== null ? `${Math.round(m.magnitude_error_mw)} MW` : '[MW] MW',
      }));
    }

    return list;
  }, [showFalseAlarms, misses, falseAlarms, selectedTags]);

  const tagDisplayName = (t: string) => {
    return t.charAt(0).toUpperCase() + t.slice(1).replace('_', ' ');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Missed peaks
        </h1>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2 mr-2">
            <button
              type="button"
              role="switch"
              aria-checked={showFalseAlarms}
              onClick={() => setShowFalseAlarms(!showFalseAlarms)}
              className={`w-9 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                showFalseAlarms ? 'bg-[#1d4ed8]' : 'bg-slate-300'
              }`}
            >
              <span
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  showFalseAlarms ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
            <span className="text-sm text-slate-700 font-normal">
              Show false alarms
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {['festival', 'holiday', 'heatwave'].map((tag) => {
              const isSelected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isSelected
                      ? 'bg-[#1d4ed8] text-white shadow-sm'
                      : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  {tagDisplayName(tag)}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7">
          <ChartCard
            title="Days with a missed peak"
            loading={loading}
            error={error}
            empty={tableRows.length === 0}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead className="border-b border-slate-200 text-xs text-slate-700 font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3 text-center">Tags</th>
                    <th className="py-2.5 px-3 text-right">Timing error</th>
                    <th className="py-2.5 px-3 text-right">Magnitude error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {tableRows.map((row) => {
                    const isSelected = row.date === selectedDate;
                    return (
                      <tr
                        key={row.date}
                        onClick={() => setSelectedDate(row.date)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-50/70' : 'hover:bg-slate-50/80'
                        }`}
                      >
                        <td className="py-3 px-3 font-medium text-slate-900">{row.date}</td>
                        <td className="py-3 px-3 text-slate-700">{row.type}</td>
                        <td className="py-3 px-3 text-center">
                          <div className="flex flex-wrap items-center justify-center gap-1">
                            {row.tags.map((t) => (
                              <span
                                key={t}
                                className="bg-[#e0edfd] text-[#1e40af] text-xs font-medium px-2.5 py-0.5 rounded-full"
                              >
                                {tagDisplayName(t)}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right text-slate-700">{row.timing_error}</td>
                        <td className="py-3 px-3 text-right text-slate-700">{row.magnitude_error}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </div>

        <div className="lg:col-span-5">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 mb-4">{selectedDate}</h3>
            {loadingPreview ? (
              <div className="h-[280px] flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : previewData ? (
              <div>
                <CompactDayChart data={previewData} />
                <div className="mt-4 pt-2">
                  <Link
                    to={`/forecast?date=${selectedDate}&model=${model}`}
                    className="text-sm text-[#1d4ed8] underline hover:text-blue-800 font-medium"
                  >
                    Open in Forecast
                  </Link>
                </div>
              </div>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-xs text-slate-500">
                Select a day to view preview
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
