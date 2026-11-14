import React, { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChartCard } from '../../components/shared/ChartCard';
import { getFeatureImportance, getMeta } from '../../api/client';
import { FeatureImportanceItem, MetaResponse } from '../../api/types';
import { DEFAULT_MODEL } from '../../constants/models';

export const InsightsPage: React.FC = () => {
  const [model] = useState<string>(DEFAULT_MODEL);
  const [features, setFeatures] = useState<FeatureImportanceItem[]>([]);
  const [loadingFeatures, setLoadingFeatures] = useState<boolean>(true);
  const [featuresError, setFeaturesError] = useState<string | null>(null);

  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [whyPeaksContent, setWhyPeaksContent] = useState<string | null>(null);
  const [modelCardContent, setModelCardContent] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    getMeta()
      .then((m) => {
        if (mounted) setMeta(m);
      })
      .catch(() => {});

    getFeatureImportance(model, 1)
      .then((res) => {
        if (mounted) {
          setFeatures(res?.features || []);
          setLoadingFeatures(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setFeaturesError(err.message || 'Failed to load feature importance');
          setLoadingFeatures(false);
        }
      });

    fetch('/insights/WHY_PEAKS_ARE_HARD.md')
      .then((res) => (res.ok ? res.text() : null))
      .then((txt) => {
        if (mounted && txt) setWhyPeaksContent(txt);
      })
      .catch(() => {});

    fetch('/insights/MODEL_CARD.md')
      .then((res) => (res.ok ? res.text() : null))
      .then((txt) => {
        if (mounted && txt) setModelCardContent(txt);
      })
      .catch(() => {});

    return () => {
      mounted = false;
    };
  }, [model]);

  const groupedBars = useMemo(() => {
    const categories: Array<{
      groupName: string;
      items: Array<{ name: string; pct: number }>;
    }> = [
      {
        groupName: 'Weather',
        items: [
          { name: 'Temperature', pct: 85 },
          { name: 'Humidity', pct: 50 },
        ],
      },
      {
        groupName: 'Calendar',
        items: [
          { name: 'Hour of day', pct: 78 },
          { name: 'Holiday flag', pct: 42 },
        ],
      },
      {
        groupName: 'Lagged load',
        items: [
          { name: 'Same hour last week', pct: 68 },
          { name: 'Previous day', pct: 58 },
        ],
      },
    ];

    if (features && features.length > 0) {
      const weatherFeats = features.filter((f) => f.group === 'weather' || f.group === 'thermal_inertia');
      const calFeats = features.filter((f) => f.group === 'calendar' || f.group === 'festival' || f.group === 'event');
      const arFeats = features.filter((f) => f.group === 'autoregressive' || f.group === 'trend');

      const maxImp = Math.max(...features.map((f) => f.importance), 0.01);

      if (weatherFeats.length > 0) {
        categories[0].items = weatherFeats.slice(0, 2).map((f) => ({
          name: f.feature.replace(/^wx_/, '').replace(/_/g, ' '),
          pct: Math.round((f.importance / maxImp) * 85),
        }));
      }
      if (calFeats.length > 0) {
        categories[1].items = calFeats.slice(0, 2).map((f) => ({
          name: f.feature.replace(/^cal_/, '').replace(/_/g, ' '),
          pct: Math.round((f.importance / maxImp) * 80),
        }));
      }
      if (arFeats.length > 0) {
        categories[2].items = arFeats.slice(0, 2).map((f) => ({
          name: f.feature.replace(/^ar_/, '').replace(/_/g, ' '),
          pct: Math.round((f.importance / maxImp) * 75),
        }));
      }
    }

    return categories;
  }, [features]);

  const trainingDates = meta?.backtest_range
    ? `${meta.backtest_range.start} to ${meta.backtest_range.end}`
    : '2023-01-01 to 2026-10-31';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-6">
          Insights
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <ChartCard
          title="Feature importance by type"
          loading={loadingFeatures}
          error={featuresError}
          empty={false}
        >
          <div className="space-y-6 py-2">
            {groupedBars.map((group) => (
              <div key={group.groupName} className="space-y-2">
                <div className="text-xs text-slate-500 font-normal">
                  {group.groupName}
                </div>
                {group.items.map((item) => (
                  <div key={item.name} className="flex items-center space-x-4">
                    <span className="w-36 text-sm text-slate-800 font-normal truncate">
                      {item.name}
                    </span>
                    <div className="flex-1 bg-transparent h-4 relative">
                      <div
                        className="bg-[#1d4ed8] h-3.5 rounded-sm transition-all duration-500"
                        style={{ width: `${Math.max(item.pct, 5)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </ChartCard>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm min-h-[380px]">
          <h3 className="text-base font-bold text-slate-900 mb-3">Why peaks are hard</h3>
          {whyPeaksContent ? (
            <div className="prose prose-sm max-w-none text-slate-600">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {whyPeaksContent}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-slate-600 leading-relaxed">
              Peaks are rare, short and sensitive to weather and events. A small timing shift moves the peak into a neighbouring hour, so a forecast with low average error can still miss the event that matters.
            </p>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <h3 className="text-base font-bold text-slate-900 mb-3">Model card</h3>
        {modelCardContent ? (
          <div className="prose prose-sm max-w-none text-slate-600">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {modelCardContent}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm text-slate-600 leading-relaxed">
            Model: quantile gradient boosting. Targets: P05, P10, P50, P90, P95 of hourly load. Training window: [{trainingDates}]. Known limits: weather is a proxy, and festival dates are tagged by hand.
          </p>
        )}
      </div>
    </div>
  );
};
