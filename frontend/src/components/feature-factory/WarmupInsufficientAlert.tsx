'use client';

import { AlertCircle } from 'lucide-react';
import type { BatchWarmupInsufficientItem, WarmupInsufficient } from '@/lib/types';
import { formatWarmupInsufficientMessage } from '@/lib/warmupInsufficient';

interface WarmupInsufficientAlertProps {
  warmup?: WarmupInsufficient | null;
  /** 批次：多標的警示 */
  items?: BatchWarmupInsufficientItem[];
  className?: string;
}

export default function WarmupInsufficientAlert({
  warmup,
  items,
  className = '',
}: WarmupInsufficientAlertProps) {
  const batchItems = items ?? [];
  const showSingle = Boolean(warmup);
  const showBatch = batchItems.length > 0;

  if (!showSingle && !showBatch) {
    return null;
  }

  return (
    <div
      data-testid="warmup-insufficient-alert"
      className={`glass-panel rounded-xl p-4 border border-amber-400/30 space-y-2 ${className}`.trim()}
    >
      <div className="flex items-center gap-2 font-medium text-amber-300">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>Warmup 歷史不足</span>
      </div>
      {showSingle && warmup && (
        <p className="text-sm text-amber-100/80" data-testid="warmup-insufficient-message">
          {formatWarmupInsufficientMessage(warmup)}
        </p>
      )}
      {showBatch && (
        <ul className="space-y-1 text-sm text-amber-100/80">
          {batchItems.map((item) => (
            <li
              key={`${item.symbol}:${item.timeframe}`}
              data-testid={`warmup-insufficient-item-${item.symbol}`}
            >
              <span className="text-amber-200/90 font-medium">{item.symbol}</span>
              {' · '}
              {formatWarmupInsufficientMessage(item.warmup_insufficient)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
