'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { FactorReturnData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface FactorReturnChartProps {
  data?: FactorReturnData;
}

export default function FactorReturnChart({ data }: FactorReturnChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    if (!data) return [];
    const firstFeature = Object.values(data)[0];
    const summary = firstFeature?.quantile_returns_summary || {};
    return Object.entries(summary).map(([name, value]) => ({ name, value: Number(value) }));
  }, [data]);

  const handleExportPNG = async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `factor_return_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C13 Factor Return</CardTitle>
          <CardDescription>Q1~Qn 平均收益</CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 Factor Return 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
