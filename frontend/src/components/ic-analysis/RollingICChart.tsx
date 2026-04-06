'use client';

import { useEffect, useMemo, useState } from 'react';
import { RollingICSeries } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Area, AreaChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface RollingICChartProps {
  series?: RollingICSeries | null;
  featureName?: string | null;
}

const BAND_WINDOW = 20;

export default function RollingICChart({ series, featureName }: RollingICChartProps) {
  const windowKeys = useMemo(() => Object.keys(series || {}), [series]);
  const [selectedWindow, setSelectedWindow] = useState<string>('');

  useEffect(() => {
    if (windowKeys.length > 0) {
      setSelectedWindow((prev) => (windowKeys.includes(prev) ? prev : windowKeys[0]));
    } else {
      setSelectedWindow('');
    }
  }, [windowKeys]);

  const chartData = useMemo(() => {
    if (!series || !selectedWindow) {
      return [];
    }
    const values = series[selectedWindow] || [];
    return values.map((value, index) => {
      const start = Math.max(0, index - BAND_WINDOW + 1);
      const slice = values.slice(start, index + 1).filter((item) => Number.isFinite(item));
      if (slice.length < 3) {
        return {
          index,
          value,
          rollMean: null,
          rollLower: null,
          rollBandHeight: null,
        };
      }

      const mean = slice.reduce((acc, current) => acc + current, 0) / slice.length;
      const variance = slice.reduce((acc, current) => acc + (current - mean) ** 2, 0) / slice.length;
      const std = Math.sqrt(variance);

      return {
        index,
        value,
        rollMean: mean,
        rollLower: mean - std,
        rollBandHeight: std * 2,
      };
    });
  }, [series, selectedWindow]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Rolling IC</CardTitle>
            <CardDescription>{featureName ? `特徵：${featureName}` : '尚未選擇特徵'}</CardDescription>
          </div>
          {windowKeys.length > 0 && (
            <Select value={selectedWindow} onValueChange={setSelectedWindow}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="選擇窗口" />
              </SelectTrigger>
              <SelectContent>
                {windowKeys.map((key) => (
                  <SelectItem key={key} value={key}>
                    {key}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無 Rolling IC 數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="index" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Area type="monotone" dataKey="rollLower" stroke="none" fillOpacity={0} />
              <Area type="monotone" dataKey="rollBandHeight" stroke="none" fill="#22d3ee33" name="Rolling Band" />
              <Line type="monotone" dataKey="rollMean" stroke="#22d3ee" strokeDasharray="4 3" strokeWidth={1.4} dot={false} name="Rolling Mean" />
              <Line type="monotone" dataKey="value" stroke="#fbbf24" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
