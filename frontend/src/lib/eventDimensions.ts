/**
 * GAP-3 UX **Task 7.1** — 五個批次維度之「可操作選項集合」之**唯一**導出處。
 *
 * `selectable(path, dim) = accepted(dim) − pathExclusions(path, dim)`（SPEC L2849–2871）
 *
 * 🔴 **兩個來源都不是人工清單**：
 *   - `accepted(dim)` 由**契約**導出（`accepted` 鍵；無該鍵者取 `enum` 全集）；
 *   - `pathExclusions` 由**單一具名常數** `EVENT_DIM_PATH_EXCLUSIONS` 導出（SPEC L2854–2860 五列封閉）。
 *
 * 🔴 **契約在前端的取得方式**（沿用本 repo 既有作法，見 `eventContractDocs.ts`／`eventId.ts`）：
 * 契約沒有對前端開放的端點 ⇒ 本檔持一份**與契約同形狀**的鏡像片段 `EVENT_DIM_CONTRACT_MIRROR`，
 * 由 `eventDimensions.test.ts` **讀契約 JSON 逐鍵比對**，漂移即轉紅。
 * 因為鏡像與契約**同形狀**，`acceptedValues()` 這支存取器對兩者都適用
 * ⇒ Task 7.2 之機械閘可以把**真契約**餵進來算 `selectable()`，
 * 而 UI 走鏡像 ⇒ 「契約加了第 5 個 `scenario` 值而 UI 沒跟」會讓 7.2 ① 直接轉紅
 * （SPEC Task 7.2 mutation (a) 之設計意圖）。
 *
 * 🔴 **不得**在元件裡另寫 `if (value === 'A') disabled`——那是第二份排除清單（SPEC「不可做」）。
 */

/** 五個批次維度（`counterexample_kind` 是**逐列選填欄**，不在此列——R5 群集 G）。 */
export const EVENT_DIMENSIONS = [
  'scenario',
  'control_kind',
  'entry_price_semantic',
  'label_return_mode',
  'decision_offset_bars',
] as const;
export type EventDimension = (typeof EVENT_DIMENSIONS)[number];

/** 出現在排除表裡的路徑鍵。`/ic-analysis` 由 Task 7.6 ③ 使用（沿用同一常數，不另建第二份）。 */
export type EventDimPath = '/search' | '/data-preparation' | '/ic-analysis';

/** 走 enum 減法的四個維度；`decision_offset_bars` 為 `int, min 0`，另走數值鎖定（見下）。 */
export const ENUM_EVENT_DIMENSIONS = [
  'scenario', 'control_kind', 'entry_price_semantic', 'label_return_mode',
] as const;
export type EnumEventDimension = (typeof ENUM_EVENT_DIMENSIONS)[number];

/** 各維度在契約檔內之取值路徑（`label_return_mode` **住 `label_definition.fields`**，不是頂層）。 */
export const EVENT_DIM_CONTRACT_PATHS: Record<EventDimension, readonly string[]> = {
  scenario: ['required_fields', 'scenario'],
  control_kind: ['required_fields', 'control_kind'],
  entry_price_semantic: ['required_fields', 'entry_price_semantic'],
  label_return_mode: ['required_fields', 'label_definition', 'fields', 'label_return_mode'],
  decision_offset_bars: ['required_fields', 'decision_offset_bars'],
};

/** 契約節點之形狀（只取本檔用得到的鍵；契約還有 `doc`／`default` 等，由 `eventContractDocs` 負責）。 */
export interface EventDimContractNode {
  enum?: readonly string[];
  accepted?: readonly string[];
  rejected_with_reason?: Readonly<Record<string, string>>;
  type?: string;
  min?: number;
}

/**
 * 契約之**同形狀鏡像片段**。
 * 🔴 這裡的每一個值都逐字取自 `momentum/Analysis/contracts/event_import_contract.json`，
 *    由 `eventDimensions.test.ts` 對證；**改契約而沒改這裡，測試會紅**。
 */
