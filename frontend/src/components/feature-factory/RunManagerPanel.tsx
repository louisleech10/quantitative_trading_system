'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import type { BulkDeleteResponse, OrphanEntry, RunInfo } from '@/lib/types';
import { sortRunsByRecency } from '@/lib/runExplorer';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import CollapsibleSection from '@/components/feature-factory/CollapsibleSection';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const RUN_MANAGER_EXPANDED_KEY = 'ff-run-manager-expanded';

const thCls =
  'px-3 py-2.5 text-left text-xs text-slate-400 font-medium whitespace-nowrap';
const tdCls = 'px-3 py-2.5 text-xs align-middle';
const btnBase =
  'inline-flex items-center justify-center gap-1 rounded-lg border px-2.5 py-1 text-xs transition disabled:opacity-40 disabled:cursor-not-allowed';

function runKey(run: RunInfo): string {
  return `${run.symbol}-${run.timeframe}-${run.config_hash}`;
}

type BulkDeleteTarget = {
  mode: 'selection' | 'batch';
  batchId?: string;
  runs: RunInfo[];
  excludedActive: RunInfo[];
};

/** 將 bytes 轉為 B / KB / MB / GB */
function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || Number.isNaN(bytes)) return '—';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'] as const;
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exp;
  const digits = exp === 0 ? 0 : value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(digits)} ${units[exp]}`;
}

function shortHash(hash: string): string {
  if (hash.length <= 8) return hash;
  return `${hash.slice(0, 8)}…`;
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return '剛剛';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} 分鐘前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小時前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay} 天前`;
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCreatedAt(createdAt: string | null | undefined): {
  label: string;
  title?: string;
} {
  if (!createdAt) return { label: '—' };
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return { label: createdAt };
  const absolute = date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
  return { label: formatRelativeTime(createdAt), title: absolute };
}

const DEFAULT_BATCH_ID_PREVIEW_LEN = 12;

function shortBatchId(batchId: string, previewLen = DEFAULT_BATCH_ID_PREVIEW_LEN): string {
  if (batchId.length <= previewLen) return batchId;
  return `${batchId.slice(0, previewLen)}…`;
}

/** 在一組 batch_id 中計算可目視區分的短碼（同名 batch_alias 時拉長前綴） */
function disambiguateBatchIds(
  batchIds: string[],
  minDivergingLen = 1,
): Map<string, string> {
  const ids = [...new Set(batchIds)];
  if (ids.length === 0) return new Map();
  if (ids.length === 1) {
    return new Map([[ids[0], shortBatchId(ids[0])]]);
  }

  const sorted = [...ids].sort();
  let lcpLen = 0;
  const [first, last] = [sorted[0], sorted[sorted.length - 1]];
  while (lcpLen < first.length && first[lcpLen] === last[lcpLen]) {
    lcpLen += 1;
  }
  while (
    lcpLen > 0
    && !ids.every((id) => id.startsWith(first.slice(0, lcpLen)))
  ) {
    lcpLen -= 1;
  }

  const maxSuffix = Math.max(...ids.map((id) => id.length - lcpLen));
  const startExtendLen = Math.max(minDivergingLen, 1);
  for (let extendLen = startExtendLen; extendLen <= maxSuffix; extendLen += 1) {
    const previews = ids.map((id) => id.slice(0, lcpLen + extendLen));
    if (new Set(previews).size === ids.length) {
      return new Map(
        ids.map((id) => {
          const previewLen = lcpLen + extendLen;
          return [id, shortBatchId(id, previewLen)];
        }),
      );
    }
  }

  return new Map(ids.map((id) => [id, id]));
}

function batchGroupLabel(batchId: string, batchAlias: string | null | undefined): string {
  const alias = batchAlias?.trim();
  if (alias) return alias;
  return shortBatchId(batchId);
}

function batchLabelForRun(run: RunInfo): string {
  const alias = run.batch_alias?.trim();
  if (alias) return alias;
  const batchId = run.batch_id?.trim();
  if (batchId) return shortBatchId(batchId);
  return '—';
}

type BatchGroup = {
  batchId: string;
  batchAlias: string | null;
  runs: RunInfo[];
};

