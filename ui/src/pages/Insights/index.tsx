import React, { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChartCard } from '../../components/shared/ChartCard';
import { PlotlyChart } from '../../components/shared/PlotlyChart';
import { StatTile } from '../../components/shared/StatTile';
import { getFeatureImportance, getMeta, getModels } from '../../api/client';
import {
  FeatureImportanceItem,
  MetaResponse,
  ModelItem,
} from '../../api/types';
import { MODEL_LABELS } from '../../constants/models';
import { CHART_THEME } from '../../constants/theme';

const GROUP_COLORS: Record<string, string> = {
  weather: '#38bdf8',
  thermal_inertia: '#818cf8',
  autoregressive: '#f43f5e',
  calendar: '#f59e0b',
  festival: '#ec4899',
  event: '#a855f7',
  trend: '#10b981',
  horizon: '#94a3b8',
  other: '#64748b',
};

const GROUP_LABELS: Record<string, string> = {
  weather: 'Weather (T, CDH, Heat Index)',
  thermal_inertia: 'Thermal Inertia (Rolling T)',
  autoregressive: 'Autoregressive (Lags)',
  calendar: 'Calendar (Hour, DoW)',
  festival: 'Festival (Windows, Distances)',
  event: 'Event Flags',
  trend: 'Trend / Day Count',
  horizon: 'Horizon Lead Time',
  other: 'Other',
};

