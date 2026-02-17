'use client';

import React, { useMemo, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { DriftReport } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface PSIComparisonChartProps {
  data: DriftReport | null;
  loading?: boolean;
  selectedFeature?: string | null;
  onFeatureSelect?: (feature: string) => void;
}

export default function PSIComparisonChart({ data, loading, selectedFeature, onFeatureSelect }: PSIComparisonChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const featureOptions = data?.results?.map(r => r.feature) || [];
  const activeFeature = selectedFeature || featureOptions[0];

  const chartData = useMemo(() => {
    if (!data || !activeFeature) return [];
    const result = data.results.find(r => r.feature === activeFeature);
    if (!result) return [];
    return result.distribution_comparison.bins.map((bin, idx) => ({
      bin,
      train_pct: result.distribution_comparison.train_pct[idx],
      test_pct: result.distribution_comparison.test_pct[idx]
    }));
  }, [data, activeFeature]);

  if (loading) return <LoadingState />;
  if (!data || !activeFeature || chartData.length === 0) return <EmptyState message="沒有 PSI 資料" />;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <select
          value={activeFeature}
          onChange={(e) => onFeatureSelect?.(e.target.value)}
          className="border border-white/10 bg-white/5 rounded px-2 py-1 text-sm text-slate-100"
        >
          {featureOptions.map(feature => (
            <option key={feature} value={feature}>{feature}</option>
          ))}
        </select>
        <ChartExportButton targetRef={chartRef} filename="psi_comparison" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="bin" tickFormatter={(v) => Number(v).toFixed(2)} />
            <YAxis />
            <Tooltip formatter={(value: unknown) => Number(value).toFixed(4)} />
            <Bar dataKey="train_pct" fill="#60a5fa" name="訓練分佈" />
            <Bar dataKey="test_pct" fill="#fbbf24" name="OOT 分佈" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
