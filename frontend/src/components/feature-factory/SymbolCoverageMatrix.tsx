'use client';

import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  GroupCoverageResponsePayload,
  GroupFeatureCoverageResponsePayload,
  FeatureRegistryEntry,
} from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SymbolCoverageMatrixProps {
  entries: FeatureRegistryEntry[];
  featureNames?: string[];
}

function clampTopN(value: number): number {
  if (!Number.isFinite(value)) return 100;
  return Math.min(500, Math.max(1, Math.floor(value)));
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
  const [topN, setTopN] = useState(100);
  const [groupPayload, setGroupPayload] = useState<GroupCoverageResponsePayload | null>(null);
  const [drillPayload, setDrillPayload] = useState<GroupFeatureCoverageResponsePayload | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [drillLoading, setDrillLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drillError, setDrillError] = useState<string | null>(null);

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

  const runGroupCoverage = async () => {
    if (selectedSymbols.length < 2) {
      setError('請至少選擇 2 個 Symbol');
      return;
    }

    setLoading(true);
    setError(null);
    setDrillPayload(null);
    setSelectedGroup(null);
    setDrillError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/group-coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: selectedSymbols,
          timeframe,
          timeout_seconds: 30,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.detail || response.statusText);
      }

      const data = (await response.json()) as GroupCoverageResponsePayload;
      setGroupPayload(data);
    } catch (fetchError) {
      setGroupPayload(null);
      setError(fetchError instanceof Error ? fetchError.message : 'Group Coverage 請求失敗');
    } finally {
      setLoading(false);
    }
  };

  const runGroupDrilldown = async (groupName: string) => {
    if (selectedSymbols.length < 2) {
      setDrillError('請至少選擇 2 個 Symbol');
      return;
    }

    setSelectedGroup(groupName);
    setDrillLoading(true);
    setDrillError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/group-feature-coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: selectedSymbols,
          timeframe,
          group_name: groupName,
          top_n: clampTopN(topN),
          timeout_seconds: 30,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.detail || response.statusText);
      }

      const data = (await response.json()) as GroupFeatureCoverageResponsePayload;
      setDrillPayload(data);
    } catch (fetchError) {
      setDrillPayload(null);
      setDrillError(fetchError instanceof Error ? fetchError.message : 'Group 下鑽請求失敗');
    } finally {
      setDrillLoading(false);
    }
  };

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
          下鑽 top_n
          <Input
            type="number"
            min={1}
            max={500}
            value={topN}
            onChange={(event) => setTopN(clampTopN(Number(event.target.value)))}
            className="w-24"
          />
        </div>

        <Button onClick={runGroupCoverage} disabled={loading || selectedSymbols.length < 2}>
          {loading ? '計算中...' : '計算 Group Coverage'}
        </Button>

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
        <div className="rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
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
        <div className="rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {drillError}
        </div>
      )}

      {selectedGroup && (
        <div className="space-y-2">
          <div className="text-sm text-slate-200">
            下鑽 Group: <span className="text-cyan-300">{selectedGroup}</span>
            {drillLoading && <span className="ml-2 text-slate-400">載入中...</span>}
          </div>

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
