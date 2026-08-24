/**
 * GAP-3 UX Task 2.1b — 答案窗下界之**鎖定**（前端側）。
 *
 * 🔴 **本檔不計算深度。** 深度公式之唯一權威實作是
 * `momentum/Analysis/event_samples/lookahead_depth.py::depth_by_timeframe()`；
 * 在 TS 重寫一份＝第二份副本，兩條路徑必然漂移（SPEC Task 2.1b「本批唯一權威定義」）。
 * 本檔只做**比較與阻擋**：拿到後端導出之下界，決定「這個選值可不可以送出」。
 *
 * 語意：使用者可**往上**調（保守方向永遠允許），**不得**調低於導出值
 * ——那等於明知條件用到第 7 根卻只隔 5 根。
 */

/** 該選值是否低於導出下界（＝必須阻擋送出）。下界為 null／undefined ⇒ 尚無約束。 */
export function isHorizonBelowLowerBound(
  selectedBars: number,
  lowerBound: number | null | undefined,
): boolean {
  if (lowerBound === null || lowerBound === undefined) return false;
  return selectedBars < lowerBound;
}

/** 把選值夾到下界之上（只往上夾，永不往下）。 */
export function clampHorizonToLowerBound(
  selectedBars: number,
  lowerBound: number | null | undefined,
): number {
  if (lowerBound === null || lowerBound === undefined) return selectedBars;
  return selectedBars < lowerBound ? lowerBound : selectedBars;
}

/** 阻擋原因文案（未達下界時顯示；不得說「label 正確」之類不可機械證明之語）。 */
export function horizonLowerBoundMessage(lowerBound: number): string {
  return (
    `篩選條件引用之未來欄最遠看到第 ${lowerBound} 根，答案窗不得低於 ${lowerBound} 根` +
    `（低於此值＝答案窗內已含條件看過的未來資料）。可以往上調，不能往下調。`
  );
}

/**
 * 匯出前之下界守衛：**未達下界時，`proceed` 一次都不會被呼叫**。
 *
 * 🔴 為什麼是這個形狀（GROK-R3-P2-01／CODEX-R3-P2-01／-02 三條合併之修法）：
 * 先前 page 內是「`if (…) return;` 之後接一長串匯出邏輯」，那種形狀**只能用原始碼 AST 檢查**，
 * 而 AST 檢查鎖的是「第一個命中」「子樹裡任一個 return」——三家各自用誘餌守衛、
 * 巢狀 return、把真守衛移到 `await` 之後，都能讓 AST 全綠而執行期照樣先做網路重活。
 *
 * ⇒ 改成**把要保護的整段包進 `proceed`**。這樣「阻擋早於任何網路動作」不再是需要被檢查的性質，
 * 而是**結構上保證**的事實：`proceed` 沒被呼叫，裡面的 `await` 就不可能發生。
 * 於是本函式可以用**真正的行為測試**驗（`proceed` 呼叫次數 `== 0`），不必再猜原始碼長相。
 */
export async function withHorizonLowerBoundGuard<T>(
  selectedBars: number,
  lowerBound: number | null | undefined,
  deps: { notify: (message: string) => void; proceed: () => Promise<T> },
): Promise<T | undefined> {
  if (isHorizonBelowLowerBound(selectedBars, lowerBound)) {
    deps.notify(horizonLowerBoundMessage(lowerBound as number));
    return undefined;
  }
  return deps.proceed();
}
