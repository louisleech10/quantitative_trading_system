'use client';

import React, { useMemo, useRef } from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import type { RegimeReport } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface RegimeRadarChartProps {
  data: RegimeReport | null;
  loading?: boolean;
}

export default function RegimeRadarChart({ data, loading }: RegimeRadarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.phase_metrics.map(item => ({
      phase: item.phase,
      auc: item.auc ?? 0
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有體制分析資料" />;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="regime_radar" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={chartData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="phase" />
            <PolarRadiusAxis domain={[0, 1]} />
            <Tooltip formatter={(value: unknown) => Number(value).toFixed(3)} />
            <Radar name="AUC" dataKey="auc" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.3} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