export const InsightsPage: React.FC = () => {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('lgbm');
  const [features, setFeatures] = useState<FeatureImportanceItem[]>([]);
  const [loadingFeatures, setLoadingFeatures] = useState<boolean>(true);
  const [featuresError, setFeaturesError] = useState<string | null>(null);

  const [meta, setMeta] = useState<MetaResponse | null>(null);

  const [whyPeaksContent, setWhyPeaksContent] = useState<string | null>(null);
  const [loadingWhyPeaks, setLoadingWhyPeaks] = useState<boolean>(true);

  const [modelCardContent, setModelCardContent] = useState<string | null>(null);
  const [loadingModelCard, setLoadingModelCard] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    getMeta()
      .then((m) => {
        if (mounted) setMeta(m);
      })
      .catch(() => {});

    getModels()
      .then(async (res) => {
        if (!mounted) return;
        const candidateModels = (res?.models || []).map((m: ModelItem) => m.id);
        const supported: string[] = [];

        await Promise.all(
          candidateModels.map(async (mId) => {
            try {
              const fi = await getFeatureImportance(mId, 1);
              if (fi?.features && fi.features.length > 0) {
                supported.push(mId);
              }
            } catch {
            }
          })
        );

        if (mounted) {
          if (supported.length > 0) {
            setAvailableModels(supported);
            if (!supported.includes(selectedModel)) {
              setSelectedModel(supported[0]);
            }
          } else {
            setAvailableModels(['lgbm', 'xgboost']);
          }
        }
      })
      .catch(() => {
        if (mounted) setAvailableModels(['lgbm', 'xgboost']);
      });

    fetch('/insights/WHY_PEAKS_ARE_HARD.md')
      .then((res) => {
        if (!res.ok) throw new Error('Not found');
        return res.text();
      })
      .then((text) => {
        if (mounted) {
          setWhyPeaksContent(text);
          setLoadingWhyPeaks(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setWhyPeaksContent(null);
          setLoadingWhyPeaks(false);
        }
      });

    fetch('/insights/MODEL_CARD.md')
      .then((res) => {
        if (!res.ok) throw new Error('Not found');
        return res.text();
      })
      .then((text) => {
        if (mounted) {
          setModelCardContent(text);
          setLoadingModelCard(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setModelCardContent(null);
          setLoadingModelCard(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedModel) return;
    let mounted = true;
    setLoadingFeatures(true);
    setFeaturesError(null);

    getFeatureImportance(selectedModel, 20)
      .then((res) => {
        if (mounted) {
          setFeatures(res.features || []);
          setLoadingFeatures(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setFeatures([]);
          setFeaturesError(err instanceof Error ? err.message : 'Failed to load feature importance');
          setLoadingFeatures(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [selectedModel]);

  const groupBreakdown = useMemo(() => {
    if (!features || features.length === 0) return [];
    const totalImportance = features.reduce((acc, f) => acc + (f.importance || 0), 0);
    const groups: Record<string, number> = {};

    for (const f of features) {
      const g = f.group || 'other';
      groups[g] = (groups[g] || 0) + (f.importance || 0);
    }

    return Object.entries(groups)
      .map(([group, val]) => ({
        group,
        importance: val,
        sharePct: totalImportance > 0 ? (val / totalImportance) * 100 : 0,
        color: GROUP_COLORS[group] || GROUP_COLORS.other,
        label: GROUP_LABELS[group] || group,
      }))
      .sort((a, b) => b.importance - a.importance);
  }, [features]);

  const chartData = useMemo(() => {
    if (!features || features.length === 0) return [];

    const sorted = [...features].sort((a, b) => a.importance - b.importance);
    const yNames = sorted.map((f) => f.feature);
    const xVals = sorted.map((f) => f.importance);
    const colors = sorted.map((f) => GROUP_COLORS[f.group] || GROUP_COLORS.other);

    return [
      {
        type: 'bar',
        orientation: 'h',
        x: xVals,
        y: yNames,
        marker: {
          color: colors,
        },
        hovertemplate: '<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>',
      },
    ];
  }, [features]);

  const chartLayout = useMemo(() => {
    return {
      margin: { t: 10, r: 20, b: 40, l: 180 },
      xaxis: {
        title: { text: 'Relative Importance Score', font: { size: 11, color: CHART_THEME.mutedColor } },
        gridcolor: CHART_THEME.gridColor,
      },
      yaxis: {
        automargin: true,
        tickfont: { size: 11, color: CHART_THEME.textColor },
      },
    };
  }, []);

  const modelCardSummary = useMemo(() => {
    if (!modelCardContent) return null;
    const lines = modelCardContent.split('\n');
    const filteredLines: string[] = [];
    let headingCount = 0;

    for (const line of lines) {
      if (line.startsWith('# ') || line.startsWith('## ')) {
        headingCount++;
        if (headingCount > 4) break;
      }
      filteredLines.push(line);
    }
    return filteredLines.join('\n');
  }, [modelCardContent]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-brand-border">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Insights & Interpretability</h1>
          <p className="text-sm text-brand-muted mt-0.5">
            Feature importance decomposition, meteorology drivers, and model risk documentation.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-brand-text">Section 1: What Drives the Forecast</h2>
            <p className="text-xs text-brand-muted">
              Top 20 features ranked by split and gain contributions for tree-based quantile models.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-brand-muted font-mono">Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-brand-surface text-brand-text border border-brand-border rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-brand-accent/50 focus:border-brand-accent cursor-pointer"
            >
              {availableModels.map((mId) => (
                <option key={mId} value={mId}>
                  {(MODEL_LABELS as Record<string, string>)[mId] || mId}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            label="Top Predictive Feature"
            value={features[0]?.feature || '—'}
            subtitle={features[0]?.group ? `Group: ${features[0].group}` : 'Model ranking'}
          />
          <StatTile
            label="Top Group Driver"
            value={groupBreakdown[0]?.label.split(' ')[0] || '—'}
            unit={groupBreakdown[0] ? `${groupBreakdown[0].sharePct.toFixed(0)}%` : undefined}
            subtitle="Share of top-20 total importance"
          />
          <StatTile
            label="Autoregressive Share"
            value={
              (
                groupBreakdown.find((g) => g.group === 'autoregressive')?.sharePct || 0
              ).toFixed(1)
            }
            unit="%"
            subtitle="Recent and weekly load momentum"
          />
          <StatTile
            label="Weather / Thermal Share"
            value={(
              (groupBreakdown.find((g) => g.group === 'weather')?.sharePct || 0) +
              (groupBreakdown.find((g) => g.group === 'thermal_inertia')?.sharePct || 0)
            ).toFixed(1)}
            unit="%"
            subtitle="Temperature & cooling degree hours"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ChartCard
              title={`Top 20 Features — ${(MODEL_LABELS as Record<string, string>)[selectedModel] || selectedModel}`}
              subtitle="Horizontal bar chart colored by feature domain group"
              loading={loadingFeatures}
              error={featuresError}
              empty={features.length === 0}
              emptyMessage="No feature importance scores found for this model"
            >
              <div className="h-96 w-full">
                <PlotlyChart data={chartData} layout={chartLayout} />
              </div>
            </ChartCard>
          </div>

          <div className="space-y-4">
            <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm space-y-3">
              <h3 className="text-xs font-semibold text-brand-text uppercase tracking-wider">
                Feature Group Legend & Shares
              </h3>
              <p className="text-[11px] text-brand-muted">
                Contribution percentage across the top 20 features for {selectedModel}:
              </p>
              <div className="space-y-2.5 pt-1">
                {groupBreakdown.map((g) => (
                  <div key={g.group} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center space-x-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full inline-block flex-shrink-0"
                          style={{ backgroundColor: g.color }}
                        />
                        <span className="text-brand-text truncate max-w-[170px]" title={g.label}>
                          {g.label}
                        </span>
                      </div>
                      <span className="text-brand-muted font-bold">{g.sharePct.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-brand-bg rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(g.sharePct, 100)}%`,
                          backgroundColor: g.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm space-y-2 text-xs">
              <span className="font-semibold text-brand-text block">Interpretation Takeaways</span>
              <ul className="list-disc list-inside text-brand-muted space-y-1 leading-relaxed">
                <li>
                  <strong className="text-brand-text">CDH (Cooling Degree Hours)</strong> and heat index capture sustained AC load saturation during heatwaves.
                </li>
                <li>
                  <strong className="text-brand-text">Thermal Inertia (24h/48h roll)</strong> reflects building heat accumulation during consecutive high-temperature days.
                </li>
                <li>
                  <strong className="text-brand-text">Autoregressive lags</strong> anchor the baseline diurnal trajectory before weather swings occur.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t border-brand-border">
        <div>
          <h2 className="text-lg font-bold text-brand-text">Section 2: Why Peaks Are Hard</h2>
          <p className="text-xs text-brand-muted">
            Analytical breakdown of Delhi electricity demand extremes, weather sensitivity, and festival load anomalies.
          </p>
        </div>

        <ChartCard
          title="Analysis & Case Studies (WHY_PEAKS_ARE_HARD.md)"
          subtitle="Rendered Markdown report from research documentation"
          loading={loadingWhyPeaks}
        >
          {whyPeaksContent ? (
            <article className="prose prose-invert max-w-none prose-sm leading-relaxed text-brand-text/90 font-sans">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => {
                    const imgSrc = src?.startsWith('/')
                      ? src
                      : `/insights/${src?.replace(/^(\.\/)?(docs\/figures\/|figures\/)?/, '')}`;
                    return (
                      <div className="my-4 rounded-lg overflow-hidden border border-brand-border bg-brand-bg p-2">
                        <img src={imgSrc} alt={alt || 'Figure'} className="rounded max-h-96 mx-auto object-contain" />
                        {alt && <p className="text-center text-xs text-brand-muted mt-1 font-mono">{alt}</p>}
                      </div>
                    );
                  },
                }}
              >
                {whyPeaksContent}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="p-8 text-center border border-dashed border-brand-border rounded-lg space-y-2">
              <p className="text-sm font-semibold text-brand-text">Report file not yet synchronized</p>
              <p className="text-xs text-brand-muted max-w-md mx-auto">
                <code className="text-brand-accent">docs/WHY_PEAKS_ARE_HARD.md</code> will be automatically synchronized to{' '}
                <code className="text-brand-accent">ui/public/insights/</code> during build or via <code className="text-brand-accent">npm run sync:insights</code>.
              </p>
            </div>
          )}
        </ChartCard>
      </div>

      <div className="space-y-4 pt-4 border-t border-brand-border">
        <div>
          <h2 className="text-lg font-bold text-brand-text">Section 3: Model Card Summary</h2>
          <p className="text-xs text-brand-muted">
            Auditable system documentation, evaluation protocol, operational assumptions, and data proxy boundaries.
          </p>
        </div>

        {meta && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm">
              <span className="text-[11px] text-brand-muted uppercase font-semibold block tracking-wider">
                Full Data Range
              </span>
              <span className="text-sm font-mono font-bold text-brand-text mt-1 block">
                {meta.data_range?.start || '—'} to {meta.data_range?.end || '—'}
              </span>
              <span className="text-[11px] text-brand-muted mt-1 block">Historical Delhi SLDC load & IMD weather</span>
            </div>

            <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm">
              <span className="text-[11px] text-brand-muted uppercase font-semibold block tracking-wider">
                Backtest Protocol Range
              </span>
              <span className="text-sm font-mono font-bold text-brand-accent mt-1 block">
                {meta.backtest_range?.start || '—'} to {meta.backtest_range?.end || '—'}
              </span>
              <span className="text-[11px] text-brand-muted mt-1 block">Strictly frozen out-of-sample evaluation</span>
            </div>

            <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-sm">
              <span className="text-[11px] text-brand-muted uppercase font-semibold block tracking-wider">
                Weather Proxy Note
              </span>
              <p className="text-xs text-brand-text/90 mt-1 line-clamp-2" title={meta.weather_proxy_note}>
                {meta.weather_proxy_note || 'Simulated day-ahead forecast with horizon-scaled noise proxy.'}
              </p>
            </div>
          </div>
        )}

        <ChartCard
          title="Model Card (MODEL_CARD.md)"
          subtitle="Scope, intended use, limitations, and operational risk boundaries"
          loading={loadingModelCard}
        >
          {modelCardSummary ? (
            <article className="prose prose-invert max-w-none prose-sm leading-relaxed text-brand-text/90 font-sans">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => {
                    const imgSrc = src?.startsWith('/')
                      ? src
                      : `/insights/${src?.replace(/^(\.\/)?(docs\/figures\/|figures\/)?/, '')}`;
                    return (
                      <div className="my-4 rounded-lg overflow-hidden border border-brand-border bg-brand-bg p-2">
                        <img src={imgSrc} alt={alt || 'Figure'} className="rounded max-h-96 mx-auto object-contain" />
                        {alt && <p className="text-center text-xs text-brand-muted mt-1 font-mono">{alt}</p>}
                      </div>
                    );
                  },
                }}
              >
                {modelCardSummary}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="p-8 text-center border border-dashed border-brand-border rounded-lg space-y-2">
              <p className="text-sm font-semibold text-brand-text">Model card not yet synchronized</p>
              <p className="text-xs text-brand-muted max-w-md mx-auto">
                <code className="text-brand-accent">docs/MODEL_CARD.md</code> will be automatically synchronized to{' '}
                <code className="text-brand-accent">ui/public/insights/</code> during build or via <code className="text-brand-accent">npm run sync:insights</code>.
              </p>
            </div>
          )}
        </ChartCard>
      </div>
    </div>
  );
};

export default InsightsPage;
