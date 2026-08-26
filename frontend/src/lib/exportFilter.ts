/**
 * GAP-3 UX Task 2.1 — `/search` 匯出前篩選（純函式；SPEC L1799–1810）。
 *
 * 對搜尋結果任一**數值**欄設 `>=`／`<=`／區間，多條件 **AND**。
 *
 * 🔴 面板**只讀**搜尋結果並產生條件物件，**不改任何原始欄位值**（SPEC「不可做」）。
 * 🔴 條件物件是 Task 2.1b（導下界）、2.2（寫 `filters`）、2.3（算筆數）之**唯一輸入來源**。
 * 🔴 只篩**數值**欄：字串欄不得出現在可選清單（SPEC 邊界①）。
 * 🔴 **深度不在這裡算**——下界一律由後端 `POST /case/lookahead-depth` 取得
 *    （`depth_by_timeframe()` 是唯一實作，在 TS 重寫一份就是第二份副本）。
 */

export type ExportFilterOp = '>=' | '<=' | 'between';

export interface ExportFilterCondition {
  column: string;
  op: ExportFilterOp;
  /** `op` 為 `>=`／`<=` 時使用。 */
  value?: number;
  /** `op` 為 `between` 時使用（閉區間 `[min, max]`）。 */
  range?: [number, number];
}

/** 契約 `label_definition.filters` 之 wire shape（Task 2.2 定案；形狀之唯一定義來源＝契約檔）。 */
export interface ExportFilterSpec {
  version: 1;
  combinator: 'AND';
  conditions: ExportFilterCondition[];
}

/** 一列搜尋結果（只取本模組需要的部分；不綁 `CaseData` 全形狀）。 */
export type FilterableRow = Record<string, unknown>;

/**
 * 可篩選之欄名＝**在所有非空樣本上都是有限數值**的欄。
 *
 * 🔴 「有一列是數值」不夠：`market_phase` 之類偶爾是數字字串的欄會混進來。
 * 判準用**全樣本**：只要有一列該欄是非空的非數值，就不是數值欄。
 * `boolean` 不算數值欄（`positive_case` 是標記，不是可比大小的量）。
 */
export function numericColumnsOf(rows: readonly FilterableRow[]): string[] {
  const names = new Set<string>();
  for (const row of rows) for (const k of Object.keys(row)) names.add(k);

  const out: string[] = [];
  for (const name of [...names].sort()) {
    let sawNumber = false;
    let ok = true;
    for (const row of rows) {
      const v = row[name];
      if (v === null || v === undefined || v === '') continue;
      if (typeof v === 'number' && Number.isFinite(v)) { sawNumber = true; continue; }
      ok = false;
      break;
    }
    if (ok && sawNumber) out.push(name);
  }
  return out;
}

/** 條件本身是否可用（欄名非空、數值有限、區間下界 ≤ 上界）。 */
export function isUsableCondition(c: ExportFilterCondition): boolean {
  if (!c.column) return false;
  if (c.op === 'between') {
    if (!c.range) return false;
    const [lo, hi] = c.range;
    return Number.isFinite(lo) && Number.isFinite(hi) && lo <= hi;
  }
  return typeof c.value === 'number' && Number.isFinite(c.value);
}

/** 單列是否通過單一條件；該欄缺值／非數值 ⇒ **不通過**（不猜）。 */
export function rowPassesCondition(row: FilterableRow, c: ExportFilterCondition): boolean {
  const raw = row[c.column];
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return false;
  if (c.op === '>=') return raw >= (c.value as number);
  if (c.op === '<=') return raw <= (c.value as number);
  const [lo, hi] = c.range as [number, number];
  return raw >= lo && raw <= hi;
}

/**
 * 套用全部條件（AND）。**不修改任何列**——回傳的是原列之參考組成的新陣列。
 *
 * 條件為空（或全部不可用）⇒ 回原陣列內容，筆數 `==` 原筆數（SPEC 邊界②：
 * 不得因為面板存在就改變預設行為）。
 */
export function applyExportFilters(
  rows: readonly FilterableRow[],
  conditions: readonly ExportFilterCondition[],
): FilterableRow[] {
  const usable = conditions.filter(isUsableCondition);
  if (usable.length === 0) return [...rows];
  return rows.filter((row) => usable.every((c) => rowPassesCondition(row, c)));
}

