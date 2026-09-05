/**
 * `G3-D2` **Task D3.1** 驗收（`--run twoStageExport`）。
 *
 * 覆蓋 SPEC D-001 D3.1 之三件事：
 *   ① `/search` 之 `scenario` 解灰 `two_stage`（可選集合恰為 `{B, C, two_stage}`）；
 *   ② 兩段必填：一段 ⇒ 阻擋（`two_stage_requires_two_stages`），**不降級**為 A／B、
 *      也不靜默寫 `stage_count=1`；深度 0 ⇒ 阻擋（`scenario_depth_inconsistent`）；
 *   ③ 未標籤路徑：每列 **`label` 鍵缺席**（禁 `null`／`''`／`0`）、
 *      `label_origin === 'search_unlabeled'`、`search_rule_summary` 為兩段 digest 之 canonical JSON。
 *
 * 🔴 本檔測**真的** `buildEventContractRecords` 與 `twoStageExportBlockReason`，不是 mock。
 * 🔴 阻擋判定**只有一份**（`twoStageExportBlockReason`）：`buildEventContractRecords` 丟例外、
 *    `/search` 頁 disable 按鈕，兩邊呼叫同一支。本檔同時釘住「兩邊結論一致」。
 */
import { describe, expect, it, vi } from 'vitest';
import {
  buildEventContractRecords,
  EventExportBlocked,
  EVENT_EXPORT_LABEL_ORIGIN,
  EVENT_EXPORT_UNLABELED_LABEL_ORIGIN,
  twoStageExportBlockReason,
  twoStageRuleSummary,
  type EventExportOptions,
} from './eventExport';
import { selectable } from './eventDimensions';
import { ruleDigestOf, ruleSummaryText } from './ruleDigest';
import type { CaseData } from './types';

const STAGE_1 = [{ parameter: 'price_change', operator: '>=', value: 3 }];
const STAGE_2 = [{ parameter: 'price_change', operator: '<=', value: -3 }];

function caseRow(over: Record<string, unknown> = {}): CaseData {
  return {
    symbol: 'ETHUSDT',
    timeframe: '1h',
    timestamp: '2024-01-01 00:00:00',
    positive_case: true,
    price_change: 3.2,
    ...over,
  } as unknown as CaseData;
}

function opts(over: Partial<EventExportOptions> = {}): EventExportOptions {
  return {
    timeframe: '1h',
    conditions: STAGE_1,
    priceChangeMethod: 'close_to_close',
    attachedHorizons: [],
    lookaheadBarsDeclared: { '1h': 2 },
    sourceFileText: '[]',
    sourceFileDigest: 'a'.repeat(64),
    ...over,
  };
}

/** two_stage 之合法 opts（兩段＋深度 2）。 */
function twoStageOpts(over: Partial<EventExportOptions> = {}): EventExportOptions {
  return opts({ scenario: 'two_stage', stageConditions: [STAGE_1, STAGE_2], ...over });
}

// ───────── ① scenario 解灰 ─────────

describe('D3.1 ① — /search 之 scenario 解灰 two_stage', () => {
  it('🔴 可選集合**恰為** {B, C, two_stage}（集合相等，不是 contains）', () => {
    expect(new Set(selectable('/search', 'scenario'))).toEqual(new Set(['B', 'C', 'two_stage']));
  });

  it('🔴 over 向：`A` 仍不可選（否則「全部解灰」也會讓上一條綠）', () => {
    expect(selectable('/search', 'scenario')).not.toContain('A');
  });
});

// ───────── ② 兩道阻擋 ─────────

