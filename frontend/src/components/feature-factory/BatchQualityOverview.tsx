'use client';

/**
 * BatchQualityOverview.tsx
 *
 * 批次特徵生成完成後的 Symbol 品質彙整總覽。
 * 主指標：real_problem（真問題數）；NaN 以五數摘要（Min/Q1/Median/Q3/Max）呈現。
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { ChevronUp, ChevronDown, RefreshCw, AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react';
import type { NanRatioQuantiles } from '@/lib/types';
import CollapsibleSection from '@/components/feature-factory/CollapsibleSection';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BATCH_QUALITY_EXPANDED_KEY = 'ff-batch-quality-expanded';

/* ---------- Types ---------- */

interface SymbolQualitySummary {
  symbol: string;
  bar_count: number;
  feature_count: number;
  nan_ratio_mean: number;
  nan_ratio_max: number;
  nan_quantiles?: NanRatioQuantiles;
  constant_feature_count: number;
  alert_count: number;
  real_problem_count?: number;
  warmup_only_count?: number;
  grade: 'pass' | 'watch' | 'reject';
}

interface BatchQualityResponse {
  batch_task_id: string;
  summaries: SymbolQualitySummary[];
  total_symbols: number;
  pass_count: number;
  watch_count: number;
  reject_count: number;
  computed_at: string;
}

type SortKey =
  | 'symbol'
  | 'bar_count'
  | 'feature_count'
  | 'real_problem'
  | 'nan_min'
  | 'nan_q1'
  | 'nan_median'
  | 'nan_q3'
  | 'nan_max'
  | 'nan_ratio_mean'
  | 'nan_ratio_max'
  | 'constant_feature_count'
  | 'grade';

/* ---------- Helpers ---------- */

const GRADE_ORDER: Record<string, number> = { reject: 0, watch: 1, pass: 2 };

const EMPTY_QUANTILES: NanRatioQuantiles = {
  min: 0,
  q1: 0,
  median: 0,
  q3: 0,
  max: 0,
};

function resolveQuantiles(summary: SymbolQualitySummary): NanRatioQuantiles {
  return summary.nan_quantiles ?? EMPTY_QUANTILES;
}

function realProblemCount(summary: SymbolQualitySummary): number {
  return summary.real_problem_count ?? summary.alert_count;
}

function sortValue(summary: SymbolQualitySummary, key: SortKey): string | number {
  const q = resolveQuantiles(summary);
  switch (key) {
    case 'real_problem':
      return realProblemCount(summary);
    case 'nan_min':
      return q.min;
    case 'nan_q1':
      return q.q1;
    case 'nan_median':
      return q.median;
    case 'nan_q3':
      return q.q3;
    case 'nan_max':
      return q.max;
    case 'grade':
      return GRADE_ORDER[summary.grade] ?? 3;
    default:
      return summary[key as keyof SymbolQualitySummary] as string | number;
  }
}

