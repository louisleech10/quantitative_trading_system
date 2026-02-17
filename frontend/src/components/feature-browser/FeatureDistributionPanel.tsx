'use client';

import { useEffect, useMemo, useState } from 'react';
import { Area, Bar, CartesianGrid, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FeatureBrowserDistributionResponse } from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface FeatureDistributionPanelProps {
  featuresPath: string;
  featureName: string | null;
}


export default function FeatureDistributionPanel({ featuresPath, featureName }: FeatureDistributionPanelProps) {
  const [data, setData] = useState<FeatureBrowserDistributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!featuresPath || !featureName) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    const query = new URLSearchParams({ features_path: featuresPath, bins: '50' });
    fetch(`${API_BASE_URL}/api/v1/features/${encodeURIComponent(featureName)}/distribution?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        return response.json() as Promise<FeatureBrowserDistributionResponse>;
      })
      .then((payload) => setData(payload))
      .catch((fetchError: unknown) => {
        setError(fetchError instanceof Error ? fetchError.message : '載入分佈失敗');
      })
      .finally(() => setLoading(false));
  }, [featuresPath, featureName]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.histogram.map((item, idx) => ({
      index: idx,
      range: `${item.left.toFixed(3)}~${item.right.toFixed(3)}`,
      count: item.count,
      density: item.density,
    }));
  }, [data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">分佈分析</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && <div className="text-slate-400 text-sm">載入中...</div>}
        {!loading && error && <div className="text-rose-300 text-sm">{error}</div>}
        {!loading && !error && !data && <div className="text-slate-400 text-sm">請先選擇特徵</div>}

        {!loading && !error && data && (
          <>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="index" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#34d399" />
                  <Area dataKey="density" stroke="#38bdf8" fill="#38bdf833" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <BoxPlot statistics={data.statistics} />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <Stat label="mean" value={data.statistics.mean} />
              <Stat label="std" value={data.statistics.std} />
              <Stat label="skew" value={data.statistics.skew} />
              <Stat label="kurtosis" value={data.statistics.kurtosis} />
              <Stat label="min" value={data.statistics.min} />
              <Stat label="q25" value={data.statistics.q25} />
              <Stat label="median" value={data.statistics.median} />
              <Stat label="q75" value={data.statistics.q75} />
              <Stat label="max" value={data.statistics.max} />
              <Stat label="NaN%" value={data.statistics.nan_pct} suffix="%" />
              <Stat label="Unique" value={data.statistics.unique_count} />
              <Stat label="Zeros" value={data.statistics.zero_count} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function BoxPlot({
  statistics,
}: {
  statistics: FeatureBrowserDistributionResponse['statistics'];
}) {
  const min = statistics.min;
  const q25 = statistics.q25;
  const median = statistics.median;
  const q75 = statistics.q75;
  const max = statistics.max;

  if ([min, q25, median, q75, max].some((value) => value === null)) {
    return (
      <div className="rounded border border-white/10 p-3">
        <div className="text-slate-300 text-sm">箱型圖</div>
        <div className="text-slate-400 text-xs mt-1">統計資料不足，無法繪製</div>
      </div>
    );
  }

  const minValue = min as number;
  const q25Value = q25 as number;
  const medianValue = median as number;
  const q75Value = q75 as number;
  const maxValue = max as number;

  const domainMin = Math.min(minValue, q25Value, medianValue, q75Value, maxValue);
  const domainMax = Math.max(minValue, q25Value, medianValue, q75Value, maxValue);
  const span = Math.max(1e-9, domainMax - domainMin);
  const toX = (value: number) => 24 + ((value - domainMin) / span) * 552;

  return (
    <div className="rounded border border-white/10 p-3">
      <div className="text-slate-300 text-sm mb-2">箱型圖</div>
      <svg viewBox="0 0 600 90" className="w-full h-[90px]">
        <line x1={toX(minValue)} y1="45" x2={toX(maxValue)} y2="45" stroke="#64748b" strokeWidth="2" />
        <line x1={toX(minValue)} y1="32" x2={toX(minValue)} y2="58" stroke="#94a3b8" strokeWidth="2" />
        <line x1={toX(maxValue)} y1="32" x2={toX(maxValue)} y2="58" stroke="#94a3b8" strokeWidth="2" />
        <rect
          x={Math.min(toX(q25Value), toX(q75Value))}
          y="30"
          width={Math.abs(toX(q75Value) - toX(q25Value))}
          height="30"
          fill="#38bdf833"
          stroke="#38bdf8"
          strokeWidth="2"
        />
        <line x1={toX(medianValue)} y1="30" x2={toX(medianValue)} y2="60" stroke="#f59e0b" strokeWidth="2" />
      </svg>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs text-slate-400 mt-2">
        <div>min: {minValue.toFixed(6)}</div>
        <div>q25: {q25Value.toFixed(6)}</div>
        <div>median: {medianValue.toFixed(6)}</div>
        <div>q75: {q75Value.toFixed(6)}</div>
        <div>max: {maxValue.toFixed(6)}</div>
      </div>
    </div>
  );
}


function Stat({ label, value, suffix = '' }: { label: string; value: number | null; suffix?: string }) {
  const display = typeof value === 'number' ? `${value.toFixed(6)}${suffix}` : '--';
  return (
    <div className="rounded border border-white/10 px-3 py-2">
      <div className="text-slate-400 text-xs">{label}</div>
      <div className="text-slate-100 font-mono text-xs">{display}</div>
    </div>
  );
}
