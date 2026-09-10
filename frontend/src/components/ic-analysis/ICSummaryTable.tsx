'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Star } from 'lucide-react';
import { ICAnalysisConfig, ICFeatureInfo, ICSummaryPage, SummaryPageParams, WatchlistStatus } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ArrowUpDown } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { useWatchlistStore } from '@/store/watchlistStore';
import {
  BINARY_COLUMN_ORDER,
  binaryColumnLabels,
  binaryColumnTooltips,
} from '@/lib/icLabelRule';

interface ICSummaryTableProps {
  /** legacy：直接給列（不分頁、不本地排序——後端序即顯示序）。 */
  data?: ICFeatureInfo[];
  /** ICRESULT_PAGING Task 2.2：伺服器分頁模式（優先於 data）。 */
  page?: ICSummaryPage | null;
  params?: SummaryPageParams;
  onParamsChange?: (patch: Partial<SummaryPageParams>) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  selectedFeature?: string | null;
  onSelectFeature?: (featureName: string) => void;
  selectable?: boolean;
  selectedFeatures?: string[];
  onSelectFeatures?: (featureNames: string[]) => void;
  analysisMode?: ICAnalysisConfig['mode'];
  crossSectionalSampleSize?: number;
  crossSectionalSymbolCount?: number;
  taskId?: string | null;
}

type SortField =
  | 'rank'
  | 'ic_mean'
  | 'icir'
  | 'ic_hit_rate'
  | 't_stat'
  | 'p_value'
  | 'p_value_adj'
  | 'monotonicity_score';

// EVTLABEL Task 3.9：表頭文案單點自 `icLabelRule`（禁在此再寫一份，兩份會分歧）。
const BINARY_LABELS = binaryColumnLabels();
const BINARY_TOOLTIPS = binaryColumnTooltips();

/** binary 欄之顯示：計數用整數、狀態用原字串、其餘用固定小數；非有限值 ⇒ `—`（不補 0）。 */
function formatBinaryCell(key: string, value: unknown): string {
  if (key === 'binary_status') return typeof value === 'string' ? value : '—';
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  if (key.startsWith('n_')) return String(value);
  if (key === 'mw_u') return value.toFixed(0);
  return value.toFixed(4);
}

const AUTO_SUGGEST_LIMIT = 12;
const PAGE_SIZES = [50, 100, 200] as const;
const SEARCH_DEBOUNCE_MS = 300; // SPEC §C-10：搜尋去抖 owner＝表格搜尋框（hook 不再去抖）

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

/** 共用 finite formatter：非有限 → '--'（CODEX-6；禁前端統計推導） */
function formatFinite(value: unknown, digits: number): string {
  if (isFiniteNumber(value)) {
    return value.toFixed(digits);
  }
  return '--';
}

