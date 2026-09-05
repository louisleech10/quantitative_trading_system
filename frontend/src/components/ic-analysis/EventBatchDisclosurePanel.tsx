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
import {
  type EnumEventDimension,
  RETURN_MEASURE_PRESETS,
  clampDecisionOffset,
  contractDecisionOffsetMin,
  decisionOffsetRange,
  dimOptions,
  resolvePairConflict,
  returnMeasurePresetOf,
} from '@/lib/eventDimensions';
import type {
  EventImportDetail,
  ICAnalysisConfig,
  ICEventLabelScan,
  ICEventScanDisclosure,
} from '@/lib/types';

/** 分析參數之 `horizon_bars` 初始值——**字面常數**，不由任何落檔欄種子化。 */
export const IC_ANALYSIS_INITIAL_HORIZON_BARS = 1;

/**
 * `G3-D2` D4.3：k 之**建議上限**（超過只警示不擋）。
 * 🔴 值取自契約 `analysis_params.decision_offset_bars_scan_max`，經由**後端揭露**傳入；
 *    前端**不硬編**——硬編會在契約改值時安靜地繼續用舊值。
 *    後端沒給 ⇒ 不顯示警示（沒有依據就不對使用者說話）。
 */
interface Props {
  importId?: string;
  labelSpec: ICAnalysisConfig['event_label_spec'];
  onChangeLabelSpec: (next: NonNullable<ICAnalysisConfig['event_label_spec']>) => void;
  /** 測試注入；不給則依 `importId` 自行查 detail。 */
  detail?: EventImportDetail | null;
  /** `G3-D2` D4.3：k／h 掃描網格（`undefined` ⇒ 單值模式）。 */
  labelScan?: ICEventLabelScan | null;
  onChangeLabelScan?: (next: ICEventLabelScan | null) => void;
  /**
   * `G3-D2` D4.2／D4.3：**後端**回傳之揭露（兩上界、k 雙值、掃描結果）。
   * 🔴 前端**不自算**任何一項：上界之公式住 producer 之 `feasible_bounds`，
   *    在此重算就是第二份實作。沒有揭露 ⇒ 顯示「尚未分析」而不是猜一個數字。
   */
  disclosure?: ICEventScanDisclosure | null;
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
      //    與 `control_kind` 不同：本欄之混值不需另設 notes 欄——`label_origin` 屬
      //    `_ALWAYS_HOMOGENEOUS_DIMENSIONS`（**無條件**同質組，不受
      //    `enforce_batch_homogeneity` 旗標約束），混值／部分宣告在匯入層即
      //    `heterogeneous_rows_in_batch` 拒收。
      //    🔴 這句話在 R2 之前是**錯的**（當時碼裡沒有這道閘，三家全員實跑打穿）；
      //    現在為真，但**它為真的理由是那次修法**，不是 Task 1.8。
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
  labelScan = null, onChangeLabelScan, disclosure = null,
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
  // `G3-D2` D1.7：目前之 `(entry, mode)` 對應哪個報酬量法；不是任一 preset ⇒ `undefined`
  // （UI 顯示警示、送出守衛會擋）。**不自動改寫使用者的 spec**——靜默改值會讓
  // 「我明明選了 X」變成「送出的是 Y」。
  const currentPreset = returnMeasurePresetOf(spec.entry_price_semantic, spec.label_return_mode);
  // 🔴 **R3 準備期自查**：`CODEX-R2-P1-03` 之修法（未設定時省略整個 `event_label_spec` 鍵）
  //    使「使用者還沒選」也落到 `currentPreset === undefined`，於是畫面顯示紅字
  //    「送出會被擋下」——**但送出守衛只在 `config.event_label_spec` 為真時才跑**
  //    （`useICAnalysis.ts` 之條件），未設定時送得出去且後端會依宣告深度導出預設。
  //    ⇒ 顯示與事實相反。兩種狀態必須分開：
  //      ① 沒選（`labelSpec === undefined`）＝合法，交給後端導出 → 中性提示；
  //      ② 選了非 preset 的組合＝真的會被擋 → 紅字警示。
  //    **刻意不在此依宣告深度算出預設**：那會是後端 D1.7 規則的第二份實作，
  //    兩份會漂（正是本票一路在防的「兩端都有、但沒接上」之反面）。
  const userChoseSpec = labelSpec !== undefined;

