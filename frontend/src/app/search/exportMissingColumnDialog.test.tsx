/**
 * GAP-3 UX Task 4.3 驗收（`--run exportMissingColumnDialog`；SPEC L2037–2049）。
 *
 * 缺欄確認框改為**逐附帶 horizon** 列缺幾筆。匯出端已無「答案窗缺欄」這件事
 * （`label_value` 不在匯出檔內）⇒ 只剩附帶欄一類。
 *
 * 🔴 反假綠：①送出鍵**保持可按**（B4 教訓：設 disabled 的話 `fireEvent.click` 什麼都沒觸發、恆綠）；
 *   ②「不阻擋匯出」用**執行期**證據（按取消 ⇒ 沒有下載；按確定 ⇒ 真的下載）而非讀碼。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
});

const blobs: string[] = [];
let confirmMock: ReturnType<typeof vi.fn>;

/** 兩列；第一列缺 future_3／future_7，第二列只缺 future_7 ⇒ 逐 horizon 之筆數刻意不同。 */
function rows(): CaseData[] {
  const base = {
    symbol: 'ETHUSDT', timeframe: '1h', positive_case: true, price_change: 3.2,
    future_1bar_return: 0.01, future_2bar_return: 0.02,
  };
  return [
    { ...base, timestamp: '2024-01-01 00:00:00' },
    { ...base, timestamp: '2024-01-01 01:00:00', positive_case: false, future_3bar_return: 0.03 },
  ] as unknown as CaseData[];
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

describe('Task 4.3 — 缺欄確認框逐 horizon 列出', () => {
  it('① 訊息含**每一個**缺欄附帶 horizon 之筆數數字（逐 horizon，非一句總計）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([1, 3, 7]);                    // future_3 缺 1 筆、future_7 缺 2 筆、future_1 不缺

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());

    const msg = String(confirmMock.mock.calls[0][0]);
    // 🔴 逐 horizon 之缺筆數**各自不同**（1 vs 2）——一句總計或共用同一個數字都會讓本條紅
    expect(msg).toContain('future_3bar_return：1/2 筆可算、1 筆');
    expect(msg).toContain('future_7bar_return：0/2 筆可算、2 筆');
  });

  /**
   * 🔴 **本條原為「不缺的欄不列出來」**（4.3 時的恆跳／恆列鑑別力保護）。
   * Task 5.3 之 SPEC L2092–2105 明令「現行只在缺…時跳，**改為**匯出前主動顯示」
   * ⇒ 不缺的欄**現在必須也列出來**，原斷言與 5.3 直接相斥、只能擇一。
   * 鑑別力改由「不缺者之數字必須是 M/M、0 筆」承接：實作若把每行寫死成同一段文字，本條紅。
   */
  it('①b 不缺的附帶欄也會被列出，且數字為全數可算（5.3 擴寫後之鑑別力）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([1, 3, 7]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());

    const msg = String(confirmMock.mock.calls[0][0]);
    expect(msg).toContain('future_1bar_return：2/2 筆可算、0 筆');
    expect(msg).not.toContain('future_2bar_return');   // 沒勾的欄仍不列
  });

  it('② 訊息**不得**含「主答案窗」字樣（該概念已隨 4.1 移除）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([7]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());

    const msg = String(confirmMock.mock.calls[0][0]);
    expect(msg).not.toContain('主答案窗');
    expect(msg).not.toContain('label_value');
  });

  it('③ 缺欄**不阻擋**匯出：按確定 ⇒ 真的下載（執行期證據，非讀碼）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([7]);

    // 🔴 送出鍵刻意保持可按——設成 disabled 的話這個 click 什麼都沒觸發、整條測試恆綠（B4 教訓）
    expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    const records = (JSON.parse(blobs[0]) as { records: unknown[] }).records;
    expect(records.length).toBe(2);           // 缺欄之列**仍在**，只是不帶那一欄
  });

  it('④ 按取消 ⇒ 不下載（對照組：證明 ③ 不是「反正都會下載」）', async () => {
    confirmMock.mockReturnValue(false);
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([7]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(confirmMock).toHaveBeenCalled());
    expect(blobs.length).toBe(0);
  });

  /**
   * 🔴 **本條原為「沒有任何缺欄 ⇒ 不跳確認框」**。Task 5.3 把顯示時機改成**主動**
   * （匯出前一律告訴使用者每個附帶欄各有幾筆可算）⇒ 「不缺就不跳」與 5.3 直接相斥。
   * 「防恆跳」之鑑別力改綁**唯一還說得通的空集合**：一個附帶欄都沒勾，就沒有東西可講。
   */
  it('⑤ 一個附帶欄都沒勾 ⇒ 不跳確認框（防「恆跳」而失去鑑別力）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    selectOnly([]);

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    expect(confirmMock).not.toHaveBeenCalled();
  });
});
