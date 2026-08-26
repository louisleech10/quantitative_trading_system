/**
 * GAP-3 B5.2（W9）：新契約匯入表單——拒收顯示後端逐列 reason 與 migration 提示（前端不重做檢查）；
 * 接受顯示 import_id；/search 匯出組裝器產契約形狀記錄（t0 ms、label、label_definition）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EventImportForm from '@/components/case/EventImportForm';
import { EventImportRejectedError } from '@/lib/api';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { buildEventContractRecords, inferDirection, toEpochMs } from '@/lib/eventExport';
import { sha256Hex } from '@/lib/ruleDigest';
import type { CaseData } from '@/lib/types';

/**
 * GAP-3 UX Task 1.3：`source_file_text`／`source_file_digest` **一律由後端提供**
 * （`SearchResultData` 之兩鍵），前端不得自算 ⇒ 測試以固定的「後端回應」餵入。
 * 覆蓋面與位元組相等之驗收在 `src/lib/canonicalSourceCoverage.test.ts`。
 */
const BACKEND_SOURCE_TEXT = '[{"close":1.0,"symbol":"ETHUSDT"}]';
const BACKEND_SOURCE = {
  sourceFileText: BACKEND_SOURCE_TEXT,
  sourceFileDigest: createHash('sha256').update(BACKEND_SOURCE_TEXT, 'utf8').digest('hex'),
  // 🔴 Task 4.1 ③／R1 `CODEX-R1-P1-02`：深度宣告 map 為**必填**——缺該列 tf 之鍵會拋錯，
  //    不再靜默 floor 成 1（那個 1 會冒充成「深度 0」）。本檔 fixture 皆為 12h。
  lookaheadBarsDeclared: { '12h': 0 },
};

const uploadMock = vi.fn();
vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, uploadEventImport: (...a: unknown[]) => uploadMock(...a) };
});

afterEach(() => {
  cleanup();
  uploadMock.mockReset();
});

function pickFile() {
  const input = screen.getByTestId('event-import-file') as HTMLInputElement;
  const file = new File(['event_id,t0\n'], 'ev.csv', { type: 'text/csv' });
  fireEvent.change(input, { target: { files: [file] } });
}

describe('GAP-3 事件匯入表單', () => {
  it('契約違規 ⇒ 逐列 reason 表格＋migration 提示', async () => {
    uploadMock.mockRejectedValueOnce(new EventImportRejectedError(422, {
      kind: 'contract_violation',
      message: '2 筆契約違規',
      failures: [
        { row: 0, event_id: 'e0', field: 'label_definition', reason: 'missing_required_field' },
        { row: 1, event_id: 'e1', field: 't0', reason: 'invalid_timestamp_unit' },
      ],
      migration_hint: { endpoint: '/api/v1/case/import-events', required_fields_absent: ['label_definition'] },
    }));
    render(<EventImportForm />);
    pickFile();
    fireEvent.click(screen.getByTestId('event-import-submit'));
    await waitFor(() => expect(screen.getByTestId('event-import-rejected')).toBeTruthy());
    const rows = screen.getAllByTestId('event-import-failure-row');
    expect(rows.length).toBe(2);
    expect(rows[1].textContent).toContain('invalid_timestamp_unit');
    expect(screen.getByTestId('event-import-rejected').textContent).toContain('required_fields_absent');
  });

  it('舊三欄 ⇒ legacy_schema_detected 訊息', async () => {
    uploadMock.mockRejectedValueOnce(new EventImportRejectedError(400, {
      kind: 'legacy_schema_detected', message: '偵測到舊三欄格式', failures: [], migration_hint: { endpoint: '/api/v1/case/import-events' },
    }));
    render(<EventImportForm />);
    pickFile();
    fireEvent.click(screen.getByTestId('event-import-submit'));
    await waitFor(() => expect(screen.getByTestId('event-import-rejected').textContent).toContain('legacy_schema_detected'));
  });

  it('接受 ⇒ 顯示 import_id 並回呼 onImported', async () => {
    uploadMock.mockResolvedValueOnce({
      accepted: true, import_id: 'imp-9', n_rows: 3, n_valid: 3, failures: [], warnings: [],
      upload_sha256: 'a'.repeat(64), source_digest_verified: false, contract_version: '1.0', stored_path: '/x/imp-9.json',
    });
    const onImported = vi.fn();
    render(<EventImportForm onImported={onImported} />);
    pickFile();
    fireEvent.click(screen.getByTestId('event-import-submit'));
    await waitFor(() => expect(screen.getByTestId('event-import-result').textContent).toContain('imp-9'));
    expect(onImported).toHaveBeenCalledTimes(1);
  });
});

