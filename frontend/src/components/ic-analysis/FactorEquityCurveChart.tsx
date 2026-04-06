'use client';

import { useMemo, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Area, ComposedChart, Line, CartesianGrid, Tooltip, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { EquityCurvePoint, QuantileReturnData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FactorEquityCurveChartProps {
  data?: QuantileReturnData | null;
  featureName?: string | null;
}

interface EquityCurveChartPoint extends EquityCurvePoint {
  short_value: number | null;
}

const MAX_POINTS = 1500;

function downsample<T extends { bar_index: number }>(points: T[], maxPoints: number): T[] {
  if (points.length <= maxPoints) {
    return points;
  }

  const stride = Math.ceil((points.length - 1) / (maxPoints - 1));
  const sampled: T[] = [];
  for (let index = 0; index < points.length; index += stride) {
    sampled.push(points[index]);
  }

  const last = points[points.length - 1];
  if (sampled[sampled.length - 1]?.bar_index !== last.bar_index) {
    sampled.push(last);
  }

  return sampled;
}

function parseQuantileIndex(key: string): number {
  const match = key.match(/Q(\d+)/i);
  if (!match) {
    return Number.NaN;
  }
  return Number(match[1]);
}

export default function FactorEquityCurveChart({ data, featureName }: FactorEquityCurveChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const transformed = useMemo(() => {
    const cumulativeReturns = data?.cumulative_returns;
    if (!cumulativeReturns || typeof cumulativeReturns !== 'object') {
      return {
        points: [] as EquityCurveChartPoint[],
        rawPoints: [] as EquityCurveChartPoint[],
        lowKey: null as string | null,
        highKey: null as string | null,
      };
    }

    const quantileKeys = Object.keys(cumulativeReturns)
      .filter((key) => Number.isFinite(parseQuantileIndex(key)))
      .sort((a, b) => parseQuantileIndex(a) - parseQuantileIndex(b));

    if (quantileKeys.length === 0) {
      return {
        points: [] as EquityCurveChartPoint[],
        rawPoints: [] as EquityCurveChartPoint[],
        lowKey: null as string | null,
        highKey: null as string | null,
      };
    }

    const lowKey = quantileKeys[0];
    const highKey = quantileKeys[quantileKeys.length - 1];
    const lowSeries = Array.isArray(cumulativeReturns[lowKey]) ? cumulativeReturns[lowKey] : [];
    const highSeries = Array.isArray(cumulativeReturns[highKey]) ? cumulativeReturns[highKey] : [];

    const length = Math.min(lowSeries.length, highSeries.length);
    if (length === 0) {
      return {
        points: [] as EquityCurveChartPoint[],
        rawPoints: [] as EquityCurveChartPoint[],
        lowKey,
        highKey,
      };
    }

    const points: EquityCurveChartPoint[] = [];
    let runningMax = Number.NEGATIVE_INFINITY;

    for (let barIndex = 0; barIndex < length; barIndex += 1) {
      const lowRaw = Number(lowSeries[barIndex]);
      const highRaw = Number(highSeries[barIndex]);
      const low = Number.isFinite(lowRaw) ? lowRaw : null;
      const high = Number.isFinite(highRaw) ? highRaw : null;
      const spread = low !== null && high !== null ? high - low : null;

      let drawdown: number | undefined;
      if (spread !== null) {
        runningMax = Math.max(runningMax, spread);
        drawdown = spread - runningMax;
      }

      points.push({
        bar_index: barIndex,
        Q1: low ?? Number.NaN,
        Q5: high ?? Number.NaN,
        short_value: low !== null ? -low : null,
        ls_spread: spread ?? Number.NaN,
        drawdown,
      });
    }

    return {
      points: downsample(points, MAX_POINTS),
      rawPoints: points,
      lowKey,
      highKey,
    };
  }, [data]);

  const metrics = useMemo(() => {
    if (transformed.rawPoints.length === 0) {
      return {
        totalReturn: null as number | null,
        maxDrawdown: null as number | null,
        sharpe: null as number | null,
      };
    }

    const spreadSeries = transformed.rawPoints
      .map((point) => point.ls_spread)
      .filter((value) => Number.isFinite(value));

    const totalReturn = spreadSeries.length > 0 ? spreadSeries[spreadSeries.length - 1] : null;

    const drawdownSeries = transformed.rawPoints
      .map((point) => point.drawdown)
      .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    const maxDrawdown = drawdownSeries.length > 0 ? Math.min(...drawdownSeries) : null;

    const spreadReturns: number[] = [];
    for (let index = 1; index < spreadSeries.length; index += 1) {
      spreadReturns.push(spreadSeries[index] - spreadSeries[index - 1]);
    }

    let sharpe: number | null = null;
    if (spreadReturns.length > 1) {
      const mean = spreadReturns.reduce((sum, value) => sum + value, 0) / spreadReturns.length;
      const variance = spreadReturns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (spreadReturns.length - 1);
      const std = Math.sqrt(variance);
      if (Number.isFinite(std) && std > 0) {
        sharpe = (mean / std) * Math.sqrt(252);
      }
    }

    return {
      totalReturn,
      maxDrawdown,
      sharpe,
    };
  }, [transformed.rawPoints]);

  const handleExportPNG = async () => {
    if (!containerRef.current) {
      return;
    }

    const canvas = await html2canvas(containerRef.current);
    const link = document.createElement('a');
    link.download = `factor_equity_curve_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card ref={containerRef}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Equity Curve（累積淨值）</CardTitle>
          <CardDescription>
            {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
          </CardDescription>
        </div>
        <button type="button" onClick={handleExportPNG} className="text-xs text-cyan-300">PNG</button>
      </CardHeader>
      <CardContent className="space-y-4">
        {transformed.points.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-slate-400">暫無累積淨值資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={transformed.points} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="bar_index" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
                formatter={(value: number, name: string) => {
                  if (!Number.isFinite(value)) {
                    return ['--', name];
                  }
                  return [value.toFixed(4), name];
                }}
                labelFormatter={(barIndex: number) => `Bar ${barIndex}`}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="none"
                fill="#ef444433"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="Q5"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                name={`Long (${transformed.highKey || 'Q-high'})`}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="short_value"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                name={`Short (${transformed.lowKey || 'Q-low'} × -1)`}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="ls_spread"
                stroke="#7dd3fc"
                strokeWidth={2}
                dot={false}
                name="L-S Spread"
                connectNulls={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-300">
          <div>
            Total Return: {typeof metrics.totalReturn === 'number' ? metrics.totalReturn.toFixed(4) : '--'}
          </div>
          <div>
            Max Drawdown: {typeof metrics.maxDrawdown === 'number' ? metrics.maxDrawdown.toFixed(4) : '--'}
          </div>
          <div>
            Sharpe Ratio: {typeof metrics.sharpe === 'number' ? metrics.sharpe.toFixed(3) : '--'}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
