import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CompactDayChart } from './CompactDayChart';
import { getDayAheadForecast } from '../../api/client';
import { DayAheadForecastResponse, MissedPeakItem, PeakDayResponse } from '../../api/types';

interface DrillDownPanelProps {
  item: MissedPeakItem | (Omit<PeakDayResponse, 'model'> & { model: string; tags?: string[]; note?: string });
  model: string;
  onClose: () => void;
}

export const DrillDownPanel: React.FC<DrillDownPanelProps> = ({ item, model, onClose }) => {
  const [data, setData] = useState<DayAheadForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    getDayAheadForecast(item.date, model)
      .then((res) => {
        if (mounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load day forecast');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [item.date, model]);

  const p50Val = 'pred_peak_mw_p50' in item
    ? item.pred_peak_mw_p50
    : item.predicted_peak_mw?.p50;

  const actualVal = 'actual_peak_mw' in item
    ? item.actual_peak_mw
    : item.actual?.peak_mw;

  return (
    <div className="bg-brand-surface border border-brand-accent/40 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-brand-border">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold text-brand-text">Day Post-Mortem: {item.date}</span>
            <span className="text-xs px-2 py-0.5 rounded bg-brand-bg font-mono border border-brand-border text-brand-muted">
              {model}
            </span>
          </div>
          {item.note && (
            <p className="text-xs text-brand-muted mt-1 italic">{item.note}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <Link
            to={`/forecast?date=${item.date}&model=${model}&view=day`}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-brand-accent text-brand-bg hover:opacity-90 transition-opacity"
          >
            Open in Forecast Page →
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-xs text-brand-muted hover:text-brand-text rounded-md hover:bg-brand-bg transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="bg-brand-bg/50 p-2.5 rounded-lg border border-brand-border">
          <span className="text-[10px] text-brand-muted block uppercase">Pred Peak P50</span>
          <span className="text-brand-text font-bold">{p50Val ? `${p50Val.toFixed(0)} MW` : '—'}</span>
        </div>
        <div className="bg-brand-bg/50 p-2.5 rounded-lg border border-brand-border">
          <span className="text-[10px] text-brand-muted block uppercase">Actual Peak</span>
          <span className="text-brand-text font-bold">{actualVal ? `${actualVal.toFixed(0)} MW` : '—'}</span>
        </div>
        <div className="bg-brand-bg/50 p-2.5 rounded-lg border border-brand-border">
          <span className="text-[10px] text-brand-muted block uppercase">Magnitude Err</span>
          <span className={item.magnitude_error_mw && item.magnitude_error_mw < 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
            {item.magnitude_error_mw ? `${item.magnitude_error_mw > 0 ? '+' : ''}${item.magnitude_error_mw.toFixed(0)} MW` : '—'}
          </span>
        </div>
        <div className="bg-brand-bg/50 p-2.5 rounded-lg border border-brand-border">
          <span className="text-[10px] text-brand-muted block uppercase">Timing Err</span>
          <span className="text-brand-text font-bold">
            {item.timing_error_min !== null && item.timing_error_min !== undefined
              ? `${item.timing_error_min > 0 ? '+' : ''}${item.timing_error_min} min`
              : '—'}
          </span>
        </div>
      </div>

      <div className="min-h-[260px] flex items-center justify-center">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 space-y-2">
            <div className="w-6 h-6 border-2 border-brand-accent border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-brand-muted font-mono">Loading day profile...</span>
          </div>
        ) : error ? (
          <div className="text-xs text-red-400 p-4 text-center">{error}</div>
        ) : data ? (
          <CompactDayChart data={data} />
        ) : null}
      </div>
    </div>
  );
};

