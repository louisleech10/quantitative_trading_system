/**
 * GAP-3 B5.2：把 /search 結果組成事件契約（event_import_contract.json）新 schema 記錄。
 * 純組裝、不算統計；欄位語意：t0＝觸發根 open（ms UTC）、label＝正反例標記、direction 由條件方向推、
 * scenario 預設 C（確認型）、entry_price_semantic 預設 trigger_close（Task 7.0 依 §F-3′ 更正）、
 * label_definition 由搜尋條件摘要＋digest 組。
 * 使用者匯入前仍可手改；後端 validator 為唯一真相源（本檔不重做檢查）。
 */
import type { CaseData } from './types';
import { canonicalEventId } from './eventId';
import { ruleDigestOf, ruleSummaryText } from './ruleDigest';
import { contractDecisionOffsetMin, contractDefault } from './eventDimensions';
// 🔴 D3.1 R2：`label_origin` 之字面由**真契約**導出（見 `labelOriginFromContract`）。
import contract from '../../../momentum/Analysis/contracts/event_import_contract.json';

/** Task 4.1：附帶報酬欄之候選 h（1..12）；預設全選。 */
export const ATTACHED_HORIZONS: readonly number[] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

/**
 * `/search` 匯出之**五個批次維度**之預設值。
 *
 * 🔴 Task 4.1b **邊界②（防寫死漂移）**：揭露區塊顯示的值必須 `==` 匯出檔實際寫入的值。
 * 兩處各寫一份字面就會漂 ⇒ **常數是唯一來源**，組裝與顯示都讀它。
 * （`control_kind` 使用者從未選過、亦不知其存在——4.1b 就是為了把它講出來。）
 *
 * 🔴 **Task 7.0（本批）新增後三個常數**：原本 `decision_offset_bars`／`label_return_mode`
 * 之預設是**寫死在 `buildEventContractRecords` 的物件字面裡**，Task 7.3 的揭露區要顯示它們時
 * 只能再抄一份字面 ⇒ 就是 4.1b 已經付過代價的那個病。故一併提成常數。
 */
export const EVENT_EXPORT_SCENARIO = 'C' as const;
export const EVENT_EXPORT_CONTROL_KIND = 'user_labeled_same_trigger' as const;
/**
 * 🔴 **Task 7.0 依 §F-3′ 把預設由 `trigger_open` 改為 `trigger_close`**（D-4 合法變更）。
 *
 * 為什麼可以改而不算改壞：匯出端自 Task 4.1 ② 起**已不寫 `label_value`**
 * ⇒ 本欄純為**宣告**，沒有任何數值依它計算 ⇒ 改的只有宣告欄字面，
 * **G-2 事件 golden 為 byte 級不變**（golden 跑 IC 管線、不碰匯出端）。
 * 🔴 §F-1′ 之支援矩陣為 `(trigger_close, close_to_close, k=0)`——舊預設 `trigger_open`
 * 落在矩陣外，等於「預設值本身就是分析層不支援的組合」，那才是原本的錯。
 *
 * 🔴 **`G3-D2` D1.5（2026-09-04）：改為讀契約 `default`，不再是本檔的字面常數。**
 * 硬編碼字面與契約 `required_fields.entry_price_semantic.default` 是兩份預設值：
 * 契約改了而這裡沒改，UI 會安靜地繼續用舊值，且舊值仍是合法枚舉 ⇒ 沒有測試會紅。
 * 常數名保留以免既有 import 斷裂，值改由 `contractDefault()` 導出。
 */
export const EVENT_EXPORT_ENTRY_PRICE_SEMANTIC = contractDefault('entry_price_semantic');
export const EVENT_EXPORT_LABEL_RETURN_MODE = contractDefault('label_return_mode');
export const EVENT_EXPORT_DECISION_OFFSET_BARS = 0 as const;

/**
 * 由契約 `optional_fields.label_origin.enum` 取出同名值；不在 enum 內即**拋錯**。
 *
 * 🔴 `G3-D2` D3.1 R2（`CODEX-R2-P2-02` ③）：`EVENT_EXPORT_LABEL_ORIGIN` 的註解原本就寫著
 * 「字面不在此硬寫、取不到即拋錯」，**而碼裡就是一個硬寫的字面**——註解與碼不符
 * （本 epic 已抓過同型：B-D1 R2 群集 1 之 Panel 註解）。
 * `R-LABEL-SOT` 當時也只對證了 `search_unlabeled` 那一半。⇒ 兩個常數一起改成真的由契約取。
 */
