'use client';

import { useEffect, useState } from 'react';
import { EventImportRejectedError, analyzeEventImport } from '@/lib/api';
import { recordImportReference } from '@/lib/eventBatchReferences';
import type { EventAnalyzeResponse, EventTableStatus } from '@/lib/types';

interface EventTablesPanelProps {
  importId?: string;
  /** 測試／外部注入用；不給則依 importId 自行呼叫後端 */
  data?: EventAnalyzeResponse | null;
}

function statusLabel(t: EventTableStatus | undefined): { ok: boolean; text: string } {
  if (!t) return { ok: false, text: '後端未回傳此表' };
  const status = t.capability_status ?? 'ok';
  if (status === 'ok') return { ok: true, text: 'ok' };
  const reason = (t.reason as string | null | undefined) ?? '';
  return { ok: false, text: `${status}${reason ? `：${reason}` : '（後端未給 reason）'}` };
}

function fmt(v: unknown, digits = 4): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') return Number.isFinite(v) ? v.toFixed(digits) : 'NaN';
  return String(v);
}

type HorizonRow = { mean?: number; median?: number; win_rate?: number; n?: number; n_effective?: number; ci?: unknown };

function ForwardReturnTable({ table }: { table: EventTableStatus }) {
  const st = statusLabel(table);
  if (!st.ok) {
    return (
      <p className="text-sm text-amber-200" data-testid="event-fwd-unavailable">
        事件後報酬表不可用：{st.text}
      </p>
    );
  }
  // 後端鍵：primary_macro[h]={mean,n_symbols}（symbol 等權）；sensitivity_micro[h]={mean,median,win_rate,n,n_effective,ci}（event 等權）
  const micro = (table.sensitivity_micro ?? {}) as Record<string, HorizonRow>;
  const macro = (table.primary_macro ?? {}) as Record<string, { mean?: number; n_symbols?: number }>;
  const horizons = ((table.horizons as number[] | undefined) ?? Object.keys(micro).map(Number)).map(String);
  if (horizons.length === 0) return <p className="text-sm text-slate-400">（表無資料）</p>;
  return (
    <table className="w-full text-xs" data-testid="event-fwd-table">
      <thead>
        <tr className="text-slate-400">
          <th className="text-left">horizon</th>
          <th className="text-right">macro mean</th>
          <th className="text-right">micro mean</th>
          <th className="text-right">median</th>
          <th className="text-right">win_rate</th>
          <th className="text-right">n</th>
          <th className="text-right">n_eff</th>
        </tr>
      </thead>
      <tbody>
        {horizons.map((h) => (
          <tr key={h} className="text-slate-200" data-testid={`event-fwd-row-${h}`}>
            <td>{h}</td>
            <td className="text-right font-mono">{fmt(macro[h]?.mean)}</td>
            <td className="text-right font-mono">{fmt(micro[h]?.mean)}</td>
            <td className="text-right font-mono">{fmt(micro[h]?.median)}</td>
            <td className="text-right font-mono">{fmt(micro[h]?.win_rate, 3)}</td>
            <td className="text-right font-mono">{fmt(micro[h]?.n, 0)}</td>
            <td className="text-right font-mono">{fmt(micro[h]?.n_effective, 2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DiscriminationTable({ table }: { table: EventTableStatus }) {
  const st = statusLabel(table);
  if (!st.ok) {
    return (
      <p className="text-sm text-amber-200" data-testid="event-disc-unavailable">
        正反例辨別表不可用：{st.text}
      </p>
    );
  }
  const o = (table.overall ?? {}) as Record<string, unknown>;
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-200" data-testid="event-disc-table">
      <dt className="text-slate-400">AUC</dt>
      <dd className="font-mono">{fmt(o.auc)}</dd>
      <dt className="text-slate-400">PR-AUC</dt>
      <dd className="font-mono">{fmt(o.pr_auc)}</dd>
      <dt className="text-slate-400">n（test）</dt>
      <dd className="font-mono">{fmt(o.n, 0)}</dd>
      <dt className="text-slate-400">AUC 落置亂帶內</dt>
      <dd className="font-mono">{String(o.auc_in_band ?? '—')}</dd>
    </dl>
  );
}

function AllBarsTable({ table }: { table: EventTableStatus | undefined }) {
  const st = statusLabel(table);
  if (!st.ok || !table) {
    return (
      <p className="text-sm text-amber-200" data-testid="event-allbars-unavailable">
        全 K 線驗證不可用：{st.text}
      </p>
    );
  }
  const counts = (table.counts ?? {}) as Record<string, unknown>;
  const o = (table.overall ?? {}) as Record<string, unknown>;
  const manifest = (table.manifest ?? {}) as Record<string, unknown>;
  const mapping = (table.signal_mapping ?? {}) as Record<string, unknown>;
  const overallOk = (o.capability_status ?? 'ok') === 'ok';
  return (
    <div className="space-y-1 text-xs text-slate-200" data-testid="event-allbars-table">
      {/* CODEX-R2-P2-01：estimand 揭露（rule／threshold／manifest）須可見，不得只有數值 */}
      <div className="rounded border border-slate-700/60 bg-slate-900/40 p-2 text-[11px] text-slate-300" data-testid="event-allbars-disclosure">
        {table.rule ? <p data-testid="event-allbars-rule">規則：{String(table.rule)}</p> : null}
        {table.estimand_note ? <p className="text-amber-200/90">{String(table.estimand_note)}</p> : null}
        {table.label_threshold_note ? <p className="text-amber-200/90" data-testid="event-allbars-threshold-note">{String(table.label_threshold_note)}</p> : null}
        <p className="text-slate-400">
          manifest：horizon {fmt(manifest.horizon_bars, 0)}／threshold {fmt(manifest.label_threshold, 4)}／direction {String(manifest.direction ?? '—')}／
          entry {String(manifest.entry_price_semantic ?? '—')}／k {fmt(manifest.decision_offset_bars, 0)}
          {mapping.n_signal_bars === undefined ? null : `／訊號根 ${fmt(mapping.n_signal_bars, 0)}（未對映 ${fmt(mapping.n_events_unmapped, 0)}）`}
        </p>
        {manifest.eligibility ? <p className="text-slate-500">eligibility：{String(manifest.eligibility)}</p> : null}
      </div>
      <p className="text-[11px] text-slate-400">
        n_total {fmt(counts.n_total, 0)}／eligible {fmt(counts.n_eligible, 0)}／labeled {fmt(counts.n_labeled, 0)}／tail_excluded {fmt(counts.n_tail_excluded, 0)}／unknown {fmt(counts.n_unknown, 0)}
      </p>
      {overallOk ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
          <dt className="text-slate-400">prevalence_full</dt>
          <dd className="font-mono">{fmt(o.prevalence_full)}</dd>
          <dt className="text-slate-400">prevalence_learn</dt>
          <dd className="font-mono">{fmt(o.prevalence_learn)}</dd>
          <dt className="text-slate-400">lift_threshold</dt>
          <dd className="font-mono">{fmt(o.lift_threshold)}</dd>
          <dt className="text-slate-400">precision</dt>
          <dd className="font-mono">{fmt(o.precision)}</dd>
          <dt className="text-slate-400">signal_frequency</dt>
          <dd className="font-mono">{fmt(o.signal_frequency, 5)}</dd>
        </dl>
      ) : (
        <p className="text-amber-200" data-testid="event-allbars-overall-unavailable">
          overall：{String(o.capability_status)}{o.reason ? `：${String(o.reason)}` : '（後端未給 reason）'}
        </p>
      )}
    </div>
  );
}

/**
 * GAP-3 B5.2：事件模式專屬表（事件後報酬表／正反例辨別表／全 K 線驗證）。
 * 只在事件模式掛載；後端 unavailable／not_computed 一律顯示原因，不顯示空白；前端不重算任何統計。
 */
export default function EventTablesPanel({ importId, data }: EventTablesPanelProps) {
  const [resp, setResp] = useState<EventAnalyzeResponse | null>(data ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data !== undefined) {
      setResp(data);
      return;
    }
    if (!importId) {
      setResp(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    analyzeEventImport(importId)
      .then((r) => {
        // GAP-3 UX Task 3.3：記下「這批真的被拿去分析過」——**成功之後**才記，不是選取當下。
        // 判準與其誠實邊界見 `@/lib/eventBatchReferences`（PENDING-RULING）。
        recordImportReference(importId);
        if (!cancelled) setResp(r);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof EventImportRejectedError ? `${err.payload.kind}：${err.payload.message}` : err instanceof Error ? err.message : '載入失敗');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [importId, data]);

  if (!importId && !resp) {
    return (
      <div className="glass-panel rounded-2xl border border-white/10 p-5" data-testid="event-tables-empty">
        <p className="text-sm text-slate-300">事件型兩表</p>
        <p className="text-xs text-slate-500 mt-1">尚未選擇事件批：請先在「數據準備」匯入事件，再於左側「從已匯入案例選事件」選一批。</p>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="glass-panel rounded-2xl border border-white/10 p-5" data-testid="event-tables-loading">
        <p className="text-sm text-slate-300">事件型兩表計算中…（對齊→去重→切分→bootstrap）</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="glass-panel rounded-2xl border border-rose-400/30 p-5 text-rose-200 text-sm" data-testid="event-tables-error">
        事件型兩表載入失敗：{error}
      </div>
    );
  }
  if (!resp) return null;
  const s = resp.summary as Record<string, unknown>;
  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4" data-testid="event-tables-panel">
      <div>
        <p className="text-sm text-slate-300">事件型兩表（批 {resp.import_id}）</p>
        <p className="text-[11px] text-slate-500">
          匯入 {fmt(s.n_input, 0)}／對齊 {fmt(s.n_aligned, 0)}／對齊失敗 {fmt(s.n_align_failures, 0)}／train {fmt(s.n_train, 0)}／test {fmt(s.n_test, 0)}／purge {fmt(s.n_purged, 0)}
        </p>
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-200 mb-1">事件後報酬表</p>
        <ForwardReturnTable table={resp.tables.event_forward_return_table} />
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-200 mb-1">正反例辨別表</p>
        <DiscriminationTable table={resp.tables.binary_discrimination_table} />
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-200 mb-1">全 K 線驗證（固定分母；rule＝事件成員）</p>
        <AllBarsTable table={resp.tables.all_bars_evaluation} />
      </div>
      {resp.align_failures.length > 0 && (
        <details className="text-[11px] text-slate-400">
          <summary>對齊失敗清單（{resp.align_failures.length}）</summary>
          <ul className="mt-1 space-y-0.5">
            {resp.align_failures.slice(0, 100).map((f) => (
              <li key={f.event_id} className="font-mono">{f.event_id}：{f.reason}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
