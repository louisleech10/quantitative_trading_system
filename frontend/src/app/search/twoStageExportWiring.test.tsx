/**
 * `G3-D2` **Task D3.1** 之**呼叫端**半邊（R1 閉合輪補；codex 6b 判 BLOCK）。
 *
 * 🔴 為什麼要獨立驗 render：R1 brief 之「我沒查的」第 2 列逐字寫
 * 「`/search` 頁 render 後兩顆匯出鈕真的 disabled 且理由可見」`NOT_RUN`。
 * `twoStageExport.test.ts` 只驗到**純函式**（`twoStageExportBlockReason`）與組裝器的一致性
 * ——那證明不了頁面真的用了它。**兩端都對但沒接上**正是本 repo 的「幽靈 feature_filter」病。
 *
 * 本檔測的是 DOM：選了 `two_stage` 而只有一段時，兩顆匯出鈕**真的**變 disabled、
 * 理由**真的**顯示，且點下去**不會**呼叫組裝器。
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
  // 🔴 只換 `buildEventContractRecords`（要驗「有沒有被呼叫」）；
  //    `twoStageExportBlockReason` 保持**真的**——本檔要驗頁面真的用了那一份判定。
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

/** 把 scenario 切成 two_stage（`two_stage` 於 D3.1 解灰，選得到才切得動）。 */
function selectTwoStage() {
  const sel = screen.getByTestId('event-dim-scenario') as HTMLSelectElement;
  const opt = Array.from(sel.querySelectorAll('option')).find((o) => o.value === 'two_stage');
  expect(opt, '`two_stage` 應出現在 /search 之 scenario 選項中（D3.1 解灰）').toBeTruthy();
  expect(opt!.disabled, '`two_stage` 解灰後不得是 disabled option').toBe(false);
  fireEvent.change(sel, { target: { value: 'two_stage' } });
}

/**
 * 填**兩段**條件 ⇒ 兩段皆非空。
 *
 * 🔴 頁面預設狀態下**兩段都是空的**：`searchParams.priceChange` 與
 * `negativeParams.priceChange` 初始皆為 `null`，`.filter()` 後兩段都成 `[]`。
 * 本檔第一版只填反例而紅——那不是碼錯，是我漏了第一段。
 */
function fillBothStages(pos = '5', neg = '-3') {
  fireEvent.change(screen.getByTestId('positive-field-priceChange'), { target: { value: pos } });
  fireEvent.click(screen.getByTestId('negative-section-header'));
  fireEvent.change(screen.getByTestId('negative-field-priceChange'), { target: { value: neg } });
}

describe('D3.1 呼叫端 — /search 之 two_stage 阻擋真的接到 DOM 上', () => {
  it('🔴 **P1-03 在真實 UI 上的樣子**：反例已啟用但一個值都沒填 ⇒ 第二段是空的 ⇒ 擋', async () => {
    // 這是頁面**預設**狀態（`negativeParams.enabled === true` 但所有值為 null）。
    // 修正前：`stages.length === 2` 成立即放行，第二段是空殼卻產出 digest。
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(true);
    });
    expect(screen.getByTestId('export-blocked-reason').textContent)
      .toContain('two_stage_requires_two_stages');
  });

  it('🔴 填了反例值 ⇒ 兩段皆非空 ⇒ 兩顆鈕可按、理由消失', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    fillBothStages();
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    });
    expect((screen.getByTestId('export-contract-csv') as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId('export-blocked-reason')).toBeNull();
  });

  it('🔴 關掉反例（只剩一段）⇒ 兩顆鈕 disabled、理由可見且含代號', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    fillBothStages();
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    });
    fireEvent.click(screen.getByTestId('negative-enabled-toggle'));
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(true);
    });
    expect((screen.getByTestId('export-contract-csv') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId('export-blocked-reason').textContent)
      .toContain('two_stage_requires_two_stages');
  });

  it('🔴 disabled 之下點擊 ⇒ **不呼叫**組裝器（disabled 不是只有樣式）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(true);
    });
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    fireEvent.click(screen.getByTestId('export-contract-csv'));
    expect(buildRecordsMock).not.toHaveBeenCalled();
  });

  it('🔴 over 向：scenario 不是 two_stage 時，反例空不空**都不影響**匯出', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId('export-blocked-reason')).toBeNull();
  });

  it('🔴 two_stage 之 opts 真的帶著兩段條件（不是頁面自己算完就丟掉）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    fillBothStages();
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    });
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    const opts = buildRecordsMock.mock.calls[0][1] as Record<string, unknown>;
    expect(opts.scenario).toBe('two_stage');
    const stages = opts.stageConditions as unknown[][];
    expect(stages).toHaveLength(2);
    expect(stages[0].length).toBeGreaterThan(0);
    expect(stages[1].length).toBeGreaterThan(0);   // 🔴 第二段非空——P1-03 之正面驗收
  });
});

describe('D3.1 R1 閉合 — 反例選 BETWEEN 時第二段仍須非空（`CODEX-R1-P1-03` ②）', () => {
  it('🔴 反例改 BETWEEN 並只填 range ⇒ 第二段非空、可匯出', async () => {
    // 🔴 修正前：`negativeStageConditions` 只讀 `negativeParams.priceChange`，
    //    而 BETWEEN 之值住 `negativeRangeValues` ⇒ 整段被 filter 成 `[]`，
    //    第二段成空殼（正例那一支有處理 BETWEEN，我複製時漏了——組法不對稱）。
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    fireEvent.change(screen.getByTestId('positive-field-priceChange'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('negative-section-header'));
    fireEvent.change(screen.getByTestId('negative-op-priceChange'), { target: { value: 'BETWEEN' } });
    fireEvent.change(screen.getByTestId('negative-range-min-priceChange'), { target: { value: '-9' } });
    fireEvent.change(screen.getByTestId('negative-range-max-priceChange'), { target: { value: '-1' } });

    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    });
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    const stages = (buildRecordsMock.mock.calls[0][1] as Record<string, unknown>).stageConditions as unknown[][];
    expect(stages).toHaveLength(2);
    expect(stages[1].length).toBeGreaterThan(0);
    // 第二段之值必須是 range 的兩端，不是 `null`
    expect((stages[1][0] as { value: unknown }).value).toEqual([-9, -1]);
  });

  it('🔴 over 向：反例選 BETWEEN 但**沒填** range ⇒ 第二段仍空 ⇒ 擋', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-event-dimensions')).toBeTruthy());
    await declareFromPreview();
    selectTwoStage();
    fireEvent.change(screen.getByTestId('positive-field-priceChange'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('negative-section-header'));
    fireEvent.change(screen.getByTestId('negative-op-priceChange'), { target: { value: 'BETWEEN' } });
    await waitFor(() => {
      expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(true);
    });
    expect(screen.getByTestId('export-blocked-reason').textContent)
      .toContain('two_stage_requires_two_stages');
  });
});