  // ── `G3-D2` D4.2：進階直改兩欄（pair-aware）────────────────────────────
  // 🔴 D1 只開三個 preset，理由是「兩個 select 各自列值會列出矩陣外組合」。
  //    D4.2 之 `pair_rejected` 讓那兩個幾何零窗對在 UI 上**直接 disabled**
  //    ⇒ 前提消失，進階直改可以開放（`D-001` D1.7 明文「留待 D4.2」）。
  const [advanced, setAdvanced] = useState(false);
  const [pairReset, setPairReset] = useState<string | undefined>(undefined);
  const selection = {
    entry_price_semantic: spec.entry_price_semantic,
    label_return_mode: spec.label_return_mode,
  };
  const changePairDim = (dim: EnumEventDimension, value: string) => {
    const next = { ...selection, [dim]: value };
    const outcome = resolvePairConflict(next, dim);
    setPairReset(outcome.reset?.disclosure);
    onChangeLabelSpec({
      ...spec,
      entry_price_semantic: outcome.selection.entry_price_semantic,
      label_return_mode: outcome.selection.label_return_mode,
      horizon_bars: spec.horizon_bars ?? IC_ANALYSIS_INITIAL_HORIZON_BARS,
    });
  };

  // ── `G3-D2` D4.3：k／h 之「單值／掃到 m」切換 ──────────────────────────
  const kScanOn = labelScan?.decision_offset_bars_max !== undefined
    && labelScan?.decision_offset_bars_max !== null;
  const hScanOn = labelScan?.horizon_bars_max !== undefined
    && labelScan?.horizon_bars_max !== null;
  const setScan = (patch: Partial<ICEventLabelScan>) => {
    if (!onChangeLabelScan) return;
    const next: ICEventLabelScan = { ...(labelScan ?? {}), ...patch };
    // 兩軸都關掉 ⇒ 整個鍵回 `null`（**不是**送一個空物件：空物件在後端仍代表「有掃描」）。
    const empty = next.decision_offset_bars_max === undefined
      && next.horizon_bars_max === undefined;
    onChangeLabelScan(empty ? null : next);
  };
  const kMin = contractDecisionOffsetMin();
  const analysisK = spec.decision_offset_bars ?? kMin;
  const recordValues = detail?.batch_fact_notes.decision_offset_bars_record_values ?? [];
  const scanMax = disclosure?.decision_offset_bars_scan_max ?? null;
  const scanResult = disclosure?.event_label_scan ?? null;

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
          <span className="mb-1 block">
            答案窗 horizon_bars（任意正整數）
            {currentPreset?.key === 'same_bar' && (
              <span className="ml-1 text-[11px] text-slate-400" data-testid="ic-param-h-inert">
                — 「當根」不用 h（送出時固定為 1）
              </span>
            )}
            {!userChoseSpec && (
              <span className="ml-1 text-[11px] text-slate-400" data-testid="ic-param-h-backend-derived">
                — 尚未選量法 ⇒ 由後端依這批宣告的深度決定；此處不預填數字
              </span>
            )}
          </span>
          {/* 🔴 `CODEX-R2-P1-03` 後半：「當根」下 h **不參與計算**，可編輯會讓使用者以為
              自己改的數字有作用（改了值、結果不變）。⇒ disabled，並在標籤明說原因。
              wire 仍送 1（inert 哨兵；`event_label_spec` 恆四鍵，缺鍵 normalizer fail-closed）。
              🔴 `CODEX-R3-P2-01`：**未選量法時不得顯示 `1`**——後端會依宣告深度導出
              （深度 3 就跑 h=3），畫面顯示 1 就是**數字誤導**，比顯示空白更糟。
              ⇒ 未選時 disabled ＋ 空值 ＋ 標籤說明由誰決定。
              **刻意不在此依 `detail` 算出深度預設**：那會是後端 D1.7 規則的第二份實作，
              兩份會漂；正確的長期解是把 route response 之 `event_label_spec` 回灌
              （codex 原建議之後半，現列為 R4 待議）。 */}
          <input
            type="number"
            min={1}
            data-testid="ic-param-horizon-bars"
            disabled={!userChoseSpec || currentPreset?.key === 'same_bar'}
            value={!userChoseSpec ? '' : (currentPreset?.key === 'same_bar' ? 1 : spec.horizon_bars)}
            onChange={(e) => onChangeLabelSpec({ ...spec, horizon_bars: Number(e.target.value) })}
            className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100 disabled:opacity-50"
          />
        </label>