export const EVENT_DIM_CONTRACT_MIRROR = {
  required_fields: {
    scenario: { enum: ['A', 'B', 'C', 'two_stage'] },
    control_kind: {
      enum: ['user_labeled_same_trigger', 'user_labeled_other', 'platform_same_trigger_rule', 'platform_random_bars'],
      accepted: ['user_labeled_same_trigger', 'user_labeled_other', 'platform_same_trigger_rule'],
      rejected_with_reason: { platform_random_bars: 'not_implemented_platform_random_bars' },
    },
    entry_price_semantic: {
      enum: ['trigger_open', 'trigger_close', 'next_open', 'decision_bar_open', 'decision_bar_close'],
    },
    decision_offset_bars: { type: 'int', min: 0 },
    label_definition: {
      fields: {
        label_return_mode: { enum: ['open_to_close', 'open_to_horizon_close', 'close_to_close'] },
      },
    },
  },
} as const;

/** 由**任一**契約形狀物件（真契約或鏡像）取出某維度之節點；路徑不存在 ⇒ `undefined`。 */
export function dimContractNode(contract: unknown, dim: EventDimension): EventDimContractNode | undefined {
  const node = EVENT_DIM_CONTRACT_PATHS[dim].reduce<unknown>(
    (acc, key) => (acc as Record<string, unknown> | undefined)?.[key], contract,
  );
  return (node && typeof node === 'object') ? node as EventDimContractNode : undefined;
}

/**
 * `accepted(dim)` ＝契約之 `accepted` 鍵；**無該鍵者取 `enum` 全集**（SPEC L2850–2852）。
 *
 * 🔴 取不到節點 ⇒ **拋錯**，不回空陣列：空陣列會讓「UI 一個選項都沒有」與
 * 「契約路徑寫錯」長得一模一樣，是 fail-open。
 */
export function acceptedValues(
  dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): readonly string[] {
  const node = dimContractNode(contract, dim);
  if (!node) throw new Error(`契約缺少維度 ${dim}（路徑 ${EVENT_DIM_CONTRACT_PATHS[dim].join('.')}）`);
  const values = node.accepted ?? node.enum;
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error(`契約之 ${dim} 既無 accepted 亦無 enum`);
  }
  return values;
}

/** 契約**恆拒**值 ⇒ 其 reason 字面（UI 對這類值顯示契約字面，與路徑排除之理由分開顯示）。 */
export function contractRejectedReason(
  dim: EnumEventDimension, value: string, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): string | undefined {
  return dimContractNode(contract, dim)?.rejected_with_reason?.[value];
}

export interface EventDimExclusion {
  /** 被排除之值（該 `(path, dim)` 之封閉集合）。 */
  readonly values: readonly string[];
  /** 🔴 **非空**理由字串；UI 對路徑排除之值顯示這一句（SPEC 驗收⑨）。 */
  readonly reason: string;
}

/** 三元組（`entry_price_semantic`／`label_return_mode`）之排除理由——§F-5′。 */
const F5_REASON = '該值宣告後，分析層本批不支援以其計算 label_value（§F-5′）⇒ 該批將無法做條件 IC';

/**
 * 🔴 **路徑排除之單一具名常數**（SPEC L2854–2860 之五列封閉內容）。
 *
 * - `/search`：`scenario` 只開 `C`；三元組只開 `(trigger_close, close_to_close)` ＝ §F-1′ 支援矩陣。
 * - `/ic-analysis`：Task 7.6 ③ 之分析參數區**沿用本常數**，不另建第二份排除清單。
 * - `/data-preparation`：CSV 匯入路徑**四種 scenario 全開**（label 由使用者自帶，系統只照抄），
 *   故本表**沒有** `/data-preparation` 之列——「限制只在該路徑」由此成立（SPEC 驗收⑧）。
 *
 * 🔴 新增或移除排除**只能改本常數**並同步 SPEC；散在元件裡的 `if` 是第二份副本。
 */