function labelOriginFromContract(name: string): string {
  const enumValues = (contract as {
    optional_fields: { label_origin: { enum: string[] } };
  }).optional_fields.label_origin.enum;
  if (!enumValues.includes(name)) {
    throw new Error(
      `label_origin '${name}' 不在契約 optional_fields.label_origin.enum 內`
      + `（現有：${enumValues.join('、')}）。契約改了而這裡沒跟上，fail-closed。`,
    );
  }
  return name;
}

/**
 * `G3-D2` D1.5：`/search` 匯出批之 `label_origin`（provenance）。
 * 值由契約導出（見 `labelOriginFromContract`）。
 */
export const EVENT_EXPORT_LABEL_ORIGIN = labelOriginFromContract('search_positive_case');

export interface EventExportOptions {
  timeframe: string;
  conditions: unknown[];
  priceChangeMethod: string;
  /**
   * Task 4.1 ①：要附帶哪些 `future_{h}bar_return`（**純供 Excel 攜帶**）。
   *
   * 🔴 **不進 `ic_feed`、不決定任何 horizon、不參與深度導出**（契約 doc 字面同此，
   * `D-004 A-020`）。改變本清單**不得**影響 `lookahead_bars_declared` 與 `window.horizon_bars`。
   */
  attachedHorizons?: readonly number[];
  /**
   * Task 4.1 ③：逐 timeframe 之**真實深度**＝使用者於匯出前**宣告**之 `declared_window_bars`
   * （R 重開 D-8／Task 1.9′：逐鍵複製，**不與任何欄位取 max**；Phase 2 之導出路徑已退役）。
   *
   * 🔴 前端**不推斷**深度——不得由附帶欄或欄名推斷（D-7：偵測不可能）。
   * 🔴 每列之 `label_definition.window.horizon_bars` ＝ `max(1, 本 map[該列 tf])`，
   *    **下限 1 是契約之 serialization floor**；深度 0 時兩者**刻意不相等**（§D-3′-a(i)）。
   * 🔴 **必填**（R1 `CODEX-R1-P1-02`）：Task 4.1 ③要求匯出檔必帶該宣告；
   *    缺該列 tf 之鍵時 `windowHorizonBarsFor` 會**拋錯**，不會靜默寫成 1。
   */
  lookaheadBarsDeclared: Record<string, number>;
  direction?: 'long' | 'short';
  /**
   * ── Task 7.0：**五個批次維度**（`scenario`／`controlKind`／`entryPriceSemantic`／
   * `labelReturnMode`／`decisionOffsetBars`）之參數化。 ─────────────────────────────
   *
   * 🔴 型別之值域一律**照契約 `enum` 全集**寫（`event_import_contract.json`），
   *    **不是** `accepted` 子集：哪些值在哪個路徑可選是 **Task 7.1 的 `selectable(path, dim)`**
   *    的事，把契約恆拒值從型別裡拿掉會讓 7.1 連「顯示為 disabled ＋ 理由」都做不到
   *    （契約 `rejected_with_reason` 之字面就無處可掛）。
   * 🔴 本 Task **只做型別與參數化，不加 UI、不動後端**（SPEC Task 7.0 邊界）。
   * 🔴 **不含 `counterexampleKind`**：那是**逐列選填欄**，不是批次維度（R5 群集 G）。
   */
  scenario?: 'A' | 'B' | 'C' | 'two_stage';
  entryPriceSemantic?: 'trigger_open' | 'trigger_close' | 'next_open' | 'decision_bar_open' | 'decision_bar_close';
  /** 契約 `enum` 四值；`platform_random_bars` 為契約恆拒（`not_implemented_platform_random_bars`）。 */
  controlKind?: 'user_labeled_same_trigger' | 'user_labeled_other' | 'platform_same_trigger_rule' | 'platform_random_bars';
  /**
   * 🔴 **寫入路徑為巢狀**：`label_definition.label_return_mode`，**不是頂層**。
   * 寫錯位置會使契約 schema 檢核通過但語意落在錯的物件（SPEC Task 7.0「不可做」）。
   */
  labelReturnMode?: 'open_to_close' | 'open_to_horizon_close' | 'close_to_close';
  /**
   * 契約為 `type: int, min: 0`（**非 enum**）⇒ Task 7.2 ③ 對它另立一層驗收
   * （有可輸入控制項／`-1` fail-closed／`k` 落檔 `=== k`），不走 enum 減法。
   */
  decisionOffsetBars?: number;
  /**
   * 後端就本結果集算好的來源 canonical 文字（`SearchResultData.source_file_text`）。
   * 🔴 前端**不得**自行序列化或雜湊——見 `ruleDigest.ts` 檔頭與 SPEC Task 1.3 之 R13 定案。
   */
  sourceFileText: string;
  /** 後端算好的 `source_file_digest`（`sha256(sourceFileText)`）。 */
  sourceFileDigest: string;
  /**
   * 🔴 **可回灌 CSV 專用**（2026-09-01 使用者裁定）：把**沒有正反例標記**的列也產出來，
   * 其 `label` 為 `null`（CSV 落成空欄）。
   *
   * 為什麼要這個選項：匯入端對「缺 `label`」是**整批拒收**（實測 HTTP 422、逐列 reason），
   * 所以 CSV 若把未標記的列**丟掉**，使用者根本看不到它們、也就**無從補標記**
   * ——而「自己決定哪些是正例」正是本 epic 的核心前提。留在檔案裡、`label` 空著，
   * 使用者在 Excel 補完就能整份上傳；沒補的話匯入訊息會逐列指名是哪幾列。
   * 這也讓 R3 `CODEX-R3-P1-01` 之裁定（「CSV 不該因少一個旗標就丟整列」）繼續成立。
   *
   * 🔴 **JSON 匯出不得開這個選項**：契約要求 `label` 必填，帶 `null` 的 JSON 必然被拒。
   */
  includeUnlabeled?: boolean;
  /**
   * `G3-D2` D3.1：**兩段式之兩段條件**（每段一個條件陣列）。
   *
   * 🔴 `scenario === 'two_stage'` 時**必填且長度恰為 2**，否則匯出阻擋
   * （`two_stage_requires_two_stages`）。**不得**在只有一段時降級為 A／B，
   * 也不得靜默寫 `stage_count=1`（SPEC D3.1 邊界③）。
   * 其他 scenario 忽略本欄。
   */
  stageConditions?: readonly (readonly unknown[])[];
}

