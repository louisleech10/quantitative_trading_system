/**
 * GAP-3 UX **Task 7.1** — 五個批次維度之「可操作選項集合」之**唯一**導出處。
 *
 * `selectable(path, dim) = accepted(dim) − pathExclusions(path, dim)`（SPEC L2849–2871）
 *
 * 🔴 **兩個來源都不是人工清單**：
 *   - `accepted(dim)` 由**契約**導出（`accepted` 鍵；無該鍵者取 `enum` 全集）；
 *   - `pathExclusions` 由**單一具名常數** `EVENT_DIM_PATH_EXCLUSIONS` 導出（SPEC L2854–2860 五列封閉）。
 *
 * 🔴 **為什麼是鏡像而不是直接 import 契約 JSON**（R3 群集 C 更正）：
 * **不是**因為做不到——`frontend/tsconfig.json` 有 `resolveJsonModule: true`，
 * `eventMetricsGlossary.ts` 就是直接 `import` 契約檔的（`CODEX-R3-P2-01` 推翻了我原本的說法）。
 * 鏡像是**刻意的雙源設計**：Task 7.2 之機械閘要能在「契約改了而 UI 沒跟」時轉紅，
 * 而那要求 **UI 側與期望值側來源不同**。兩邊都讀真契約 ⇒ 契約變異時兩側同動、
 * `7.2-M1` 直接變成 false negative（本批第一版就是這樣，當場錄到**空紅集合**）。
 * 漂移由 `eventContractOptions.test.tsx` 之「契約鏡像防漂移」逐鍵比對守住。
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
  /** `G3-D2` D1.5：誠實預設之唯一來源（前端禁硬編字面）。見 `contractDefault()`。 */
  default?: string;
}

/**
 * 契約之**同形狀鏡像片段**。
 * 🔴 這裡的每一個值都逐字取自 `momentum/Analysis/contracts/event_import_contract.json`，
 *    由 `eventContractOptions.test.tsx` 之「契約鏡像防漂移」對證；**改契約而沒改這裡，測試會紅**。
 *    （R3 群集 E `COMPOSER-R3-P2-01`：原本寫成不存在的 `eventDimensions.test.ts`。）
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
      // 🔴 `G3-D2` D1.5：鏡像同步契約之 `default`（原檔 §F-3′ 誠實預設之唯一來源）。
      //    漂移由 `eventContractOptions.test.tsx` 逐鍵比對真契約守住。
      default: 'trigger_close',
    },
    decision_offset_bars: { type: 'int', min: 0 },
    label_definition: {
      fields: {
        label_return_mode: {
          enum: ['open_to_close', 'open_to_horizon_close', 'close_to_close'],
          default: 'close_to_close',
        },
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
  // 🔴 `G3-D2` D1.5（2026-09-04）：`B` 解灰。`A` 仍排除但**理由改了**——
  //    它不是「未交付」，而是**已併入 `B`**（裁定① 2026-09-03）：有無用未來根
  //    由 `lookahead_bars_declared` 之深度宣告區分，不由 scenario 值區分。
  '/search|scenario': {
    values: ['A', 'two_stage'],
    reason: 'A 已併入預測型（B）；有無用未來根由深度宣告（lookahead_bars_declared）區分，'
      + '不由 scenario 值區分（裁定① 2026-09-03）。two_stage 之兩段式 label 路徑於 Phase D3 交付',
  },
  // 🔴 D1.5：`trigger_open` 自排除集合**移除**（＝解灰為可選）。
  //    其餘三值留待 D4.2（全矩陣＋成對可行域）。
  '/search|entry_price_semantic': {
    values: ['next_open', 'decision_bar_open', 'decision_bar_close'],
    reason: F5_REASON,
  },
  // 🔴 D1.5：兩個 `open_to_*` 皆移除（三種報酬選項；取價修法已於 B-D0 落地）。
  //    ⇒ `/search|label_return_mode` 已無任何排除值，但**保留鍵並置空**而非刪鍵：
  //    刪鍵會讓「這個 (path, dim) 從未被考慮過」與「考慮過且結論是全開」在碼上無從區分。
  '/search|label_return_mode': {
    values: [],
    reason: F5_REASON,
  },
  '/ic-analysis|entry_price_semantic': {
    values: ['next_open', 'decision_bar_open', 'decision_bar_close'],
    reason: F5_REASON,
  },
  '/ic-analysis|label_return_mode': {
    values: [],
    reason: F5_REASON,
  },
};

/**
 * `G3-D2` D1.5：某維度之**契約宣告預設值**（誠實預設之唯一來源）。
 *
 * 🔴 取不到 ⇒ **拋錯，不回退任何字面**。回退等於在前端造出第二份預設值：
 * 契約把 `default` 從 `trigger_close` 改成別的，UI 會安靜地繼續用舊值，
 * 而那個舊值仍是合法枚舉 ⇒ 沒有任何測試會紅。這正是本函式取代硬編碼字面的理由。
 *
 * 🔴 同時驗 `default ∈ enum/accepted`：契約寫了枚舉外之預設 ⇒ 當場炸，不讓它傳到 UI。
 */
