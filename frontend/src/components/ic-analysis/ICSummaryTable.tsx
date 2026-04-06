'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import { Star } from 'lucide-react';
import { ICAnalysisConfig, ICFeatureInfo, WatchlistStatus } from '@/lib/types';
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

interface ICSummaryTableProps {
  data: ICFeatureInfo[];
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

type SortField = 'rank' | 'ic_mean' | 'icir' | 'ic_hit_rate' | 't_stat' | 'p_value' | 'monotonicity_score';

type SortDirection = 'asc' | 'desc';

const AUTO_SUGGEST_LIMIT = 12;

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export default function ICSummaryTable({
  data,
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
  const [sortField, setSortField] = useState<SortField>('icir');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
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

  const resolveTStat = useCallback((item: ICFeatureInfo): number | null => {
    if (typeof item.t_stat === 'number' && Number.isFinite(item.t_stat)) {
      return item.t_stat;
    }

    if (!isCrossSectional || crossSectionalSampleSize < 2) {
      return null;
    }

    const icMean = item.ic_mean;
    const icir = item.icir;
    if (!Number.isFinite(icMean) || !Number.isFinite(icir) || icir === 0) {
      return null;
    }

    const icStd = Math.abs(icMean / icir);
    if (!Number.isFinite(icStd) || icStd <= 0) {
      return null;
    }

    return icMean / (icStd / Math.sqrt(crossSectionalSampleSize));
  }, [isCrossSectional, crossSectionalSampleSize]);

  const resolveICStd = useCallback((item: ICFeatureInfo): number | null => {
    if (typeof item.ic_std === 'number' && Number.isFinite(item.ic_std) && item.ic_std > 0) {
      return item.ic_std;
    }

    const icMean = item.ic_mean;
    const icir = item.icir;
    if (!Number.isFinite(icMean) || !Number.isFinite(icir) || icir === 0) {
      return null;
    }

    const derivedStd = Math.abs(icMean / icir);
    if (!Number.isFinite(derivedStd) || derivedStd <= 0) {
      return null;
    }
    return derivedStd;
  }, []);

  const resolveConfidenceInterval = useCallback((item: ICFeatureInfo): { lower: number; upper: number } | null => {
    if (!isCrossSectional || crossSectionalSampleSize < 2) {
      return null;
    }

    const icMean = item.ic_mean;
    const icStd = resolveICStd(item);
    if (!Number.isFinite(icMean) || icStd === null || icStd <= 0) {
      return null;
    }

    const standardError = icStd / Math.sqrt(crossSectionalSampleSize);
    if (!Number.isFinite(standardError) || standardError <= 0) {
      return null;
    }

    const margin = 1.96 * standardError;
    return {
      lower: icMean - margin,
      upper: icMean + margin,
    };
  }, [crossSectionalSampleSize, isCrossSectional, resolveICStd]);

  const getSortValue = useCallback((item: ICFeatureInfo, field: SortField): number => {
    if (field === 't_stat') {
      const value = resolveTStat(item);
      return value ?? Number.NEGATIVE_INFINITY;
    }

    const value = item[field as keyof ICFeatureInfo];
    return typeof value === 'number' && Number.isFinite(value) ? value : Number.NEGATIVE_INFINITY;
  }, [resolveTStat]);

  const sortedData = useMemo(() => {
    const cloned = [...data];
    cloned.sort((a, b) => {
      const aVal = getSortValue(a, sortField);
      const bVal = getSortValue(b, sortField);
      if (aVal === bVal) return 0;
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });
    return cloned;
  }, [data, sortDirection, sortField, getSortValue]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleSort(field)}
      className="h-8 px-2 text-xs"
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );

  const allSelected = sortedData.length > 0 && sortedData.every((item) => selectedFeatures.includes(item.feature_name));

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectFeatures) return;
    if (!checked) {
      onSelectFeatures([]);
      return;
    }
    onSelectFeatures(sortedData.map((item) => item.feature_name));
  };

  const toggleFeature = (featureName: string, checked: boolean) => {
    if (!onSelectFeatures) return;
    if (checked) {
      onSelectFeatures(Array.from(new Set([...selectedFeatures, featureName])));
      return;
    }
    onSelectFeatures(selectedFeatures.filter((item) => item !== featureName));
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
    for (const featureName of selectedFeatures) {
      const item = sortedData.find((row) => row.feature_name === featureName);
      if (!item) {
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
    setWatchlistInfo(`已將 ${updatedCount} 個因子標記為已驗證`);
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
    setWatchlistInfo(`Auto-Suggest 已更新 ${updatedCount} 個候選因子`);
  };

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
        {sortedData.length === 0 ? (
          <div className="flex items-center justify-center h-[200px] text-slate-400">
            暫無分析結果
          </div>
        ) : (
          <div className="rounded-md border border-white/10">
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
                  <TableHead className="w-[120px]">
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
                      <TableHead className="w-[180px]">CI 95%</TableHead>
                    </>
                  ) : (
                    <>
                      <TableHead className="w-[120px]">
                        <SortButton field="p_value" label="P-Value" />
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
                  const tStat = resolveTStat(item);
                  const confidenceInterval = resolveConfidenceInterval(item);
                  return (
                    <TableRow
                      key={`${item.feature_name}-${index}`}
                      className={isSelected ? 'bg-cyan-500/10' : ''}
                      onClick={() => onSelectFeature?.(item.feature_name)}
                    >
                      {selectable && (
                        <TableCell onClick={(event) => event.stopPropagation()}>
                          <Checkbox
                            checked={selectedFeatures.includes(item.feature_name)}
                            onCheckedChange={(checked) => toggleFeature(item.feature_name, Boolean(checked))}
                          />
                        </TableCell>
                      )}
                      <TableCell className="text-sm text-slate-300">#{item.rank ?? index + 1}</TableCell>
                      <TableCell className="font-medium text-slate-100">
                        <Link
                          href={`/feature-browser?feature=${encodeURIComponent(item.feature_name)}&tab=distribution`}
                          onClick={(event) => event.stopPropagation()}
                          className="text-cyan-300 hover:text-cyan-200 underline-offset-2 hover:underline"
                        >
                          {item.feature_name}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-200">
                        {item.ic_mean?.toFixed(4)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-emerald-300">
                        {item.icir?.toFixed(3)}
                      </TableCell>
                      {isCrossSectional ? (
                        <>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {typeof item.ic_hit_rate === 'number' ? `${(item.ic_hit_rate * 100).toFixed(1)}%` : '--'}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {typeof tStat === 'number' && Number.isFinite(tStat) ? tStat.toFixed(3) : '--'}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {confidenceInterval
                              ? `[${confidenceInterval.lower.toFixed(4)}, ${confidenceInterval.upper.toFixed(4)}]`
                              : '--'}
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {item.p_value?.toFixed(4)}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-slate-300">
                            {item.monotonicity_score?.toFixed(2) ?? '--'}
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
                IC: {watchlistFeature.ic_mean.toFixed(4)} | ICIR: {watchlistFeature.icir.toFixed(3)}
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
