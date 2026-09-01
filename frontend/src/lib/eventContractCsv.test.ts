/**
 * 可回灌 CSV 之前端驗收（`--run eventContractCsv`）。
 *
 * 🔴 後端另有 `tests/api/test_gap3_csv_roundtrip.py`，它**逐字重現本檔之規則**再打真的端點
 * ——兩邊是刻意的第二份實作：任一邊改了規則而另一邊沒跟，兩邊都會紅。
 * 本檔驗「產出的欄名與值對不對」，後端那檔驗「後端收不收」。
 */
import { describe, expect, it } from 'vitest';
import { buildEventContractCsv } from './eventContractCsv';

function rec(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    event_id: 'ETHUSDT:12h:1704067200000',
    symbol: 'ETHUSDT',
    timeframe: '12h',
    t0: 1704067200000,
    label: 1,
    direction: 'long',
    label_definition: {
      rule_id: 'r',
      window: { horizon_bars: 3 },
      label_return_mode: 'close_to_close',
    },
    lookahead_bars_declared: { '12h': 3 },
    ...over,
  };
}

const header = (csv: string) => csv.split('\n')[0].split(',');
const row = (csv: string, i = 1) => csv.split('\n')[i].split(',');

describe('可回灌 CSV — 欄名規則', () => {
  it('契約頂層欄用**契約欄名本身**（上傳時零對映）', () => {
    const h = header(buildEventContractCsv([rec()]));
    for (const name of ['event_id', 'symbol', 'timeframe', 't0', 'label', 'direction']) {
      expect(h, `缺契約欄 ${name}`).toContain(name);
    }
  });

  it('巢狀欄攤平成**點路徑**（後端 `_csv_rows_to_records` 據此還原）', () => {
    const h = header(buildEventContractCsv([rec()]));
    expect(h).toContain('label_definition.window.horizon_bars');
    expect(h).toContain('label_definition.label_return_mode');
    expect(h).not.toContain('label_definition');      // 不得留下未攤平的物件欄
  });

  it('🔴 答案只有 `label` 一欄——不得再寫 `Positive_Case`', () => {
    const h = header(buildEventContractCsv([rec()]));
    expect(h).toContain('label');
    expect(h.some((c) => /positive_case/i.test(c))).toBe(false);
  });

  it('非契約之分析欄一律放進 `meta.`，且排在契約欄之後', () => {
    const csv = buildEventContractCsv([rec()], [{ market_phase: 'bull', price_change: 0.031 }]);
    const h = header(csv);
    expect(h).toContain('meta.market_phase');
    expect(h).toContain('meta.price_change');
    // 契約欄在前、meta 在後
    const firstMeta = h.findIndex((c) => c.startsWith('meta.'));
    expect(h.slice(0, firstMeta).some((c) => c.startsWith('meta.'))).toBe(false);
    // 🔴 分析欄**不得**出現在頂層（那會被契約以 unknown_field 拒收）
    expect(h).not.toContain('market_phase');
  });
});

describe('可回灌 CSV — 值', () => {
  it('逐列對齊：第 i 列之 meta 來自第 i 個 extras，不跨列共用', () => {
    const csv = buildEventContractCsv(
      [rec({ event_id: 'a' }), rec({ event_id: 'b' })],
      [{ market_phase: 'bull' }, { market_phase: 'bear' }],
    );
    const h = header(csv);
    const mi = h.indexOf('meta.market_phase');
    expect(row(csv, 1)[mi]).toBe('bull');
    expect(row(csv, 2)[mi]).toBe('bear');
  });

  it('含逗號／引號之值要被正確引用（否則欄位會錯位）', () => {
    const csv = buildEventContractCsv([rec()], [{ note: 'a,b "c"' }]);
    expect(csv.split('\n')[1]).toContain('"a,b ""c"""');
    // 欄數不變（引用正確才不會被逗號切開）
    expect(row(csv, 1).length).toBeGreaterThanOrEqual(header(csv).length - 1);
  });

  it('陣列以 JSON 字面存放（解析端 `json.loads` 還原）', () => {
    const csv = buildEventContractCsv([rec({ some_list: [1, 2] })]);
    const h = header(csv);
    expect(h).toContain('some_list');
    expect(csv.split('\n')[1]).toContain('"[1,2]"');
  });

  it('空輸入 ⇒ 空字串（不產生只有標頭的假檔）', () => {
    expect(buildEventContractCsv([])).toBe('');
  });
});
