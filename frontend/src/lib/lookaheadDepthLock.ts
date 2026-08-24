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
