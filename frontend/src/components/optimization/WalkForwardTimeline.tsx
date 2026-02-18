'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Bar, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { WalkForwardResult } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface WalkForwardTimelineProps {
  data: WalkForwardResult;
  onExportPNG?: () => void;
}

export default function WalkForwardTimeline({ data, onExportPNG }: WalkForwardTimelineProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    const validPeriods = data.period_results.filter((period) => typeof period.test_auc === 'number');
    let rollingTotal = 0;

    return validPeriods.map((period, index) => {
      const auc = period.test_auc as number;
      rollingTotal += auc;
      const movingAvg = rollingTotal / (index + 1);

      let color = '#22c55e';
      if (auc < 0.55) {
        color = '#ef4444';
      } else if (auc < 0.65) {
        color = '#eab308';
      }

      return {
        periodIndex: period.period_index,
        auc,
        movingAvg,
        color,
        trainRange: `${period.train_start_idx}-${period.train_end_idx}`,
        testRange: `${period.test_start_idx}-${period.test_end_idx}`,
        gap: period.is_oos_gap,
      };
    });
  }, [data.period_results]);

  const yDomain = useMemo<[number, number]>(() => {
    if (chartData.length === 0) {
      return [0, 1];
    }
    const aucs = chartData.map((item) => item.auc);
    const minAuc = Math.min(...aucs);
    const maxAuc = Math.max(...aucs);
    const lower = Math.max(0, minAuc - 0.05);
    const upper = Math.min(1, maxAuc + 0.05);
    return [lower, upper];
  }, [chartData]);

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
      link.download = `walk_forward_timeline_${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('WalkForwardTimeline PNG 匯出失敗', error);
    }
  };

  return (
    <div ref={containerRef}>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">C24 Walk-Forward Timeline</CardTitle>
            <CardDescription>Period AUC（Bar）+ 移動平均（Line）</CardDescription>
          </div>
          <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">
            PNG
          </button>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="h-[260px] flex items-center justify-center text-slate-400">暫無可用 period AUC 資料</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={chartData}>
                <XAxis dataKey="periodIndex" />
                <YAxis domain={yDomain} />
                <Tooltip
                  labelFormatter={(label, payload) => {
                    const first = payload?.[0]?.payload as {
                      trainRange?: string;
                      testRange?: string;
                      gap?: number | null;
                    } | undefined;
                    const gapText = typeof first?.gap === 'number' ? first.gap.toFixed(4) : '--';
                    return `Period ${label} | Train ${first?.trainRange ?? '--'} | Test ${first?.testRange ?? '--'} | Gap ${gapText}`;
                  }}
                />
                <Bar dataKey="auc" name="AUC">
                  {chartData.map((entry) => (
                    <Cell key={`cell-${entry.periodIndex}`} fill={entry.color} />
                  ))}
                </Bar>
                <Line type="monotone" dataKey="movingAvg" stroke="#38bdf8" strokeWidth={2} dot={false} name="Moving Avg" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
