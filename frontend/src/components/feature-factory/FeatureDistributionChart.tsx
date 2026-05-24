'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TooltipProps } from 'recharts';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';

interface FeatureDistributionChartProps {
  taskId: string;
}

/**
 * 反正態 CDF（probit），Acklam 理性近似，最大誤差 1.15e-9
 * 用於 Q-Q Plot：將累積機率 p 轉換成標準常態分位數 z
 */
function probit(p: number): number {
  if (p <= 0) return -6;
  if (p >= 1) return 6;
  const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
              1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
  const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
              6.680131188771972e+01, -1.328068155288572e+01];
  const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
              -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
  const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
  const pLow = 0.02425;
  if (p < pLow) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
           ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  } else if (p <= 1 - pLow) {
    const q = p - 0.5;
    const r = q * q;
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
  } else {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
              ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  }
}

const FEATURE_NAME_LIMIT = 1000000;

/** Virtual list 相關常數 */
const ITEM_HEIGHT = 24;        // 每個特徵按鈕的固定高度 (px)
const LIST_VISIBLE_HEIGHT = 420; // 可見視窗高度 (px)，對應 max-h-[420px]
const OVERSCAN = 10;           // 上下各多渲染 10 個項目，讓捲動更流暢

export default function FeatureDistributionChart({ taskId }: FeatureDistributionChartProps) {
  const { explorerSelectedFeature, setExplorerActiveTab } = useFeatureFactoryStore();
  const sharedFeatureNames = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask[taskId]);
  const { browseDistribution, browseFeatures } = useFeatureFactory();
  const [feature, setFeature] = useState<string>('');
  const [featureOptions, setFeatureOptions] = useState<string[]>([]);
  const [filteredFeatureOptions, setFilteredFeatureOptions] = useState<string[]>([]);
  const [bins, setBins] = useState(50);
  // P2-A: ADF is opt-in — defaults OFF so the first paint stays fast.
  const [computeAdf, setComputeAdf] = useState(false);
  const [payload, setPayload] = useState<{
    bins: number[];
    edges: number[];
    stats: Record<string, number | null | boolean>;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Virtual list 捲動狀態
  const listRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const handleListScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  useEffect(() => {
    let active = true;
    if (sharedFeatureNames) {
      setFeatureOptions(sharedFeatureNames);
      setFeature((current) => current || explorerSelectedFeature || sharedFeatureNames[0] || '');
      return;
    }

    browseFeatures(taskId, { offset: 0, limit: FEATURE_NAME_LIMIT, sortBy: 'name', sortOrder: 'asc', detailLevel: 'names' })
      .then((resp) => {
        if (!active) return;
        const options = resp.features.map((item) => item.name);
        setFeatureOptions(options);
        setFeature(explorerSelectedFeature || options[0] || '');
      })
      .catch(() => {
        if (!active) return;
        setFeatureOptions([]);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId, explorerSelectedFeature, sharedFeatureNames]);

  // 建立 O(1) 查找 Set，取代 .includes() 的 O(n) 掃描
  const filteredFeatureSet = useMemo(
    () => new Set(filteredFeatureOptions),
    [filteredFeatureOptions],
  );

  useEffect(() => {
    if (!feature && filteredFeatureOptions.length > 0) {
      setFeature(filteredFeatureOptions[0]);
      return;
    }
    if (feature && filteredFeatureOptions.length > 0 && !filteredFeatureSet.has(feature)) {
      setFeature(filteredFeatureOptions[0]);
    }
  }, [feature, filteredFeatureOptions, filteredFeatureSet]);

  // 當選中的特徵不在可見範圍內時，自動捲動到該項目
  useEffect(() => {
    if (!feature || !listRef.current) return;
    const idx = filteredFeatureOptions.indexOf(feature);
    if (idx < 0) return;
    const itemTop = idx * ITEM_HEIGHT;
    const itemBottom = itemTop + ITEM_HEIGHT;
    const viewTop = listRef.current.scrollTop;
    const viewBottom = viewTop + LIST_VISIBLE_HEIGHT;
    if (itemTop < viewTop || itemBottom > viewBottom) {
      listRef.current.scrollTop = Math.max(0, itemTop - LIST_VISIBLE_HEIGHT / 2 + ITEM_HEIGHT / 2);
    }
  }, [feature, filteredFeatureOptions]);

  useEffect(() => {
    if (!feature) return;
    let active = true;
    setLoading(true);
    setError(null);

    browseDistribution(taskId, feature, bins, computeAdf)
      .then((resp) => {
        if (!active) return;
        setPayload({
          bins: resp.bins,
          edges: resp.edges,
          stats: resp.stats as unknown as Record<string, number | null | boolean>
        });
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入分佈失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseDistribution, taskId, feature, bins, computeAdf]);

  const histogramData = useMemo(() => {
    if (!payload || payload.bins.length === 0 || payload.edges.length <= 1) return [];
    const mean = typeof payload.stats.mean === 'number' ? payload.stats.mean : 0;
    const std = typeof payload.stats.std === 'number' && payload.stats.std > 0 ? payload.stats.std : 1;
    // 統計正確做法：total_n * bin_width * PDF(x)
    // 確保橘線曲線的總面積 = 直方圖總面積 = n，可直接比較「期望頻次」vs「實際頻次」
    const totalN = payload.bins.reduce((sum, c) => sum + c, 0);

    return payload.bins.map((count, idx) => {
      const x = payload.edges[idx];
      const xEnd = payload.edges[idx + 1] ?? x;
      const binWidth = xEnd - x;
      const density = Math.exp(-0.5 * ((x - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI));
      return {
        x,
        xEnd,
        count,
        // 期望頻次：若資料完全常態，這個 bin 預期應有的資料點數
        normal: density * totalN * binWidth,
      };
    });
  }, [payload]);

  const qqData = useMemo(() => {
    if (!payload || payload.bins.length === 0) return [];
    const mean = typeof payload.stats.mean === 'number' ? payload.stats.mean : 0;
    const std  = typeof payload.stats.std  === 'number' && payload.stats.std > 0 ? payload.stats.std : 1;
    const totalN = payload.bins.reduce((sum, c) => sum + c, 0);
    if (totalN === 0) return [];

    // 正確 Q-Q Plot：X = 理論常態分位數，Y = 實際資料值（bin 中點）
    // 方法：逐 bin 累積頻次，取該 bin 頻次質心的累積機率 p，
    //       再用 probit 換算成同量綱的理論分位數 mean + std * Φ⁻¹(p)
    let cumCount = 0;
    const result: { theoretical: number; empirical: number }[] = [];
    for (let i = 0; i < payload.bins.length; i++) {
      const count = payload.bins[i];
      if (count === 0) continue;
      const p = (cumCount + count / 2) / totalN; // 頻次質心的累積機率
      cumCount += count;
      const midpoint =
        payload.edges[i] !== undefined && payload.edges[i + 1] !== undefined
          ? (payload.edges[i] + payload.edges[i + 1]) / 2
          : (payload.edges[i] ?? 0);
      result.push({ theoretical: mean + std * probit(p), empirical: midpoint });
    }
    return result;
  }, [payload]);

  // Q-Q 參考線範圍：取 theoretical 和 empirical 的共同 min/max，畫 y=x 對角線
  const qqRange = useMemo(() => {
    if (qqData.length === 0) return { min: 0, max: 1 };
    const allVals = qqData.flatMap((d) => [d.theoretical, d.empirical]);
    return { min: Math.min(...allVals), max: Math.max(...allVals) };
  }, [qqData]);

  return (
    <div id="feature-distribution-chart" className="glass-panel rounded-2xl p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-sm text-slate-300">Distribution</div>
        <div className="ml-auto text-xs text-slate-300">bins: {bins}</div>
        <input
          type="range"
          min={10}
          max={200}
          step={1}
          value={bins}
          onChange={(e) => setBins(Number(e.target.value))}
        />
        <button
          onClick={() => setComputeAdf((v) => !v)}
          className={`text-xs px-2 py-1 rounded border ${
            computeAdf
              ? 'border-emerald-400/40 text-emerald-200 bg-emerald-500/10'
              : 'border-white/10 text-slate-300'
          }`}
          title="ADF 平穩性檢定（耗時，預設關閉；按下後會重新請求並計算）"
        >
          {computeAdf ? '✓ ADF 已啟用' : '計算 ADF（耗時）'}
        </button>
        <button
          onClick={() => exportChartToPNG('feature-distribution-chart', 'feature_distribution', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200"
        >
          匯出 PNG
        </button>
      </div>

      <FeatureNameSegmentFilter features={featureOptions} onFilteredFeaturesChange={setFilteredFeatureOptions} />
      <div className="flex gap-3 min-w-0">
        <div className="w-72 shrink-0">
          {/* Virtual list：只渲染可見範圍內的項目，大幅避免大量 DOM 節點造成卡頓 */}
          {(() => {
            const total = filteredFeatureOptions.length;
            const visibleStart = Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - OVERSCAN);
            const visibleEnd = Math.min(total, Math.ceil((scrollTop + LIST_VISIBLE_HEIGHT) / ITEM_HEIGHT) + OVERSCAN);
            const totalHeight = total * ITEM_HEIGHT;
            const offsetTop = visibleStart * ITEM_HEIGHT;
            return (
              <div
                ref={listRef}
                className="rounded border border-white/5 bg-black/20"
                style={{ height: LIST_VISIBLE_HEIGHT, overflowY: 'auto' }}
                onScroll={handleListScroll}
              >
                {/* 撐開全部高度，讓捲軸正確反映總項目數 */}
                <div style={{ height: totalHeight, position: 'relative' }}>
                  {/* 只掛載可見視窗 ± OVERSCAN 範圍內的 DOM 節點 */}
                  <div style={{ position: 'absolute', top: offsetTop, left: 0, right: 0 }}>
                    {filteredFeatureOptions.slice(visibleStart, visibleEnd).map((name) => (
                      <button
                        key={name}
                        type="button"
                        onClick={() => {
                          setFeature(name);
                          setExplorerActiveTab('distribution', name);
                        }}
                        title={name}
                        style={{ height: ITEM_HEIGHT }}
                        className={`w-full text-left truncate text-xs px-2 rounded ${
                          feature === name ? 'bg-indigo-400/20 text-indigo-200' : 'text-slate-300 hover:bg-white/5'
                        }`}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                </div>
                {total === 0 && (
                  <div className="px-2 py-2 text-xs text-slate-500">無符合的特徵</div>
                )}
              </div>
            );
          })()}
          <div className="mt-1 text-right text-[10px] text-slate-600">
            {filteredFeatureOptions.length.toLocaleString()} 個特徵
          </div>
        </div>
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="text-xs text-slate-400">載入中...</div>
          ) : error ? (
            <div className="text-xs text-rose-300">{error}</div>
          ) : !payload ? (
            <div className="text-xs text-slate-400">尚無資料。</div>
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={histogramData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="x" hide />
                  <YAxis />
                  <Tooltip content={<HistogramTooltip />} />
                  <Bar dataKey="count" fill="#60a5fa" />
                  <Line type="monotone" dataKey="normal" stroke="#f59e0b" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="h-[300px]">
              <div className="text-[10px] text-slate-400 mb-1 text-center">Q-Q Plot（點貼近虛線 → 常態；翹起 → fat tail；S 型 → 偏態）</div>
              <ResponsiveContainer width="100%" height="90%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="theoretical"
                    type="number"
                    name="理論常態分位數"
                    label={{ value: '理論', position: 'insideBottomRight', offset: -4, fill: '#94a3b8', fontSize: 10 }}
                    tickFormatter={(v: number) => v.toFixed(1)}
                    domain={[qqRange.min, qqRange.max]}
                  />
                  <YAxis
                    dataKey="empirical"
                    type="number"
                    name="實際資料值"
                    label={{ value: '實際', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 10 }}
                    tickFormatter={(v: number) => v.toFixed(1)}
                    domain={[qqRange.min, qqRange.max]}
                  />
                  <Tooltip content={<QQTooltip />} />
                  {/* 對角線 y=x：資料完全常態時所有點都落在此線上 */}
                  <ReferenceLine
                    segment={[
                      { x: qqRange.min, y: qqRange.min },
                      { x: qqRange.max, y: qqRange.max },
                    ]}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                  />
                  <Scatter data={qqData} fill="#f59e0b" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <Stat label="Mean" value={payload.stats.mean} />
            <Stat label="Std" value={payload.stats.std} />
            <Stat label="Skew" value={payload.stats.skewness} />
            <Stat label="Kurt" value={payload.stats.kurtosis} />
            <Stat label="ADF p-value" value={payload.stats.adf_pvalue} />
            <Stat label="NaN ratio" value={payload.stats.nan_ratio} percentage />
          </div>
        </>
      )}
        </div>
      </div>
    </div>
  );
}

function QQTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as { theoretical: number; empirical: number } | undefined;
  if (!d) return null;
  const diff = d.empirical - d.theoretical;
  const pct = d.theoretical !== 0 ? Math.abs(diff / d.theoretical) * 100 : 0;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs space-y-1 shadow-xl">
      <div className="text-slate-300">理論常態分位數：<span className="text-slate-100 font-medium">{d.theoretical.toFixed(4)}</span></div>
      <div className="text-amber-300">實際資料值：<span className="text-amber-100 font-medium">{d.empirical.toFixed(4)}</span></div>
      <div className={pct < 5 ? 'text-green-300' : pct < 15 ? 'text-amber-300' : 'text-rose-300'}>
        偏差：{diff >= 0 ? '+' : ''}{diff.toFixed(4)}
        <span className="text-slate-400 ml-1">({pct.toFixed(1)}%)</span>
      </div>
    </div>
  );
}

function HistogramTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as { x: number; xEnd: number; count: number; normal: number } | undefined;
  if (!d) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs space-y-1 shadow-xl">
      <div className="text-slate-300 font-medium">
        區間：{d.x?.toFixed(4)} ~ {d.xEnd?.toFixed(4)}
      </div>
      <div className="text-blue-300">
        頻次（count）：<span className="font-semibold text-blue-100">{d.count}</span>
      </div>
      <div className="text-amber-300">
        常態期望（normal）：<span className="font-semibold text-amber-100">{d.normal?.toFixed(2)}</span>
        <div className="text-slate-400 text-[10px] mt-0.5">若資料完全常態，此區間的理論期望頻次</div>
      </div>
    </div>
  );
}

function Stat({ label, value, percentage = false }: { label: string; value: unknown; percentage?: boolean }) {
  const number = typeof value === 'number' ? value : null;
  const formatted = number === null ? '-' : percentage ? `${(number * 100).toFixed(2)}%` : number.toFixed(4);
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-2">
      <div className="text-slate-400">{label}</div>
      <div className="text-slate-100">{formatted}</div>
    </div>
  );
}
