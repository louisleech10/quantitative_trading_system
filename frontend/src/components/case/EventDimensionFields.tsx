'use client';

/**
 * GAP-3 UX **Task 7.1** — 五個批次維度之 UI 控制項（`/search` 匯出面板與 `/data-preparation` 匯入表單共用）。
 *
 * 🔴 **本元件不知道任何值域**：選項、可操作性、理由字串全部來自 `@/lib/eventDimensions`
 *    （契約 ＋ 單一具名常數 `EVENT_DIM_PATH_EXCLUSIONS`）。
 *    在這裡寫 `if (value === 'A') disabled` 就是 SPEC「不可做」所指之第二份排除清單。
 * 🔴 **兩類不可選值分別顯示**：契約恆拒者顯示契約 `rejected_with_reason` 字面；
 *    路徑排除者顯示排除常數之理由字串。兩者皆 `disabled`。
 * 🔴 白話說明取自契約 `doc` 欄之鏡像（`eventContractDocs.ts`），**不在本檔另寫文案**。
 */

import { EVENT_CONTRACT_DOCS } from '@/lib/eventContractDocs';
import { useState } from 'react';

import {
  type EnumEventDimension,
  type EventDimPath,
  decisionOffsetRange,
  dimOptions,
  resolvePairConflict,
} from '@/lib/eventDimensions';

/**
 * 五維度之當前取值（`/search` 與 `/data-preparation` 共用同一形狀）。
 * `''` ＝**未選**，只在 `allowUnset` 之路徑（CSV 匯入）出現，代表「不寫這個鍵」。
 */
export interface EventDimensionValues {
  scenario: string;
  control_kind: string;
  entry_price_semantic: string;
  label_return_mode: string;
  decision_offset_bars: number | '';
}

interface EventDimensionFieldsProps {
  path: EventDimPath;
  values: EventDimensionValues;
  onChange: (next: EventDimensionValues) => void;
  /**
   * 是否提供「未選」。
   *
   * 🔴 `/data-preparation` **必須**為 `true`：`scenario`／`control_kind` 在該頁**也可以由 CSV 欄對映**
   *    （`MAPPABLE_CONTRACT_FIELDS`）⇒ 若下拉一律帶著預設值送出，會把使用者對映到的欄蓋掉，
   *    而且是**靜默**蓋掉。未選＝不寫該鍵，維持既有流程逐位元不變（Task 1.5 之 A-4′ 同一條原則）。
   */
  allowUnset?: boolean;
  /** 測試可餵**真契約**進來（Task 7.2 之機械閘即如此），生產走鏡像預設值。 */
  contract?: unknown;
}

const ENUM_LABELS: Record<EnumEventDimension, string> = {
  scenario: 'scenario（情境類型）',
  control_kind: 'control_kind（反例來源）',
  entry_price_semantic: 'entry_price_semantic（進場價語意）',
  label_return_mode: 'label_return_mode（報酬算法）',
};

const ENUM_DIMS: readonly EnumEventDimension[] = [
  'scenario', 'control_kind', 'entry_price_semantic', 'label_return_mode',
];

export default function EventDimensionFields({
  path, values, onChange, allowUnset = false, contract,
}: EventDimensionFieldsProps) {
  const range = decisionOffsetRange(path, contract);
  // 🔴 `G3-D2` D4.2：`pair_rejected` 需要「另一維目前選了什麼」⇒ 兩欄一起餵進去。
  //    `''`（未選）在 `pairRejectedReason` 內視為未選 ⇒ 不擋。
  const selection = {
    entry_price_semantic: values.entry_price_semantic || undefined,
    label_return_mode: values.label_return_mode || undefined,
  };
  // 成對重設之揭露字串（`undefined` ⇒ 本次沒有發生重設）。**不靜默重設**。
  const [pairReset, setPairReset] = useState<string | undefined>(undefined);

  /** 改一個 enum 維度：先套新值，再解成對衝突（另一維重設為契約 default）。 */
  const changeEnum = (dim: EnumEventDimension, value: string) => {
    const next = { ...values, [dim]: value };
    if (dim !== 'entry_price_semantic' && dim !== 'label_return_mode') {
      setPairReset(undefined);
      onChange(next);
      return;
    }
    const outcome = resolvePairConflict(
      {
        entry_price_semantic: next.entry_price_semantic || undefined,
        label_return_mode: next.label_return_mode || undefined,
      },
      dim, contract,
    );
    setPairReset(outcome.reset?.disclosure);
    onChange({
      ...next,
      entry_price_semantic: outcome.selection.entry_price_semantic ?? next.entry_price_semantic,
      label_return_mode: outcome.selection.label_return_mode ?? next.label_return_mode,
    });
  };

  return (
    <div className="space-y-3" data-testid="event-dimension-fields">
      {pairReset && (
        <p className="text-[11px] text-amber-200/90" data-testid="event-dim-pair-reset">
          {pairReset}
        </p>
      )}
      {ENUM_DIMS.map((dim) => {
        const options = dimOptions(path, dim, contract, selection);
        const blocked = options.filter((o) => o.disabled);
        return (
          <label key={dim} className="block text-sm text-slate-200">
            <span className="block mb-1">{ENUM_LABELS[dim]}</span>
            <select
              data-testid={`event-dim-${dim}`}
              value={values[dim]}
              onChange={(e) => changeEnum(dim, e.target.value)}
              className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
            >
              {/* 「未選」不是契約的值，也**不計入** selectable——它代表「這批不由本控制項決定」。 */}
              {allowUnset && <option value="">（未選：不寫這個鍵）</option>}
              {options.map((o) => (
                <option key={o.value} value={o.value} disabled={o.disabled} title={o.reason}>
                  {o.value}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-[11px] text-slate-400" data-testid={`event-dim-doc-${dim}`}>
              {EVENT_CONTRACT_DOCS[dim]}
            </span>
            {blocked.map((o) => (
              <span
                key={o.value}
                className="mt-1 block text-[11px] text-amber-200/80"
                data-testid={`event-dim-blocked-${dim}-${o.value}`}
              >
                {o.value}：{o.reason}
              </span>
            ))}
          </label>
        );
      })}

      {/* 🔴 `G3-D2` **D4.3**（裁定②④ 2026-09-03）：`decision_offset_bars`（k）**不再由使用者於
          匯出／匯入時填**——它是**分析參數**，同一批事件可以用不同 k 各分析一次。
          ⇒ 本控制項整個移除（DOM 不得再有 `event-dim-decision_offset_bars`），
          只留一句去哪裡設定的指路，以及契約 doc（讓使用者知道這個欄位仍存在於檔案裡）。
          🔴 **契約欄本身不動**：CSV 欄對映表仍可對映 `decision_offset_bars`
          （`/data-preparation` 之 `MAPPABLE_CONTRACT_FIELDS`），匯出端一律寫 `0`
          （`eventExport.ts`），記錄值以獨立揭露欄呈現於分析頁。 */}
      <div className="block text-sm text-slate-200" data-testid="event-dim-decision_offset_bars-moved">
        <span className="block mb-1">decision_offset_bars（決策位移 k）</span>
        <span className="block text-[11px] text-amber-200/80">
          k 於 IC 分析頁設定（同一批事件可用不同 k 各分析一次；此處不填、匯出一律寫 {range.min}）
        </span>
        <span className="mt-1 block text-[11px] text-slate-400" data-testid="event-dim-doc-decision_offset_bars">
          {EVENT_CONTRACT_DOCS.decision_offset_bars}
        </span>
      </div>
    </div>
  );
}