        {/* ── `G3-D2` D1.7：報酬量法三選項（取代原本兩個枚舉 select）────────────────
            🔴 **B-D1 不提供「進階直改兩欄」**：兩個 select 各自列值會列出
            `(trigger_close, open_to_close)` 這種矩陣外組合（幾何窗長 0），使用者選得到卻算不出來。
            進階直改留待 D4.2 之 pair-aware `dimOptions(selection)` 落地。
            ⇒ 本區塊之 DOM **不得**出現 `ic-param-entry_price_semantic`／`ic-param-label_return_mode`。 */}
        <fieldset className="mt-3" data-testid="ic-param-return-measure">
          <legend className="mb-1 block text-xs text-slate-200">報酬量法（要量哪一段的漲跌）</legend>
          <p className="mb-1 text-[11px] text-slate-500">
            初始值依這批宣告的答案窗深度自動選；想量別段就自己改。
          </p>
          {RETURN_MEASURE_PRESETS.map((p) => {
            const active = currentPreset?.key === p.key;
            return (
              <label key={p.key} className="mt-1 flex items-start gap-2 text-xs text-slate-200">
                <input
                  type="radio"
                  name="ic-return-measure"
                  data-testid={`ic-param-return-measure-${p.key}`}
                  checked={active}
                  onChange={() => onChangeLabelSpec({
                    ...spec,
                    entry_price_semantic: p.entry_price_semantic,
                    label_return_mode: p.label_return_mode,
                    // 「當根」不用 h，但 `event_label_spec` 恆為四鍵 ⇒ 仍送 inert 哨兵 1。
                    horizon_bars: p.key === 'same_bar' ? 1 : (spec.horizon_bars ?? 1),
                  })}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium">{p.label}</span>
                  <span className="ml-1 text-[11px] text-slate-400">{p.hint}</span>
                </span>
              </label>
            );
          })}
          {currentPreset === undefined && userChoseSpec && (
            <span className="mt-1 block text-[11px] text-rose-300" data-testid="ic-param-return-measure-invalid">
              目前的組合（{spec.entry_price_semantic ?? '?'} / {spec.label_return_mode ?? '?'}）
              不是可分析的量法，送出會被擋下——請選上面三種其中一種。
            </span>
          )}
          {currentPreset === undefined && !userChoseSpec && (
            <span className="mt-1 block text-[11px] text-slate-400" data-testid="ic-param-return-measure-unset">
              尚未選擇報酬量法 ⇒ 送出時由後端依**這批宣告的深度**導出（不會被擋下）。
              要指定就點上面三種其中一種。
            </span>
          )}
        </fieldset>

