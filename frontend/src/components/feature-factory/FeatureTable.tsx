'use client';

import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BrowseFeatureItem } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';
import type { FeatureSummary } from '@/lib/types';

/** stats 暖機進度提示（獨立元件便於 unit test） */
export function StatsWarmupBanner({
  statsWarmup,
}: {
  statsWarmup?: FeatureSummary['stats_warmup'];
}) {
  if (!statsWarmup || statsWarmup.complete) return null;
  return (
    <div className="text-xs text-amber-200/90 border border-amber-300/30 bg-amber-400/10 rounded-lg px-3 py-2">
      暖機 {statsWarmup.pct.toFixed(0)}%，排序暫定
      {statsWarmup.total > 0 && (
        <span className="text-amber-200/70">
          {' '}
          （{statsWarmup.computed.toLocaleString()} / {statsWarmup.total.toLocaleString()} 特徵統計已就緒）
        </span>
      )}
    </div>
  );
}

interface FeatureTableProps {
  taskId: string;
  totalCount?: number;
  onOpenDistribution: (feature: string) => void;
  onOpenCorrelation: (features: string[]) => void;
}

const levelTabs: Array<'All' | 'L1' | 'L2' | 'L3'> = ['All', 'L1', 'L2', 'L3'];
const PAGE_SIZE = 100;
const INITIAL_LOAD_LIMIT = 500;
const BACKGROUND_PAGE_LIMIT = 5000;
// Hard cap on how many feature rows we materialize on the client. For very
// wide CGSA tasks (200k+ columns) loading everything would explode browser
// memory AND blow past the API rate limit. Above this cap we show a notice
// telling users to use the search/filter to narrow the view.
const MAX_CLIENT_ROWS = 20000;
const TABLE_VIEWPORT_HEIGHT = 520;
const TABLE_ROW_HEIGHT = 34;
const VIRTUAL_OVERSCAN = 12;