/** `G3-D2` D3.1：匯出被前端阻擋時丟這個型別，`reason` 為契約／SPEC 之字面代號。 */
export class EventExportBlocked extends Error {
  readonly reason: string;

  constructor(reason: string, message: string) {
    // 🔴 `message` 由 `twoStageExportBlockReason` 產生時**已含代號**，此處不再加前綴
    //    ——加了就變成兩處各自組字串，畫面與例外訊息會漂。
    super(message);
    this.name = 'EventExportBlocked';
    this.reason = reason;
  }
}

/**
 * `G3-D2` D3.1：**兩段式匯出之阻擋判定——唯一一份**。
 *
 * 🔴 `buildEventContractRecords`（丟 `EventExportBlocked`）與 `/search` 頁
 * （把匯出鈕 disable 並顯示理由）**共用本函式**。
 * 若頁面另寫一次 `if (stages.length !== 2)`，那就是第二份判斷——
 * 兩份遲早會漂（本 epic 已因「同一規則兩份實作」踩過三次）。
 *
 * 回 `undefined` ＝ 不阻擋。
 */
/**
 * 一個條件物件是否**帶得出值**（D3.1 R1：判斷「這一段是不是空的」用）。
 *
 * `null`／`undefined` ⇒ 否；陣列（`BETWEEN` 之 `[min, max]`）⇒ 至少一端非 `null` 才算。
 * 非物件或無 `value` 鍵 ⇒ 否（fail-closed：形狀不認得就不當它是條件）。
 */
function hasUsableConditionValue(cond: unknown): boolean {
  if (cond === null || typeof cond !== 'object') return false;
  return isUsableConditionValue((cond as { value?: unknown }).value);
}

/**
 * 單一值是否可用（`G3-D2` D3.1 R2 `CODEX-R2-P2-01`）。
 *
 * 🔴 第一版只驗「非 `null`／`undefined`」⇒ codex production probe 得
 * `empty-string=PASS, NaN=PASS, false=PASS, 0=PASS`：`''`／`NaN`／`false` 都被當成
 * 「有條件」，第二段因此仍算非空。（grok 補充：`/search` 之寫入是
 * `e.target.value ? parseFloat(...) : null`，所以那三種**從 UI 走不到**——
 * 這是**防禦深度**缺口而非使用者路徑缺陷；主委取較嚴版，仍修。）
 *
 * 🔴 `0` 是**合法值**（codex 明列），不得因為「falsy」被一起擋掉。
 * ⇒ 規則：數字須**有限**（排除 `NaN`／`±Infinity`，保留 `0` 與負數）；
 *    字串須**去空白後非空**；`boolean` 不是本頁條件的值型別 ⇒ 不可用。
 */
function isUsableConditionValue(v: unknown): boolean {
  if (v === null || v === undefined) return false;
  if (Array.isArray(v)) return v.some(isUsableConditionValue);
  if (typeof v === 'number') return Number.isFinite(v);
  if (typeof v === 'string') return v.trim() !== '';
  // `boolean` 與其餘型別：本頁之條件值為數值或數值區間，其他型別一律不當成條件。
  return false;
}

