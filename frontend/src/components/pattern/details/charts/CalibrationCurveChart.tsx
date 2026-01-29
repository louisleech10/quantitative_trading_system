'use client';

import React, { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { CalibrationCurveData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface CalibrationCurveChartProps {
  data: CalibrationCurveData | null;
  loading?: boolean;
}

export default function CalibrationCurveChart({ data, loading }: CalibrationCurveChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.bin_midpoints.map((midpoint, idx) => ({
      midpoint,
      actual: data.actual_positive_rate[idx],
      predicted: data.predicted_mean[idx]
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有校準曲線資料" />;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="calibration_curve" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="midpoint" tickFormatter={(v) => v.toFixed(2)} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => v.toFixed(2)} />
            <Tooltip formatter={(value: any) => Number(value).toFixed(3)} />
            <Line type="monotone" dataKey="actual" stroke="#10b981" name="實際正例率" />
            <Line type="monotone" dataKey="predicted" stroke="#3b82f6" name="預測平均" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