describe('GAP-3 /search 匯出組裝器', () => {
  it('t0 為 ms（秒級自動 ×1000、ISO 可解）；label 取正反例；缺標記者列 skipped', async () => {
    const cases = [
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704067200', positive_case: 1 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '2024-01-01 12:00:00', positive_case: false },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: 'n/a', positive_case: 1 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704153600', positive_case: undefined },
    ] as unknown as CaseData[];
    const out = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [{ parameter: 'price_change', operator: '>=', value: 0.05 }], priceChangeMethod: 'close_to_close', ...BACKEND_SOURCE });
    expect(out.n_records).toBe(2);
    // 整列被剔除者（附帶欄缺值只是不寫該欄、列仍保留——見 `missing_by_horizon`）
    expect(out.skipped.map((s) => s.reason))
      .toEqual(['unparseable_timestamp', 'missing_positive_case_flag']);
    const r0 = out.records[0];
    expect(r0.t0).toBe(1704067200000);
    expect(r0.label).toBe(1);
    expect(out.records[1].t0).toBe(Date.parse('2024-01-01T12:00:00Z'));
    expect(out.records[1].label).toBe(0);
    // 🔴 Task 4.1 ③：`horizon_bars` 由該列 tf 之宣告深度導出（下限 1）。
    //    本例未傳 `lookaheadBarsDeclared` ⇒ 深度視為 0 ⇒ floor 後為 1（**不是**舊的預設 2）。
    expect(r0.label_definition.window.horizon_bars).toBe(1);
    expect(r0.label_definition.canonical_digest).toHaveLength(64);
    expect(r0.source_file_digest).toHaveLength(64);
    expect(r0.control_kind).toBe('user_labeled_same_trigger');
    expect(r0.direction).toBe('long');
  });

  it('GAP-3 UX Task 1.3：source_file_digest 沿用**後端**提供之值（前端不自算）；rule_digest 仍為真 SHA-256', async () => {
    const cases = [
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704067200', positive_case: 1, price_change: 0.052 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704110400', positive_case: 0, price_change: -0.011 },
    ] as unknown as CaseData[];
    const out = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [], priceChangeMethod: 'close_to_close', ...BACKEND_SOURCE });
    expect(out.source_file_digest).toBe(BACKEND_SOURCE.sourceFileDigest);
    expect(out.records.every((r) => r.source_file_digest === BACKEND_SOURCE.sourceFileDigest)).toBe(true);
    // rule_digest（綁 search_rule_summary）與 source_file_digest 是兩件事；前者仍由前端算，且是真 SHA-256
    expect(await sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    expect(out.records[0].label_definition.canonical_digest).toHaveLength(64);
    // CODEX-R2-P1-03：companion 來源檔內容即 source_file_text，其 sha256 === source_file_digest（匯入可 verify）
    expect(out.source_file_text).toBe(BACKEND_SOURCE_TEXT);
    expect(createHash('sha256').update(out.source_file_text, 'utf8').digest('hex')).toBe(out.source_file_digest);
    expect(out.verify_note).toContain('source_file');
    // 後端沒給 ⇒ fail-closed（不得退回前端自算、不得寫空值）
    await expect(buildEventContractRecords(cases, {
      timeframe: '12h', conditions: [], priceChangeMethod: 'x',
      sourceFileText: BACKEND_SOURCE_TEXT, sourceFileDigest: '',
      lookaheadBarsDeclared: { '12h': 0 },   // R2 `CODEX-R2-P2-03`：必填欄，漏傳只有 tsc 看得到
    })).rejects.toThrow(/前端不得自算/);
    // 覆蓋面（刪／改名／改值任一 future_* 欄 ⇒ digest 改變）由後端 golden 驅動，見 canonicalSourceCoverage.test.ts
  });

  it('🔴 Task 4.1 ②（覆蓋 CODEX-R2-P1-02）：匯出端**不再寫 `label_value`**——答案窗已移到 IC 分析層', async () => {
    // 歷史：本條原本驗「`label_value` 取同 horizon 之 `future_Nbar_return`、short 取負」。
    // R8 依 §D-3′ 撤回主答案窗 ⇒ 匯出端不再有答案窗這件事，`label_value` 於**分析時**才由後端算。
    // 這條保留下來當**回歸**：任何形式的 `label_value`（含 null／0／改名新欄）都不得回到匯出檔。
    const cases = [
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704067200', positive_case: 1, price_change: 0.052, future_2bar_return: 0.031, future_4bar_return: 0.077 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704110400', positive_case: 0, price_change: -0.011 },
    ] as unknown as CaseData[];
    const out = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [], priceChangeMethod: 'x', ...BACKEND_SOURCE });
    // **逐列**驗（不是只看第一列）
    for (const r of out.records) expect('label_value' in r).toBe(false);
    // 附帶欄照樣帶（原值，不因 direction 取負——附帶欄沒有 label 語意）
    // 🔴 附帶欄是動態鍵（`...attachedColumns`）⇒ 推導型別看不到它們，取值須經 Record 視角。
    const cols = (r: (typeof out.records)[number]) => r as unknown as Record<string, number>;
    expect(cols(out.records[0]).future_2bar_return).toBe(0.031);
    expect(cols(out.records[0]).future_4bar_return).toBe(0.077);
    const short = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [{ parameter: 'price_change', operator: '<=', value: -0.03 }], priceChangeMethod: 'x', ...BACKEND_SOURCE });
    expect(short.records[0].direction).toBe('short');
    expect(cols(short.records[0]).future_2bar_return).toBe(0.031);       // short 也不取負
    for (const r of short.records) expect('label_value' in r).toBe(false);
    // 缺附帶欄 ⇒ 逐 horizon 計數（Task 4.3），**不**再走 skipped
    expect(out.missing_by_horizon[2]).toBe(1);
    expect(out.skipped).toEqual([]);
  });

  it('方向推斷：price_change <= 或負值 ⇒ short；toEpochMs 邊界', () => {
    expect(inferDirection([{ parameter: 'price_change', operator: '<=', value: -0.03 }])).toBe('short');
    expect(inferDirection([{ parameter: 'price_change', operator: '>=', value: 0.03 }])).toBe('long');
    expect(toEpochMs(1704067200)).toBe(1704067200000);
    expect(toEpochMs(1704067200000)).toBe(1704067200000);
    expect(toEpochMs('')).toBeNull();
  });
});