        {/* ── `G3-D2` D4.2：進階直改 entry／mode 兩欄（pair-aware）───────────────
            🔴 兩個幾何零窗對在此**直接 disabled** 並顯示理由（`kind: 'pair_rejected'`），
            改一維使另一維落入拒收對時，另一維**重設為契約 default** 並揭露。
            選項與理由全部由 `dimOptions(..., selection)` 導出，本檔不寫第二份清單。 */}
        <div className="mt-3" data-testid="ic-param-advanced">
          <button
            type="button"
            data-testid="ic-param-advanced-toggle"
            onClick={() => setAdvanced((v) => !v)}
            className="text-[11px] text-slate-300 underline underline-offset-2"
          >
            {advanced ? '收起進階：直接改兩欄' : '進階：直接改 entry／mode 兩欄'}
          </button>
          {advanced && (
            <div className="mt-2 space-y-2">
              {pairReset && (
                <p className="text-[11px] text-amber-200/90" data-testid="ic-param-pair-reset">
                  {pairReset}
                </p>
              )}
              {(['entry_price_semantic', 'label_return_mode'] as const).map((dim) => {
                const options = dimOptions('/ic-analysis', dim, undefined, selection);
                const blocked = options.filter((o) => o.kind === 'pair_rejected');
                return (
                  <label key={dim} className="block text-xs text-slate-200">
                    <span className="mb-1 block">{dim}</span>
                    <select
                      data-testid={`ic-param-${dim}`}
                      value={selection[dim] ?? ''}
                      onChange={(e) => changePairDim(dim, e.target.value)}
                      className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
                    >
                      {selection[dim] === undefined && <option value="">（尚未選）</option>}
                      {options.map((o) => (
                        <option key={o.value} value={o.value} disabled={o.disabled} title={o.reason}>
                          {o.value}
                        </option>
                      ))}
                    </select>
                    {blocked.map((o) => (
                      <span
                        key={o.value}
                        className="mt-1 block text-[11px] text-amber-200/80"
                        data-testid={`ic-param-pair-blocked-${dim}-${o.value}`}
                      >
                        {o.value}：{o.reason}
                      </span>
                    ))}
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {/* ── `G3-D2` D4.3：k 之雙值揭露 ＋ 單值／掃描切換 ─────────────────────
            🔴 **解鎖**（D4.2）：k 已不在支援矩陣內，其上界是**逐事件可行域**，
            由後端揭露 `k_max_feasible_at_h`；前端不再假裝有一個 `max`，也不再鎖 0。
            🔴 **不再回退 seeds**（D4.3）：`declaration_seeds.decision_offset_bars` 已移除；
            初始值＝契約 min 之常數，批內記錄值以獨立欄並排顯示。 */}
        <label className="mt-3 block text-xs text-slate-200">
          <span className="mb-1 block">decision_offset_bars（本次分析要用的 k）</span>
          <input
            type="number"
            data-testid="ic-param-decision-offset-bars"
            min={kRange.min}
            step={1}
            value={analysisK}
            disabled={kScanOn}
            onChange={(e) => onChangeLabelSpec({
              ...spec, decision_offset_bars: clampDecisionOffset(Number(e.target.value), kRange),
            })}
            className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100 disabled:opacity-50"
          />
          {/* 並排「批次記錄 k／本次分析 k」——同名不同義，分開講 */}
          <span className="mt-1 block text-[11px] text-slate-400" data-testid="ic-param-k-dual">
            批次記錄的 k ＝ {recordValues.length ? recordValues.join('、') : '（這批沒有這個欄）'}
            ；本次分析的 k ＝ {analysisK}
            {recordValues.length === 1 && recordValues[0] !== analysisK
              && '（兩者不同是正常的：記錄是匯入當下的宣告，分析 k 是這一次的參數）'}
          </span>
          {scanMax !== null && analysisK > scanMax && (
            <span className="mt-1 block text-[11px] text-amber-200/80" data-testid="ic-param-k-over-scan-max">
              k ＝ {analysisK} 超過建議上限 {scanMax}（契約 analysis_params）——**不擋**，
              但可行的事件會變少，請看下面的上界揭露。
            </span>
          )}
        </label>

        {/* k／h 之「單值／掃到 m」切換（裁定③：填 m 就掃 0～m；h 自 1 起） */}
        {onChangeLabelScan && (
          <div className="mt-2 space-y-2" data-testid="ic-param-scan">
            <label className="flex items-center gap-2 text-xs text-slate-200">
              <input
                type="checkbox"
                data-testid="ic-param-scan-k-toggle"
                checked={kScanOn}
                onChange={(e) => setScan({
                  decision_offset_bars_max: e.target.checked ? analysisK : undefined,
                })}
              />
              <span>k 掃描：0 ～</span>
              <input
                type="number"
                data-testid="ic-param-scan-k-max"
                min={kMin}
                step={1}
                disabled={!kScanOn}
                value={labelScan?.decision_offset_bars_max ?? ''}
                onChange={(e) => setScan({ decision_offset_bars_max: Number(e.target.value) })}
                className="w-20 rounded border border-slate-700 bg-slate-900/70 px-2 py-0.5 text-xs disabled:opacity-50"
              />
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-200">
              <input
                type="checkbox"
                data-testid="ic-param-scan-h-toggle"
                checked={hScanOn}
                onChange={(e) => setScan({
                  horizon_bars_max: e.target.checked ? (spec.horizon_bars ?? 1) : undefined,
                })}
              />
              <span>h 掃描：1 ～</span>
              <input
                type="number"
                data-testid="ic-param-scan-h-max"
                min={1}
                step={1}
                disabled={!hScanOn}
                value={labelScan?.horizon_bars_max ?? ''}
                onChange={(e) => setScan({ horizon_bars_max: Number(e.target.value) })}
                className="w-20 rounded border border-slate-700 bg-slate-900/70 px-2 py-0.5 text-xs disabled:opacity-50"
              />
            </label>
          </div>
        )}

        {/* ── 兩個條件上界（後端揭露；前端不自算）───────────────────────────── */}
        <p className="mt-2 text-[11px] text-slate-400" data-testid="ic-param-bounds">
          {disclosure
            ? `這批在目前設定下的上界：k 最多 ${
              disclosure.k_bound_status === 'bounded' ? disclosure.k_max_feasible_at_h : '（這個 h 下沒有可行的 k）'
            }；h 最多 ${
              disclosure.h_bound_status === 'bounded' ? disclosure.h_max_feasible_at_k
                : (disclosure.h_bound_status === 'h_inert_for_mode' ? '（這個量法不用 h，沒有上界）' : '（這個 k 下沒有可行的 h）')
            }。這是**幾何與資料涵蓋**的上界：超過就一定算不出來；沒超過**不保證**每一筆都算得出來。`
            : '上界要分析過才知道（由後端依這批的 bar 表逐事件算），這裡不猜。'}
          {/* 🔴 `CODEX-R1-P2-04`：上界是「對誰」算的必須說出來——這批若含他 symbol 事件，
              它們不進本次 IC，也不該讓上界看起來比實際母體更嚴而使用者不知情。 */}
          {disclosure?.bounds_scope_symbol && (
            <span data-testid="ic-param-bounds-scope">
              {' '}（上界只對本次 run 的 {disclosure.bounds_scope_symbol} 事件計算
              {(disclosure.bounds_scope_excluded_events ?? 0) > 0
                ? `；另有 ${disclosure.bounds_scope_excluded_events} 筆他 symbol 事件不計入，它們也不進本次 IC`
                : ''}）
            </span>
          )}
        </p>

        {/* ── 掃描結果矩陣（行 k、列 h）───────────────────────────────────── */}
        {scanResult && (
          <div className="mt-2" data-testid="ic-param-scan-result">
            {scanResult.capability === 'unavailable' ? (
              <p className="text-[11px] text-rose-300" data-testid="ic-param-scan-rejected">
                掃描沒有執行：{scanResult.reason}
                {scanResult.message ? `——${scanResult.message}` : ''}
              </p>
            ) : (
              <>
                <p className="text-[11px] text-slate-400">
                  掃描完成 {scanResult.scan_done}/{scanResult.scan_total} 格
                </p>
                <div className="mt-1 overflow-x-auto">
                  <table className="text-[11px] text-slate-200">
                    <tbody>
                      {Array.from(new Set(scanResult.scan_results.map((c) => c.k))).map((k) => (
                        <tr key={k}>
                          <th className="pr-2 text-left font-normal text-slate-400">k={k}</th>
                          {scanResult.scan_results.filter((c) => c.k === k).map((c) => (
                            <td
                              key={`${c.k}-${c.h}`}
                              data-testid={`ic-scan-cell-${c.k}-${c.h}`}
                              className="px-2 py-0.5"
                              title={c.reason ?? undefined}
                            >
                              {c.capability === 'available'
                                ? `h=${c.h}: ${c.n_events} 筆`
                                : `h=${c.h}: 不可用`}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {/* 🔴 本次答案窗之可算／缺筆數 ＋ 本次 purge 下界（式之權威在 §D-3′-a(ii)，本區只顯示結果） */}
        {/* 🔴 `GROK-R4-P2-01`：本行是**同一個數字在同一面板的第二處顯示**。
            `CODEX-R3-P2-01` 的修法只改了 input，這裡仍插值 `spec.horizon_bars`
            ⇒ 未選量法時照樣寫「本次答案窗 ＝ 1 根」，而後端對宣告深度 3 的批跑 h=3。
            grok 實跑探針命中。⇒ 未選時不報數字，與 input 同一套說法。 */}
        <p className="mt-2 text-[11px] text-slate-400" data-testid="ic-param-window-note">
          本次答案窗 ＝ {userChoseSpec ? `${spec.horizon_bars} 根` : '由後端依這批宣告的深度決定（尚未選量法）'}；
          這批共 {detail.summary.n_events} 筆事件，
          實際可算／缺的筆數與本次 purge 下界由後端於分析後回報（前端不自算，避免第二份公式）。
        </p>
      </div>
    </div>
  );
}
