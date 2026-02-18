'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

import type { FeatureQualityScore } from '@/lib/types';

interface QualityScorecardProps {
  featuresPath: string;
  selectedFeature: string | null;
  onSelectFeature: (feature: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface QualityResponse {
  items: FeatureQualityScore[];
  funnel: {
    raw: number;
    after_ic: number;
    after_vif: number;
    final: number;
  };
}

export default function QualityScorecard({ featuresPath, selectedFeature, onSelectFeature }: QualityScorecardProps) {
  const [data, setData] = useState<QualityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath.trim()) {
      return;
    }

    const run = async () => {
      setError(null);
      try {
        const query = new URLSearchParams({ features_path: featuresPath, top_k: '150' });
        const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/quality-scorecard?${query.toString()}`);
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.detail || response.statusText);
        }
        const payload: QualityResponse = await response.json();
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : '讀取品質分數卡失敗');
        setData(null);
      }
    };

    void run();
  }, [featuresPath]);

  const selectedScore = useMemo(() => {
    if (!data || data.items.length === 0) {
      return null;
    }
    return data.items.find((item) => item.feature_name === selectedFeature) || data.items[0];
  }, [data, selectedFeature]);

  if (!featuresPath.trim()) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">請先輸入 features_path 並載入資料。</div>;
  }

  if (error) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-rose-300">{error}</div>;
  }

  if (!data || data.items.length === 0) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">沒有品質分數資料。</div>;
  }

  const radarData = selectedScore
    ? [
        { metric: 'stationarity', value: selectedScore.stationarity_score },
        { metric: 'coverage', value: selectedScore.coverage_score },
        { metric: 'drift', value: selectedScore.drift_score },
        { metric: 'redundancy', value: selectedScore.redundancy_score },
      ]
    : [];

  const gradeColor = (grade: string) => {
    if (grade === 'A') return 'text-emerald-300';
    if (grade === 'B') return 'text-lime-300';
    if (grade === 'C') return 'text-amber-300';
    if (grade === 'D') return 'text-orange-300';
    return 'text-rose-300';
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C36 QualityScorecardTable</h3>
        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">Total</th>
                <th className="px-2 py-1 text-right">Grade</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.feature_name}
                  className={selectedScore?.feature_name === item.feature_name ? 'bg-white/10 cursor-pointer' : 'cursor-pointer'}
                  onClick={() => onSelectFeature(item.feature_name)}
                >
                  <td className="px-2 py-1 text-slate-100">{item.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.total_score.toFixed(3)}</td>
                  <td className={`px-2 py-1 text-right font-semibold ${gradeColor(item.grade)}`}>{item.grade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C37 FeatureFunnelChart</h3>
        <div className="mt-3 h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={[
                { stage: 'raw', value: data.funnel.raw },
                { stage: 'after_ic', value: data.funnel.after_ic },
                { stage: 'after_vif', value: data.funnel.after_vif },
                { stage: 'final', value: data.funnel.final },
              ]}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="stage" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#38bdf8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C38 QualityRadarChart</h3>
        {radarData.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">請先選擇特徵。</div>
        ) : (
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <PolarRadiusAxis domain={[0, 1]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Radar dataKey="value" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.4} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
