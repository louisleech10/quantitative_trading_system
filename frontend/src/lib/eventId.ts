/**
 * GAP-3 UX Task 1.3／D-2：`event_id` 之前端呼叫點。
 *
 * 🔴 **不得發明新演算法**（R1 兩家獨立判 BLOCKING）。公式之唯一定義來源＝契約檔
 *    `momentum/Analysis/contracts/event_import_contract.json` 之 `event_id_template`；
 *    後端唯一實作＝`import_contract.canonical_event_id()`。
 *    本檔之 `EVENT_ID_TEMPLATE` 由 `canonicalSourceCoverage.test.ts` **讀該契約檔逐字對證**
 *    ⇒「前後端同一定義來源」是機械閘保證的事實，不是靠紀律維持的約定。
 */

/** 逐字等於契約 `event_id_template`（測試機械對證；改這裡而不改契約會轉紅，反之亦然）。 */
export const EVENT_ID_TEMPLATE = '{symbol}:{timeframe}:{t0}';

/**
 * 逐字等於契約 `ms_magnitude_min`（同上，由 vitest 讀契約檔對證）。
 *
 * GAP-3 UX Task 1.5／殘留 `R-B2-1`：對映 UI 需要在**送出前**就看得出「這個 t0 是秒級」，
 * 才能把契約要求的**毫秒版** `event_id` 先算給使用者看。判定門檻只有這一個來源。
 */
export const MS_MAGNITUDE_MIN = 1000000000000;

/**
 * 由模板產生 `event_id`。`t0` 須為**毫秒整數**。
 * 以模板取代硬編字串拼接，使「公式住在契約」這件事在前端也成立。
 */
export function canonicalEventId(symbol: string, timeframe: string, t0: number): string {
  return EVENT_ID_TEMPLATE
    .replace('{symbol}', String(symbol))
    .replace('{timeframe}', String(timeframe))
    .replace('{t0}', String(t0));
}
