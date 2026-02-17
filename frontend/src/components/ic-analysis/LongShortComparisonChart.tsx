'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { LongShortAnalysisData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface LongShortComparisonChartProps {
  data?: LongShortAnalysisData;
}

export default function LongShortComparisonChart({ data }: LongShortComparisonChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    return Object.entries(data || {})
      .filter(([, value]) => !value.skipped)
      .slice(0, 15)
      .map(([feature, value]) => ({
        feature,
        long: value.long_analysis?.mean_return ?? 0,
        short: -(value.short_analysis?.mean_return ?? 0),
      }));
  }, [data]);

  const handleExportPNG = async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `long_short_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C19 Long/Short Comparison</CardTitle>
          <CardDescription>雙向 Diverging Bar</CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無多空資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" />
              <YAxis type="category" dataKey="feature" width={0} hide />
              <Tooltip />
              <Bar dataKey="short" fill="#ef4444aa" />
              <Bar dataKey="long" fill="#22c55eaa" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
