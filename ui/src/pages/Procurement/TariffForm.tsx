import React from 'react';
import { ProcurementTariff } from '../../api/types';

interface TariffFormProps {
  tariff: ProcurementTariff;
  onChange: (t: ProcurementTariff) => void;
  peakWindow?: string;
  onPeakWindowChange?: (w: string) => void;
}

export const TariffForm: React.FC<TariffFormProps> = ({
  tariff,
  onChange,
  peakWindow = '18:00 to 22:00',
  onPeakWindowChange,
}) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
      <div>
        <h3 className="text-base font-bold text-slate-900 mb-4">Tariff</h3>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-600 font-normal mb-1.5 block">
              Peak tariff
            </label>
            <input
              type="text"
              value={tariff.under_price_inr_per_mwh || ''}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || 0;
                onChange({ ...tariff, under_price_inr_per_mwh: val });
              }}
              placeholder="[YOUR RATE]"
              className="w-full bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-slate-600 font-normal mb-1.5 block">
              Off-peak tariff
            </label>
            <input
              type="text"
              value={tariff.da_price_inr_per_mwh || ''}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || 0;
                onChange({ ...tariff, da_price_inr_per_mwh: val });
              }}
              placeholder="[YOUR RATE]"
              className="w-full bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="text-xs text-slate-600 font-normal mb-1.5 block">
              Peak window
            </label>
            <input
              type="text"
              value={peakWindow}
              onChange={(e) => onPeakWindowChange && onPeakWindowChange(e.target.value)}
              placeholder="18:00 to 22:00"
              className="w-full bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