/**
 * 組出契約形狀之 `filters`（Task 2.2 寫入 `label_definition.filters` 用）。
 *
 * 無可用條件 ⇒ 回 `null`（不寫空殼；`filters` 存在與否本身有語意——
 * 後端之 L2 會據此判斷「這批有沒有條件」）。
 */
export function buildExportFilterSpec(
  conditions: readonly ExportFilterCondition[],
): ExportFilterSpec | null {
  const usable = conditions.filter(isUsableCondition);
  if (usable.length === 0) return null;
  return {
    version: 1,
    combinator: 'AND',
    conditions: usable.map((c) => (c.op === 'between'
      ? { column: c.column, op: c.op, range: [c.range![0], c.range![1]] as [number, number] }
      : { column: c.column, op: c.op, value: c.value as number })),
  };
}

/**
 * 答案窗下界之狀態。
 *
 * 🔴 `status` 與 `bound` **不可互相取代**（R1 `CODEX-R1-P1-01`）：
 * `bound === null` 有兩種完全相反的意思——「沒有條件所以沒有約束」（可匯出）
 * 與「有條件但算不出下界」（**必須擋住**）。舊版只留 `bound`，於是初次查詢失敗時
 * 下界仍是 `null`，守衛照樣放行 ⇒ fail-open。`status` 就是用來分辨這兩者的。
 */
export interface LowerBoundState {
  status: 'unconstrained' | 'resolved' | 'pending' | 'error';
  /** 逐 timeframe 之下界（SPEC Task 2.1b 之 derived 值形狀；**不得塌成 scalar**）。 */
  depthByTimeframe: Record<string, number>;
  /**
   * 可用**單一** scalar 表達時之下界；各 tf 下界不同或未解析時為 `null`。
   *
   * 🔴 `D-004 A-021(d)`：`bound === null` **不再**代表「不可匯出」。Task 4.1 之後
   * `window.horizon_bars` 是**逐列**依該列 tf 由 `depthByTimeframe` 導出，混 TF 已可表達
   * ⇒ 舊的 `inexpressible` 狀態失去存在理由（它當初存在，是因為單一 scalar 表達不了
   * 逐 tf 之不同下界，SPEC §D-3′-a(ii) 又禁止取 max 冒充 per-scope 下界）。
   * 「可不可以匯出」現在只看 `status`，見 `exportAllowedByLowerBoundState()`。
   */
  bound: number | null;
  error: string | null;
}

export const UNCONSTRAINED_LOWER_BOUND: LowerBoundState = {
  status: 'unconstrained', depthByTimeframe: {}, bound: null, error: null,
};

/** 一次下界查詢之結果。 */
export type LowerBoundOutcome =
  /**
   * 沒有篩選條件 ⇒ 沒有下界約束。
   * 🔴 `depthByTimeframe` **仍由後端提供**（Task 4.1 之匯出檔必帶 `lookahead_bars_declared`）
   * ——前端不得自行填 0：那是把 `depth_by_timeframe()` 的退化分支複製一份。
   */
  | { kind: 'no-conditions'; depthByTimeframe: Record<string, number> }
  | { kind: 'pending' }
  | { kind: 'resolved'; depthByTimeframe: Record<string, number> }
  | { kind: 'error'; message: string };

/**
 * 由查詢結果決定下一個下界狀態（Task 2.1b／`D-002 A-004` 之**決策本體**）。
 *
 * - `no-conditions`：沒有條件就沒有約束 ⇒ `unconstrained`。
 * - `pending`：有條件、還沒拿到下界 ⇒ **擋住**（不是「暫時沒有約束」）。
 * - `resolved`：保留**逐 tf map**；各 tf 下界相同（含單一 tf）時 `bound` 為該值，
 *   🔴 **不同時 `bound` 為 `null` 但仍是 `resolved`（可匯出）**——`D-004 A-021(d)`：
 *   Task 4.1 之後 `window.horizon_bars` **逐列**依該列 tf 寫入，混 TF 已可表達，
 *   舊的 `inexpressible`（拒絕匯出）失去理由。
 *   🔴 **仍不得取 max 塞進 `bound`**——那是 SPEC §D-3′-a(ii) 明令禁止之
 *   「以單一 batch scalar 冒充 per-scope 下界」（對窗較小的 scope 是過度 purge）。
 * - `error`：🔴 **擋住並回報**——算不出下界時當成「沒有約束」就是 fail-open。
 */