export const EVENT_DIM_PATH_EXCLUSIONS: Readonly<Record<string, EventDimExclusion>> = {
  '/search|scenario': {
    values: ['A', 'B', 'two_stage'],
    reason: '此路徑之 label 由 t0 條件產生（eventExport.ts 以 positive_case 判定）；'
      + 'A／B／two_stage 為預測型，事件在未來，需獨立之 label producer 與 provenance，本批未交付',
  },
  '/search|entry_price_semantic': {
    values: ['trigger_open', 'next_open', 'decision_bar_open', 'decision_bar_close'],
    reason: F5_REASON,
  },
  '/search|label_return_mode': {
    values: ['open_to_close', 'open_to_horizon_close'],
    reason: F5_REASON,
  },
  '/ic-analysis|entry_price_semantic': {
    values: ['trigger_open', 'next_open', 'decision_bar_open', 'decision_bar_close'],
    reason: F5_REASON,
  },
  '/ic-analysis|label_return_mode': {
    values: ['open_to_close', 'open_to_horizon_close'],
    reason: F5_REASON,
  },
};

/** 組出 `EVENT_DIM_PATH_EXCLUSIONS` 之鍵；鍵格式集中在此，避免各處手拼字串。 */
export function exclusionKey(path: EventDimPath, dim: EventDimension): string {
  return `${path}|${dim}`;
}

/** 該 `(path, dim)` 被路徑排除之值集合（無排除 ⇒ 空陣列）。 */
export function pathExclusions(path: EventDimPath, dim: EventDimension): readonly string[] {
  return EVENT_DIM_PATH_EXCLUSIONS[exclusionKey(path, dim)]?.values ?? [];
}

/** 該值被路徑排除之理由（沒被排除 ⇒ `undefined`）。 */
export function pathExclusionReason(
  path: EventDimPath, dim: EventDimension, value: string,
): string | undefined {
  const row = EVENT_DIM_PATH_EXCLUSIONS[exclusionKey(path, dim)];
  return row && row.values.includes(value) ? row.reason : undefined;
}

/**
 * 🔴 **可操作選項集合**＝`accepted(dim) − pathExclusions(path, dim)`。
 *
 * 順序沿用契約之 `accepted`／`enum` 順序（UI 呈現順序因此也由契約決定，不另排）。
 */
export function selectable(
  path: EventDimPath, dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): readonly string[] {
  const excluded = new Set(pathExclusions(path, dim));
  return acceptedValues(dim, contract).filter((v) => !excluded.has(v));
}

/**
 * 某維度在該路徑之**全部**選項與其可操作性（UI 直接 map 這個）。
 *
 * 兩類不可選值**分別**顯示（SPEC L2874–2876）：
 * - `kind: 'contract_rejected'` ⇒ 顯示契約 `rejected_with_reason` 之字面；
 * - `kind: 'path_excluded'`     ⇒ 顯示 `pathExclusions` 之理由字串。
 * 兩者皆 `disabled` 且**不計入** `selectable`。
 */
export interface EventDimOption {
  value: string;
  disabled: boolean;
  kind: 'selectable' | 'contract_rejected' | 'path_excluded';
  /** 不可選時之理由（可選時為 `undefined`）。 */
  reason?: string;
}

export function dimOptions(
  path: EventDimPath, dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): readonly EventDimOption[] {
  const node = dimContractNode(contract, dim);
  const all = node?.enum ?? acceptedValues(dim, contract);
  const ok = new Set(selectable(path, dim, contract));
  return all.map((value) => {
    if (ok.has(value)) return { value, disabled: false, kind: 'selectable' as const };
    const rejected = contractRejectedReason(dim, value, contract);
    if (rejected !== undefined) {
      return { value, disabled: true, kind: 'contract_rejected' as const, reason: rejected };
    }
    return {
      value, disabled: true, kind: 'path_excluded' as const,
      reason: pathExclusionReason(path, dim, value) ?? '此路徑不開放本值',
    };
  });
}

