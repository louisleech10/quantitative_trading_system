/**
 * GAP-3 UX Task 5.3 驗收（`--run exportHorizonCoverageDialog`；SPEC L2092–2105）。
 *
 * 5.3 ＝**擴寫 Task 4.3 的同一個確認框**（不另建第二個）：從「只在缺欄時跳、只列缺幾筆」
 * 改為**匯出前主動顯示**每個附帶 horizon「N/M 筆可算、K 筆因資料尾端不足而缺」。
 *
 * 邊界①：fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（**數字精確比對**，不是「含某個數字」）。
 * 邊界②：訊息**不得**含「主答案窗」字樣。
 * 不可做：不得阻擋匯出。
 *
 * 🔴 反假綠：①送出鍵**保持可按**；②「不阻擋」用執行期證據（按確定真的下載／按取消不下載）；
 *   ③另有對照組證明訊息不是恆顯示同一段（不同缺筆數 ⇒ 不同數字）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { horizonCoverage, horizonCoverageLines } from '@/lib/eventExport';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
});

const blobs: string[] = [];
let confirmMock: ReturnType<typeof vi.fn>;

/**
 * 五列，**尾端 3 筆**沒有 `future_4bar_return`（＝答案窗還沒走完）；
 * `future_1bar_return` 五列都有 ⇒ 同一畫面上同時存在「有缺」與「不缺」兩種欄。
 */
function rows(): CaseData[] {
  return [0, 1, 2, 3, 4].map((i) => ({
    symbol: 'ETHUSDT',
    timeframe: '1h',
    timestamp: `2024-01-01 0${i}:00:00`,
    positive_case: i % 2 === 0,
    price_change: 1 + i,
    future_1bar_return: 0.01 * (i + 1),
    ...(i < 2 ? { future_4bar_return: 0.04 * (i + 1) } : {}),   // 後 3 列缺
  })) as unknown as CaseData[];
}

function seed() {
  useSearchStore.setState({
    currentResult: {
      cases: rows(), source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
}

function selectOnly(keep: number[]) {
  for (const h of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) {
    const box = screen.getByTestId(`export-attached-h${h}`) as HTMLInputElement;
    if (box.checked !== keep.includes(h)) fireEvent.click(box);
  }
}

beforeEach(() => {
  seed();
  depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 0 } });
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
  vi.stubGlobal('alert', vi.fn());
  confirmMock = vi.fn(() => true);
  vi.stubGlobal('confirm', confirmMock);
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 5.3 — 匯出前主動顯示每個附帶 horizon 之可算／缺筆數', () => {
  it('① 尾端 3 筆不足 ⇒ 訊息逐字含「2/5 筆可算、3 筆因資料尾端不足而缺」（數字精確比對）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([1, 4]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());

    const msg = String(confirmMock.mock.calls[0][0]);
    expect(msg).toContain('future_4bar_return：2/5 筆可算、3 筆因資料尾端不足而缺');
    // 對照組：不缺的那個欄**也**被主動列出，且數字是 5/5、0 筆缺（不是抄同一行）
    expect(msg).toContain('future_1bar_return：5/5 筆可算、0 筆因資料尾端不足而缺');
  });

  it('② 訊息不得含「主答案窗」字樣（該概念已隨 4.1 移出匯出層）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([4]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());

    const msg = String(confirmMock.mock.calls[0][0]);
    expect(msg).not.toContain('主答案窗');
    expect(msg).not.toContain('label_value');
  });

  it('③ 主動顯示：**全部欄都算得出來**時仍然顯示，且逐行為 5/5、0 筆缺', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([1]);                       // 這欄五列都有

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());
    const msg = String(confirmMock.mock.calls[0][0]);
    expect(msg).toContain('future_1bar_return：5/5 筆可算、0 筆因資料尾端不足而缺');
    expect(msg).not.toContain('future_4bar_return');   // 沒勾的欄不列（防「全部 12 欄硬列」）
  });

  it('④ 不阻擋匯出：按確定 ⇒ 真的下載，缺欄之列仍在（執行期證據）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([4]);

    // 🔴 送出鍵刻意保持可按——設 disabled 的話這個 click 什麼都沒觸發、整條測試恆綠（B4 教訓）
    expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    const records = (JSON.parse(blobs[0]) as { records: unknown[] }).records;
    expect(records.length).toBe(5);
  });

  it('⑤ 對照組：按取消 ⇒ 不下載（證明 ④ 不是「反正都會下載」）', async () => {
    confirmMock.mockReturnValue(false);
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([4]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());
    expect(blobs.length).toBe(0);
  });

  it('⑥ 一個附帶欄都沒勾 ⇒ 不跳確認框（沒有東西可講；防「恆跳」）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    expect(confirmMock).not.toHaveBeenCalled();
  });

  it('⑦ 純函式層：可算＋缺 == 分母，且逐 horizon 各自算（不得共用同一個數）', () => {
    const cov = horizonCoverage({ attached_horizons: [4, 1], missing_by_horizon: { 4: 3 }, n_records: 5 });
    expect(cov.map((c) => c.horizon)).toEqual([1, 4]);          // 升序
    for (const c of cov) expect(c.computable + c.missing).toBe(c.total);
    expect(cov).toEqual([
      { horizon: 1, computable: 5, total: 5, missing: 0 },
      { horizon: 4, computable: 2, total: 5, missing: 3 },
    ]);
    expect(horizonCoverageLines({ attached_horizons: [], missing_by_horizon: {}, n_records: 5 })).toEqual([]);
  });
});
