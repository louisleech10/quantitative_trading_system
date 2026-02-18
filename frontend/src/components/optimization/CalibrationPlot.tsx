'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { CalibrationResult } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface CalibrationPlotProps {
  data: CalibrationResult;
  onExportPNG?: () => void;
}

export default function CalibrationPlot({ data, onExportPNG }: CalibrationPlotProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    const curve = data?.reliability_curve;
    const bins = curve?.bin_midpoints ?? [];
    const original = curve?.original_freq ?? [];
    const calibrated = curve?.calibrated_freq ?? [];

    return bins.map((bin, index) => ({
      bin,
      diagonal: bin,
      original: original[index] ?? null,
      calibrated: calibrated[index] ?? null,
    }));
  }, [data]);

  const handleExportPNG = async () => {
    if (onExportPNG) {
      onExportPNG();
      return;
    }

    if (!containerRef.current || chartData.length === 0) {
      return;
    }

    try {
      const canvas = await html2canvas(containerRef.current);
      const link = document.createElement('a');
      link.download = `calibration_plot_${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('CalibrationPlot PNG 匯出失敗', error);
    }
  };

  return (
    <div ref={containerRef}>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">C23 Calibration Plot</CardTitle>
            <CardDescription>對角基準線 + 校準前後 reliability curve</CardDescription>
          </div>
          <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">
            PNG
          </button>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="h-[260px] flex items-center justify-center text-slate-400">暫無校準曲線資料</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <XAxis dataKey="bin" type="number" domain={[0, 1]} tickFormatter={(value) => Number(value).toFixed(1)} />
                <YAxis domain={[0, 1]} tickFormatter={(value) => Number(value).toFixed(1)} />
                <Tooltip />
                <Line type="linear" dataKey="diagonal" stroke="#94a3b8" dot={false} strokeDasharray="4 4" name="Diagonal" />
                <Line type="monotone" dataKey="original" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} connectNulls={false} name="Original" />
                <Line type="monotone" dataKey="calibrated" stroke="#22c55e" strokeWidth={2} dot={{ r: 2 }} connectNulls={false} name="Calibrated" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
