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
  exportAllowedUnderBound,
  horizonOptions,
  isUsableCondition,
  nextLowerBoundState,
  numericColumnsOf,
  referencedColumnsOf,
  rowPassesCondition,
  UNCONSTRAINED_LOWER_BOUND,
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

  it('⑩ 下界狀態機（`D-002 A-004` 之決策本體）：四種情形之 status 與 bound', () => {
    const resolved7: LowerBoundState = {
      status: 'resolved', depthByTimeframe: { '12h': 7 }, bound: 7, error: null,
    };

    // 沒有條件就沒有約束
    expect(nextLowerBoundState(resolved7, { kind: 'no-conditions' })).toEqual(UNCONSTRAINED_LOWER_BOUND);

    // 有條件、還沒拿到下界 ⇒ pending（不是「暫時沒有約束」）
    expect(nextLowerBoundState(UNCONSTRAINED_LOWER_BOUND, { kind: 'pending' }).status).toBe('pending');

    // 逐 tf 下界**相同**（含單一 tf）⇒ 可用單一答案窗表達
    expect(nextLowerBoundState(UNCONSTRAINED_LOWER_BOUND,
      { kind: 'resolved', depthByTimeframe: { '1h': 6, '12h': 6 } }))
      .toEqual({ status: 'resolved', depthByTimeframe: { '1h': 6, '12h': 6 }, bound: 6, error: null });

    // 🔴 逐 tf 下界**不同** ⇒ inexpressible，**不得**取 max 冒充 per-scope 下界
    const mixed = nextLowerBoundState(UNCONSTRAINED_LOWER_BOUND,
      { kind: 'resolved', depthByTimeframe: { '1h': 72, '12h': 6 } });
    expect(mixed.status).toBe('inexpressible');
    expect(mixed.bound).toBe(null);                       // 不是 72
    expect(mixed.depthByTimeframe).toEqual({ '1h': 72, '12h': 6 });   // map 保留，不塌平
    expect(mixed.error).toContain('1h=72');

    // 🔴 算不出下界 ⇒ error，且 map 與 bound 沿用前值（但 status 已不是 resolved ⇒ 擋）
    const err = nextLowerBoundState(resolved7, { kind: 'error', message: 'boom' });
    expect(err).toEqual({ status: 'error', depthByTimeframe: { '12h': 7 }, bound: 7, error: 'boom' });
  });

  it('⑪ 🔴 系統無法證明安全時不得放行：只有 unconstrained 與 resolved 且達標才可匯出', () => {
    expect(exportAllowedUnderBound(UNCONSTRAINED_LOWER_BOUND, 1)).toBe(true);

    const resolved7: LowerBoundState = {
      status: 'resolved', depthByTimeframe: { '12h': 7 }, bound: 7, error: null,
    };
    expect(exportAllowedUnderBound(resolved7, 6)).toBe(false);
    expect(exportAllowedUnderBound(resolved7, 7)).toBe(true);
    expect(exportAllowedUnderBound(resolved7, 12)).toBe(true);

    // ⚠️ 這三種之 bound 都是 null——舊版只看 bound 就會把它們讀成「沒有約束」而放行
    for (const status of ['pending', 'error', 'inexpressible'] as const) {
      expect(exportAllowedUnderBound(
        { status, depthByTimeframe: {}, bound: null, error: 'x' }, 12)).toBe(false);
    }
  });

  it('⑫ 下界大於固定清單上限時，至少要有一個可選值滿足它（不得所有選項都被鎖）', () => {
    const base = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    expect(horizonOptions(UNCONSTRAINED_LOWER_BOUND, base)).toEqual(base);

    const bound72: LowerBoundState = {
      status: 'resolved', depthByTimeframe: { '1h': 72 }, bound: 72, error: null,
    };
    const opts = horizonOptions(bound72, base);
    expect(opts).toContain(72);
    expect(opts.some((h) => h >= 72)).toBe(true);
    expect(opts).toEqual([...base, 72]);                 // 只多那一個，不亂加

    // pending／error 不得偷偷加選項（那會讓使用者以為有可選的合法值）
    expect(horizonOptions({ status: 'pending', depthByTimeframe: {}, bound: null, error: null }, base))
      .toEqual(base);
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
