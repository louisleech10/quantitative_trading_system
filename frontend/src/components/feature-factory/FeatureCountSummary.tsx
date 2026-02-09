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
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="text-xs text-slate-400">預計特徵數</div>
        <div className="text-2xl font-semibold text-slate-100">
          {preview.total_features.toLocaleString('en-US')}
        </div>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="text-xs text-slate-400">估算耗時</div>
        <div className="text-2xl font-semibold text-slate-100">
          {preview.estimated_time_seconds.toFixed(1)}s
        </div>
      </div>
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="text-xs text-slate-400">記憶體需求</div>
        <div className="text-2xl font-semibold text-slate-100">
          {preview.memory_mb.toFixed(0)}MB
        </div>
      </div>
    </div>
  );
}