function groupRunsByBatch(runs: RunInfo[]): { groups: BatchGroup[]; singles: RunInfo[] } {
  const singles: RunInfo[] = [];
  const byBatch = new Map<string, BatchGroup>();
  for (const run of runs) {
    const batchId = run.batch_id?.trim();
    if (!batchId) {
      singles.push(run);
      continue;
    }
    const existing = byBatch.get(batchId);
    if (existing) {
      existing.runs.push(run);
      if (!existing.batchAlias && run.batch_alias?.trim()) {
        existing.batchAlias = run.batch_alias.trim();
      }
    } else {
      byBatch.set(batchId, {
        batchId,
        batchAlias: run.batch_alias?.trim() || null,
        runs: [run],
      });
    }
  }
  const groups = [...byBatch.values()].sort((a, b) => {
    const aTime = Math.max(
      ...a.runs.map((run) => Date.parse(run.last_generated_at ?? run.created_at ?? '') || 0),
    );
    const bTime = Math.max(
      ...b.runs.map((run) => Date.parse(run.last_generated_at ?? run.created_at ?? '') || 0),
    );
    return bTime - aTime;
  });
  return { groups, singles };
}

function displayName(run: RunInfo): { visible: string; fullHash: string; truncated: boolean } {
  const alias = run.alias?.trim();
  if (alias) return { visible: alias, fullHash: run.config_hash, truncated: false };
  const truncated = run.config_hash.length > 8;
  return {
    visible: shortHash(run.config_hash),
    fullHash: run.config_hash,
    truncated,
  };
}

function dedupeSelectedRuns(runs: RunInfo[]): RunInfo[] {
  const seen = new Set<string>();
  const result: RunInfo[] = [];
  for (const run of runs) {
    const key = runKey(run);
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(run);
  }
  return result;
}

