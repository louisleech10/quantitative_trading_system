'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

import type { ICDashboardResult, RollingIC } from '@/lib/types';

interface ICDashboardProps {
  featuresPath: string;
  selectedFeature: string | null;
  onSelectFeature: (feature: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ICDashboard({ featuresPath, selectedFeature, onSelectFeature }: ICDashboardProps) {
  const [dashboard, setDashboard] = useState<ICDashboardResult | null>(null);
  const [rolling, setRolling] = useState<RollingIC | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath.trim()) {
      return;
    }

    const run = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const query = new URLSearchParams({ features_path: featuresPath, top_k: '40' });
        const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/ic-dashboard?${query.toString()}`);
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        const payload: ICDashboardResult = await response.json();
        setDashboard(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取 IC Dashboard 失敗');
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [featuresPath]);

  useEffect(() => {
    const feature = selectedFeature || dashboard?.entries[0]?.feature_name;
    if (!feature || !featuresPath.trim()) {
      return;
    }

    const run = async () => {
      try {
        const query = new URLSearchParams({ features_path: featuresPath, window: '63' });
        const response = await fetch(
          `${API_BASE_URL}/api/v1/feature-browser/rolling-ic/${encodeURIComponent(feature)}?${query.toString()}`,
        );
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        const payload: RollingIC = await response.json();
        setRolling(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取 Rolling IC 失敗');
        setRolling(null);
      }
    };

    onSelectFeature(feature);
    void run();
  }, [dashboard, featuresPath, selectedFeature, onSelectFeature]);

  const rollingData = useMemo(() => {
    if (!rolling) {
      return [];
    }
    return rolling.points.map((point, index) => ({
      index,
      timestamp: point.timestamp,
      ic: point.ic,
      ir: point.ir,
    }));
  }, [rolling]);

  if (!featuresPath.trim()) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">請先輸入 features_path 並載入資料。</div>;
  }

  if (isLoading) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">載入 IC Dashboard 中...</div>;
  }

  if (error) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-rose-300">{error}</div>;
  }

  if (!dashboard || !dashboard.available) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">{dashboard?.message || 'IC 資料不可用'}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C33 ICDashboardTable</h3>
        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">IC Mean</th>
                <th className="px-2 py-1 text-right">IC Std</th>
                <th className="px-2 py-1 text-right">IR</th>
                <th className="px-2 py-1 text-right">t-stat</th>
                <th className="px-2 py-1 text-right">Sig</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.entries.map((entry) => (
                <tr
                  key={entry.feature_name}
                  className={selectedFeature === entry.feature_name ? 'bg-white/10 cursor-pointer' : 'cursor-pointer'}
                  onClick={() => onSelectFeature(entry.feature_name)}
                >
                  <td className="px-2 py-1 text-slate-100">{entry.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{entry.ic_mean.toFixed(4)}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{entry.ic_std.toFixed(4)}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{entry.ir.toFixed(4)}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{entry.t_stat.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right text-sky-300">{entry.significance || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C34 RollingICChart</h3>
        {rollingData.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">沒有可用的 rolling IC 資料。</div>
        ) : (
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rollingData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="index" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip />
                <Line dataKey="ic" stroke="#60a5fa" dot={false} strokeWidth={2} />
                <Line dataKey="ir" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C35 ICDecayChart</h3>
        <p className="mt-2 text-sm text-slate-400">
          以 rolling IC 近端資料近似觀察遞減趨勢（lag=1..N），用於快速辨識訊號衰減速度。
        </p>
      </div>
    </div>
  );
}