export function contractDefault(
  dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): string {
  const node = dimContractNode(contract, dim);
  const value = node?.default;
  if (typeof value !== 'string' || value === '') {
    throw new Error(`契約之 ${dim} 缺 default（路徑 ${EVENT_DIM_CONTRACT_PATHS[dim].join('.')}.default）`);
  }
  const allowed = node?.accepted ?? node?.enum ?? [];
  if (!allowed.includes(value)) {
    throw new Error(`契約之 ${dim}.default=${value} 不在其 accepted/enum 內`);
  }
  return value;
}

/**
 * `G3-D2` D1.7：IC 分析頁之「報酬量法」三選項（裁定② 2026-09-03）。
 *
 * 使用者選的是**白話的量法**，不是兩個枚舉欄；底層仍寫入 `event_label_spec` 之
 * `entry_price_semantic`／`label_return_mode` 兩欄——**這不是第二份支援矩陣**，
 * 而是矩陣內三個組合的**具名捷徑**。
 *
 * 🔴 **B-D1 只開這三個 preset，不開「進階直改兩欄」**：兩個 select 各自列值會列出
 * `(trigger_close, open_to_close)` 這種**矩陣外**的組合（幾何上窗長 0），使用者選得到卻算不出來。
 * 進階直改留待 D4.2 之 pair-aware `dimOptions(selection)` 落地後才開放。
 */
export const RETURN_MEASURE_PRESETS = [
  {
    key: 'same_bar',
    label: '當根',
    hint: '事件那一根的開盤買、同一根收盤賣（不用答案窗 h）',
    entry_price_semantic: 'trigger_open',
    label_return_mode: 'open_to_close',
  },
  {
    key: 'follow_through',
    label: '續漲',
    hint: '從事件那一根的收盤起算，看之後 h 根的漲跌',
    entry_price_semantic: 'trigger_close',
    label_return_mode: 'close_to_close',
  },
  {
    key: 'hold',
    label: '持有',
    hint: '事件那一根的開盤買，持有 h 根到收盤',
    entry_price_semantic: 'trigger_open',
    label_return_mode: 'open_to_horizon_close',
  },
] as const;

export type ReturnMeasurePresetKey = (typeof RETURN_MEASURE_PRESETS)[number]['key'];

/** `(entry, mode)` → preset；不是任何 preset ⇒ `undefined`（送出守衛據此阻擋）。 */
export function returnMeasurePresetOf(
  entry: string | undefined, mode: string | undefined,
): (typeof RETURN_MEASURE_PRESETS)[number] | undefined {
  return RETURN_MEASURE_PRESETS.find(
    (p) => p.entry_price_semantic === entry && p.label_return_mode === mode,
  );
}

