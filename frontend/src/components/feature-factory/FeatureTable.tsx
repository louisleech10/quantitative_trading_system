'use client';

import { useEffect, useState } from 'react';
import { BrowseFeatureItem } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';

interface FeatureTableProps {
  taskId: string;
  onOpenDistribution: (feature: string) => void;
  onOpenCorrelation: (features: string[]) => void;
}

const levelTabs: Array<'All' | 'L1' | 'L2' | 'L3'> = ['All', 'L1', 'L2', 'L3'];

export default function FeatureTable({ taskId, onOpenDistribution, onOpenCorrelation }: FeatureTableProps) {
  const { browseFeatures } = useFeatureFactory();
  const [rows, setRows] = useState<BrowseFeatureItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(50);
  const [category, setCategory] = useState('');
  const [level, setLevel] = useState<'All' | 'L1' | 'L2' | 'L3'>('All');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    browseFeatures(taskId, {
      offset,
      limit,
      category: category || undefined,
      level: level === 'All' ? undefined : level,
      search: search || undefined,
      sortBy,
      sortOrder,
    })
      .then((resp) => {
        if (!active) return;
        setRows((prev) => (offset === 0 ? resp.features : [...prev, ...resp.features]));
        setTotal(resp.total);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入特徵列表失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId, offset, limit, category, level, search, sortBy, sortOrder]);

  const hasMore = offset + limit < total;

  const toggleSelect = (name: string) => {
    setSelected((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  };

  const selectAllCurrentPage = () => {
    const pageNames = rows.map((row) => row.name);
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
            setOffset(0);
            setRows([]);
            setSearchInput(e.target.value);
          }}
          placeholder="搜尋特徵名..."
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
        />
        <input
          value={category}
          onChange={(e) => {
            setOffset(0);
            setRows([]);
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
              setOffset(0);
              setRows([]);
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

      {error && <div className="text-xs text-rose-300">{error}</div>}
      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : rows.length === 0 ? (
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
              {rows.map((row) => (
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
        <div>已載入 {rows.length.toLocaleString()} / {total.toLocaleString()}</div>
        <button
          onClick={() => setOffset((prev) => prev + limit)}
          disabled={!hasMore || loading}
          className="px-3 py-1 rounded border border-white/10 disabled:opacity-50"
        >
          {hasMore ? '載入更多' : '已全部載入'}
        </button>
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
