/**
 * GAP-3 UX **Task 7.2** ② 之**呼叫端**半邊（SPEC mutation (c)：「呼叫端 `page.tsx` 漏傳某維度之 opts ⇒ ②紅」）。
 *
 * 為什麼要獨立一檔：`vi.mock` 是**檔案層 hoist**——`contractEnumWiring.test.tsx` 要真的呼叫
 * `buildEventContractRecords`（②之落檔層），本檔要把它換成間諜（②之傳參層），兩者不能共存於同一檔。
 * 兩檔皆命中 `--run contractEnumWiring` 之檔名選擇器。
 *
 * 🔴 **本檔驗的是「有沒有傳」，不是「傳了什麼值算得對不對」**：
 *    後者是 `contractEnumWiring.test.tsx` 之②（真的跑組裝器、比對落檔路徑）。
 *    分開的理由＝值相同的維度（`/search` 上只有一個可選值者）用值比對抓不到漏傳，
 *    只有「鍵在不在 opts 裡」抓得到。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { declareFromPreview, previewOf } from '@/test/lookaheadDeclarationTestUtils';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();
const buildRecordsMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDeclarationPreviewColumns: (...a: unknown[]) => depthMock(...a) };
});

vi.mock('@/lib/eventExport', async (orig) => {
  const actual = await orig<typeof import('@/lib/eventExport')>();
  return { ...actual, buildEventContractRecords: (...a: unknown[]) => buildRecordsMock(...a) };
});

const CASE_ROW = {
  symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00',
  positive_case: true, price_change: 3.2, future_1bar_return: 0.01,
} as unknown as CaseData;

beforeEach(() => {
  useSearchStore.setState({
    currentResult: {
      cases: [CASE_ROW],
      source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
  depthMock.mockResolvedValue(previewOf({ '1h': 2 }));
  buildRecordsMock.mockResolvedValue({
    records: [], skipped: [], n_cases: 0, n_records: 0,
    source_file_digest: 'a'.repeat(64), source_file_text: '[]',
    missing_by_horizon: {}, attached_horizons: [],
  });
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
  vi.stubGlobal('URL', { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} });
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  buildRecordsMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 7.2 ② 呼叫端 — /search page 之 opts 逐鍵帶著五維度', () => {
  it('🔴 五個 camelCase 維度鍵**全部**出現在 opts，且值來自 UI 狀態而非寫死預設', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    // 就緒訊號＝深度已回、揭露區已逐 tf 顯示（無篩選條件時不會出現 `export-lower-bound`）
    await declareFromPreview();
    // 改動「唯一在 /search 上有多個可選值」之維度 ⇒ 「有傳」與「寫死預設」在這一格可分辨
    fireEvent.change(screen.getByTestId('event-dim-control_kind'), { target: { value: 'user_labeled_other' } });
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));

    const opts = buildRecordsMock.mock.calls[0][1] as Record<string, unknown>;
    for (const key of ['scenario', 'controlKind', 'entryPriceSemantic', 'labelReturnMode', 'decisionOffsetBars']) {
      expect(opts[key], `page 未把 ${key} 傳給 buildEventContractRecords`).not.toBeUndefined();
    }
    expect(opts.controlKind).toBe('user_labeled_other');
  });

  it('🔴 under（R3 群集 A，三家一致之 P1 反例）：在 /search 把 k 改成 3 ⇒ 落檔仍為 0', async () => {
    // 原缺陷：`min`／`max` 只是提示，`fireEvent.change` 送得進去，而組裝器只擋 `k < 契約 min`
    // ⇒ UI 文案說「鎖定為 0」而匯出檔裡是 3。修法為 `readOnly` ＋ `onChange` clamp 兩層。
    render(<SearchPage />);
    await declareFromPreview();
    const k = screen.getByTestId('event-dim-decision_offset_bars') as HTMLInputElement;
    expect(k.readOnly).toBe(true);                       // 第一層：使用者改不動
    fireEvent.change(k, { target: { value: '3' } });     // 第二層：程式化設值也要被夾回
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    const opts = buildRecordsMock.mock.calls[0][1] as Record<string, unknown>;
    expect(opts.decisionOffsetBars).toBe(0);
  });

  it('🔴 over：使用者不動 UI ⇒ 五鍵仍逐一傳出，且值等於 Task 7.0 之預設（不得因此不傳）', async () => {
    render(<SearchPage />);
    // 就緒訊號＝深度已回、揭露區已逐 tf 顯示（無篩選條件時不會出現 `export-lower-bound`）
    await declareFromPreview();
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));

    const opts = buildRecordsMock.mock.calls[0][1] as Record<string, unknown>;
    expect(opts.scenario).toBe('C');
    expect(opts.controlKind).toBe('user_labeled_same_trigger');
    expect(opts.entryPriceSemantic).toBe('trigger_close');
    expect(opts.labelReturnMode).toBe('close_to_close');
    expect(opts.decisionOffsetBars).toBe(0);
  });
});
