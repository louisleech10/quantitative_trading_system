'use client';

import React, { useMemo, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { FeatureImportanceTypesResponse } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface FeatureImportanceComparisonProps {
  data: FeatureImportanceTypesResponse | null;
  loading?: boolean;
}

export default function FeatureImportanceComparison({ data, loading }: FeatureImportanceComparisonProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    const gain = data.types.gain || [];
    const cover = data.types.cover || [];
    const weight = data.types.weight || [];

    const topFeatures = gain.slice(0, 10).map(item => item.feature);
    return topFeatures.map(feature => ({
      feature,
      gain: gain.find(i => i.feature === feature)?.importance || 0,
      cover: cover.find(i => i.feature === feature)?.importance || 0,
      weight: weight.find(i => i.feature === feature)?.importance || 0
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有特徵重要性資料" />;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="importance_comparison" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="feature" hide />
            <YAxis />
            <Tooltip formatter={(value: any) => Number(value).toFixed(4)} />
            <Legend />
            <Bar dataKey="gain" fill="#60a5fa" name="Gain" />
            <Bar dataKey="cover" fill="#34d399" name="Cover" />
            <Bar dataKey="weight" fill="#fbbf24" name="Weight" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
