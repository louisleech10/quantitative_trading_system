'use client';

import { useEffect, useMemo, useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import type { RunInfo } from '@/lib/types';
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

export default function RunManagerPanel() {
  const { runs, runsLoading, runsError, fetchRuns, updateRunAlias, deleteRun } = useFeatureFactoryStore();
  const sortedRuns = useMemo(() => sortRunsByRecency(runs), [runs]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [renamingKey, setRenamingKey] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [savingRename, setSavingRename] = useState(false);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

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
  const runCountLabel = runsLoading ? '載入中…' : `${runs.length} 個 Run`;

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

      {!runsLoading && !runsError && runs.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-8">尚無 Runs</p>
      ) : !runsLoading && !runsError && runs.length > 0 ? (
        <div className="overflow-auto rounded-xl border border-white/10 bg-white/[0.03]">
          <table className="w-full min-w-[760px]">
            <thead className="sticky top-0 bg-[#0f1117]/90 backdrop-blur-sm border-b border-white/10">
              <tr>
                <th className={thCls}>名稱</th>
                <th className={thCls}>Symbol / TF</th>
                <th className={`${thCls} text-right`}>大小</th>
                <th className={thCls}>建立時間</th>
                <th className={thCls}>狀態</th>
                <th className={`${thCls} text-right`}>操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {sortedRuns.map((run) => {
                const key = runKey(run);
                const name = displayName(run);
                const created = formatCreatedAt(run.last_generated_at ?? run.created_at);
                return (
                  <tr key={key} className="hover:bg-white/5 transition-colors">
                    <td className={`${tdCls} text-slate-200 font-medium max-w-[180px]`}>
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
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      <Dialog open={renamingKey !== null} onOpenChange={(open) => { if (!open) closeRename(); }}>
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
    </CollapsibleSection>
  );
}
