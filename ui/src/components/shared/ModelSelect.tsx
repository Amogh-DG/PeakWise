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
          setModelList(res.models.map((m: ModelItem) => ({ id: m.id, label: m.label })));
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
        className="bg-brand-surface text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-accent/50 focus:border-brand-accent disabled:opacity-50 cursor-pointer"
      >
        {modelList.map((m) => (
          <option key={m.id} value={m.id} className="bg-brand-surface text-brand-text">
            {m.label}
          </option>
        ))}
      </select>
    </div>
  );
};
