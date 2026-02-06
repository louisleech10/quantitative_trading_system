'use client';

import React, { useMemo, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts';
import type { RollingAUCData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

interface RollingAUCChartProps {
  data: RollingAUCData | null;
  loading?: boolean;
}

export default function RollingAUCChart({ data, loading }: RollingAUCChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.timestamps.map((ts, idx) => ({
      ts,
      auc: data.auc_values[idx]
    }));
  }, [data]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有滾動 AUC 資料" />;

  const formatTs = (ts: number) => {
    const date = new Date(ts > 10 ** 12 ? ts : ts * 1000);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  const isMs = data.timestamps[0] > 10 ** 12;
  const normalizeZoneTs = (iso: string) => {
    const ms = new Date(iso).getTime();
    return isMs ? ms : Math.floor(ms / 1000);
  };

  return (
    <div>
      <div className="flex justify-end mb-2">
        <ChartExportButton targetRef={chartRef} filename="rolling_auc" />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="ts" tickFormatter={formatTs} />
            <YAxis domain={[0, 1]} />
            <Tooltip formatter={(value: any) => value === null ? 'N/A' : Number(value).toFixed(3)} labelFormatter={(label) => formatTs(Number(label))} />
            {data.warning_zones?.map((zone, idx) => (
              <ReferenceArea
                key={`zone-${idx}`}
                x1={normalizeZoneTs(zone.start)}
                x2={normalizeZoneTs(zone.end)}
                fill="rgba(251,113,133,0.15)"
                fillOpacity={0.4}
              />
            ))}
            <Line type="monotone" dataKey="auc" stroke="#60a5fa" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
