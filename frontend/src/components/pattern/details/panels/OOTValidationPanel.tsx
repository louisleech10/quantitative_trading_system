'use client';

import React from 'react';
import type { OOTValidationResult } from '@/lib/patternTypes';
import LoadingState from '../shared/LoadingState';
import EmptyState from '../shared/EmptyState';
import MetricCard from '../shared/MetricCard';

interface OOTValidationPanelProps {
  data: OOTValidationResult | null;
  loading?: boolean;
}

export default function OOTValidationPanel({ data, loading }: OOTValidationPanelProps) {
  if (loading) return <LoadingState />;
  if (!data) return <EmptyState message="沒有 OOT 驗證資料" />;

  const aucColor = data.oot_auc >= 0.65 ? 'text-emerald-400' : data.oot_auc >= 0.55 ? 'text-amber-400' : 'text-rose-400';

  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="mb-4">
        <div className="text-sm text-slate-400">OOT AUC</div>
        <div className={`text-3xl font-semibold ${aucColor}`}>{data.oot_auc.toFixed(4)}</div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard title="OOT Precision" value={data.oot_precision} format="percent" />
        <MetricCard title="OOT Recall" value={data.oot_recall} format="percent" />
        <MetricCard title="OOT F1" value={data.oot_f1} format="percent" />
        <MetricCard title="CV-OOT Gap" value={data.cv_oot_gap} format="percent" status={data.gap_status} />
      </div>
      <div className="mt-4 text-sm text-slate-400">
        期間：{data.oot_period_start} ~ {data.oot_period_end}
      </div>
      <div className="mt-1 text-sm text-slate-400">
        樣本數：{data.oot_samples}｜正例比例：{(data.oot_positive_rate * 100).toFixed(2)}%
      </div>
    </div>
  );
}