describe('D3.1 ② — 兩段必填與深度 ≥1 之前端阻擋', () => {
  it('🔴 一段 ⇒ 阻擋 `two_stage_requires_two_stages`，且**不產出任何 record**', async () => {
    // 🔴 R1 `CODEX-R1-P1-02`／`GROK-R1-P2-01`：原本寫 `vi.spyOn(globalThis, 'fetch' as never)`，
    //    回傳型別被推成 `never` ⇒ `.mockRestore()` 為 `TS2339`，使 `tsc` 由 8 增為 9。
    //    改為裝一個 `vi.fn()` 並在 `finally` 還原——不需要 `as never`，型別乾淨。
    const realFetch = globalThis.fetch;
    const fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof globalThis.fetch;
    try {
      await expect(buildEventContractRecords([caseRow()], twoStageOpts({ stageConditions: [STAGE_1] })))
        .rejects.toBeInstanceOf(EventExportBlocked);
      // SPEC D3.1：`fetch` call count === 0（匯出是純前端組裝，阻擋時更不該有任何請求）
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      globalThis.fetch = realFetch;
    }
  });

  it('🔴 一段之理由字串含代號，且**不得**降級為 A／B（訊息不提「已改用」之類）', async () => {
    const err = await buildEventContractRecords([caseRow()], twoStageOpts({ stageConditions: [STAGE_1] }))
      .then(() => null, (e: unknown) => e as EventExportBlocked);
    expect(err).toBeInstanceOf(EventExportBlocked);
    expect(err!.reason).toBe('two_stage_requires_two_stages');
    expect(err!.message).toContain('two_stage_requires_two_stages');
    // 邊界③：不得靜默降級。訊息要求使用者自己選，不能宣稱系統已代為改成別的情境。
    expect(err!.message).toContain('系統不會替你把它當成單段情境送出');
  });

  it('🔴 零段（未傳 `stageConditions`）亦阻擋——undefined 不等於「不必檢查」', async () => {
    await expect(buildEventContractRecords([caseRow()], opts({ scenario: 'two_stage' })))
      .rejects.toMatchObject({ reason: 'two_stage_requires_two_stages' });
  });

  it('🔴 三段亦阻擋（`!== 2` 不是 `< 2`）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      stageConditions: [STAGE_1, STAGE_2, STAGE_1],
    }))).rejects.toMatchObject({ reason: 'two_stage_requires_two_stages' });
  });

  it('🔴 深度全 0 ⇒ 阻擋 `scenario_depth_inconsistent`（與匯入端同名 reason）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': 0, '12h': 0 },
    }))).rejects.toMatchObject({ reason: 'scenario_depth_inconsistent' });
  });

  it('🔴 只要**任一** tf 深度 ≥1 即放行（不是要求全部 ≥1）', async () => {
    const out = await buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': 0, '12h': 1 },
    }));
    expect(out.records).toHaveLength(1);
  });

  it('🔴 over 向：兩道阻擋**只對 two_stage 生效**——B 批一段且深度 0 仍可匯出', async () => {
    const out = await buildEventContractRecords([caseRow()], opts({
      scenario: 'B', lookaheadBarsDeclared: { '1h': 0 },
    }));
    expect(out.records).toHaveLength(1);
    expect(twoStageExportBlockReason({ scenario: 'B', lookaheadBarsDeclared: { '1h': 0 } }))
      .toBeUndefined();
  });

  it('🔴 頁面 disable 與函式丟例外**用同一份判定**：兩者結論逐條相同', async () => {
    const cases: Partial<EventExportOptions>[] = [
      { stageConditions: [STAGE_1] },
      { stageConditions: [STAGE_1, STAGE_2, STAGE_1] },
      { lookaheadBarsDeclared: { '1h': 0 } },
      {},   // 合法
    ];
    for (const over of cases) {
      const o = twoStageOpts(over);
      const predicted = twoStageExportBlockReason({
        scenario: o.scenario,
        stageConditions: o.stageConditions,
        lookaheadBarsDeclared: o.lookaheadBarsDeclared,
      });
      const actual = await buildEventContractRecords([caseRow()], o)
        .then(() => undefined, (e: unknown) => (e as EventExportBlocked).reason);
      expect(actual).toBe(predicted?.reason);
    }
  });
});

// ───────── ③ 未標籤路徑 ─────────

