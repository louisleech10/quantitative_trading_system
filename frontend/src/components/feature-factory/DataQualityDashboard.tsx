'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Clock, Database, Search } from 'lucide-react';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { DataQualityReport, DataQualityRealProblemFeature } from '@/lib/types';

type ProblemTab = 'real_problem' | 'mid_holes' | 'trailing_nans' | 'scattered_nans';

interface DataQualityDashboardProps {
  taskId: string;
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}

function formatPercent(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`;
}

function formatTimestamp(value: string): string {
  if (!value) return '—';
  // Strip microseconds if ISO format
  if (value.includes('T')) {
    return value.split('.')[0].replace('T', ' ');
  }
  return value;
}

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint?: string;
  tone?: 'good' | 'warn' | 'bad' | 'neutral';
}

function SummaryCard({ icon, label, value, hint, tone = 'neutral' }: SummaryCardProps) {
  const toneCls: Record<string, string> = {
    good: 'border-emerald-400/30 text-emerald-200',
    warn: 'border-amber-400/30 text-amber-200',
    bad: 'border-rose-400/30 text-rose-200',
    neutral: 'border-white/10 text-slate-200',
  };
  return (
    <div className={`glass-panel rounded-xl border ${toneCls[tone]} p-4 flex flex-col gap-1`}>
      <div className="flex items-center gap-2 text-xs text-slate-400">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-xl font-semibold">{value}</div>
      {hint && <div className="text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export default function DataQualityDashboard({ taskId }: DataQualityDashboardProps) {
  const { browseDataQuality } = useFeatureFactory();
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [problemTab, setProblemTab] = useState<ProblemTab>('real_problem');
  const [problemSearch, setProblemSearch] = useState('');

  const handleTabChange = useCallback((tab: ProblemTab) => {
    setProblemTab(tab);
    setProblemSearch('');
  }, []);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    browseDataQuality(taskId)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '資料品質載入失敗');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [taskId, browseDataQuality]);

  const warmupChartData = useMemo(() => {
    if (!report) return [];
    return report.warmup_distribution.map((b) => ({
      bucket: b.bucket,
      count: b.count,
      ratio: b.ratio,
    }));
  }, [report]);

  const coverageChartData = useMemo(() => {
    if (!report) return [];
    return report.coverage_timeline.map((p) => ({
      index: p.index,
      timestamp: formatTimestamp(p.timestamp),
      coverage: p.coverage * 100,
    }));
  }, [report]);

  // P2: training-start tradeoff — for each candidate start index, coverage at
  // that row vs the % of samples retained if you trim everything before it.
  const tradeoffChartData = useMemo(() => {
    if (!report || report.total_timesteps === 0) return [];
    const total = report.total_timesteps;
    return report.coverage_timeline.map((p) => ({
      index: p.index,
      coverage: p.coverage * 100,
      retained: ((total - p.index) / total) * 100,
    }));
  }, [report]);

  // P3: feature-group (layer × tf) NaN breakdown — stacked warmup vs real.
  const groupChartData = useMemo(() => {
    if (!report?.group_breakdown) return [];
    return report.group_breakdown.map((g) => ({
      name: `${g.layer}·${g.tf}`,
      warmup_only: g.warmup_only,
      real_problem: g.real_problem,
      feature_count: g.feature_count,
      mean_nan: g.mean_nan_ratio * 100,
    }));
  }, [report]);

  if (loading) {
    return (
      <div className="glass-panel rounded-xl p-8 text-center space-y-3">
        <div className="text-slate-300">正在分析資料品質…</div>
        <div className="text-xs text-slate-500 leading-relaxed max-w-xl mx-auto">
          首次分析需實際掃描所有 parquet 欄位以偵測 IEEE-754 NaN（parquet metadata 不算浮點 NaN）。
          結果會自動快取到 task 目錄，下次開啟此 tab 將秒開。
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel rounded-xl p-6 border border-rose-400/30 flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-rose-300 flex-shrink-0 mt-0.5" />
        <div>
          <div className="text-sm text-rose-200 font-medium">資料品質載入失敗</div>
          <div className="text-xs text-slate-400 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  if (!report || report.total_features === 0) {
    return (
      <div className="glass-panel rounded-xl p-8 text-center text-slate-400">
        無可用特徵資料。
      </div>
    );
  }

  const recommendationTone: 'good' | 'warn' | 'bad' =
    report.warmup_loss_ratio < 0.05 ? 'good' : report.warmup_loss_ratio < 0.2 ? 'warn' : 'bad';
  const coverageTone: 'good' | 'warn' | 'bad' =
    report.min_coverage >= 0.95 ? 'good' : report.min_coverage >= 0.8 ? 'warn' : 'bad';
  // "Real" problems exclude benign leading warmup. Fall back to legacy framing
  // for pre-dq_v2 reports that lack the split fields.
  const realProblem =
    report.counts.real_problem ??
    report.counts.mid_holes + report.counts.trailing_nans + report.counts.high_nan;
  const warmupBenign = report.counts.warmup_only_high_nan ?? 0;
  const issueTone: 'good' | 'warn' | 'bad' =
    realProblem === 0 ? 'good' : realProblem < report.total_features * 0.05 ? 'warn' : 'bad';

  return (
    <div className="space-y-4">
      {/* ── Summary cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryCard
          icon={<Database className="h-4 w-4" />}
          label="特徵總數"
          value={formatNumber(report.total_features)}
          hint={`${formatNumber(report.total_timesteps)} 個時間步`}
        />
        <SummaryCard
          icon={<Clock className="h-4 w-4" />}
          label="推薦訓練起點 (P95)"
          value={`索引 ${formatNumber(report.recommended_start_index)}`}
          hint={`${formatTimestamp(report.recommended_start_timestamp)} · 損失 ${formatPercent(report.warmup_loss_ratio)} 樣本`}
          tone={recommendationTone}
        />
        <SummaryCard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="最低截面覆蓋率"
          value={formatPercent(report.min_coverage)}
          hint={`發生於 ${formatTimestamp(report.min_coverage_timestamp)}`}
          tone={coverageTone}
        />
        <SummaryCard
          icon={<AlertTriangle className="h-4 w-4" />}
          label="真問題特徵數"
          value={formatNumber(realProblem)}
          hint={`NaN ≥ 5% 且有中間孔洞，或整列全空　|　另有 ${formatNumber(warmupBenign)} 良性 warmup（trim 即可）、孔洞 ${report.counts.mid_holes}、尾缺 ${report.counts.trailing_nans}`}
          tone={issueTone}
        />
      </div>

      {report.is_clean && (
        <div className="glass-panel rounded-xl p-4 border border-emerald-400/30 flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-300" />
          <div className="text-sm text-emerald-200">
            資料完整：無 warmup、無孔洞、無尾端缺失，可直接全量訓練。
          </div>
        </div>
      )}

      {/* ── Charts row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Warmup distribution */}
        <div className="glass-panel rounded-xl p-4 space-y-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Warmup 長度分布</h3>
            <span className="text-xs text-slate-400">
              最大 {formatNumber(report.max_warmup)} · P95 {formatNumber(report.p95_warmup)}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            每個特徵需要多少 bar 才開始輸出有效值（rolling lookback 等造成）。
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={warmupChartData} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="bucket" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => formatNumber(v as number)} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#e2e8f0',
                  }}
                  labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
                  itemStyle={{ color: '#cbd5e1' }}
                  formatter={(value: number, _name, item: { payload?: { ratio: number } }) => [
                    `${formatNumber(value)} 個 (${formatPercent(item?.payload?.ratio ?? 0)})`,
                    '特徵數',
                  ]}
                />
                <Bar dataKey="count" fill="#22d3ee" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Coverage timeline */}
        <div className="glass-panel rounded-xl p-4 space-y-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">截面覆蓋率時間序列</h3>
            <span className="text-xs text-slate-400">
              每個 bar 中可用特徵的比例
            </span>
          </div>
          <p className="text-xs text-slate-400">
            低點代表該時段有大量特徵 NaN（exchange 停盤、資料源異常或 warmup 期）。
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={coverageChartData} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis
                  dataKey="index"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickFormatter={(v) => formatNumber(v as number)}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#e2e8f0',
                  }}
                  labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
                  itemStyle={{ color: '#cbd5e1' }}
                  labelFormatter={(label, items) => {
                    const p = items?.[0]?.payload as { timestamp?: string } | undefined;
                    return p?.timestamp ? `索引 ${label} · ${p.timestamp}` : `索引 ${label}`;
                  }}
                  formatter={(v: number) => [`${v.toFixed(2)}%`, '覆蓋率']}
                />
                {report.recommended_start_index > 0 && (
                  <ReferenceLine
                    x={report.recommended_start_index}
                    stroke="#fbbf24"
                    strokeDasharray="3 3"
                    label={{
                      value: '推薦起點',
                      fill: '#fbbf24',
                      fontSize: 10,
                      position: 'insideTopRight',
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="coverage"
                  stroke="#22d3ee"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Training-start tradeoff ────────────────────────────────────── */}
      {tradeoffChartData.length > 0 && (
        <div className="glass-panel rounded-xl p-4 space-y-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">訓練起點權衡</h3>
            <span className="text-xs text-slate-400">覆蓋率 vs 保留樣本</span>
          </div>
          <p className="text-xs text-slate-400">
            從某索引起訓練：覆蓋率（左軸，該起點可用特徵比例）與保留樣本（右軸）此消彼長。
            黃線為 P95 推薦起點。
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={tradeoffChartData} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis
                  dataKey="index"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickFormatter={(v) => formatNumber(v as number)}
                />
                <YAxis
                  yAxisId="left"
                  stroke="#22d3ee"
                  fontSize={11}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#a78bfa"
                  fontSize={11}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#e2e8f0',
                  }}
                  labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
                  itemStyle={{ color: '#cbd5e1' }}
                  labelFormatter={(label) => `從索引 ${formatNumber(label as number)} 起訓練`}
                  formatter={(v: number, name: string) => [
                    `${v.toFixed(1)}%`,
                    name === 'coverage' ? '覆蓋率' : '保留樣本',
                  ]}
                />
                <Legend
                  formatter={(v) => (v === 'coverage' ? '覆蓋率' : '保留樣本')}
                  wrapperStyle={{ fontSize: 11 }}
                />
                {report.recommended_start_index > 0 && (
                  <ReferenceLine
                    yAxisId="left"
                    x={report.recommended_start_index}
                    stroke="#fbbf24"
                    strokeDasharray="3 3"
                  />
                )}
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="retained"
                  stroke="#a78bfa"
                  fill="rgba(167,139,250,0.12)"
                  strokeWidth={1.5}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="coverage"
                  stroke="#22d3ee"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Feature-group (layer × tf) breakdown ───────────────────────── */}
      {groupChartData.length > 0 && (
        <div className="glass-panel rounded-xl p-4 space-y-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">特徵群組 NaN 分解（layer × 時框）</h3>
            <span className="text-xs text-slate-400">良性 warmup vs 真問題</span>
          </div>
          <p className="text-xs text-slate-400">
            一眼看出哪個 layer × 時框貢獻最多 NaN。長週期 12h 的 L3/L2 通常是 warmup（良性）大宗。
          </p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={groupChartData} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => formatNumber(v as number)} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#e2e8f0',
                  }}
                  labelStyle={{ color: '#e2e8f0', marginBottom: 4 }}
                  itemStyle={{ color: '#cbd5e1' }}
                  formatter={(v: number, name: string) => [
                    formatNumber(v),
                    name === 'warmup_only' ? '良性 warmup' : '真問題',
                  ]}
                  labelFormatter={(label, items) => {
                    const p = items?.[0]?.payload as { feature_count?: number; mean_nan?: number } | undefined;
                    return p
                      ? `${label}　特徵 ${formatNumber(p.feature_count ?? 0)} · 平均NaN ${(p.mean_nan ?? 0).toFixed(1)}%`
                      : String(label);
                  }}
                />
                <Legend
                  formatter={(v) => (v === 'warmup_only' ? '良性 warmup' : '真問題')}
                  wrapperStyle={{ fontSize: 11 }}
                />
                <Bar dataKey="warmup_only" stackId="g" fill="#475569" radius={[0, 0, 0, 0]} />
                <Bar dataKey="real_problem" stackId="g" fill="#fb7185" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Problem feature lists ──────────────────────────────────────── */}
      {(realProblem + report.counts.mid_holes + report.counts.trailing_nans + report.counts.high_nan) > 0 && (
        <div className="glass-panel rounded-xl p-4 space-y-3">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">問題特徵</h3>
            <span className="text-xs text-slate-400">可搜尋 · 可排序 · 完整清單</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ProblemTabButton
              active={problemTab === 'real_problem'}
              onClick={() => handleTabChange('real_problem')}
              label={`真問題 (${realProblem})`}
              tone="bad"
            />
            <ProblemTabButton
              active={problemTab === 'mid_holes'}
              onClick={() => handleTabChange('mid_holes')}
              label={`中間孔洞 (${report.counts.mid_holes})`}
            />
            <ProblemTabButton
              active={problemTab === 'trailing_nans'}
              onClick={() => handleTabChange('trailing_nans')}
              label={`尾端缺失 (${report.counts.trailing_nans})`}
            />
            <ProblemTabButton
              active={problemTab === 'scattered_nans'}
              onClick={() => handleTabChange('scattered_nans')}
              label={`高 NaN / 全空 (${report.counts.high_nan})`}
            />
            <div className="ml-auto flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5">
              <Search className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
              <input
                type="text"
                placeholder="搜尋特徵名稱…"
                value={problemSearch}
                onChange={(e) => setProblemSearch(e.target.value)}
                className="bg-transparent text-xs text-slate-200 placeholder-slate-500 outline-none w-48"
              />
            </div>
          </div>
          <ProblemTable report={report} tab={problemTab} search={problemSearch} />
        </div>
      )}
    </div>
  );
}

function ProblemTabButton({ active, onClick, label, tone }: { active: boolean; onClick: () => void; label: string; tone?: 'bad' }) {
  const activeCls = tone === 'bad'
    ? 'bg-rose-400/20 border-rose-300/40 text-rose-200'
    : 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200';
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs border transition-colors ${
        active ? activeCls : 'border-white/10 text-slate-300 hover:border-white/20'
      }`}
    >
      {label}
    </button>
  );
}

