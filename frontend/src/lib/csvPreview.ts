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
   * 檔案用了**只有 `\r`** 的舊式 Mac 換行（unquoted lone CR）。
   *
   * 🔴 **不支援，且兩端一致地明說**（R4 `CODEX-R4-P1-01`）：舊版本把 unquoted `\r` 直接丟掉，
   * 於是整個檔被黏成一行、產出「看起來很合理」的欄名（`a,b\r1,2\r` ⇒ `["a","b1","23","4"]`）
   * 讓使用者照著對映；後端則以 `parse_error` 拒收 ⇒ 又是一次前端收／後端擋。
   * 偵測到時本檔回**空模型**（`columns`／`rows` 皆空），UI 因此不會渲染對映區塊，只顯示錯誤。
   */
  unsupportedLineEnding: boolean;

  /**
   * 欄數與標頭不符之列（0-based 列序 ＋ 實際欄數）。
   *
   * 🔴 **不得靜默截斷或補齊就當沒事**（R1 三家共提）：後端 `pd.read_csv` 在「每列都比標頭多一格」
   * 時會把首欄當 index、**整列左移且零 warning**，`label` 讀到的會是隔壁欄的值。
   * 後端已改為 fail-closed 拒收；前端在預覽階段就要擋，否則使用者會依錯誤筆數勾下確認。
   */
  raggedRows: { row: number; width: number }[];
}

/**
 * RFC4180 逐字元解析：吃引號內之逗號／換行／跳脫雙引號。
 *
 * `loneCr` ＝ 是否出現**未被 `\n` 跟隨**之 unquoted `\r`（舊式 Mac 換行）。
 * 引號**內**之 `\r` 是資料、原樣保留（後端 pandas 亦保留），不算。
 */
function splitRecords(text: string): { records: string[][]; loneCr: boolean } {
  const records: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let quoted = false;
  let touched = false;
  let loneCr = false;
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
    if (ch === '\r') {
      if (text[i + 1] !== '\n') loneCr = true;   // 舊式 Mac 換行 ⇒ 不支援，交由呼叫端明說
      continue;                                   // CRLF 之 `\r` 照舊丟棄
    }
    if (ch === '\n') { pushCell(); pushRow(); continue; }
    cell += ch;
  }
  if (touched || cell !== '' || row.length > 0) { pushCell(); pushRow(); }
  return {
    records: records.filter((r) => !(r.length === 1 && r[0].trim() === '')),
    loneCr,
  };
}

/**
 * 解析 CSV 文字。標頭列＝第一列；資料列全數保留（正反例筆數要數的是整份檔，不是預覽那 5 列）。
 *
 * @param previewRowLimit 預覽列數上限（SPEC 為 5）。
 */
export function parseCsvText(text: string, previewRowLimit = 5): ParsedCsv {
  const { records, loneCr } = splitRecords(text.replace(/^﻿/, ''));
  const empty: ParsedCsv = {
    columns: [], previewRows: [], rows: [], duplicateNames: [], raggedRows: [],
    unsupportedLineEnding: loneCr,
  };
  // 🔴 舊式 Mac 換行 ⇒ 回空模型：不得產出「看起來很合理」的欄名讓使用者照著對映（R4）。
  if (loneCr || records.length === 0) return empty;

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
    unsupportedLineEnding: false,
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