export function nextLowerBoundState(
  previous: LowerBoundState,
  outcome: LowerBoundOutcome,
): LowerBoundState {
  if (outcome.kind === 'no-conditions') {
    return { ...UNCONSTRAINED_LOWER_BOUND, depthByTimeframe: outcome.depthByTimeframe };
  }
  if (outcome.kind === 'pending') {
    return { status: 'pending', depthByTimeframe: {}, bound: null, error: null };
  }
  if (outcome.kind === 'resolved') {
    const depth = outcome.depthByTimeframe;
    const values = Object.values(depth);
    if (values.length === 0) return UNCONSTRAINED_LOWER_BOUND;
    const distinct = [...new Set(values)];
    // 各 tf 下界不同 ⇒ 仍 `resolved`（可匯出），只是無法以單一 scalar 表達 ⇒ `bound: null`。
    // 逐 tf 之值一律留在 `depthByTimeframe`（**不得塌成 scalar**）。
    if (distinct.length > 1) {
      return { status: 'resolved', depthByTimeframe: depth, bound: null, error: null };
    }
    return { status: 'resolved', depthByTimeframe: depth, bound: distinct[0], error: null };
  }
  return {
    status: 'error',
    depthByTimeframe: previous.depthByTimeframe,
    bound: previous.bound,
    error: outcome.message,
  };
}

/**
 * 這個狀態下允許匯出嗎？——`false` 時**一定**要擋（`D-004 A-021(b)`）。
 *
 * **readiness fail-closed**：只問「系統證明得出這批的深度了嗎」。
 * `unconstrained`（沒有條件＝沒有約束）與 `resolved`（已導出逐 tf 深度）⇒ 可匯出；
 * `pending`（還沒拿到）／`error`（算不出來）⇒ 擋——**系統無法證明安全時不得放行**。
 *
 * 🔴 **不再比較使用者選值**：Task 4.1 移除主答案窗後 `window.horizon_bars` 由深度導出、
 * 不再由使用者選 ⇒ 「使用者選太小」這個風險消失，`selectedBars >= bound` 恆真＝死碼。
 * 🔴 **`bound === null` 不再是擋的理由**（`A-021(d)`）——混 TF 之逐列寫入已可表達 per-scope 下界；
 * 要擋的是 `pending`／`error`，那才是「算不出來」。
 */
export function exportAllowedByLowerBoundState(state: LowerBoundState): boolean {
  return state.status === 'unconstrained' || state.status === 'resolved';
}

/**
 * 後端回傳之深度 map 是否可信（R1 `CODEX-R1-P1-02`）。
 *
 * 判準：**恰好覆蓋本批出現的每一個 timeframe**，且每個值都是非負整數。
 *
 * 🔴 為什麼要驗：`api.ts` 之型別只是 TS compile-time，執行期拿到什麼都會直接進 state。
 * 舊版之三個 fail-open：
 * ①**空 map** ⇒ `nextLowerBoundState` 判為 `unconstrained`（可匯出），而匯出檔的深度宣告是空的；
 * ②**缺某個 tf** ⇒ 該列 `window.horizon_bars` 被 floor 成 1，**冒充成「深度 0」**；
 * ③**非法值**（負數／小數／字串）⇒ 直接寫進匯出檔。
 * 三者都會產出「宣稱帶著深度宣告、實際上沒有」的檔。
 */
export function depthMapCoversTimeframes(
  depthByTimeframe: unknown,
  timeframes: readonly string[],
): boolean {
  if (typeof depthByTimeframe !== 'object' || depthByTimeframe === null) return false;
  const map = depthByTimeframe as Record<string, unknown>;
  const keys = Object.keys(map);
  if (keys.length !== timeframes.length) return false;
  for (const tf of timeframes) {
    if (!Object.prototype.hasOwnProperty.call(map, tf)) return false;
    const v = map[tf];
    if (typeof v !== 'number' || !Number.isInteger(v) || v < 0) return false;
  }
  return true;
}

/**
 * 條件實際引用之欄名（去重、排序）——送去後端算下界用。
 *
 * 🔴 **只含條件引用之欄**；Task 4.1 之附帶欄不得混入
 * （SPEC Task 2.1b：附帶欄與 label 判定無關，納入會過度 purge、吃掉訓練樣本）。
 */
export function referencedColumnsOf(conditions: readonly ExportFilterCondition[]): string[] {
  return [...new Set(conditions.filter(isUsableCondition).map((c) => c.column))].sort();
}
