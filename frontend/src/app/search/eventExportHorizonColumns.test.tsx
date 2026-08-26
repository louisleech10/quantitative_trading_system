/**
 * GAP-3 UX Task 4.1 驗收（`--run eventExportHorizonColumns`；SPEC L1957–1972 之①–⑥）。
 *
 * 🔴 **本檔不 mock 匯出組裝器**——跑的是真的 `buildEventContractRecords`，
 *    斷言對象是**真的被下載出去的那個 JSON**（攔 `Blob` 取內容）。
 *    只 mock 兩件事：深度端點（外部 I/O）與下載副作用。
 *    理由（§6.2、B5 R3）：`endpoint 綠 ≠ page effect 綠`；mock 掉組裝器就只是在測 mock。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import { windowHorizonBarsFor } from '@/lib/eventExport';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
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
    currentResult: {
      cases: rows, source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false,
    error: null,
  });
}

/** 攔下載：回傳「事件契約 JSON」之解析結果（第一個 Blob；第二個是 companion 來源檔）。 */
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
  vi.stubGlobal('URL', {
    createObjectURL: (b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; },
    revokeObjectURL: () => {},
  });
}

async function exportAndParse(): Promise<{ records: Row[]; payload: Row }> {
  fireEvent.click(screen.getByTestId('export-gap3-events'));
  await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
  const payload = JSON.parse(blobs[0]) as Row;
  return { records: payload.records as Row[], payload };
}

/** 只留指定 h（其餘取消勾選）。 */
function selectOnly(keep: number[]) {
  for (const h of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) {
    const box = screen.getByTestId(`export-attached-h${h}`) as HTMLInputElement;
    if (box.checked !== keep.includes(h)) fireEvent.click(box);
  }
}

beforeEach(() => {
  seed([caseRow(), caseRow({ timestamp: '2024-01-01 01:00:00', positive_case: false })]);
  depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 0 } });
  stubDownloads();
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 4.1 — 匯出檔之附帶 future_* 欄；移除答案窗與 label_value', () => {
  it('① 附帶選 [1,3,7] ⇒ 匯出檔含 future_{1,3,7}bar_return 三欄，且**不含**沒選的', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([1, 3, 7]);

    const { records } = await exportAndParse();
    for (const r of records) {
      expect(Object.keys(r).filter((k) => k.startsWith('future_')).sort())
        .toEqual(['future_1bar_return', 'future_3bar_return', 'future_7bar_return']);
    }
  });

  it('② `label_value` 不在匯出檔內——**逐列**驗，不是只看第一列', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());

    const { records } = await exportAndParse();
    expect(records.length).toBeGreaterThan(1);           // 只有一列的話「逐列」沒有意義
    for (const r of records) {
      expect('label_value' in r).toBe(false);
      // 連改名／換形狀的復活都擋：任何 label_value* 之鍵都不得出現
      expect(Object.keys(r).filter((k) => k.startsWith('label_value'))).toEqual([]);
    }
  });

  it('③ 匯出面板**不存在**「主答案窗」控制項', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    expect(screen.queryByTestId('export-gap3-horizon')).toBeNull();
    // 對照：面板本身在（否則「整個面板沒 render」也會讓上一行綠）
    expect(screen.getByTestId('export-attached-columns')).toBeTruthy();
  });

  it('④ `lookahead_bars_declared` ＝後端深度端點之回傳 map；`horizon_bars` 由**同一 exported 函式**導出', async () => {
    const depth = { '1h': 7 };
    depthMock.mockResolvedValue({ depth_by_timeframe: depth });
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());

    const { records } = await exportAndParse();
    const r0 = records[0];
    // 🔴 比對對象是**端點回傳之 map**，不是寫死數字（寫死的話改端點回傳也不會紅）
    expect(r0.lookahead_bars_declared).toEqual(depth);
    // 🔴 呼叫**同一 exported 函式**比對（第二份實作必然漂移）
    const ld = r0.label_definition as { window: { horizon_bars: number } };
    expect(ld.window.horizon_bars).toBe(
      windowHorizonBarsFor(String(r0.timeframe), depth as Record<string, number>),
    );
    expect(ld.window.horizon_bars).toBe(
      Math.max(1, (r0.lookahead_bars_declared as Record<string, number>)[String(r0.timeframe)]),
    );
  });

  it('⑤ 改變附帶欄之選擇 ⇒ `lookahead_bars_declared` 與 `horizon_bars` **皆不變**', async () => {
    const depth = { '1h': 7 };
    depthMock.mockResolvedValue({ depth_by_timeframe: depth });
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());

    selectOnly([1, 2]);
    const a = (await exportAndParse()).records[0];
    blobs.length = 0;
    selectOnly([3, 9, 12]);
    const b = (await exportAndParse()).records[0];

    // 附帶欄確實變了（否則本條在比兩份一樣的東西）
    expect(Object.keys(a).filter((k) => k.startsWith('future_')))
      .not.toEqual(Object.keys(b).filter((k) => k.startsWith('future_')));
    // 而深度宣告與答案窗**不受影響**——附帶欄不參與深度導出（D-7）
    expect(b.lookahead_bars_declared).toEqual(a.lookahead_bars_declared);
    expect((b.label_definition as { window: { horizon_bars: number } }).window.horizon_bars)
      .toBe((a.label_definition as { window: { horizon_bars: number } }).window.horizon_bars);
  });

  it('⑥ 深度 0 之 floor：`lookahead_bars_declared[1h] === 0` 且 `window.horizon_bars === 1`（**刻意不等**）', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 0 } });
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());

    const { records } = await exportAndParse();
    const r0 = records[0];
    expect(r0.scenario).toBe('C');
    expect((r0.lookahead_bars_declared as Record<string, number>)['1h']).toBe(0);
    expect((r0.label_definition as { window: { horizon_bars: number } }).window.horizon_bars).toBe(1);
    // 🔴 兩者刻意不相等——「順手對齊」會讓契約之 serialization floor 吃掉真實深度
    expect((r0.lookahead_bars_declared as Record<string, number>)['1h'])
      .not.toBe((r0.label_definition as { window: { horizon_bars: number } }).window.horizon_bars);
  });
});
