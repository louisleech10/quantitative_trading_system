/**
 * GAP-3 UX Task 5.2 — 事件型表格表頭 tooltip 之文案來源。
 *
 * 🔴 **本檔一個 definition 字面都沒有**：全部由 build-time import
 * `momentum/Analysis/contracts/event_metrics_glossary.json`（Task 5.0 之 SoT）**當場導出**。
 *
 * 為什麼不用「鏡像常數＋vitest 逐字比對」（本檔首版之作法，`CODEX-R1-P1-01` 抓掉）：
 * 那種作法的 production bundle **根本不讀 JSON**——SoT 改了字、前端沒同步跟改，
 * 畫面就會一直顯示舊文案，而漂移只有在**有人跑測試**時才看得到。
 * 「唯一文案來源」必須是 runtime 真的讀的那一份，逐字測試只能當額外保險。
 *
 * 後設欄（以 `_` 起首，如 `_doc`／`_version`）之排除規則與 loader
 * （`momentum/Analysis/event_samples/metrics_glossary.py`）**同一條**：鍵以 `_` 起首即非指標。
 */
import glossary from '../../../momentum/Analysis/contracts/event_metrics_glossary.json';

interface GlossaryEntry {
  term: string;
  definition: string;
  formula_ref: string;
}

/** glossary 各指標鍵之 `definition`（由 SoT 當場導出，非副本）。 */
export const EVENT_METRIC_DEFINITIONS: Record<string, string> = Object.fromEntries(
  Object.entries(glossary as unknown as Record<string, GlossaryEntry | string | number>)
    .filter(([key, value]) => !key.startsWith('_') && typeof value === 'object' && value !== null)
    .map(([key, value]) => [key, (value as GlossaryEntry).definition]),
);

/**
 * Task 5.2 邊界②：glossary 缺該鍵 ⇒ **fail-closed 佔位**，不是空字串。
 *
 * 空字串會讓「這個指標沒人寫定義」看起來跟「這個表頭本來就沒有 tooltip」一樣，
 * 使用者與我們都不會發現漏掉；佔位字串把它顯式講出來，並指名該補在哪個檔。
 */
export const GLOSSARY_MISSING_PREFIX = '尚未登記於指標詞彙表（event_metrics_glossary.json）：';

/**
 * 由**指定的**定義表取 tooltip 文字；缺鍵回佔位（含鍵名），永不回空字串。
 *
 * 定義表作為參數傳入，是為了讓「缺鍵 ⇒ 佔位」這條 fail-closed 路徑能在
 * **真的 render 出來的畫面上**被驗（測試餵一份少一鍵的表），而不是只能靠讀原始碼推論。
 */
export function tooltipFrom(definitions: Record<string, string>, metricKey: string): string {
  const definition = definitions[metricKey];
  return definition ?? `${GLOSSARY_MISSING_PREFIX}${metricKey}`;
}

/** 表頭 tooltip 文字；缺鍵回佔位（含鍵名），永不回空字串。 */
export function metricTooltip(metricKey: string): string {
  return tooltipFrom(EVENT_METRIC_DEFINITIONS, metricKey);
}
