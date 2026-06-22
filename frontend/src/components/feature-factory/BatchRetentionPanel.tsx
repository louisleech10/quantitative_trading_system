'use client';

import { useEffect, useMemo, useState } from 'react';
import { Archive } from 'lucide-react';
import type { BatchRetentionItem } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import CollapsibleSection from './CollapsibleSection';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const BATCH_RETENTION_EXPANDED_KEY = 'ff-batch-retention-expanded';

const btnBase =
  'inline-flex items-center justify-center rounded-lg border px-2.5 py-1.5 text-xs transition disabled:opacity-40 disabled:cursor-not-allowed';

function itemKey(item: Pick<BatchRetentionItem, 'symbol' | 'timeframe' | 'config_hash'>): string {
  return `${item.symbol}|${item.timeframe}|${item.config_hash}`;
}

type DiscardConfirmMode = 'selected' | 'all' | null;

export default function BatchRetentionPanel() {
  const batchTask = useFeatureFactoryStore((state) => state.batchTask);
  const batchConnectionStatus = useFeatureFactoryStore((state) => state.batchConnectionStatus);
  const fetchBatchRetentionPending = useFeatureFactoryStore((state) => state.fetchBatchRetentionPending);
  const applyBatchRetentionDecision = useFeatureFactoryStore((state) => state.applyBatchRetentionDecision);
  const bulkRetentionDecision = useFeatureFactoryStore((state) => state.bulkRetentionDecision);

  const batchId = batchTask?.batch_id ?? batchTask?.task_id ?? null;

  const [decidingKeys, setDecidingKeys] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(() => new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [discardConfirmMode, setDiscardConfirmMode] = useState<DiscardConfirmMode>(null);

  const visiblePending = useMemo(() => {
    const pending = batchTask?.retention_pending ?? [];
    return pending.filter((item) => item.state === 'pending' || decidingKeys.has(itemKey(item)));
  }, [batchTask?.retention_pending, decidingKeys]);

  const pendingOnly = useMemo(
    () => visiblePending.filter((item) => item.state === 'pending'),
    [visiblePending],
  );

  const allPendingSelected = pendingOnly.length > 0
    && pendingOnly.every((item) => selectedKeys.has(itemKey(item)));
  const somePendingSelected = pendingOnly.some((item) => selectedKeys.has(itemKey(item)));
  const isBusy = bulkBusy || decidingKeys.size > 0;

  const discardTargets = useMemo(() => {
    if (discardConfirmMode === 'all') return pendingOnly;
    if (discardConfirmMode === 'selected') {
      return pendingOnly.filter((item) => selectedKeys.has(itemKey(item)));
    }
    return [];
  }, [discardConfirmMode, pendingOnly, selectedKeys]);

  useEffect(() => {
    if (!batchId) return;
    void fetchBatchRetentionPending(batchId);
  }, [batchId, fetchBatchRetentionPending]);

  useEffect(() => {
    if (!batchId || batchConnectionStatus !== 'lost') return;
    void fetchBatchRetentionPending(batchId);
  }, [batchConnectionStatus, batchId, fetchBatchRetentionPending]);

  useEffect(() => {
    const valid = new Set(visiblePending.map(itemKey));
    setSelectedKeys((prev) => {
      const next = new Set([...prev].filter((key) => valid.has(key)));
      return next.size === prev.size ? prev : next;
    });
  }, [visiblePending]);

  if (visiblePending.length === 0) {
    return null;
  }

  const toggleSelection = (item: BatchRetentionItem) => {
    const key = itemKey(item);
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allPendingSelected) {
      setSelectedKeys(new Set());
      return;
    }
    setSelectedKeys(new Set(pendingOnly.map(itemKey)));
  };

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
    } else {
      setSelectedKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  const handleRetainAll = async () => {
    if (!batchId || pendingOnly.length === 0) return;
    setBulkBusy(true);
    setActionErrorsClear();
    const result = await bulkRetentionDecision(
      batchId,
      'retain',
      pendingOnly.map((item) => ({
        symbol: item.symbol,
        timeframe: item.timeframe,
        config_hash: item.config_hash,
      })),
    );
    setBulkBusy(false);
    if (!result.ok) {
      setErrors((prev) => ({ ...prev, _bulk: result.error ?? '批量保留失敗' }));
      return;
    }
    setSelectedKeys(new Set());
    const failed = result.data.results.filter((item) => item.status === 'failed');
    if (failed.length > 0) {
      const nextErrors: Record<string, string> = {};
      for (const item of failed) {
        nextErrors[itemKey(item)] = item.error ?? item.code ?? 'failed';
      }
      setErrors(nextErrors);
    }
  };

  const setActionErrorsClear = () => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next._bulk;
      return next;
    });
  };

  const executeBulkDiscard = async () => {
    if (!batchId || discardTargets.length === 0) return;
    setBulkBusy(true);
    setActionErrorsClear();
    const result = await bulkRetentionDecision(
      batchId,
      'discard',
      discardTargets.map((item) => ({
        symbol: item.symbol,
        timeframe: item.timeframe,
        config_hash: item.config_hash,
      })),
    );
    setBulkBusy(false);
    setDiscardConfirmMode(null);
    if (!result.ok) {
      setErrors((prev) => ({ ...prev, _bulk: result.error ?? '批量丟棄失敗' }));
      return;
    }
    const succeededKeys = new Set(
      result.data.results
        .filter((item) => item.status === 'succeeded')
        .map((item) => itemKey(item)),
    );
    setSelectedKeys((prev) => new Set([...prev].filter((key) => !succeededKeys.has(key))));
    const failed = result.data.results.filter((item) => item.status === 'failed');
    if (failed.length > 0) {
      const nextErrors: Record<string, string> = {};
      for (const item of failed) {
        nextErrors[itemKey(item)] = item.error ?? item.code ?? 'failed';
      }
      setErrors(nextErrors);
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
      <div data-testid="batch-retention-panel" className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={isBusy || pendingOnly.length === 0}
            onClick={() => void handleRetainAll()}
            className={`${btnBase} border-cyan-400/30 bg-cyan-400/10 text-cyan-100`}
            aria-label="全部保留"
          >
            {bulkBusy ? '處理中…' : '全部保留'}
          </button>
          <button
            type="button"
            disabled={isBusy || !somePendingSelected}
            onClick={() => setDiscardConfirmMode('selected')}
            className={`${btnBase} border-rose-400/30 text-rose-200`}
            aria-label="丟棄選取"
          >
            丟棄選取
          </button>
          <button
            type="button"
            disabled={isBusy || pendingOnly.length === 0}
            onClick={() => setDiscardConfirmMode('all')}
            className={`${btnBase} border-rose-400/30 text-rose-200`}
            aria-label="全部丟棄"
          >
            全部丟棄
          </button>
          <label className="ml-auto inline-flex items-center gap-1.5 text-xs text-slate-400">
            <input
              type="checkbox"
              aria-label="全選待決項目"
              checked={allPendingSelected}
              ref={(el) => {
                if (el) el.indeterminate = somePendingSelected && !allPendingSelected;
              }}
              disabled={isBusy || pendingOnly.length === 0}
              onChange={toggleSelectAll}
              className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 disabled:opacity-40"
            />
            全選
          </label>
        </div>
        {errors._bulk && (
          <p role="alert" className="text-xs text-rose-300">
            {errors._bulk}
          </p>
        )}
        {visiblePending.map((item) => {
          const key = itemKey(item);
          const busy = decidingKeys.has(key) || bulkBusy;
          const selectable = item.state === 'pending';
          return (
            <div
              key={key}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 space-y-2"
              data-testid={`batch-retention-item-${item.symbol}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  {selectable && (
                    <input
                      type="checkbox"
                      aria-label={`選取 ${item.symbol}`}
                      checked={selectedKeys.has(key)}
                      disabled={isBusy}
                      onChange={() => toggleSelection(item)}
                      className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 disabled:opacity-40"
                    />
                  )}
                  <div className="font-mono text-slate-200">
                    {item.symbol} / {item.timeframe}
                    <span className="ml-2 text-slate-500">{item.config_hash}</span>
                  </div>
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

      {discardConfirmMode && (
        <Dialog open onOpenChange={(open) => { if (!open && !bulkBusy) setDiscardConfirmMode(null); }}>
          <DialogContent className="max-w-lg gap-4 p-5" aria-label="確認丟棄選取">
            <DialogHeader>
              <DialogTitle className="text-sm font-semibold text-slate-100">
                確認丟棄
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-400">
                {discardConfirmMode === 'all'
                  ? `即將丟棄全部 ${discardTargets.length} 筆待決 Run（會刪除檔案，無法復原）`
                  : `即將丟棄選取的 ${discardTargets.length} 筆 Run（會刪除檔案，無法復原）`}
              </DialogDescription>
            </DialogHeader>
            <ul className="max-h-40 overflow-auto rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 list-disc pl-5">
              {discardTargets.map((item) => (
                <li key={itemKey(item)}>
                  {item.symbol}/{item.timeframe} · {item.config_hash}
                </li>
              ))}
            </ul>
            <DialogFooter className="gap-2 sm:justify-end">
              <button
                type="button"
                disabled={bulkBusy}
                onClick={() => setDiscardConfirmMode(null)}
                className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
              >
                取消
              </button>
              <button
                type="button"
                disabled={bulkBusy || discardTargets.length === 0}
                onClick={() => void executeBulkDiscard()}
                className={`${btnBase} border-rose-400/30 bg-rose-400/10 text-rose-100`}
              >
                {bulkBusy ? '刪除中…' : '確認丟棄'}
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </CollapsibleSection>
  );
}