export default function FeatureTable({ taskId, totalCount, onOpenDistribution, onOpenCorrelation }: FeatureTableProps) {
  const { browseFeatures, browseSummary } = useFeatureFactory();
  const sharedFeatureNames = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask[taskId]);
  const statsWarmup = useFeatureFactoryStore(
    (state) => state.explorerSummaryByTask[taskId]?.stats_warmup,
  );
  const setExplorerSummaryForTask = useFeatureFactoryStore((state) => state.setExplorerSummaryForTask);

  // All features loaded once from the server (up to 5000)
  const [allRows, setAllRows] = useState<BrowseFeatureItem[]>([]);
  const [serverTotal, setServerTotal] = useState(0);
  const [loadedCount, setLoadedCount] = useState(0);
  const loadedTaskRef = useRef<string | null>(null);

  // Client-side filter/sort state — no re-fetch needed
  const [category, setCategory] = useState('');
  const [level, setLevel] = useState<'All' | 'L1' | 'L2' | 'L3'>('All');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [segmentFilteredNames, setSegmentFilteredNames] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [isBackgroundLoading, setIsBackgroundLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [isSegmentFilterOpen, setIsSegmentFilterOpen] = useState(false);
  const [tableScrollTop, setTableScrollTop] = useState(0);
  const tableContainerRef = useRef<HTMLDivElement | null>(null);

  // Server-side search results — used when the search box is non-empty so
  // features beyond the MAX_CLIENT_ROWS client cache are still searchable.
  const [serverSearchRows, setServerSearchRows] = useState<BrowseFeatureItem[]>([]);
  const [isServerSearching, setIsServerSearching] = useState(false);

  // Server-sort mode — activated when sort != name:asc.
  // The server sorts ALL rows; we just page through the results.
  const isServerSortMode = sortBy !== 'name' || sortOrder !== 'asc';
  const [serverSortRows, setServerSortRows] = useState<BrowseFeatureItem[]>([]);
  const [serverSortTotal, setServerSortTotal] = useState(0);
  const [serverSortLoading, setServerSortLoading] = useState(false);
  const serverSortAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setVisibleCount(PAGE_SIZE);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // stats 暖機未完成時輪詢 summary 以更新進度條
  useEffect(() => {
    if (!taskId || !statsWarmup || statsWarmup.complete) return;
    const interval = setInterval(() => {
      browseSummary(taskId)
        .then((payload) => setExplorerSummaryForTask(taskId, payload))
        .catch(() => undefined);
    }, 5000);
    return () => clearInterval(interval);
  }, [taskId, statsWarmup, browseSummary, setExplorerSummaryForTask]);

  // When sort is non-default, ask the server to sort ALL rows and return first page.
  // category/level are forwarded so the result is accurate even with filters.
  useEffect(() => {
    if (!isServerSortMode) {
      setServerSortRows([]);
      setServerSortTotal(0);
      return;
    }
    serverSortAbortRef.current?.abort();
    const ctrl = new AbortController();
    serverSortAbortRef.current = ctrl;
    setServerSortLoading(true);
    setServerSortRows([]);
    setVisibleCount(PAGE_SIZE);
    browseFeatures(taskId, {
      offset: 0,
      limit: 500,
      sortBy,
      sortOrder,
      category: category || undefined,
      level: level !== 'All' ? level : undefined,
      detailLevel: 'table',
    })
      .then((resp) => {
        if (ctrl.signal.aborted) return;
        setServerSortRows(resp.features);
        setServerSortTotal(resp.total);
      })
      .catch(() => { /* aborted or error — ignore */ })
      .finally(() => { if (!ctrl.signal.aborted) setServerSortLoading(false); });
    return () => ctrl.abort();
  }, [isServerSortMode, taskId, sortBy, sortOrder, category, level, browseFeatures]);

  // Load all features in chunks once per taskId
  useEffect(() => {
    if (loadedTaskRef.current === taskId) return;
    loadedTaskRef.current = taskId;

    let active = true;
    setLoading(true);
    setError(null);
    setAllRows([]);
    setLoadedCount(0);
    setServerTotal(0);
    setSelected([]);
    setSegmentFilteredNames([]);
    setIsBackgroundLoading(false);
    setIsSegmentFilterOpen(false);

    const loadAllFeatures = async () => {
      try {
        let total = 0;
        const merged: BrowseFeatureItem[] = [];

        // First request uses a smaller payload for faster first paint.
        const firstResp = await browseFeatures(taskId, {
          offset: 0,
          limit: INITIAL_LOAD_LIMIT,
          sortBy: 'name',
          sortOrder: 'asc',
          detailLevel: 'table',
        });
        if (!active) return;

        total = firstResp.total;
        setServerTotal(total);

        if (firstResp.features.length > 0) {
          merged.push(...firstResp.features);
          setAllRows([...merged]);
          setLoadedCount(merged.length);
        }

        // Allow users to interact with the first page immediately.
        setLoading(false);

        if (merged.length >= total || firstResp.features.length === 0) {
          return;
        }

        setIsBackgroundLoading(true);

        let cursor = firstResp.next_cursor ?? null;
        while (active && cursor && merged.length < MAX_CLIENT_ROWS) {
          const remaining = MAX_CLIENT_ROWS - merged.length;
          const resp = await browseFeatures(taskId, {
            cursor,
            limit: Math.min(BACKGROUND_PAGE_LIMIT, remaining),
            sortBy: 'name',
            sortOrder: 'asc',
            detailLevel: 'table',
          });

          if (!active) return;
          if (resp.features.length === 0) break;

          merged.push(...resp.features);
          setAllRows([...merged]);
          setLoadedCount(Math.min(merged.length, total));
          cursor = resp.next_cursor ?? null;
        }

        setLoadedCount(Math.min(merged.length, total));
        setIsBackgroundLoading(false);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入特徵列表失敗');
      } finally {
        if (!active) return;
        setLoading(false);
        setIsBackgroundLoading(false);
      }
    };

    void loadAllFeatures();

    return () => {
      active = false;
      // Reset ref so React StrictMode remount (or future taskId changes) triggers a fresh fetch.
      // Without this, the 2nd StrictMode mount returns early via the ref-guard, leaving
      // loading=true permanently (the first fetch's finally skips setLoading because active=false).
      loadedTaskRef.current = null;
    };
  }, [browseFeatures, taskId]);

  // When the debounced search term is non-empty, fetch from the server so
  // features beyond MAX_CLIENT_ROWS are reachable (server searches all rows).
  useEffect(() => {
    if (!search) {
      setServerSearchRows([]);
      return;
    }
    let active = true;
    setIsServerSearching(true);
    browseFeatures(taskId, {
      search,
      limit: 5000,
      sortBy,
      sortOrder,
      detailLevel: 'table',
    })
      .then((resp) => {
        if (!active) return;
        setServerSearchRows(resp.features);
      })
      .catch(() => {
        if (!active) return;
        setServerSearchRows([]);
      })
      .finally(() => {
        if (!active) return;
        setIsServerSearching(false);
      });
    return () => {
      active = false;
    };
  }, [search, taskId, browseFeatures]);

  const loadMoreServerSort = useCallback(() => {
    if (serverSortLoading) return;
    setServerSortLoading(true);
    browseFeatures(taskId, {
      offset: serverSortRows.length,
      limit: 500,
      sortBy,
      sortOrder,
      category: category || undefined,
      level: level !== 'All' ? level : undefined,
      detailLevel: 'table',
    })
      .then((resp) => {
        setServerSortRows((prev) => [...prev, ...resp.features]);
        setServerSortTotal(resp.total);
      })
      .catch(() => {})
      .finally(() => setServerSortLoading(false));
  }, [serverSortLoading, serverSortRows.length, taskId, sortBy, sortOrder, category, level, browseFeatures]);

  const featureNames = useMemo(
    () => (sharedFeatureNames && sharedFeatureNames.length > 0 ? sharedFeatureNames : allRows.map((row) => row.name)),
    [allRows, sharedFeatureNames]
  );

  // Client-side filter + sort (instant, no network).
  // When search is active we use the server-returned results (all 437k reachable).
  // When sort is non-default we use server-sort results (sorted across all 437k).
  // Otherwise we operate on the locally cached allRows (up to MAX_CLIENT_ROWS).
  const filteredRows = useMemo(() => {
    let result: BrowseFeatureItem[];
    if (search) {
      result = serverSearchRows; // server already applied search + sort
    } else if (isServerSortMode) {
      result = serverSortRows;   // server already applied sort + category/level
    } else {
      result = allRows;
    }

    // Segment filter is always client-side (too granular for server)
    if (isSegmentFilterOpen && segmentFilteredNames.length > 0) {
      const allowed = new Set(segmentFilteredNames);
      result = result.filter((r) => allowed.has(r.name));
    }

    // category/level only need client-side filtering in client-cache mode;
    // server-sort/server-search modes already have them applied server-side.
    if (!isServerSortMode && !search) {
      if (category) {
        const lower = category.toLowerCase();
        result = result.filter((r) => r.category?.toLowerCase().includes(lower));
      }
      if (level !== 'All') {
        result = result.filter((r) => r.level === level);
      }
    }

    // Sort only needed in client-cache mode; server modes return pre-sorted data.
    if (!isServerSortMode && !search) {
      return [...result].sort((a, b) => {
        const mul = sortOrder === 'asc' ? 1 : -1;
        if (sortBy === 'name') return mul * a.name.localeCompare(b.name);
        return mul * (getSortableMetric(a, sortBy) - getSortableMetric(b, sortBy));
      });
    }
    return result;
  }, [allRows, serverSearchRows, serverSortRows, isServerSortMode, category, level, search, sortBy, sortOrder, segmentFilteredNames, isSegmentFilterOpen]);

  // In server-sort mode show all loaded rows (virtual scroll handles rendering);
  // in client mode slice by visibleCount for gradual reveal.
  const visibleRows = isServerSortMode ? filteredRows : filteredRows.slice(0, visibleCount);
  const hasMore = isServerSortMode
    ? serverSortRows.length < serverSortTotal
    : visibleCount < filteredRows.length;
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const virtualStartIndex = Math.max(0, Math.floor(tableScrollTop / TABLE_ROW_HEIGHT) - VIRTUAL_OVERSCAN);
  const viewportRowCount = Math.ceil(TABLE_VIEWPORT_HEIGHT / TABLE_ROW_HEIGHT) + VIRTUAL_OVERSCAN * 2;
  const virtualEndIndex = Math.min(visibleRows.length, virtualStartIndex + viewportRowCount);
  const virtualRows = visibleRows.slice(virtualStartIndex, virtualEndIndex);
  const topSpacerHeight = virtualStartIndex * TABLE_ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (visibleRows.length - virtualEndIndex) * TABLE_ROW_HEIGHT);

  const toggleSelect = useCallback((name: string) => {
    setSelected((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  }, []);

  const openDistribution = useCallback(
    (name: string) => {
      onOpenDistribution(name);
    },
    [onOpenDistribution]
  );

  const handleTableScroll = useCallback(() => {
    const el = tableContainerRef.current;
    if (!el) return;
    setTableScrollTop(el.scrollTop);
  }, []);

  useEffect(() => {
    const el = tableContainerRef.current;
    if (el) {
      el.scrollTop = 0;
    }
    setTableScrollTop(0);
  }, [search, category, level, sortBy, sortOrder, isSegmentFilterOpen, segmentFilteredNames, taskId]);

  const selectAllCurrentPage = () => {
    const pageNames = visibleRows.map((row) => row.name);
    const pageAllSelected = pageNames.every((name) => selected.includes(name));
    if (pageAllSelected) {
      setSelected((prev) => prev.filter((name) => !pageNames.includes(name)));
      return;
    }
    setSelected((prev) => Array.from(new Set([...prev, ...pageNames])));
  };

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      <div className="flex flex-col lg:flex-row gap-2">
        <input
          value={searchInput}
          onChange={(e) => {
            setVisibleCount(PAGE_SIZE);
            setSearchInput(e.target.value);
          }}
          placeholder="搜尋特徵名..."
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
        />
        <input
          value={category}
          onChange={(e) => {
            setVisibleCount(PAGE_SIZE);
            setCategory(e.target.value);
          }}
          placeholder="category（可留空）"
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
        />
        <div className="flex items-center gap-1.5">
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [nextSortBy, nextSortOrder] = e.target.value.split(':');
              setSortBy(nextSortBy);
              setSortOrder(nextSortOrder as 'asc' | 'desc');
            }}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          >
            <option value="name:asc">Name ↑</option>
            <option value="name:desc">Name ↓</option>
            <option value="nan_ratio:desc">NaN% ↓（全量）</option>
            <option value="mean:desc">Mean ↓ *</option>
            <option value="std:desc">Std ↓ *</option>
            <option value="skewness:desc">Skew ↓ *</option>
            <option value="kurtosis:desc">Kurt ↓ *</option>
          </select>
          {isServerSortMode && !['name', 'nan_ratio'].includes(sortBy) && (
            <span className="text-[11px] text-amber-400/80" title="大型 CGSA 任務需等背景統計暖機完成後排序才完整；NaN% 排序不受此限制">
              * 暖機後準確
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {levelTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setVisibleCount(PAGE_SIZE);
              setLevel(tab);
            }}
            className={`px-3 py-1 text-xs rounded-full border ${
              level === tab ? 'bg-amber-400/20 border-amber-300/40 text-amber-200' : 'border-white/10 text-slate-300'
            }`}
          >
            {tab}
          </button>
        ))}

        <button
          onClick={() => onOpenCorrelation(selected.slice(0, 50))}
          disabled={selected.length < 2}
          className="ml-auto px-3 py-1 text-xs rounded-full border border-white/10 text-slate-200 disabled:opacity-50"
        >
          比較 ({selected.length})
        </button>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-2">
        <button
          type="button"
          onClick={() => {
            setIsSegmentFilterOpen((prev) => {
              if (prev) {
                setSegmentFilteredNames([]);
              }
              return !prev;
            });
          }}
          className="w-full text-left text-xs text-slate-300 hover:text-slate-100"
        >
          {isSegmentFilterOpen ? '收合進階命名段落篩選' : '展開進階命名段落篩選（較耗時計算）'}
        </button>
      </div>

      {isSegmentFilterOpen && (
        <FeatureNameSegmentFilter
          features={featureNames}
          onFilteredFeaturesChange={setSegmentFilteredNames}
        />
      )}

      <div className="text-[11px] text-slate-400">
        提示：表格會先載入前段資料並在背景補齊；統計值以目前已載入的特徵列為準。
      </div>

      {statsWarmup && !statsWarmup.complete && (
        <StatsWarmupBanner statsWarmup={statsWarmup} />
      )}

      {error && <div className="text-xs text-rose-300">{error}</div>}
      {loading ? (
        <div className="text-xs text-slate-400">
          載入中...
          {serverTotal > 0
            ? ` 已載入 ${loadedCount.toLocaleString()} / ${serverTotal.toLocaleString()} 筆`
            : totalCount != null
            ? ` 正在計算 ${totalCount.toLocaleString()} 個特徵的統計`
            : ' 首次載入全量資料，請稍候'}
        </div>
      ) : isServerSearching ? (
        <div className="text-xs text-slate-400">搜尋中...</div>
      ) : allRows.length === 0 ? (
        <div className="text-xs text-slate-400">沒有可用特徵。</div>
      ) : filteredRows.length === 0 ? (
        <div className="text-xs text-slate-400">沒有符合條件的特徵。</div>
      ) : (
        <div
          ref={tableContainerRef}
          onScroll={handleTableScroll}
          className="overflow-auto border border-white/10 rounded-xl max-h-[520px]"
        >
          <table className="min-w-full text-xs">
            <thead className="bg-white/5 text-slate-300">
              <tr>
                <th className="px-2 py-2 text-left">
                  <input type="checkbox" onChange={selectAllCurrentPage} />
                </th>
                <th className="px-2 py-2 text-left">Feature</th>
                <th className="px-2 py-2 text-left">Category</th>
                <th className="px-2 py-2 text-left">Level</th>
                <th className="px-2 py-2 text-left">Layer</th>
                <th className="px-2 py-2 text-left">NaN%</th>
                <th className="px-2 py-2 text-left">Mean</th>
                <th className="px-2 py-2 text-left">Std</th>
                <th className="px-2 py-2 text-left">Skew</th>
                <th className="px-2 py-2 text-left">Kurt</th>
              </tr>
            </thead>
            <tbody>
              {topSpacerHeight > 0 && (
                <tr aria-hidden="true">
                  <td colSpan={10} style={{ height: `${topSpacerHeight}px`, padding: 0, border: 0 }} />
                </tr>
              )}
              {virtualRows.map((row) => (
                <FeatureTableRow
                  key={row.name}
                  row={row}
                  checked={selectedSet.has(row.name)}
                  onToggle={toggleSelect}
                  onOpenDistribution={openDistribution}
                />
              ))}
              {bottomSpacerHeight > 0 && (
                <tr aria-hidden="true">
                  <td colSpan={10} style={{ height: `${bottomSpacerHeight}px`, padding: 0, border: 0 }} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-2 flex-wrap">
          {isServerSortMode ? (
            <>
              顯示 {visibleRows.length.toLocaleString()} / 全量排序 {serverSortTotal.toLocaleString()} 筆
              <span className="text-cyan-300 border border-cyan-300/30 rounded px-1.5 py-0.5">伺服端全量排序</span>
              {serverSortLoading && <span className="text-slate-400">載入中…</span>}
            </>
          ) : (
            <>
              顯示 {visibleRows.length.toLocaleString()} / 篩選 {filteredRows.length.toLocaleString()} / 總計 {serverTotal.toLocaleString()}
              {search && !isServerSearching && <span className="text-cyan-300">（伺服端搜尋）</span>}
              {isBackgroundLoading && <span className="text-cyan-300">（背景載入中：{loadedCount.toLocaleString()}）</span>}
            </>
          )}
        </div>
        {hasMore && (
          <button
            onClick={isServerSortMode ? loadMoreServerSort : () => setVisibleCount((prev) => prev + PAGE_SIZE)}
            disabled={isServerSortMode && serverSortLoading}
            className="px-3 py-1 rounded border border-white/10 hover:border-cyan-300/40 disabled:opacity-40"
          >
            {isServerSortMode
              ? `載入更多 (${serverSortRows.length.toLocaleString()} / ${serverSortTotal.toLocaleString()})`
              : `顯示更多 (+${Math.min(PAGE_SIZE, filteredRows.length - visibleCount)})`}
          </button>
        )}
      </div>
    </div>
  );
}

function formatNum(value: number | null) {
  if (value === null || Number.isNaN(value)) return '-';
  return value.toFixed(4);
}

function ratioColor(value: number, low: number, high: number) {
  if (value < low) return 'text-emerald-300';
  if (value < high) return 'text-amber-300';
  return 'text-rose-300';
}

function absColor(value: number | null, low: number, high: number) {
  const v = Math.abs(value || 0);
  if (v < low) return 'text-emerald-300';
  if (v < high) return 'text-amber-300';
  return 'text-rose-300';
}

function getSortableMetric(item: BrowseFeatureItem, sortBy: string): number {
  if (sortBy === 'nan_ratio') return item.nan_ratio ?? 0;
  if (sortBy === 'std') return item.std ?? 0;
  if (sortBy === 'skewness') return item.skewness ?? 0;
  if (sortBy === 'kurtosis') return item.kurtosis ?? 0;
  if (sortBy === 'mean') return item.mean ?? 0;
  return 0;
}

interface FeatureTableRowProps {
  row: BrowseFeatureItem;
  checked: boolean;
  onToggle: (name: string) => void;
  onOpenDistribution: (name: string) => void;
}

const FeatureTableRow = memo(function FeatureTableRow({
  row,
  checked,
  onToggle,
  onOpenDistribution,
}: FeatureTableRowProps) {
  return (
    <tr className="border-t border-white/5 text-slate-100">
      <td className="px-2 py-2">
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(row.name)}
        />
      </td>
      <td className="px-2 py-2">
        <button className="text-cyan-300 hover:underline" onClick={() => onOpenDistribution(row.name)}>
          {row.name}
        </button>
      </td>
      <td className="px-2 py-2">{row.category}</td>
      <td className="px-2 py-2">{row.level}</td>
      <td className="px-2 py-2">{row.layer}</td>
      <td className={`px-2 py-2 ${ratioColor(row.nan_ratio, 0.05, 0.1)}`}>
        {(row.nan_ratio * 100).toFixed(2)}%
      </td>
      <td className="px-2 py-2">{formatNum(row.mean)}</td>
      <td className="px-2 py-2">{formatNum(row.std)}</td>
      <td className={`px-2 py-2 ${absColor(row.skewness, 1, 3)}`}>{formatNum(row.skewness)}</td>
      <td className={`px-2 py-2 ${absColor(row.kurtosis, 5, 10)}`}>{formatNum(row.kurtosis)}</td>
    </tr>
  );
});
