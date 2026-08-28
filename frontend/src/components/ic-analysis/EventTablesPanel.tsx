'use client';

import { useEffect, useState } from 'react';
import { EventImportRejectedError, analyzeEventImport } from '@/lib/api';
import { recordImportReference } from '@/lib/eventBatchReferences';
import { metricTooltip } from '@/lib/eventMetricsGlossary';
import type { EventAnalyzeResponse, EventTableStatus } from '@/lib/types';

interface EventTablesPanelProps {
  importId?: string;
  /**
   * GAP-3 UX Task 4.2：要算哪些 horizon（來自 IC 設定面板之「Horizon 多選」）。
   *
   * 🔴 不傳 ⇒ 後端用預設 `[1, 2, 4]`（`event_import_models.py:123`）——B7 之前
   * 這裡**恆不傳**，於是使用者在 IC 面板選的 horizon 對事件後報酬表完全沒作用。
   * 🔴 **只改要算哪些 horizon**，不改每個 horizon 之計算式、不改 `n_eff` 之定義。
   * 🔴 空／重複／非正整數一律**不傳**（fail-closed 回後端預設，不送出無意義的請求）。
   */
  horizons?: number[];
  /** 測試／外部注入用；不給則依 importId 自行呼叫後端 */
  data?: EventAnalyzeResponse | null;
}

/** 送給後端之 horizon 集合；不合法（空／重複後為空／非正整數）⇒ `undefined`＝用後端預設。 */
export function sanitizeHorizons(horizons: number[] | undefined): number[] | undefined {
  if (!horizons) return undefined;
  const clean = [...new Set(horizons)]
    .filter((h) => Number.isInteger(h) && h > 0)
    .sort((a, b) => a - b);
  return clean.length > 0 ? clean : undefined;
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

/**
 * GAP-3 UX Task 5.2：表頭 ＋ tooltip（文案唯一來源＝Task 5.0 之 glossary，經 `metricTooltip`）。
 *
 * 🔴 只加 tooltip，**不改標籤字面、不改數值與版面**（Task 5.2 邊界）。
 * `title` 屬性為原生 tooltip：不需額外元件、不改排版，且測試可直接讀 `title` 斷言（執行期，非原始碼形狀）。
 */
function MetricLabel({ metricKey, label }: { metricKey: string; label: string }) {
  return (
    <span title={metricTooltip(metricKey)} data-testid={`event-metric-${metricKey}`}>
      {label}
    </span>
  );
}

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
    <>
    {/* 全批 macro／micro（既有）。🔴 Task 7.5 之三組**另外**垂直排在下方——
        保留這張是因為 `primary_macro`（symbol 等權）是批次層統計，不屬於任何一組。 */}
    <table className="w-full text-xs" data-testid="event-fwd-table">
      <thead>
        <tr className="text-slate-400">
          <th className="text-left"><MetricLabel metricKey="horizon" label="horizon" /></th>
          <th className="text-right"><MetricLabel metricKey="macro_mean" label="macro mean" /></th>
          <th className="text-right"><MetricLabel metricKey="micro_mean" label="micro mean" /></th>
          <th className="text-right"><MetricLabel metricKey="median" label="median" /></th>
          <th className="text-right"><MetricLabel metricKey="win_rate" label="win_rate" /></th>
          <th className="text-right"><MetricLabel metricKey="n" label="n" /></th>
          <th className="text-right"><MetricLabel metricKey="n_eff" label="n_eff" /></th>
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
    <ByLabelTables table={table} />
    </>
  );
}

/**
 * GAP-3 UX **Task 7.5 ⑪** — 事件後報酬表之**正／反／全體三組，垂直排列**。
 *
 * 🔴 資料一律讀 `strata.by_label`（後端 Task 7.5 之產出），**不是** `sensitivity_micro`
 *    ——後端全綠而前端仍顯示舊的單一組，就是「靜默失效」（SPEC ⑪ 之病因）。
 * 🔴 `all` 為 `not_computed` 時**顯示其 `reason`，不顯示空表**；reason 字面由後端契約給，前端不寫死。
 * 🔴 分組**不改變**任何統計定義：`n_eff`／bootstrap 都是後端算的，前端一格都不重算。
 */
/**
 * 三組之顯示順序與其 glossary 鍵。
 * 🔴 **標題文字不寫在這裡**——`metricKey` 指向 `event_metrics_glossary.json` 之條目，
 *    tooltip 由 Task 5.2 之 `metricTooltip()` 當場導出（Task 7.5「須同步 (c)②」：
 *    新增之分組標籤與 `not_computed` 狀態文字須先登記 glossary，否則 5.2 無可比對來源）。
 */
const BY_LABEL_GROUPS: readonly { key: string; label: string; metricKey: string }[] = [
  { key: 'positive', label: '正例組（label = 1）', metricKey: 'by_label_positive' },
  { key: 'negative', label: '反例組（label = 0）', metricKey: 'by_label_negative' },
  { key: 'all', label: '全體組（正＋反）', metricKey: 'by_label_all' },
];

type GroupBlock = Record<string, HorizonRow> | { status?: string; reason?: string };

