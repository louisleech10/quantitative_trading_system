"use client";

import type { EventImportSummary } from "@/lib/types";

/**
 * GAP-3 UX Task 3.2 ＋ 3.3 —— 事件批刪除之二次確認框。
 *
 * 🔴 Task 3.2：**不得以 `window.confirm` 帶過**（須為可測之元件）；未確認 ⇒ 呼叫端不得發出請求。
 * 🔴 Task 3.3：於**同一個**確認框疊加警語，**不另建元件**；有警語時**仍可刪**
 *    ——警語不改動確認流程之控制流（3.2 之「未確認 ⇒ 不發請求」須維持通過）。
 * 🔴 本元件對「是否已被引用」之**資料來源無知**：只吃 `isReferenced` prop
 *    ⇒ `eventBatchReferences.ts` 之判準若經三家改裁，本元件與其驗收都不必動。
 * 🔴 確認鍵**刻意不設 `disabled`**：設了的話 `fireEvent.click` 什麼都不會觸發、測試恆綠
 *    （B4 之教訓）。進行中之保護改由呼叫端以執行期狀態處理。
 */
export const REFERENCED_WARNING = "引用它的分析結果將無法重現";

/**
 * 🔴 R1 群集 C（`CODEX-R1-P1-03`）：引用紀錄之現行來源只在**這個瀏覽器**有效
 * （判準與誠實邊界見 `@/lib/eventBatchReferences`）。原文案「這批事件已被引用」是**全域語氣**，
 * 換裝置／清快取時使用者會以為「沒被引用」——那是**說了一件不成立的事**，
 * 比「什麼都不說」更糟。故顯示時必須帶上範圍限定語。
 * 反向（未被引用）**不加任何宣稱**：不能說「這批沒有被引用」，因為本機紀錄證明不了那件事。
 */
export const REFERENCED_SCOPE_PREFIX = "在這個瀏覽器上，這批事件曾被拿去分析";

export interface EventBatchDeleteDialogProps {
  batch: EventImportSummary;
  /** 該批是否已被引用（判準與來源見 `@/lib/eventBatchReferences`）。 */
  isReferenced: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  /** 刪除進行中——只影響文案，不影響可按性。 */
  busy?: boolean;
  errorMessage?: string | null;
}

export default function EventBatchDeleteDialog({
  batch,
  isReferenced,
  onCancel,
  onConfirm,
  busy = false,
  errorMessage = null,
}: EventBatchDeleteDialogProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="刪除事件批確認"
      data-testid="event-batch-delete-dialog"
      className="mt-3 rounded-lg border border-rose-400/40 bg-rose-500/10 p-4"
    >
      <p className="text-sm font-bold text-rose-100">確定要刪除這批事件嗎？此操作無法撤銷。</p>

      <ul className="mt-2 space-y-1 text-xs text-slate-200">
        <li className="font-mono" data-testid="event-batch-delete-import-id">{batch.import_id}</li>
        {/* 筆數與匯入時間取自批列表該列既有欄位——不另查後端（Task 3.2 實作要點 1） */}
        <li>
          筆數：<span data-testid="event-batch-delete-n-events">{batch.n_events}</span>
        </li>
        <li>
          匯入時間：<span data-testid="event-batch-delete-imported-at">{batch.imported_at}</span>
        </li>
      </ul>

      {isReferenced && (
        <p
          data-testid="event-batch-delete-referenced-warning"
          className="mt-3 rounded border border-amber-400/40 bg-amber-500/10 p-2 text-xs text-amber-100"
        >
          {REFERENCED_SCOPE_PREFIX}：刪除後，{REFERENCED_WARNING}。仍可刪除。
          （這筆紀錄只存在於這台裝置的瀏覽器；在別的裝置上分析過的話，這裡看不到。）
        </p>
      )}

      {errorMessage && (
        <p data-testid="event-batch-delete-error" className="mt-3 text-xs text-rose-300">
          刪除失敗：{errorMessage}
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          data-testid="event-batch-delete-confirm"
          onClick={onConfirm}
          className="rounded bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-500"
        >
          {busy ? "刪除中…" : "確認刪除"}
        </button>
        <button
          type="button"
          data-testid="event-batch-delete-cancel"
          onClick={onCancel}
          className="rounded border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
        >
          取消
        </button>
      </div>
    </div>
  );
}
