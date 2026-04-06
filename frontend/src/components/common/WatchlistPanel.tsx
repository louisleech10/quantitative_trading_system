'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Download, FileUp, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { WatchlistStatus } from '@/lib/types';
import { useWatchlistStore } from '@/store/watchlistStore';

interface WatchlistPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type FilterStatus = 'all' | WatchlistStatus;

const STATUS_LABEL: Record<WatchlistStatus, string> = {
  candidate: '候選',
  verified: '已驗證',
  rejected: '淘汰',
  watching: '觀察中',
};

const STATUS_BADGE_CLASS: Record<WatchlistStatus, string> = {
  candidate: 'bg-cyan-500/20 text-cyan-200 border-cyan-400/30',
  verified: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30',
  rejected: 'bg-rose-500/20 text-rose-200 border-rose-400/30',
  watching: 'bg-amber-500/20 text-amber-200 border-amber-400/30',
};

function downloadJson(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function buildFileName(prefix: string): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = `${now.getMonth() + 1}`.padStart(2, '0');
  const d = `${now.getDate()}`.padStart(2, '0');
  return `${prefix}_${y}${m}${d}.json`;
}

export default function WatchlistPanel({ open, onOpenChange }: WatchlistPanelProps) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const {
    entries,
    isSyncing,
    syncError,
    hydrateFromServer,
    removeEntry,
    updateStatus,
    updateNote,
    exportJSON,
    exportVerifiedJSON,
    importJSON,
    clearAll,
  } = useWatchlistStore();

  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [keyword, setKeyword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      void hydrateFromServer();
    }
  }, [open, hydrateFromServer]);

  const filteredEntries = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    return entries.filter((entry) => {
      const statusPass = filterStatus === 'all' || entry.status === filterStatus;
      const textPass = !normalized || entry.feature_name.toLowerCase().includes(normalized);
      return statusPass && textPass;
    });
  }, [entries, filterStatus, keyword]);

  const handleExportAll = () => {
    downloadJson(exportJSON(), buildFileName('watchlist'));
    setInfo('已匯出 Watchlist JSON');
  };

  const handleExportVerified = () => {
    downloadJson(exportVerifiedJSON(), buildFileName('watchlist_verified'));
    setInfo('已匯出已驗證因子 JSON');
  };

  const handleHandoffToML = () => {
    const verifiedEntries = entries.filter((entry) => entry.status === 'verified');
    if (verifiedEntries.length === 0) {
      setError('沒有可帶入 ML 的已驗證因子');
      return;
    }

    setError(null);
    setInfo(`已帶入 ${verifiedEntries.length} 個已驗證因子到 ML 頁面`);
    onOpenChange(false);
    router.push('/patterns/xgboost-analysis?use_watchlist=verified');
  };

  const handleImport = async (file: File | null) => {
    if (!file) {
      return;
    }

    try {
      setError(null);
      setInfo(null);
      const content = await file.text();
      const parsed = JSON.parse(content) as { entries?: unknown[] };
      const importedCount = Array.isArray(parsed.entries) ? parsed.entries.length : 0;
      importJSON(content);

      if (importedCount > 500) {
        setInfo('匯入成功，但已超過容量上限 500，超出部分已截斷');
      } else {
        setInfo(`匯入成功，共處理 ${importedCount} 筆 entries`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '匯入失敗';
      setError(message);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Factor Watchlist</SheetTitle>
          <SheetDescription>
            本地快取 + 後端持久化（data_cache/watchlists），可一鍵帶入 ML 訓練。
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          <div className="flex items-center justify-between rounded-md border border-white/10 px-3 py-2 text-xs text-slate-300">
            <span>{isSyncing ? '同步中...' : '同步狀態正常'}</span>
            <span>共 {entries.length} 筆</span>
          </div>

          {syncError && (
            <div className="rounded-md border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              後端同步警告：{syncError}
            </div>
          )}

          <Input
            placeholder="搜尋 feature_name"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />

          <Tabs value={filterStatus} onValueChange={(value) => setFilterStatus(value as FilterStatus)}>
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="all">全部</TabsTrigger>
              <TabsTrigger value="candidate">候選</TabsTrigger>
              <TabsTrigger value="verified">已驗證</TabsTrigger>
              <TabsTrigger value="rejected">淘汰</TabsTrigger>
              <TabsTrigger value="watching">觀察中</TabsTrigger>
            </TabsList>
          </Tabs>

          {error && (
            <div className="rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          )}

          {info && (
            <div className="rounded-md border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
              {info}
            </div>
          )}

          <div className="space-y-2">
            {filteredEntries.length === 0 ? (
              <div className="rounded-md border border-white/10 p-4 text-sm text-slate-400">
                目前沒有符合條件的 Watchlist 因子。
              </div>
            ) : (
              filteredEntries.map((entry) => (
                <div key={entry.feature_name} className="rounded-md border border-white/10 bg-white/5 p-3 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-slate-100 break-all">{entry.feature_name}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        IC: {typeof entry.ic_snapshot === 'number' ? entry.ic_snapshot.toFixed(4) : '--'} | ICIR: {typeof entry.icir_snapshot === 'number' ? entry.icir_snapshot.toFixed(3) : '--'}
                      </div>
                    </div>
                    <Badge className={STATUS_BADGE_CLASS[entry.status]}>{STATUS_LABEL[entry.status]}</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-[160px_1fr_auto] gap-2">
                    <select
                      value={entry.status}
                      onChange={(event) => updateStatus(entry.feature_name, event.target.value as WatchlistStatus)}
                      className="h-9 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
                    >
                      <option value="candidate">候選</option>
                      <option value="verified">已驗證</option>
                      <option value="rejected">淘汰</option>
                      <option value="watching">觀察中</option>
                    </select>

                    <Input
                      placeholder="備註"
                      value={entry.note}
                      onChange={(event) => updateNote(entry.feature_name, event.target.value)}
                    />

                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => removeEntry(entry.feature_name)}
                      className="whitespace-nowrap"
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      刪除
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
            <Button type="button" variant="outline" onClick={handleExportAll}>
              <Download className="h-4 w-4 mr-1" />
              匯出 JSON
            </Button>
            <Button type="button" variant="outline" onClick={handleExportVerified}>
              <Download className="h-4 w-4 mr-1" />
              匯出已驗證
            </Button>
            <Button type="button" variant="outline" onClick={handleHandoffToML}>
              一鍵帶入 ML
            </Button>
            <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
              <FileUp className="h-4 w-4 mr-1" />
              匯入 JSON
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                clearAll();
                setInfo('已清空 Watchlist');
              }}
            >
              清空
            </Button>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0] || null;
                void handleImport(file);
                event.currentTarget.value = '';
              }}
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
