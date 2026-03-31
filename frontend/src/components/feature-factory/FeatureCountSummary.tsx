'use client';

import { FeaturePreview } from '@/lib/types';

interface FeatureCountSummaryProps {
  preview: FeaturePreview | null;
}

export default function FeatureCountSummary({ preview }: FeatureCountSummaryProps) {
  if (!preview) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
        尚未取得預覽結果。
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 flex items-center gap-3">
      <div className="text-xs text-slate-400 shrink-0">預計特徵數</div>
      <div className="text-lg font-semibold text-slate-100 tabular-nums">
        {preview.total_features.toLocaleString('en-US')}
      </div>
    </div>
  );
}
