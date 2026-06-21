'use client';

import { useEffect, useMemo, useState } from 'react';
import { Archive } from 'lucide-react';
import type { BatchRetentionItem } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import CollapsibleSection from './CollapsibleSection';

const BATCH_RETENTION_EXPANDED_KEY = 'ff-batch-retention-expanded';

const btnBase =
  'inline-flex items-center justify-center rounded-lg border px-2.5 py-1.5 text-xs transition disabled:opacity-40 disabled:cursor-not-allowed';

function itemKey(item: Pick<BatchRetentionItem, 'symbol' | 'timeframe' | 'config_hash'>): string {
  return `${item.symbol}|${item.timeframe}|${item.config_hash}`;
}

export default function BatchRetentionPanel() {
  const batchTask = useFeatureFactoryStore((state) => state.batchTask);
  const batchConnectionStatus = useFeatureFactoryStore((state) => state.batchConnectionStatus);
  const fetchBatchRetentionPending = useFeatureFactoryStore((state) => state.fetchBatchRetentionPending);
  const applyBatchRetentionDecision = useFeatureFactoryStore((state) => state.applyBatchRetentionDecision);

  const batchId = batchTask?.batch_id ?? batchTask?.task_id ?? null;

  const [decidingKeys, setDecidingKeys] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});

  const visiblePending = useMemo(() => {
    const pending = batchTask?.retention_pending ?? [];
    return pending.filter((item) => item.state === 'pending' || decidingKeys.has(itemKey(item)));
  }, [batchTask?.retention_pending, decidingKeys]);

  useEffect(() => {
    if (!batchId) return;
    void fetchBatchRetentionPending(batchId);
  }, [batchId, fetchBatchRetentionPending]);

  useEffect(() => {
    if (!batchId || batchConnectionStatus !== 'lost') return;
    void fetchBatchRetentionPending(batchId);
  }, [batchConnectionStatus, batchId, fetchBatchRetentionPending]);

  if (visiblePending.length === 0) {
    return null;
  }

  const handleDecision = async (
    item: BatchRetentionItem,
    decision: 'retain' | 'discard',
  ) => {
    if (!batchId) return;
    const key = itemKey(item);
    setDecidingKeys((prev) => new Set(prev).add(key));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });

    const result = await applyBatchRetentionDecision(
      batchId,
      item.symbol,
      item.timeframe,
      item.config_hash,
      decision,
    );

    setDecidingKeys((prev) => {
      const next = new Set(prev);
      next.delete(key);
      return next;
    });

    if (!result.ok) {
      setErrors((prev) => ({
        ...prev,
        [key]: result.error ?? '決策失敗',
      }));
    }
  };

  return (
    <CollapsibleSection
      storageKey={BATCH_RETENTION_EXPANDED_KEY}
      title="批次 Run 保留決策"
      description="逐項決定是否保留剛完成的 batch run。此面板一次處理所有待決項目（非逐項彈窗）。"
      titleHeadingLevel="h3"
      expandedClassName="glass-panel rounded-xl p-4 border border-amber-300/20 space-y-3"
      collapsedClassName="glass-panel rounded-xl border border-amber-300/20 px-4 py-3"
      contentClassName="space-y-2"
      leading={<Archive className="h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />}
    >
      <div data-testid="batch-retention-panel" className="space-y-2">
        {visiblePending.map((item) => {
          const key = itemKey(item);
          const busy = decidingKeys.has(key);
          return (
            <div
              key={key}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 space-y-2"
              data-testid={`batch-retention-item-${item.symbol}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="font-mono text-slate-200">
                  {item.symbol} / {item.timeframe}
                  <span className="ml-2 text-slate-500">{item.config_hash}</span>
                </div>
                <span className="text-slate-400">state: {busy ? 'deciding' : item.state}</span>
              </div>
              {errors[key] && (
                <p role="alert" className="text-xs text-rose-300">
                  {errors[key]}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleDecision(item, 'retain')}
                  className={`${btnBase} border-cyan-400/30 bg-cyan-400/10 text-cyan-100`}
                  aria-label={`Retain ${item.symbol}`}
                >
                  {busy ? '處理中…' : '保留'}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleDecision(item, 'discard')}
                  className={`${btnBase} border-rose-400/30 text-rose-200`}
                  aria-label={`Discard ${item.symbol}`}
                >
                  {busy ? '處理中…' : '捨棄'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </CollapsibleSection>
  );
}