export default function RunManagerPanel() {
  const {
    runs,
    runsLoading,
    runsError,
    fetchRuns,
    updateRunAlias,
    setBatchAlias,
    deleteRun,
    bulkDeleteRuns,
    scanOrphans,
    cleanOrphans,
  } = useFeatureFactoryStore();
  const sortedRuns = useMemo(() => sortRunsByRecency(runs), [runs]);
  const { groups, singles } = useMemo(() => groupRunsByBatch(sortedRuns), [sortedRuns]);
  const selectableRuns = useMemo(
    () => sortedRuns.filter((run) => !run.active),
    [sortedRuns],
  );
  const batchIdPreviewById = useMemo(() => {
    const aliasToIds = new Map<string, string[]>();
    for (const group of groups) {
      const alias = group.batchAlias?.trim();
      if (!alias) continue;
      const existing = aliasToIds.get(alias) ?? [];
      existing.push(group.batchId);
      aliasToIds.set(alias, existing);
    }
    const previews = new Map<string, string>();
    for (const group of groups) {
      const alias = group.batchAlias?.trim();
      const peerIds = alias ? aliasToIds.get(alias) ?? [group.batchId] : [group.batchId];
      const disambiguated = disambiguateBatchIds(
        peerIds,
        peerIds.length > 1 ? 3 : 1,
      );
      previews.set(group.batchId, disambiguated.get(group.batchId) ?? shortBatchId(group.batchId));
    }
    return previews;
  }, [groups]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [renamingKey, setRenamingKey] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [savingRename, setSavingRename] = useState(false);
  const [batchRenamingId, setBatchRenamingId] = useState<string | null>(null);
  const [batchRenameValue, setBatchRenameValue] = useState('');
  const [savingBatchRename, setSavingBatchRename] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(() => new Set());
  const [bulkDeleteTarget, setBulkDeleteTarget] = useState<BulkDeleteTarget | null>(null);
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkDeleteResponse | null>(null);
  const [orphanDialogOpen, setOrphanDialogOpen] = useState(false);
  const [orphanScanning, setOrphanScanning] = useState(false);
  const [orphanCleaning, setOrphanCleaning] = useState(false);
  const [orphanList, setOrphanList] = useState<OrphanEntry[]>([]);
  const [orphanConfirmClean, setOrphanConfirmClean] = useState(false);
  const [orphanCleanResult, setOrphanCleanResult] = useState<string | null>(null);

  const selectedRuns = useMemo(
    () => dedupeSelectedRuns(
      sortedRuns.filter((run) => selectedKeys.has(runKey(run)) && !run.active),
    ),
    [sortedRuns, selectedKeys],
  );
  const excludedActiveRuns = useMemo(
    () => sortedRuns.filter((run) => selectedKeys.has(runKey(run)) && run.active),
    [sortedRuns, selectedKeys],
  );
  const targetRuns = useMemo(
    () => bulkDeleteTarget?.runs ?? [],
    [bulkDeleteTarget],
  );
  const targetExcludedActive = useMemo(
    () => bulkDeleteTarget?.excludedActive ?? [],
    [bulkDeleteTarget],
  );
  const targetTotalBytes = useMemo(
    () => targetRuns.reduce((sum, run) => sum + (run.size_bytes ?? 0), 0),
    [targetRuns],
  );
  const allSelectableSelected = selectableRuns.length > 0
    && selectableRuns.every((run) => selectedKeys.has(runKey(run)));
  const someSelectableSelected = selectableRuns.some((run) => selectedKeys.has(runKey(run)));

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    setSelectedKeys((prev) => {
      const valid = new Set(sortedRuns.map(runKey));
      const next = new Set([...prev].filter((key) => valid.has(key)));
      return next.size === prev.size ? prev : next;
    });
  }, [sortedRuns]);

  const toggleRunSelection = (run: RunInfo) => {
    if (run.active) return;
    const key = runKey(run);
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allSelectableSelected) {
      setSelectedKeys(new Set());
      return;
    }
    setSelectedKeys(new Set(selectableRuns.map(runKey)));
  };

  const openBulkConfirm = () => {
    if (selectedRuns.length === 0) return;
    setBulkResult(null);
    setBulkDeleteTarget({
      mode: 'selection',
      runs: selectedRuns,
      excludedActive: excludedActiveRuns,
    });
    setBulkConfirmOpen(true);
  };

  const openBatchDeleteConfirm = (group: { batchId: string; runs: RunInfo[] }) => {
    const deletable = dedupeSelectedRuns(group.runs.filter((run) => !run.active));
    const excluded = group.runs.filter((run) => run.active);
    if (deletable.length === 0) {
      setActionError('此批次無可刪除的 Run（全部使用中）');
      return;
    }
    setActionError(null);
    setBulkResult(null);
    setBulkDeleteTarget({
      mode: 'batch',
      batchId: group.batchId,
      runs: deletable,
      excludedActive: excluded,
    });
    setBulkConfirmOpen(true);
  };

  const closeBulkConfirm = () => {
    if (bulkDeleting) return;
    setBulkConfirmOpen(false);
    if (bulkResult && bulkDeleteTarget?.mode === 'selection') {
      const deletedKeys = new Set(
        bulkResult.deleted.map((item) => `${item.symbol}-${item.timeframe}-${item.config_hash}`),
      );
      setSelectedKeys((prev) => new Set([...prev].filter((key) => !deletedKeys.has(key))));
    }
    setBulkDeleteTarget(null);
    setBulkResult(null);
  };

  const executeBulkDelete = async () => {
    if (targetRuns.length === 0) return;
    setBulkDeleting(true);
    setActionError(null);
    const result = await bulkDeleteRuns(
      targetRuns.map((run) => ({
        symbol: run.symbol,
        timeframe: run.timeframe,
        config_hash: run.config_hash,
      })),
    );
    setBulkDeleting(false);
    if (!result.ok) {
      setActionError(result.error ?? '批次刪除失敗');
      return;
    }
    setBulkResult(result.data);
    if (result.data.failed.length > 0) {
      const summary = result.data.failed
        .map((item) => `${item.symbol}/${item.timeframe}: ${item.error ?? 'failed'}`)
        .join('; ');
      setActionError(`部分刪除失敗：${summary}`);
    }
  };

  const openOrphanDialog = async () => {
    setOrphanDialogOpen(true);
    setOrphanConfirmClean(false);
    setOrphanCleanResult(null);
    setOrphanScanning(true);
    setActionError(null);
    const result = await scanOrphans();
    setOrphanScanning(false);
    if (!result.ok) {
      setActionError(result.error ?? '孤兒掃描失敗');
      setOrphanList([]);
      return;
    }
    setOrphanList(result.data.orphans);
  };

  const closeOrphanDialog = () => {
    if (orphanCleaning) return;
    setOrphanDialogOpen(false);
    setOrphanConfirmClean(false);
    setOrphanList([]);
    setOrphanCleanResult(null);
  };

  const executeOrphanClean = async () => {
    setOrphanCleaning(true);
    setActionError(null);
    const result = await cleanOrphans(false);
    setOrphanCleaning(false);
    if (!result.ok) {
      setActionError(result.error ?? '孤兒清理失敗');
      return;
    }
    const { cleaned_registry: reg, cleaned_leaves: leaves, errors } = result.data;
    if (errors.length > 0) {
      setActionError(`孤兒清理部分失敗：${errors.join('; ')}`);
    }
    setOrphanCleanResult(`已清理 registry ${reg} 筆、leaf ${leaves} 筆`);
    setOrphanList(result.data.orphans);
    setOrphanConfirmClean(false);
  };

  const openRename = (run: RunInfo) => {
    const key = runKey(run);
    setRenamingKey(key);
    setRenameValue(run.alias?.trim() ?? '');
    setActionError(null);
  };

  const closeRename = () => {
    setRenamingKey(null);
    setRenameValue('');
    setSavingRename(false);
  };

  const openBatchRename = (group: BatchGroup) => {
    setBatchRenamingId(group.batchId);
    setBatchRenameValue(group.batchAlias ?? '');
    setActionError(null);
  };

  const closeBatchRename = () => {
    setBatchRenamingId(null);
    setBatchRenameValue('');
    setSavingBatchRename(false);
  };

  const saveBatchRename = async (batchId: string) => {
    setSavingBatchRename(true);
    setActionError(null);
    const result = await setBatchAlias(batchId, batchRenameValue.trim());
    setSavingBatchRename(false);
    if (!result.ok) {
      setActionError(result.error ?? '批次命名失敗');
      return;
    }
    closeBatchRename();
  };

  const saveRename = async (run: RunInfo) => {
    setSavingRename(true);
    setActionError(null);
    const result = await updateRunAlias(
      run.symbol,
      run.timeframe,
      run.config_hash,
      renameValue.trim(),
    );
    setSavingRename(false);
    if (!result.ok) {
      setActionError(result.error ?? '命名失敗');
      return;
    }
    closeRename();
  };

  const remove = async (run: RunInfo) => {
    const sizeLabel = formatBytes(run.size_bytes);
    if (!confirm(`刪除 ${sizeLabel}（含 CGSA）？`)) return;
    setActionError(null);
    const result = await deleteRun(run.symbol, run.timeframe, run.config_hash);
    if (!result.ok) {
      setActionError(result.error ?? '刪除失敗');
    }
  };

  const renamingRun = renamingKey ? runs.find((run) => runKey(run) === renamingKey) : undefined;
  const batchRenamingGroup = batchRenamingId
    ? groups.find((group) => group.batchId === batchRenamingId)
    : undefined;
  const runCountLabel = runsLoading ? '載入中…' : `${runs.length} 個 Run`;

  const renderRunRow = (run: RunInfo, indent = false) => {
    const key = runKey(run);
    const name = displayName(run);
    const created = formatCreatedAt(run.last_generated_at ?? run.created_at);
    const isSelected = selectedKeys.has(key);
    return (
      <tr key={key} className="hover:bg-white/5 transition-colors">
        <td className={`${tdCls} w-10`}>
          <input
            type="checkbox"
            aria-label={`選取 ${name.visible}`}
            checked={isSelected}
            disabled={run.active || bulkDeleting}
            title={run.active ? '使用中無法選取' : undefined}
            onChange={() => toggleRunSelection(run)}
            className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 disabled:opacity-40"
          />
        </td>
        <td className={`${tdCls} text-slate-200 font-medium max-w-[180px] ${indent ? 'pl-6' : ''}`}>
          <span title={name.fullHash} className="truncate block">
            {name.visible}
          </span>
          {name.truncated && (
            <span className="sr-only">{run.config_hash}</span>
          )}
        </td>
        <td className={`${tdCls} text-slate-300 font-mono`}>
          {run.symbol}
          <span className="text-slate-500 mx-1">/</span>
          {run.timeframe}
        </td>
        <td className={`${tdCls} text-slate-400 text-right tabular-nums`}>
          {formatBytes(run.size_bytes)}
        </td>
        <td className={`${tdCls} text-slate-400`} title={created.title}>
          {created.label}
        </td>
        <td className={tdCls}>
          {run.active ? (
            <span className="inline-flex items-center rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-200">
              使用中
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-slate-500">
              閒置
            </span>
          )}
        </td>
        <td className={`${tdCls} text-right`}>
          <div className="inline-flex items-center gap-2 justify-end">
            <button
              type="button"
              aria-label={`重命名 ${name.visible}`}
              onClick={() => openRename(run)}
              className={`${btnBase} border-white/15 text-slate-200 hover:border-cyan-300/40 hover:bg-white/5`}
            >
              <Pencil className="h-3 w-3" aria-hidden />
              重命名
            </button>
            <button
              type="button"
              disabled={run.active}
              title={run.active ? '使用中無法刪除' : undefined}
              onClick={() => void remove(run)}
              className={`${btnBase} border-rose-400/30 text-rose-200 hover:border-rose-300/50 hover:bg-rose-400/10`}
            >
              <Trash2 className="h-3 w-3" aria-hidden />
              刪除
            </button>
          </div>
        </td>
      </tr>
    );
  };

  return (
    <CollapsibleSection
      storageKey={RUN_MANAGER_EXPANDED_KEY}
      title="Run 管理"
      description={`命名、檢視與刪除已產生的 Feature Run · ${runCountLabel}`}
    >
      {runsLoading && (
        <p className="text-sm text-slate-400">載入 Runs…</p>
      )}

      {!runsLoading && runsError && (
        <div className="space-y-3">
          <p role="alert" className="text-sm text-rose-300">
            {runsError}
          </p>
          <button
            type="button"
            onClick={() => void fetchRuns()}
            className={`${btnBase} border-white/15 text-slate-200 hover:border-cyan-300/40 hover:bg-white/5`}
          >
            重試
          </button>
        </div>
      )}

      {!runsLoading && !runsError && actionError && (
        <p role="alert" className="text-xs text-rose-300 border border-rose-400/30 bg-rose-400/10 rounded-lg px-3 py-2">
          {actionError}
        </p>
      )}

      {!runsLoading && !runsError && runs.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={selectedRuns.length === 0 || bulkDeleting}
            onClick={openBulkConfirm}
            className={`${btnBase} border-rose-400/30 text-rose-200 hover:border-rose-300/50 hover:bg-rose-400/10`}
          >
            <Trash2 className="h-3 w-3" aria-hidden />
            批次刪除{selectedRuns.length > 0 ? ` (${selectedRuns.length})` : ''}
          </button>
          <button
            type="button"
            disabled={orphanScanning || orphanCleaning}
            onClick={() => void openOrphanDialog()}
            className={`${btnBase} border-amber-400/30 text-amber-100 hover:border-amber-300/50 hover:bg-amber-400/10`}
          >
            孤兒清理
          </button>
        </div>
      )}

      {!runsLoading && !runsError && runs.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-8">尚無 Runs</p>
      ) : !runsLoading && !runsError && runs.length > 0 ? (
        <div className="overflow-auto rounded-xl border border-white/10 bg-white/[0.03]">
          <table className="w-full min-w-[800px]">
            <thead className="sticky top-0 bg-[#0f1117]/90 backdrop-blur-sm border-b border-white/10">
              <tr>
                <th className={`${thCls} w-10`}>
                  <input
                    type="checkbox"
                    aria-label="全選可刪除的 Run"
                    checked={allSelectableSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelectableSelected && !allSelectableSelected;
                    }}
                    disabled={selectableRuns.length === 0 || bulkDeleting}
                    onChange={toggleSelectAll}
                    className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 disabled:opacity-40"
                  />
                </th>
                <th className={thCls}>名稱</th>
                <th className={thCls}>Symbol / TF</th>
                <th className={`${thCls} text-right`}>大小</th>
                <th className={thCls}>建立時間</th>
                <th className={thCls}>狀態</th>
                <th className={`${thCls} text-right`}>操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {groups.map((group) => {
                const headerLabel = batchGroupLabel(group.batchId, group.batchAlias);
                const batchIdPreview = batchIdPreviewById.get(group.batchId) ?? shortBatchId(group.batchId);
                return (
                  <Fragment key={`batch-${group.batchId}`}>
                    <tr className="bg-white/[0.04]">
                      <td className={tdCls} />
                      <td colSpan={5} className={`${tdCls} text-slate-200 font-medium`}>
                        <span title={group.batchId}>
                          批次：{headerLabel}
                        </span>
                        <span className="ml-2 text-slate-500">
                          ({group.runs.length} runs · {batchIdPreview})
                        </span>
                      </td>
                      <td className={`${tdCls} text-right`}>
                        <div className="flex flex-wrap justify-end gap-1">
                          <button
                            type="button"
                            aria-label={`重命名整批 ${headerLabel}`}
                            onClick={() => openBatchRename(group)}
                            className={`${btnBase} border-cyan-400/30 text-cyan-100 hover:border-cyan-300/50 hover:bg-cyan-400/10`}
                          >
                            <Pencil className="h-3 w-3" aria-hidden />
                            重命名整批
                          </button>
                          <button
                            type="button"
                            aria-label={`刪除整批 ${headerLabel}`}
                            disabled={bulkDeleting}
                            onClick={() => openBatchDeleteConfirm(group)}
                            className={`${btnBase} border-rose-400/30 text-rose-200 hover:border-rose-300/50 hover:bg-rose-400/10`}
                          >
                            <Trash2 className="h-3 w-3" aria-hidden />
                            刪除整批
                          </button>
                        </div>
                      </td>
                    </tr>
                    {sortRunsByRecency(group.runs).map((run) => renderRunRow(run, true))}
                  </Fragment>
                );
              })}
              {singles.map((run) => renderRunRow(run))}
            </tbody>
          </table>
        </div>
      ) : null}

      {bulkConfirmOpen && (
      <Dialog open onOpenChange={(open) => { if (!open) closeBulkConfirm(); }}>
        <DialogContent className="max-w-2xl gap-4 p-5" aria-label="確認批次刪除">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold text-slate-100">
              {bulkResult ? '批次刪除結果' : '確認批次刪除'}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              {bulkResult
                ? `已刪除 ${bulkResult.deleted.length} 筆，失敗 ${bulkResult.failed.length} 筆，略過 ${bulkResult.skipped.length} 筆`
                : bulkDeleteTarget?.mode === 'batch'
                  ? `即將刪除整批 ${targetRuns.length} 筆 Run，共 ${formatBytes(targetTotalBytes)}（含 CGSA）`
                  : `即將刪除 ${targetRuns.length} 筆 Run，共 ${formatBytes(targetTotalBytes)}（含 CGSA）`}
            </DialogDescription>
          </DialogHeader>
          {!bulkResult && targetExcludedActive.length > 0 && (
            <div
              role="note"
              className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-100"
            >
              <p className="mb-1 font-medium">
                已排除 {targetExcludedActive.length} 筆使用中 Run（不會送出刪除）：
              </p>
              <ul className="list-disc pl-4 text-amber-100/90">
                {targetExcludedActive.map((run) => {
                  const name = displayName(run);
                  return (
                    <li key={runKey(run)}>
                      {run.symbol}/{run.timeframe} · {name.visible} · {run.config_hash}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          <div className="max-h-64 overflow-auto rounded-lg border border-white/10">
            <table className="w-full text-xs">
              <thead className="bg-white/[0.04] text-slate-400">
                <tr>
                  <th className="px-2 py-1.5 text-left font-medium">Symbol/TF</th>
                  <th className="px-2 py-1.5 text-left font-medium">別名</th>
                  <th className="px-2 py-1.5 text-left font-medium">Hash</th>
                  <th className="px-2 py-1.5 text-right font-medium">大小</th>
                  <th className="px-2 py-1.5 text-left font-medium">批次</th>
                  {bulkResult && <th className="px-2 py-1.5 text-left font-medium">結果</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {(bulkResult
                  ? [
                    ...bulkResult.deleted.map((item) => ({ item, status: 'deleted' as const, run: targetRuns.find((r) => runKey(r) === `${item.symbol}-${item.timeframe}-${item.config_hash}`) })),
                    ...bulkResult.failed.map((item) => ({ item, status: 'failed' as const, run: targetRuns.find((r) => runKey(r) === `${item.symbol}-${item.timeframe}-${item.config_hash}`) })),
                    ...bulkResult.skipped.map((item) => ({ item, status: 'skipped' as const, run: targetRuns.find((r) => runKey(r) === `${item.symbol}-${item.timeframe}-${item.config_hash}`) })),
                  ]
                  : targetRuns.map((run) => ({
                    item: {
                      symbol: run.symbol,
                      timeframe: run.timeframe,
                      config_hash: run.config_hash,
                      bytes: run.size_bytes ?? 0,
                    },
                    status: undefined,
                    run,
                  }))
                ).map(({ item, status, run }) => {
                  const name = run ? displayName(run) : { visible: shortHash(item.config_hash), fullHash: item.config_hash };
                  return (
                    <tr key={`${item.symbol}-${item.timeframe}-${item.config_hash}-${status ?? 'confirm'}`}>
                      <td className="px-2 py-1.5 font-mono">{item.symbol}/{item.timeframe}</td>
                      <td className="px-2 py-1.5">{name.visible}</td>
                      <td className="px-2 py-1.5 font-mono text-slate-500" title={item.config_hash}>{item.config_hash}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{formatBytes(item.bytes ?? run?.size_bytes)}</td>
                      <td className="px-2 py-1.5">{run ? batchLabelForRun(run) : '—'}</td>
                      {bulkResult && (
                        <td className="px-2 py-1.5">
                          {status === 'deleted' && <span className="text-emerald-300">已刪除</span>}
                          {status === 'failed' && (
                            <span className="text-rose-300" title={item.error ?? undefined}>
                              失敗{item.error ? `: ${item.error}` : ''}
                            </span>
                          )}
                          {status === 'skipped' && (
                            <span className="text-amber-200" title={item.error ?? undefined}>
                              略過{item.error ? `: ${item.error}` : ''}
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!bulkResult && (
            <p className="text-xs text-slate-500">
              總計：{targetRuns.length} 筆 · {formatBytes(targetTotalBytes)}
            </p>
          )}
          <DialogFooter className="gap-2 sm:justify-end">
            <button
              type="button"
              disabled={bulkDeleting}
              onClick={closeBulkConfirm}
              className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
            >
              {bulkResult ? '關閉' : '取消'}
            </button>
            {!bulkResult && (
              <button
                type="button"
                disabled={bulkDeleting || targetRuns.length === 0}
                onClick={() => void executeBulkDelete()}
                className={`${btnBase} border-rose-400/30 bg-rose-400/10 text-rose-100 hover:border-rose-300/50`}
              >
                {bulkDeleting ? '刪除中…' : '確認刪除'}
              </button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      )}

      {orphanDialogOpen && (
      <Dialog open onOpenChange={(open) => { if (!open) closeOrphanDialog(); }}>
        <DialogContent className="max-w-2xl gap-4 p-5" aria-label="孤兒清理">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold text-slate-100">孤兒清理</DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              {orphanScanning
                ? '掃描中…'
                : orphanCleanResult
                  ? orphanCleanResult
                  : `掃描到 ${orphanList.length} 筆孤兒（registry 與 features/CGSA leaf 不一致）`}
            </DialogDescription>
          </DialogHeader>
          {!orphanScanning && orphanList.length > 0 && (
            <div className="max-h-64 overflow-auto rounded-lg border border-white/10">
              <table className="w-full text-xs">
                <thead className="bg-white/[0.04] text-slate-400">
                  <tr>
                    <th className="px-2 py-1.5 text-left font-medium">類型</th>
                    <th className="px-2 py-1.5 text-left font-medium">Symbol/TF</th>
                    <th className="px-2 py-1.5 text-left font-medium">Hash</th>
                    <th className="px-2 py-1.5 text-left font-medium">Leaf</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {orphanList.map((orphan) => (
                    <tr key={`${orphan.kind}-${orphan.symbol}-${orphan.timeframe}-${orphan.config_hash}`}>
                      <td className="px-2 py-1.5">{orphan.kind}</td>
                      <td className="px-2 py-1.5 font-mono">{orphan.symbol}/{orphan.timeframe}</td>
                      <td className="px-2 py-1.5 font-mono text-slate-500">{orphan.config_hash}</td>
                      <td className="px-2 py-1.5">{orphan.leaf_kind ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!orphanScanning && orphanList.length === 0 && !orphanCleanResult && (
            <p className="text-sm text-slate-500 text-center py-4">未發現孤兒</p>
          )}
          <DialogFooter className="gap-2 sm:justify-end">
            <button
              type="button"
              disabled={orphanCleaning}
              onClick={closeOrphanDialog}
              className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
            >
              關閉
            </button>
            {!orphanScanning && orphanList.length > 0 && !orphanCleanResult && (
              <button
                type="button"
                disabled={orphanCleaning}
                onClick={() => setOrphanConfirmClean(true)}
                className={`${btnBase} border-amber-400/30 bg-amber-400/10 text-amber-100 hover:border-amber-300/50`}
              >
                清理孤兒
              </button>
            )}
          </DialogFooter>
          {orphanConfirmClean && (
            <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">
              <p className="mb-2">確認清理 {orphanList.length} 筆孤兒？此操作無法復原。</p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  disabled={orphanCleaning}
                  onClick={() => setOrphanConfirmClean(false)}
                  className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={orphanCleaning}
                  onClick={() => void executeOrphanClean()}
                  className={`${btnBase} border-amber-400/30 bg-amber-400/10 text-amber-100 hover:border-amber-300/50`}
                >
                  {orphanCleaning ? '清理中…' : '確認清理'}
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      )}

      {renamingKey !== null && (
      <Dialog open onOpenChange={(open) => { if (!open) closeRename(); }}>
        <DialogContent className="max-w-md gap-4 p-5" aria-label="重命名 Run">
          {renamingRun && (
            <>
              <DialogHeader>
                <DialogTitle className="text-sm font-semibold text-slate-100">重命名 Run</DialogTitle>
                <DialogDescription
                  className="text-xs text-slate-400 font-mono truncate"
                  title={renamingRun.config_hash}
                >
                  {renamingRun.symbol} / {renamingRun.timeframe} · {shortHash(renamingRun.config_hash)}
                </DialogDescription>
              </DialogHeader>
              <input
                aria-label={`Alias ${renamingRun.config_hash}`}
                value={renameValue}
                onChange={(event) => setRenameValue(event.target.value)}
                placeholder="輸入顯示名稱"
                className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-300/40"
                autoFocus
              />
              <DialogFooter className="gap-2 sm:justify-end">
                <button
                  type="button"
                  onClick={closeRename}
                  className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={savingRename}
                  onClick={() => void saveRename(renamingRun)}
                  className={`${btnBase} border-cyan-400/30 bg-cyan-400/10 text-cyan-100 hover:border-cyan-300/50`}
                >
                  {savingRename ? '儲存中…' : '儲存'}
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
      )}

      {batchRenamingId !== null && (
      <Dialog open onOpenChange={(open) => { if (!open) closeBatchRename(); }}>
        <DialogContent className="max-w-md gap-4 p-5" aria-label="重命名整批 Run">
          {batchRenamingGroup && (
            <>
              <DialogHeader>
                <DialogTitle className="text-sm font-semibold text-slate-100">重命名整批</DialogTitle>
                <DialogDescription className="text-xs text-slate-400 font-mono truncate" title={batchRenamingGroup.batchId}>
                  batch_id · {shortBatchId(batchRenamingGroup.batchId)} · {batchRenamingGroup.runs.length} runs
                </DialogDescription>
              </DialogHeader>
              <input
                aria-label={`Batch alias ${batchRenamingGroup.batchId}`}
                value={batchRenameValue}
                onChange={(event) => setBatchRenameValue(event.target.value)}
                placeholder="輸入批次顯示名稱"
                className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-300/40"
                autoFocus
              />
              <DialogFooter className="gap-2 sm:justify-end">
                <button
                  type="button"
                  onClick={closeBatchRename}
                  className={`${btnBase} border-white/15 text-slate-300 hover:bg-white/5`}
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={savingBatchRename}
                  onClick={() => void saveBatchRename(batchRenamingGroup.batchId)}
                  className={`${btnBase} border-cyan-400/30 bg-cyan-400/10 text-cyan-100 hover:border-cyan-300/50`}
                >
                  {savingBatchRename ? '儲存中…' : '儲存'}
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
      )}
    </CollapsibleSection>
  );
}
