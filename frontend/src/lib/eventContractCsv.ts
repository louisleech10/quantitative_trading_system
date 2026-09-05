/**
 * 契約記錄 → **可直接回灌**的 CSV（2026-09-01 使用者裁定）。
 *
 * 🔴 **出生事故（使用者 UAT B9）**：`/search` 原本的「導出CSV檔案」用的是**展示用欄名**
 * （`Timestamp`／`Positive_Case`／`Price_Change_%`…），與契約的欄名、型別、單位全都對不上
 * ⇒ 使用者在 Excel 標好正反例之後**回不去**：得逐欄對映，還要手寫一段含兩個 64 位 hex
 * digest 的批次預設 JSON。使用者原話：「我根本也看不懂也沒辦法自己寫」。
 * 而「自己決定哪些是正例」正是本 epic 的核心前提 ⇒ 少了這條路等於主流程缺一塊。
 *
 * 🔴 **由契約記錄產生，不是另外拼一份**：欄名與值都取自 `buildEventContractRecords()` 之輸出，
 * 所以 CSV 與 JSON 兩種匯出**不可能漂移**（同一個來源攤平兩次）。
 *
 * 欄名規則（對應後端 `case_import_service._csv_rows_to_records` 之解析）：
 * - 契約頂層欄 ⇒ **契約欄名本身**（`symbol`／`t0`／`label`…）⇒ 上傳時**零對映**
 * - 巢狀欄 ⇒ **點路徑**（`label_definition.window.horizon_bars`）
 * - 非契約之分析欄 ⇒ 放進 **`meta.`**（契約之自由欄）⇒ Excel 裡照樣看得到、篩得動，
 *   而且**不會被 `unknown_field` 拒收**
 *
 * 🔴 **答案只有一欄**：`label`（0／1）。不再另寫 `Positive_Case`——
 * 兩欄並存時，使用者改了其中一個而系統讀另一個，是必然的誤會來源。
 */

import contract from '../../../momentum/Analysis/contracts/event_import_contract.json';

/**
 * 契約 `required_fields` 之**純量**欄名——CSV header 一律保留這些欄（缺鍵 ⇒ 空欄）。
 *
 * 🔴 由**真契約**導出，不是人工清單：契約加一個必填純量欄，這裡自動跟上。
 * （`eventMetricsGlossary.ts` 早有直接 import 契約 JSON 之前例；
 *  `eventDimensions.ts` 之所以走鏡像是為了讓 Task 7.2 之漂移閘有兩個來源可比，
 *  那個理由**不適用**於本檔——這裡要的就是「跟著契約走」。）
 *
 * 物件型欄（`label_definition`／`lookahead_bars_declared`）**不列入**：
 * 它們以點路徑攤平，容器名本身不是合法欄名。
 */
export function reservedScalarColumnsOf(
  requiredFields: Record<string, { type?: string }>,
): readonly string[] {
  return Object.entries(requiredFields)
    .filter(([, spec]) => spec.type !== undefined && spec.type !== 'object')
    .map(([name]) => name)
    .sort();
}

export const RESERVED_SCALAR_CONTRACT_COLUMNS: readonly string[] = reservedScalarColumnsOf(
  (contract as { required_fields: Record<string, { type?: string }> }).required_fields,
);

/** 巢狀物件 → 點路徑扁平化；陣列與 `null` 視為葉節點（以 JSON 字面存放，解析端會還原）。 */
function flatten(obj: Record<string, unknown>, prefix = ''): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      Object.assign(out, flatten(v as Record<string, unknown>, key));
    } else {
      out[key] = v;
    }
  }
  return out;
}

function cell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * @param records   `buildEventContractRecords()` 之 `records`
 * @param extraByRow 逐列之**非契約**分析欄（會被放進 `meta.`）；長度須與 `records` 對齊
 */
export function buildEventContractCsv(
  records: readonly Record<string, unknown>[],
  extraByRow: readonly Record<string, unknown>[] = [],
): string {
  if (records.length === 0) return '';

  const rows = records.map((rec, i) => {
    const flat = flatten(rec);
    for (const [k, v] of Object.entries(extraByRow[i] ?? {})) {
      if (v === null || v === undefined || v === '') continue;
      flat[`meta.${k}`] = v;          // 🔴 一律進 `meta.`，不污染契約之頂層鍵集
    }
    return flat;
  });

  // 欄集＝所有列之聯集；契約欄在前、`meta.` 在後（人讀時契約欄先出現）
  const names = new Set<string>();
  for (const r of rows) for (const k of Object.keys(r)) names.add(k);
  // 🔴 `G3-D2` D3.1 R1（三家全員命中：`CODEX-R1-P1-01`／`GROK-R1-P1-01`／`COMPOSER-R1-P2-01`）：
  //    header 原本**只**取列鍵聯集 ⇒ two_stage 之未標籤匯出（`label` 鍵刻意缺席）
  //    產出的 CSV **連 `label` 欄都沒有**，使用者在 Excel 裡無處可補
  //    ——D3.1 的整條路徑（匯出 → 補標 → 以 `user_csv` 匯入）就此斷掉。
  //    grok 探針：two_stage header＝`direction,event_id,label_origin,scenario,…`（無 label）。
  //
  //    ⇒ **契約導出**：契約 `required_fields` 之**純量**欄一律保留為欄，缺鍵即空欄。
  //    🔴 刻意**不**寫成「`label_origin === 'search_unlabeled'` 就補 `label` 欄」那種值判斷：
  //       那是把「哪些欄該出現」綁到某個值上，日後多一種未標籤來源就漏。
  //       欄集是契約的事實，不是某一列的值的函式。
  //       （與 `G3-D2` R5 學到的「值域是資料不是程式碼，一律從契約導出」同一條原則。）
  //    🔴 只保留**純量**欄：`label_definition`／`lookahead_bars_declared` 是物件，
  //       它們以點路徑攤平（`label_definition.window.horizon_bars`），
  //       把容器名本身當成欄會產出一個解析端不認得的欄。
  for (const name of RESERVED_SCALAR_CONTRACT_COLUMNS) names.add(name);
  const header = [...names].sort((a, b) => {
    const am = a.startsWith('meta.') ? 1 : 0;
    const bm = b.startsWith('meta.') ? 1 : 0;
    return am !== bm ? am - bm : a.localeCompare(b);
  });

  return [header.join(','), ...rows.map((r) => header.map((h) => cell(r[h])).join(','))].join('\n');
}
