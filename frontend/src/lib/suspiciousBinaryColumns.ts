/**
 * GAP-3 UX Task 1.7 — 可疑欄警示（純函式；SPEC L1602–1613）。
 *
 * 預覽階段掃描所有欄，列出**除使用者所選以外**也是二元（值域 ⊆ {0,1} 或 {true,false}）的欄名，
 * 提示「這些欄看起來也像標記，請確認你選的是哪一個」。
 *
 * 🔴 **只警示不阻擋**（語意不可機械判定，見 D-1）、**不持久化**。
 * 🔴 **不得因為只有一個二元欄就自動選它**（A-4′：不推斷）——`suggestedLabelColumn` 恆為 `null`，
 *    且該值是 Task 1.5 對映 UI 之 label 下拉初始值的**唯一來源**，故這條不是死欄位：
 *    改成「只有一個就選它」會讓下拉出現預設選取，UI 與本檔之驗收同時轉紅。
 * 🔴 **不得**與 Phase 2 之篩選合併為同一實作——系統內搜尋結果之旗標欄值域多半落在 {0,1}，
 *    合併後所有系統欄都會被列為可疑，本 Task 之「`len == 2`」即會鬆脫（SPEC「須同步」）。
 */

/** 二元判定之兩個封閉值域（比對前 `trim().toLowerCase()`；空白儲存格不計入值域）。 */
const BINARY_DOMAINS: ReadonlyArray<ReadonlySet<string>> = [
  new Set(['0', '1']),
  new Set(['true', 'false']),
];

export interface BinaryColumnScan {
  /** 值域落在任一封閉值域之欄名（依欄序）。 */
  binaryColumns: string[];
  /** 警示清單＝`binaryColumns` 扣掉使用者已選之欄。 */
  suspicious: string[];
  /** 🔴 恆為 `null`：本掃描**不推斷**該選哪一欄（A-4′）。 */
  suggestedLabelColumn: string | null;
}

/** 單欄是否二元：非空值域須非空、且整個落在某一個封閉值域內。 */
export function isBinaryColumn(values: readonly string[]): boolean {
  const domain = new Set<string>();
  for (const raw of values) {
    const s = String(raw).trim().toLowerCase();
    if (s === '') continue;
    domain.add(s);
    if (domain.size > 2) return false;
  }
  if (domain.size === 0) return false;
  return BINARY_DOMAINS.some((allowed) => [...domain].every((v) => allowed.has(v)));
}

/**
 * 掃描全欄。
 *
 * @param columns 欄名（依欄序）。
 * @param rows    資料列（每列與 `columns` 等長；短列以空字串補）。
 * @param selectedLabelColumn 使用者**已選**之 label 欄名；未選填 `null`。
 */
export function scanBinaryColumns(
  columns: readonly string[],
  rows: ReadonlyArray<readonly string[]>,
  selectedLabelColumn: string | null,
): BinaryColumnScan {
  const binaryColumns: string[] = [];
  columns.forEach((name, index) => {
    if (isBinaryColumn(rows.map((r) => r[index] ?? ''))) binaryColumns.push(name);
  });
  return {
    binaryColumns,
    suspicious: binaryColumns.filter((name) => name !== selectedLabelColumn),
    suggestedLabelColumn: null,
  };
}