describe('GAP-3 /search 匯出頁面接線（B7 改形後）', () => {
  it('附帶欄多選、缺附帶欄先提示、同時下載來源檔；主答案窗已不存在', () => {
    const src = readFileSync(resolve(__dirname, '../../app/search/page.tsx'), 'utf-8');
    // 🔴 Task 4.1 ②：主答案窗之 select 與其傳參皆已移除
    expect(src).not.toContain('export-gap3-horizon');
    expect(src).not.toContain('horizonBars: eventHorizonBars');
    expect(src).toContain('export-attached-columns');                   // 附帶欄多選
    expect(src).toContain('attachedHorizons,');                         // 傳入匯出器
    expect(src).toContain('lookaheadBarsDeclared: lowerBoundState.depthByTimeframe');
    // Task 4.3 ＋ 5.3：**同一個**確認框之訊息組裝（5.3 擴寫後改由 `horizonCoverageLines` 產行）
    // 🔴 行為本身由 `exportMissingColumnDialog`／`exportHorizonCoverageDialog` 之執行期測試守住；
    //    此處只是頁面接線 smoke，錨點跟著實際呼叫走。
    expect(src).toContain('horizonCoverageLines(payload)');
    expect(src).toContain('.source.json');                              // companion 來源檔
    expect(src).toContain('payload.source_file_text');
  });
});
