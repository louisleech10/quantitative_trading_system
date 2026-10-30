'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { FactorCentralityData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FactorCentralityChartProps {
  data?: FactorCentralityData;
}

export default function FactorCentralityChart({ data }: FactorCentralityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  // ICPERF ⑲：門檻＝後端實際值（τ × 跨特徵平均）；後端不判擁擠時為 null ⇒ 不畫參考線。擁擠與否以後端逐特徵旗標為準
  const threshold = data?.pca_summary?.crowded_threshold ?? null;

  const chartData = useMemo(() => {
    const features = data?.features || {};
    return Object.entries(features).map(([name, value]) => ({
      name,
      centrality: value.centrality ?? 0,
      over: value.crowded ? value.centrality ?? 0 : 0,
    }));
  }, [data?.features]);

  const handleExportPNG = async () => {
    if (!containerRef.current) return;
    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `factor_centrality_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base">C14 Factor Centrality</CardTitle>
          <CardDescription>擁擠度與閾值警示</CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無 Centrality 資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData}>
              <XAxis dataKey="name" hide />
              <YAxis />
              <Tooltip />
              {threshold !== null && <ReferenceLine y={threshold} stroke="#f59e0b" strokeDasharray="4 4" />}
              <Area dataKey="over" fill="#ef444433" stroke="none" />
              <Line dataKey="centrality" stroke="#a78bfa" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