export function twoStageExportBlockReason(input: {
  scenario?: string;
  stageConditions?: readonly (readonly unknown[])[];
  lookaheadBarsDeclared?: Record<string, number>;
}): { reason: string; message: string } | undefined {
  if (input.scenario !== 'two_stage') return undefined;
  const stages = input.stageConditions ?? [];
  if (stages.length !== 2) {
    return {
      reason: 'two_stage_requires_two_stages',
      // 代號放在訊息裡（單一來源）：畫面與 `EventExportBlocked.message` 用的是同一份字串。
      message: `[two_stage_requires_two_stages] scenario=two_stage 需要恰兩段條件，目前 ${stages.length} 段。`
        + '兩段式的意思就是「先看第一段成立、再看第二段」——只有一段時它不是兩段式，'
        + '系統不會替你把它當成單段情境送出。請補上第二段（啟用反例條件），或把情境改成 B／C。',
    };
  }
  // 🔴 R1 `CODEX-R1-P1-03`／`GROK-R1-P2-02`：只驗**段數**不驗**段內非空**
  //    ⇒ `[STAGE_1, []]`／`[[], []]` 且深度 ≥1 時放行，第二段成了空殼：
  //    它仍會產出一個 digest（空條件之 digest），摘要因此聲稱「有兩段」而其實只有一段。
  //    ⇒ 任一段為空即擋。沿用同一個代號（使用者要做的事一樣：把第二段補起來）。
  //    🔴 「非空」是**語意**的，不只是 `length > 0`：`BETWEEN` 兩端都沒填時，
  //       條件物件長成 `{operator:'BETWEEN', value:[null,null]}`——它通過了頁面的
  //       `.filter(v != null)`（陣列不是 null），卻不表達任何篩選。
  //       本檔第一版只驗 `length === 0` 而讓它過（我自己的 over 向測試當場抓到）。
  //       ⇒ 判定改為「該段有沒有**任一個帶得出值**的條件」。
  //       🔴 只在此判定，**不動** `opts.conditions`／`ruleSummary` 之既有內容——
  //          那會改變所有既有匯出的 digest，超出 D3.1 範圍。
  const emptyStageIndex = stages.findIndex((s) => !s.some(hasUsableConditionValue));
  if (emptyStageIndex >= 0) {
    return {
      reason: 'two_stage_requires_two_stages',
      message: `[two_stage_requires_two_stages] 第 ${emptyStageIndex + 1} 段沒有任何條件。`
        + '空的一段會產出一個「空條件」的摘要 digest，看起來像兩段、實際只有一段。'
        + '請把該段的條件補起來（反例區至少填一個值），或把情境改成 B／C。',
    };
  }
  // 兩段式之事件相對決策必為未來 ⇒ 深度 0 與該情境自相矛盾（匯入端同名 reason 亦拒）。
  // 🔴 R1 codex 2a：負值／非數字之深度不得被 `Number(v) || 0` 靜默當成 0 而混過去
  //    ——`Number('abc') || 0 === 0`、`-1` 亦然。深度是契約 `int >= 0`，
  //    出現不合法值代表宣告本身壞了，與「深度 0」是兩件事，須各自可辨。
  const rawDepths = Object.values(input.lookaheadBarsDeclared ?? {});
  const badDepth = rawDepths.find(
    (v) => typeof v !== 'number' || !Number.isInteger(v) || v < 0,
  );
  if (badDepth !== undefined) {
    return {
      reason: 'invalid_lookahead_declaration',
      message: `[invalid_lookahead_declaration] 深度宣告含不合法值（${String(badDepth)}）。`
        + '契約要求 lookahead_bars_declared 之每個值為 int >= 0；'
        + '出現其他型別或負值代表宣告本身壞了，系統不會替它猜一個深度。',
    };
  }
  const depths = rawDepths.map((v) => Number(v));
  if (Math.max(0, ...depths) < 1) {
    return {
      reason: 'scenario_depth_inconsistent',
      message: '[scenario_depth_inconsistent] scenario=two_stage 需要至少一個 timeframe 宣告深度 ≥ 1（lookahead_bars_declared）。'
        + '深度 0 表示「事件在決策當下就已知」，那與兩段式互相矛盾，匯入端也會拒收。',
    };
  }
  return undefined;
}

/**
 * `G3-D2` D3.1：two_stage 之未標籤匯出標記。
 *
 * 🔴 契約 `optional_fields.label_origin.not_importable` 含本值 ⇒ **直接匯入必拒**。
 * 這是刻意的：兩段式路徑不產 label，使用者必須在 CSV 自填後改以 `user_csv` 匯入
 * （`/data-preparation` 之 `batch_defaults`）。寫 `user_csv` 等於替使用者宣告他還沒做的事。
 */
