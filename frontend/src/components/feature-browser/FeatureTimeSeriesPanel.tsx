'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FeatureBrowserTimeSeriesResponse } from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const COLORS = ['#38bdf8', '#34d399', '#f59e0b', '#f472b6', '#a78bfa'];


interface FeatureTimeSeriesPanelProps {
  featuresPath: string;
  selectedFeatures: string[];
}


export default function FeatureTimeSeriesPanel({ featuresPath, selectedFeatures }: FeatureTimeSeriesPanelProps) {
  const [data, setData] = useState<FeatureBrowserTimeSeriesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = selectedFeatures.slice(0, 5);

  useEffect(() => {
    if (!featuresPath || selected.length === 0) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    const query = new URLSearchParams({
      features_path: featuresPath,
      features: selected.join(','),
      sample_rate: '1',
    });

    fetch(`${API_BASE_URL}/api/v1/features/time-series?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        return response.json() as Promise<FeatureBrowserTimeSeriesResponse>;
      })
      .then((payload) => setData(payload))
      .catch((fetchError: unknown) => {
        setError(fetchError instanceof Error ? fetchError.message : '載入時間序列失敗');
      })
      .finally(() => setLoading(false));
  }, [featuresPath, selected]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.points.map((point) => ({ timestamp: point.timestamp ?? '', ...point.values }));
  }, [data]);

  const acfData = useMemo(() => {
    if (!data || selected.length === 0) return [];
    const first = selected[0];
    return (data.acf[first] || []).map((item) => ({ lag: item.lag, value: item.value }));
  }, [data, selected]);

  const fftData = useMemo(() => {
    if (!data || selected.length === 0) return [];
    const first = selected[0];
    return data.periodicity[first] || [];
  }, [data, selected]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">時間序列分析（最多 5 條）</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && <div className="text-slate-400 text-sm">載入中...</div>}
        {!loading && error && <div className="text-rose-300 text-sm">{error}</div>}
        {!loading && !error && !data && <div className="text-slate-400 text-sm">請先選擇特徵</div>}

        {!loading && !error && data && (
          <>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" tick={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip />
                  {selected.map((feature, idx) => (
                    <Line key={feature} type="monotone" dataKey={feature} stroke={COLORS[idx % COLORS.length]} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={acfData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="lag" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#38bdf8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded border border-white/10 p-3">
                <div className="text-sm text-slate-300 mb-2">FFT 週期性 Top 5</div>
                <div className="space-y-2 text-xs text-slate-300">
                  {fftData.map((item) => (
                    <div key={`${item.frequency}-${item.amplitude}`} className="flex justify-between">
                      <span>f={item.frequency.toFixed(4)}</span>
                      <span>amp={item.amplitude.toFixed(6)}</span>
                    </div>
                  ))}
                  {fftData.length === 0 && <div className="text-slate-400">無可用週期訊號</div>}
                </div>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
