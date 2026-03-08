'use client';

import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { FeaturePreview } from '@/lib/types';

const MAX_FEATURES_WARNING = 10000;
const MAX_FEATURES_HARD_LIMIT = 50000;
const MIN_FEATURES_WARNING = 5;

interface FeaturePreviewBarProps {
  preview: FeaturePreview | null;
  isLoading?: boolean;
}

export default function FeaturePreviewBar({ preview, isLoading = false }: FeaturePreviewBarProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs text-slate-500 animate-pulse">
        正在估算特徵數量...
      </div>
    );
  }

  if (!preview) return null;

  const { total_features, estimated_time_seconds, memory_mb } = preview;

  const isZero = total_features === 0;
  const isTooFew = total_features > 0 && total_features < MIN_FEATURES_WARNING;
  const isWarning = total_features > MAX_FEATURES_WARNING;
  const isHardLimit = total_features > MAX_FEATURES_HARD_LIMIT;

  let borderColor = 'border-white/10';
  let Icon = CheckCircle;
  let iconColor = 'text-emerald-400';
  let message = '';

  if (isZero) {
    borderColor = 'border-rose-400/30';
    Icon = XCircle;
    iconColor = 'text-rose-400';
    message = '無啟用的特徵，請至少啟用一個指標';
  } else if (isTooFew) {
    borderColor = 'border-amber-400/30';
    Icon = AlertTriangle;
    iconColor = 'text-amber-400';
    message = `僅 ${total_features} 個特徵，可能不足以進行有意義的分析`;
  } else if (isHardLimit) {
    borderColor = 'border-rose-400/30';
    Icon = XCircle;
    iconColor = 'text-rose-400';
    message = `特徵數 ${total_features.toLocaleString('en-US')} 超過上限 ${MAX_FEATURES_HARD_LIMIT.toLocaleString('en-US')}`;
  } else if (isWarning) {
    borderColor = 'border-amber-400/30';
    Icon = AlertTriangle;
    iconColor = 'text-amber-400';
    message = `特徵數超過 ${MAX_FEATURES_WARNING.toLocaleString('en-US')} 建議上限，可能影響效能`;
  }

  return (
    <div className={`rounded-xl border ${borderColor} bg-white/5 px-4 py-2 space-y-1`}>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
          <span className="text-slate-300">預估特徵數:</span>
          <span className="font-semibold text-slate-100">{total_features.toLocaleString('en-US')}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400">耗時:</span>
          <span className="text-slate-200">~{estimated_time_seconds.toFixed(1)}s</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400">記憶體:</span>
          <span className="text-slate-200">~{memory_mb.toFixed(0)}MB</span>
        </div>
      </div>
      {message && (
        <div className={`text-[11px] ${isHardLimit || isZero ? 'text-rose-300' : 'text-amber-300'}`}>
          ⚠️ {message}
        </div>
      )}
    </div>
  );
}