function CriteriaLegend() {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-slate-400 hover:text-slate-200 transition"
      >
        <span className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5" />
          評級標準說明
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-3">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left py-1 pr-2 text-slate-400 font-medium">評級</th>
                <th className="text-left py-1 pr-2 text-slate-400 font-medium">真問題數</th>
                <th className="text-left py-1 pr-2 text-slate-400 font-medium">Bar 數</th>
                <th className="text-left py-1 pr-2 text-slate-400 font-medium">常數特徵</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              <tr>
                <td className="py-1 pr-2"><GradeBadge grade="pass" /></td>
                <td className="py-1 pr-2 text-emerald-300">= 0</td>
                <td className="py-1 pr-2 text-emerald-300">≥ 500</td>
                <td className="py-1 pr-2 text-emerald-300">= 0</td>
              </tr>
              <tr>
                <td className="py-1 pr-2"><GradeBadge grade="watch" /></td>
                <td className="py-1 pr-2 text-amber-300">&gt; 5</td>
                <td className="py-1 pr-2 text-amber-300">200–500</td>
                <td className="py-1 pr-2 text-amber-300">-</td>
              </tr>
              <tr>
                <td className="py-1 pr-2"><GradeBadge grade="reject" /></td>
                <td className="py-1 pr-2 text-rose-300">-</td>
                <td className="py-1 pr-2 text-rose-300">&lt; 200</td>
                <td className="py-1 pr-2 text-rose-300">&gt; 0</td>
              </tr>
            </tbody>
          </table>
          <div className="space-y-1.5 border-t border-white/10 pt-2">
            <div className="text-slate-400 font-medium mb-1">欄位說明</div>
            <div className="flex gap-2">
              <span className="text-slate-300 w-20 shrink-0">真問題</span>
              <span className="text-slate-500">mid-hole / 全 NaN 特徵數（不含純暖機 leading NaN）。評級以此為主。</span>
            </div>
            <div className="flex gap-2">
              <span className="text-slate-300 w-20 shrink-0">NaN 五數</span>
              <span className="text-slate-500">各特徵真實缺值率（np.isnan）的 Min / Q1 / Median / Q3 / Max，比單一均值更能反映分布。</span>
            </div>
            <div className="flex gap-2">
              <span className="text-slate-300 w-20 shrink-0">均/峰</span>
              <span className="text-slate-500 text-slate-600">含暖機僅供參考；主判斷請看五數與真問題數。</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatPct(value: number): string {
  // NaN 統計(5-number + 均/峰)用小數第三位:小比例(如 q1=0.47%)在 1 位會被抹成 0.5%/0%,失真
  return `${(value * 100).toFixed(3)}%`;
}

function GradeBadge({ grade }: { grade: 'pass' | 'watch' | 'reject' }) {
  if (grade === 'pass') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/15 px-2 py-0.5 text-xs text-emerald-300 border border-emerald-400/30">
        <CheckCircle className="w-3 h-3" />
        Pass
      </span>
    );
  }
  if (grade === 'watch') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-400/15 px-2 py-0.5 text-xs text-amber-300 border border-amber-400/30">
        <AlertTriangle className="w-3 h-3" />
        Watch
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-rose-400/15 px-2 py-0.5 text-xs text-rose-300 border border-rose-400/30">
      <XCircle className="w-3 h-3" />
      Reject
    </span>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  const cls = `w-3 h-3 ${active ? 'text-amber-300' : 'text-slate-500'}`;
  return dir === 'asc' ? <ChevronUp className={cls} /> : <ChevronDown className={cls} />;
}

function nanColor(ratio: number): string {
  if (ratio > 0.3) return 'text-rose-300';
  if (ratio > 0.1) return 'text-amber-300';
  return 'text-emerald-300';
}

/* ---------- Batch discovery (checkpoint list) ---------- */

export interface RecoverableBatchSummary {
  batch_id: string;
  symbols: string[];
  timeframe: string;
  completed_count: number;
  updated_at: string;
}

function formatBatchOptionLabel(batch: RecoverableBatchSummary): string {
  const symPreview =
    batch.symbols.length > 2
      ? `${batch.symbols.slice(0, 2).join(', ')}+${batch.symbols.length - 2}`
      : batch.symbols.join(', ');
  const idShort =
    batch.batch_id.length > 20
      ? `${batch.batch_id.slice(0, 8)}…${batch.batch_id.slice(-8)}`
      : batch.batch_id;
  return `${symPreview || idShort} · ${batch.timeframe || '?'} · ${batch.completed_count}`;
}

interface BatchRecoverableSelectProps {
  batches: RecoverableBatchSummary[];
  value: string;
  onChange: (batchId: string) => void;
  disabled?: boolean;
}

