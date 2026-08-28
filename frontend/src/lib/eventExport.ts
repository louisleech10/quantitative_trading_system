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
import type { ExportFilterSpec } from './exportFilter';

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
 */
export const EVENT_EXPORT_ENTRY_PRICE_SEMANTIC = 'trigger_close' as const;
export const EVENT_EXPORT_LABEL_RETURN_MODE = 'close_to_close' as const;
export const EVENT_EXPORT_DECISION_OFFSET_BARS = 0 as const;

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
   * Task 4.1 ③：逐 timeframe 之**真實深度**（後端 `depth_by_timeframe()` 導出之 map）。
   *
   * 🔴 前端**不自算**——第二份實作必然漂移（SPEC Task 2.1b）。
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
   * GAP-3 UX Task 2.2：匯出前篩選條件，寫進 `label_definition.filters`（契約已登記之欄）。
   *
   * 🔴 **不得納入 `event_id` 之輸入**（D-2：同事件跨批 id 必須相同）。
   * 🔴 形狀之唯一定義來源＝契約 `label_definition.fields.filters.wire_shape`；
   *    由 `exportFilter.buildExportFilterSpec()` 產生，本檔不自訂形狀。
   * 無條件時傳 `null`／不傳 ⇒ **不寫該鍵**（`filters` 存在與否本身有語意）。
   */
  filters?: ExportFilterSpec | null;
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

export async function buildEventContractRecords(cases: CaseData[], opts: EventExportOptions) {
  const attached = [...(opts.attachedHorizons ?? ATTACHED_HORIZONS)];
  const declaredMap = opts.lookaheadBarsDeclared;
  const direction = opts.direction ?? inferDirection(opts.conditions);
  const ruleSummary = ruleSummaryText(opts.conditions, opts.priceChangeMethod, opts.timeframe);
  const ruleDigest = await ruleDigestOf(ruleSummary);
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
    if (label === null) {
      skipped.push({ index: i, reason: 'missing_positive_case_flag' });
      return [];
    }
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
      label,
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
        // Task 2.2：條件為空時**不寫該鍵**（`filters` 存在與否本身有語意——後端 L2 據此判斷有無條件）。
        // 🔴 `event_id` 於本物件**之外**產生（見上），故篩選條件不可能進入 ID 之輸入（D-2）。
        ...(opts.filters ? { filters: opts.filters } : {}),
      },
      control_kind: opts.controlKind ?? EVENT_EXPORT_CONTROL_KIND,
      source_file_digest: sourceDigest,
      data_snapshot_digest: snapshot,
      search_rule_summary: ruleSummary,
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
