'use client';

import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CoverageMatrixResponsePayload, FeatureRegistryEntry } from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SymbolCoverageMatrixProps {
  entries: FeatureRegistryEntry[];
  featureNames: string[];
}

function clampFeatureLimit(value: number): number {
  if (!Number.isFinite(value)) return 100;
  return Math.min(100, Math.max(1, Math.floor(value)));
}

function getCellClass(nanRatio: number | null): string {
  if (nanRatio === null || !Number.isFinite(nanRatio)) {
    return 'bg-slate-500/30';
  }

  const coverage = 1 - nanRatio;
  if (coverage >= 1.0) return 'bg-emerald-500/80';
  if (coverage >= 0.8) return 'bg-emerald-500/60';
  if (coverage >= 0.5) return 'bg-amber-500/60';
  if (coverage >= 0.3) return 'bg-orange-500/60';
  return 'bg-rose-500/70';
}

export default function SymbolCoverageMatrix({ entries, featureNames }: SymbolCoverageMatrixProps) {
  const [timeframe, setTimeframe] = useState('');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [maxFeatures, setMaxFeatures] = useState(100);
  const [payload, setPayload] = useState<CoverageMatrixResponsePayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const limitedFeatureNames = useMemo(() => {
    return featureNames.slice(0, clampFeatureLimit(maxFeatures));
  }, [featureNames, maxFeatures]);

  const toggleSymbol = (symbol: string, checked: boolean) => {
    setSelectedSymbols((prev) => {
      if (checked) {
        return Array.from(new Set([...prev, symbol]));
      }
      return prev.filter((item) => item !== symbol);
    });
  };

  const runCoverage = async () => {
    if (selectedSymbols.length < 2) {
      setError('請至少選擇 2 個 Symbol');
      return;
    }

    if (limitedFeatureNames.length === 0) {
      setError('目前無可用 features，請先載入 Feature Browser overview');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/coverage-matrix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: selectedSymbols,
          timeframe,
          feature_names: limitedFeatureNames,
          timeout_seconds: 30,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.detail || response.statusText);
      }

      const data = (await response.json()) as CoverageMatrixResponsePayload;
      setPayload(data);
    } catch (fetchError) {
      setPayload(null);
      setError(fetchError instanceof Error ? fetchError.message : 'Coverage Matrix 請求失敗');
    } finally {
      setLoading(false);
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
          最多 features
          <Input
            type="number"
            min={1}
            max={100}
            value={maxFeatures}
            onChange={(event) => setMaxFeatures(clampFeatureLimit(Number(event.target.value)))}
            className="w-24"
          />
        </div>

        <Button onClick={runCoverage} disabled={loading || selectedSymbols.length < 2}>
          {loading ? '計算中...' : '計算 Coverage Matrix'}
        </Button>

        {payload?.summary && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge className="border-cyan-400/40 bg-cyan-500/10 text-cyan-200">Avg {(payload.summary.avg_coverage * 100).toFixed(2)}%</Badge>
            {payload.summary.worst_symbol && (
              <Badge className="border-amber-400/40 bg-amber-500/10 text-amber-200">Worst Symbol {payload.summary.worst_symbol}</Badge>
            )}
            {payload.summary.worst_feature && (
              <Badge className="border-rose-400/40 bg-rose-500/10 text-rose-200">Worst Feature {payload.summary.worst_feature}</Badge>
            )}
          </div>
        )}
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

      {!payload ? (
        <div className="rounded-md border border-white/10 p-4 text-sm text-slate-400">
          執行計算後顯示 Coverage Matrix。
        </div>
      ) : payload.features.length === 0 ? (
        <div className="rounded-md border border-white/10 p-4 text-sm text-slate-400">
          Coverage Matrix 無可用 feature，請確認 Feature Browser 已載入目錄資料。
        </div>
      ) : (
        <div className="overflow-auto max-h-[560px] rounded border border-white/10">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-[#0f172a] z-10">
              <tr>
                <th className="px-2 py-2 text-left text-slate-300">Feature</th>
                {payload.symbols.map((symbol) => (
                  <th key={symbol} className="px-2 py-2 text-left text-slate-300">{symbol}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {payload.features.map((featureName) => (
                <tr key={featureName} className="border-t border-white/5">
                  <td className="px-2 py-1 text-slate-200 whitespace-nowrap">{featureName}</td>
                  {payload.symbols.map((symbol) => {
                    const nanRatio = payload.matrix?.[featureName]?.[symbol] ?? null;
                    const validCount = payload.valid_counts?.[featureName]?.[symbol] ?? 0;
                    const totalCount = payload.row_counts?.[symbol] ?? 0;
                    const coveragePct =
                      nanRatio === null || !Number.isFinite(nanRatio)
                        ? '--'
                        : `${((1 - nanRatio) * 100).toFixed(1)}%`;

                    return (
                      <td key={`${featureName}-${symbol}`} className="px-2 py-1">
                        <div
                          className={`rounded px-2 py-1 text-[11px] text-slate-100 ${getCellClass(nanRatio)}`}
                          title={`NaN: ${nanRatio === null ? '--' : (nanRatio * 100).toFixed(2)}% | Coverage: ${coveragePct} | Valid: ${validCount}/${totalCount}`}
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
  );
}