describe('D3.1 ③ — two_stage 之未標籤匯出路徑', () => {
  it('🔴 每列 `label` **鍵缺席**（不是 null、不是 ""、不是 0）', async () => {
    const out = await buildEventContractRecords([caseRow(), caseRow({ positive_case: false })], twoStageOpts());
    expect(out.records).toHaveLength(2);
    for (const r of out.records as Record<string, unknown>[]) {
      expect('label' in r).toBe(false);
      // 逐一排除三種「看起來有值」的假缺席
      expect(r.label).toBeUndefined();
    }
  });

  it('🔴 `label_origin === search_unlabeled`（契約 not_importable ⇒ 直接匯入必拒）', async () => {
    const out = await buildEventContractRecords([caseRow()], twoStageOpts());
    const r = out.records[0] as Record<string, unknown>;
    expect(r.label_origin).toBe(EVENT_EXPORT_UNLABELED_LABEL_ORIGIN);
    expect(r.label_origin).toBe('search_unlabeled');
    // 🔴 over 向：非 two_stage 仍是 `search_positive_case`（否則「一律改成 unlabeled」也會綠）
    const b = await buildEventContractRecords([caseRow()], opts({ scenario: 'B' }));
    expect((b.records[0] as Record<string, unknown>).label_origin).toBe(EVENT_EXPORT_LABEL_ORIGIN);
  });

  it('🔴 未標記之列**照樣落檔**（two_stage 強制 includeUnlabeled，使用者關不掉）', async () => {
    const out = await buildEventContractRecords(
      [caseRow({ positive_case: null })],
      twoStageOpts({ includeUnlabeled: false }),   // 刻意關掉
    );
    expect(out.records).toHaveLength(1);
    expect('label' in (out.records[0] as Record<string, unknown>)).toBe(false);
  });

  it('🔴 `search_rule_summary` ＝ 兩段 digest 之 canonical JSON（形狀逐字對證契約）', async () => {
    const out = await buildEventContractRecords([caseRow()], twoStageOpts());
    const summary = (out.records[0] as Record<string, unknown>).search_rule_summary as string;
    const d1 = await ruleDigestOf(ruleSummaryText(STAGE_1, 'close_to_close', '1h'));
    const d2 = await ruleDigestOf(ruleSummaryText(STAGE_2, 'close_to_close', '1h'));
    expect(summary).toBe(twoStageRuleSummary([d1, d2]));
    // 形狀：鍵序 stage_count→stages、無空白、stage_count 恆 2
    expect(summary).toBe(`{"stage_count":2,"stages":["${d1}","${d2}"]}`);
    expect(JSON.parse(summary)).toEqual({ stage_count: 2, stages: [d1, d2] });
    // 🔴 兩段順序有意義：第一段在前。對調 ⇒ 不同字串（否則「順序無所謂」的實作也會綠）
    expect(summary).not.toBe(twoStageRuleSummary([d2, d1]));
  });

  it('🔴 over 向：非 two_stage 之 `search_rule_summary` 維持**單段摘要**、無 `stage_count` 形狀', async () => {
    // 🔴 注意：單段摘要本身也是 JSON（`ruleSummaryText` 就是 `JSON.stringify`），
    //    所以「開頭是不是 `{`」**不能**當區別（本條第一版就是這樣寫而紅——我的假設錯，不是碼錯）。
    //    真正的區別是**鍵集**：單段為 `{conditions, price_change_method, timeframe}`，
    //    兩段式為 `{stage_count, stages}`。
    const out = await buildEventContractRecords([caseRow()], opts({ scenario: 'B' }));
    const summary = (out.records[0] as Record<string, unknown>).search_rule_summary as string;
    expect(summary).toBe(ruleSummaryText(STAGE_1, 'close_to_close', '1h'));
    expect(Object.keys(JSON.parse(summary))).not.toContain('stage_count');
    expect(Object.keys(JSON.parse(summary))).not.toContain('stages');
  });

  it('🔴 `scenario` 仍忠實落為 `two_stage`（不因走未標籤路徑而被改寫）', async () => {
    const out = await buildEventContractRecords([caseRow()], twoStageOpts());
    expect((out.records[0] as Record<string, unknown>).scenario).toBe('two_stage');
  });
});

