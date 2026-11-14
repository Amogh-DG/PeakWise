import React from 'react';

interface StatTileProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string | number;
  deltaType?: 'positive' | 'negative' | 'neutral';
  subtitle?: string;
  className?: string;
}

export const StatTile: React.FC<StatTileProps> = ({
  label,
  value,
  unit,
  delta,
  deltaType = 'neutral',
  subtitle,
  className = '',
}) => {
  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 font-normal">{label}</span>
        {delta && (
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              deltaType === 'positive'
                ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                : deltaType === 'negative'
                ? 'text-red-700 bg-red-50 border border-red-200'
                : 'text-slate-600 bg-slate-100 border border-slate-200'
            }`}
          >
            {delta}
          </span>
        )}
      </div>
      <div className="flex items-baseline space-x-1.5">
        <span className="text-3xl font-bold tracking-tight text-slate-900">{value}</span>
        {unit && <span className="text-sm font-medium text-slate-500">{unit}</span>}
      </div>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
};