/**
 * 送出守衛：`event_label_spec` 之 `(entry, mode)` 必須是三個 preset 之一。
 *
 * 🔴 **具名邊界（比後端矩陣嚴）**：後端 `SUPPORTED_MATRIX` 有**四**對，本守衛只放行**三**個
 * preset ⇒ `(trigger_open, close_to_close)` 雖為後端支援組合，在 D1 之 UI 仍被擋。
 * 這是刻意的：D1 的 UI 根本產不出那一對，能出現只有偽造或程式化設值；
 * **寧可誤擋一個支援組合，也不要放行一個矩陣外組合**（後者會讓使用者拿到 fail-closed 錯誤）。
 * D4.2 開放進階直改時，本守衛改為對 pair-aware 之可行域判定。
 */
export function isSubmittableLabelSpec(spec: unknown): boolean {
  if (!spec || typeof spec !== 'object') return false;
  const s = spec as Record<string, unknown>;
  const entry = s.entry_price_semantic;
  const mode = s.label_return_mode;

  // 🔴 **兩欄皆缺 ⇒ 放行**：這不是漏洞，是分工。使用者只改了 h 時，面板產出的 spec
  //    本來就沒有這兩欄，由**後端**依該批宣告深度導出預設（D1.7 後端半邊）。
  //    在此擋下等於要求前端自己算深度 ⇒ 第二份預設值規則。
  const bothAbsent = entry === undefined && mode === undefined;
  if (!bothAbsent) {
    // 只給一半也不行：半組值送到後端會與導出的另一半拼成未預期組合。
    if (typeof entry !== 'string' || typeof mode !== 'string') return false;
    if (returnMeasurePresetOf(entry, mode) === undefined) return false;
  }
  // `horizon_bars` 若有給，須為正整數（「當根」下亦送 1 之 inert 哨兵）。
  const h = s.horizon_bars;
  if (h === undefined) return true;
  return typeof h === 'number' && Number.isInteger(h) && h >= 1;
}

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
  // 🔴 R4 `CODEX-R4-P2-01`：契約之 `decision_offset_bars` 為 `int`。
  //    非整數**顯式擋下並說出原因**，不由 clamp 靜默截成整數——後者會讓使用者
  //    以為自己填的是 1.9 而系統收了 1，且永遠看不到契約那條拒絕。
  const k = values.decision_offset_bars;
  if (k !== '' && k !== undefined && !Number.isInteger(k)) {
    out.push(`decision_offset_bars 必須是整數（契約 event_import_contract.json 之 type: int）；收到 ${k}`);
  }
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
 * 🔴 **R3 群集 A**：把 `k` 夾進該路徑之合法範圍。
 *
 * 為什麼要有這支（三家一致之 P1）：HTML 之 `min`／`max` **只是提示**，
 * `fireEvent.change` 與使用者打字都能送出範圍外的值；而 `buildEventContractRecords`
 * 只擋 `k < min`（契約下界），**擋不到「本路徑鎖 0 但傳了 3」**
 * ⇒ 鎖 0 的路徑上真的會落檔 `k=3`，UI 文案說鎖 0 而檔案裡不是。
 *
 * clamp 而非 raise：本函式在 `onChange` 上，raise 會讓使用者按鍵時整頁炸掉；
 * 鎖定路徑之 `readOnly` 才是第一層，本函式是**程式化設值**那條路的第二層。
 * 非有限值（`NaN`／空字串轉數字）⇒ 回下界，不讓 `NaN` 流進 state。
 *
 * 🔴 **本函式只夾範圍，不管整數性**（R4 `CODEX-R4-P2-01`）：
 * 原版寫了 `Math.trunc`，於是在自由路徑上 `0.5 → 0`、`1.9 → 1`——**靜默改值**。
 * 契約之 `decision_offset_bars` 是 `int`，而 `buildEventContractRecords` 已用
 * `Number.isInteger(k)` **顯式拒絕**小數 ⇒ 前端先偷偷截掉，使用者就永遠看不到那個拒絕，
 * 兩端於是各有一套規則（B4 R5 已為同型付過代價）。整數性交給既有之 fail-closed 與
 * 送出前的可見阻擋，本函式不代勞。
 */
export function clampDecisionOffset(
  value: number, range: { min: number; max: number | null },
): number {
  if (!Number.isFinite(value)) return range.min;
  const lower = Math.max(value, range.min);
  return range.max === null ? lower : Math.min(lower, range.max);
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
