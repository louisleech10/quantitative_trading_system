/**
 * GAP-3 UX Task 2.3 驗收（`npm --prefix frontend test -- --run exportCounts`）。
 *
 * 判準字面之唯一來源＝SPEC L1880–1891「驗證」欄：
 * ①`N + 被濾掉數 == M`；②`X + Y == N`。**不得以估算值**。
 */
import { describe, expect, it, vi } from 'vitest';
import { computeExportCounts, searchRowLabel } from '@/lib/exportCounts';
import * as exportCountsModule from '@/lib/exportCounts';
import * as exportFilterModule from '@/lib/exportFilter';

const ROWS = [
  { price_change: 3.2, positive_case: true },
  { price_change: -1.0, positive_case: false },
  { price_change: 5.5, positive_case: true },
  { price_change: 0.4, positive_case: false },
  { price_change: 7.7, positive_case: true },
  { price_change: 2.0, positive_case: null },      // 沒有標記 ⇒ 不會被匯出
];

describe('Task 2.3 即時筆數', () => {
  it('① N + 被濾掉數 == M（含條件與不含條件兩種）', () => {
    const none = computeExportCounts(ROWS, []);
    expect(none.N + none.filteredOut).toBe(none.M);
    expect(none.M).toBe(6);

    const filtered = computeExportCounts(ROWS, [{ column: 'price_change', op: '>=', value: 2.0 }]);
    expect(filtered.N + filtered.filteredOut).toBe(filtered.M);
    // 手算：≥2 者為 3.2／5.5／7.7／2.0 共 4 筆；其中 2.0 無標記不匯出 ⇒ N = 3
    expect(filtered.droppedByFilters).toBe(2);
    expect(filtered.droppedUnreadableLabel).toBe(1);
    expect(filtered.N).toBe(3);
  });

  it('② X + Y == N（無標記者不塞進 X 或 Y，而是單獨計數並排除）', () => {
    const c = computeExportCounts(ROWS, []);
    expect(c.X + c.Y).toBe(c.N);
    expect(c.X).toBe(3);
    expect(c.Y).toBe(2);
    expect(c.N).toBe(5);                 // 6 列裡有 1 列沒標記
    expect(c.droppedUnreadableLabel).toBe(1);
  });

  it('③ 不是估算：逐列改動後數字要跟著逐一改變（抽樣推估會在這裡失準）', () => {
    for (let cut = -2; cut <= 8; cut += 1) {
      const c = computeExportCounts(ROWS, [{ column: 'price_change', op: '>=', value: cut }]);
      const manual = ROWS.filter((r) => r.price_change >= cut);
      expect(c.droppedByFilters).toBe(ROWS.length - manual.length);
      expect(c.X).toBe(manual.filter((r) => r.positive_case === true).length);
      expect(c.Y).toBe(manual.filter((r) => r.positive_case === false).length);
      expect(c.X + c.Y).toBe(c.N);
      expect(c.N + c.filteredOut).toBe(c.M);
    }
  });

  it('④ 空輸入不報錯，四個數字皆為 0', () => {
    expect(computeExportCounts([], [])).toEqual({
      N: 0, M: 0, X: 0, Y: 0, filteredOut: 0, droppedByFilters: 0, droppedUnreadableLabel: 0,
    });
  });

  it('⑤ 判讀規則：true／1 為正、false／0 為反，其餘不猜', () => {
    expect(searchRowLabel({ positive_case: true })).toBe(true);
    expect(searchRowLabel({ positive_case: 1 })).toBe(true);
    expect(searchRowLabel({ positive_case: false })).toBe(false);
    expect(searchRowLabel({ positive_case: 0 })).toBe(false);
    expect(searchRowLabel({ positive_case: 'true' })).toBe(null);   // 字串不猜
    expect(searchRowLabel({})).toBe(null);
  });

  it('⑥ 計數確實走 Task 2.1 之同一支篩選實作（呼叫探針＋餵入內容）', () => {
    // 🔴 §6.2：不用「原始碼裡有出現 applyExportFilters」這種形狀斷言，
    //    改以執行期探針證明它**真的被呼叫**、而且**餵進去的是那些條件**。
    const spy = vi.spyOn(exportFilterModule, 'applyExportFilters');
    try {
      const conditions = [{ column: 'price_change', op: '>=' as const, value: 1 }];
      exportCountsModule.computeExportCounts(ROWS, conditions);
      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy.mock.calls[0][1]).toBe(conditions);
    } finally {
      spy.mockRestore();
    }
  });
});
