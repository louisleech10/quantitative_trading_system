/**
 * GAP-3 UX Task 1.3：`rule_digest`（綁 `search_rule_summary`）之**唯一**前端實作。
 *
 * 🔴 本模組是前端**唯一**允許碰雜湊入口的地方，而且它**只**產出 `rule_digest`。
 *    `source_file_digest` 綁的是完整 `CaseData` 列、由**後端** §G S-9 參考實作計算，
 *    前端不得自算——兩者是兩件事，序列化路徑不共用（SPEC Task 1.3 之 R13 定案）。
 *    把雜湊入口隔離在本檔，使「無任何模組同時碰雜湊入口且寫 source_file_digest」
 *    成為**結構保證**，而不是需要靠掃描原始碼形狀去猜的性質。
 */

/** 真 SHA-256（WebCrypto）；環境無 subtle ⇒ 拋錯，不做假 hash 退路（CODEX-R1-P1-02）。 */
export async function sha256Hex(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error('WebCrypto subtle 不可用：無法計算 rule_digest（不提供非 SHA-256 退路）');
  const buf = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** 搜尋規則摘要之 canonical 文字（`label_definition.canonical_digest` 之輸入）。 */
export function ruleSummaryText(conditions: unknown[], priceChangeMethod: string, timeframe: string): string {
  return JSON.stringify({ conditions, price_change_method: priceChangeMethod, timeframe });
}

/** `label_definition.canonical_digest` ＝ 規則摘要之 sha256。 */
export async function ruleDigestOf(ruleSummary: string): Promise<string> {
  return sha256Hex(ruleSummary);
}
