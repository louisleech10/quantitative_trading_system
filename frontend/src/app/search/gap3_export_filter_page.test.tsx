/**
 * GAP-3 UX B5 R1 `CODEX-R1-P1-05`／`R-B3-1` — `/search` 之**執行期**接線測試。
 *
 * R1 之缺口：端到端測試停在 API 層（`canonical_filter_columns()` ＋ TestClient POST），
 * **沒有跑到 page 的 effect、state 更新與匯出點擊** ⇒ page wiring 被改壞時整組驗收仍可綠。
 * 本檔補的就是那一段：真的 render `SearchPage`、真的改條件、真的按匯出鈕。
 *
 * 🔴 斷言一律是**執行期事實**（呼叫次數、送出的 payload），不看原始碼長相（§6.2）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();
const buildRecordsMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
});

// 匯出組裝器：用它的呼叫次數當「匯出是否真的發生」之執行期證據
vi.mock('@/lib/eventExport', async (orig) => {
  const actual = await orig<typeof import('@/lib/eventExport')>();
  return { ...actual, buildEventContractRecords: (...a: unknown[]) => buildRecordsMock(...a) };
});

const CASES = [
  { symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00', positive_case: true,
    price_change: 3.2, future_2bar_return: 1.1 },
  { symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 01:00:00', positive_case: false,
    price_change: -1.0, future_2bar_return: -0.3 },
] as unknown as CaseData[];

function seedResult() {
  useSearchStore.setState({
    currentResult: {
      cases: CASES,
      source_file_text: '[]',
      source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false,
    error: null,
  });
}

/** 加一條條件並填欄位／運算子／值。 */
function addCondition(column: string, value: string) {
  fireEvent.click(screen.getByTestId('export-filter-add'));
  fireEvent.change(screen.getByTestId('export-filter-column-0'), { target: { value: column } });
  fireEvent.change(screen.getByTestId('export-filter-value-0'), { target: { value } });
}

beforeEach(() => {
  seedResult();
  buildRecordsMock.mockResolvedValue({
    records: [], skipped: [], n_cases: 0, n_records: 0,
    source_file_digest: 'a'.repeat(64), source_file_text: '[]',
    // Task 4.3：逐附帶 horizon 之缺欄計數（取代舊的 `n_missing_label_value`）。
    // 🔴 刻意不在 page 側寫 `?? {}` 容錯——欄位真的不見時應該當場炸，不是靜默跳過確認框。
    missing_by_horizon: {}, attached_horizons: [], lookahead_bars_declared: {},
  });
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  buildRecordsMock.mockReset();
  vi.unstubAllGlobals();
});

