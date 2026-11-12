import React from 'react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  units?: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
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
}) => {
  return (
    <div className={`bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-semibold text-brand-text">{title}</h3>
            {units && (
              <span className="text-xs px-2 py-0.5 rounded bg-brand-bg text-brand-muted border border-brand-border font-mono">
                {units}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-brand-muted mt-1">{subtitle}</p>}
        </div>
        {action && <div>{action}</div>}
      </div>

      <div className="flex-1 min-h-[280px] flex flex-col justify-center">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-3 py-12">
            <div className="w-8 h-8 border-2 border-brand-accent border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-brand-muted font-mono">Loading chart data...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center bg-red-950/20 border border-red-900/30 rounded-lg">
            <span className="text-red-400 font-medium text-sm mb-1">Failed to load chart</span>
            <span className="text-xs text-brand-muted">{error}</span>
          </div>
        ) : empty ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <span className="text-xs text-brand-muted">{emptyMessage}</span>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
};
