/**
 * GAP-3 UX **Task 7.0** 驗收（`--run eventExportOptions`；SPEC L2321–2346 之①–⑤／⑦／⑧）。
 *
 * 🔴 **本檔測的是真的 `buildEventContractRecords`**，不是 mock：Task 7.0 的交付就是
 *    「五維度由寫死改為 `opts.X ?? <常數>`」，錨點若不落在該函式本體，
 *    mutation 會錄到空紅集合（§4.2 假綠形態 6）。
 *
 * 🔴 **本檔刻意不驗 UI**：Task 7.0 的邊界是「只做型別與參數化，不加 UI」。
 *    「可操作選項集合 == selectable(path,dim)」是 **Task 7.2** 的三層閘，
 *    在這裡先寫一份會變成第二份副本（TODO 7.2「不可做」明禁人工清單）。
 *
 * 🔴 **`label_return_mode` 一律斷言巢狀路徑**（`records[0].label_definition.label_return_mode`）。
 *    寫成頂層會讓契約 schema 檢核通過而語意落在錯的物件——那正是 SPEC「不可做」列的那條。
 */
import { describe, expect, it } from 'vitest';
import {
  buildEventContractRecords,
  EVENT_EXPORT_CONTROL_KIND,
  EVENT_EXPORT_DECISION_OFFSET_BARS,
  EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
  EVENT_EXPORT_LABEL_RETURN_MODE,
  EVENT_EXPORT_SCENARIO,
  type EventExportOptions,
} from './eventExport';
import type { CaseData } from './types';

function caseRow(over: Record<string, unknown> = {}): CaseData {
  return {
    symbol: 'ETHUSDT',
    timeframe: '1h',
    timestamp: '2024-01-01 00:00:00',
    positive_case: true,
    price_change: 3.2,
    future_1bar_return: 0.01,
    ...over,
  } as unknown as CaseData;
}

/** 只帶**必填**欄的 opts：五個批次維度一個都不傳（＝現行 `/search` caller 的實況）。 */
function baseOpts(over: Partial<EventExportOptions> = {}): EventExportOptions {
  return {
    timeframe: '1h',
    conditions: [{ parameter: 'price_change', operator: '>=', value: 3 }],
    priceChangeMethod: 'close_to_close',
    attachedHorizons: [1],
    lookaheadBarsDeclared: { '1h': 2 },
    sourceFileText: '[]',
    sourceFileDigest: 'a'.repeat(64),
    ...over,
  };
}

async function firstRecord(over: Partial<EventExportOptions> = {}) {
  const out = await buildEventContractRecords([caseRow()], baseOpts(over));
  expect(out.records).toHaveLength(1);
  return out.records[0] as Record<string, unknown> & {
    label_definition: Record<string, unknown>;
  };
}

describe('Task 7.0 — EventExportOptions 五維度參數化（①–⑤：傳非預設值 ⇒ 落檔忠實等於所傳值）', () => {
  it('① `scenario`：傳非預設 `two_stage` ⇒ 頂層 `scenario` === 所傳值', async () => {
    const r = await firstRecord({ scenario: 'two_stage' });
    expect(r.scenario).toBe('two_stage');
    // 反向對照：不傳時才是預設。同一條裡驗兩向，避免「恆等於所傳值」被恆真實作騙過。
    expect(r.scenario).not.toBe(EVENT_EXPORT_SCENARIO);
  });

  it('② `controlKind`：傳非預設 `platform_same_trigger_rule` ⇒ 頂層 `control_kind` === 所傳值', async () => {
    const r = await firstRecord({ controlKind: 'platform_same_trigger_rule' });
    expect(r.control_kind).toBe('platform_same_trigger_rule');
    expect(r.control_kind).not.toBe(EVENT_EXPORT_CONTROL_KIND);
  });

  it('③ `entryPriceSemantic`：傳非預設 `next_open` ⇒ 頂層 `entry_price_semantic` === 所傳值', async () => {
    const r = await firstRecord({ entryPriceSemantic: 'next_open' });
    expect(r.entry_price_semantic).toBe('next_open');
    expect(r.entry_price_semantic).not.toBe(EVENT_EXPORT_ENTRY_PRICE_SEMANTIC);
  });

  it('④ `labelReturnMode`：傳非預設 `open_to_horizon_close` ⇒ **巢狀** `label_definition.label_return_mode` === 所傳值，且**不得**出現在頂層', async () => {
    const r = await firstRecord({ labelReturnMode: 'open_to_horizon_close' });
    expect(r.label_definition.label_return_mode).toBe('open_to_horizon_close');
    expect(r.label_definition.label_return_mode).not.toBe(EVENT_EXPORT_LABEL_RETURN_MODE);
    // 🔴 寫錯位置（頂層）會使契約檢核過而語意落錯物件 ⇒ 明確釘住「頂層沒有這個鍵」。
    expect('label_return_mode' in r).toBe(false);
  });

  it('⑤ `decisionOffsetBars`：傳非預設 `3` ⇒ 頂層 `decision_offset_bars` === 3（非 enum 欄，型別為 number）', async () => {
    const r = await firstRecord({ decisionOffsetBars: 3 });
    expect(r.decision_offset_bars).toBe(3);
    expect(r.decision_offset_bars).not.toBe(EVENT_EXPORT_DECISION_OFFSET_BARS);
  });
});