export const EVENT_EXPORT_UNLABELED_LABEL_ORIGIN = labelOriginFromContract('search_unlabeled');

/**
 * D3.1：兩段式之 `search_rule_summary` canonical 形狀（契約 `two_stage_shape` 逐字）。
 *
 * 🔴 R1 `CODEX-R1-P2-01`：本函式原本直接用 `stageDigests.length`
 * ⇒ 直呼者可產出 `stage_count: 1` 或 `3`，而契約 `two_stage_shape` 寫死 2 ⇒ 兩者會漂。
 * 「只靠 builder 的前置 guard」不足——guard 守的是 builder 那條路，不是這個公開入口。
 * ⇒ 本函式自證恰兩段，fail-closed。
 */
export function twoStageRuleSummary(stageDigests: readonly string[]): string {
  if (stageDigests.length !== 2) {
    throw new EventExportBlocked(
      'two_stage_requires_two_stages',
      `[two_stage_requires_two_stages] twoStageRuleSummary 需要恰兩段 digest，收到 ${stageDigests.length} 段。`
      + '契約 search_rule_summary.two_stage_shape 之 stage_count 恆為 2；'
      + '寫出其他數字會讓摘要與契約形狀不符。',
    );
  }
  // 鍵序固定 stage_count→stages、無空白——契約 `search_rule_summary.two_stage_shape` 之字面。
  return JSON.stringify({ stage_count: stageDigests.length, stages: [...stageDigests] });
}

/**
 * 後端未提供來源 digest 時**fail-closed**：不得退回前端自算，也不得寫入空值。
 * （舊版於此自算 canonical 五欄子集 ⇒ 刪／改名／改值任一 `future_*` 欄後 digest 不變，
 *  改名攻擊之證據面未閉合；R6 群集 H。）
 */
function requireBackendSource(opts: EventExportOptions): { text: string; digest: string } {
  const text = opts.sourceFileText;
  const digest = opts.sourceFileDigest;
  if (typeof text !== 'string' || !/^[0-9a-f]{64}$/.test(String(digest))) {
    throw new Error(
      'source_file_digest 必須由後端提供（SearchResultData.source_file_text／source_file_digest）；'
      + '前端不得自算。請重新執行搜尋以取得帶 digest 的結果。',
    );
  }
  return { text, digest };
}

