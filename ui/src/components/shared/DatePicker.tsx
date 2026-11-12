import React, { useEffect, useState } from 'react';
import { getMeta } from '../../api/client';

interface DatePickerProps {
  value: string;
  onChange: (date: string) => void;
  minDate?: string;
  maxDate?: string;
  disabled?: boolean;
  className?: string;
}

export const DatePicker: React.FC<DatePickerProps> = ({
  value,
  onChange,
  minDate,
  maxDate,
  disabled = false,
  className = '',
}) => {
  const [min, setMin] = useState<string>(minDate || '');
  const [max, setMax] = useState<string>(maxDate || '');

  useEffect(() => {
    if (minDate) setMin(minDate);
    if (maxDate) setMax(maxDate);
    if (!minDate || !maxDate) {
      let mounted = true;
      getMeta()
        .then((res) => {
          if (mounted && res?.backtest_range) {
            if (!minDate && res.backtest_range.start) setMin(res.backtest_range.start);
            if (!maxDate && res.backtest_range.end) setMax(res.backtest_range.end);
          }
        })
        .catch(() => {});
      return () => {
        mounted = false;
      };
    }
  }, [minDate, maxDate]);

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <input
        type="date"
        value={value}
        min={min || undefined}
        max={max || undefined}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="bg-brand-surface text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-accent/50 focus:border-brand-accent disabled:opacity-50 cursor-pointer"
      />
    </div>
  );
};
