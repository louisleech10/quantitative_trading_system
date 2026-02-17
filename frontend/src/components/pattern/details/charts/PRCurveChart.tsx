'use client';

import React, { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { PRCurveData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface PRCurveChartProps {
  data: PRCurveData | null;
  loading?: boolean;
}

export default function PRCurveChart({ data, loading }: PRCurveChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.recall.map((recall, idx) => ({
      recall,
      precision: data.precision[idx]
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有 PR 曲線資料" />;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="pr_curve" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="recall" domain={[0, 1]} tickFormatter={(v) => v.toFixed(2)} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => v.toFixed(2)} />
            <Tooltip formatter={(value: unknown) => Number(value).toFixed(3)} />
            {data.baseline !== undefined && data.baseline !== null && (
              <ReferenceLine y={data.baseline} stroke="#64748b" strokeDasharray="4 4" />
            )}
            <Line type="monotone" dataKey="precision" stroke="#818cf8" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-xs text-slate-400 mt-2">
        PR AUC: {data.pr_auc !== undefined && data.pr_auc !== null ? data.pr_auc.toFixed(4) : 'N/A'}
      </div>
    </div>
  );
}