/** timestamp 字串／數字 → epoch ms（秒級自動 ×1000；ISO 字串 Date.parse）。 */
export function toEpochMs(ts: string | number | null | undefined): number | null {
  if (ts === null || ts === undefined || ts === '') return null;
  if (typeof ts === 'number') return ts < 1e12 ? Math.round(ts * 1000) : Math.round(ts);
  const n = Number(ts);
  if (Number.isFinite(n)) return n < 1e12 ? Math.round(n * 1000) : Math.round(n);
  const parsed = Date.parse(ts.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts.replace(' ', 'T')}Z`);
  return Number.isFinite(parsed) ? parsed : null;
}

export function inferDirection(conditions: unknown[]): 'long' | 'short' {
  for (const c of conditions as { parameter?: string; operator?: string; value?: unknown }[]) {
    if (c?.parameter === 'price_change') {
      const v = Array.isArray(c.value) ? Number(c.value[0]) : Number(c.value);
      if (c.operator === '<=' || (Number.isFinite(v) && v < 0)) return 'short';
    }
  }
  return 'long';
}

/**
 * 該列之 `label_definition.window.horizon_bars`（Task 4.1 ③）。
 *
 * 🔴 **唯一寫入點**：`max(1, declared[該列 tf])`。下限 1 為契約之 serialization floor，
 * 故深度 0 時此值為 1 而 `lookahead_bars_declared[tf]` 仍是 0——**兩者刻意不相等**，
 * 不要「順手」把它們對齊（SPEC §D-3′-a(i)、Task 4.1 邊界②）。
 * 🔴 **map 缺該 tf ⇒ 拋錯，不是視為 0**（R1 `CODEX-R1-P1-02`）：舊版的
 * 「缺鍵就當 0、floor 成 1」是 fail-open——那個 1 會**冒充成「深度 0」**寫進匯出檔，
 * 而使用者無從分辨「真的是 0」與「根本沒算出來」。寫不出宣告值就不該產出檔。
 * 🔴 **不得**改用全批 max 補（那是 §D-3′-a(ii) 明禁之 per-scope 冒充）。
 */
export function windowHorizonBarsFor(
  timeframe: string,
  lookaheadBarsDeclared: Record<string, number>,
): number {
  const declared = lookaheadBarsDeclared[timeframe];
  if (typeof declared !== 'number' || !Number.isInteger(declared) || declared < 0) {
    throw new Error(
      `lookahead_bars_declared 缺少或不合法之週期 ${timeframe}（實得 ${String(declared)}）；`
      + '匯出檔必帶逐 timeframe 深度宣告，請等深度查詢完成後再匯出。',
    );
  }
  return Math.max(1, declared);
}

/** Task 5.3：單一附帶 horizon 之覆蓋率（可算／缺／分母）。 */
export interface HorizonCoverage {
  horizon: number;
  /** 該欄真的有有限數值、算得出來的筆數 */
  computable: number;
  /** 分母＝實際進到匯出檔的列數（`n_records`；被 skip 的列不在其中） */
  total: number;
  /** 算不出來的筆數＝`total - computable` */
  missing: number;
}

/**
 * GAP-3 UX Task 5.3：**逐一**列出每個附帶 horizon 的可算與缺筆數。
 *
 * 🔴 與 Task 4.3 之差別：4.3 只列「有缺的那幾個」，本函式列**全部附帶 horizon**——
 * SPEC Task 5.3 之「現行確認框只在缺…時跳，**改為**匯出前主動顯示」即針對這一點：
 * 使用者不必自己去湊時間點，才知道某個 h 到底算不算得出來。
 *
 * 抽成純函式而不寫在 page 的事件處理器裡，是因為錨在處理器裡的決策無法被獨立測到
 * （本 epic §4.2 第 6 條之教訓：錨點落在無測試涵蓋處 ⇒ mutation 錄到空紅集合）。
 */
export function horizonCoverage(payload: {
  attached_horizons: readonly number[];
  missing_by_horizon: Record<number, number>;
  n_records: number;
}): HorizonCoverage[] {
  const total = payload.n_records;
  return [...payload.attached_horizons].sort((a, b) => a - b).map((horizon) => {
    const missing = payload.missing_by_horizon[horizon] ?? 0;
    return { horizon, computable: total - missing, total, missing };
  });
}

/** Task 5.3：覆蓋率 → 確認框逐行文字（一個附帶 horizon 一行）。 */
export function horizonCoverageLines(payload: {
  attached_horizons: readonly number[];
  missing_by_horizon: Record<number, number>;
  n_records: number;
}): string[] {
  return horizonCoverage(payload).map(
    (c) => `　future_${c.horizon}bar_return：${c.computable}/${c.total} 筆可算、${c.missing} 筆因資料尾端不足而缺`,
  );
}

/**
 * GAP-3 UX **Task 7.1**：UI 之五維度取值（契約欄名，snake_case）→ `EventExportOptions` 之對應鍵。
 *
 * 🔴 對映**只住這裡一份**：呼叫端展開本函式之回傳即可，逐鍵手寫 `scenario: dims.scenario`
 *    正是「漏傳其中一個」之發生處（Task 7.2 ② 之 mutation (c)）。
 */
export function eventDimsToExportOptions(dims: {
  scenario: string;
  control_kind: string;
  entry_price_semantic: string;
  label_return_mode: string;
  /** `''`（未選）在本路徑不合法；不在此靜默補預設，交給契約下界檢查 fail-closed。 */
  decision_offset_bars: number | '';
}): Required<Pick<EventExportOptions,
  'scenario' | 'controlKind' | 'entryPriceSemantic' | 'labelReturnMode' | 'decisionOffsetBars'>> {
  return {
    scenario: dims.scenario as NonNullable<EventExportOptions['scenario']>,
    controlKind: dims.control_kind as NonNullable<EventExportOptions['controlKind']>,
    entryPriceSemantic: dims.entry_price_semantic as NonNullable<EventExportOptions['entryPriceSemantic']>,
    labelReturnMode: dims.label_return_mode as NonNullable<EventExportOptions['labelReturnMode']>,
    decisionOffsetBars: dims.decision_offset_bars as number,
  };
}

export async function buildEventContractRecords(cases: CaseData[], opts: EventExportOptions) {
  // 🔴 Task 7.2 ③：`decision_offset_bars` 是唯一之**非 enum** 維度 ⇒ enum validator 守不到它。
  //    契約為 `int, min: 0`；數值輸入框可以打出 `-1`／小數 ⇒ 在**組裝前** fail-closed。
  //    這不是重做後端檢查（本檔檔頭之原則不變）：負 k 會把決策錨點移到 t0 **之後**，
  //    落檔後每一列都帶著一個語意上不存在的決策時點，比整批拒收難查得多。
  const k = opts.decisionOffsetBars ?? EVENT_EXPORT_DECISION_OFFSET_BARS;
  const kMin = contractDecisionOffsetMin();
  if (!Number.isInteger(k) || k < kMin) {
    throw new Error(
      `decision_offset_bars 必須是 >= ${kMin} 的整數（契約 event_import_contract.json 之 min）；收到 ${String(k)}`,
    );
  }
  const attached = [...(opts.attachedHorizons ?? ATTACHED_HORIZONS)];
  const declaredMap = opts.lookaheadBarsDeclared;
  const direction = opts.direction ?? inferDirection(opts.conditions);

  // ── `G3-D2` D3.1：two_stage 之前端阻擋（在組裝**之前**，不產出半成品）───────────
  //    判定走 `twoStageExportBlockReason`——與 `/search` 頁之 disable 邏輯同一份。
  const isTwoStage = opts.scenario === 'two_stage';
  const blocked = twoStageExportBlockReason({
    scenario: opts.scenario,
    stageConditions: opts.stageConditions,
    lookaheadBarsDeclared: declaredMap,
  });
  if (blocked) throw new EventExportBlocked(blocked.reason, blocked.message);

  const ruleSummary = ruleSummaryText(opts.conditions, opts.priceChangeMethod, opts.timeframe);
  const ruleDigest = await ruleDigestOf(ruleSummary);
  // D3.1 ②：兩段各自之 canonical digest ⇒ `search_rule_summary` 之 canonical JSON 單一字串。
  //    🔴 digest 一律走與單段相同的 `ruleSummaryText`＋`ruleDigestOf`，不另寫第二套序列化。
  const stageDigests = isTwoStage
    ? await Promise.all((opts.stageConditions ?? []).map(
      (conds) => ruleDigestOf(ruleSummaryText([...conds], opts.priceChangeMethod, opts.timeframe)),
    ))
    : [];
  const recordRuleSummary = isTwoStage ? twoStageRuleSummary(stageDigests) : ruleSummary;
  const { text: sourceText, digest: sourceDigest } = requireBackendSource(opts);
  const snapshot = `search:${opts.timeframe}:${new Date().toISOString().slice(0, 10)}`;
  const skipped: { index: number; reason: string }[] = [];
  /** Task 4.3：逐**附帶** horizon 之缺欄筆數（匯出端已無「答案窗缺欄」這件事）。 */
  const missingByHorizon: Record<number, number> = {};
  const records = cases.flatMap((c, i) => {
    const t0 = toEpochMs(c.timestamp);
    if (t0 === null) {
      skipped.push({ index: i, reason: 'unparseable_timestamp' });
      return [];
    }
    const pc = (c as CaseData & { positive_case?: boolean | number }).positive_case;
    const label = pc === true || pc === 1 ? 1 : pc === false || pc === 0 ? 0 : null;
    // 🔴 D3.1：two_stage **強制**走未標籤路徑——`includeUnlabeled` 不由使用者關掉
    //    （SPEC 邊界①：`includeUnlabeled=false` 且 two_stage ⇒ 前端強制切為 true 並揭露）。
    if (label === null && !opts.includeUnlabeled && !isTwoStage) {
      skipped.push({ index: i, reason: 'missing_positive_case_flag' });
      return [];
    }
    // 🔴 `includeUnlabeled` 之下仍記入 `skipped`：那一列**確實**還不能匯入，
    //    只是我們把它留在檔案裡讓使用者去補 `label`（見該選項之說明）。
    if (label === null) skipped.push({ index: i, reason: 'missing_positive_case_flag' });
    // Task 4.1 ①：附帶報酬欄——**原值攜帶**（不依 direction 取負；那是 label 語意，附帶欄沒有 label 語意）。
    // 🔴 匯出端**不再寫 `label_value`**（Task 4.1 ②，含不得寫 null／0／另立新欄）：
    //    答案窗已依 §D-3′ 移到 IC 分析層，`label_value` 於分析時才由後端 producer 計算。
    const attachedColumns: Record<string, number> = {};
    for (const h of attached) {
      const key = `future_${h}bar_return` as keyof CaseData;
      const raw = c[key];
      if (typeof raw === 'number' && Number.isFinite(raw)) {
        attachedColumns[`future_${h}bar_return`] = raw;
      } else {
        missingByHorizon[h] = (missingByHorizon[h] ?? 0) + 1;
      }
    }
    const rowTimeframe = c.timeframe || opts.timeframe;
    return [{
      // D-2：公式住契約（`event_id_template`），前端只呼叫共用定義來源，禁在此手寫第二份
      event_id: canonicalEventId(c.symbol, rowTimeframe, t0),
      symbol: c.symbol,
      timeframe: rowTimeframe,
      t0,
      // Task 7.0：五維度全部走 `opts.X ?? <常數>`；預設值除 §F-3′ 之 entry_price_semantic 外一律不動。
      decision_offset_bars: opts.decisionOffsetBars ?? EVENT_EXPORT_DECISION_OFFSET_BARS,
      entry_price_semantic: opts.entryPriceSemantic ?? EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
      direction,
      scenario: opts.scenario ?? EVENT_EXPORT_SCENARIO,
      // 🔴 D3.1：two_stage ⇒ `label` **鍵整個缺席**（禁 `null`／`''`／`0`）。
      //    寫 `null` 會讓 CSV 落成空欄看起來「有這一欄只是沒填」，而 JSON 路徑則會被
      //    契約當成「有宣告但缺值」；鍵缺席才誠實表達「這條路徑不產 label」。
      //    （驗證見 vitest：每列 `'label' in record === false`。）
      ...(isTwoStage ? {} : { label }),
      // Task 4.1 ③：真實深度（逐 tf map）。批次層屬性 ⇒ **逐列同值**（契約驗批內一致性）。
      lookahead_bars_declared: declaredMap,
      ...attachedColumns,
      label_definition: {
        rule_id: `search:price_change:${opts.priceChangeMethod || 'default'}`,
        canonical_digest: ruleDigest,
        // 🔴 由**該列自己的 tf** 導出，不是全批單一 scalar（§D-3′-a(ii) 禁 per-scope 冒充）。
        window: { horizon_bars: windowHorizonBarsFor(rowTimeframe, declaredMap) },
        // 🔴 Task 7.0：**巢狀**路徑（`label_definition.label_return_mode`），刻意不放頂層。
        label_return_mode: opts.labelReturnMode ?? EVENT_EXPORT_LABEL_RETURN_MODE,
        // 🔴 R 重開（SPEC D-8）：Phase 2 退役 ⇒ 匯出端**不再寫** `label_definition.filters`
        //    （契約鍵保留、匯入端接受缺鍵）；正反例判定在系統外完成，深度由宣告承載。
      },
      control_kind: opts.controlKind ?? EVENT_EXPORT_CONTROL_KIND,
      source_file_digest: sourceDigest,
      data_snapshot_digest: snapshot,
      // D3.1 ②：two_stage ⇒ canonical JSON `{stage_count,stages}`；其餘維持單段文字摘要。
      search_rule_summary: recordRuleSummary,
      // 🔴 `G3-D2` D1.5：provenance。`/search` 匯出批一律 `search_positive_case`
      //    ——本路徑之 label 由 t0 條件產生（`positive_case` 判定），這就是它的來源。
      //    契約對 `scenario ∈ {A,B,two_stage}` 條件必填；C 批雖不強制，仍照寫，
      //    因為「來源」是事實而非只為過閘（舊批缺欄回 null 是相容路徑，不是目標狀態）。
      // 🔴 D3.1：two_stage 不產 label ⇒ provenance 為 `search_unlabeled`（契約
      //    `not_importable`）。這批**故意**匯不進去，逼使用者補標後改以 `user_csv` 匯入。
      label_origin: isTwoStage ? EVENT_EXPORT_UNLABELED_LABEL_ORIGIN : EVENT_EXPORT_LABEL_ORIGIN,
      kind_source: 'user',
    }];
  });
  return {
    records,
    skipped,
    n_cases: cases.length,
    n_records: records.length,
    source_file_digest: sourceDigest,
    source_digest_of: 'backend §G S-9 canonical bytes of full CaseData rows (all own keys, UTF-8 ascending key order)',
    /** 契約所指「來源檔」之內容：其 sha256 === source_file_digest；匯入時以 source_file 一併上傳即可通過 verify（CODEX-R2-P1-03） */
    source_file_text: sourceText,
    verify_note: '要驗 digest：匯入時把同時下載的 *.source.json 放在 source_file 欄並開 verify_source_digest；事件檔自身含 digest 欄，自我對證必然不符',
    /** Task 4.1 ①：本次實際附帶之 horizon（順序即使用者選擇之升序）。 */
    attached_horizons: [...attached].sort((a, b) => a - b),
    /**
     * Task 4.3：逐附帶 horizon 之缺欄筆數（只列真的有缺的）。
     * 🔴 缺欄**不阻擋匯出**，也**不**在此揭露答案窗（那已不屬匯出層，見 Task 7.6）。
     */
    missing_by_horizon: Object.fromEntries(
      Object.entries(missingByHorizon)
        .map(([h, n]) => [Number(h), n] as const)
        .sort((a, b) => a[0] - b[0]),
    ) as Record<number, number>,
    /** Task 4.1 ③：本批之真實深度（逐 tf；**不是** `window.horizon_bars`，後者有 floor）。 */
    lookahead_bars_declared: declaredMap,
    note: '附帶之 future_* 欄純供 Excel 分析攜帶：不進 ic_feed、不決定任何 horizon、不參與深度導出；label_definition.window.horizon_bars 由該列 timeframe 之宣告深度導出（下限 1），欄位以 event_import_contract.json 為準',
  };
}