export function BatchRecoverableSelect({
  batches,
  value,
  onChange,
  disabled = false,
}: BatchRecoverableSelectProps) {
  return (
    <select
      value={value}
      disabled={disabled || batches.length === 0}
      onChange={(e) => {
        const next = e.target.value;
        if (next) onChange(next);
      }}
      className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/40 max-w-full min-w-[12rem]"
      title="切換最近批次"
    >
      <option value="">最近批次 ({batches.length})…</option>
      {batches.map((batch) => (
        <option key={batch.batch_id} value={batch.batch_id}>
          {formatBatchOptionLabel(batch)}
        </option>
      ))}
    </select>
  );
}

/* ---------- Component ---------- */

interface BatchQualityOverviewProps {
  batchTaskId: string;
  onBatchExpired?: () => void;
}

export default function BatchQualityOverview({ batchTaskId, onBatchExpired }: BatchQualityOverviewProps) {
  const [data, setData] = useState<BatchQualityResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('grade');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  // onBatchExpired 以 ref 保存：避免父層傳 inline callback 時，每次 re-render 都
  // 產生新 reference → fetchQuality 變新 → useEffect 重跑 → 對 /quality 重複請求
  // （12s 級慢端點）。fetch 僅應在 batchTaskId 改變時觸發。
  const onBatchExpiredRef = useRef(onBatchExpired);
  useEffect(() => {
    onBatchExpiredRef.current = onBatchExpired;
  }, [onBatchExpired]);

  const fetchQuality = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/features/batch/${batchTaskId}/quality`);
      if (res.status === 404) {
        setError('批次已失效');
        onBatchExpiredRef.current?.();
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = (await res.json()) as BatchQualityResponse;
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : '品質分析失敗');
    } finally {
      setIsLoading(false);
    }
  }, [batchTaskId]);

  useEffect(() => {
    fetchQuality();
  }, [fetchQuality]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sorted = data
    ? [...data.summaries].sort((a, b) => {
        const va = sortValue(a, sortKey);
        const vb = sortValue(b, sortKey);
        const cmp = va < vb ? -1 : va > vb ? 1 : 0;
        return sortDir === 'asc' ? cmp : -cmp;
      })
    : [];

  const thCls =
    'px-2 py-2 text-left text-xs text-slate-400 font-medium cursor-pointer select-none hover:text-slate-200 transition whitespace-nowrap';

  const tdCls = 'px-2 py-2 text-xs';

  const renderTh = (key: SortKey, label: string) => (
    <th className={thCls} onClick={() => handleSort(key)}>
      <span className="inline-flex items-center gap-1">
        {label}
        <SortIcon active={sortKey === key} dir={sortDir} />
      </span>
    </th>
  );

  return (
    <CollapsibleSection
      storageKey={BATCH_QUALITY_EXPANDED_KEY}
      title="批次品質彙整"
      description="真問題數 + NaN 五數摘要 — 問題標的優先顯示"
      titleHeadingLevel="h3"
      expandedClassName="glass-panel rounded-xl p-5 border border-white/10 space-y-4"
      collapsedClassName="glass-panel rounded-xl border border-white/10 px-4 py-3"
      contentClassName="space-y-4"
      headerTrailing={(
        <button
          type="button"
          onClick={() => {
            void fetchQuality();
          }}
          disabled={isLoading}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 transition disabled:opacity-40"
          title="重新計算"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      )}
    >
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 rounded-lg bg-white/5 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-400/30 px-4 py-3 text-xs text-rose-200 flex items-center gap-2">
          <XCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {!isLoading && data && (
        <>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="rounded-lg bg-emerald-400/10 border border-emerald-400/20 px-3 py-2 text-center">
              <div className="text-lg font-semibold text-emerald-300">{data.pass_count}</div>
              <div className="text-slate-400">Pass</div>
            </div>
            <div className="rounded-lg bg-amber-400/10 border border-amber-400/20 px-3 py-2 text-center">
              <div className="text-lg font-semibold text-amber-300">{data.watch_count}</div>
              <div className="text-slate-400">Watch</div>
            </div>
            <div className="rounded-lg bg-rose-400/10 border border-rose-400/20 px-3 py-2 text-center">
              <div className="text-lg font-semibold text-rose-300">{data.reject_count}</div>
              <div className="text-slate-400">Reject</div>
            </div>
          </div>

          <CriteriaLegend />

          {sorted.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-4">無可分析的標的</div>
          ) : (
            <div className="overflow-auto rounded-xl border border-white/10 bg-white/[0.03] max-h-72">
              <table className="w-full min-w-[900px]">
                <thead className="sticky top-0 bg-[#0f1117]/90 backdrop-blur-sm border-b border-white/10">
                  <tr>
                    {renderTh('grade', '評級')}
                    {renderTh('symbol', 'Symbol')}
                    {renderTh('bar_count', 'Bar')}
                    {renderTh('feature_count', '特徵')}
                    {renderTh('real_problem', '真問題')}
                    {renderTh('nan_min', 'Min')}
                    {renderTh('nan_q1', 'Q1')}
                    {renderTh('nan_median', 'Med')}
                    {renderTh('nan_q3', 'Q3')}
                    {renderTh('nan_max', 'Max')}
                    {renderTh('nan_ratio_mean', '均†')}
                    {renderTh('nan_ratio_max', '峰†')}
                    {renderTh('constant_feature_count', '常數')}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sorted.map((s) => {
                    const q = resolveQuantiles(s);
                    return (
                      <tr key={s.symbol} className="hover:bg-white/5 transition">
                        <td className={tdCls}>
                          <GradeBadge grade={s.grade} />
                        </td>
                        <td className={`${tdCls} text-slate-200 font-mono font-medium`}>{s.symbol}</td>
                        <td
                          className={`${tdCls} ${
                            s.bar_count < 200
                              ? 'text-rose-300'
                              : s.bar_count < 500
                                ? 'text-amber-300'
                                : 'text-slate-300'
                          }`}
                        >
                          {s.bar_count.toLocaleString()}
                        </td>
                        <td className={`${tdCls} text-slate-400`}>{s.feature_count.toLocaleString()}</td>
                        <td
                          className={`${tdCls} ${
                            realProblemCount(s) > 5
                              ? 'text-rose-300'
                              : realProblemCount(s) > 0
                                ? 'text-amber-300'
                                : 'text-emerald-300'
                          }`}
                        >
                          {realProblemCount(s)}
                        </td>
                        <td className={`${tdCls} ${nanColor(q.min)}`}>{formatPct(q.min)}</td>
                        <td className={`${tdCls} ${nanColor(q.q1)}`}>{formatPct(q.q1)}</td>
                        <td className={`${tdCls} ${nanColor(q.median)} font-medium`}>{formatPct(q.median)}</td>
                        <td className={`${tdCls} ${nanColor(q.q3)}`}>{formatPct(q.q3)}</td>
                        <td className={`${tdCls} ${nanColor(q.max)}`}>{formatPct(q.max)}</td>
                        <td className={`${tdCls} text-slate-500`} title="含暖機僅參考">
                          {formatPct(s.nan_ratio_mean)}
                        </td>
                        <td className={`${tdCls} text-slate-500`} title="含暖機僅參考">
                          {formatPct(s.nan_ratio_max)}
                        </td>
                        <td
                          className={`${tdCls} ${s.constant_feature_count > 0 ? 'text-rose-300' : 'text-slate-400'}`}
                        >
                          {s.constant_feature_count}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="px-3 py-1 text-[10px] text-slate-600 border-t border-white/5">† 均/峰含暖機，僅參考</div>
            </div>
          )}

          <div className="text-xs text-slate-500">
            計算時間：{new Date(data.computed_at).toLocaleString('zh-TW')}
          </div>
        </>
      )}
    </CollapsibleSection>
  );
}
