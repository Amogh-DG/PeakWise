import React, { useState, useEffect, useMemo } from 'react';
import { ModelSelect } from '../../components/shared/ModelSelect';
import { ChartCard } from '../../components/shared/ChartCard';
import { StatTile } from '../../components/shared/StatTile';
import { DrillDownPanel } from './DrillDownPanel';
import { getMissedPeaks, getPeakEvents, getMeta } from '../../api/client';
import { MissedPeakItem, PeakDayResponse } from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

type TabType = 'misses' | 'false_alarms';

const ALL_TAGS = ['festival', 'holiday', 'heatwave', 'weather_miss', 'weekend', 'other'] as const;

type SortField = 'date' | 'magnitude_error_mw' | 'timing_error_min' | 'peak_probability';

export const MissedPeaksPage: React.FC = () => {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [activeTab, setActiveTab] = useState<TabType>('misses');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const [misses, setMisses] = useState<MissedPeakItem[]>([]);
  const [falseAlarms, setFalseAlarms] = useState<Array<Omit<PeakDayResponse, 'model'>>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [sortField, setSortField] = useState<SortField>('magnitude_error_mw');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const [selectedItem, setSelectedItem] = useState<MissedPeakItem | (Omit<PeakDayResponse, 'model'> & { model: string; tags?: string[]; note?: string }) | null>(null);

  const [page, setPage] = useState<number>(0);
  const pageSize = 50;

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        const meta = await getMeta().catch(() => null);
        const fromDate = meta?.backtest_range?.start || '2024-01-01';
        const toDate = meta?.backtest_range?.end || '2024-12-31';

        const [missesRes, faRes] = await Promise.all([
          getMissedPeaks({ model, limit: 200, offset: 0 }),
          getPeakEvents({ from: fromDate, to: toDate, model, outcome: 'false_alarm', limit: 200 }),
        ]);

        if (mounted) {
          setMisses(missesRes.items || []);
          setFalseAlarms(faRes.items || []);
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

  const toggleTag = (tag: string) => {
    setPage(0);
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const filteredMisses = useMemo(() => {
    let res = misses;
    if (selectedTags.length > 0) {
      res = res.filter((item) =>
        item.tags && item.tags.some((t) => selectedTags.includes(t))
      );
    }
    return [...res].sort((a, b) => {
      let valA: number = 0;
      let valB: number = 0;

      if (sortField === 'magnitude_error_mw') {
        valA = Math.abs(a.magnitude_error_mw ?? 0);
        valB = Math.abs(b.magnitude_error_mw ?? 0);
      } else if (sortField === 'timing_error_min') {
        valA = Math.abs(a.timing_error_min ?? 0);
        valB = Math.abs(b.timing_error_min ?? 0);
      } else if (sortField === 'peak_probability') {
        valA = a.peak_probability ?? 0;
        valB = b.peak_probability ?? 0;
      } else if (sortField === 'date') {
        return sortDirection === 'asc'
          ? a.date.localeCompare(b.date)
          : b.date.localeCompare(a.date);
      }

      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
  }, [misses, selectedTags, sortField, sortDirection]);

  const filteredFalseAlarms = useMemo(() => {
    return [...falseAlarms].sort((a, b) => {
      let valA: number = 0;
      let valB: number = 0;

      if (sortField === 'magnitude_error_mw') {
        valA = Math.abs(a.magnitude_error_mw ?? 0);
        valB = Math.abs(b.magnitude_error_mw ?? 0);
      } else if (sortField === 'timing_error_min') {
        valA = Math.abs(a.timing_error_min ?? 0);
        valB = Math.abs(b.timing_error_min ?? 0);
      } else if (sortField === 'peak_probability') {
        valA = a.peak_probability ?? 0;
        valB = b.peak_probability ?? 0;
      } else if (sortField === 'date') {
        return sortDirection === 'asc'
          ? a.date.localeCompare(b.date)
          : b.date.localeCompare(a.date);
      }

      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
  }, [falseAlarms, sortField, sortDirection]);

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const tag of ALL_TAGS) counts[tag] = 0;
    for (const item of misses) {
      if (item.tags) {
        for (const t of item.tags) {
          if (counts[t] !== undefined) counts[t]++;
        }
      }
    }
    return counts;
  }, [misses]);

  const meanMagnitudeError = useMemo(() => {
    if (misses.length === 0) return 0;
    const sum = misses.reduce((acc, m) => acc + Math.abs(m.magnitude_error_mw ?? 0), 0);
    return sum / misses.length;
  }, [misses]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const paginatedMisses = useMemo(() => {
    const start = page * pageSize;
    return filteredMisses.slice(start, start + pageSize);
  }, [filteredMisses, page, pageSize]);

  const paginatedFalseAlarms = useMemo(() => {
    const start = page * pageSize;
    return filteredFalseAlarms.slice(start, start + pageSize);
  }, [filteredFalseAlarms, page, pageSize]);

  const formatTime = (tsStr: string | null | undefined) => {
    if (!tsStr) return '—';
    try {
      const d = new Date(tsStr);
      return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' });
    } catch {
      return tsStr.split('T')[1]?.slice(0, 5) || tsStr;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Missed-Peak Drill-Down</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Post-mortem analysis of peak events where demand or probability was under-predicted.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <ModelSelect value={model} onChange={setModel} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="Missed Peaks Count"
          value={misses.length}
          subtitle={`Under-predicted by ${model}`}
        />
        <StatTile
          label="Mean Magnitude Error"
          value={meanMagnitudeError.toFixed(0)}
          unit="MW"
          subtitle="Average peak shortfall"
        />
        <StatTile
          label="False Alarms Count"
          value={falseAlarms.length}
          subtitle="Predicted peak, wasn't peak"
        />
        <StatTile
          label="Top Driver"
          value={
            Object.entries(tagCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '—'
          }
          subtitle="Most frequent diagnostic tag"
        />
      </div>

      <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold text-brand-muted uppercase tracking-wider">
          <span>Diagnostic Driver Breakdown</span>
          <span className="font-mono lowercase text-[11px]">click chip to toggle filter</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {ALL_TAGS.map((t) => {
            const count = tagCounts[t] || 0;
            const pct = misses.length > 0 ? ((count / misses.length) * 100).toFixed(0) : '0';
            const isSelected = selectedTags.includes(t);
            return (
              <button
                key={t}
                type="button"
                onClick={() => toggleTag(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors border flex items-center space-x-1.5 ${
                  isSelected
                    ? 'bg-brand-accent text-brand-bg border-brand-accent font-semibold'
                    : 'bg-brand-bg border-brand-border text-brand-muted hover:text-brand-text'
                }`}
              >
                <span>{t}</span>
                <span className={`text-[10px] px-1 py-0.2 rounded ${isSelected ? 'bg-black/20 text-brand-bg' : 'bg-brand-surface text-brand-muted'}`}>
                  {count} ({pct}%)
                </span>
              </button>
            );
          })}
          {selectedTags.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTags([])}
              className="px-2.5 py-1 text-xs text-red-400 hover:text-red-300 underline"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {selectedItem && (
        <DrillDownPanel
          item={selectedItem}
          model={model}
          onClose={() => setSelectedItem(null)}
        />
      )}

      <ChartCard
        title={activeTab === 'misses' ? 'Missed Peaks Table' : 'False Alarms Table'}
        subtitle={
          activeTab === 'misses'
            ? 'Rows where actual demand exceeded top-decile peak threshold but model under-forecasted'
            : 'Rows where model predicted a peak event that did not materialise'
        }
        action={
          <div className="flex bg-brand-bg border border-brand-border rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => {
                setActiveTab('misses');
                setSelectedItem(null);
                setPage(0);
              }}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'misses'
                  ? 'bg-brand-accent text-brand-bg font-semibold'
                  : 'text-brand-muted hover:text-brand-text'
              }`}
            >
              Misses ({filteredMisses.length})
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('false_alarms');
                setSelectedItem(null);
                setPage(0);
              }}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'false_alarms'
                  ? 'bg-brand-accent text-brand-bg font-semibold'
                  : 'text-brand-muted hover:text-brand-text'
              }`}
            >
              False Alarms ({filteredFalseAlarms.length})
            </button>
          </div>
        }
        loading={loading}
        error={error}
        empty={activeTab === 'misses' ? filteredMisses.length === 0 : filteredFalseAlarms.length === 0}
        emptyMessage={
          selectedTags.length > 0
            ? 'No peak events match the selected tag filters'
            : activeTab === 'misses'
            ? 'No missed peaks recorded for this model'
            : 'No false alarms recorded for this model'
        }
      >
        <div className="overflow-x-auto border border-brand-border rounded-lg shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-brand-bg text-brand-muted uppercase tracking-wider text-[11px] font-semibold sticky top-0 border-b border-brand-border">
              <tr>
                <th
                  onClick={() => handleSort('date')}
                  className="py-3 px-3 cursor-pointer select-none hover:text-brand-text"
                >
                  Date {sortField === 'date' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="py-3 px-3">Season</th>
                <th
                  onClick={() => handleSort('peak_probability')}
                  className="py-3 px-3 cursor-pointer select-none text-right hover:text-brand-text"
                >
                  Peak Prob {sortField === 'peak_probability' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="py-3 px-3 text-center">Pred vs Act Time</th>
                <th className="py-3 px-3 text-right">Pred P50 vs Act MW</th>
                <th
                  onClick={() => handleSort('magnitude_error_mw')}
                  className="py-3 px-3 cursor-pointer select-none text-right hover:text-brand-text"
                >
                  Magnitude Err {sortField === 'magnitude_error_mw' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('timing_error_min')}
                  className="py-3 px-3 cursor-pointer select-none text-right hover:text-brand-text"
                >
                  Timing Err {sortField === 'timing_error_min' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                {activeTab === 'misses' && <th className="py-3 px-3">Diagnostic Tags</th>}
                <th className="py-3 px-3">Note / Observation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border/40 font-mono">
              {activeTab === 'misses'
                ? paginatedMisses.map((item) => {
                    const isSelected = selectedItem?.date === item.date;
                    return (
                      <tr
                        key={item.date}
                        onClick={() => setSelectedItem(isSelected ? null : item)}
                        className={`cursor-pointer transition-colors hover:bg-brand-surface/80 ${
                          isSelected ? 'bg-brand-accent/10 border-l-2 border-brand-accent' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3 font-semibold text-brand-text whitespace-nowrap">
                          {item.date}
                        </td>
                        <td className="py-2.5 px-3 text-brand-muted capitalize">
                          {item.season}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[11px] font-bold ${
                              item.peak_probability >= 0.35
                                ? 'bg-amber-950/40 text-amber-400 border border-amber-800/40'
                                : 'bg-brand-bg text-brand-muted'
                            }`}
                          >
                            {(item.peak_probability * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center text-brand-muted whitespace-nowrap">
                          <span className="text-brand-text">{formatTime(item.pred_peak_ts)}</span>
                          <span className="text-brand-muted mx-1">→</span>
                          <span className="text-amber-400 font-semibold">{formatTime(item.actual_peak_ts)}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-brand-muted whitespace-nowrap">
                          <span>{item.pred_peak_mw_p50?.toFixed(0)}</span>
                          <span className="text-brand-muted mx-1">/</span>
                          <span className="text-brand-text font-semibold">{item.actual_peak_mw?.toFixed(0)}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap font-bold">
                          <span className={item.magnitude_error_mw < 0 ? 'text-red-400' : 'text-emerald-400'}>
                            {item.magnitude_error_mw > 0 ? '+' : ''}
                            {item.magnitude_error_mw?.toFixed(0)} MW
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          {item.timing_error_min !== null ? (
                            <span className={item.timing_error_min !== 0 ? 'text-amber-400' : 'text-brand-muted'}>
                              {item.timing_error_min > 0 ? '+' : ''}
                              {item.timing_error_min} m
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex flex-wrap gap-1">
                            {item.tags?.map((tg) => (
                              <span
                                key={tg}
                                className="text-[10px] px-1.5 py-0.2 rounded bg-brand-bg border border-brand-border text-brand-muted"
                              >
                                {tg}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-sans text-xs text-brand-muted max-w-xs truncate" title={item.note}>
                          {item.note || '—'}
                        </td>
                      </tr>
                    );
                  })
                : paginatedFalseAlarms.map((item) => {
                    const isSelected = selectedItem?.date === item.date;
                    const p50 = item.predicted_peak_mw?.p50;
                    const actMw = item.actual?.peak_mw;
                    const magErr = item.magnitude_error_mw;

                    return (
                      <tr
                        key={item.date}
                        onClick={() => setSelectedItem(isSelected ? null : { ...item, model })}
                        className={`cursor-pointer transition-colors hover:bg-brand-surface/80 ${
                          isSelected ? 'bg-brand-accent/10 border-l-2 border-brand-accent' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3 font-semibold text-brand-text whitespace-nowrap">
                          {item.date}
                        </td>
                        <td className="py-2.5 px-3 text-brand-muted">
                          —
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <span className="px-1.5 py-0.5 rounded text-[11px] font-bold bg-amber-950/40 text-amber-400 border border-amber-800/40">
                            {(item.peak_probability * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center text-brand-muted whitespace-nowrap">
                          <span className="text-brand-text">{formatTime(item.predicted_peak_ts)}</span>
                          <span className="text-brand-muted mx-1">→</span>
                          <span>{formatTime(item.actual?.peak_ts)}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-brand-muted whitespace-nowrap">
                          <span>{p50?.toFixed(0)}</span>
                          <span className="text-brand-muted mx-1">/</span>
                          <span>{actMw ? actMw.toFixed(0) : '—'}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap font-bold">
                          <span className={magErr && magErr < 0 ? 'text-red-400' : 'text-emerald-400'}>
                            {magErr ? `${magErr > 0 ? '+' : ''}${magErr.toFixed(0)} MW` : '—'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          {item.timing_error_min !== null ? `${item.timing_error_min} m` : '—'}
                        </td>
                        <td className="py-2.5 px-3 font-sans text-xs text-brand-muted">
                          Over-predicted peak probability (did not cross threshold)
                        </td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>

        {((activeTab === 'misses' && filteredMisses.length > pageSize) ||
          (activeTab === 'false_alarms' && filteredFalseAlarms.length > pageSize)) && (
          <div className="flex items-center justify-between pt-3 text-xs text-brand-muted">
            <span>
              Showing {page * pageSize + 1} to{' '}
              {Math.min(
                (page + 1) * pageSize,
                activeTab === 'misses' ? filteredMisses.length : filteredFalseAlarms.length
              )}{' '}
              of {activeTab === 'misses' ? filteredMisses.length : filteredFalseAlarms.length}
            </span>
            <div className="flex space-x-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-2.5 py-1 rounded bg-brand-bg border border-brand-border disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={
                  (page + 1) * pageSize >=
                  (activeTab === 'misses' ? filteredMisses.length : filteredFalseAlarms.length)
                }
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 rounded bg-brand-bg border border-brand-border disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </ChartCard>
    </div>
  );
};

export default MissedPeaksPage;
