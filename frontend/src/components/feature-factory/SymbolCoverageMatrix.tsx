'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  CoverageTaskCreatedPayload,
  CoverageTaskStatusPayload,
  GroupCoverageResponsePayload,
  GroupFeatureCoverageResponsePayload,
  FeatureRegistryEntry,
} from '@/lib/types';
import { httpErrorMessage } from '@/lib/httpError';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BROWSER_API = `${API_BASE_URL}/api/v1/feature-browser`;

/**
 * Coverage 計算為背景任務（ICPERF Task 0.6 (h) ⑦；NOCAP Task 5.3 前端契約）：POST 回 task_id，輪詢狀態至終態
 * （completed／failed／cancelled／interrupted），**不設次數或時間上限**；網路錯誤依退避重試、不丟棄任務；
 * 使用者可取消。下鑽結果以 offset／limit 自同一任務之完整結果分頁讀取（③，每頁筆數 ≥ 1、無上界）。
 */
const POLL_INTERVAL_MS = 1000;
/** 網路錯誤退避：自 1 秒起倍增、單次等待最多 16 秒（只是重試間隔，不放棄任務）。 */
const RETRY_BASE_MS = 1000;
const RETRY_MAX_MS = 16000;
const DEFAULT_PAGE_SIZE = 100;
const TERMINAL_STATES = new Set(['completed', 'failed', 'cancelled', 'interrupted']);

interface SymbolCoverageMatrixProps {
  entries: FeatureRegistryEntry[];
  featureNames?: string[];
}

/** 伺服器回非 2xx（非網路錯誤）：不重試，直接呈現。 */
class CoverageHttpError extends Error {}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new CoverageHttpError(httpErrorMessage(body, response.statusText));
  }
  return (await response.json()) as T;
}

/** 輪詢任務狀態至終態；`isActive()` 為假（元件卸載或已發起新任務）即停止並回 null。 */
async function pollTask(
  taskId: string,
  onStatus: (status: CoverageTaskStatusPayload) => void,
  isActive: () => boolean,
): Promise<CoverageTaskStatusPayload | null> {
  let retryDelay = RETRY_BASE_MS;
  while (isActive()) {
    let status: CoverageTaskStatusPayload;
    try {
      status = await requestJson<CoverageTaskStatusPayload>(`${BROWSER_API}/tasks/${taskId}`);
      retryDelay = RETRY_BASE_MS;
    } catch (pollError) {
      if (pollError instanceof CoverageHttpError) throw pollError;
      await sleep(retryDelay); // 網路錯誤：退避後重試同一任務
      retryDelay = Math.min(retryDelay * 2, RETRY_MAX_MS);
      continue;
    }
    if (!isActive()) return null;
    onStatus(status);
    if (TERMINAL_STATES.has(status.state)) return status;
    await sleep(POLL_INTERVAL_MS);
  }
  return null;
}

function terminalMessage(status: CoverageTaskStatusPayload): string | null {
  if (status.state === 'failed') return `計算失敗：${status.error ?? '未知原因'}`;
  if (status.state === 'interrupted') return `計算中斷：${status.error ?? '服務重啟'}`;
  if (status.state === 'cancelled') return '已取消';
  return null;
}

function TaskProgress({ status }: { status: CoverageTaskStatusPayload | null }) {
  if (!status || TERMINAL_STATES.has(status.state)) return null;
  const { processed, total, updated_at: updatedAt } = status.progress;
  return (
    <span className="text-xs text-slate-400">
      {status.state === 'cancelling' ? '取消中' : '計算中'} {processed} / {total}（更新於 {updatedAt}）
    </span>
  );
}

function pageSizeOf(value: string): number {
  const parsed = Math.floor(Number(value));
  return Number.isFinite(parsed) && parsed >= 1 ? parsed : DEFAULT_PAGE_SIZE;
}

function getCellClassFromCoverage(coverage: number | null): string {
  if (coverage === null || !Number.isFinite(coverage)) {
    return 'bg-slate-500/30';
  }

  if (coverage >= 1.0) return 'bg-emerald-500/80';
  if (coverage >= 0.8) return 'bg-emerald-500/60';
  if (coverage >= 0.5) return 'bg-amber-500/60';
  if (coverage >= 0.3) return 'bg-orange-500/60';
  return 'bg-rose-500/70';
}

