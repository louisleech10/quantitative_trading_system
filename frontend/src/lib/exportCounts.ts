/**
 * GAP-3 UX Task 1.5／4.1b／7.3 — 匯出筆數之**單一計算函式**。
 *
 * 顯示「原 M 筆／你聲明的正例 X／反例 Y」。
 *
 * 🔴 R 重開（SPEC D-8，2026-09-02）：**匯出前篩選整區退役**，本函式不再接任何條件——
 *    `/search` 匯出＝搜尋結果**全部**列，正反例在系統外（Excel）判定。
 *    原 Task 2.3 之「將匯出 N 筆」隨篩選一併退役；留下的三個數字仍由本函式唯一產生，
 *    任一 Phase 改變計數口徑時全部顯示點同步改變（Task 1.5 上傳確認與 `/search` 匯出面板）。
 * 🔴 **不得以估算值**：守恆式 `X + Y + droppedUnreadableLabel == M` 是驗收本體。
 */

/** 可計數之列（只要求可讀 `positive_case` 或由呼叫端另給判讀器）。 */
export type CountableRow = Readonly<Record<string, unknown>>;

export interface ExportCounts {
  /**
   * **事件契約 JSON 會收**之筆數＝標記可判讀者（`X + Y`）。
   *
   * 🔴 為何要扣掉不可判讀者：`eventExport.buildEventContractRecords()` 本來就會跳過
   * 沒有正反例標記的列（`skipped: missing_positive_case_flag`）。若 N 含那些列，畫面說的
   * 筆數就會**比實際匯出的多**，守恆式只能靠把它們硬塞進 X 或 Y 來維持——那是假數字。
   * 可回灌 CSV 則帶**全部** M 列（未標記者 `label` 留空供 Excel 補）。
   */
  N: number;
  /** 原筆數（＝CSV 匯出之筆數）。 */
  M: number;
  /** 使用者聲明為正例之筆數。 */
  X: number;
  /** 使用者聲明為反例之筆數。 */
  Y: number;
  /** **標記無法判讀**而不會進事件 JSON 的筆數（不猜，且要顯示出來）；`N + droppedUnreadableLabel == M`。 */
  droppedUnreadableLabel: number;
}

/** 一列的「正反例」判讀；`null` ＝ 無法判讀（不猜）。 */
export type LabelReader = (row: CountableRow) => boolean | null;

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
 * 算出四個數字（不篩選；每一列都計入 M）。
 *
 * @param rows 原始列。
 * @param readLabel 正反例判讀器（預設為 `/search` 結果之規則；Task 1.5 之 CSV 路徑另傳）。
 */
export function computeExportCounts(
  rows: readonly CountableRow[],
  readLabel: LabelReader = searchRowLabel,
): ExportCounts {
  const M = rows.length;
  let X = 0;
  let Y = 0;
  let droppedUnreadableLabel = 0;
  for (const row of rows) {
    const label = readLabel(row);
    if (label === true) X += 1;
    else if (label === false) Y += 1;
    else droppedUnreadableLabel += 1;
  }
  const N = X + Y;                       // 守恆式依建構成立，不是靠事後湊
  return { N, M, X, Y, droppedUnreadableLabel };
}
