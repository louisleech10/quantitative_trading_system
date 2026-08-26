/**
 * GAP-3 UX Task 2.3 — 匯出筆數之**單一計算函式**（SPEC L1880–1891）。
 *
 * 顯示「將匯出 N 筆（原 M 筆）／你聲明的正例 X／反例 Y」。
 *
 * 🔴 **本函式是那組事實的唯一來源**——任一 Phase 改變計數口徑時全部顯示點同步改變，
 *    否則同一個畫面會出現互相矛盾的筆數（RISK-(b)）。
 *    **現況（誠實邊界，R1 `CODEX-R1-P2-06`）**：已接上的 production 顯示點是**兩個**
 *    ——Task 1.5 之上傳確認（`EventCsvMappingForm`）與 Task 2.1 之篩選面板（`/search`）。
 *    SPEC 所稱之四個顯示點還差 Task 4.1b 與 7.3，**那兩個 Task 尚未實作**；
 *    它們落地時須沿用本函式並各自補 runtime 覆蓋，不得另寫一份計數。
 * 🔴 **不得以估算值**（SPEC「不可做」）：兩條守恆式是驗收本體——
 *    `N + filtered_out == M` 且 `X + Y == N`。
 */

import { applyExportFilters, type ExportFilterCondition, type FilterableRow } from '@/lib/exportFilter';

export interface ExportCounts {
  /**
   * **將匯出**筆數＝通過條件**且標記可判讀**者。
   *
   * 🔴 為何要扣掉不可判讀者：SPEC 邊界②是 `X + Y == N`，而
   * `eventExport.buildEventContractRecords()` 本來就會跳過沒有正反例標記的列
   * （`skipped: missing_positive_case_flag`）。若 N 含那些列，畫面說的「將匯出 N 筆」
   * 就會**比實際匯出的多**，且守恆式只能靠把它們硬塞進 X 或 Y 來維持——那是假數字。
   */
  N: number;
  /** 原筆數。 */
  M: number;
  /** 將匯出者之中，使用者聲明為正例之筆數。 */
  X: number;
  /** 將匯出者之中，使用者聲明為反例之筆數。 */
  Y: number;
  /** 沒進到匯出的筆數；`N + filteredOut == M` 恆成立。 */
  filteredOut: number;
  /**
   * 通過條件之列數＝**CSV 匯出**之筆數。
   *
   * 🔴 與 `N` 不同是**正常的**（R3 `CODEX-R3-P1-01`）：事件契約 JSON 必須有正反例標記，
   * 沒標記的列會被 `eventExport` 跳過；CSV 是原始搜尋結果之匯出，**不該因為少一個旗標
   * 就把整列丟掉**。兩個數字不同時要**同時顯示**，不能只給一個讓使用者對不上。
   */
  keptByFilters: number;
  /** `filteredOut` 之拆解：被條件濾掉的。 */
  droppedByFilters: number;
  /** `filteredOut` 之拆解：通過條件但**標記無法判讀**而不會被匯出的（不猜，且要顯示出來）。 */
  droppedUnreadableLabel: number;
}

/** 一列的「正反例」判讀；`null` ＝ 無法判讀（不猜）。 */
export type LabelReader = (row: FilterableRow) => boolean | null;

/**
 * `/search` 結果之預設判讀：`positive_case` 為 `true`／`1` ⇒ 正例，`false`／`0` ⇒ 反例，其餘 `null`。
 * 🔴 與 `eventExport.buildEventContractRecords()` 之判讀**同一條規則**（字串不猜）。
 */
export const searchRowLabel: LabelReader = (row) => {
  const v = (row as { positive_case?: unknown }).positive_case;
  if (v === true || v === 1) return true;
  if (v === false || v === 0) return false;
  return null;
};

/**
 * 算出四個數字。
 *
 * @param rows 原始列（未篩選）。
 * @param conditions 篩選條件；空陣列 ⇒ `N == M`。
 * @param readLabel 正反例判讀器（預設為 `/search` 結果之規則；Task 1.5 之 CSV 路徑另傳）。
 */
export function computeExportCounts(
  rows: readonly FilterableRow[],
  conditions: readonly ExportFilterCondition[] = [],
  readLabel: LabelReader = searchRowLabel,
): ExportCounts {
  const M = rows.length;
  const kept = applyExportFilters(rows, conditions);

  let X = 0;
  let Y = 0;
  let droppedUnreadableLabel = 0;
  for (const row of kept) {
    const label = readLabel(row);
    if (label === true) X += 1;
    else if (label === false) Y += 1;
    else droppedUnreadableLabel += 1;
  }
  const N = X + Y;                       // 邊界②：依建構成立，不是靠事後湊
  return {
    N,
    M,
    X,
    Y,
    filteredOut: M - N,                  // 邊界①：依建構成立
    keptByFilters: kept.length,
    droppedByFilters: M - kept.length,
    droppedUnreadableLabel,
  };
}