describe('GAP-3 B5 /search 匯出前篩選之執行期接線', () => {
  it('① 條件變動 ⇒ 真的呼叫下界端點，且送出的 referenced_columns 只含條件引用之欄', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    const payload = depthMock.mock.calls.at(-1)![0] as {
      referenced_columns: string[]; declared_window_bars: Record<string, number>; timeframes: string[];
    };
    expect(payload.referenced_columns).toEqual(['future_2bar_return']);
    expect(payload.timeframes).toEqual(['1h']);
    expect(Object.keys(payload.declared_window_bars)).toEqual(['1h']);
  });

  it('② 🔴 下界查詢失敗 ⇒ 匯出被擋（`buildEventContractRecords` 呼叫次數 == 0）', async () => {
    // 這正是 R1 `CODEX-R1-P1-01` 的可重現序列：有條件 → 查詢失敗 → 使用者按匯出
    depthMock.mockRejectedValue(new Error('boom'));
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-error')).toBeTruthy());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);
  });

  it('②b 下界還沒回來（pending）⇒ 匯出同樣被擋', async () => {
    let release: ((v: unknown) => void) | undefined;
    depthMock.mockImplementation(() => new Promise((res) => { release = res; }));
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-pending')).toBeTruthy());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);
    release?.({ depth_by_timeframe: { '1h': 2 } });
  });

  it('③ 下界解析成功且選值達標 ⇒ 匯出真的發生，且送出的是**篩選後**之列與條件物件', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    render(<SearchPage />);
    addCondition('price_change', '0');          // 只留第一列（3.2 ≥ 0；-1.0 落選）

    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));

    const [rows, opts] = buildRecordsMock.mock.calls[0] as [CaseData[], { filters?: unknown }];
    expect(rows.length).toBe(1);
    expect((rows[0] as unknown as { price_change: number }).price_change).toBe(3.2);
    expect(opts.filters).toEqual({
      version: 1, combinator: 'AND',
      conditions: [{ column: 'price_change', op: '>=', value: 0 }],
    });
  });

  it('④ 🔴 混 TF 且逐 tf 下界不同 ⇒ 顯示逐週期下界、**可匯出**，且送入完整逐 tf map（不得取 max 冒充）', async () => {
    useSearchStore.setState({
      currentResult: {
        cases: [
          { ...(CASES[0] as object), timeframe: '1h' },
          { ...(CASES[1] as object), timeframe: '12h' },
        ] as unknown as CaseData[],
        source_file_text: '[]',
        source_file_digest: 'a'.repeat(64),
      } as unknown as SearchResultData,
      isLoading: false,
      error: null,
    });
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 72, '12h': 6 } });
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-map')).toBeTruthy());
    expect(screen.getByTestId('export-lower-bound-map').textContent).toContain('1h=72');
    expect(screen.getByTestId('export-lower-bound-map').textContent).toContain('12h=6');

    // 🔴 `D-004 A-021(d)`：混 TF 且下界不同**現在可以匯出**（4.1 後 horizon_bars 逐列依該列 tf 寫入）。
    //    改形前這裡是「擋住」；擋的理由（單一 scalar 表達不了 per-scope）已隨逐列寫入消失。
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    expect(alert).not.toHaveBeenCalled();
    // 🔴 但**不得**塌成 scalar：送進組裝器的必須是完整逐 tf map（取 max 冒充會被這條抓到）
    const [, opts] = buildRecordsMock.mock.calls[0] as [CaseData[], { lookaheadBarsDeclared?: Record<string, number> }];
    expect(opts.lookaheadBarsDeclared).toEqual({ '1h': 72, '12h': 6 });
  });

  it('⑤ 🔴 沒有任何篩選條件時也會查深度，且該 map 真的送進匯出組裝器（Task 4.1 ③）', async () => {
    // 改形前這裡驗的是「下界 72 時答案窗下拉要有可選值」——主答案窗已移除（`A-021(e)`）。
    // 換成釘住新的必要條件：匯出檔必帶 `lookahead_bars_declared`，而它只有後端算得出來
    // ⇒ **無條件時也要查**，且前端不得自填 0。
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 0 } });
    render(<SearchPage />);

    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    const payload = depthMock.mock.calls.at(-1)![0] as {
      referenced_columns: string[]; declared_window_bars: Record<string, number>;
    };
    expect(payload.referenced_columns).toEqual([]);
    // `A-021(a)`：匯出路徑之左項一律送 0，且**不得省略鍵**（缺 tf 後端會 KeyError）
    expect(payload.declared_window_bars).toEqual({ '1h': 0 });

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    const [, opts] = buildRecordsMock.mock.calls[0] as [CaseData[], { lookaheadBarsDeclared?: Record<string, number> }];
    expect(opts.lookaheadBarsDeclared).toEqual({ '1h': 0 });
  });

  it('⑦ 🔴 CSV 匯出也套同一組條件（R2 `CODEX-R2-P1-01`：面板就在按鈕上方，不能只有事件 JSON 套）', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    const blobs: string[] = [];
    vi.stubGlobal('URL', {
      createObjectURL: (b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; },
      revokeObjectURL: () => {},
    });
    // jsdom 的 Blob 讀不回內容 ⇒ 攔在建構處把文字留下來
    const RealBlob = globalThis.Blob;
    vi.stubGlobal('Blob', class extends RealBlob {
      _text: string;
      constructor(parts: BlobPart[], opts?: BlobPropertyBag) {
        super(parts, opts);
        this._text = String(parts[0] ?? '');
      }
    });

    render(<SearchPage />);
    addCondition('price_change', '0');            // 兩列裡只有第一列（3.2 ≥ 0）通過
    await waitFor(() => expect(screen.getByTestId('export-count-n').textContent).toBe('1'));

    fireEvent.click(screen.getByText('導出CSV檔案'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    const dataLines = blobs[0].split('\n').filter((l) => l.trim().length > 0).slice(1);
    expect(dataLines.length).toBe(1);              // 畫面說 1 筆，檔案裡就是 1 筆
    // 留下來的必須是**通過條件**那一列（第一列），不是隨便留一列
    expect(dataLines[0]).toContain('2024-01-01 00:00:00');
    expect(dataLines[0]).not.toContain('2024-01-01 01:00:00');
  });

  it('⑧ 🔴 有列缺正反例標記時：CSV 筆數與事件 JSON 筆數**不同且都要顯示**（R3 `CODEX-R3-P1-01`）', async () => {
    // 事件契約 JSON 必須有標記 ⇒ 少一列；CSV 是原始結果 ⇒ 不該因少一個旗標就丟整列。
    // 兩個數字不同是正常的，**只顯示一個讓使用者對不上**才是缺陷。
    useSearchStore.setState({
      currentResult: {
        cases: [
          ...(CASES as unknown as Record<string, unknown>[]),
          { symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 02:00:00',
            positive_case: null, price_change: 5.0, future_2bar_return: 2.2 },
        ] as unknown as CaseData[],
        source_file_text: '[]', source_file_digest: 'a'.repeat(64),
      } as unknown as SearchResultData,
      isLoading: false, error: null,
    });
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });

    const blobs: string[] = [];
    vi.stubGlobal('URL', {
      createObjectURL: (b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; },
      revokeObjectURL: () => {},
    });
    const RealBlob = globalThis.Blob;
    vi.stubGlobal('Blob', class extends RealBlob {
      _text: string;
      constructor(parts: BlobPart[], opts?: BlobPropertyBag) {
        super(parts, opts);
        this._text = String(parts[0] ?? '');
      }
    });

    render(<SearchPage />);
    // 三列全部通過（無條件）：事件 JSON 收 2 筆（有標記者），CSV 收 3 筆
    expect(screen.getByTestId('export-count-n').textContent).toBe('2');
    expect(screen.getByTestId('export-count-csv').textContent).toContain('3');

    fireEvent.click(screen.getByText('導出CSV檔案'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    const dataLines = blobs[0].split('\n').filter((l) => l.trim().length > 0).slice(1);
    expect(dataLines.length).toBe(3);              // CSV 就是畫面說的 CSV 筆數
    expect(dataLines.some((l) => l.includes('2024-01-01 02:00:00'))).toBe(true);   // 無標記那列仍在
  });

  it('⑥ Task 2.3：畫面上的筆數就是 computeExportCounts 的結果（同一組事實）', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    render(<SearchPage />);
    expect(screen.getByTestId('export-count-m').textContent).toBe('2');
    expect(screen.getByTestId('export-count-n').textContent).toBe('2');
    expect(screen.getByTestId('export-count-x').textContent).toBe('1');
    expect(screen.getByTestId('export-count-y').textContent).toBe('1');

    addCondition('price_change', '0');
    await waitFor(() => expect(screen.getByTestId('export-count-n').textContent).toBe('1'));
    expect(screen.getByTestId('export-count-x').textContent).toBe('1');
    expect(screen.getByTestId('export-count-y').textContent).toBe('0');
    expect(screen.getByTestId('export-count-m').textContent).toBe('2');   // 原筆數不變
  });
});
