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
import { buildEventContractRecords, canonicalSourceText, inferDirection, sha256Hex, toEpochMs } from '@/lib/eventExport';
import type { CaseData } from '@/lib/types';

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
    const out = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [{ parameter: 'price_change', operator: '>=', value: 0.05 }], priceChangeMethod: 'close_to_close' });
    expect(out.n_records).toBe(2);
    // 整列被剔除者（label_value 缺欄只是不寫該欄、列仍保留）
    expect(out.skipped.filter((s) => !s.reason.includes('label_value_omitted')).map((s) => s.reason))
      .toEqual(['unparseable_timestamp', 'missing_positive_case_flag']);
    const r0 = out.records[0];
    expect(r0.t0).toBe(1704067200000);
    expect(r0.label).toBe(1);
    expect(out.records[1].t0).toBe(Date.parse('2024-01-01T12:00:00Z'));
    expect(out.records[1].label).toBe(0);
    expect(r0.label_definition.window.horizon_bars).toBe(2);
    expect(r0.label_definition.canonical_digest).toHaveLength(64);
    expect(r0.source_file_digest).toHaveLength(64);
    expect(r0.control_kind).toBe('user_labeled_same_trigger');
    expect(r0.direction).toBe('long');
  });

  it('CODEX-R1-P1-02：source_file_digest＝來源 canonical JSON 之真 SHA-256（對照 node:crypto）；無假 hash 退路', async () => {
    const cases = [
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704067200', positive_case: 1, price_change: 0.052 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704110400', positive_case: 0, price_change: -0.011 },
    ] as unknown as CaseData[];
    const out = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [], priceChangeMethod: 'close_to_close' });
    const expected = createHash('sha256').update(canonicalSourceText(cases)).digest('hex');
    expect(out.source_file_digest).toBe(expected);
    expect(out.records.every((r) => r.source_file_digest === expected)).toBe(true);
    expect(await sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    // CODEX-R2-P1-03：companion 來源檔內容即 source_file_text，其 sha256 === source_file_digest（匯入可 verify）
    expect(out.source_file_text).toBe(canonicalSourceText(cases));
    expect(createHash('sha256').update(out.source_file_text).digest('hex')).toBe(out.source_file_digest);
    expect(out.verify_note).toContain('source_file');
    // 改值 ⇒ digest 變
    const out2 = await buildEventContractRecords([{ ...cases[0], price_change: 0.06 }, cases[1]] as CaseData[], { timeframe: '12h', conditions: [], priceChangeMethod: 'x' });
    expect(out2.source_file_digest).not.toBe(expected);
  });

  it('CODEX-R2-P1-02：label_value＝同 horizon 之答案窗未來報酬（future_Nbar_return），非觸發根 price_change；short 取負；缺欄不寫並記 skipped', async () => {
    const cases = [
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704067200', positive_case: 1, price_change: 0.052, future_2bar_return: 0.031, future_4bar_return: 0.077 },
      { symbol: 'ETHUSDT', timeframe: '12h', timestamp: '1704110400', positive_case: 0, price_change: -0.011 },
    ] as unknown as CaseData[];
    const h2 = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [], priceChangeMethod: 'x' });
    expect(h2.records[0].label_value).toBe(0.031);                       // 非 price_change 0.052
    expect('label_value' in h2.records[1]).toBe(false);
    expect(h2.skipped.some((s) => s.reason.includes('future_2bar_return'))).toBe(true);
    expect(h2.label_value_source).toContain('future_2bar_return');
    expect(h2.n_missing_label_value).toBe(1);                            // CODEX-R3-P1-02：缺欄筆數可供匯出前提示
    const h4 = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [], priceChangeMethod: 'x', horizonBars: 4 });
    expect(h4.records[0].label_value).toBe(0.077);                       // 隨 horizon 改欄
    expect(h4.records[0].label_definition.window.horizon_bars).toBe(4);
    const short = await buildEventContractRecords(cases, { timeframe: '12h', conditions: [{ parameter: 'price_change', operator: '<=', value: -0.03 }], priceChangeMethod: 'x' });
    expect(short.records[0].direction).toBe('short');
    expect(short.records[0].label_value).toBe(-0.031);
  });

  it('方向推斷：price_change <= 或負值 ⇒ short；toEpochMs 邊界', () => {
    expect(inferDirection([{ parameter: 'price_change', operator: '<=', value: -0.03 }])).toBe('short');
    expect(inferDirection([{ parameter: 'price_change', operator: '>=', value: 0.03 }])).toBe('long');
    expect(toEpochMs(1704067200)).toBe(1704067200000);
    expect(toEpochMs(1704067200000)).toBe(1704067200000);
    expect(toEpochMs('')).toBeNull();
  });
});

describe('GAP-3 /search 匯出頁面接線（CODEX-R3-P1-02）', () => {
  it('答案窗可選、缺 label_value 先提示、同時下載來源檔', () => {
    const src = readFileSync(resolve(__dirname, '../../app/search/page.tsx'), 'utf-8');
    expect(src).toContain('export-gap3-horizon');                       // horizon 選單
    expect(src).toContain('horizonBars: eventHorizonBars');             // 傳入匯出器
    expect(src).toContain('payload.n_missing_label_value > 0');         // 缺欄提示
    expect(src).toContain('missing_label_value');
    expect(src).toContain('.source.json');                              // companion 來源檔
    expect(src).toContain('payload.source_file_text');
  });
});
