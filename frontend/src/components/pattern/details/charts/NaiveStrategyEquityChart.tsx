'use client';

import React, { useMemo, useRef, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { EquityCurveData } from '@/lib/patternTypes';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';
import ChartExportButton from '../shared/ChartExportButton';

/**
 * 權益曲線之計算模式（PA-CUMSUM，2026-08-18 使用者定：單利／複利兩條都算、都標清楚、可切換）。
 * - simple：單利（固定本金／固定金額下注）＝每期報酬相加（cumsum）
 * - compound：複利（全額滾入／固定比例）＝資產連乘（cumprod−1）
 * 兩者是不同部位假設下的正確算法；預設 compound（等於帳戶實際淨值變化）。
 */
export type EquityMode = 'simple' | 'compound';

const MODE_LABEL: Record<EquityMode, string> = {
  simple: '單利（固定本金）',
  compound: '複利（全額滾入）',
};

interface NaiveStrategyEquityChartProps {
  data: EquityCurveData | null;
  loading?: boolean;
  defaultMode?: EquityMode;
}

export default function NaiveStrategyEquityChart({ data, loading, defaultMode = 'compound' }: NaiveStrategyEquityChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<EquityMode>(defaultMode);

  const chartData = useMemo(() => {
    if (!data) return [];
    const strategy = mode === 'simple' ? data.strategy_returns_simple : data.strategy_returns_compound;
    const benchmark = mode === 'simple' ? data.benchmark_returns_simple : data.benchmark_returns_compound;
    return data.timestamps.map((ts, idx) => ({
      ts,
      strategy: strategy[idx],
      benchmark: benchmark[idx],
    }));
  }, [data, mode]);

  if (loading) return <LoadingState />;
  if (!data || chartData.length === 0) return <EmptyState message="沒有權益曲線資料" />;

  const formatTs = (ts: number) => {
    const date = new Date(ts > 10 ** 12 ? ts : ts * 1000);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };
  const pct = (v: number) => `${(v * 100).toFixed(2)}%`;
  const finalStrategy = mode === 'simple' ? data.final_return_pct.strategy_simple : data.final_return_pct.strategy_compound;
  const finalBenchmark = mode === 'simple' ? data.final_return_pct.benchmark_simple : data.final_return_pct.benchmark_compound;

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-1 text-xs" role="tablist" aria-label="權益曲線計算模式">
          {(['compound', 'simple'] as EquityMode[]).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={`px-2 py-1 rounded border ${
                mode === m
                  ? 'bg-emerald-400/20 border-emerald-400/60 text-emerald-200'
                  : 'bg-white/5 border-white/10 text-slate-400 hover:text-slate-200'
              }`}
              title={m === 'simple' ? '每期報酬相加（cumsum）；等於每期都拿同一筆本金下注' : '資產連乘（cumprod−1）；等於帳戶實際淨值變化'}
            >
              {MODE_LABEL[m]}
            </button>
          ))}
        </div>
        <ChartExportButton targetRef={chartRef} filename={`strategy_equity_${mode}`} />
      </div>
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis dataKey="ts" tickFormatter={formatTs} />
            <YAxis tickFormatter={(v: number) => pct(v)} width={64} />
            <Tooltip formatter={(value: unknown) => pct(Number(value))} labelFormatter={(label) => formatTs(Number(label))} />
            <Line type="monotone" dataKey="strategy" stroke="#34d399" dot={false} name={`策略（${MODE_LABEL[mode]}）`} />
            <Line type="monotone" dataKey="benchmark" stroke="#60a5fa" dot={false} name={`基準（${MODE_LABEL[mode]}）`} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-xs text-slate-400 mt-2">
        <span className="text-slate-300">{MODE_LABEL[mode]}</span> — 策略累積報酬 {finalStrategy.toFixed(2)}% ｜ 基準 {finalBenchmark.toFixed(2)}%
        <span className="ml-3 text-slate-500">
          （另一種：{MODE_LABEL[mode === 'simple' ? 'compound' : 'simple']} 策略{' '}
          {(mode === 'simple' ? data.final_return_pct.strategy_compound : data.final_return_pct.strategy_simple).toFixed(2)}% ｜ 基準{' '}
          {(mode === 'simple' ? data.final_return_pct.benchmark_compound : data.final_return_pct.benchmark_simple).toFixed(2)}%）
        </span>
      </div>
    </div>
  );
}
