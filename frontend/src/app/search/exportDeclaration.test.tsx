/**
 * GAP-3 UX Task 1.9′ 驗收（`--run exportDeclaration`；SPEC Task 1.9′ 驗證 ①–⑦）——
 * `/search` 匯出端答案窗宣告框與 `withExportDeclarationGuard`。
 *
 * 🔴 **本檔不 mock 匯出組裝器**：跑真的 `buildEventContractRecords`，斷言對象是**真的被下載出去的 JSON／CSV**
 *    （攔 `Blob` 取內容）。只 mock 兩件事：preview 端點（外部 I/O）與下載副作用；另 stub `fetch` 計數。
 * 🔴 mutation（皆須紅）：匯出動作移到 `proceed` 外 ⇒ ②③；守衛對缺鍵 tf 以 `1` 默認 ⇒ ②；
 *    CSV 路徑另組一份 map ⇒ ⑥；前端自寫第二份 validator ⇒ ⑦。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { declareFromPreview, previewOf } from '@/test/lookaheadDeclarationTestUtils';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import * as declarationModule from '@/lib/lookaheadDeclaration';
import type { CaseData, SearchResultData } from '@/lib/types';

const previewMock = vi.fn();
const validateSpy = vi.fn();
const buildSpy = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDeclarationPreviewColumns: (...a: unknown[]) => previewMock(...a) };
});

// 執行期探針：validator 與組裝器都走**真實**實作，只記錄呼叫（⑥⑦ 之證據）
vi.mock('@/lib/lookaheadDeclaration', async (orig) => {
  const actual = await orig<typeof import('@/lib/lookaheadDeclaration')>();
  return {
    ...actual,
    validateDeclaration: (...a: Parameters<typeof actual.validateDeclaration>) => {
      validateSpy(...a);
      return actual.validateDeclaration(...a);
    },
  };
});
vi.mock('@/lib/eventExport', async (orig) => {
  const actual = await orig<typeof import('@/lib/eventExport')>();
  return {
    ...actual,
    buildEventContractRecords: (...a: Parameters<typeof actual.buildEventContractRecords>) => {
      buildSpy(...a);
      return actual.buildEventContractRecords(...a);
    },
  };
});

type Row = Record<string, unknown>;

function caseRow(over: Row = {}): CaseData {
  return {
    symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00', positive_case: true,
    price_change: 3.2,
    ...Object.fromEntries([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((h) => [`future_${h}bar_return`, h / 100])),
    ...over,
  } as unknown as CaseData;
}

function seed(rows: CaseData[]) {
  useSearchStore.setState({
    currentResult: { cases: rows, source_file_text: '[]', source_file_digest: 'a'.repeat(64) } as unknown as SearchResultData,
    isLoading: false,
    error: null,
  });
}

const blobs: string[] = [];
const createObjectURL = vi.fn((b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; });
const fetchSpy = vi.fn();

function stubDownloads() {
  blobs.length = 0;
  const RealBlob = globalThis.Blob;
  vi.stubGlobal('Blob', class extends RealBlob {
    _text: string;
    constructor(parts: BlobPart[], opts?: BlobPropertyBag) {
      super(parts, opts);
      this._text = String(parts[0] ?? '');
    }
  });
  // 🔴 保留 `URL` 建構子（CSV 路徑之模組載入會 `new URL(...)`），只覆蓋兩個靜態方法
  const RealURL = globalThis.URL;
  vi.stubGlobal('URL', class extends RealURL {
    static createObjectURL = createObjectURL as unknown as typeof RealURL.createObjectURL;
    static revokeObjectURL = () => {};
  });
  vi.stubGlobal('fetch', fetchSpy);
  Object.defineProperty(HTMLAnchorElement.prototype, 'click', { configurable: true, value: () => {} });
}

async function exportJson(): Promise<Row[]> {
  fireEvent.click(screen.getByTestId('export-gap3-events'));
  await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
  return (JSON.parse(blobs[0]) as { records: Row[] }).records;
}

const twoRows = () => [caseRow(), caseRow({ timestamp: '2024-01-01 01:00:00', positive_case: false })];

beforeEach(() => {
  seed(twoRows());
  previewMock.mockResolvedValue(previewOf({ '1h': 12 }));
  stubDownloads();
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  previewMock.mockReset();
  validateSpy.mockReset();
  buildSpy.mockReset();
  createObjectURL.mockClear();
  fetchSpy.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 1.9′ — /search 匯出端答案窗宣告框', () => {
  it('① 批內 {1h,12h} ⇒ 恰兩個輸入框；單一 tf 退化為一個', async () => {
    seed([caseRow(), caseRow({ timeframe: '12h', timestamp: '2024-01-01 12:00:00', positive_case: false })]);
    previewMock.mockResolvedValue(previewOf({ '1h': 12, '12h': 12 }));
    const first = render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
    expect(screen.getByTestId('lookahead-window-1h')).toBeTruthy();
    expect(screen.getByTestId('lookahead-window-12h')).toBeTruthy();
    expect(screen.getAllByTestId(/^lookahead-window-/)).toHaveLength(2);
    // preview 之輸入＝結果欄 ∪ 附帶欄、批內 tf 集合（前端不自算預設）
    const arg = previewMock.mock.calls[0][0] as { columns: string[]; timeframes: string[] };
    expect(new Set(arg.timeframes)).toEqual(new Set(['1h', '12h']));
    expect(arg.columns).toContain('future_12bar_return');
    first.unmount();

    seed(twoRows());
    previewMock.mockResolvedValue(previewOf({ '1h': 12 }));
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
    expect(screen.getAllByTestId(/^lookahead-window-/)).toHaveLength(1);
  });

  it('② 不填任一 tf 即按匯出 ⇒ proceed 未呼叫：createObjectURL 與 fetch call count 皆 == 0', async () => {
    previewMock.mockResolvedValue(previewOf({ '1h': 0 }));   // 預設 0 ⇒ 留空不預填
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
    expect((screen.getByTestId('lookahead-window-1h') as HTMLInputElement).value).toBe('');
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    fireEvent.click(screen.getByTestId('export-contract-csv'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildSpy).toHaveBeenCalledTimes(0);
    expect(createObjectURL).toHaveBeenCalledTimes(0);
    expect(fetchSpy).toHaveBeenCalledTimes(0);
    expect(String((alert as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0])).toContain('尚未填寫');
  });

  it('③ 調低於預設且未勾聲明 ⇒ 擋；勾選後 ⇒ 匯出且逐列 lookahead_bars_declared 等於宣告 map', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
    fireEvent.change(screen.getByTestId('lookahead-window-1h'), { target: { value: '3' } });   // 預設 12 ⇒ 調低
    const ack = screen.getByTestId('lookahead-acknowledge') as HTMLInputElement;
    if (ack.checked) fireEvent.click(ack);
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(createObjectURL).toHaveBeenCalledTimes(0);
    expect(buildSpy).toHaveBeenCalledTimes(0);

    fireEvent.click(ack);
    const records = await exportJson();
    expect(records.length).toBe(2);
    for (const r of records) expect(r.lookahead_bars_declared).toEqual({ '1h': 3 });
  });

  it('④ 宣告 {1h:20}（>12）⇒ 接受且 horizon_bars === 20；宣告 {1h:0} ⇒ 接受、深度 0 且 horizon_bars === 1；留白 ⇒ 擋', async () => {
    const first = render(<SearchPage />);
    await declareFromPreview({ '1h': 20 });
    let records = await exportJson();
    for (const r of records) {
      expect(r.lookahead_bars_declared).toEqual({ '1h': 20 });
      expect((r.label_definition as { window: { horizon_bars: number } }).window.horizon_bars).toBe(Math.max(1, 20));
    }
    first.unmount();
    cleanup();
    blobs.length = 0;
    createObjectURL.mockClear();

    render(<SearchPage />);
    await declareFromPreview({ '1h': 0 });                   // 🔴 R36：0 明填 ⇒ 接受
    records = await exportJson();
    for (const r of records) {
      expect((r.lookahead_bars_declared as Record<string, number>)['1h']).toBe(0);
      expect((r.label_definition as { window: { horizon_bars: number } }).window.horizon_bars).toBe(1);
    }
    cleanup();
    blobs.length = 0;
    createObjectURL.mockClear();

    // 留白（清空）⇒ 走②之擋（留白≠0）
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
    fireEvent.change(screen.getByTestId('lookahead-window-1h'), { target: { value: '' } });
    fireEvent.click(screen.getByTestId('lookahead-acknowledge'));
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(createObjectURL).toHaveBeenCalledTimes(0);
  });

  it('⑤ 附帶欄選擇改變 ⇒ 已宣告 map 與 window.horizon_bars 皆不變', async () => {
    render(<SearchPage />);
    const declared = await declareFromPreview({ '1h': 5 });
    // 改附帶欄 ⇒ preview 會重取（預設候選可能變），但已宣告值不得被覆寫
    previewMock.mockResolvedValue(previewOf({ '1h': 3 }));
    fireEvent.click(screen.getByTestId('export-attached-h12'));
    fireEvent.click(screen.getByTestId('export-attached-h11'));
    await waitFor(() => expect(previewMock.mock.calls.length).toBeGreaterThan(1));
    expect((screen.getByTestId('lookahead-window-1h') as HTMLInputElement).value).toBe('5');
    const records = await exportJson();
    for (const r of records) {
      expect(r.lookahead_bars_declared).toEqual(declared);
      expect((r.label_definition as { window: { horizon_bars: number } }).window.horizon_bars).toBe(5);
    }
  });

  it('⑥ JSON 與 CSV 兩條匯出對同一宣告產出相同 lookahead_bars_declared（逐鍵 ==）', async () => {
    render(<SearchPage />);
    await declareFromPreview({ '1h': 7 });
    const jsonRecords = await exportJson();
    fireEvent.click(screen.getByTestId('export-contract-csv'));
    const alertCalls = (alert as unknown as { mock: { calls: unknown[][] } }).mock.calls;
    await waitFor(() => expect(blobs.length > 2 || alertCalls.length > 0).toBe(true));
    expect(alertCalls).toEqual([]);                                  // 守衛未擋、proceed 未拋錯
    await waitFor(() => expect(blobs.length).toBeGreaterThan(2));
    const csv = blobs[blobs.length - 1];
    const [header, ...lines] = csv.trim().split('\n');
    const cols = header.split(',');
    const idx = cols.indexOf('lookahead_bars_declared.1h');
    expect(idx).toBeGreaterThanOrEqual(0);
    for (const line of lines) expect(Number(line.split(',')[idx])).toBe(7);
    for (const r of jsonRecords) expect(r.lookahead_bars_declared).toEqual({ '1h': 7 });
    // 兩條路徑餵給組裝器的 map **逐鍵相等**，且來自同一函式（CSV 不另組）
    expect(buildSpy).toHaveBeenCalledTimes(2);
    const a = (buildSpy.mock.calls[0][1] as { lookaheadBarsDeclared: Record<string, number> }).lookaheadBarsDeclared;
    const b = (buildSpy.mock.calls[1][1] as { lookaheadBarsDeclared: Record<string, number> }).lookaheadBarsDeclared;
    expect(a).toEqual(b);
    expect(Object.keys(a)).toEqual(['1h']);
  });

  it('⑦ /search 與匯入頁取用同一 exported validateDeclaration（執行期探針＋來源對證）', async () => {
    render(<SearchPage />);
    await declareFromPreview({ '1h': 4 });
    // 頁面把使用者當下的宣告餵給**同一模組**之 `validateDeclaration`（執行期探針；不是自寫一份）
    await waitFor(() => expect(validateSpy).toHaveBeenCalled());
    const last = validateSpy.mock.calls[validateSpy.mock.calls.length - 1];
    expect(last[0]).toEqual({ '1h': 4 });
    expect(last[1]).toBe(true);
    expect(typeof declarationModule.validateDeclaration).toBe('function');
    const records = await exportJson();
    for (const r of records) expect(r.lookahead_bars_declared).toEqual({ '1h': 4 });
    // 兩頁皆自 `@/lib/lookaheadDeclaration` 取用，且都沒有自己再寫一份
    const page = readFileSync(resolve(__dirname, './page.tsx'), 'utf-8');
    const form = readFileSync(resolve(__dirname, '../../components/case/EventCsvMappingForm.tsx'), 'utf-8');
    for (const src of [page, form]) {
      expect(src).toMatch(/import\s*\{[\s\S]*?validateDeclaration[\s\S]*?\}\s*from\s*'@\/lib\/lookaheadDeclaration'/);
      expect(src).not.toMatch(/function\s+validateDeclaration\s*\(/);
      expect(src).not.toMatch(/const\s+validateDeclaration\s*=/);
    }
  });
});
