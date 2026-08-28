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
import {
  type EnumEventDimension,
  type EventDimPath,
  clampDecisionOffset,
  decisionOffsetRange,
  dimOptions,
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
  return (
    <div className="space-y-3" data-testid="event-dimension-fields">
      {ENUM_DIMS.map((dim) => {
        const options = dimOptions(path, dim, contract);
        const blocked = options.filter((o) => o.disabled);
        return (
          <label key={dim} className="block text-sm text-slate-200">
            <span className="block mb-1">{ENUM_LABELS[dim]}</span>
            <select
              data-testid={`event-dim-${dim}`}
              value={values[dim]}
              onChange={(e) => onChange({ ...values, [dim]: e.target.value })}
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

      {/* `decision_offset_bars` 是 `int, min 0`，不是 enum ⇒ 數值控制項；範圍由 `decisionOffsetRange` 給。 */}
      <label className="block text-sm text-slate-200">
        <span className="block mb-1">decision_offset_bars（決策位移 k）</span>
        {/* 🔴 R3 群集 A（`CODEX-R3-P1-01`／`COMPOSER-R3-P1-01`／`GROK-R3-P1-01`，三家一致）：
            HTML 之 `min`／`max` **只是提示**，使用者打字照樣送得出 `k>0`，
            而 `buildEventContractRecords` 只擋 `k < min` ⇒ 鎖 0 的路徑上真的會落檔 `k=3`。
            兩層都補：`readOnly` 讓使用者改不動、`onChange` clamp 讓程式化設值也進不來。 */}
        <input
          type="number"
          data-testid="event-dim-decision_offset_bars"
          value={values.decision_offset_bars}
          min={range.min}
          readOnly={range.locked}
          {...(range.max !== null ? { max: range.max } : {})}
          onChange={(e) => onChange({
            ...values,
            // 清空＝未選（只在 `allowUnset` 之路徑有意義）；否則一律轉數字後**夾到本路徑之範圍內**。
            decision_offset_bars: e.target.value === '' && allowUnset
              ? ''
              : clampDecisionOffset(Number(e.target.value), range),
          })}
          className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
        />
        <span className="mt-1 block text-[11px] text-slate-400" data-testid="event-dim-doc-decision_offset_bars">
          {EVENT_CONTRACT_DOCS.decision_offset_bars}
        </span>
        {range.locked && (
          <span
            className="mt-1 block text-[11px] text-amber-200/80"
            data-testid="event-dim-blocked-decision_offset_bars"
          >
            k：{range.reason}
          </span>
        )}
      </label>
    </div>
  );
}
