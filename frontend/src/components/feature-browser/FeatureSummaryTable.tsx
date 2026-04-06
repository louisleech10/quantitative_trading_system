'use client';

import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Star } from 'lucide-react';

import type { FeatureBrowserDistributionResponse, FeatureOverview, WatchlistStatus } from '@/lib/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useWatchlistStore } from '@/store/watchlistStore';

interface FeatureSummaryTableProps {
  overview: FeatureOverview | null;
  featuresPath: string;
  selectedFeature: string | null;
  onSelectFeature: (feature: string) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function FeatureSummaryTable({
  overview,
  featuresPath,
  selectedFeature,
  onSelectFeature,
}: FeatureSummaryTableProps) {
  const [distribution, setDistribution] = useState<FeatureBrowserDistributionResponse | null>(null);
  const [isLoadingDistribution, setIsLoadingDistribution] = useState(false);
  const [distributionError, setDistributionError] = useState<string | null>(null);
  const [watchlistFeature, setWatchlistFeature] = useState<string | null>(null);
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>('candidate');
  const [watchlistNote, setWatchlistNote] = useState('');
  const [watchlistError, setWatchlistError] = useState<string | null>(null);

  const watchlistEntries = useWatchlistStore((state) => state.entries);
  const addWatchlistEntry = useWatchlistStore((state) => state.addEntry);

  const selected = selectedFeature || overview?.items[0]?.feature_name || null;

  const watchlistSet = useMemo(
    () => new Set(watchlistEntries.map((entry) => entry.feature_name)),
    [watchlistEntries]
  );

  const nanHeatmapData = useMemo(() => {
    if (!overview) {
      return [];
    }
    return overview.items.slice(0, 30).map((item) => ({
      feature_name: item.feature_name,
      nan_pct: item.nan_pct,
    }));
  }, [overview]);

  const handleLoadDistribution = async (featureName: string) => {
    if (!featuresPath.trim()) {
      setDistributionError('請先輸入 features_path');
      return;
    }

    onSelectFeature(featureName);
    setDistributionError(null);
    setIsLoadingDistribution(true);

    try {
      const query = new URLSearchParams({
        features_path: featuresPath,
        bins: '40',
      });
      const response = await fetch(
        `${API_BASE_URL}/api/v1/feature-browser/distribution/${encodeURIComponent(featureName)}?${query.toString()}`,
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || response.statusText);
      }
      const payload: FeatureBrowserDistributionResponse = await response.json();
      setDistribution(payload);
    } catch (error) {
      setDistributionError(error instanceof Error ? error.message : '讀取分佈失敗');
      setDistribution(null);
    } finally {
      setIsLoadingDistribution(false);
    }
  };

  const openWatchlistDialog = (featureName: string) => {
    const existing = watchlistEntries.find((entry) => entry.feature_name === featureName);
    setWatchlistFeature(featureName);
    setWatchlistStatus(existing?.status || 'candidate');
    setWatchlistNote(existing?.note || '');
    setWatchlistError(null);
  };

  const submitWatchlist = () => {
    if (!watchlistFeature) {
      return;
    }

    try {
      addWatchlistEntry({
        feature_name: watchlistFeature,
        task_id: featuresPath || 'feature-browser',
        status: watchlistStatus,
        note: watchlistNote,
        ic_snapshot: null,
        icir_snapshot: null,
        added_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setWatchlistFeature(null);
      setWatchlistError(null);
    } catch (error) {
      setWatchlistError(error instanceof Error ? error.message : '加入 Watchlist 失敗');
    }
  };

  if (!overview || overview.items.length === 0) {
    return <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4 text-sm text-slate-300">沒有可顯示的特徵摘要。</div>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C30 FeatureSummaryTable</h3>
        <p className="mt-1 text-xs text-slate-400">
          特徵數 {overview.total_features} / 數值欄位 {overview.numeric_features} / 平均 NaN% {overview.mean_nan_pct.toFixed(2)}
        </p>

        {watchlistError && (
          <div className="mt-2 text-xs text-rose-300">{watchlistError}</div>
        )}

        <div className="mt-4 max-h-72 overflow-auto">
          <table className="min-w-full text-xs">
            <thead className="text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">Feature</th>
                <th className="px-2 py-1 text-right">Mean</th>
                <th className="px-2 py-1 text-right">Std</th>
                <th className="px-2 py-1 text-right">Min</th>
                <th className="px-2 py-1 text-right">Max</th>
                <th className="px-2 py-1 text-right">NaN%</th>
                <th className="px-2 py-1 text-right">Action</th>
                <th className="px-2 py-1 text-right">Watchlist</th>
              </tr>
            </thead>
            <tbody>
              {overview.items.slice(0, 120).map((item) => (
                <tr key={item.feature_name} className={selected === item.feature_name ? 'bg-white/10' : ''}>
                  <td className="px-2 py-1 text-slate-100">{item.feature_name}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.mean?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.std?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.min?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.max?.toFixed(4) ?? '-'}</td>
                  <td className="px-2 py-1 text-right text-slate-300">{item.nan_pct.toFixed(2)}</td>
                  <td className="px-2 py-1 text-right">
                    <button
                      onClick={() => handleLoadDistribution(item.feature_name)}
                      className="rounded border border-white/20 px-2 py-1 text-slate-200 hover:bg-white/10"
                    >
                      C31
                    </button>
                  </td>
                  <td className="px-2 py-1 text-right">
                    <button
                      onClick={() => openWatchlistDialog(item.feature_name)}
                      className="inline-flex items-center rounded border border-amber-400/40 px-2 py-1 text-amber-200 hover:bg-amber-400/10"
                    >
                      <Star className={`h-3.5 w-3.5 ${watchlistSet.has(item.feature_name) ? 'fill-amber-300' : ''}`} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C31 FeatureDistributionChart</h3>
        {isLoadingDistribution ? (
          <div className="mt-3 text-sm text-slate-300">載入分佈中...</div>
        ) : distributionError ? (
          <div className="mt-3 text-sm text-rose-300">{distributionError}</div>
        ) : !distribution || distribution.histogram.length === 0 ? (
          <div className="mt-3 text-sm text-slate-300">請從上方點選 C31 載入特徵分佈。</div>
        ) : (
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distribution.histogram}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="left" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#60a5fa" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-[#141b2d] p-4">
        <h3 className="text-base font-semibold text-slate-100">C32 NaNHeatmap</h3>
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6">
          {nanHeatmapData.map((item) => {
            const level = Math.min(100, Math.max(0, item.nan_pct));
            return (
              <div
                key={item.feature_name}
                title={`${item.feature_name}: ${item.nan_pct.toFixed(2)}%`}
                className="rounded border border-white/10 p-2"
                style={{
                  background: `rgba(244, 63, 94, ${0.1 + (level / 100) * 0.7})`,
                }}
              >
                <div className="truncate text-[10px] text-slate-100">{item.feature_name}</div>
                <div className="text-[10px] text-slate-200">{item.nan_pct.toFixed(1)}%</div>
              </div>
            );
          })}
        </div>
      </div>

      <Dialog open={Boolean(watchlistFeature)} onOpenChange={(open) => !open && setWatchlistFeature(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>加入 Watchlist</DialogTitle>
            <DialogDescription>{watchlistFeature || '--'}</DialogDescription>
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

            {watchlistError && <div className="text-xs text-rose-300">{watchlistError}</div>}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setWatchlistFeature(null)}>取消</Button>
            <Button onClick={submitWatchlist}>儲存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
