'use client';

import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { FeatureBrowserDistributionResponse, FeatureOverview } from '@/lib/types';

interface FeatureSummaryTableProps {
  overview: FeatureOverview | null;
  featuresPath: string;
  selectedFeature: string | null;
  onSelectFeature: (feature: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function FeatureSummaryTable({
  overview,
  featuresPath,
  selectedFeature,
  onSelectFeature,
}: FeatureSummaryTableProps) {
  const [distribution, setDistribution] = useState<FeatureBrowserDistributionResponse | null>(null);
  const [isLoadingDistribution, setIsLoadingDistribution] = useState(false);
  const [distributionError, setDistributionError] = useState<string | null>(null);

  const selected = selectedFeature || overview?.items[0]?.feature_name || null;

  const nanHeatmapData = useMemo(() => {
    if (!overview) {
      return [];
    }
    return overview.items.slice(0, 30).map((item) => ({
      feature_name: item.feature_name,
      nan_pct: item.nan_pct,
    }));
  }, [overview]);

  const handleLoadDistribution = async (featureName: string) => {
    if (!featuresPath.trim()) {
      setDistributionError('請先輸入 features_path');
      return;
    }

    onSelectFeature(featureName);
    setDistributionError(null);
    setIsLoadingDistribution(true);

    try {
      const query = new URLSearchParams({
        features_path: featuresPath,
        bins: '40',
      });
      const response = await fetch(
        `${API_BASE_URL}/api/v1/feature-browser/distribution/${encodeURIComponent(featureName)}?${query.toString()}`,
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || response.statusText);
      }
      const payload: FeatureBrowserDistributionResponse = await response.json();
      setDistribution(payload);
    } catch (error) {
      setDistributionError(error instanceof Error ? error.message : '讀取分佈失敗');
      setDistribution(null);
    } finally {
      setIsLoadingDistribution(false);
    }
  };

  if (!overview || overview.items.length === 0) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">沒有可顯示的特徵摘要。</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C30 FeatureSummaryTable</h3>
        <p className="mt-1 text-xs text-slate-400">
          特徵數 {overview.total_features} / 數值欄位 {overview.numeric_features} / 平均 NaN% {overview.mean_nan_pct.toFixed(2)}
        </p>

        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">Mean</th>
                <th className="px-2 py-1 text-right">Std</th>
                <th className="px-2 py-1 text-right">Min</th>
                <th className="px-2 py-1 text-right">Max</th>
                <th className="px-2 py-1 text-right">NaN%</th>
                <th className="px-2 py-1 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {overview.items.slice(0, 120).map((item) => (
                <tr key={item.feature_name} className={selected === item.feature_name ? 'bg-white/10' : ''}>
                  <td className="px-2 py-1 text-slate-100">{item.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.mean?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.std?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.min?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.max?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.nan_pct.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">
                    <button
                      onClick={() => handleLoadDistribution(item.feature_name)}
                      className="rounded border border-white/20 px-2 py-1 text-slate-200 hover:bg-white/10"
                    >
                      C31
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C31 FeatureDistributionChart</h3>
        {isLoadingDistribution ? (
          <div className="mt-3 text-sm text-slate-300">載入分佈中...</div>
        ) : distributionError ? (
          <div className="mt-3 text-sm text-rose-300">{distributionError}</div>
        ) : !distribution || distribution.histogram.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">請從上方點選 C31 載入特徵分佈。</div>
        ) : (
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distribution.histogram}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="left" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#60a5fa" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C32 NaNHeatmap</h3>
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6">
          {nanHeatmapData.map((item) => {
            const level = Math.min(100, Math.max(0, item.nan_pct));
            return (
              <div
                key={item.feature_name}
                title={`${item.feature_name}: ${item.nan_pct.toFixed(2)}%`}
                className="rounded border border-white/10 p-2"
                style={{
                  background: `rgba(244, 63, 94, ${0.1 + (level / 100) * 0.7})`,
                }}
              >
                <div className="truncate text-[10px] text-slate-100">{item.feature_name}</div>
                <div className="text-[10px] text-slate-200">{item.nan_pct.toFixed(1)}%</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