// ───────── R1 閉合輪：三家 findings 之負向測試 ─────────

describe('D3.1 R1 閉合 — 群集 A：CSV header 由契約導出，未標籤批仍有 label 欄', () => {
  it('🔴 two_stage 之 CSV **必須**有 `label` 欄（空值），否則補標主路徑斷掉', async () => {
    const { buildEventContractCsv } = await import('./eventContractCsv');
    const out = await buildEventContractRecords([caseRow()], twoStageOpts());
    const csv = buildEventContractCsv(out.records as Record<string, unknown>[], []);
    const header = csv.split('\n')[0].split(',');
    // 三家全員命中：修正前 header 為
    // `direction,event_id,label_origin,scenario,search_rule_summary,symbol,t0,timeframe`（無 label）
    expect(header).toContain('label');
    // 該欄之值為空（不是 0／不是 "null"）——使用者要在 Excel 自己填
    const cells = csv.split('\n')[1].split(',');
    expect(cells[header.indexOf('label')]).toBe('');
  });

  it('🔴 over 向：非 two_stage 之 `label` 欄仍帶實際值（不得因保留欄而一律清空）', async () => {
    const { buildEventContractCsv } = await import('./eventContractCsv');
    const out = await buildEventContractRecords([caseRow()], opts({ scenario: 'B' }));
    const csv = buildEventContractCsv(out.records as Record<string, unknown>[], []);
    const header = csv.split('\n')[0].split(',');
    expect(csv.split('\n')[1].split(',')[header.indexOf('label')]).toBe('1');
  });

  it('🔴 保留欄由**契約**導出，不是人工清單', async () => {
    // 🔴 **本條第一版是假的**（mutation `a2_reserved_hardcoded` 首跑 GREEN）：
    //    當時只寫「遍歷 `RESERVED_SCALAR_CONTRACT_COLUMNS`，檢查 header 都有」——
    //    把該常數手刻成 `['label']` 時，遍歷一個元素、header 也真的有它 ⇒ 照樣綠。
    //    **一條宣稱「證明 X 來自 Y」的測試，若 X 在兩種來源下都能滿足斷言，它什麼也沒證明**
    //    （這條判準是 B-D1 R6 寫下的，我在本批又犯了一次）。
    //    ⇒ 改為與**真契約**逐鍵集合相等：手刻清單少了其他必填純量欄，當場不等。
    const { buildEventContractCsv, RESERVED_SCALAR_CONTRACT_COLUMNS } = await import('./eventContractCsv');
    const contract = (await import('../../../momentum/Analysis/contracts/event_import_contract.json')).default as {
      required_fields: Record<string, { type?: string }>;
    };
    const expected = Object.entries(contract.required_fields)
      .filter(([, spec]) => spec.type !== undefined && spec.type !== 'object')
      .map(([name]) => name)
      .sort();
    expect([...RESERVED_SCALAR_CONTRACT_COLUMNS]).toEqual(expected);
    // 前提：契約之必填純量欄**不只一個**（否則「集合相等」與「只有 label」無從區分）
    expect(expected.length).toBeGreaterThan(1);
    expect(expected).toContain('label');

    const out = await buildEventContractRecords([caseRow()], twoStageOpts());
    const header = new Set(buildEventContractCsv(out.records as Record<string, unknown>[], []).split('\n')[0].split(','));
    for (const name of expected) expect(header.has(name)).toBe(true);
    // 物件型必填欄**不得**以容器名出現（它們走點路徑攤平）
    expect(RESERVED_SCALAR_CONTRACT_COLUMNS).not.toContain('label_definition');
    expect(RESERVED_SCALAR_CONTRACT_COLUMNS).not.toContain('lookahead_bars_declared');
  });
});

