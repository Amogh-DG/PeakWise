import React from 'react';
import { PeakMetricRow } from '../../api/types';

interface PeakEventsCardProps {
  rows: PeakMetricRow[];
  thresholdDefinition?: string;
}

export const PeakEventsCard: React.FC<PeakEventsCardProps> = ({
  rows,
  thresholdDefinition,
}) => {
  const classifierRow = rows.find(
    (r) => r.classifier === 'lgbm_clf' || r.model === 'ensemble'
  ) || rows[0];

  const ruleRow = rows.find(
    (r) => r.classifier.startsWith('rule') || r.model === 'seasonal_naive'
  ) || (rows.length > 1 ? rows[1] : undefined);

  const renderMetricComparison = (
    label: string,
    val1: number | string,
    val2: number | string | undefined,
    format: (v: number) => string = (v) => String(v),
    higherIsBetter: boolean = true
  ) => {
    const num1 = typeof val1 === 'number' ? val1 : null;
    const num2 = typeof val2 === 'number' ? val2 : null;
    let isBetter1 = false;
    if (num1 !== null && num2 !== null) {
      isBetter1 = higherIsBetter ? num1 > num2 : num1 < num2;
    }

    return (
      <div className="flex items-center justify-between py-2 border-b border-brand-border/40 text-xs">
        <span className="text-brand-muted font-medium">{label}</span>
        <div className="flex items-center space-x-6 font-mono">
          <span
            className={`font-semibold ${
              isBetter1 ? 'text-emerald-400 font-bold' : 'text-brand-text'
            }`}
          >
            {typeof val1 === 'number' ? format(val1) : val1}
          </span>
          <span className="text-brand-muted/80 w-16 text-right">
            {val2 !== undefined && typeof val2 === 'number'
              ? format(val2)
              : val2 ?? '—'}
          </span>
        </div>
      </div>
    );
  };

  const renderConfusionMatrix = (
    title: string,
    confusion: PeakMetricRow['confusion']
  ) => {
    const total = confusion.tp + confusion.fp + confusion.fn + confusion.tn;
    return (
      <div className="bg-brand-bg/60 border border-brand-border rounded-lg p-3">
        <div className="text-xs font-semibold text-brand-text mb-2 flex items-center justify-between">
          <span>{title} Matrix</span>
          <span className="text-[10px] text-brand-muted font-mono">N = {total}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs font-mono">
          <div className="bg-emerald-950/20 border border-emerald-800/40 rounded p-2">
            <div className="text-[10px] text-emerald-400/80 uppercase">True Positive (TP)</div>
            <div className="text-base font-bold text-emerald-300 mt-0.5">{confusion.tp}</div>
          </div>
          <div className="bg-red-950/20 border border-red-800/40 rounded p-2">
            <div className="text-[10px] text-red-400/80 uppercase">False Positive (FP)</div>
            <div className="text-base font-bold text-red-400 mt-0.5">{confusion.fp}</div>
          </div>
          <div className="bg-amber-950/20 border border-amber-800/40 rounded p-2">
            <div className="text-[10px] text-amber-400/80 uppercase">False Negative (FN)</div>
            <div className="text-base font-bold text-amber-400 mt-0.5">{confusion.fn}</div>
          </div>
          <div className="bg-brand-surface/40 border border-brand-border rounded p-2">
            <div className="text-[10px] text-brand-muted uppercase">True Negative (TN)</div>
            <div className="text-base font-bold text-brand-muted mt-0.5">{confusion.tn}</div>
          </div>
        </div>
      </div>
    );
  };

  if (!classifierRow) {
    return (
      <div className="text-xs text-brand-muted py-6 text-center">
        No peak metrics data available
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {thresholdDefinition && (
        <div className="bg-brand-bg/40 border border-brand-border/60 rounded-lg px-3.5 py-2 text-xs text-brand-muted flex items-center justify-between">
          <span className="font-medium text-brand-text/90">Peak Event Definition:</span>
          <span className="font-mono text-[11px] text-brand-muted">{thresholdDefinition}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-brand-border">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-muted">
              Classification & Timing Metric
            </span>
            <div className="flex items-center space-x-6 text-xs font-mono">
              <span className="text-emerald-400 font-semibold">
                {classifierRow.model} ({classifierRow.classifier})
              </span>
              <span className="text-brand-muted w-16 text-right">
                {ruleRow ? ruleRow.model : 'Rule Baseline'}
              </span>
            </div>
          </div>

          <div className="space-y-0.5">
            {renderMetricComparison(
              'Precision',
              classifierRow.precision,
              ruleRow?.precision,
              (v) => `${(v * 100).toFixed(1)}%`,
              true
            )}
            {renderMetricComparison(
              'Recall (Sensitivity)',
              classifierRow.recall,
              ruleRow?.recall,
              (v) => `${(v * 100).toFixed(1)}%`,
              true
            )}
            {renderMetricComparison(
              'F1 Score',
              classifierRow.f1,
              ruleRow?.f1,
              (v) => v.toFixed(3),
              true
            )}
            {renderMetricComparison(
              'PR-AUC',
              classifierRow.pr_auc,
              ruleRow?.pr_auc,
              (v) => v.toFixed(3),
              true
            )}
            {renderMetricComparison(
              'Timing MAE',
              classifierRow.timing_mae_min,
              ruleRow?.timing_mae_min,
              (v) => `${Math.round(v)} min`,
              false
            )}
            {renderMetricComparison(
              'Timing within ±1 hour',
              classifierRow.timing_within_1h_pct,
              ruleRow?.timing_within_1h_pct,
              (v) => `${(v * 100).toFixed(1)}%`,
              true
            )}
            {renderMetricComparison(
              'Peak Magnitude MAE',
              classifierRow.magnitude_mae_mw,
              ruleRow?.magnitude_mae_mw,
              (v) => `${v.toFixed(1)} MW`,
              false
            )}
            {renderMetricComparison(
              'Peak Magnitude Bias',
              classifierRow.magnitude_bias_mw,
              ruleRow?.magnitude_bias_mw,
              (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)} MW`,
              false
            )}
            {renderMetricComparison(
              'Decision Threshold',
              classifierRow.decision_threshold,
              ruleRow?.decision_threshold,
              (v) => v.toFixed(2),
              true
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-brand-muted pb-2 border-b border-brand-border">
            Contingency / Confusion Matrices
          </div>
          <div className="space-y-3">
            {renderConfusionMatrix(
              `${classifierRow.model} (${classifierRow.classifier})`,
              classifierRow.confusion
            )}
            {ruleRow &&
              renderConfusionMatrix(
                `${ruleRow.model} (${ruleRow.classifier})`,
                ruleRow.confusion
              )}
          </div>
        </div>
      </div>
    </div>
  );
};