export default function SymbolCoverageMatrix({ entries }: SymbolCoverageMatrixProps) {
  const [timeframe, setTimeframe] = useState('');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [pageSizeInput, setPageSizeInput] = useState(String(DEFAULT_PAGE_SIZE));
  const [groupPayload, setGroupPayload] = useState<GroupCoverageResponsePayload | null>(null);
  const [drillPayload, setDrillPayload] = useState<GroupFeatureCoverageResponsePayload | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [drillLoading, setDrillLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drillError, setDrillError] = useState<string | null>(null);
  const [groupStatus, setGroupStatus] = useState<CoverageTaskStatusPayload | null>(null);
  const [drillStatus, setDrillStatus] = useState<CoverageTaskStatusPayload | null>(null);
  const [groupTaskId, setGroupTaskId] = useState<string | null>(null);
  const [drillTaskId, setDrillTaskId] = useState<string | null>(null);

  const mountedRef = useRef(true);
  /** 請求世代：每次發起新計算即遞增，舊世代之晚到回應（task_id、狀態、結果、錯誤）一律丟棄。 */
  const groupRunRef = useRef(0);
  const drillRunRef = useRef(0);
  /** 下鑽讀頁序號：每次讀頁遞增，只採用最新一次讀頁之回應。 */
  const drillPageRef = useRef(0);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const timeframes = useMemo(() => {
    return Array.from(new Set(entries.map((item) => item.timeframe))).sort();
  }, [entries]);

  const symbolsByTimeframe = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const entry of entries) {
      const list = map.get(entry.timeframe) || [];
      if (!list.includes(entry.symbol)) {
        list.push(entry.symbol);
      }
      map.set(entry.timeframe, list);
    }

    for (const [key, list] of map.entries()) {
      map.set(key, list.sort());
    }

    return map;
  }, [entries]);

  const availableSymbols = useMemo(() => {
    return symbolsByTimeframe.get(timeframe) || [];
  }, [symbolsByTimeframe, timeframe]);

  useEffect(() => {
    if (!timeframe && timeframes.length > 0) {
      setTimeframe(timeframes[0]);
    }
  }, [timeframe, timeframes]);

  useEffect(() => {
    if (availableSymbols.length === 0) {
      setSelectedSymbols([]);
      return;
    }

    setSelectedSymbols((prev) => {
      const kept = prev.filter((item) => availableSymbols.includes(item));
      if (kept.length >= 2) {
        return kept;
      }
      return availableSymbols.slice(0, Math.min(3, availableSymbols.length));
    });
  }, [availableSymbols]);

  const toggleSymbol = (symbol: string, checked: boolean) => {
    setSelectedSymbols((prev) => {
      if (checked) {
        return Array.from(new Set([...prev, symbol]));
      }
      return prev.filter((item) => item !== symbol);
    });
  };

  const cancelTask = async (taskId: string | null) => {
    if (!taskId) return;
    try {
      await requestJson(`${BROWSER_API}/tasks/${taskId}/cancel`, { method: 'POST' });
    } catch {
      // 取消請求失敗不改變輪詢：任務終態仍以狀態端點為準
    }
  };

  const runGroupCoverage = async () => {
    if (selectedSymbols.length < 2) {
      setError('請至少選擇 2 個 Symbol');
      return;
    }

    const token = ++groupRunRef.current;
    const isActive = () => mountedRef.current && groupRunRef.current === token;
    drillRunRef.current += 1; // 主表重算 ⇒ 舊下鑽世代失效（其晚到回應不得寫回已清空之區域）
    drillPageRef.current += 1;
    setLoading(true);
    setError(null);
    setGroupStatus(null);
    setDrillPayload(null);
    setSelectedGroup(null);
    setDrillError(null);
    setDrillStatus(null);
    setDrillTaskId(null);
    setDrillLoading(false);

    try {
      const created = await requestJson<CoverageTaskCreatedPayload>(`${BROWSER_API}/group-coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: selectedSymbols, timeframe }),
      });
      if (!isActive()) return;
      setGroupTaskId(created.task_id);
      const final = await pollTask(created.task_id, (status) => setGroupStatus(status), isActive);
      if (!final || !isActive()) return;
      if (final.state === 'completed') {
        const data = await requestJson<GroupCoverageResponsePayload>(`${BROWSER_API}/tasks/${created.task_id}/result`);
        if (isActive()) setGroupPayload(data);
      } else {
        setGroupPayload(null);
        setError(terminalMessage(final));
      }
    } catch (fetchError) {
      if (!isActive()) return;
      setGroupPayload(null);
      setError(fetchError instanceof Error ? fetchError.message : 'Group Coverage 請求失敗');
    } finally {
      if (isActive()) setLoading(false);
    }
  };

  const loadDrillPage = useCallback(async (taskId: string, offset: number, limit: number, isActive: () => boolean) => {
    const page = await requestJson<GroupFeatureCoverageResponsePayload>(
      `${BROWSER_API}/tasks/${taskId}/result?offset=${offset}&limit=${limit}`,
    );
    if (isActive()) setDrillPayload(page);
  }, []);

  const runGroupDrilldown = async (groupName: string) => {
    if (selectedSymbols.length < 2) {
      setDrillError('請至少選擇 2 個 Symbol');
      return;
    }

    const token = ++drillRunRef.current;
    const isActive = () => mountedRef.current && drillRunRef.current === token;
    setSelectedGroup(groupName);
    setDrillLoading(true);
    setDrillError(null);
    setDrillStatus(null);
    setDrillPayload(null);

    try {
      const created = await requestJson<CoverageTaskCreatedPayload>(`${BROWSER_API}/group-feature-coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: selectedSymbols, timeframe, group_name: groupName }),
      });
      if (!isActive()) return; // 已發起新下鑽或主表重算：此晚到之 task_id 不得取代現行任務
      setDrillTaskId(created.task_id);
      const final = await pollTask(created.task_id, (status) => setDrillStatus(status), isActive);
      if (!final || !isActive()) return;
      if (final.state === 'completed') {
        const pageSeq = ++drillPageRef.current;
        await loadDrillPage(created.task_id, 0, pageSizeOf(pageSizeInput),
          () => isActive() && drillPageRef.current === pageSeq);
      } else {
        setDrillError(terminalMessage(final));
      }
    } catch (fetchError) {
      if (!isActive()) return;
      setDrillPayload(null);
      setDrillError(fetchError instanceof Error ? fetchError.message : 'Group 下鑽請求失敗');
    } finally {
      if (isActive()) setDrillLoading(false);
    }
  };

  const goToDrillPage = async (direction: 1 | -1) => {
    if (!drillPayload || !drillTaskId) return;
    const limit = pageSizeOf(pageSizeInput);
    const offset = Math.max(0, drillPayload.offset + direction * limit);
    const token = drillRunRef.current;
    const pageSeq = ++drillPageRef.current;
    const isActive = () => mountedRef.current && drillRunRef.current === token && drillPageRef.current === pageSeq;
    try {
      await loadDrillPage(drillTaskId, offset, limit, isActive);
    } catch (fetchError) {
      if (isActive()) setDrillError(fetchError instanceof Error ? fetchError.message : '讀取下一頁失敗');
    }
  };

  const groupRunning = loading && groupStatus !== null && !TERMINAL_STATES.has(groupStatus.state);
  const drillRunning = drillLoading && drillStatus !== null && !TERMINAL_STATES.has(drillStatus.state);

  if (timeframes.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">
        尚無可用 Symbol Coverage 資料，請先在 Feature Factory 生成至少 2 個 Symbol 的特徵。
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={timeframe}
          onChange={(event) => setTimeframe(event.target.value)}
          className="h-9 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
        >
          {timeframes.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>

        <div className="flex items-center gap-2 text-sm text-slate-300">
          下鑽每頁筆數
          <Input
            type="number"
            min={1}
            value={pageSizeInput}
            onChange={(event) => setPageSizeInput(event.target.value)}
            className="w-24"
          />
        </div>

        <Button onClick={runGroupCoverage} disabled={loading || selectedSymbols.length < 2}>
          {loading ? '計算中...' : '計算 Group Coverage'}
        </Button>

        {groupRunning && (
          <Button variant="outline" onClick={() => cancelTask(groupTaskId)}>
            取消
          </Button>
        )}
        <TaskProgress status={groupStatus} />

        {groupPayload?.summary && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge
              className="border-cyan-400/40 bg-cyan-500/10 text-cyan-200"
              title="所有 group × 所有所選 symbol 的平均覆蓋率（覆蓋率 = 1 − NaN 比率，越高越好）"
            >
              Avg {(groupPayload.summary.avg_coverage * 100).toFixed(2)}%
            </Badge>
            {groupPayload.summary.worst_symbol && (
              <Badge
                className="border-amber-400/40 bg-amber-500/10 text-amber-200"
                title="平均覆蓋率最低的 symbol（跨所有 group 取平均後最差者）"
              >
                Worst Symbol {groupPayload.summary.worst_symbol}
              </Badge>
            )}
            {groupPayload.summary.worst_group && (
              <Badge
                className="border-rose-400/40 bg-rose-500/10 text-rose-200"
                title="跨 symbol 覆蓋率差異（Δ）最大的 group，即各 symbol 最不一致者"
              >
                Worst Group {groupPayload.summary.worst_group}
              </Badge>
            )}
          </div>
        )}
      </div>

      <div className="rounded-md border border-white/10 bg-slate-950/30 px-3 py-2 text-[11px] text-slate-400 leading-relaxed">
        <span className="text-slate-300">名詞定義：</span>
        <span className="ml-1">
          <b className="text-slate-200">覆蓋率</b> = 非 NaN 比率 = 1 − NaN 比率（越高越好）；
          <b className="text-slate-200"> Δ</b> = 跨 symbol 覆蓋率離散度 = 各 symbol 覆蓋率的（最大 − 最小），越大代表該 group/feature 在不同標的越不一致（表格預設按 Δ 由大到小排序）；
          <b className="text-slate-200"> Worst Symbol</b> = 平均覆蓋率最低的標的；
          <b className="text-slate-200"> Worst Group</b> = Δ 最大的 group。
        </span>
      </div>

      <div className="rounded-md border border-white/10 bg-slate-950/40 p-3">
        <div className="text-xs text-slate-400 mb-2">Symbol 選擇（至少 2 個）</div>
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-2">
          {availableSymbols.map((symbol) => (
            <label key={symbol} className="flex items-center gap-2 text-xs text-slate-200">
              <input
                type="checkbox"
                checked={selectedSymbols.includes(symbol)}
                onChange={(event) => toggleSymbol(symbol, event.target.checked)}
              />
              <span>{symbol}</span>
            </label>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          <span>{error}</span>
          {groupStatus?.state === 'interrupted' && (
            <Button variant="outline" onClick={runGroupCoverage} disabled={loading}>
              重送
            </Button>
          )}
        </div>
      )}

      {!groupPayload ? (
        <div className="rounded-md border border-white/10 p-4 text-sm text-slate-400">
          執行計算後顯示 Group × Symbol 覆蓋率熱圖（按跨 symbol 離散度排序）。
        </div>
      ) : groupPayload.groups.length === 0 ? (
        <div className="rounded-md border border-white/10 p-4 text-sm text-slate-400">
          無可用 group，請確認所選 Symbol 已在 Feature Factory 以 V2 路徑生成特徵。
        </div>
      ) : (
        <div className="overflow-auto max-h-[420px] rounded border border-white/10">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-[#0f172a] z-10">
              <tr>
                <th className="px-2 py-2 text-left text-slate-300">Group</th>
                <th
                  className="px-2 py-2 text-left text-slate-300 cursor-help"
                  title="跨 symbol 覆蓋率離散度 = 各 symbol 覆蓋率的（最大 − 最小）。越大＝在不同標的越不一致，越可疑。"
                >
                  Δ
                </th>
                {groupPayload.symbols.map((symbol) => (
                  <th key={symbol} className="px-2 py-2 text-left text-slate-300">{symbol}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groupPayload.groups.map((groupName) => (
                <tr
                  key={groupName}
                  className={`border-t border-white/5 cursor-pointer hover:bg-white/5 ${
                    selectedGroup === groupName ? 'bg-cyan-500/10' : ''
                  }`}
                  onClick={() => runGroupDrilldown(groupName)}
                >
                  <td className="px-2 py-1 text-slate-200 whitespace-nowrap">{groupName}</td>
                  <td className="px-2 py-1 text-slate-400">
                    {((groupPayload.divergence[groupName] ?? 0) * 100).toFixed(1)}%
                  </td>
                  {groupPayload.symbols.map((symbol) => {
                    const coverage = groupPayload.matrix?.[groupName]?.[symbol] ?? null;
                    const coveragePct =
                      coverage === null || !Number.isFinite(coverage)
                        ? '--'
                        : `${(coverage * 100).toFixed(1)}%`;

                    return (
                      <td key={`${groupName}-${symbol}`} className="px-2 py-1">
                        <div
                          className={`rounded px-2 py-1 text-[11px] text-slate-100 ${getCellClassFromCoverage(coverage)}`}
                          title={`Coverage: ${coveragePct}`}
                        >
                          {coveragePct}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {drillError && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          <span>{drillError}</span>
          {drillStatus?.state === 'interrupted' && selectedGroup && (
            <Button variant="outline" onClick={() => runGroupDrilldown(selectedGroup)} disabled={drillLoading}>
              重送下鑽
            </Button>
          )}
        </div>
      )}

      {selectedGroup && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-200">
            <span>
              下鑽 Group: <span className="text-cyan-300">{selectedGroup}</span>
            </span>
            {drillLoading && <span className="text-slate-400">載入中...</span>}
            <TaskProgress status={drillStatus} />
            {drillRunning && (
              <Button variant="outline" onClick={() => cancelTask(drillTaskId)}>
                取消下鑽
              </Button>
            )}
          </div>

          {drillPayload && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
              <span>
                第 {drillPayload.total === 0 ? 0 : drillPayload.offset + 1}–{drillPayload.offset + drillPayload.features.length} 筆，共 {drillPayload.total} 筆
              </span>
              <Button variant="outline" onClick={() => goToDrillPage(-1)} disabled={drillPayload.offset <= 0}>
                上一頁
              </Button>
              <Button
                variant="outline"
                onClick={() => goToDrillPage(1)}
                disabled={drillPayload.offset + drillPayload.features.length >= drillPayload.total}
              >
                下一頁
              </Button>
            </div>
          )}

          {drillPayload && drillPayload.features.length > 0 && (
            <div className="overflow-auto max-h-[360px] rounded border border-white/10">
              <table className="min-w-full text-xs">
                <thead className="sticky top-0 bg-[#0f172a] z-10">
                  <tr>
                    <th className="px-2 py-2 text-left text-slate-300">Feature</th>
                    <th
                  className="px-2 py-2 text-left text-slate-300 cursor-help"
                  title="跨 symbol 覆蓋率離散度 = 各 symbol 覆蓋率的（最大 − 最小）。越大＝在不同標的越不一致，越可疑。"
                >
                  Δ
                </th>
                    {drillPayload.symbols.map((symbol) => (
                      <th key={symbol} className="px-2 py-2 text-left text-slate-300">{symbol}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {drillPayload.features.map((featureName) => (
                    <tr key={featureName} className="border-t border-white/5">
                      <td className="px-2 py-1 text-slate-200 whitespace-nowrap">{featureName}</td>
                      <td className="px-2 py-1 text-slate-400">
                        {((drillPayload.divergence[featureName] ?? 0) * 100).toFixed(1)}%
                      </td>
                      {drillPayload.symbols.map((symbol) => {
                        const coverage = drillPayload.matrix?.[featureName]?.[symbol] ?? null;
                        const validCount = drillPayload.row_counts?.[symbol] ?? 0;
                        const coveragePct =
                          coverage === null || !Number.isFinite(coverage)
                            ? '--'
                            : `${(coverage * 100).toFixed(1)}%`;

                        return (
                          <td key={`${featureName}-${symbol}`} className="px-2 py-1">
                            <div
                              className={`rounded px-2 py-1 text-[11px] text-slate-100 ${getCellClassFromCoverage(coverage)}`}
                              title={`Coverage: ${coveragePct} | Rows: ${validCount}`}
                            >
                              {coveragePct}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
