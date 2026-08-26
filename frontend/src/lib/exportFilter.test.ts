/**
 * GAP-3 UX Task 2.1 驗收（`npm --prefix frontend test -- --run exportFilter`）。
 *
 * 判準字面之唯一來源＝SPEC L1799–1810「驗證」欄：≥6 條；
 * 含「篩選後筆數 `==` 手算筆數」之**數值**斷言。
 * TODO 邊界：①只篩數值欄（字串欄不得出現在可選清單）②條件為空 ⇒ 匯出筆數 `==` 原筆數。
 */
import { describe, expect, it } from 'vitest';
import {
  applyExportFilters,
  buildExportFilterSpec,
  isUsableCondition,
  nextLowerBoundState,
  numericColumnsOf,
  referencedColumnsOf,
  rowPassesCondition,
  type ExportFilterCondition,
  type LowerBoundState,
} from '@/lib/exportFilter';

/** 6 列；`symbol`／`market_phase` 是字串欄，其餘為數值欄。 */
const ROWS = [
  { symbol: 'ETHUSDT', market_phase: 'up', price_change: 3.2, volume_multiplier: 1.5, future_2bar_return: 0.9, positive_case: true },
  { symbol: 'ETHUSDT', market_phase: 'up', price_change: -1.0, volume_multiplier: 2.5, future_2bar_return: -0.4, positive_case: false },
  { symbol: 'BTCUSDT', market_phase: 'down', price_change: 5.5, volume_multiplier: 0.8, future_2bar_return: 2.1, positive_case: true },
  { symbol: 'BTCUSDT', market_phase: 'down', price_change: 0.4, volume_multiplier: 3.1, future_2bar_return: 0.1, positive_case: false },
  { symbol: 'SOLUSDT', market_phase: 'up', price_change: 7.7, volume_multiplier: 1.1, future_2bar_return: 4.4, positive_case: true },
  { symbol: 'SOLUSDT', market_phase: 'flat', price_change: 2.0, volume_multiplier: 2.0, future_2bar_return: 1.0, positive_case: false },
];

