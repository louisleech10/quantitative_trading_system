/**
 * GAP-3 UX Task 4.1b 驗收（`--run eventExportDisclosureLegacy`；SPEC L1979–2005）。
 *
 * 把四件「使用者從未被告知」的事實顯示在匯出面板：scenario／lookahead 深度／purge 下界／control_kind。
 *
 * 🔴 四段**皆由實際設定導出，禁寫死**——本檔之反假綠設計：
 *   ①`control_kind` 之顯示值與**匯出檔實際寫入的值**逐字比對（不是比對一個字面常數）；
 *   ②深度改變 ⇒ 顯示跟著變（防硬編）；
 *   ③混 TF ⇒ **逐 tf 各一行**（B5 R1 群集 B：不得被 `Math.max` 塌成單一 scalar）。
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

const blobs: string[] = [];

function caseRow(over: Record<string, unknown> = {}): CaseData {
  return {
    symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00', positive_case: true,
    price_change: 3.2, future_1bar_return: 0.01,
    ...over,
  } as unknown as CaseData;
}

function seed(rows: CaseData[]) {
  useSearchStore.setState({
    currentResult: {
      cases: rows, source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
}

beforeEach(() => {
  seed([caseRow(), caseRow({ timestamp: '2024-01-01 01:00:00', positive_case: false })]);
  depthMock.mockResolvedValue(previewOf({ '1h': 0 }));
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
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 4.1b — 匯出時揭露每個選項在動什麼', () => {
  it('① 四段皆出現：scenario／lookahead 深度＋來源／purge 下界＋取較大者／control_kind', async () => {
    depthMock.mockResolvedValue(previewOf({ '1h': 7 }));
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());

    expect(screen.getByTestId('export-disclosure-scenario').textContent).toContain('scenario');
    // 深度那段須顯示 `lookahead_bars_declared` 之值（7），並說出來源
    const depthText = screen.getByTestId('export-disclosure-depth-1h').textContent ?? '';
    expect(depthText).toContain('7');
    expect(depthText).toContain('來源');
    // purge 那段須明示「取兩者較大者」（公式權威在 §D-3′-a(ii)，此處只揭露）
    const purgeText = screen.getByTestId('export-disclosure-purge-1h').textContent ?? '';
    expect(purgeText).toContain('purge');
    expect(purgeText).toContain('較大者');
    expect(screen.getByTestId('export-disclosure-control-kind').textContent).toContain('control_kind');
  });

  it('② `control_kind` 之顯示值 == 匯出檔實際寫入之值（防寫死漂移）', async () => {
    render(<SearchPage />);
    await declareFromPreview();

    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
    const records = (JSON.parse(blobs[0]) as { records: Record<string, unknown>[] }).records;
    const actual = String(records[0].control_kind);

    // 🔴 比對對象是**匯出檔裡的那個值**，不是一個字面常數——
    //    只比字面的話，改了組裝器而忘了改顯示（或反之）都不會紅。
    expect(screen.getByTestId('export-disclosure-control-kind').textContent).toContain(actual);
    // 同理，scenario 也逐字對上匯出檔
    expect(screen.getByTestId('export-disclosure-scenario').textContent)
      .toContain(String(records[0].scenario));
  });

  it('③ 深度顯示由實際回傳導出（換一個值 ⇒ 顯示跟著變；防硬編）', async () => {
    depthMock.mockResolvedValue(previewOf({ '1h': 3 }));
    const first = render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h').textContent).toContain('3'));
    first.unmount();

    depthMock.mockResolvedValue(previewOf({ '1h': 11 }));
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h').textContent).toContain('11'));
    expect(screen.getByTestId('export-disclosure-depth-1h').textContent).not.toContain('＝ 3 根');
  });

  it('④ 🔴 批內多 TF ⇒ **逐 tf 各一行**，不得塌成單一 scalar', async () => {
    seed([
      caseRow({ timeframe: '1h' }),
      caseRow({ timeframe: '12h', timestamp: '2024-01-01 01:00:00', positive_case: false }),
    ]);
    depthMock.mockResolvedValue(previewOf({ '1h': 72, '12h': 6 }));
    render(<SearchPage />);

    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());
    expect(screen.getByTestId('export-disclosure-depth-1h').textContent).toContain('72');
    expect(screen.getByTestId('export-disclosure-depth-12h').textContent).toContain('6');
    // purge 段同樣逐 tf（兩段都會被「塌成 max」弄壞，兩段都要驗）
    expect(screen.getByTestId('export-disclosure-purge-1h').textContent).toContain('72');
    expect(screen.getByTestId('export-disclosure-purge-12h').textContent).toContain('6');
  });

  it('⑤ 🔴 深度那段顯示的是 `lookahead_bars_declared`，**不是** `window.horizon_bars`（後者有 floor）', async () => {
    // 深度 0 ⇒ 真實深度顯示 0；若誤顯示 window.horizon_bars 會變成 1。
    depthMock.mockResolvedValue(previewOf({ '1h': 0 }));
    render(<SearchPage />);
    // R 重開：預設 0 不預填（0 須明填）⇒ 由使用者宣告 0 後，揭露才顯示
    await declareFromPreview({ '1h': 0 });
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());

    const text = screen.getByTestId('export-disclosure-depth-1h').textContent ?? '';
    expect(text).toContain('0');
    expect(text).not.toMatch(/深度（1h）＝\s*1\s*根/);
  });
});
