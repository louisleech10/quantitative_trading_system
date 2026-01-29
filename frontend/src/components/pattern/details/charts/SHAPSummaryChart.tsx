'use client';

import React, { useMemo, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { GlobalSHAPResult } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface SHAPSummaryChartProps {
  data: GlobalSHAPResult | null;
  loading?: boolean;
  onFeatureClick?: (feature: string) => void;
}

export default function SHAPSummaryChart({ data, loading, onFeatureClick }: SHAPSummaryChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.feature_importance_shap.map(item => ({
      feature: item.feature,
      mean_abs_shap: item.mean_abs_shap,
      rank: item.rank
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有 SHAP 資料" />;

  const topData = chartData.slice(0, 15);
  const maxValue = Math.max(...topData.map(item => item.mean_abs_shap), 0);

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="shap_summary" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={topData} layout="vertical" margin={{ top: 10, right: 20, left: 120, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, maxValue || 'auto']} />
            <YAxis dataKey="feature" type="category" width={110} />
            <Tooltip formatter={(value: any) => Number(value).toFixed(4)} />
            <Bar dataKey="mean_abs_shap" onClick={(entry: any) => onFeatureClick?.(entry.feature)}>
              {topData.map((entry) => (
                <Cell key={entry.feature} fill={entry.rank <= 3 ? '#f59e0b' : '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
