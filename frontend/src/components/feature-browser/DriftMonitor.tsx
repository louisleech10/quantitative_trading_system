'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DriftMonitorEntry } from '@/lib/types';

interface DriftMonitorProps {
  featuresPath: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DriftMonitor({ featuresPath }: DriftMonitorProps) {
  const [items, setItems] = useState<DriftMonitorEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath.trim()) {
      return;
    }

    const run = async () => {
      setError(null);
      try {
        const query = new URLSearchParams({ features_path: featuresPath, max_features: '120' });
        const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/drift-monitor?${query.toString()}`);
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        const payload = await response.json();
        setItems((payload?.items || []) as DriftMonitorEntry[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取漂移監控資料失敗');
        setItems([]);
      }
    };

    void run();
  }, [featuresPath]);

  const timelineData = useMemo(() => {
    return items.slice(0, 40).map((item, idx) => ({
      index: idx + 1,
      feature_name: item.feature_name,
      psi: item.psi,
    }));
  }, [items]);

  if (!featuresPath.trim()) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">請先輸入 features_path 並載入資料。</div>;
  }

  if (error) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-rose-300">{error}</div>;
  }

  if (items.length === 0) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">沒有漂移監控資料。</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C41 PSITimelineChart</h3>
        <div className="mt-3 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="index" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="psi" stroke="#38bdf8" strokeWidth={2} dot={false} />
              <ReferenceLine y={0.1} stroke="#f59e0b" strokeDasharray="4 4" />
              <ReferenceLine y={0.2} stroke="#f43f5e" strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C42 DistributionComparisonChart</h3>
        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">PSI</th>
                <th className="px-2 py-1 text-right">KS Stat</th>
                <th className="px-2 py-1 text-right">KS p-value</th>
                <th className="px-2 py-1 text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 120).map((item) => (
                <tr key={item.feature_name}>
                  <td className="px-2 py-1 text-slate-100">{item.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.psi.toFixed(4)}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.ks_stat.toFixed(4)}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.ks_pvalue.toExponential(2)}</td>
                  <td className="px-2 py-1 text-right">
                    <span
                      className={
                        item.status === 'stable'
                          ? 'text-emerald-300'
                          : item.status === 'warning'
                            ? 'text-amber-300'
                            : 'text-rose-300'
                      }
                    >
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
