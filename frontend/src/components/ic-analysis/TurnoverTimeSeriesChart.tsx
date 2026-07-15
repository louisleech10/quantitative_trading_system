'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TurnoverFeatureData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface TurnoverTimeSeriesChartProps {
  data?: TurnoverFeatureData | null;
  featureName?: string | null;
}

const MAX_POINTS = 1500;

interface TurnoverChartPoint {
  index: number;
  timestamp: number | string;
  quantile_turnover: number;
  rank_change_rate: number;
}

function downsample(points: TurnoverChartPoint[], maxPoints: number): TurnoverChartPoint[] {
  if (points.length <= maxPoints) {
    return points;
  }

  const stride = Math.ceil((points.length - 1) / (maxPoints - 1));
  const sampled: TurnoverChartPoint[] = [];
  for (let index = 0; index < points.length; index += stride) {
    sampled.push(points[index]);
  }

  const last = points[points.length - 1];
  if (sampled[sampled.length - 1]?.index !== last.index) {
    sampled.push(last);
  }

  return sampled;
}

export default function TurnoverTimeSeriesChart({ data, featureName }: TurnoverTimeSeriesChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const chartData = useMemo(() => {
    const series = data?.time_series;
    if (!series) {
      return [];
    }

    const quantileTurnovers = Array.isArray(series.quantile_turnovers) ? series.quantile_turnovers : [];
    const rankChangeRates = Array.isArray(series.rank_change_rates) ? series.rank_change_rates : [];
    const timestamps = Array.isArray(series.timestamps) ? series.timestamps : [];

    const size = Math.min(quantileTurnovers.length, rankChangeRates.length, timestamps.length);
    if (size === 0) {
      return [];
    }

    const rows: TurnoverChartPoint[] = [];
    for (let index = 0; index < size; index += 1) {
      // S2/RULING-5: skip JSON null warmup（Number(null)===0 會誤畫）
      const rawTurnover = quantileTurnovers[index];
      const rawRankChange = rankChangeRates[index];
      if (rawTurnover == null || rawRankChange == null) {
        continue;
      }
      const turnover = Number(rawTurnover);
      const rankChange = Number(rawRankChange);
      if (!Number.isFinite(turnover) || !Number.isFinite(rankChange)) {
        continue;
      }

      rows.push({
        index,
        timestamp: timestamps[index],
        quantile_turnover: turnover,
        rank_change_rate: rankChange,
      });
    }

    return downsample(rows, MAX_POINTS);
  }, [data]);

  const yMax = useMemo(() => {
    if (chartData.length === 0) {
      return 1;
    }
    const peak = chartData.reduce((acc, point) => {
      const localMax = Math.max(point.quantile_turnover, point.rank_change_rate);
      return Math.max(acc, localMax);
    }, 0);

    if (!Number.isFinite(peak) || peak <= 1) {
      return 1;
    }
    return Math.ceil(peak * 10) / 10;
  }, [chartData]);

  const autocorrelation =
    typeof data?.autocorrelation === 'number' && Number.isFinite(data.autocorrelation)
      ? data.autocorrelation
      : null;

  const handleExportPNG = async () => {
    if (!containerRef.current) {
      return;
    }

    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `turnover_time_series_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Turnover 時序</CardTitle>
          <CardDescription>
            {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {autocorrelation !== null && (
            <span className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-2 py-1 text-xs text-cyan-200">
              自相關: {autocorrelation.toFixed(3)}
            </span>
          )}
          <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
        </div>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-slate-400">暫無 Turnover 時序資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="index" className="text-xs" />
              <YAxis className="text-xs" domain={[0, yMax]} />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
                formatter={(value: number, name: string) => [
                  Number(value).toFixed(4),
                  name === 'quantile_turnover' ? 'Quantile Turnover' : 'Rank Change Rate',
                ]}
                labelFormatter={(index: number) => {
                  const row = chartData[index];
                  if (!row) {
                    return `Bar ${index}`;
                  }
                  return `Bar ${row.index} / T=${row.timestamp}`;
                }}
              />
              <Line
                type="monotone"
                dataKey="quantile_turnover"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={false}
                name="quantile_turnover"
              />
              <Line
                type="monotone"
                dataKey="rank_change_rate"
                stroke="#fb923c"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                name="rank_change_rate"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
