'use client';

import React, { useMemo, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { SingleCaseContribution } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import ChartExportButton from '../shared/ChartExportButton';

interface SHAPWaterfallChartProps {
  contributions: SingleCaseContribution[] | null;
}

export default function SHAPWaterfallChart({ contributions }: SHAPWaterfallChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!contributions) return [];
    return [...contributions]
      .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
      .slice(0, 12)
      .map(item => ({
        feature: item.feature,
        shap_value: item.shap_value
      }));
  }, [contributions]);

  if (!contributions || chartData.length === 0) {
    return <EmptyState message="沒有 SHAP 單案例資料" />;
  }

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="shap_waterfall" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 10, right: 20, left: 120, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis type="number" />
            <YAxis dataKey="feature" type="category" width={110} />
            <Tooltip formatter={(value: any) => Number(value).toFixed(4)} />
            <Bar dataKey="shap_value">
              {chartData.map((entry) => (
                <Cell key={entry.feature} fill={entry.shap_value >= 0 ? '#34d399' : '#fb7185'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
