'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { BrowseFeatureItem } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';

interface FeatureTableProps {
  taskId: string;
  totalCount?: number;
  onOpenDistribution: (feature: string) => void;
  onOpenCorrelation: (features: string[]) => void;
}

const levelTabs: Array<'All' | 'L1' | 'L2' | 'L3'> = ['All', 'L1', 'L2', 'L3'];
const PAGE_SIZE = 100;
const SERVER_PAGE_LIMIT = 5000;
const PARALLEL_BATCH_SIZE = 4;

export default function FeatureTable({ taskId, totalCount, onOpenDistribution, onOpenCorrelation }: FeatureTableProps) {
  const { browseFeatures } = useFeatureFactory();

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
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setVisibleCount(PAGE_SIZE);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

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

    const loadAllFeatures = async () => {
      try {
        let total = 0;
        const merged: BrowseFeatureItem[] = [];

        // First request gets total count and initial data block.
        const firstResp = await browseFeatures(taskId, {
          offset: 0,
          limit: SERVER_PAGE_LIMIT,
          sortBy: 'name',
          sortOrder: 'asc',
        });
        if (!active) return;

        total = firstResp.total;
        setServerTotal(total);

        if (firstResp.features.length > 0) {
          merged.push(...firstResp.features);
          setAllRows([...merged]);
          setLoadedCount(merged.length);
        }

        if (merged.length >= total || firstResp.features.length === 0) {
          return;
        }

        const offsets: number[] = [];
        for (let nextOffset = merged.length; nextOffset < total; nextOffset += SERVER_PAGE_LIMIT) {
          offsets.push(nextOffset);
        }

        for (let i = 0; i < offsets.length && active; i += PARALLEL_BATCH_SIZE) {
          const batchOffsets = offsets.slice(i, i + PARALLEL_BATCH_SIZE);
          const batchResponses = await Promise.all(
            batchOffsets.map((offset) =>
              browseFeatures(taskId, {
                offset,
                limit: SERVER_PAGE_LIMIT,
                sortBy: 'name',
                sortOrder: 'asc',
              })
            )
          );

          if (!active) return;

          // Promise.all keeps batch order aligned with batchOffsets.
          for (const resp of batchResponses) {
            if (resp.features.length === 0) continue;
            merged.push(...resp.features);
          }

          setAllRows([...merged]);
          setLoadedCount(Math.min(merged.length, total));
        }

        setLoadedCount(Math.min(merged.length, total));
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入特徵列表失敗');
      } finally {
        if (!active) return;
        setLoading(false);
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

  // Client-side filter + sort (instant, no network)
  const filteredRows = useMemo(() => {
    let result = allRows;

    if (segmentFilteredNames.length > 0) {
      const allowed = new Set(segmentFilteredNames);
      result = result.filter((r) => allowed.has(r.name));
    }

    if (category) {
      const lower = category.toLowerCase();
      result = result.filter((r) => r.category?.toLowerCase().includes(lower));
    }
    if (level !== 'All') {
      result = result.filter((r) => r.level === level);
    }
    if (search) {
      const lower = search.toLowerCase();
      result = result.filter((r) => r.name.toLowerCase().includes(lower));
    }

    return [...result].sort((a, b) => {
      const mul = sortOrder === 'asc' ? 1 : -1;
      if (sortBy === 'name') return mul * a.name.localeCompare(b.name);
      const aVal = getSortableMetric(a, sortBy);
      const bVal = getSortableMetric(b, sortBy);
      return mul * (aVal - bVal);
    });
  }, [allRows, category, level, search, sortBy, sortOrder, segmentFilteredNames]);

  const visibleRows = filteredRows.slice(0, visibleCount);
  const hasMore = visibleCount < filteredRows.length;

  const toggleSelect = (name: string) => {
    setSelected((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  };

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
          <option value="nan_ratio:desc">NaN% ↓</option>
          <option value="std:desc">Std ↓</option>
          <option value="skewness:desc">Skew ↓</option>
          <option value="kurtosis:desc">Kurt ↓</option>
        </select>
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

      <FeatureNameSegmentFilter
        features={allRows.map((row) => row.name)}
        onFilteredFeaturesChange={setSegmentFilteredNames}
      />

      <div className="text-[11px] text-slate-400">
        提示：ADF 指標會在背景預熱，首次載入後同任務的後續分頁與查詢會更快。
      </div>

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
      ) : allRows.length === 0 ? (
        <div className="text-xs text-slate-400">沒有可用特徵。</div>
      ) : filteredRows.length === 0 ? (
        <div className="text-xs text-slate-400">沒有符合條件的特徵。</div>
      ) : (
        <div className="overflow-auto border border-white/10 rounded-xl">
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
                <th className="px-2 py-2 text-left">Std</th>
                <th className="px-2 py-2 text-left">Skew</th>
                <th className="px-2 py-2 text-left">Kurt</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.name} className="border-t border-white/5 text-slate-100">
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      checked={selected.includes(row.name)}
                      onChange={() => toggleSelect(row.name)}
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
                  <td className="px-2 py-2">{formatNum(row.std)}</td>
                  <td className={`px-2 py-2 ${absColor(row.skewness, 1, 3)}`}>{formatNum(row.skewness)}</td>
                  <td className={`px-2 py-2 ${absColor(row.kurtosis, 5, 10)}`}>{formatNum(row.kurtosis)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-300">
        <div>
          顯示 {visibleRows.length.toLocaleString()} / 篩選 {filteredRows.length.toLocaleString()} / 總計 {serverTotal.toLocaleString()}
        </div>
        {hasMore && (
          <button
            onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
            className="px-3 py-1 rounded border border-white/10 hover:border-cyan-300/40"
          >
            顯示更多 (+{Math.min(PAGE_SIZE, filteredRows.length - visibleCount)})
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