export default function ICSummaryTable({
  data,
  page = null,
  params,
  onParamsChange,
  loading = false,
  error = null,
  onRetry,
  selectedFeature,
  onSelectFeature,
  selectable = false,
  selectedFeatures = [],
  onSelectFeatures,
  analysisMode = 'global',
  crossSectionalSampleSize = 0,
  crossSectionalSymbolCount = 0,
  taskId = null,
}: ICSummaryTableProps) {
  const serverMode = page !== null && page !== undefined;
  // EVTLABEL Task 3.9：由**資料本身**判是不是匯入標籤模式（第一列有無主統計欄），
  // 不另外拉一個 prop——多一個真相源就會有兩者不一致的一天。
  const firstRow = (page?.rows ?? data ?? [])[0];
  const isBinaryMode = firstRow?.rank_biserial !== undefined;
  const sortField = (params?.sort_by ?? page?.sort_by ?? 'icir') as SortField;
  const sortDirection = params?.sort_order ?? page?.sort_order ?? 'desc';
  // 翻頁時保留舊列到新列到達（不閃白）；skeleton 以 overlay 呈現
  const lastRowsRef = useRef<ICFeatureInfo[]>([]);
  const [searchText, setSearchText] = useState(params?.search ?? '');
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [watchlistFeature, setWatchlistFeature] = useState<ICFeatureInfo | null>(null);
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>('candidate');
  const [watchlistNote, setWatchlistNote] = useState('');
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistInfo, setWatchlistInfo] = useState<string | null>(null);

  const watchlistEntries = useWatchlistStore((state) => state.entries);
  const addWatchlistEntry = useWatchlistStore((state) => state.addEntry);

  const isCrossSectional = analysisMode === 'cross_sectional';

  const watchlistMap = useMemo(
    () => new Map(watchlistEntries.map((entry) => [entry.feature_name, entry])),
    [watchlistEntries]
  );

  // ICRESULT_PAGING §C-8：排序一律在後端（分頁序取代前端本地序）；legacy data 模式亦不本地排序
  const sortedData = useMemo<ICFeatureInfo[]>(() => {
    if (serverMode) {
      const rows = page?.rows ?? [];
      if (rows.length > 0 || !loading) lastRowsRef.current = rows;
      return loading && rows.length === 0 ? lastRowsRef.current : rows;
    }
    return data ?? [];
  }, [data, loading, page, serverMode]);
  const selectedSet = useMemo(() => new Set(selectedFeatures), [selectedFeatures]);
  const total = serverMode ? (page?.total ?? 0) : sortedData.length;
  const offset = serverMode ? (page?.offset ?? 0) : 0;
  const limit = serverMode ? (params?.limit ?? page?.limit ?? 50) : sortedData.length;

  const handleSort = (field: SortField) => {
    if (!onParamsChange) return;
    const nextOrder = sortField === field ? (sortDirection === 'asc' ? 'desc' : 'asc') : 'desc';
    onParamsChange({ sort_by: field, sort_order: nextOrder, offset: 0 });
  };

  useEffect(() => () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current); }, []);
  // URL 還原／外部改 params.search ⇒ 同步搜尋框（B2 review COMPOSER-R1-P2-01）
  useEffect(() => { setSearchText(params?.search ?? ''); }, [params?.search]);
  const handleSearchChange = (value: string) => {
    setSearchText(value);
    if (!onParamsChange) return;
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      onParamsChange({ search: value.trim(), offset: 0 });
    }, SEARCH_DEBOUNCE_MS);
  };

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleSort(field)}
      disabled={!onParamsChange}
      data-sort-field={field}
      className="h-8 px-2 text-xs"
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );

  const allSelected = sortedData.length > 0 && sortedData.every((item) => selectedSet.has(item.feature_name));

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectFeatures) return;
    if (!checked) {
      // 取消全選＝只移除當頁（B2 review CODEX-R1-P1-02）；其他頁已勾者保留
      const next = new Set(selectedSet);
      for (const item of sortedData) next.delete(item.feature_name);
      onSelectFeatures(Array.from(next));
      return;
    }
    // 全選＝當頁；保留其他頁已勾者（Set 跨頁保留）
    const next = new Set(selectedSet);
    for (const item of sortedData) next.add(item.feature_name);
    onSelectFeatures(Array.from(next));
  };

  const toggleFeature = (featureName: string, checked: boolean) => {
    if (!onSelectFeatures) return;
    const next = new Set(selectedSet);
    if (checked) next.add(featureName); else next.delete(featureName);
    onSelectFeatures(Array.from(next));
  };

  const openWatchlistDialog = (item: ICFeatureInfo) => {
    const existing = watchlistMap.get(item.feature_name);
    setWatchlistFeature(item);
    setWatchlistStatus(existing?.status || 'candidate');
    setWatchlistNote(existing?.note || '');
    setWatchlistError(null);
  };

  const saveWatchlist = () => {
    if (!watchlistFeature) {
      return;
    }

    try {
      addWatchlistEntry({
        feature_name: watchlistFeature.feature_name,
        task_id: taskId || 'ic-analysis',
        status: watchlistStatus,
        note: watchlistNote,
        ic_snapshot: Number.isFinite(watchlistFeature.ic_mean) ? watchlistFeature.ic_mean : null,
        icir_snapshot: Number.isFinite(watchlistFeature.icir) ? watchlistFeature.icir : null,
        turnover_snapshot: Number.isFinite(watchlistFeature.turnover_rate)
          ? watchlistFeature.turnover_rate
          : null,
        added_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setWatchlistFeature(null);
      setWatchlistError(null);
      setWatchlistInfo(`已更新 ${watchlistFeature.feature_name}`);
    } catch (error) {
      setWatchlistError(error instanceof Error ? error.message : '加入 Watchlist 失敗');
    }
  };

  const markSelectedAsVerified = () => {
    if (selectedFeatures.length === 0) {
      setWatchlistError('請先勾選至少 1 個因子');
      return;
    }

    let updatedCount = 0;
    const skipped: string[] = [];
    for (const featureName of selectedFeatures) {
      const item = sortedData.find((row) => row.feature_name === featureName);
      if (!item) {
        skipped.push(featureName); // 不在當頁 ⇒ 無 row 資料可回寫（B2 review CODEX-R1-P2-06：明示僅當頁）
        continue;
      }

      const existing = watchlistMap.get(featureName);
      addWatchlistEntry({
        feature_name: featureName,
        task_id: taskId || 'ic-analysis',
        status: 'verified',
        note: existing?.note || '',
        ic_snapshot: Number.isFinite(item.ic_mean) ? item.ic_mean : null,
        icir_snapshot: Number.isFinite(item.icir) ? item.icir : null,
        turnover_snapshot: Number.isFinite(item.turnover_rate) ? item.turnover_rate : null,
        added_at: existing?.added_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      updatedCount += 1;
    }

    if (updatedCount === 0) {
      setWatchlistError('未找到可更新的因子');
      return;
    }
    setWatchlistError(null);
    setWatchlistInfo(
      skipped.length > 0
        ? `已將 ${updatedCount} 個因子標記為已驗證；${skipped.length} 個不在當頁未處理（批次操作僅作用於當頁）`
        : `已將 ${updatedCount} 個因子標記為已驗證`
    );
  };

  const autoSuggestToWatchlist = () => {
    const scored = sortedData
      .map((item) => {
        if (!isFiniteNumber(item.ic_mean) || !isFiniteNumber(item.icir)) {
          return null;
        }

        const turnover = isFiniteNumber(item.turnover_rate) ? Math.max(0, item.turnover_rate) : 0;
        const score = Math.abs(item.ic_mean) * 100 + item.icir * 10 - turnover * 5;
        return { item, score };
      })
      .filter((row): row is { item: ICFeatureInfo; score: number } => row !== null)
      .sort((left, right) => right.score - left.score)
      .slice(0, AUTO_SUGGEST_LIMIT);

    if (scored.length === 0) {
      setWatchlistError('目前沒有符合 Auto-Suggest 條件的因子');
      return;
    }

    let updatedCount = 0;
    for (const { item, score } of scored) {
      const existing = watchlistMap.get(item.feature_name);
      if (existing?.status === 'verified' || existing?.status === 'rejected') {
        continue;
      }

      addWatchlistEntry({
        feature_name: item.feature_name,
        task_id: taskId || 'ic-analysis',
        status: existing?.status || 'candidate',
        note: existing?.note || `auto_suggest(score=${score.toFixed(2)})`,
        ic_snapshot: isFiniteNumber(item.ic_mean) ? item.ic_mean : null,
        icir_snapshot: isFiniteNumber(item.icir) ? item.icir : null,
        turnover_snapshot: isFiniteNumber(item.turnover_rate) ? item.turnover_rate : null,
        added_at: existing?.added_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      updatedCount += 1;
    }

    if (updatedCount === 0) {
      setWatchlistError('Auto-Suggest 沒有產生可更新項目（可能皆為已驗證/淘汰）');
      return;
    }

    setWatchlistError(null);
    setWatchlistInfo(serverMode ? `Auto-Suggest 已更新 ${updatedCount} 個候選因子（僅評分當頁 ${sortedData.length} 列）` : `Auto-Suggest 已更新 ${updatedCount} 個候選因子`);
  };

  // silence unused prop lint (仍由 caller 傳入以保持 API 相容)
  void crossSectionalSampleSize;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">IC 排名總覽</CardTitle>
        <CardDescription>點擊特徵即可更新右側圖表</CardDescription>
        {watchlistError && <div className="text-xs text-rose-300">{watchlistError}</div>}
        {watchlistInfo && <div className="text-xs text-emerald-300">{watchlistInfo}</div>}
        {isCrossSectional && crossSectionalSymbolCount > 0 && crossSectionalSymbolCount < 5 && (
          <div className="text-xs text-amber-300">樣本量不足（Symbol &lt; 5），解讀需謹慎</div>
        )}
        {selectable && (
          <div className="pt-1">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={markSelectedAsVerified} disabled={selectedFeatures.length === 0}>
                將已勾選因子標記為已驗證
              </Button>
              <Button variant="outline" size="sm" onClick={autoSuggestToWatchlist}>
                Auto-Suggest 推薦
              </Button>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Deep Analysis 完成後，可用此按鈕批次回寫 Watchlist 狀態。
            </p>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {serverMode && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Input
              value={searchText}
              onChange={(event) => handleSearchChange(event.target.value)}
              placeholder="搜尋特徵名（300 ms 去抖）"
              className="h-8 w-64 text-xs"
              data-testid="ic-summary-search"
            />
            <span className="text-xs text-slate-400" data-testid="ic-summary-range">
              {total === 0 ? '共 0 列' : `第 ${offset + 1}–${Math.min(offset + limit, total)} 列，共 ${total} 列`}
              {selectedFeatures.length > 0 ? `；已選 ${selectedFeatures.length}` : ''}
            </span>
            {error && (
              <span className="text-xs text-rose-300" data-testid="ic-summary-error">
                {error}{' '}
                {onRetry && (
                  <Button variant="outline" size="sm" className="h-6 px-2 text-[11px]" onClick={onRetry} data-testid="ic-summary-retry">
                    重試
                  </Button>
                )}
              </span>
            )}
          </div>
        )}
        {sortedData.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-[200px] text-slate-400">
            {serverMode && (params?.search || '').length > 0 ? '沒有符合搜尋的特徵' : '暫無分析結果'}
          </div>
        ) : (
          <div className="relative rounded-md border border-white/10">
            {loading && (
              <div
                className="absolute inset-0 z-10 flex items-start justify-center bg-slate-950/40 pt-3 text-xs text-slate-300"
                data-testid="ic-summary-skeleton"
                aria-busy="true"
              >
                載入中…
              </div>
            )}
            <Table>
              <TableHeader>
                <TableRow>
                  {selectable && (
                    <TableHead className="w-[42px]">
                      <Checkbox checked={allSelected} onCheckedChange={(checked) => handleSelectAll(Boolean(checked))} />
                    </TableHead>
                  )}
                  <TableHead className="w-[70px]">排名</TableHead>
                  <TableHead>特徵</TableHead>
                  {/* EVTLABEL Task 3.9：匯入標籤模式 ⇒ 主統計欄排在報酬版**之前**。
                      表頭一律統計學標準名（使用者 2026-09-10），文案單點自 icLabelRule。 */}
                  {isBinaryMode &&
                    BINARY_COLUMN_ORDER.map((key) => (
                      <TableHead
                        key={key}
                        className="w-[110px]"
                        title={BINARY_TOOLTIPS[key]}
                        data-testid={`ic-summary-binary-${key}`}
                      >
                        {BINARY_LABELS[key]}
                      </TableHead>
                    ))}
                  <TableHead className="w-[120px]" title="描述性 rolling 均值,非檢定量">
                    <SortButton field="ic_mean" label="IC Mean" />
                  </TableHead>
                  <TableHead className="w-[120px]">
                    <SortButton field="icir" label="ICIR" />
                  </TableHead>
                  {isCrossSectional ? (
                    <>
                      <TableHead className="w-[140px]">
                        <SortButton field="ic_hit_rate" label="Positive Rate" />
                      </TableHead>
                      <TableHead className="w-[120px]">
                        <SortButton field="t_stat" label="t-stat" />
                      </TableHead>
                      <TableHead className="w-[120px]">
                        <SortButton field="p_value" label="P-Value" />
                      </TableHead>
                      <TableHead className="w-[180px]">CI 95%</TableHead>
                      <TableHead className="w-[120px]">
                        <SortButton field="p_value_adj" label="q" />
                      </TableHead>
                    </>
                  ) : (
                    <>
                      <TableHead className="w-[120px]">
                        <SortButton field="t_stat" label="t-stat" />
                      </TableHead>
                      <TableHead className="w-[120px]">
                        <SortButton field="p_value" label="P-Value" />
                      </TableHead>
                      <TableHead className="w-[120px]">
                        <SortButton field="p_value_adj" label="q" />
                      </TableHead>
                      <TableHead className="w-[140px]">
                        <SortButton field="monotonicity_score" label="單調性" />
                      </TableHead>
                    </>
                  )}
                  <TableHead className="w-[96px]">Watchlist</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((item, index) => {
                  const isSelected = item.feature_name === selectedFeature;
                  return (
                    <TableRow
                      key={`${item.feature_name}-${index}`}
                      className={isSelected ? 'bg-cyan-500/10' : ''}
                      onClick={() => onSelectFeature?.(item.feature_name)}
                    >
                      {selectable && (
                        <TableCell onClick={(event) => event.stopPropagation()}>
                          <Checkbox
                            checked={selectedSet.has(item.feature_name)}
                            onCheckedChange={(checked) => toggleFeature(item.feature_name, Boolean(checked))}
                          />
                        </TableCell>
                      )}
                      <TableCell className="text-sm text-slate-300">#{item.rank ?? offset + index + 1}</TableCell>
                      <TableCell className="font-medium text-slate-100">
                        {item.feature_name}
                      </TableCell>
                      {isBinaryMode &&
                        BINARY_COLUMN_ORDER.map((key) => (
                          <TableCell
                            key={key}
                            className="font-mono text-xs text-sky-200"
                            data-testid={`ic-summary-binary-cell-${key}`}
                          >
                            {formatBinaryCell(key, item[key as keyof ICFeatureInfo])}
                          </TableCell>
                        ))}
                      <TableCell
                        className="font-mono text-xs text-slate-200"
                        title="描述性 rolling 均值,非檢定量"
                      >
                        {formatFinite(item.ic_mean, 4)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-emerald-300">
                        {formatFinite(item.icir, 3)}
                      </TableCell>
                      {isCrossSectional ? (
                        <>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {isFiniteNumber(item.ic_hit_rate)
                              ? `${(item.ic_hit_rate * 100).toFixed(1)}%`
                              : '--'}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.t_stat, 3)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.p_value, 4)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {/* 無後端 CI 欄 → 誠實 '--'；禁前端 SE 推導 */}
                            {'--'}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.p_value_adj, 4)}
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.t_stat, 3)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.p_value, 4)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.p_value_adj, 4)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {formatFinite(item.monotonicity_score, 2)}
                          </TableCell>
                        </>
                      )}
                      <TableCell onClick={(event) => event.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => openWatchlistDialog(item)}
                          className="inline-flex items-center rounded border border-amber-400/40 px-2 py-1 text-amber-200 hover:bg-amber-400/10"
                        >
                          <Star className={`h-3.5 w-3.5 ${watchlistMap.has(item.feature_name) ? 'fill-amber-300' : ''}`} />
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
        {serverMode && total > 0 && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300" data-testid="ic-summary-pager">
            <div className="flex items-center gap-2">
              <span>每頁</span>
              {PAGE_SIZES.map((size) => (
                <Button
                  key={size}
                  variant={limit === size ? 'default' : 'outline'}
                  size="sm"
                  className="h-7 px-2 text-[11px]"
                  onClick={() => onParamsChange?.({ limit: size, offset: 0 })}
                  disabled={!onParamsChange}
                >
                  {size}
                </Button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-7 px-2 text-[11px]"
                onClick={() => onParamsChange?.({ offset: Math.max(0, offset - limit) })}
                disabled={!onParamsChange || offset === 0}
                data-testid="ic-summary-prev"
              >
                上一頁
              </Button>
              <span data-testid="ic-summary-pageno">第 {Math.floor(offset / limit) + 1} / {Math.max(1, Math.ceil(total / limit))} 頁</span>
              <Button
                variant="outline"
                size="sm"
                className="h-7 px-2 text-[11px]"
                onClick={() => onParamsChange?.({ offset: offset + limit })}
                disabled={!onParamsChange || offset + limit >= total}
                data-testid="ic-summary-next"
              >
                下一頁
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      <Dialog open={Boolean(watchlistFeature)} onOpenChange={(open) => !open && setWatchlistFeature(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>加入 Watchlist</DialogTitle>
            <DialogDescription>{watchlistFeature?.feature_name || '--'}</DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <select
              value={watchlistStatus}
              onChange={(event) => setWatchlistStatus(event.target.value as WatchlistStatus)}
              className="h-9 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
            >
              <option value="candidate">候選</option>
              <option value="verified">已驗證</option>
              <option value="rejected">淘汰</option>
              <option value="watching">觀察中</option>
            </select>

            <Input
              value={watchlistNote}
              onChange={(event) => setWatchlistNote(event.target.value)}
              placeholder="備註"
            />

            {watchlistFeature && (
              <div className="text-xs text-slate-400">
                IC: {formatFinite(watchlistFeature.ic_mean, 4)} | ICIR: {formatFinite(watchlistFeature.icir, 3)}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setWatchlistFeature(null)}>取消</Button>
            <Button onClick={saveWatchlist}>儲存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
