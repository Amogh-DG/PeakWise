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
  const getDeltaBadge = () => {
    if (!delta) return null;
    const colorClasses =
      deltaType === 'positive'
        ? 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50'
        : deltaType === 'negative'
        ? 'text-red-400 bg-red-950/40 border-red-800/50'
        : 'text-brand-muted bg-brand-bg border-brand-border';

    return (
      <span className={`text-xs px-2 py-0.5 rounded-full border font-mono font-medium ${colorClasses}`}>
        {delta}
      </span>
    );
  };

  return (
    <div className={`bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm flex flex-col justify-between ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">{label}</span>
        {getDeltaBadge()}
      </div>
      <div className="flex items-baseline space-x-1.5">
        <span className="text-2xl font-bold font-mono tracking-tight text-brand-text">{value}</span>
        {unit && <span className="text-xs font-mono text-brand-muted">{unit}</span>}
      </div>
      {subtitle && <p className="text-xs text-brand-muted mt-1">{subtitle}</p>}
    </div>
  );
};
