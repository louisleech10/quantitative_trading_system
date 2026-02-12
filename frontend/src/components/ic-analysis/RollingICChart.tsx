'use client';

import { useEffect, useMemo, useState } from 'react';
import { RollingICSeries } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
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
    return values.map((value, index) => ({ index, value }));
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
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
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
              <Line type="monotone" dataKey="value" stroke="#fbbf24" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
