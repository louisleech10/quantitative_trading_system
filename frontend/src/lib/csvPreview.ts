/**
 * GAP-3 UX Task 1.5 — 上傳 CSV 之**前端預覽解析**（純函式）。
 *
 * 🔴 **誠實邊界**：本檔只為「讓使用者在送出前看得到自己的檔」而存在——預覽列、欄名清單、
 *    可疑欄警示（Task 1.7）、正反例筆數。**任何契約檢核都不在這裡**（V-3：檢核唯一實作在
 *    `momentum`，經 `/case/import-events/csv` 之後端路徑執行）。前端解析與後端 pandas 解析
 *    在極端 CSV 上可能不同，故本檔之產物一律是**警示／預覽**，不得用來放行或阻擋契約層的事。
 */

/** 一個 CSV 欄；`label` 是**下拉可辨字樣**（同名欄以欄序區分，不得靜默取第一個）。 */
export interface ParsedCsvColumn {
  /** 標頭原字樣。 */
  name: string;
  /** 0-based 欄序。 */
  index: number;
  /** 下拉顯示字樣：唯一欄名＝原字樣；重複欄名＝`名稱（第 N 欄）`。 */
  label: string;
  /** 該欄名在標頭出現超過一次。 */
  duplicated: boolean;
}

export interface ParsedCsv {
  columns: ParsedCsvColumn[];
  /** 前 N 列（預設 5）——SPEC Task 1.5「顯示前 5 列預覽與全部欄名」。 */
  previewRows: string[][];
  /** 全部資料列（不含標頭）；長度一律對齊標頭（短列補空、長列**不截**，見 `raggedRows`）。 */
  rows: string[][];
  /** 出現超過一次的欄名（升冪去重）。 */
  duplicateNames: string[];
  /**
   * 欄數與標頭不符之列（0-based 列序 ＋ 實際欄數）。
   *
   * 🔴 **不得靜默截斷或補齊就當沒事**（R1 三家共提）：後端 `pd.read_csv` 在「每列都比標頭多一格」
   * 時會把首欄當 index、**整列左移且零 warning**，`label` 讀到的會是隔壁欄的值。
   * 後端已改為 fail-closed 拒收；前端在預覽階段就要擋，否則使用者會依錯誤筆數勾下確認。
   */
  raggedRows: { row: number; width: number }[];
}

/** RFC4180 逐字元解析：吃引號內之逗號／換行／跳脫雙引號。 */
function splitRecords(text: string): string[][] {
  const records: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let quoted = false;
  let touched = false;
  const pushCell = () => { row.push(cell); cell = ''; };
  const pushRow = () => { records.push(row); row = []; touched = false; };

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    touched = true;
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 1; } else { quoted = false; }
      } else {
        cell += ch;
      }
      continue;
    }
    if (ch === '"') { quoted = true; continue; }
    if (ch === ',') { pushCell(); continue; }
    if (ch === '\r') continue;
    if (ch === '\n') { pushCell(); pushRow(); continue; }
    cell += ch;
  }
  if (touched || cell !== '' || row.length > 0) { pushCell(); pushRow(); }
  return records.filter((r) => !(r.length === 1 && r[0].trim() === ''));
}

/**
 * 解析 CSV 文字。標頭列＝第一列；資料列全數保留（正反例筆數要數的是整份檔，不是預覽那 5 列）。
 *
 * @param previewRowLimit 預覽列數上限（SPEC 為 5）。
 */
export function parseCsvText(text: string, previewRowLimit = 5): ParsedCsv {
  const records = splitRecords(text.replace(/^﻿/, ''));
  if (records.length === 0) {
    return { columns: [], previewRows: [], rows: [], duplicateNames: [], raggedRows: [] };
  }

  const header = records[0].map((c) => c.trim());
  const counts = new Map<string, number>();
  for (const name of header) counts.set(name, (counts.get(name) ?? 0) + 1);

  const columns: ParsedCsvColumn[] = header.map((name, index) => {
    const duplicated = (counts.get(name) ?? 0) > 1;
    return { name, index, duplicated, label: duplicated ? `${name}（第 ${index + 1} 欄）` : name };
  });
  const dataRecords = records.slice(1);
  const rows = dataRecords.map((r) => header.map((_, i) => (r[i] ?? '')));
  const raggedRows = dataRecords
    .map((r, i) => ({ row: i, width: r.length }))
    .filter((x) => x.width !== header.length);
  return {
    columns,
    previewRows: rows.slice(0, previewRowLimit),
    rows,
    duplicateNames: [...counts.entries()].filter(([, n]) => n > 1).map(([n]) => n).sort(),
    raggedRows,
  };
}

/** 取某欄之全部儲存格值（欄不存在 ⇒ 空陣列）。 */
export function columnValues(parsed: ParsedCsv, columnIndex: number): string[] {
  if (columnIndex < 0) return [];
  return parsed.rows.map((r) => r[columnIndex] ?? '');
}

/**
 * 使用者**聲明**的正反例筆數。
 *
 * 🔴 `1`／`0` 以外一律不猜（`true`／`yes`／`Y` 都不算）——與後端對映層之 label 判定同一條規則；
 * 猜了就會出現「畫面說 12 筆、後端拒收」的不一致。空白列（後端由 `batch_defaults` 補值）與
 * 不可辨識列**分開計數**，兩者都必須顯示出來，不得靜默吞掉。
 */
export function countDeclaredLabels(
  values: string[],
): { positive: number; negative: number; blank: number; unreadable: number } {
  let positive = 0;
  let negative = 0;
  let blank = 0;
  let unreadable = 0;
  for (const raw of values) {
    const s = String(raw).trim();
    if (s === '1') positive += 1;
    else if (s === '0') negative += 1;
    else if (s === '') blank += 1;
    else unreadable += 1;
  }
  return { positive, negative, blank, unreadable };
}
