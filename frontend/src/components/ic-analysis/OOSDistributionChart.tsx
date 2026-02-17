'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Bar, ComposedChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RollingOOSData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface OOSDistributionChartProps {
  data?: RollingOOSData;
}

export default function OOSDistributionChart({ data }: OOSDistributionChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    const features = data?.features || {};
    return Object.entries(features)
      .filter(([, value]) => !value.skipped && value.oos_stability)
      .slice(0, 15)
      .map(([feature, value]) => ({
        feature,
        mean_oos_ic: value.oos_stability?.mean_oos_ic ?? 0,
        std_oos_ic: value.oos_stability?.std_oos_ic ?? 0,
      }));
  }, [data?.features]);

  const handleExportPNG = async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `oos_distribution_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C18 OOS Distribution</CardTitle>
          <CardDescription>OOS IC 分佈（Box Plot 簡化視圖）</CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 OOS 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData}>
              <XAxis dataKey="feature" hide />
              <YAxis />
              <Tooltip />
              <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
              <Bar dataKey="mean_oos_ic" fill="#22c55e99" />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
