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

  const entries = Object.entries(preview.breakdown).sort((a, b) => b[1] - a[1]);
  const maxValue = Math.max(...entries.map((item) => item[1]), 1);

  return (
    <div className="space-y-3">
      <div className="text-sm text-slate-200">分類分佈</div>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{key}</span>
              <span>{value}</span>
            </div>
            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-400/50 to-amber-400/40"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
