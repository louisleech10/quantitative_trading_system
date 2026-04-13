'use client';

import React, { useMemo, useRef } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';
import type { RegimeReport, RegimeClusterStat } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface RegimeClusterChartProps {
  data: RegimeReport | null;
  loading?: boolean;
}

const REGIME_COLORS: Record<string, string> = {
  high_vol_trending: '#ef4444',
  mid_vol_trending: '#f59e0b',
  mid_vol_ranging: '#3b82f6',
  low_vol_ranging: '#10b981',
  high_volatility: '#ef4444',
  medium_volatility: '#f59e0b',
  low_volatility: '#10b981',
  // rule-based fallback
  bull: '#10b981',
  bear: '#ef4444',
  high_vol: '#f59e0b',
  low_vol: '#3b82f6',
};

const REGIME_LABELS: Record<string, string> = {
  high_vol_trending: '高波動趨勢',
  mid_vol_trending: '中波動趨勢',
  mid_vol_ranging: '中波動盤整',
  low_vol_ranging: '低波動盤整',
  high_volatility: '高波動',
  medium_volatility: '中波動',
  low_volatility: '低波動',
  bull: '牛市',
  bear: '熊市',
  high_vol: '高波動',
  low_vol: '低波動',
};

function getColor(regime: string): string {
  return REGIME_COLORS[regime] ?? '#6b7280';
}

function getLabel(regime: string): string {
  return REGIME_LABELS[regime] ?? regime;
}

export default function RegimeClusterChart({ data, loading }: RegimeClusterChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const isKmeans = data?.regime_method === 'kmeans';
  const clusterStats = data?.cluster_stats ?? [];

  const distributionData = useMemo(() => {
    if (!clusterStats || clusterStats.length === 0) return [];
    return clusterStats.map((stat: RegimeClusterStat) => ({
      regime: getLabel(stat.regime),
      rawRegime: stat.regime,
      pct: stat.pct,
      count: stat.count,
    }));
  }, [clusterStats]);

  const featureData = useMemo(() => {
    if (!clusterStats || clusterStats.length === 0) return [];
    return clusterStats.map((stat: RegimeClusterStat) => ({
      regime: getLabel(stat.regime),
      rawRegime: stat.regime,
      volatility: stat.volatility_mean ?? 0,
      trend: stat.trend_strength_mean ?? 0,
      volume: stat.volume_ratio_mean ?? 0,
    }));
  }, [clusterStats]);

  if (loading) return <LoadingState />;
  if (!data) return <EmptyState message="沒有體制分析資料" />;

  if (!isKmeans || clusterStats.length === 0) {
    return (
      <div className="text-sm text-slate-400 p-4 rounded-lg bg-slate-800/30">
        <p className="font-medium mb-1">Regime 方法：規則式（Rule-based）</p>
        <p>當前使用 EMA + Volatility Percentile 規則分組。</p>
        <p className="mt-1 text-xs">
          切換至 K-Means 聚類：修改 <code className="text-cyan-400">ic_config.yaml</code> 中{' '}
          <code className="text-cyan-400">regime_method: &quot;kmeans&quot;</code>
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-sm font-medium text-slate-300">
            K-Means Regime 聚類分布
          </h4>
          <p className="text-xs text-slate-500">
            {clusterStats.length} 個體制 · 無監督聚類
          </p>
        </div>
        <ChartExportButton targetRef={chartRef} filename="regime_cluster" />
      </div>

      <div ref={chartRef} className="space-y-4">
        {/* Distribution bar chart */}
        <div>
          <p className="text-xs text-slate-400 mb-1">樣本分布 (%)</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={distributionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis
                type="category"
                dataKey="regime"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                width={100}
              />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontSize: 12,
                }}
                formatter={(value: number, _name: string, entry: { payload: { count: number } }) => [
                  `${value.toFixed(1)}% (${entry.payload.count} 筆)`,
                  '占比',
                ]}
              />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
                {distributionData.map((entry, i) => (
                  <Cell key={i} fill={getColor(entry.rawRegime)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Feature comparison grouped bar chart */}
        <div>
          <p className="text-xs text-slate-400 mb-1">聚類特徵均值</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={featureData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="regime" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontSize: 12,
                }}
                formatter={(value: number) => value.toFixed(4)}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="volatility" name="波動率" fill="#ef4444" radius={[2, 2, 0, 0]} />
              <Bar dataKey="trend" name="趨勢強度" fill="#3b82f6" radius={[2, 2, 0, 0]} />
              <Bar dataKey="volume" name="量能比" fill="#10b981" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
