'use client';

import { ICDecayData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface ICDecayChartProps {
  data?: ICDecayData | null;
  featureName?: string | null;
  timeframe?: string;
}

const parseTimeframeHours = (timeframe?: string): number | null => {
  if (!timeframe) {
    return null;
  }

  const match = String(timeframe).trim().match(/^(\d+)(m|h|d|w)$/i);
  if (!match) {
    return null;
  }

  const amount = Number(match[1]);
  const unit = match[2].toLowerCase();
  if (!Number.isFinite(amount) || amount <= 0) {
    return null;
  }

  if (unit === 'm') {
    return amount / 60;
  }
  if (unit === 'h') {
    return amount;
  }
  if (unit === 'd') {
    return amount * 24;
  }
  if (unit === 'w') {
    return amount * 24 * 7;
  }

  return null;
};

export default function ICDecayChart({ data, featureName, timeframe }: ICDecayChartProps) {
  const chartData = data
    ? data.horizons.map((horizon, index) => ({
        horizon,
        ic: data.ic_values[index] ?? 0,
      }))
    : [];

  const halfLifeRaw = data?.half_life;
  const halfLife =
    typeof halfLifeRaw === 'number' && Number.isFinite(halfLifeRaw) && halfLifeRaw >= 0
      ? halfLifeRaw
      : null;
  const halfLifeInvalid =
    typeof halfLifeRaw === 'number' && Number.isFinite(halfLifeRaw) && halfLifeRaw < 0;

  const fitR2Raw = data?.fit_r2;
  const fitR2 = typeof fitR2Raw === 'number' && Number.isFinite(fitR2Raw) ? fitR2Raw : null;
  const hasFitField = data ? Object.prototype.hasOwnProperty.call(data, 'fit_r2') : false;

  const timeframeHours = parseTimeframeHours(timeframe);
  const halfLifeHours =
    halfLife !== null && timeframeHours !== null ? halfLife * timeframeHours : null;

  const showFitFailed = data?.decay_type === 'fit_failed';
  const showLowFitWarning = fitR2 !== null && fitR2 < 0.5;
  const showMissingFitWarning = hasFitField && fitR2 === null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">IC Decay</CardTitle>
        <CardDescription>
          {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[240px] text-slate-400">
            暫無衰減數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
              <XAxis dataKey="horizon" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  background: '#1a233a',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}
              />
              {halfLife !== null && (
                <ReferenceLine
                  x={halfLife}
                  stroke="#facc15"
                  strokeDasharray="4 4"
                  label={{
                    value: `Half-Life = ${halfLife.toFixed(2)} bars`,
                    fill: '#fef08a',
                    position: 'insideTopRight',
                    fontSize: 11,
                  }}
                />
              )}
              <Line type="monotone" dataKey="ic" stroke="#22d3ee" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
        {data && (
          <div className="mt-4 space-y-3">
            {(showFitFailed || showLowFitWarning || showMissingFitWarning || halfLifeInvalid) && (
              <div className="flex flex-wrap gap-2 text-xs">
                {showFitFailed && (
                  <span className="rounded-full border border-red-400/50 bg-red-500/10 px-2 py-1 text-red-300">
                    擬合失敗
                  </span>
                )}
                {showLowFitWarning && (
                  <span className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-1 text-amber-300">
                    擬合品質不佳（R² &lt; 0.5）
                  </span>
                )}
                {showMissingFitWarning && (
                  <span className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-1 text-amber-300">
                    無擬合資料
                  </span>
                )}
                {halfLifeInvalid && (
                  <span className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-1 text-amber-300">
                    Half-Life 值無效（負數）
                  </span>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-xs text-slate-300">
              <div>
                Half-Life = {halfLife !== null ? halfLife.toFixed(2) : '--'} bars
                {halfLifeHours !== null ? ` (≈ ${halfLifeHours.toFixed(1)} 小時)` : ''}
              </div>
              <div>Fit R²: {fitR2 !== null ? fitR2.toFixed(2) : '--'}</div>
              <div>Peak Horizon: {data.peak_horizon ?? '--'}</div>
              <div>Decay Rate: {data.decay_rate?.toFixed(3) ?? '--'}</div>
              <div>Decay Type: {data.decay_type ?? '--'}</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
