/**
 * 「這份 CSV 已經是契約格式了」之偵測（**只用於引導，不是契約判定**）。
 *
 * 🔴 出生事故（2026-09-02 使用者 UAT B10）：使用者把 `/search` 匯出的契約 CSV
 * 丟進「用自己的欄名匯入事件 CSV」那一區，把下拉**全部選滿**之後送出，
 * 得到 `99 筆契約違規／列 0／label_definition／missing_required_field`。
 * 成因：對映路徑**只保留下拉指定的欄**（`case_import_service.csv_records_from_mapping`），
 * 而下拉只提供契約的**頂層**欄——`label_definition.window.horizon_bars` 這種
 * 巢狀欄根本沒得選 ⇒ 全部被丟掉。那份檔本來就該走「匯入事件」直傳（零對映）。
 *
 * 缺陷不在後端拒收（拒收是對的），而在於**沒有人在使用者做那一輪對映之前告訴他走錯區**。
 *
 * 🔴 **判準與後端逐字相同**：欄名正規化＝去 BOM／引號／空白後 casefold，
 * marker ＝ `{event_id, t0, label}` 三者皆在。後端唯一實作為
 * `EventImportService.looks_new_schema()`；`tests/api/test_gap3_contract_csv_guard.py`
 * 逐字對證本檔之 marker 與正規化規則，任一端改了另一端沒跟就會紅。
 */

/** 與後端 `_canon_cols()` 同規則。 */
export function canonColumnName(name: string): string {
  return String(name).replace(/﻿/g, '').trim().replace(/^["']|["']$/g, '').trim().toLowerCase();
}

/** 與後端 `looks_new_schema()` 同一組 marker。 */
export const CONTRACT_MARKER_COLUMNS = ['event_id', 't0', 'label'] as const;

/** 這份 CSV 的欄名是否已是契約格式（marker 三欄皆在）。 */
export function looksContractCsv(columns: readonly string[]): boolean {
  const canon = new Set(columns.map(canonColumnName));
  return CONTRACT_MARKER_COLUMNS.every((m) => canon.has(m));
}

/** 走錯區時要顯示的引導（**擋住送出**，不是只提醒）。 */
export const CONTRACT_CSV_WRONG_SECTION_HINT =
  '這份 CSV 的欄名已經是契約欄名（含 event_id／t0／label）——不需要做欄位對映。'
  + '請改用上方「匯入事件」直接上傳；'
  + '在這一區送出會丟掉沒有下拉可選的巢狀欄（例如 label_definition.window.horizon_bars），'
  + '導致整批被拒收。';
