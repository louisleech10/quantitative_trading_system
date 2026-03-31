'use client';

import { FeaturePreview } from '@/lib/types';

interface FeatureDistributionProps {
  preview: FeaturePreview | null;
}

export default function FeatureDistribution({ preview }: FeatureDistributionProps) {
  if (!preview || !preview.breakdown) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
        尚無分類分佈資料。
      </div>
    );
  }

  const entries = Object.entries(preview.breakdown)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1]);
  const maxValue = Math.max(...entries.map((item) => item[1]), 1);

  if (entries.length === 0) {
    return (
      <div className="text-xs text-slate-500">所有分類特徵數均為 0。</div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-xs font-medium text-slate-400">分類分佈</div>
      <div className="space-y-0.5">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-24 shrink-0 text-[11px] text-slate-400 truncate">{key}</span>
            <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-400/50 to-amber-400/40"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
            <span className="w-7 shrink-0 text-right text-[11px] text-slate-300 tabular-nums">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
