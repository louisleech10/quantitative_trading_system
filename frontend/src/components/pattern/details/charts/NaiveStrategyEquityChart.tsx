'use client';

import React, { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { EquityCurveData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface NaiveStrategyEquityChartProps {
  data: EquityCurveData | null;
  loading?: boolean;
}

export default function NaiveStrategyEquityChart({ data, loading }: NaiveStrategyEquityChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.timestamps.map((ts, idx) => ({
      ts,
      strategy: data.strategy_returns[idx],
      benchmark: data.benchmark_returns[idx]
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有權益曲線資料" />;

  const formatTs = (ts: number) => {
    const date = new Date(ts > 10 ** 12 ? ts : ts * 1000);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="strategy_equity" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="ts" tickFormatter={formatTs} />
            <YAxis />
            <Tooltip formatter={(value: any) => Number(value).toFixed(4)} labelFormatter={(label) => formatTs(Number(label))} />
            <Line type="monotone" dataKey="strategy" stroke="#10b981" dot={false} name="策略" />
            <Line type="monotone" dataKey="benchmark" stroke="#3b82f6" dot={false} name="基準" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-xs text-gray-500 mt-2">
        策略報酬: {data.final_return_pct.strategy.toFixed(2)}% ｜ 基準: {data.final_return_pct.benchmark.toFixed(2)}%
      </div>
    </div>
  );
}