// ── Virtual-scroll table ────────────────────────────────────────────────────
const ROW_H = 30;        // px per row
const VISIBLE_ROWS = 16; // rows visible in the viewport
const BUFFER = 8;        // extra rows rendered above/below viewport

interface ColDef<T> {
  key: keyof T & string;
  label: string;
  align?: 'left' | 'right' | 'center';
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => number | string;
}

function VirtualTable<T extends { name: string }>({
  rows,
  cols,
  emptyMsg,
  note,
}: {
  rows: T[];
  cols: ColDef<T>[];
  emptyMsg: string;
  note?: string;
}) {
  const [sortKey, setSortKey] = useState<string>(cols[1]?.key ?? '');
  const [sortDir, setSortDir] = useState<1 | -1>(-1);
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sorted = useMemo(() => {
    const col = cols.find((c) => c.key === sortKey);
    if (!col?.sortValue) return rows;
    return [...rows].sort((a, b) => {
      const av = col.sortValue!(a);
      const bv = col.sortValue!(b);
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir;
      return String(av).localeCompare(String(bv)) * sortDir;
    });
  }, [rows, sortKey, sortDir, cols]);

  const totalH = sorted.length * ROW_H;
  const startIdx = Math.max(0, Math.floor(scrollTop / ROW_H) - BUFFER);
  const endIdx = Math.min(sorted.length, startIdx + VISIBLE_ROWS + BUFFER * 2);
  const visibleRows = sorted.slice(startIdx, endIdx);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === 1 ? -1 : 1));
    else { setSortKey(key); setSortDir(-1); }
  };

  if (rows.length === 0) return <div className="text-xs text-slate-500 py-3">{emptyMsg}</div>;

  return (
    <div className="space-y-2">
      {note && <p className="text-xs text-slate-400">{note}</p>}
      <div className="text-xs text-slate-500">{formatNumber(rows.length)} 筆</div>
      <div className="rounded-lg border border-white/8 overflow-hidden">
        {/* sticky header */}
        <table className="w-full text-xs table-fixed">
          <thead className="bg-slate-900/80 text-slate-400">
            <tr>
              {cols.map((c) => (
                <th
                  key={c.key}
                  onClick={() => c.sortValue && toggleSort(c.key)}
                  className={`py-2 px-2 font-medium select-none ${c.sortValue ? 'cursor-pointer hover:text-slate-200' : ''} ${c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left'}`}
                >
                  <span className="inline-flex items-center gap-0.5">
                    {c.label}
                    {c.sortValue && sortKey === c.key
                      ? sortDir === -1
                        ? <ChevronDown className="h-3 w-3" />
                        : <ChevronUp className="h-3 w-3" />
                      : null}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
        </table>
        {/* virtual body */}
        <div
          ref={containerRef}
          style={{ height: Math.min(totalH, VISIBLE_ROWS * ROW_H), overflowY: 'auto' }}
          onScroll={(e) => setScrollTop((e.target as HTMLDivElement).scrollTop)}
          className="relative"
        >
          <div style={{ height: totalH, position: 'relative' }}>
            <table
              className="w-full text-xs table-fixed"
              style={{ position: 'absolute', top: startIdx * ROW_H, width: '100%' }}
            >
              <tbody className="text-slate-200">
                {visibleRows.map((row) => (
                  <tr key={row.name} className="border-t border-white/5 hover:bg-white/3">
                    {cols.map((c) => (
                      <td
                        key={c.key}
                        className={`py-1.5 px-2 ${c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left'}`}
                      >
                        {c.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function RealProblemKindBadge({ kind }: { kind: DataQualityRealProblemFeature['kind'] }) {
  return kind === 'all_nan'
    ? <span className="rounded px-1.5 py-0.5 text-[10px] bg-rose-400/20 text-rose-300 border border-rose-300/20">全空</span>
    : <span className="rounded px-1.5 py-0.5 text-[10px] bg-amber-400/20 text-amber-300 border border-amber-300/20">高NaN+孔洞</span>;
}

function ProblemTable({ report, tab, search }: { report: DataQualityReport; tab: ProblemTab; search: string }) {
  const q = search.trim().toLowerCase();

  if (tab === 'real_problem') {
    const all = report.real_problem_features ?? [];
    const rows = q ? all.filter((f) => f.name.toLowerCase().includes(q)) : all;
    const cols: ColDef<typeof rows[0]>[] = [
      { key: 'name', label: '特徵名稱', render: (f) => <span className="font-mono text-[11px]">{f.name}</span>, sortValue: (f) => f.name },
      { key: 'kind', label: '類型', align: 'center', render: (f) => <RealProblemKindBadge kind={f.kind} />, sortValue: (f) => f.kind },
      { key: 'nan_ratio', label: 'NaN 比例', align: 'right', render: (f) => <span className="text-rose-300">{formatPercent(f.nan_ratio, 2)}</span>, sortValue: (f) => f.nan_ratio },
      { key: 'hole_count', label: '孔洞數（bars）', align: 'right', render: (f) => <span className="text-amber-300">{f.hole_count > 0 ? formatNumber(f.hole_count) : '—'}</span>, sortValue: (f) => f.hole_count },
    ];
    return <VirtualTable rows={rows} cols={cols} emptyMsg={q ? '無符合搜尋的特徵。' : '無真問題特徵。'} note="真問題 = NaN ≥ 5% 且有中間孔洞，或整列全空。不含小孔洞（NaN < 5%）與尾端缺失。" />;
  }

  if (tab === 'mid_holes') {
    const all = report.mid_holes;
    const rows = q ? all.filter((f) => f.name.toLowerCase().includes(q)) : all;
    const cols: ColDef<typeof rows[0]>[] = [
      { key: 'name', label: '特徵名稱', render: (f) => <span className="font-mono text-[11px]">{f.name}</span>, sortValue: (f) => f.name },
      { key: 'hole_count', label: '孔洞數量', align: 'right', render: (f) => <span>{formatNumber(f.hole_count)}</span>, sortValue: (f) => f.hole_count },
      { key: 'hole_ratio', label: '孔洞比例（有效區間）', align: 'right', render: (f) => <span className="text-amber-300">{formatPercent(f.hole_ratio, 2)}</span>, sortValue: (f) => f.hole_ratio },
    ];
    return <VirtualTable rows={rows} cols={cols} emptyMsg={q ? '無符合搜尋的特徵。' : '無中間孔洞特徵。'} />;
  }

  if (tab === 'trailing_nans') {
    const all = report.trailing_nans;
    const rows = q ? all.filter((f) => f.name.toLowerCase().includes(q)) : all;
    const cols: ColDef<typeof rows[0]>[] = [
      { key: 'name', label: '特徵名稱', render: (f) => <span className="font-mono text-[11px]">{f.name}</span>, sortValue: (f) => f.name },
      { key: 'trailing_length', label: '尾端 NaN 長度（bars）', align: 'right', render: (f) => <span className="text-rose-300">{formatNumber(f.trailing_length)}</span>, sortValue: (f) => f.trailing_length },
    ];
    return <VirtualTable rows={rows} cols={cols} emptyMsg={q ? '無符合搜尋的特徵。' : '無尾端缺失特徵。'} />;
  }

  // scattered_nans
  const all = report.scattered_nans;
  const rows = q ? all.filter((f) => f.name.toLowerCase().includes(q)) : all;
  const cols: ColDef<typeof rows[0]>[] = [
    { key: 'name', label: '特徵名稱', render: (f) => <span className="font-mono text-[11px]">{f.name}</span>, sortValue: (f) => f.name },
    { key: 'nan_ratio', label: '整體 NaN 比例', align: 'right', render: (f) => <span className="text-rose-300">{formatPercent(f.nan_ratio, 2)}</span>, sortValue: (f) => f.nan_ratio },
  ];
  return <VirtualTable rows={rows} cols={cols} emptyMsg={q ? '無符合搜尋的特徵。' : '無高 NaN 特徵。'} note="含良性 warmup（純前端 warmup 期），真正問題請看「真問題」tab。" />;
}