function ByLabelTables({ table }: { table: EventTableStatus }) {
  const strata = (table.strata ?? {}) as Record<string, unknown>;
  const byLabel = strata.by_label as Record<string, GroupBlock> | undefined;
  if (!byLabel) {
    return (
      <p className="text-sm text-amber-200" data-testid="event-fwd-by-label-missing">
        後端未回傳 strata.by_label（正／反／全體三組）——請確認後端版本
      </p>
    );
  }
  const horizons = ((table.horizons as number[] | undefined) ?? []).map(String);
  return (
    <div className="mt-3 space-y-3" data-testid="event-fwd-by-label">
      {BY_LABEL_GROUPS.map(({ key, label, metricKey }) => {
        const group = byLabel[key];
        const status = (group as { status?: string })?.status;
        const reason = (group as { reason?: string })?.reason;
        return (
          <div key={key} data-testid={`event-fwd-group-${key}`}>
            <p className="text-xs text-slate-300">
              <MetricLabel metricKey={metricKey} label={label} />
            </p>
            {status ? (
              // not_computed ⇒ 顯示 reason（不是空表）；reason 之白話同樣掛 glossary
              <p className="text-xs text-amber-200" data-testid={`event-fwd-group-${key}-not-computed`}>
                {status}：
                {reason ? <MetricLabel metricKey={reason} label={reason} /> : '（後端未給 reason）'}
              </p>
            ) : (
              <table className="w-full text-xs" data-testid={`event-fwd-group-${key}-table`}>
                <thead>
                  <tr className="text-slate-400">
                    <th className="text-left"><MetricLabel metricKey="horizon" label="horizon" /></th>
                    <th className="text-right"><MetricLabel metricKey="micro_mean" label="mean" /></th>
                    <th className="text-right"><MetricLabel metricKey="median" label="median" /></th>
                    <th className="text-right"><MetricLabel metricKey="win_rate" label="win_rate" /></th>
                    <th className="text-right"><MetricLabel metricKey="n" label="n" /></th>
                    <th className="text-right"><MetricLabel metricKey="n_eff" label="n_eff" /></th>
                  </tr>
                </thead>
                <tbody>
                  {horizons.map((h) => {
                    const row = (group as Record<string, HorizonRow>)[h];
                    return (
                      <tr key={h} className="text-slate-200" data-testid={`event-fwd-group-${key}-row-${h}`}>
                        <td>{h}</td>
                        <td className="text-right font-mono">{fmt(row?.mean)}</td>
                        <td className="text-right font-mono">{fmt(row?.median)}</td>
                        <td className="text-right font-mono">{fmt(row?.win_rate, 3)}</td>
                        <td className="text-right font-mono">{fmt(row?.n, 0)}</td>
                        <td className="text-right font-mono">{fmt(row?.n_effective, 2)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
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
      <dt className="text-slate-400"><MetricLabel metricKey="auc" label="AUC" /></dt>
      <dd className="font-mono">{fmt(o.auc)}</dd>
      <dt className="text-slate-400"><MetricLabel metricKey="pr_auc" label="PR-AUC" /></dt>
      <dd className="font-mono">{fmt(o.pr_auc)}</dd>
      <dt className="text-slate-400"><MetricLabel metricKey="n_test" label="n（test）" /></dt>
      <dd className="font-mono">{fmt(o.n, 0)}</dd>
      <dt className="text-slate-400"><MetricLabel metricKey="auc_in_band" label="AUC 落置亂帶內" /></dt>
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
        <MetricLabel metricKey="n_total" label="n_total" /> {fmt(counts.n_total, 0)}／
        <MetricLabel metricKey="n_eligible" label="eligible" /> {fmt(counts.n_eligible, 0)}／
        <MetricLabel metricKey="n_labeled" label="labeled" /> {fmt(counts.n_labeled, 0)}／
        <MetricLabel metricKey="tail_excluded" label="tail_excluded" /> {fmt(counts.n_tail_excluded, 0)}／
        <MetricLabel metricKey="n_unknown" label="unknown" /> {fmt(counts.n_unknown, 0)}
      </p>
      {overallOk ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
          <dt className="text-slate-400"><MetricLabel metricKey="prevalence_full" label="prevalence_full" /></dt>
          <dd className="font-mono">{fmt(o.prevalence_full)}</dd>
          <dt className="text-slate-400"><MetricLabel metricKey="prevalence_learn" label="prevalence_learn" /></dt>
          <dd className="font-mono">{fmt(o.prevalence_learn)}</dd>
          <dt className="text-slate-400"><MetricLabel metricKey="lift_threshold" label="lift_threshold" /></dt>
          <dd className="font-mono">{fmt(o.lift_threshold)}</dd>
          <dt className="text-slate-400"><MetricLabel metricKey="precision" label="precision" /></dt>
          <dd className="font-mono">{fmt(o.precision)}</dd>
          <dt className="text-slate-400"><MetricLabel metricKey="signal_frequency" label="signal_frequency" /></dt>
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
export default function EventTablesPanel({ importId, horizons, data }: EventTablesPanelProps) {
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
    // Task 4.2：把使用者在 IC 面板選的 horizon 集合真的送出去（此前恆送 `{}`）。
    const wanted = sanitizeHorizons(horizons);
    analyzeEventImport(importId, wanted ? { horizons: wanted } : {})
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
    // `horizons` 以正規化後之字面入依賴，避免每次 render 之新陣列參考造成重打 API
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importId, data, JSON.stringify(sanitizeHorizons(horizons) ?? null)]);

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
