import React from 'react';
import { ProcurementTariff } from '../../api/types';

interface TariffFormProps {
  tariff: ProcurementTariff;
  onChange: (t: ProcurementTariff) => void;
  defaultTariff: ProcurementTariff | null;
  disclaimer?: string;
  disabled?: boolean;
}

export const TariffForm: React.FC<TariffFormProps> = ({
  tariff,
  onChange,
  defaultTariff,
  disclaimer,
  disabled = false,
}) => {
  const isValid =
    tariff.under_price_inr_per_mwh > tariff.da_price_inr_per_mwh &&
    tariff.da_price_inr_per_mwh > tariff.resale_price_inr_per_mwh &&
    tariff.resale_price_inr_per_mwh >= 0;

  const handleFieldChange = (field: keyof ProcurementTariff, valueStr: string) => {
    const num = parseFloat(valueStr);
    onChange({
      ...tariff,
      [field]: isNaN(num) ? 0 : num,
    });
  };

  const handleReset = () => {
    if (defaultTariff) {
      onChange(defaultTariff);
    }
  };

  return (
    <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-brand-border pb-3">
        <div>
          <h3 className="text-sm font-bold text-brand-text">Procurement Tariff</h3>
          <p className="text-xs text-brand-muted mt-0.5">Rates in INR / MWh</p>
        </div>
        {defaultTariff && (
          <button
            type="button"
            onClick={handleReset}
            disabled={disabled}
            className="text-xs px-2.5 py-1 rounded bg-brand-surface-secondary hover:bg-brand-border text-brand-text transition-colors font-medium border border-brand-border disabled:opacity-50"
          >
            Reset Defaults
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
            Day-Ahead Base (DA)
          </label>
          <input
            type="number"
            value={tariff.da_price_inr_per_mwh}
            onChange={(e) => handleFieldChange('da_price_inr_per_mwh', e.target.value)}
            disabled={disabled}
            step="100"
            min="0"
            className="w-full bg-brand-bg text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-accent/50 disabled:opacity-50"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
            Shortfall Surcharge (Under)
          </label>
          <input
            type="number"
            value={tariff.under_price_inr_per_mwh}
            onChange={(e) => handleFieldChange('under_price_inr_per_mwh', e.target.value)}
            disabled={disabled}
            step="100"
            min="0"
            className="w-full bg-brand-bg text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-accent/50 disabled:opacity-50"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-brand-muted uppercase tracking-wider block">
            Surplus Salvage (Resale)
          </label>
          <input
            type="number"
            value={tariff.resale_price_inr_per_mwh}
            onChange={(e) => handleFieldChange('resale_price_inr_per_mwh', e.target.value)}
            disabled={disabled}
            step="100"
            min="0"
            className="w-full bg-brand-bg text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-accent/50 disabled:opacity-50"
          />
        </div>
      </div>

      {!isValid && (
        <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <span className="font-semibold">Tariff constraint violation:</span>
          <span>Ordering must satisfy Shortfall Price &gt; Day-Ahead Price &gt; Resale Price ≥ 0.</span>
        </div>
      )}

      {disclaimer && (
        <div className="pt-2 border-t border-brand-border/60 text-[11px] text-amber-500/90 leading-tight flex items-start gap-1.5">
          <span className="font-semibold uppercase tracking-wider">Note:</span>
          <span>{disclaimer}</span>
        </div>
      )}
    </div>
  );
};
