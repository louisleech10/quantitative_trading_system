'use client';

import React, { useEffect, useState } from 'react';
import { usePatternStore } from '@/store/patternStore';
import { getSHAPSingleCase } from '@/lib/api/patternApi';
import SHAPWaterfallChart from '../charts/SHAPWaterfallChart';
import EmptyState from '../shared/EmptyState';
import LoadingState from '../shared/LoadingState';

interface SingleCaseSHAPPanelProps {
  taskId: string;
  caseId: string | null;
  onClose?: () => void;
}

export default function SingleCaseSHAPPanel({ taskId, caseId }: SingleCaseSHAPPanelProps) {
  const { shapSingleCase, setSHAPSingleCase } = usePatternStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!caseId) return;
      setLoading(true);
      try {
        const response = await getSHAPSingleCase(taskId, caseId);
        setSHAPSingleCase(response.result || null);
      } finally {
        setLoading(false);
      }
    };

    if (!caseId) {
      setSHAPSingleCase(null);
      return;
    }

    fetchData();
  }, [taskId, caseId, setSHAPSingleCase]);

  if (!caseId) return <EmptyState message="請選擇案例" />;
  if (loading) return <LoadingState />;
  if (!shapSingleCase) return <EmptyState message="沒有 SHAP 單案例資料" />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/5 border border-white/10 rounded p-3">
          <div className="text-sm text-slate-400">預測機率</div>
          <div className="text-xl font-semibold text-slate-100">{shapSingleCase.predicted_proba.toFixed(4)}</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded p-3">
          <div className="text-sm text-slate-400">Expected Value</div>
          <div className="text-xl font-semibold text-slate-100">{shapSingleCase.expected_value.toFixed(4)}</div>
        </div>
      </div>

      <SHAPWaterfallChart contributions={shapSingleCase.contributions} />

      <div className="space-y-2">
        {shapSingleCase.contributions.map((item) => (
          <div key={item.feature} className="flex justify-between text-sm">
            <span className="font-mono text-slate-300 break-all">{item.feature}</span>
            <span className={item.shap_value >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
              {item.shap_value.toFixed(4)} ({item.contribution_pct.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
