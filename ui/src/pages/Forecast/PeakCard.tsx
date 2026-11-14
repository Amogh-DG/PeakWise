import React from 'react';
import { PeakDayResponse } from '../../api/types';

interface PeakCardProps {
  data: PeakDayResponse | null;
  loading?: boolean;
}

export const PeakCard: React.FC<PeakCardProps> = ({ data, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm min-h-[360px] flex flex-col justify-between animate-pulse">
        <div className="space-y-4">
          <div className="h-5 bg-slate-100 rounded w-24"></div>
          <div className="h-4 bg-slate-100 rounded w-32"></div>
          <div className="h-12 bg-slate-100 rounded w-28"></div>
          <div className="h-4 bg-slate-100 rounded w-44"></div>
        </div>
      </div>
    );
  }

  const probPercent = data ? Math.round(data.peak_probability * 100) : 72;
  const predTime = data?.predicted_peak_ts
    ? new Date(data.predicted_peak_ts).toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'Asia/Kolkata',
      })
    : '19:30';

  const lowMw = data?.predicted_peak_mw?.p10 ? Math.round(data.predicted_peak_mw.p10).toLocaleString() : '[LOW]';
  const highMw = data?.predicted_peak_mw?.p90 ? Math.round(data.predicted_peak_mw.p90).toLocaleString() : '[HIGH]';

  const outcomeLabel = data?.outcome
    ? data.outcome === 'hit'
      ? 'Hit'
      : data.outcome === 'miss'
      ? 'Miss'
      : data.outcome === 'false_alarm'
      ? 'False Alarm'
      : 'Correct Reject'
    : 'Hit';

  const timingErr = data?.timing_error_min !== undefined && data?.timing_error_min !== null
    ? `${data.timing_error_min >= 0 ? '+' : ''}${data.timing_error_min}`
    : '[+/- MIN]';

  const magErr = data?.magnitude_error_mw !== undefined && data?.magnitude_error_mw !== null
    ? `${data.magnitude_error_mw >= 0 ? '+' : ''}${Math.round(data.magnitude_error_mw)}`
    : '[+/- MW]';

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full min-h-[380px]">
      <div>
        <h3 className="text-base font-bold text-slate-900 mb-4">Peak card</h3>

        <div className="space-y-4">
          <div>
            <span className="text-xs text-slate-500 font-normal block">Peak probability</span>
            <div className="text-5xl font-bold text-[#c2410c] mt-1 tracking-tight">
              {probPercent}%
            </div>
          </div>

          <div className="space-y-1 text-sm text-slate-800">
            <div>Predicted peak {predTime}</div>
            <div>Range {lowMw} to {highMw} MW</div>
          </div>

          <div className="pt-2">
            <div className="flex items-center">
              <span className="bg-[#e0edfd] text-[#1e40af] text-xs font-semibold px-2.5 py-0.5 rounded-md mr-2">
                {outcomeLabel}
              </span>
              <span className="text-xs text-slate-500">
                Outcome: hit, miss, false alarm or correct reject
              </span>
            </div>
          </div>

          <div className="space-y-1 text-sm text-slate-700 pt-1">
            <div>Timing error: {timingErr} min</div>
            <div>Magnitude error: {magErr} MW</div>
          </div>
        </div>
      </div>
    </div>
  );
};
