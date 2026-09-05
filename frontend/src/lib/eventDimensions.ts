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
  /**
   * `G3-D2` D1.5：誠實預設之唯一來源（前端禁硬編字面）。見 `contractDefault()`。
   *
   * 🔴 型別為 `string | number`：enum 維度之 default 是字串，而 `decision_offset_bars`
   * 是 `int` 欄、其契約 default 是**數字 `0`**。原本只宣告 `string` ⇒ 鏡像放不進那個 0，
   * 於是鏡像少了一個鍵而沒人發現（`GROK-R1-P2-01` 強化鍵集後當場現形）。
   * `contractDefault()` 仍只接受字串——它服務的是 enum 維度之重設，數值欄不走它。
   */
  default?: string | number;
  /**
   * `G3-D2` D4.2：**成對**拒收表 `{label_return_mode 值: [entry_price_semantic 值, ...]}`。
   * 只住 `label_return_mode` 節點（契約以 mode 為鍵）；`entry_price_semantic` 方向由
   * `pairRejectedReason()` **反查**同一張表導出，不另存一份反向表。
   */
  rejected_pairs?: Readonly<Record<string, readonly string[]>>;
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
    // 🔴 `GROK-R1-P2-01`（R1 閉合）補上 `default`：契約寫著 `"default": 0`，
    //    而鏡像原本沒有這一鍵——強化後的逐鍵對證當場抓到（這就是它存在的理由）。
    decision_offset_bars: { type: 'int', min: 0, default: 0 },
    label_definition: {
      fields: {
        label_return_mode: {
          enum: ['open_to_close', 'open_to_horizon_close', 'close_to_close'],
          default: 'close_to_close',
          // 🔴 `G3-D2` D4.2：成對拒收（幾何窗長 0）。逐字鏡像契約
          //    `label_definition.fields.label_return_mode.rejected_pairs`。
          rejected_pairs: { open_to_close: ['trigger_close', 'decision_bar_close'] },
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
  // 🔴 `G3-D2` D3.1（2026-09-05）：`two_stage` **解灰**——兩段式走「未標籤匯出」路徑
  //    （`label` 鍵缺席、`label_origin='search_unlabeled'`，補標後以 `user_csv` 匯入）。
  //    ⇒ 本路徑之排除集合只剩 `A` 一個值。
  '/search|scenario': {
    values: ['A'],
    reason: 'A 已併入預測型（B）；有無用未來根由深度宣告（lookahead_bars_declared）區分，'
      + '不由 scenario 值區分（裁定① 2026-09-03）',
  },
  // 🔴 D4.2（2026-09-05）：其餘三值**全部解灰**——後端 `SUPPORTED_PAIRS` 已為 13 對
  //    （5 entry × 3 mode 減兩個幾何零窗對）⇒ 路徑排除清空。
  //    **保留鍵並置空**而非刪鍵：刪鍵會讓「這個 (path, dim) 從未被考慮過」與
  //    「考慮過且結論是全開」在碼上無從區分（同 `label_return_mode` 之理由）。
  //    仍不可選的兩個組合改由 `kind: 'pair_rejected'` 表達——它是**成對**限制，
  //    不是單維度排除，硬塞進本表會把「trigger_close 這個值不能用」講錯。
  '/search|entry_price_semantic': {
    values: [],
    reason: F5_REASON,
  },
  // 🔴 D1.5：兩個 `open_to_*` 皆移除（三種報酬選項；取價修法已於 B-D0 落地）。
  //    ⇒ `/search|label_return_mode` 已無任何排除值，但**保留鍵並置空**而非刪鍵：
  //    刪鍵會讓「這個 (path, dim) 從未被考慮過」與「考慮過且結論是全開」在碼上無從區分。
  '/search|label_return_mode': {
    values: [],
    reason: F5_REASON,
  },
  // 🔴 D4.2：同上，`/ic-analysis` 之三元組排除值一併清空。
  '/ic-analysis|entry_price_semantic': {
    values: [],
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
 * 送出守衛：`event_label_spec` 之 `(entry, mode)` 必須在**支援矩陣**內。
 *
 * 🔴 **`G3-D2` D4.2 改寫**：D1 之守衛只放行三個 preset（比後端矩陣嚴），理由是
 * 「D1 的 UI 產不出其他組合」。D4.2 開放**進階直改兩欄** ⇒ UI 現在產得出全部 13 對，
 * 守衛必須跟著改成 pair-aware，否則使用者選得到卻送不出去。
 * 判定＝**兩個枚舉皆為契約 enum 值** ∧ **不是 `rejected_pairs` 之對**
 * ——與後端 `SUPPORTED_PAIRS`（全積減拒收）逐字同構，由 `contractEnumWiring` 之對證閘守。
 *
 * 🔴 **k 不在守衛內**：k 之上界是逐事件可行域（資料決定），前端算不出來；
 * 超界之後果是該事件 loud 進 failures，不是送出被擋。
 */
export function isSubmittableLabelSpec(
  spec: unknown, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): boolean {
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
    if (!acceptedValues('entry_price_semantic', contract).includes(entry)) return false;
    if (!acceptedValues('label_return_mode', contract).includes(mode)) return false;
    if (isRejectedPair(entry, mode, contract)) return false;
  }
  // `horizon_bars` 若有給，須為正整數（「當根」下亦送 1 之 inert 哨兵）。
  const h = s.horizon_bars;
  if (h !== undefined && !(typeof h === 'number' && Number.isInteger(h) && h >= 1)) return false;
  // `decision_offset_bars` 若有給，須為 >= 契約 min 之整數（值域來自契約，不寫死 0）。
  const k = s.decision_offset_bars;
  if (k === undefined) return true;
  return typeof k === 'number' && Number.isInteger(k) && k >= contractDecisionOffsetMin(contract);
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

/* ─────────────────────────────────────────────────────────────────────────────
 * `G3-D2` **D4.2**：成對拒收（`kind: 'pair_rejected'`）
 * ────────────────────────────────────────────────────────────────────────── */

/** 判定成對拒收所需之**當前選值**（只用得到兩欄；其餘維度與 pair 無關）。 */
export interface PairSelection {
  entry_price_semantic?: string;
  label_return_mode?: string;
}

/**
 * 契約之成對拒收表（唯一取值點）。形狀＝`{mode: [entry, ...]}`。
 *
 * 🔴 表**只有一份**（住 `label_return_mode` 節點），反向由本檔反查，
 *    不另存 `{entry: [mode,...]}`——兩份必然漂移，而漂移的方向是「UI 放行後端算不出的組合」。
 */
export function rejectedPairs(
  contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): Readonly<Record<string, readonly string[]>> {
  return dimContractNode(contract, 'label_return_mode')?.rejected_pairs ?? {};
}

/** 成對拒收之理由字面（由契約導出，前端不硬編）。 */
export function pairRejectedReasonText(mode: string, entry: string): string {
  return `(${entry}, ${mode}) 幾何上答案窗長度為 0（進場價與結算價落在同一根的同一個時點）`
    + '⇒ 分析層永遠算不出報酬；換 k 或 h 都不會改變這件事';
}

/**
 * 🔴 **雙向**判定：某維度之某值在**目前另一維之選值**下是否被成對拒收。
 *
 * - `dim === 'label_return_mode'`：`selection.entry_price_semantic ∈ rejected_pairs[value]` ⇒ 拒；
 * - `dim === 'entry_price_semantic'`：`selection.label_return_mode` 之 pair 含 `value` ⇒ 拒。
 *
 * 另一維未選（`undefined`／`''`）⇒ **不拒**：還沒選就先擋，使用者連進入合法組合的路都沒有。
 */
export function pairRejectedReason(
  dim: EnumEventDimension, value: string,
  contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
  selection?: PairSelection,
): string | undefined {
  if (!selection) return undefined;
  const table = rejectedPairs(contract);
  if (dim === 'label_return_mode') {
    const entry = selection.entry_price_semantic;
    if (!entry) return undefined;
    return (table[value] ?? []).includes(entry) ? pairRejectedReasonText(value, entry) : undefined;
  }
  if (dim === 'entry_price_semantic') {
    const mode = selection.label_return_mode;
    if (!mode) return undefined;
    return (table[mode] ?? []).includes(value) ? pairRejectedReasonText(mode, value) : undefined;
  }
  return undefined;
}

/** `(entry, mode)` 是否為幾何必拒之對（送出守衛用；**不看** `selection`，看實際要送的兩值）。 */
export function isRejectedPair(
  entry: string | undefined, mode: string | undefined,
  contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): boolean {
  if (!entry || !mode) return false;
  return (rejectedPairs(contract)[mode] ?? []).includes(entry);
}

/** 成對重設之結果：新選值 ＋ 給使用者看的揭露字串（`reset === undefined` ⇒ 不需重設）。 */
export interface PairResetOutcome {
  selection: PairSelection;
  reset?: { dim: EnumEventDimension; from: string; to: string; disclosure: string };
}

/**
 * 🔴 **既選非法 pair ⇒ 另一維自動重設為契約 `default`** 並回傳揭露字串。
 *
 * 為什麼不是「靜默保留非法組合，送出時才擋」：那讓畫面上同時存在兩個看起來都被選中的
 * 值，而它們合起來不可能送出——使用者要自己推理是哪一個該改。
 * 為什麼不是「回退到上一個合法值」：上一個值是 UI 的歷史狀態，不是契約的事實；
 * 重設一律讀契約 `default`（`contractDefault()`），前端不硬編字面。
 *
 * `changedDim` ＝使用者**剛改**的維度 ⇒ 保留它、重設另一維。
 */
export function resolvePairConflict(
  selection: PairSelection, changedDim: EnumEventDimension,
  contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
): PairResetOutcome {
  const { entry_price_semantic: entry, label_return_mode: mode } = selection;
  if (!isRejectedPair(entry, mode, contract)) return { selection };
  const other: EnumEventDimension = changedDim === 'label_return_mode'
    ? 'entry_price_semantic' : 'label_return_mode';
  const from = String(selection[other]);
  const preferred = contractDefault(other, contract);
  const withValue = (v: string): PairSelection => ({ ...selection, [other]: v });

  // 🔴 **具名偏離 `D-001` D4.2**（實作時由本檔之 vitest 當場打穿）：
  //    D-001 寫「另一維自動重設為契約 `default`」，但契約之
  //    `entry_price_semantic.default = "trigger_close"` **本身就在** `open_to_close`
  //    的拒收對裡 ⇒ 在「使用者改 mode 成 open_to_close」這個方向上，重設為 default
  //    會直接落回非法組合。D-001 沒有涵蓋這個方向。
  //    ⇒ 規則細化為兩段（**皆由契約導出，不硬編任何字面**）：
  //      ① 契約 `default` 合法 ⇒ 用它（D-001 原意，覆蓋另一個方向）；
  //      ② 否則 ⇒ 取該維度**契約 enum 順序**中第一個合法值，並在揭露字串裡
  //         明說「契約預設在這個組合下也不合法，改用第一個可用值」。
  //    ②仍是**確定性**且**單一來源**（契約 enum 順序），不是猜。
  let to = preferred;
  let usedFallback = false;
  if (isRejectedPair(withValue(to).entry_price_semantic, withValue(to).label_return_mode, contract)) {
    const legal = acceptedValues(other, contract).find(
      (v) => !isRejectedPair(withValue(v).entry_price_semantic, withValue(v).label_return_mode, contract),
    );
    // 🔴 一個合法值都沒有 ⇒ **fail-closed**：那代表契約把某個 mode 的所有 entry 都拒了，
    //    是契約自相矛盾，靜默挑一個值會把它藏起來。
    if (legal === undefined) {
      throw new Error(
        `契約之 ${other} 在此組合下無任何合法值（rejected_pairs 拒光整個枚舉）——拒絕猜測`,
      );
    }
    to = legal;
    usedFallback = true;
  }
  const next = withValue(to);
  const disclosure = `因 pair 拒收已重設：${other} 由 ${from} 改為 ${to}`
    + (usedFallback
      ? `（契約預設 ${preferred} 在這個組合下也不合法，故取契約 enum 順序中第一個可用值）`
      : '（契約預設）')
    + `。${pairRejectedReasonText(String(mode), String(entry))}`;
  return { selection: next, reset: { dim: other, from, to, disclosure } };
}

/**
 * 🔴 **可操作選項集合**＝`accepted(dim) − pathExclusions(path, dim)`。
 *
 * 順序沿用契約之 `accepted`／`enum` 順序（UI 呈現順序因此也由契約決定，不另排）。
 */
export function selectable(
  path: EventDimPath, dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
  selection?: PairSelection,
): readonly string[] {
  const excluded = new Set(pathExclusions(path, dim));
  return acceptedValues(dim, contract).filter(
    (v) => !excluded.has(v) && pairRejectedReason(dim, v, contract, selection) === undefined,
  );
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
  kind: 'selectable' | 'contract_rejected' | 'path_excluded' | 'pair_rejected';
  /** 不可選時之理由（可選時為 `undefined`）。 */
  reason?: string;
}

/**
 * `selection` 為**可選**參數（`G3-D2` D4.2）：不給 ⇒ 舊行為（selection-free），
 * 供 Task 7.2 之 selection-free 機械閘沿用；給了才會出現 `kind: 'pair_rejected'`。
 *
 * 🔴 判定順序＝`contract_rejected` → `pair_rejected` → `path_excluded`：
 *    三者都可能同時成立，而使用者只看得到一句話——先講**最不可能改變**的那個原因
 *    （契約恆拒 ⇒ 永遠不行；成對拒收 ⇒ 改另一維就行；路徑排除 ⇒ 換頁面就行）。
 */
export function dimOptions(
  path: EventDimPath, dim: EnumEventDimension, contract: unknown = EVENT_DIM_CONTRACT_MIRROR,
  selection?: PairSelection,
): readonly EventDimOption[] {
  const node = dimContractNode(contract, dim);
  const all = node?.enum ?? acceptedValues(dim, contract);
  const ok = new Set(selectable(path, dim, contract, selection));
  return all.map((value) => {
    if (ok.has(value)) return { value, disabled: false, kind: 'selectable' as const };
    const rejected = contractRejectedReason(dim, value, contract);
    if (rejected !== undefined) {
      return { value, disabled: true, kind: 'contract_rejected' as const, reason: rejected };
    }
    const paired = pairRejectedReason(dim, value, contract, selection);
    if (paired !== undefined) {
      return { value, disabled: true, kind: 'pair_rejected' as const, reason: paired };
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
  // 🔴 `G3-D2` **D4.2**：`/ic-analysis` 之 k **解鎖**——k 已不在支援矩陣內，
  //    其上界是**逐事件成對可行域**（後端 `feasible(e,k,h)` 導出之 `k_max_feasible_at_h`），
  //    而那是**資料**決定的、前端算不出來 ⇒ 這裡不得再假裝有一個 `max`。
  //    超出可行域之後果是逐事件 loud 進 failures（不是 400），揭露由後端回報。
  // 🔴 `G3-D2` **D4.3**：`/search` 之 k 控制項**整個移除**（k 改於分析頁設定），
  //    但本函式仍回 locked——它同時服務「若有人程式化設值」之 clamp 第二層。
  if (path === '/data-preparation' || path === '/ic-analysis') {
    return { min, max: null, locked: false };
  }
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
