'use client';

/**
 * GAP-3 UX **Task 7.6** — IC 分析頁之「批次事實欄**唯讀揭露**」＋「**分析參數**可設定」。
 *
 * 🔴 **兩類刻意分開**（SPEC L3073–3080 之三分表）：
 *   - **批次事實欄** `{scenario, control_kind, direction, t0, label}` ⇒ **唯讀**，
 *     其 DOM 節點**不得有任何可輸入控制項**（驗收③）。
 *   - **分析參數** `event_label_spec` 之四欄 ⇒ **可設定**，且**只作用於本次分析、不回寫事件批**（驗收⑥）。
 *
 * 🔴 文案與 `/search` 之匯出面板**共用同一 exported formatter registry**
 *    （`EVENT_FIELD_FORMATTERS`），但**欄集各自選取**——本頁用 `IC_BATCH_FACT_FIELDS`，
 *    `/search` 用 `SEARCH_DISCLOSURE_FIELDS`，兩者不相等（Task 7.3 邊界②）。
 * 🔴 `horizon_bars` 初始值＝**字面常數 `1`**，**禁**以該批之
 *    `label_definition.window.horizon_bars` 種子化（§D-3′-a 已裁定該欄為 D-7 深度宣告）。
 * 🔴 報酬語意三元組之可操作集合**沿用** Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`
 *    （路徑鍵 `/ic-analysis`），**不另創第四種機制**。
 */

import { useEffect, useState } from 'react';
import { getEventImport } from '@/lib/api';
import {
  EVENT_FIELD_FORMATTERS,
  IC_BATCH_FACT_FIELDS,
  type EventFieldKey,
} from '@/lib/eventFieldFormatters';
import { clampDecisionOffset, decisionOffsetRange, dimOptions } from '@/lib/eventDimensions';
import type { EventImportDetail, ICAnalysisConfig } from '@/lib/types';

/** 分析參數之 `horizon_bars` 初始值——**字面常數**，不由任何落檔欄種子化。 */
export const IC_ANALYSIS_INITIAL_HORIZON_BARS = 1;

interface Props {
  importId?: string;
  labelSpec: ICAnalysisConfig['event_label_spec'];
  onChangeLabelSpec: (next: NonNullable<ICAnalysisConfig['event_label_spec']>) => void;
  /** 測試注入；不給則依 `importId` 自行查 detail。 */
  detail?: EventImportDetail | null;
}

/** 由批次事實欄產生該欄之白話字串；欄集之外的欄一律不顯示（各頁只選自己的欄集）。 */
function factLine(field: EventFieldKey, detail: EventImportDetail): string {
  const f = detail.batch_facts;
  switch (field) {
    case 'scenario':
      return EVENT_FIELD_FORMATTERS.scenario(f.scenario ?? '（未宣告）');
    case 'control_kind':
      // 🔴 `null` 有兩種意思 ⇒ 由 `control_kind_values` 分辨，不讓「混批」被讀成「沒宣告」。
      if (f.control_kind !== null) return EVENT_FIELD_FORMATTERS.control_kind(f.control_kind);
      return detail.batch_fact_notes.control_kind_values.length > 1
        ? `control_kind ＝ 批內有 ${detail.batch_fact_notes.control_kind_values.length} 種`
          + `（${detail.batch_fact_notes.control_kind_values.join('、')}）——`
          + '報酬表之全體組會標為 mixed_control_kind_in_batch，不取多數決'
        : EVENT_FIELD_FORMATTERS.control_kind('（未宣告）');
    case 'label_origin':
      // 🔴 D1.6：formatter 自己處理 `null`（顯示「（未宣告）」），此處**不補值**。
      //    與 `control_kind` 不同：本欄之混值不需另設 notes 欄——契約對
      //    scenario ∈ {A,B,two_stage} 條件必填且批內同質，混值批在匯入層就被擋。
      return EVENT_FIELD_FORMATTERS.label_origin(f.label_origin);
    case 'direction':
      return EVENT_FIELD_FORMATTERS.direction(f.direction ?? '（未宣告）');
    case 't0':
      return EVENT_FIELD_FORMATTERS.t0(f.t0);
    case 'label':
      return EVENT_FIELD_FORMATTERS.label(
        f.label.map((r) => ({ event_id: r.event_id, label: r.label === 1 ? 1 : 0 })),
      );
    default:
      return '';
  }
}

