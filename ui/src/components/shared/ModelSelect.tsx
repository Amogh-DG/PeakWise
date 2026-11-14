import React, { useEffect, useState } from 'react';
import { getModels } from '../../api/client';
import { ModelItem } from '../../api/types';
import { MODELS, MODEL_LABELS, DEFAULT_MODEL } from '../../constants/models';

interface ModelSelectProps {
  value?: string;
  onChange: (model: string) => void;
  disabled?: boolean;
  className?: string;
}

export const ModelSelect: React.FC<ModelSelectProps> = ({
  value = DEFAULT_MODEL,
  onChange,
  disabled = false,
  className = '',
}) => {
  const [modelList, setModelList] = useState<Array<{ id: string; label: string }>>(
    MODELS.map((m) => ({ id: m, label: MODEL_LABELS[m] || m }))
  );

  useEffect(() => {
    let mounted = true;
    getModels()
      .then((res) => {
        if (mounted && res?.models?.length) {
          setModelList(
            res.models.map((m: ModelItem) => ({
              id: m.id,
              label: MODEL_LABELS[m.id as keyof typeof MODEL_LABELS] || m.label,
            }))
          );
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className={`relative inline-block ${className}`}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="bg-white text-slate-800 border border-slate-300 rounded-lg px-3.5 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 cursor-pointer min-w-[220px]"
      >
        {modelList.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>
    </div>
  );
};
