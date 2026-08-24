/**
 * GAP-3 UX Task 2.1b — 答案窗下界鎖定（前端側）之驗收。
 *
 * SPEC 驗收①之後半：「嘗試設低於下界 ⇒ 前端阻擋且 `fetch` call count `== 0`」。
 * 深度 7 之導出由 pytest 側（`gap3_lookahead_depth`）驗；本檔驗**鎖定行為**。
 *
 * 🔴 R3 修法：阻擋不再測「一個與 page 同形態的替身」，而是測 page **實際呼叫的那個函式**
 *    `withHorizonLowerBoundGuard`——受保護的整段包在 `proceed` 內，
 *    「未達下界時網路動作不會發生」因此可用 `proceed` 呼叫次數直接驗，不必猜原始碼長相。
 */
import { describe, expect, it, vi } from 'vitest';
import {
  clampHorizonToLowerBound,
  horizonLowerBoundMessage,
  isHorizonBelowLowerBound,
  withHorizonLowerBoundGuard,
} from './lookaheadDepthLock';

describe('gap3 lookahead depth lock — 判定', () => {
  it('低於下界即阻擋（下界 7、選 5）', () => {
    expect(isHorizonBelowLowerBound(5, 7)).toBe(true);
  });

  it('等於或高於下界皆放行（保守方向永遠允許）', () => {
    expect(isHorizonBelowLowerBound(7, 7)).toBe(false);
    expect(isHorizonBelowLowerBound(12, 7)).toBe(false);
  });

  it('尚無下界（null／undefined）⇒ 無約束，不得誤擋', () => {
    expect(isHorizonBelowLowerBound(1, null)).toBe(false);
    expect(isHorizonBelowLowerBound(1, undefined)).toBe(false);
  });

  it('夾值只往上，永不往下', () => {
    expect(clampHorizonToLowerBound(5, 7)).toBe(7);
    expect(clampHorizonToLowerBound(12, 7)).toBe(12);
    expect(clampHorizonToLowerBound(3, null)).toBe(3);
  });
});

describe('gap3 lookahead depth lock — 阻擋文案', () => {
  // 🔴 COMPOSER-R3-P2-01／GROK-R3-P3-01：原本只驗 `toContain('7')`。
  //    「17 根」含子字串「7」；`String(lowerBound)` 也含。兩種掏空文案的壞法都能全綠。
  //    改為**逐字**比對整串，並另驗「換一個下界會得到不同字串」（防硬編碼）。
  const expected = (n: number) =>
    `篩選條件引用之未來欄最遠看到第 ${n} 根，答案窗不得低於 ${n} 根` +
    `（低於此值＝答案窗內已含條件看過的未來資料）。可以往上調，不能往下調。`;

  it('文案逐字相等（不是「含有那個數字」）', () => {
    expect(horizonLowerBoundMessage(7)).toBe(expected(7));
  });

  it('不同下界 ⇒ 不同文案（防硬編碼／忽略參數）', () => {
    expect(horizonLowerBoundMessage(17)).toBe(expected(17));
    expect(horizonLowerBoundMessage(7)).not.toBe(horizonLowerBoundMessage(17));
  });

  it('不得出現不可機械證明之「label 正確」字樣', () => {
    expect(horizonLowerBoundMessage(7)).not.toContain('label 正確');
  });
});

describe('gap3 lookahead depth lock — 守衛之行為（page 實際呼叫的那個函式）', () => {
  it('選 5、下界 7 ⇒ proceed 一次都沒被呼叫、fetch call count == 0', async () => {
    const fetchSpy = vi.fn();
    const notify = vi.fn();
    const proceed = vi.fn(async () => {
      await fetchSpy('/api/v1/case/import-events');
      return 'sent' as const;
    });

    const r = await withHorizonLowerBoundGuard(5, 7, { notify, proceed });

    expect(r).toBeUndefined();
    expect(proceed).toHaveBeenCalledTimes(0);
    expect(fetchSpy).toHaveBeenCalledTimes(0);
    expect(notify).toHaveBeenCalledTimes(1);
    expect(notify.mock.calls[0][0]).toContain('7');
  });

  it('對照組：選 7、下界 7 ⇒ proceed 被呼叫且回其結果（防「恆擋型假保證」）', async () => {
    const notify = vi.fn();
    const proceed = vi.fn(async () => 'sent' as const);

    const r = await withHorizonLowerBoundGuard(7, 7, { notify, proceed });

    expect(r).toBe('sent');
    expect(proceed).toHaveBeenCalledTimes(1);
    expect(notify).toHaveBeenCalledTimes(0);
  });

  it('尚無下界（null）⇒ 放行（防把「還沒接上值」誤擋成阻擋）', async () => {
    const notify = vi.fn();
    const proceed = vi.fn(async () => 'sent' as const);

    expect(await withHorizonLowerBoundGuard(1, null, { notify, proceed })).toBe('sent');
    expect(proceed).toHaveBeenCalledTimes(1);
    expect(notify).toHaveBeenCalledTimes(0);
  });
});