export default function EventBatchDisclosurePanel({
  importId, labelSpec, onChangeLabelSpec, detail: injected,
}: Props) {
  const [detail, setDetail] = useState<EventImportDetail | null>(injected ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (injected !== undefined) { setDetail(injected); return; }
    if (!importId) { setDetail(null); return; }
    let cancelled = false;
    getEventImport(importId)
      .then((d) => { if (!cancelled) { setDetail(d); setError(null); } })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '讀取事件批失敗');
      });
    return () => { cancelled = true; };
  }, [importId, injected]);

  const spec = labelSpec ?? { horizon_bars: IC_ANALYSIS_INITIAL_HORIZON_BARS };
  const kRange = decisionOffsetRange('/ic-analysis');

  if (error) {
    return (
      <p className="text-sm text-rose-200" data-testid="ic-batch-disclosure-error">
        讀不到這批事件的設定：{error}
      </p>
    );
  }
  if (!detail) return null;

  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4" data-testid="ic-batch-disclosure">
      {/* ── 批次事實欄（唯讀）：本區塊**不得**出現任何 combobox／textbox ────────────── */}
      <div data-testid="ic-batch-facts">
        <p className="text-sm text-slate-300">這批事件的事實（不可在這裡改）</p>
        <p className="text-[11px] text-slate-500">
          這些是匯入當下就決定的事；要改只能重做一批——改了它們就不是同一批事實了。
        </p>
        <ul className="mt-2 space-y-1 text-xs text-slate-200">
          {IC_BATCH_FACT_FIELDS.map((field) => (
            <li key={field} data-testid={`ic-batch-fact-${field}`}>{factLine(field, detail)}</li>
          ))}
        </ul>
      </div>

      {/* ── 分析參數（可設定；只作用於本次分析、不回寫事件批）───────────────────── */}
      <div data-testid="ic-analysis-params">
        <p className="text-sm text-slate-300">這次分析要用的參數（只影響這一次分析，不會寫回事件批）</p>
        <label className="mt-2 block text-xs text-slate-200">
          <span className="mb-1 block">答案窗 horizon_bars（任意正整數）</span>
          <input
            type="number"
            min={1}
            data-testid="ic-param-horizon-bars"
            value={spec.horizon_bars}
            onChange={(e) => onChangeLabelSpec({ ...spec, horizon_bars: Number(e.target.value) })}
            className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
          />
        </label>

        {/* 三元組：可操作集合鎖 §F-1′；其餘值 disabled ＋顯示 §F-5′ 之開放前置理由 */}
        {(['entry_price_semantic', 'label_return_mode'] as const).map((dim) => {
          const options = dimOptions('/ic-analysis', dim);
          const value = spec[dim] ?? detail.declaration_seeds[dim] ?? options.find((o) => !o.disabled)?.value ?? '';
          return (
            <label key={dim} className="mt-2 block text-xs text-slate-200">
              <span className="mb-1 block">{dim}（本批之宣告種子為初始值）</span>
              <select
                data-testid={`ic-param-${dim}`}
                value={value}
                onChange={(e) => onChangeLabelSpec({ ...spec, [dim]: e.target.value })}
                className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
              >
                {options.map((o) => (
                  <option key={o.value} value={o.value} disabled={o.disabled} title={o.reason}>{o.value}</option>
                ))}
              </select>
              {options.filter((o) => o.disabled).map((o) => (
                <span
                  key={o.value}
                  className="mt-1 block text-[11px] text-amber-200/80"
                  data-testid={`ic-param-blocked-${dim}-${o.value}`}
                >
                  {o.value}：{o.reason}
                </span>
              ))}
            </label>
          );
        })}

        <label className="mt-2 block text-xs text-slate-200">
          <span className="mb-1 block">decision_offset_bars（本批鎖定為 {kRange.min}）</span>
          {/* 🔴 R3 群集 A（三家一致）：與 `/search` 同型——`min`／`max` 只是提示。
              本頁之 `k` 會進 `event_label_spec` 送去分析，繞過後直接撞 §F-2′ 之 fail-closed，
              使用者只會看到「分析被拒絕」而不知道是自己那格改出來的。兩層都補。
              🔴 種子值亦須 clamp：既有批之 `declaration_seeds.decision_offset_bars` 可能是 2
              （舊批宣告過非 F-1′ 之值），直接當初始值會讓本頁一載入就處在鎖定範圍外。 */}
          <input
            type="number"
            data-testid="ic-param-decision-offset-bars"
            min={kRange.min}
            readOnly={kRange.locked}
            {...(kRange.max !== null ? { max: kRange.max } : {})}
            value={clampDecisionOffset(
              spec.decision_offset_bars ?? detail.declaration_seeds.decision_offset_bars ?? kRange.min,
              kRange,
            )}
            onChange={(e) => onChangeLabelSpec({
              ...spec, decision_offset_bars: clampDecisionOffset(Number(e.target.value), kRange),
            })}
            className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
          />
          {kRange.locked && (
            <span className="mt-1 block text-[11px] text-amber-200/80" data-testid="ic-param-blocked-decision_offset_bars">
              k：{kRange.reason}
            </span>
          )}
        </label>

        {/* 🔴 本次答案窗之可算／缺筆數 ＋ 本次 purge 下界（式之權威在 §D-3′-a(ii)，本區只顯示結果） */}
        <p className="mt-2 text-[11px] text-slate-400" data-testid="ic-param-window-note">
          本次答案窗 ＝ {spec.horizon_bars} 根；這批共 {detail.summary.n_events} 筆事件，
          實際可算／缺的筆數與本次 purge 下界由後端於分析後回報（前端不自算，避免第二份公式）。
        </p>
      </div>
    </div>
  );
}
