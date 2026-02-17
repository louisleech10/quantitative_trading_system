'use client';

import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts';
import { FeatureSummary } from '@/lib/types';
import { exportChartToPNG } from '@/lib/exportUtils';

interface OverviewDashboardProps {
  summary: FeatureSummary | null;
  loading: boolean;
  error: string | null;
  taskId?: string;
}

const PIE_COLORS = ['#34d399', '#60a5fa', '#f59e0b', '#f472b6', '#a78bfa'];

const qualityClass = (score: number) => {
  if (score >= 80) return 'text-emerald-300';
  if (score >= 60) return 'text-amber-300';
  return 'text-rose-300';
};

export default function OverviewDashboard({ summary, loading, error, taskId }: OverviewDashboardProps) {
  const qualityScore = useMemo(() => {
    if (!summary || summary.total_features <= 0) return 0;
    const nanRatio = summary.quality.nan_ratio_mean;
    const stationaryRatio = summary.quality.stationary_ratio;
    const constantRatio = summary.quality.constant_features.length / summary.total_features;
    const denominator = (summary.total_features * (summary.total_features - 1)) / 2;
    const highCorrRatio = denominator > 0 ? summary.quality.high_corr_pairs_count / denominator : 0;

    const score =
      (1 - nanRatio) * 40 +
      stationaryRatio * 30 +
      (1 - constantRatio) * 15 +
      (1 - highCorrRatio) * 15;

    return Math.max(0, Math.min(100, score));
  }, [summary]);

  const categoryData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_category).map(([name, value]) => ({ name, value }));
  }, [summary]);

  const levelData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_level).map(([name, value]) => ({ name, value }));
  }, [summary]);

  const layerData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_layer).map(([name, value]) => ({ name, value }));
  }, [summary]);

  const alerts = useMemo(() => {
    const source = summary?.quality.quality_alerts || [];
    const rank = { error: 0, warning: 1, info: 2 };
    return [...source].sort((a, b) => rank[a.severity] - rank[b.severity]);
  }, [summary]);

  if (loading) {
    return <div className="glass-panel rounded-2xl p-6 text-slate-300">載入 Overview 中...</div>;
  }

  if (error) {
    return <div className="glass-panel rounded-2xl p-6 text-rose-300">{error}</div>;
  }

  if (!summary) {
    return <div className="glass-panel rounded-2xl p-6 text-slate-300">尚無可用摘要資料。</div>;
  }

  return (
    <div id="feature-overview-dashboard" className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => taskId && exportChartToPNG('feature-overview-dashboard', 'feature_overview', taskId)}
          disabled={!taskId}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200 disabled:opacity-50"
        >
          匯出 PNG
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <KpiCard label="Features" value={summary.total_features.toLocaleString()} />
        <KpiCard label="Rows" value={summary.total_rows.toLocaleString()} />
        <KpiCard label="NaN Avg" value={`${(summary.quality.nan_ratio_mean * 100).toFixed(2)}%`} />
        <KpiCard label="Quality" value={qualityScore.toFixed(1)} valueClass={qualityClass(qualityScore)} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass-panel rounded-2xl p-4 h-[320px]">
          <div className="text-sm text-slate-300 mb-2">By Category</div>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryData}>
              <XAxis dataKey="name" hide />
              <YAxis hide />
              <Tooltip />
              <Bar dataKey="value" fill="#60a5fa" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-panel rounded-2xl p-4 h-[320px]">
          <div className="text-sm text-slate-300 mb-2">By Level</div>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={levelData} dataKey="value" nameKey="name" outerRadius={100}>
                {levelData.map((entry, idx) => (
                  <Cell key={`${entry.name}-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass-panel rounded-2xl p-4 h-[280px]">
        <div className="text-sm text-slate-300 mb-2">By Layer</div>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={layerData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#34d399" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="glass-panel rounded-2xl p-4">
        <div className="text-sm text-slate-300 mb-2">Quality Alerts</div>
        {alerts.length === 0 ? (
          <div className="text-xs text-slate-400">目前沒有警示。</div>
        ) : (
          <div className="space-y-2 max-h-40 overflow-auto">
            {alerts.slice(0, 20).map((alert, idx) => (
              <div
                key={`${alert.feature}-${idx}`}
                className={`text-xs rounded-lg px-3 py-2 border ${
                  alert.severity === 'error'
                    ? 'border-rose-400/40 text-rose-200'
                    : alert.severity === 'warning'
                    ? 'border-amber-400/40 text-amber-200'
                    : 'border-blue-400/40 text-blue-200'
                }`}
              >
                {alert.feature}: {alert.message}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="glass-panel rounded-2xl p-4 border border-white/10">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`text-xl font-semibold text-slate-100 ${valueClass || ''}`}>{value}</div>
    </div>
  );
}
