/**
 * GAP-3 UX Task 2.1b — 答案窗下界鎖定（前端側）之驗收。
 *
 * SPEC 驗收①之後半：「條件用到 future_2 與 future_7（bar 命名，1h 批）⇒ 答案窗鎖定 >= 7；
 * 嘗試設 5 ⇒ 前端阻擋且 fetch call count == 0」。
 * 深度 7 之導出由 pytest 側（`gap3_lookahead_depth`）驗；本檔驗**鎖定行為**。
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import {
  clampHorizonToLowerBound,
  horizonLowerBoundMessage,
  isHorizonBelowLowerBound,
} from './lookaheadDepthLock';

describe('gap3 lookahead depth lock', () => {
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

  it('阻擋文案含下界值，且不得出現不可機械證明之「label 正確」字樣', () => {
    const msg = horizonLowerBoundMessage(7);
    expect(msg).toContain('7');
    expect(msg).not.toContain('label 正確');
  });
});

describe('gap3 lookahead depth lock — 阻擋須發生在任何網路動作之前', () => {
  const realFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
  });
  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  /** 匯出處理器之最小重現：與 search/page.tsx 中之守衛同一形態（同一函式）。 */
  async function exportGuarded(selected: number, lowerBound: number | null): Promise<'blocked' | 'sent'> {
    if (isHorizonBelowLowerBound(selected, lowerBound)) return 'blocked';
    await fetch('/api/v1/case/import-events');
    return 'sent';
  }

  it('選 5、下界 7 ⇒ blocked 且 fetch call count == 0', async () => {
    const r = await exportGuarded(5, 7);
    expect(r).toBe('blocked');
    expect((globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBe(0);
  });

  it('對照組：選 7、下界 7 ⇒ 送出（防「恆擋型假保證」）', async () => {
    const r = await exportGuarded(7, 7);
    expect(r).toBe('sent');
    expect((globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
  });
});