describe('D3.1 R1 閉合 — 群集 C：空段與不合法深度', () => {
  it('🔴 第二段為空 ⇒ 阻擋（修正前：長度是 2 就放行，第二段成空殼）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      stageConditions: [STAGE_1, []],
    }))).rejects.toMatchObject({ reason: 'two_stage_requires_two_stages' });
  });

  it('🔴 第一段為空亦阻擋，且訊息指出是**第 1 段**（不是含糊說「有段是空的」）', async () => {
    const err = await buildEventContractRecords([caseRow()], twoStageOpts({
      stageConditions: [[], STAGE_2],
    })).then(() => null, (e: unknown) => e as EventExportBlocked);
    expect(err!.reason).toBe('two_stage_requires_two_stages');
    expect(err!.message).toContain('第 1 段');
  });

  it('🔴 兩段皆空亦阻擋', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      stageConditions: [[], []],
    }))).rejects.toMatchObject({ reason: 'two_stage_requires_two_stages' });
  });

  it('🔴 深度負值 ⇒ `invalid_lookahead_declaration`（不得被 `Number(v) || 0` 當成 0）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': -1 },
    }))).rejects.toMatchObject({ reason: 'invalid_lookahead_declaration' });
  });

  it('🔴 深度非數字 ⇒ 亦為 `invalid_lookahead_declaration`，非 `scenario_depth_inconsistent`', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': 'abc' as unknown as number },
    }))).rejects.toMatchObject({ reason: 'invalid_lookahead_declaration' });
  });

  it('🔴 深度為小數 ⇒ 亦不合法（契約為 int）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': 1.5 },
    }))).rejects.toMatchObject({ reason: 'invalid_lookahead_declaration' });
  });

  it('🔴 over 向：合法深度 0 仍回 `scenario_depth_inconsistent`（兩種錯要分得開）', async () => {
    await expect(buildEventContractRecords([caseRow()], twoStageOpts({
      lookaheadBarsDeclared: { '1h': 0 },
    }))).rejects.toMatchObject({ reason: 'scenario_depth_inconsistent' });
  });
});

describe('D3.1 R1 閉合 — 群集 D：twoStageRuleSummary 公開入口自證恰兩段', () => {
  it('🔴 一段 ⇒ 丟例外（修正前：直呼可產出 stage_count:1，與契約寫死的 2 漂移）', () => {
    expect(() => twoStageRuleSummary(['a'.repeat(64)])).toThrow(EventExportBlocked);
  });

  it('🔴 三段 ⇒ 丟例外', () => {
    expect(() => twoStageRuleSummary(['a'.repeat(64), 'b'.repeat(64), 'c'.repeat(64)]))
      .toThrow(EventExportBlocked);
  });

  it('🔴 over 向：恰兩段仍正常產出，且 `stage_count` 為 2', () => {
    const s = twoStageRuleSummary(['a'.repeat(64), 'b'.repeat(64)]);
    expect(JSON.parse(s).stage_count).toBe(2);
  });
});

describe('D3.1 R1 閉合 — R-LABEL-SOT：label_origin 之字面由契約導出', () => {
  it('🔴 `search_unlabeled` 在契約 enum 內且屬 `not_importable`（不是前端自己編的字）', async () => {
    const contract = (await import('../../../momentum/Analysis/contracts/event_import_contract.json')).default as {
      optional_fields: { label_origin: { enum: string[]; not_importable: string[] } };
    };
    expect(contract.optional_fields.label_origin.enum).toContain(EVENT_EXPORT_UNLABELED_LABEL_ORIGIN);
    expect(contract.optional_fields.label_origin.not_importable).toContain(EVENT_EXPORT_UNLABELED_LABEL_ORIGIN);
    // over 向：一般匯出用的那個值**不在** not_importable（否則正常路徑也匯不進去）
    expect(contract.optional_fields.label_origin.not_importable).not.toContain(EVENT_EXPORT_LABEL_ORIGIN);
  });
});
