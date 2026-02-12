'use client';

import { ICDecayData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ICDecayChartProps {
  data?: ICDecayData | null;
  featureName?: string | null;
}

export default function ICDecayChart({ data, featureName }: ICDecayChartProps) {
  const chartData = data
    ? data.horizons.map((horizon, index) => ({
        horizon,
        ic: data.ic_values[index] ?? 0,
      }))
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">IC Decay</CardTitle>
        <CardDescription>
          {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無衰減數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="horizon" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Line type="monotone" dataKey="ic" stroke="#22d3ee" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
        {data && (
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-300">
            <div>Half-Life: {data.half_life?.toFixed(2) ?? '--'}</div>
            <div>Peak Horizon: {data.peak_horizon ?? '--'}</div>
            <div>Decay Rate: {data.decay_rate?.toFixed(3) ?? '--'}</div>
            <div>Decay Type: {data.decay_type ?? '--'}</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
