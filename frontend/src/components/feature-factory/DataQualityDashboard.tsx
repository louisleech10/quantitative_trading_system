'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, Database } from 'lucide-react';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { DataQualityReport } from '@/lib/types';

type ProblemTab = 'mid_holes' | 'trailing_nans' | 'scattered_nans';

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
  const [problemTab, setProblemTab] = useState<ProblemTab>('mid_holes');

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
  const issueTotal =
    report.counts.mid_holes + report.counts.trailing_nans + report.counts.high_nan;
  const issueTone: 'good' | 'warn' | 'bad' =
    issueTotal === 0 ? 'good' : issueTotal < report.total_features * 0.05 ? 'warn' : 'bad';

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
          label="問題特徵數"
          value={formatNumber(issueTotal)}
          hint={`孔洞 ${report.counts.mid_holes} · 尾缺 ${report.counts.trailing_nans} · 高NaN ${report.counts.high_nan}`}
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
                  }}
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
                  }}
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

      {/* ── Problem feature lists ──────────────────────────────────────── */}
      {issueTotal > 0 && (
        <div className="glass-panel rounded-xl p-4 space-y-3">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-slate-200">問題特徵 Top {report.mid_holes.length + report.trailing_nans.length + report.scattered_nans.length > 0 ? 20 : 0}</h3>
            <span className="text-xs text-slate-400">優先檢查或排除的特徵</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <ProblemTabButton
              active={problemTab === 'mid_holes'}
              onClick={() => setProblemTab('mid_holes')}
              label={`中間孔洞 (${report.counts.mid_holes})`}
            />
            <ProblemTabButton
              active={problemTab === 'trailing_nans'}
              onClick={() => setProblemTab('trailing_nans')}
              label={`尾端缺失 (${report.counts.trailing_nans})`}
            />
            <ProblemTabButton
              active={problemTab === 'scattered_nans'}
              onClick={() => setProblemTab('scattered_nans')}
              label={`高 NaN / 全空 (${report.counts.high_nan})`}
            />
          </div>
          <ProblemTable report={report} tab={problemTab} />
        </div>
      )}
    </div>
  );
}

function ProblemTabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs border transition-colors ${
        active
          ? 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200'
          : 'border-white/10 text-slate-300 hover:border-white/20'
      }`}
    >
      {label}
    </button>
  );
}

function ProblemTable({ report, tab }: { report: DataQualityReport; tab: ProblemTab }) {
  if (tab === 'mid_holes') {
    if (report.mid_holes.length === 0) {
      return <div className="text-xs text-slate-500 py-3">無中間孔洞特徵。</div>;
    }
    return (
      <table className="w-full text-xs">
        <thead className="text-slate-400">
          <tr className="border-b border-white/10">
            <th className="text-left py-2 font-medium">特徵名稱</th>
            <th className="text-right py-2 font-medium">孔洞數量</th>
            <th className="text-right py-2 font-medium">孔洞比例（有效區間內）</th>
          </tr>
        </thead>
        <tbody className="text-slate-200">
          {report.mid_holes.map((f) => (
            <tr key={f.name} className="border-b border-white/5">
              <td className="py-1.5 font-mono text-[11px]">{f.name}</td>
              <td className="py-1.5 text-right">{formatNumber(f.hole_count)}</td>
              <td className="py-1.5 text-right text-amber-300">{formatPercent(f.hole_ratio, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (tab === 'trailing_nans') {
    if (report.trailing_nans.length === 0) {
      return <div className="text-xs text-slate-500 py-3">無尾端缺失特徵。</div>;
    }
    return (
      <table className="w-full text-xs">
        <thead className="text-slate-400">
          <tr className="border-b border-white/10">
            <th className="text-left py-2 font-medium">特徵名稱</th>
            <th className="text-right py-2 font-medium">尾端 NaN 長度（bars）</th>
          </tr>
        </thead>
        <tbody className="text-slate-200">
          {report.trailing_nans.map((f) => (
            <tr key={f.name} className="border-b border-white/5">
              <td className="py-1.5 font-mono text-[11px]">{f.name}</td>
              <td className="py-1.5 text-right text-rose-300">{formatNumber(f.trailing_length)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  // scattered_nans
  if (report.scattered_nans.length === 0) {
    return <div className="text-xs text-slate-500 py-3">無高 NaN 特徵。</div>;
  }
  return (
    <table className="w-full text-xs">
      <thead className="text-slate-400">
        <tr className="border-b border-white/10">
          <th className="text-left py-2 font-medium">特徵名稱</th>
          <th className="text-right py-2 font-medium">整體 NaN 比例</th>
        </tr>
      </thead>
      <tbody className="text-slate-200">
        {report.scattered_nans.map((f) => (
          <tr key={f.name} className="border-b border-white/5">
            <td className="py-1.5 font-mono text-[11px]">{f.name}</td>
            <td className="py-1.5 text-right text-rose-300">{formatPercent(f.nan_ratio, 2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
