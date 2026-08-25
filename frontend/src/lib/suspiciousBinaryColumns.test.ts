/**
 * GAP-3 UX Task 1.7 驗收（`npm --prefix frontend test -- --run suspiciousBinaryColumns`）。
 *
 * 判準字面之唯一來源＝SPEC L1602–1613 之「驗證」欄：
 * ①fixture 含 3 個二元欄 ⇒ 警示 `len == 2` 且集合相等；②全欄皆非二元 ⇒ `[]` 且不報錯。
 *
 * 🔴 ①同時鎖住「不得因為只有一個二元欄就自動選它」（A-4′）——那是本 Task 的
 *    `不可做`，也是 mutation 要打的點；把它放進①，是因為只有 3 欄的 fixture
 *    對「只有一個就自動選」這個變異**沒有鑑別力**（變異了照樣綠＝假綠）。
 */
import { describe, expect, it } from 'vitest';
import { isBinaryColumn, scanBinaryColumns } from '@/lib/suspiciousBinaryColumns';

/** 3 個二元欄（is_up／flag／confirmed）＋ 2 個非二元欄。 */
const COLUMNS = ['symbol', 'is_up', 'price', 'flag', 'confirmed'];
const ROWS = [
  ['ETHUSDT', '1', '3200.5', 'true', '0'],
  ['ETHUSDT', '0', '3210.0', 'false', '1'],
  ['ETHUSDT', '1', '3190.2', 'true', '1'],
];

describe('Task 1.7 可疑欄警示', () => {
  it('① 3 個二元欄且已選其一 ⇒ 警示另外 2 個（len == 2 且集合相等）；只有一個二元欄時仍不自動選', () => {
    const scan = scanBinaryColumns(COLUMNS, ROWS, 'is_up');
    expect(scan.binaryColumns).toEqual(['is_up', 'flag', 'confirmed']);
    expect(scan.suspicious.length).toBe(2);
    expect(new Set(scan.suspicious)).toEqual(new Set(['flag', 'confirmed']));

    // 🔴 A-4′：只有一個二元欄也**不得**自動選它——`suggestedLabelColumn` 是 Task 1.5
    //    label 下拉初始值之唯一來源，改成「只有一個就選它」在這裡就會轉紅。
    const single = scanBinaryColumns(['symbol', 'is_up'], [['ETHUSDT', '1'], ['ETHUSDT', '0']], null);
    expect(single.binaryColumns).toEqual(['is_up']);
    expect(single.suggestedLabelColumn).toBe(null);
    expect(scan.suggestedLabelColumn).toBe(null);
  });

  it('② 全欄皆非二元 ⇒ 警示為空陣列且不報錯', () => {
    const columns = ['symbol', 'price', 'volume'];
    const rows = [['ETHUSDT', '3200.5', '12'], ['BTCUSDT', '65000', '7']];
    const scan = scanBinaryColumns(columns, rows, null);
    expect(scan.binaryColumns).toEqual([]);
    expect(scan.suspicious).toEqual([]);
  });

  it('值域判定：{0,1}／{true,false} 為二元；混值域與三值皆不是', () => {
    expect(isBinaryColumn(['1', '0', '1'])).toBe(true);
    expect(isBinaryColumn(['TRUE', 'false'])).toBe(true);
    expect(isBinaryColumn(['1', '0', '2'])).toBe(false);
    expect(isBinaryColumn(['1', 'true'])).toBe(false);   // 兩個值域不得混用
    expect(isBinaryColumn(['', '  '])).toBe(false);      // 全空欄不算二元
    expect(isBinaryColumn([])).toBe(false);
  });

  it('未選 label 時，全部二元欄都列為可疑（沒有任何一欄被當成已選）', () => {
    const scan = scanBinaryColumns(COLUMNS, ROWS, null);
    expect(scan.suspicious).toEqual(['is_up', 'flag', 'confirmed']);
  });
});
