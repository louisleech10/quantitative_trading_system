/**
 * GAP-3 UX Task 2.1b ＋ `D-004 A-021(c)` — 匯出前 readiness 守衛之驗收。
 *
 * 🔴 **B7 改形**：本檔原本驗「使用者選的答案窗低於導出下界 ⇒ 擋」。Task 4.1 移除主答案窗後
 *    那個比較恆真＝死碼（`A-021(b)`），守衛職責改為 **readiness fail-closed**：
 *    「系統還證明不出這批的深度（`pending`／`error`）⇒ 一個網路動作都不許發生」。
 *    受保護的整段仍包在 `proceed` 內，故仍以 **`proceed` 呼叫次數**直接驗，不必猜原始碼長相。
 *
 * 🔴 保留的反假綠設計（B5 R3／R4 三家提出，改形後同樣適用）：
 *    ①**對照組**（可放行時 `proceed` 真的被呼叫且回其結果）——否則「恆擋」也會全綠；
 *    ②notify 收到的字串**逐字**等於文案函式之輸出——否則守衛只要 `notify('任何字')` 就綠；
 *    ③不同 state ⇒ 不同文案（防守衛硬編一個字串）。
 */
import { describe, expect, it, vi } from 'vitest';
import { exportLowerBoundBlockMessage, withExportLowerBoundGuard } from './lookaheadDepthLock';
import { UNCONSTRAINED_LOWER_BOUND, type LowerBoundState } from './exportFilter';

const state = (over: Partial<LowerBoundState>): LowerBoundState => ({
  status: 'resolved', depthByTimeframe: {}, bound: null, error: null, ...over,
});

const PENDING = state({ status: 'pending' });
const ERROR = state({ status: 'error', error: '後端 500' });
const RESOLVED = state({ status: 'resolved', depthByTimeframe: { '12h': 6 }, bound: 6 });
const RESOLVED_MIXED = state({ status: 'resolved', depthByTimeframe: { '1h': 72, '12h': 6 } });

describe('gap3 export lower-bound guard — 擋（readiness 未就緒）', () => {
  // 🔴 兩種未就緒各驗一次：只驗 pending 的話，把守衛寫成 `status === 'pending'` 仍全綠。
  it.each([
    ['pending（還沒拿到深度）', PENDING],
    ['error（算不出深度）', ERROR],
  ])('%s ⇒ proceed 一次都沒被呼叫、fetch call count == 0', async (_label, s) => {
    const fetchSpy = vi.fn();
    const notify = vi.fn();
    const proceed = vi.fn(async () => {
      await fetchSpy('/api/v1/case/import-events');
      return 'sent' as const;
    });

    const r = await withExportLowerBoundGuard(s, { notify, proceed });

    expect(r).toBeUndefined();
    expect(proceed).toHaveBeenCalledTimes(0);
    expect(fetchSpy).toHaveBeenCalledTimes(0);
    expect(notify).toHaveBeenCalledTimes(1);
    // 驗**配線本身**：notify 收到的須逐字等於文案函式對同一 state 之輸出
    // （只驗 `toContain` 的話，`notify('錯誤')` 之類掏空文案的寫法照樣綠）。
    expect(notify.mock.calls[0][0]).toBe(exportLowerBoundBlockMessage(s));
  });

  it('阻擋文案隨 state 改變（防守衛硬編一個字串）', async () => {
    const notify = vi.fn();
    const proceed = vi.fn(async () => 'sent' as const);

    await withExportLowerBoundGuard(ERROR, { notify, proceed });
    await withExportLowerBoundGuard(PENDING, { notify, proceed });

    expect(proceed).toHaveBeenCalledTimes(0);
    expect(notify.mock.calls[0][0]).toBe(exportLowerBoundBlockMessage(ERROR));
    expect(notify.mock.calls[1][0]).toBe(exportLowerBoundBlockMessage(PENDING));
    expect(notify.mock.calls[0][0]).not.toBe(notify.mock.calls[1][0]);
  });

  it('error 之原因會被帶出來（不是吞掉換成通用句）', () => {
    expect(exportLowerBoundBlockMessage(ERROR)).toBe('後端 500');
    expect(exportLowerBoundBlockMessage(PENDING)).toContain('尚未取得');
  });
});

describe('gap3 export lower-bound guard — 放行（對照組；防「恆擋型假保證」）', () => {
  it.each([
    ['unconstrained（沒有條件）', UNCONSTRAINED_LOWER_BOUND],
    ['resolved（單一 tf）', RESOLVED],
    // 🔴 `A-021(d)`：混 TF 且下界不同（舊 `inexpressible`）**現在可以匯出**——
    //    4.1 之後 horizon_bars 逐列依該列 tf 寫入，per-scope 已可表達。
    ['resolved（混 TF、bound 為 null）', RESOLVED_MIXED],
  ])('%s ⇒ proceed 被呼叫一次且回其結果', async (_label, s) => {
    const notify = vi.fn();
    const proceed = vi.fn(async () => 'sent' as const);

    const r = await withExportLowerBoundGuard(s, { notify, proceed });

    expect(r).toBe('sent');
    expect(proceed).toHaveBeenCalledTimes(1);
    expect(notify).toHaveBeenCalledTimes(0);
  });
});