describe('Task 7.0 ⑦ — 五維度全部不傳 ⇒ 值 === 預設；`counterexample_kind` 不出現', () => {
  it('⑦ 不傳任何維度 ⇒ 五欄為 `C`／`user_labeled_same_trigger`／**`trigger_close`**／`close_to_close`／`0`', async () => {
    const r = await firstRecord();
    // 🔴 斷言**字面**而非只比常數：常數與字面若一起被改掉，比常數的斷言會一起漂而全綠。
    expect(r.scenario).toBe('C');
    expect(r.control_kind).toBe('user_labeled_same_trigger');
    expect(r.entry_price_semantic).toBe('trigger_close');
    expect(r.label_definition.label_return_mode).toBe('close_to_close');
    expect(r.decision_offset_bars).toBe(0);
    // 常數本身也要對得上（防「常數改了但組裝端另寫一份字面」）。
    expect(r.scenario).toBe(EVENT_EXPORT_SCENARIO);
    expect(r.control_kind).toBe(EVENT_EXPORT_CONTROL_KIND);
    expect(r.entry_price_semantic).toBe(EVENT_EXPORT_ENTRY_PRICE_SEMANTIC);
    expect(r.label_definition.label_return_mode).toBe(EVENT_EXPORT_LABEL_RETURN_MODE);
    expect(r.decision_offset_bars).toBe(EVENT_EXPORT_DECISION_OFFSET_BARS);
  });

  it('⑦b `entry_price_semantic` 之預設已依 §F-3′ 由 `trigger_open` 改為 `trigger_close`（回歸；改回去須紅）', async () => {
    const r = await firstRecord();
    expect(r.entry_price_semantic).not.toBe('trigger_open');
  });

  it('⑦c `counterexample_kind` **不出現於輸出**（逐列選填欄，非批次維度；R5 群集 G）', async () => {
    const r = await firstRecord();
    expect('counterexample_kind' in r).toBe(false);
    // 連改名復活都擋：任何 `counterexample_kind*` 之鍵皆不得出現。
    expect(Object.keys(r).filter((k) => k.startsWith('counterexample_kind'))).toEqual([]);
  });
});

describe('Task 7.0 ⑧ — 非 F-1′ 三元組：匯出照常成功、無 `label_value`、宣告即事實', () => {
  it('⑧ 傳 `(trigger_open, open_to_close, k=2)`（非 F-1′）⇒ 匯出成功、逐列不含 `label_value`、宣告欄忠實等於所傳值', async () => {
    const out = await buildEventContractRecords(
      [caseRow(), caseRow({ timestamp: '2024-01-01 01:00:00' })],
      baseOpts({
        entryPriceSemantic: 'trigger_open',
        labelReturnMode: 'open_to_close',
        decisionOffsetBars: 2,
      }),
    );
    // 匯出**照常成功**——fail-closed 已隨 §D-3′ 移到分析層（§F-2′／Task 7.0b），不在匯出端擋。
    expect(out.records).toHaveLength(2);
    expect(out.n_records).toBe(2);
    for (const row of out.records as Record<string, unknown>[]) {
      // 🔴 **逐列**驗，不是只看第一列；連改名／換形狀的復活都擋。
      expect('label_value' in row).toBe(false);
      expect(Object.keys(row).filter((k) => k.startsWith('label_value'))).toEqual([]);
      // 宣告即事實：三個宣告欄忠實等於所傳值，不因「不支援」而被偷改成支援值。
      expect(row.entry_price_semantic).toBe('trigger_open');
      expect(row.decision_offset_bars).toBe(2);
      expect((row.label_definition as Record<string, unknown>).label_return_mode).toBe('open_to_close');
    }
  });

  it('⑧b **over 向對照**：F-1′ 之三元組 `(trigger_close, close_to_close, k=0)` 同樣照常成功（證明⑧不是「因為不支援才成功」）', async () => {
    const out = await buildEventContractRecords(
      [caseRow()],
      baseOpts({
        entryPriceSemantic: 'trigger_close',
        labelReturnMode: 'close_to_close',
        decisionOffsetBars: 0,
      }),
    );
    expect(out.records).toHaveLength(1);
    expect('label_value' in (out.records[0] as Record<string, unknown>)).toBe(false);
  });
});
