import React, { useState } from 'react';

interface ChartCardProps {
  title?: string;
  subtitle?: string;
  units?: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  showStatesButton?: boolean;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  units,
  loading = false,
  error = null,
  empty = false,
  emptyMessage = 'No data available',
  action,
  children,
  className = '',
  showStatesButton = true,
}) => {
  const [showStates, setShowStates] = useState(false);

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center space-x-2">
              {title && <h3 className="text-base font-bold text-slate-900">{title}</h3>}
              {units && (
                <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                  {units}
                </span>
              )}
            </div>
            {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}

      <div className="flex-1 min-h-[220px] flex flex-col justify-center">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-3 py-12">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500 font-mono">Loading chart data...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center bg-red-50 border border-red-200 rounded-lg">
            <span className="text-red-700 font-medium text-sm mb-1">Failed to load chart</span>
            <span className="text-xs text-slate-500">{error}</span>
          </div>
        ) : empty ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <span className="text-xs text-slate-500">{emptyMessage}</span>
          </div>
        ) : (
          children
        )}
      </div>

      {showStatesButton && (
        <div className="mt-4 pt-2">
          <button
            type="button"
            onClick={() => setShowStates(!showStates)}
            className="text-xs text-[#1d4ed8] hover:underline flex items-center gap-1 cursor-pointer font-normal"
          >
            <span>{showStates ? '▼' : '►'}</span> Chart states
          </button>
          {showStates && (
            <div className="mt-2 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
              State: {loading ? 'Loading' : error ? `Error: ${error}` : empty ? 'Empty' : 'Rendered successfully'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
