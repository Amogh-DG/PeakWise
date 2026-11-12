import React from 'react';
import { PeakDayResponse, PeakOutcome } from '../../api/types';

interface PeakCardProps {
  data: PeakDayResponse | null;
  loading?: boolean;
}

const OUTCOME_CONFIG: Record<
  PeakOutcome,
  { label: string; description: string; badgeClass: string }
> = {
  hit: {
    label: 'Hit',
    description: 'Predicted peak & was peak',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  },
  miss: {
    label: 'Miss',
    description: 'Under-predicted peak',
    badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  },
  false_alarm: {
    label: 'False Alarm',
    description: 'Predicted peak, was not peak',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  },
  correct_reject: {
    label: 'Correct Reject',
    description: 'Correctly predicted non-peak',
    badgeClass: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  },
};

export const PeakCard: React.FC<PeakCardProps> = ({ data, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-brand-surface border border-brand-border rounded-xl p-6 flex flex-col justify-between h-full min-h-[360px] animate-pulse">
        <div className="space-y-4">
          <div className="h-5 bg-brand-bg rounded w-24"></div>
          <div className="h-4 bg-brand-bg rounded w-32"></div>
          <div className="h-12 bg-brand-bg rounded w-28"></div>
          <div className="h-4 bg-brand-bg rounded w-44"></div>
          <div className="h-4 bg-brand-bg rounded w-48"></div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-brand-surface border border-brand-border rounded-xl p-6 flex flex-col items-center justify-center h-full min-h-[360px] text-center">
        <span className="text-sm text-brand-muted">No peak event data for this date</span>
      </div>
    );
  }

  const probPercent = Math.round(data.peak_probability * 100);
  const outcomeInfo = data.outcome ? OUTCOME_CONFIG[data.outcome] : null;

  const formatTime = (ts: string) => {
    try {
      const dt = new Date(ts);
      return dt.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'Asia/Kolkata',
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="bg-brand-surface border border-brand-border rounded-xl p-6 flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-brand-border">
          <h3 className="text-base font-semibold text-brand-text">Peak Card</h3>
          <span className="text-xs font-mono text-brand-muted">
            Threshold: {data.threshold_mw.toLocaleString()} MW
          </span>
        </div>

        <div className="mt-5 space-y-5">
          <div>
            <span className="text-xs font-medium text-brand-muted uppercase tracking-wider block">
              Peak Probability
            </span>
            <div className="flex items-baseline space-x-2 mt-1">
              <span className={`text-4xl font-extrabold font-mono tracking-tight ${
                probPercent >= 70 ? 'text-amber-400' : 'text-brand-text'
              }`}>
                {probPercent}%
              </span>
              <span className="text-xs text-brand-muted">
                (cut-off: {Math.round(data.decision_threshold * 100)}%)
              </span>
            </div>
          </div>

          <div className="space-y-1 text-sm">
            <div className="text-brand-text">
              <span className="text-brand-muted text-xs block">Predicted Peak Time</span>
              <span className="font-semibold font-mono">
                {formatTime(data.predicted_peak_ts)} IST (Hour {data.predicted_peak_hour}:00)
              </span>
            </div>
            <div className="text-xs text-brand-muted">
              Range: <span className="font-mono text-brand-text font-medium">{Math.round(data.predicted_peak_mw.p10).toLocaleString()}</span> to{' '}
              <span className="font-mono text-brand-text font-medium">{Math.round(data.predicted_peak_mw.p90).toLocaleString()} MW</span>{' '}
              <span className="text-[11px] font-mono text-brand-muted">(P50: {Math.round(data.predicted_peak_mw.p50).toLocaleString()} MW)</span>
            </div>
          </div>

          {data.actual && (
            <div className="pt-3 border-t border-brand-border space-y-1 text-sm">
              <span className="text-brand-muted text-xs block">Observed Peak</span>
              <div className="font-semibold font-mono text-brand-text">
                {Math.round(data.actual.peak_mw).toLocaleString()} MW at {formatTime(data.actual.peak_ts)} IST
              </div>
            </div>
          )}

          {outcomeInfo && (
            <div className="pt-3 border-t border-brand-border">
              <span className="text-brand-muted text-xs block mb-1.5">Classifier Outcome</span>
              <div className="flex items-center space-x-2">
                <span className={`px-2.5 py-0.5 rounded-full border text-xs font-semibold font-mono uppercase tracking-wide ${outcomeInfo.badgeClass}`}>
                  {outcomeInfo.label}
                </span>
                <span className="text-xs text-brand-muted">{outcomeInfo.description}</span>
              </div>
            </div>
          )}

          <div className="pt-3 border-t border-brand-border grid grid-cols-2 gap-3">
            <div>
              <span className="text-[11px] text-brand-muted block">Timing Error</span>
              <span className="text-xs font-mono font-medium text-brand-text">
                {data.timing_error_min !== null
                  ? `${data.timing_error_min > 0 ? '+' : ''}${data.timing_error_min} min`
                  : 'N/A'}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-brand-muted block">Magnitude Error</span>
              <span className="text-xs font-mono font-medium text-brand-text">
                {data.magnitude_error_mw !== null
                  ? `${data.magnitude_error_mw > 0 ? '+' : ''}${data.magnitude_error_mw.toFixed(1)} MW`
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
