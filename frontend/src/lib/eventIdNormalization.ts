/**
 * GAP-3 UX Task 1.5 ＋ 具名殘留 `R-B2-1` — 秒級 `t0` 之 `event_id` 摩擦（純函式）。
 *
 * **摩擦是什麼**：使用者上傳秒級 `t0` 的 CSV 時，後端會把 `t0` 正規化成毫秒（Task 1.4），
 * 但 `event_id` 是使用者自己寫的字串，仍是秒版 ⇒ D-2 之 canonical 檢核不符、整批 fail-closed
 * 拒收。使用者得先被拒一次、看懂訊息、回去改檔，才能匯入。
 *
 * **本檔怎麼解**：對映一填好，就在**送出前**用契約模板算出毫秒版 `event_id` 給使用者看
 * （三家 R2 判此屬 Task 1.5：「前端對映 UI 應在單位偵測後預填正規化 ID」）。
 *
 * 🔴 **只警示不阻擋**：前端解析與後端 pandas 解析在極端 CSV 上可能不同，
 *    契約檢核之權威一律是後端（fail-closed 那條路不動）。
 * 🔴 **不得發明第二份公式**：ID 由 `eventId.ts::canonicalEventId()` 產生（其模板逐字對證契約），
 *    單位門檻由 `MS_MAGNITUDE_MIN`（同樣對證契約）決定——本檔一個字面都不自寫。
 */

import { MS_MAGNITUDE_MIN, canonicalEventId } from '@/lib/eventId';

/** 單位偵測結果；`undetected` ＝兩帶皆不落入（後端亦不猜，直接拒）。 */
export type T0Unit = 'ms' | 'seconds' | 'undetected';

export interface EventIdMismatch {
  /** 0-based 資料列序（不含標頭）。 */
  row: number;
  given: string;
  expected: string;
}

export interface EventIdNormalizationReport {
  /** 本批 t0 之單位（逐列判定後之單一結論；混雜 ⇒ `undetected`）。 */
  unit: T0Unit;
  /** 已檢查之列數（對映不全時為 0）。 */
  checked: number;
  /** 使用者所寫 ID 與契約毫秒版不符之列（依列序，最多 `limit` 筆）。 */
  mismatches: EventIdMismatch[];
}

/**
 * 單值單位偵測——與後端 `detect_t0_unit_ms` **同一條門檻**導出：
 * 合法 ms 帶＝`[min, min*1000)`；秒帶＝「×1000 後落在 ms 帶」。兩帶依建構互斥，不必猜。
 */
export function detectT0UnitMs(value: number): { unit: T0Unit; ms: number | null } {
  if (!Number.isInteger(value)) return { unit: 'undetected', ms: null };
  const max = MS_MAGNITUDE_MIN * 1000;
  if (value >= MS_MAGNITUDE_MIN && value < max) return { unit: 'ms', ms: value };
  if (value * 1000 >= MS_MAGNITUDE_MIN && value * 1000 < max) return { unit: 'seconds', ms: value * 1000 };
  return { unit: 'undetected', ms: null };
}

interface InspectInput {
  /** 逐列之四個值；缺任一欄 ⇒ 呼叫端別呼叫（回 checked=0）。 */
  rows: ReadonlyArray<{ eventId: string; symbol: string; timeframe: string; t0: string }>;
  limit?: number;
}

/** 逐列比對「使用者寫的 `event_id`」vs「契約毫秒版 `event_id`」。 */
export function inspectEventIdNormalization({ rows, limit = 5 }: InspectInput): EventIdNormalizationReport {
  const units = new Set<T0Unit>();
  const mismatches: EventIdMismatch[] = [];
  let checked = 0;

  rows.forEach((r, index) => {
    const raw = String(r.t0).trim();
    if (raw === '') return;
    const numeric = Number(raw);
    const { unit, ms } = detectT0UnitMs(numeric);
    units.add(unit);
    checked += 1;
    if (ms === null) return;
    const expected = canonicalEventId(String(r.symbol).trim(), String(r.timeframe).trim(), ms);
    const given = String(r.eventId).trim();
    if (given !== expected && mismatches.length < limit) mismatches.push({ row: index, given, expected });
  });

  const unit: T0Unit = units.size === 1 ? [...units][0] : 'undetected';
  return { unit, checked, mismatches };
}