/**
 * `decision_offset_bars` 之**逐路徑可輸入範圍**（非 enum，不走上面的減法）。
 *
 * 🔴 SPEC L2864：於 `/search` 與 `/ic-analysis` **鎖定為 `0`**（§F-1′ 之 `k=0`）；
 *    `/data-preparation` 為 CSV 匯入路徑，**不經 F-1′ 支援矩陣**（§F-5′ 末段）⇒ 只受契約 `min: 0` 限制。
 * 🔴 下界一律取自契約之 `min`，**不寫死 0**。
 */
export function decisionOffsetRange(
  path: EventDimPath, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): { min: number; max: number | null; locked: boolean; reason?: string } {
  const min = contractDecisionOffsetMin(contract);
  if (path === '/data-preparation') return { min, max: null, locked: false };
  return { min, max: min, locked: true, reason: F5_REASON };
}

/** 五維度之 UI 取值；`''` ＝未選（CSV 匯入路徑才有）。 */
export interface EventDimensionSelection {
  scenario: string;
  control_kind: string;
  entry_price_semantic: string;
  label_return_mode: string;
  decision_offset_bars: number | '';
}

/** `label_return_mode` **住 `label_definition` 之內**；其餘四個是事件頂層欄。 */
const NESTED_DIM: EventDimension = 'label_return_mode';

/**
 * Task 7.1（`/data-preparation`）：把**已選**之維度轉成 CSV 匯入之「批次預設」片段。
 *
 * 🔴 未選者**不出現在回傳物件裡**——不是寫 `null`／空字串。
 *    匯入路徑之 `scenario`／`control_kind` 也可以由 CSV 欄對映而來，
 *    寫一個空值進去會把對映結果蓋成非法值，而且是靜默的。
 */
export function dimensionBatchDefaults(
  values: EventDimensionSelection, typed: Record<string, unknown> | undefined,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...(typed ?? {}) };
  for (const dim of EVENT_DIMENSIONS) {
    if (dim === NESTED_DIM) continue;
    const v = values[dim];
    if (v === '' || v === undefined) continue;
    out[dim] = v;
  }
  if (values.label_return_mode !== '') {
    const existing = (typed?.label_definition ?? {}) as Record<string, unknown>;
    out.label_definition = { ...existing, label_return_mode: values.label_return_mode };
  }
  return out;
}

/**
 * 🔴 **同一個維度不得有兩個來源**：下拉選了、而 JSON 批次預設或 CSV 欄對映也給了同一欄
 * ⇒ 回傳阻擋訊息（**不自行決定誰贏**）。靜默覆蓋是本 epic 反覆付過代價的形態。
 */
export function dimensionDefaultConflicts(
  values: EventDimensionSelection,
  typed: Record<string, unknown> | undefined,
  mappedFields: readonly string[],
): string[] {
  const out: string[] = [];
  for (const dim of EVENT_DIMENSIONS) {
    if (values[dim] === '' || values[dim] === undefined) continue;
    const inTyped = dim === NESTED_DIM
      ? (typed?.label_definition as Record<string, unknown> | undefined)?.[dim] !== undefined
      : typed?.[dim] !== undefined;
    if (inTyped) {
      out.push(`${dim} 同時由上方下拉與「批次預設 JSON」給值——請只留一個來源（平台不替你決定誰優先）`);
    }
    if (mappedFields.includes(dim)) {
      out.push(`${dim} 同時由上方下拉與 CSV 欄對映給值——請只留一個來源`);
    }
  }
  return out;
}

/**
 * 契約之 `decision_offset_bars.min`（**唯一**下界來源；任何地方都不得寫死 `0`）。
 * 契約缺該鍵 ⇒ 拋錯而非退回 0：靜默取 0 會讓「契約改了」與「契約沒改」長得一樣。
 */
export function contractDecisionOffsetMin(contract: unknown = EVENT_DIM_CONTRACT_MIRROR): number {
  const node = dimContractNode(contract, 'decision_offset_bars');
  if (typeof node?.min !== 'number') throw new Error('契約缺少 decision_offset_bars.min');
  return node.min;
}