describe('Task 2.1 匯出前篩選', () => {
  it('① 只有數值欄可選；字串欄不得出現在清單（SPEC 邊界①）', () => {
    const cols = numericColumnsOf(ROWS);
    expect(cols).toEqual(['future_2bar_return', 'price_change', 'volume_multiplier']);
    expect(cols).not.toContain('symbol');
    expect(cols).not.toContain('market_phase');
    expect(cols).not.toContain('positive_case');      // boolean 是標記，不是可比大小的量
  });

  it('①b 某欄只要有一列是非空的非數值，就不算數值欄（不能只看第一列）', () => {
    const mixed = [{ x: 1 }, { x: 2 }, { x: 'n/a' }];
    expect(numericColumnsOf(mixed)).toEqual([]);
    const sparse = [{ x: 1 }, { x: null }, { x: '' }, { x: 3 }];
    expect(numericColumnsOf(sparse)).toEqual(['x']);   // 空值不否定「這是數值欄」
  });

  it('② 條件為空 ⇒ 匯出筆數 == 原筆數（不得因面板存在而改變預設行為）', () => {
    expect(applyExportFilters(ROWS, []).length).toBe(ROWS.length);
    // 半填的條件（選了欄位還沒填值）同樣不得改變結果
    expect(applyExportFilters(ROWS, [{ column: 'price_change', op: '>=' }]).length).toBe(ROWS.length);
  });

  it('③ 篩選後筆數 == 手算筆數（數值斷言，逐列列出）', () => {
    const kept = applyExportFilters(ROWS, [{ column: 'price_change', op: '>=', value: 2.0 }]);
    // 手算：3.2 ✓、-1.0 ✗、5.5 ✓、0.4 ✗、7.7 ✓、2.0 ✓（閉區間）⇒ 4 筆
    expect(kept.length).toBe(4);
    expect(kept.map((r) => r.price_change)).toEqual([3.2, 5.5, 7.7, 2.0]);
  });

  it('④ 多條件是 AND；區間為閉區間', () => {
    const kept = applyExportFilters(ROWS, [
      { column: 'price_change', op: '>=', value: 2.0 },
      { column: 'volume_multiplier', op: 'between', range: [1.0, 2.0] },
    ]);
    // price_change ≥ 2 ⇒ 3.2／5.5／7.7／2.0；其中 volume ∈ [1,2] ⇒ 1.5、1.1、2.0（0.8 落選）
    expect(kept.map((r) => r.volume_multiplier)).toEqual([1.5, 1.1, 2.0]);
  });

  it('⑤ 面板不改動任何原始欄位值（回傳的是原列之參考，且原陣列不變）', () => {
    const before = JSON.stringify(ROWS);
    const kept = applyExportFilters(ROWS, [{ column: 'price_change', op: '<=', value: 0.5 }]);
    expect(JSON.stringify(ROWS)).toBe(before);
    expect(kept[0]).toBe(ROWS[1]);                     // 同一個物件參考，不是複本
  });

  it('⑥ 缺值／非數值之儲存格一律不通過（不猜）', () => {
    expect(rowPassesCondition({ x: undefined }, { column: 'x', op: '>=', value: 0 })).toBe(false);
    expect(rowPassesCondition({ x: '3' }, { column: 'x', op: '>=', value: 0 })).toBe(false);
    expect(rowPassesCondition({ x: Number.NaN }, { column: 'x', op: '>=', value: 0 })).toBe(false);
    expect(rowPassesCondition({ x: 0 }, { column: 'x', op: '>=', value: 0 })).toBe(true);
  });

  it('⑦ 條件可用性：欄名、數值有限、區間下界 ≤ 上界', () => {
    const cases: [ExportFilterCondition, boolean][] = [
      [{ column: '', op: '>=', value: 1 }, false],
      [{ column: 'x', op: '>=', value: Number.NaN }, false],
      [{ column: 'x', op: 'between', range: [2, 1] }, false],
      [{ column: 'x', op: 'between', range: [1, 2] }, true],
      [{ column: 'x', op: '<=', value: 0 }, true],
    ];
    for (const [cond, want] of cases) expect(isUsableCondition(cond)).toBe(want);
  });

  it('⑧ 引用欄只含條件用到的欄（附帶欄不得混入，否則會過度 purge）', () => {
    expect(referencedColumnsOf([
      { column: 'future_2bar_return', op: '>=', value: 0 },
      { column: 'price_change', op: '<=', value: 9 },
      { column: 'future_2bar_return', op: '<=', value: 5 },
      { column: 'ignored_incomplete', op: '>=' },
    ])).toEqual(['future_2bar_return', 'price_change']);
  });

  it('⑩ 下界狀態機（`D-002 A-004` 之決策本體）：無條件 ⇒ null；resolved ⇒ 取最嚴；error ⇒ **保留現值**', () => {
    const had: LowerBoundState = { bound: 7, error: null };

    // 沒有條件就沒有約束——是 null，不是 0，也不是沿用舊值
    expect(nextLowerBoundState(had, { kind: 'no-conditions' })).toEqual({ bound: null, error: null });

    // 逐 tf 下界不同時取最嚴者（往上調永遠允許，往下調才是危險方向）
    expect(nextLowerBoundState({ bound: null, error: null },
      { kind: 'resolved', depthByTimeframe: { '1h': 72, '12h': 6 } })).toEqual({ bound: 72, error: null });
    expect(nextLowerBoundState(had,
      { kind: 'resolved', depthByTimeframe: {} })).toEqual({ bound: null, error: null });

    // 🔴 算不出下界時**不得**當成「沒有約束」——那會讓使用者在系統無法證明安全時把答案窗調到任意小
    expect(nextLowerBoundState(had, { kind: 'error', message: 'boom' }))
      .toEqual({ bound: 7, error: 'boom' });
    expect(nextLowerBoundState({ bound: null, error: null }, { kind: 'error', message: 'boom' }))
      .toEqual({ bound: null, error: 'boom' });
  });

  it('⑨ 契約形狀：無可用條件 ⇒ null（不寫空殼）；有條件 ⇒ version/combinator/conditions', () => {
    expect(buildExportFilterSpec([])).toBe(null);
    expect(buildExportFilterSpec([{ column: 'x', op: '>=' }])).toBe(null);
    expect(buildExportFilterSpec([
      { column: 'price_change', op: '>=', value: 2 },
      { column: 'volume_multiplier', op: 'between', range: [1, 2] },
    ])).toEqual({
      version: 1,
      combinator: 'AND',
      conditions: [
        { column: 'price_change', op: '>=', value: 2 },
        { column: 'volume_multiplier', op: 'between', range: [1, 2] },
      ],
    });
  });
});
