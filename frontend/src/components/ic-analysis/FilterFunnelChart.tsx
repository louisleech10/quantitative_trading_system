'use client';

import { useMemo } from 'react';
import { FilterLogData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface FilterFunnelChartProps {
  filterLog?: FilterLogData | null;
}

export default function FilterFunnelChart({ filterLog }: FilterFunnelChartProps) {
  const chartData = useMemo(() => {
    if (!filterLog) {
      return [];
    }

    return Object.entries(filterLog).map(([stage, values]) => ({
      stage,
      output: values.output,
      input: values.input,
      removed: Math.max(values.input - values.output, 0),
    }));
  }, [filterLog]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">篩選漏斗</CardTitle>
        <CardDescription>各階段特徵數變化</CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無漏斗數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="stage" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="output" fill="#34d399" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
