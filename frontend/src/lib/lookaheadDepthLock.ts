/**
 * GAP-3 UX Task 2.1b — 匯出前之下界守衛（前端側）。
 *
 * 🔴 **本檔不計算深度。** 深度公式之唯一權威實作是
 * `momentum/Analysis/event_samples/lookahead_depth.py::depth_by_timeframe()`；
 * 在 TS 重寫一份＝第二份副本，兩條路徑必然漂移（SPEC Task 2.1b「本批唯一權威定義」）。
 *
 * 🔴 **`D-004 A-021(c)` 之改形（B7／Task 4.1）**：本檔原本的職責是「比較使用者選的答案窗與
 * 導出下界」。Task 4.1 移除主答案窗後，`window.horizon_bars` **由深度導出**而非使用者選
 * ⇒ 那個比較恆真＝死碼，已隨 `exportAllowedUnderBound` 一併移除。
 * 但守衛**本體不刪**，職責改為 **readiness fail-closed**：
 * 「系統還證明不出這批的深度（`pending`／`error`）時，一個網路動作都不許發生」。
 * 三家 consult 之 `RULING-3(c)` 為 **2 vs 1**（codex＋grok 裁保留、composer 裁移除），取多數且較嚴版。
 */
import { exportAllowedByLowerBoundState, type LowerBoundState } from './exportFilter';

/** 擋下時顯示的原因（`error` 有值就用它，否則用 readiness 的通用說法）。 */
export function exportLowerBoundBlockMessage(state: LowerBoundState): string {
  return (
    state.error
    ?? '尚未取得答案窗下界（系統還無法證明這批條件安全），請稍候或修正條件後再匯出'
  );
}

/**
 * 匯出前之 readiness 守衛：**未就緒時，`proceed` 一次都不會被呼叫**。
 *
 * 🔴 為什麼是這個形狀（GROK-R3-P2-01／CODEX-R3-P2-01／-02 三條合併之修法，B7 續用）：
 * 先前 page 內是「`if (…) return;` 之後接一長串匯出邏輯」，那種形狀**只能用原始碼 AST 檢查**，
 * 而 AST 檢查鎖的是「第一個命中」「子樹裡任一個 return」——三家各自用誘餌守衛、
 * 巢狀 return、把真守衛移到 `await` 之後，都能讓 AST 全綠而執行期照樣先做網路重活。
 *
 * ⇒ **把要保護的整段包進 `proceed`**。這樣「阻擋早於任何網路動作」不再是需要被檢查的性質，
 * 而是**結構上保證**的事實：`proceed` 沒被呼叫，裡面的 `await` 就不可能發生。
 * 🔴 **不得**把它退回成裸 `if (…) return;` 後接長串 `await`——那正是 B5 R3 已否定、
 * 可被 AST 繞過的形狀（grok 於 consult 輪明列此警告）。
 */
export async function withExportLowerBoundGuard<T>(
  state: LowerBoundState,
  deps: { notify: (message: string) => void; proceed: () => Promise<T> },
): Promise<T | undefined> {
  if (!exportAllowedByLowerBoundState(state)) {
    deps.notify(exportLowerBoundBlockMessage(state));
    return undefined;
  }
  return deps.proceed();
}
