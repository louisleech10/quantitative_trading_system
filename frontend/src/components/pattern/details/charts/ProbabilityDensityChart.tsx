'use client';

import React, { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { ProbabilityDensityData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface ProbabilityDensityChartProps {
  data: ProbabilityDensityData | null;
  loading?: boolean;
}

export default function ProbabilityDensityChart({ data, loading }: ProbabilityDensityChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.positive_density.bins.map((bin, idx) => ({
      bin,
      positive: data.positive_density.density[idx] || 0,
      negative: data.negative_density.density[idx] || 0
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有機率分佈資料" />;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="probability_density" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="bin" tickFormatter={(v) => v.toFixed(2)} />
            <YAxis />
            <Tooltip formatter={(value: unknown) => Number(value).toFixed(4)} />
            <Line type="monotone" dataKey="positive" stroke="#34d399" name="正例密度" dot={false} />
            <Line type="monotone" dataKey="negative" stroke="#fb7185" name="反例密度" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-xs text-slate-400 mt-2">重疊分數：{data.overlap_score.toFixed(4)}</div>
    </div>
  );
}
