/**
 * GAP-3 UX Task 3.3 —— 「該批是否**已被引用**」之判準與其資料來源。
 *
 * 🔴 **PENDING-RULING（待三家裁定）**：本模組之**判準選擇**尚未定案，已於 B6 R1 之
 * review brief 具名請 codex／composer／grok 裁。以下為主委落地之**臨時案（選項 1）**，
 * 刻意把「資料來源」與「確認框」切開——確認框只吃一個 `isReferenced: boolean` prop
 * ⇒ 三家若裁另一案，換的是本檔之 provider，**不是**確認框與其驗收。
 *
 * 為什麼需要裁：偵察（2026-08-26）確認 `import_id` **沒有**任何伺服器端的引用紀錄——
 * `event_import_id` 在 `api/`／`momentum/` 完全不存在（事件模式之後端接線屬 Phase 7／B10），
 * 且 `EventImportService.analyze()` **不落任何檔**，`ic_survivors_*.json` 以 `case_id` 為鍵。
 * 沒有判準就實作，會做出一個**恆顯示或恆不顯示**的警語，TODO 邊界②（未被引用者不顯示）
 * 直接失去鑑別力。
 *
 * 臨時案（選項 1）之語意：**「這批曾被真的拿去做過事件型分析」**。
 * 於 `analyzeEventImport()` 成功回傳時記一筆；刪除該批時把該筆一併移除（不留指向不存在批之紀錄）。
 * 誠實邊界：紀錄存活於**本瀏覽器**，換裝置／清快取即失真。但因 `analyze` 本來就不留存結果、
 * 結果只存在於當時畫面，「這台機器上看過的分析」與「會失去重現的分析」在現況下是同一件事。
 */

const STORAGE_KEY = 'gap3.eventBatchReferences.v1';

/** 讀取本機之引用紀錄；任何不可用／畸形狀況一律回空集合（不猜、不拋）。 */
export function referencedImportIds(): Set<string> {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    // 🔴 malformed 輸入 probe：非陣列、或陣列內含非字串，一律逐項過濾而非整包信任
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === 'string' && x.length > 0));
  } catch {
    return new Set();
  }
}

/** 純述詞：該批是否已被引用。`refs` 由呼叫端傳入 ⇒ 可測、可換來源。 */
export function isImportReferenced(importId: string, refs: Set<string>): boolean {
  return Boolean(importId) && refs.has(importId);
}

function write(ids: Set<string>): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify([...ids].sort()));
  } catch {
    /* 儲存不可用（無痕／配額）⇒ 靜默降級為「未被引用」，不阻擋任何操作 */
  }
}

/** 記下「這批被拿去分析過」。呼叫點＝分析**成功之後**，不是選取當下。 */
export function recordImportReference(importId: string): void {
  if (!importId) return;
  const ids = referencedImportIds();
  if (ids.has(importId)) return;
  ids.add(importId);
  write(ids);
}

/** 該批已被刪除 ⇒ 移除其引用紀錄（否則會留下指向不存在批之紀錄）。 */
export function forgetImportReference(importId: string): void {
  if (!importId) return;
  const ids = referencedImportIds();
  if (!ids.delete(importId)) return;
  write(ids);
}
