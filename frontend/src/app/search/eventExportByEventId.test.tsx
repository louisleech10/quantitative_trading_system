/**
 * SPLITUNIFY D-002 `Task 9.5`（`C5-18`／`M-SU-D2-11`）：匯出之 `byEventId` Map 維持 `canonicalEventId` 建鍵。
 *
 * 🔴 `byEventId` 之鍵由原始搜尋列之 `canonicalEventId(symbol, timeframe, t0)` 建立，匯出 record 只有 `event_id`；
 *    若有人把它「跟著後端」改成複合鍵（例如再接 `feature_timeframe`），`byEventId.get(String(rec.event_id))`
 *    會**全數 miss**，CSV 之 `meta.*` 附帶欄位**靜默變空**——不會報錯，只會少欄。
 *    ⇒ 本檔斷言附帶欄位之**值**逐列正確（不是只看「有匯出」），且來源列帶 `feature_timeframe` 時仍對得上。
 *
 * 🔴 附帶欄位只進 **CSV** 匯出（`buildEventContractCsv(records, extras)`，一律 `meta.` 前綴）；JSON 匯出不帶。
 * 🔴 不 mock 匯出組裝器（同 `eventExportHorizonColumns.test.tsx`）：只 mock 深度端點與下載副作用。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { declareFromPreview, previewOf } from '@/test/lookaheadDeclarationTestUtils';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDeclarationPreviewColumns: (...a: unknown[]) => depthMock(...a) };
});

type Row = Record<string, unknown>;

function caseRow(over: Row = {}): CaseData {
  return {
    symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00', positive_case: true,
    ...over,
  } as unknown as CaseData;
}

function seed(rows: CaseData[]) {
  useSearchStore.setState({
    currentResult: {
      cases: rows, source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false,
    error: null,
  });
}

const blobs: string[] = [];

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
  // 🔴 保留 `URL` 建構子（CSV 路徑之模組載入會 `new URL(...)`；整個換成物件即「URL is not a constructor」），
  //    只覆蓋兩個靜態方法——同 `exportDeclaration.test.tsx`。
  const RealURL = globalThis.URL;
  vi.stubGlobal('URL', class extends RealURL {
    static createObjectURL = ((b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; }) as unknown as typeof RealURL.createObjectURL;
    static revokeObjectURL = () => {};
  });
  Object.defineProperty(HTMLAnchorElement.prototype, 'click', { configurable: true, value: () => {} });
}

/** 依 `eventContractCsv.cell` 之引號規則解析一列（雙引號包住、內部 `""` 為一個引號）。 */
function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else cur += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { out.push(cur); cur = ''; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}

async function exportCsvRows(): Promise<Row[]> {
  fireEvent.click(screen.getByTestId('export-contract-csv'));
  const alertCalls = (alert as unknown as { mock: { calls: unknown[][] } }).mock.calls;
  // CSV 路徑有兩次動態 import，首跑可能超過 waitFor 預設 1 秒；同時等「守衛擋下」以免空等後誤判為 miss。
  await waitFor(() => expect(blobs.length > 0 || alertCalls.length > 0).toBe(true), { timeout: 5000 });
  expect(alertCalls).toEqual([]);                                   // 守衛未擋、proceed 未拋錯
  const [header, ...lines] = blobs[blobs.length - 1].trim().split('\n');
  const cols = parseCsvLine(header);
  return lines.map((ln) => Object.fromEntries(parseCsvLine(ln).map((v, i) => [cols[i], v])));
}

beforeEach(() => {
  depthMock.mockResolvedValue(previewOf({ '1h': 0 }));
  stubDownloads();
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 9.5 — 匯出 byEventId 以 canonicalEventId 建鍵（CSV 附帶欄位不得靜默變空）', () => {
  it('① `meta.*` 附帶欄位之**值**逐列對回各自的來源列（非位置對位、非只看有無）', async () => {
    // 兩列之附帶值刻意不同：任何 miss（欄空）或錯位（值互換）都會使斷言不符。
    seed([
      caseRow({ price_change: 3.2, analyst_note: 'first' }),
      caseRow({ timestamp: '2024-01-01 01:00:00', positive_case: false, price_change: -1.5, analyst_note: 'second' }),
    ]);
    render(<SearchPage />);
    await declareFromPreview();

    const rows = await exportCsvRows();
    expect(rows.length).toBe(2);                           // 兩列皆匯出，否則「逐列」無意義
    const byNote = Object.fromEntries(rows.map((r) => [r['meta.analyst_note'], r]));
    expect(Object.keys(byNote).sort()).toEqual(['first', 'second']);
    expect(Number(byNote.first['meta.price_change'])).toBe(3.2);
    expect(Number(byNote.second['meta.price_change'])).toBe(-1.5);
    // 附帶值與事件身分一致：note＝first 之列 t0 早於 second（證明不是把兩列的附帶值互換）
    expect(Number(byNote.first.t0)).toBeLessThan(Number(byNote.second.t0));
  });

  it('② 來源列帶 `feature_timeframe` 時仍以 canonicalEventId 建鍵：附帶欄位不為空、值正確', async () => {
    seed([
      caseRow({ price_change: 7.7, feature_timeframe: '4h' }),
      caseRow({ timestamp: '2024-01-01 01:00:00', positive_case: false, price_change: 8.8, feature_timeframe: '12h' }),
    ]);
    render(<SearchPage />);
    await declareFromPreview();

    const rows = await exportCsvRows();
    expect(rows.length).toBe(2);
    for (const r of rows) {
      expect(r['meta.price_change']).not.toBe('');          // miss 時 extras 為 {}，該欄即空
    }
    const byTf = Object.fromEntries(rows.map((r) => [r['meta.feature_timeframe'], Number(r['meta.price_change'])]));
    expect(byTf).toEqual({ '4h': 7.7, '12h': 8.8 });
  });
});
