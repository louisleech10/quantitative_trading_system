'use client';

import { QuantileReturnData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface QuantileReturnChartProps {
  data?: QuantileReturnData | null;
  featureName?: string | null;
}

export default function QuantileReturnChart({ data, featureName }: QuantileReturnChartProps) {
  const chartData = data
    ? Object.entries(data.quantile_mean_returns || {}).map(([quantile, value]) => ({
        quantile,
        value,
      }))
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">分位數收益</CardTitle>
        <CardDescription>
          {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無分位數收益數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="quantile" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="value" fill="#60a5fa" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
        {data && (
          <div className="mt-4 text-xs text-slate-300">
            Long-Short Spread: <span className="text-emerald-300">{data.long_short_spread?.toFixed(4) ?? '--'}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
