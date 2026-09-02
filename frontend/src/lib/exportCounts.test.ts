/**
 * GAP-3 UX Task 1.5／4.1b 之筆數計算驗收（`npm --prefix frontend test -- --run exportCounts`）。
 *
 * R 重開（SPEC D-8）：匯出前篩選退役 ⇒ 本函式不再接條件；守恆式改為
 * `X + Y + droppedUnreadableLabel == M` 且 `N == X + Y`。**不得以估算值**。
 */
import { describe, expect, it } from 'vitest';
import { computeExportCounts, searchRowLabel } from '@/lib/exportCounts';

const ROWS = [
  { price_change: 3.2, positive_case: true },
  { price_change: -1.0, positive_case: false },
  { price_change: 5.5, positive_case: true },
  { price_change: 0.4, positive_case: false },
  { price_change: 7.7, positive_case: true },
  { price_change: 2.0, positive_case: null },      // 沒有標記 ⇒ 不進事件 JSON
];

describe('匯出筆數（無篩選）', () => {
  it('① X + Y + 無法判讀 == M；N == X + Y', () => {
    const c = computeExportCounts(ROWS);
    expect(c.M).toBe(6);
    expect(c.X).toBe(3);
    expect(c.Y).toBe(2);
    expect(c.droppedUnreadableLabel).toBe(1);
    expect(c.X + c.Y + c.droppedUnreadableLabel).toBe(c.M);
    expect(c.N).toBe(c.X + c.Y);
  });

  it('② 不是估算：逐列改動後數字要跟著逐一改變', () => {
    for (let k = 0; k <= ROWS.length; k += 1) {
      const rows = ROWS.slice(0, k);
      const c = computeExportCounts(rows);
      expect(c.M).toBe(k);
      expect(c.X).toBe(rows.filter((r) => r.positive_case === true).length);
      expect(c.Y).toBe(rows.filter((r) => r.positive_case === false).length);
      expect(c.X + c.Y + c.droppedUnreadableLabel).toBe(c.M);
    }
  });

  it('③ 空輸入不報錯，數字皆為 0', () => {
    expect(computeExportCounts([])).toEqual({ N: 0, M: 0, X: 0, Y: 0, droppedUnreadableLabel: 0 });
  });

  it('④ 🔴 CSV 筆數（M）與事件 JSON 筆數（N）在有無標記列時本就不同', () => {
    const c = computeExportCounts(ROWS);
    expect(c.M).toBe(6);                   // CSV 帶全部列（未標記者 label 留空）
    expect(c.N).toBe(5);                   // 其中一列沒標記 ⇒ 事件 JSON 五筆
    expect(c.M - c.N).toBe(c.droppedUnreadableLabel);
  });

  it('⑤ 判讀規則：true／1 為正、false／0 為反，其餘不猜', () => {
    expect(searchRowLabel({ positive_case: true })).toBe(true);
    expect(searchRowLabel({ positive_case: 1 })).toBe(true);
    expect(searchRowLabel({ positive_case: false })).toBe(false);
    expect(searchRowLabel({ positive_case: 0 })).toBe(false);
    expect(searchRowLabel({ positive_case: 'true' })).toBe(null);   // 字串不猜
    expect(searchRowLabel({})).toBe(null);
  });

  it('⑥ 自訂判讀器（Task 1.5 之 CSV 儲存格路徑）走同一套守恆式', () => {
    const cells = ['1', '0', '', 'x', '1'].map((cell) => ({ cell }));
    const c = computeExportCounts(cells, (row) => {
      const s = String((row as { cell: string }).cell).trim();
      return s === '1' ? true : s === '0' ? false : null;
    });
    expect(c).toEqual({ N: 3, M: 5, X: 2, Y: 1, droppedUnreadableLabel: 2 });
  });
});
