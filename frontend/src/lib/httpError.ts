/**
 * HTTP 錯誤回應 → **人看得懂的一行字**。
 *
 * 🔴 出生事故（2026-09-02 使用者 UAT B11）：畫面顯示 `[object Object]`。
 * 成因是各處都寫 `new Error(body.detail || '預設訊息')`，而 FastAPI 的 `detail`
 * **不一定是字串**——結構化拒收（`{kind, message, failures}`）走的就是物件，
 * `new Error(物件)` 的 message 就變成 `[object Object]`，使用者完全看不出發生什麼事。
 *
 * 🔴 **不要在呼叫點自己判型別**：那正是原本的寫法，十幾處各寫一份、漏一處就再出現一次。
 * 一律走本函式。
 */

/** 從結構化 detail 取訊息；取不到就回 `null`（交給呼叫端的 fallback）。 */
function messageOf(detail: unknown): string | null {
  if (typeof detail === 'string') return detail.trim() || null;
  if (typeof detail === 'number' || typeof detail === 'boolean') return String(detail);
  if (detail === null || detail === undefined) return null;

  if (Array.isArray(detail)) {
    // FastAPI 422 之 validation error 陣列：逐項取 msg
    const parts = detail.map((d) => messageOf(d)).filter((s): s is string => !!s);
    return parts.length > 0 ? parts.join('；') : null;
  }

  const obj = detail as Record<string, unknown>;
  // 本專案之結構化拒收有兩種形狀：{kind, message, failures[]}（事件匯入）
  // 與 {code, message?}（Feature Factory）。後者常常**只有 code**——那也要顯示，
  // 因為 `run_not_found` 這種字對使用者雖不漂亮，卻足以讓人查出是哪一類錯。
  const head = typeof obj.message === 'string' ? obj.message
    : typeof obj.msg === 'string' ? obj.msg
      : typeof obj.error === 'string' ? obj.error
        : typeof obj.code === 'string' ? obj.code
          : null;
  if (head === null) return null;

  const kind = typeof obj.kind === 'string' ? obj.kind
    : (typeof obj.code === 'string' && obj.code !== head ? obj.code : null);
  const failures = Array.isArray(obj.failures) ? obj.failures : [];
  const shown = failures.slice(0, 3).map((f) => {
    const r = f as Record<string, unknown>;
    const where = r.row === null || r.row === undefined ? '' : `列 ${String(r.row)}`;
    const field = typeof r.field === 'string' && r.field ? `／${r.field}` : '';
    const reason = typeof r.reason === 'string' && r.reason ? `／${r.reason}` : '';
    return `${where}${field}${reason}`.replace(/^／/, '');
  }).filter((s) => s.length > 0);

  const tail = failures.length > shown.length ? `（另有 ${failures.length - shown.length} 筆）` : '';
  return [
    kind ? `${kind}：${head}` : head,
    shown.length > 0 ? `— ${shown.join('；')}${tail}` : '',
  ].filter(Boolean).join(' ');
}

/**
 * @param body     `response.json()` 的結果（或任何已解析的回應主體）
 * @param fallback 取不出訊息時要顯示的字（一律要給，別讓使用者看到空白）
 */
export function httpErrorMessage(body: unknown, fallback: string): string {
  if (body === null || body === undefined) return fallback;
  const container = body as Record<string, unknown>;
  return messageOf(container.detail)
    ?? messageOf(container.error)
    ?? messageOf(body)
    ?? fallback;
}
