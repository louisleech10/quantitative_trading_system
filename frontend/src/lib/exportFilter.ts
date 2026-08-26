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

/** 答案窗下界之狀態（`bound` 為 `null` ＝尚無約束）。 */
export interface LowerBoundState {
  bound: number | null;
  error: string | null;
}

/** 一次下界查詢之結果。 */
export type LowerBoundOutcome =
  | { kind: 'no-conditions' }
  | { kind: 'resolved'; depthByTimeframe: Record<string, number> }
  | { kind: 'error'; message: string };

/**
 * 由查詢結果決定下一個下界狀態（Task 2.1b／`D-002 A-004` 之**決策本體**）。
 *
 * 三種情形各自的正確處置：
 * - `no-conditions`：沒有條件就沒有約束 ⇒ `null`（不是 0，也不是沿用舊值）。
 * - `resolved`：逐 tf 下界取**最嚴**者（往上調永遠允許，往下調才是危險方向）。
 * - `error`：🔴 **保留現值並回報錯誤**——算不出下界時當成「沒有約束」就是 fail-open，
 *   那會讓使用者在系統無法證明安全的情況下把答案窗調到任意小。
 */
export function nextLowerBoundState(
  previous: LowerBoundState,
  outcome: LowerBoundOutcome,
): LowerBoundState {
  if (outcome.kind === 'no-conditions') return { bound: null, error: null };
  if (outcome.kind === 'resolved') {
    const bounds = Object.values(outcome.depthByTimeframe);
    return { bound: bounds.length > 0 ? Math.max(...bounds) : null, error: null };
  }
  return { bound: previous.bound, error: outcome.message };
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
