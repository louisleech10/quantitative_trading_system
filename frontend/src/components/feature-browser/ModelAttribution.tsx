'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { ImportanceComparison, SHAPSummary } from '@/lib/types';

interface ModelAttributionProps {
  featuresPath: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ModelAttribution({ featuresPath }: ModelAttributionProps) {
  const [shap, setShap] = useState<SHAPSummary | null>(null);
  const [comparison, setComparison] = useState<ImportanceComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath.trim()) {
      return;
    }

    const run = async () => {
      setError(null);
      try {
        const shapQuery = new URLSearchParams({ features_path: featuresPath, top_k: '30' });
        const shapResp = await fetch(`${API_BASE_URL}/api/v1/feature-browser/shap-summary?${shapQuery.toString()}`);
        if (!shapResp.ok) {
          const payload = await shapResp.json().catch(() => ({}));
          throw new Error(payload?.detail || shapResp.statusText);
        }
        const shapPayload: SHAPSummary = await shapResp.json();
        setShap(shapPayload);

        const cmpQuery = new URLSearchParams({ features_path: featuresPath, top_k: '30' });
        const cmpResp = await fetch(`${API_BASE_URL}/api/v1/feature-browser/importance-comparison?${cmpQuery.toString()}`);
        if (!cmpResp.ok) {
          const payload = await cmpResp.json().catch(() => ({}));
          throw new Error(payload?.detail || cmpResp.statusText);
        }
        const cmpPayload: ImportanceComparison = await cmpResp.json();
        setComparison(cmpPayload);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取模型歸因資料失敗');
        setShap(null);
        setComparison(null);
      }
    };

    void run();
  }, [featuresPath]);

  const dependenceData = useMemo(() => {
    if (!shap || !shap.items.length) {
      return [];
    }
    return shap.items.slice(0, 80).map((item, idx) => ({
      x: idx,
      y: item.mean_shap,
      name: item.feature_name,
      magnitude: item.mean_abs_shap,
    }));
  }, [shap]);

  if (!featuresPath.trim()) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">請先輸入 features_path 並載入資料。</div>;
  }

  if (error) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-rose-300">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C43 SHAPBeeswarmPlot</h3>
        {!shap || !shap.available || shap.items.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">{shap?.message || '沒有 SHAP 摘要資料。'}</div>
        ) : (
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shap.items.slice(0, 20)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="category" dataKey="feature_name" tick={{ fill: '#94a3b8', fontSize: 10 }} width={140} />
                <Tooltip />
                <Bar dataKey="mean_abs_shap" fill="#60a5fa" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C44 SHAPDependencePlot</h3>
        {dependenceData.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">沒有 SHAP 依賴資料。</div>
        ) : (
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" dataKey="x" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="number" dataKey="y" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                <Scatter data={dependenceData} fill="#22d3ee" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C45 ImportanceComparisonChart</h3>
        {!comparison || comparison.items.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">沒有跨引擎重要性資料。</div>
        ) : (
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison.items.slice(0, 15)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="feature_name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="lightgbm_importance" fill="#60a5fa" />
                <Bar dataKey="xgboost_importance" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
