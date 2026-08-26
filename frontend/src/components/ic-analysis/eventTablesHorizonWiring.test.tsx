/**
 * GAP-3 UX Task 4.2（前端側）驗收（`--run eventTablesHorizonWiring`）。
 *
 * 後端早已參數化（`case_import_service.py` 傳 `horizons=tuple(req.horizons)`），
 * **缺的一直是前端接線**：`EventTablesPanel` 呼叫 `analyzeEventImport(importId)` 不帶 body
 * ⇒ 後端恆用預設 `[1, 2, 4]`，使用者在 IC 面板選的 horizon 對事件後報酬表完全沒作用。
 *
 * 🔴 斷言對象＝**送出去的 request body**（執行期），不是讀原始碼有沒有那個字串。
 */
import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EventTablesPanel, { sanitizeHorizons } from '@/components/ic-analysis/EventTablesPanel';
import type { EventAnalyzeResponse } from '@/lib/types';

const analyzeMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, analyzeEventImport: (...a: unknown[]) => analyzeMock(...a) };
});

const RESP = {
  import_id: 'imp-1',
  summary: { n_input: 2, n_aligned: 2, n_align_failures: 0, n_train: 1, n_test: 1, n_purged: 0 },
  align_failures: [],
  tables: {
    event_forward_return_table: { capability_status: 'ok', horizons: [1, 3, 7], primary_macro: {}, sensitivity_micro: {} },
    binary_discrimination_table: { capability_status: 'not_computed', reason: 'x' },
    all_bars_evaluation: { capability_status: 'not_computed', reason: 'x' },
  },
  event_timestamps: [],
  event_timestamps_ic_seconds: [],
} as unknown as EventAnalyzeResponse;

beforeEach(() => {
  analyzeMock.mockResolvedValue(RESP);
});

afterEach(() => {
  cleanup();
  analyzeMock.mockReset();
});

describe('Task 4.2 — 前端把選定之 horizon 集合送進事件表 API', () => {
  it('① 選 [1,3,7] ⇒ POST body 恰為該陣列（不是後端預設 [1,2,4]）', async () => {
    render(<EventTablesPanel importId="imp-1" horizons={[1, 3, 7]} />);
    await waitFor(() => expect(analyzeMock).toHaveBeenCalled());
    expect(analyzeMock.mock.calls[0]).toEqual(['imp-1', { horizons: [1, 3, 7] }]);
  });

  it('② 未指定 ⇒ 送空 body（沿用後端預設；不得自己在前端複製一份 [1,2,4]）', async () => {
    render(<EventTablesPanel importId="imp-1" />);
    await waitFor(() => expect(analyzeMock).toHaveBeenCalled());
    expect(analyzeMock.mock.calls[0]).toEqual(['imp-1', {}]);
  });

  it('③ fail-closed：空／重複／非正整數之輸入不得送出無意義請求', async () => {
    // 純函式層先釘住判準（每一種壞輸入各一組，避免只驗一種而實作寫成特例）
    expect(sanitizeHorizons([])).toBeUndefined();
    expect(sanitizeHorizons([0, -1, 1.5, NaN])).toBeUndefined();
    expect(sanitizeHorizons([3, 1, 3, 1])).toEqual([1, 3]);
    expect(sanitizeHorizons([2, 1, 4])).toEqual([1, 2, 4]);
    expect(sanitizeHorizons(undefined)).toBeUndefined();

    // 接線層：壞輸入 ⇒ 與「沒給」同一條路徑
    render(<EventTablesPanel importId="imp-1" horizons={[0, -3]} />);
    await waitFor(() => expect(analyzeMock).toHaveBeenCalled());
    expect(analyzeMock.mock.calls[0]).toEqual(['imp-1', {}]);
  });

  it('④ 改變 horizon 集合 ⇒ 真的重打 API（否則使用者改了選擇卻看到舊表）', async () => {
    const view = render(<EventTablesPanel importId="imp-1" horizons={[1, 2]} />);
    await waitFor(() => expect(analyzeMock).toHaveBeenCalledTimes(1));
    view.rerender(<EventTablesPanel importId="imp-1" horizons={[1, 2, 4]} />);
    await waitFor(() => expect(analyzeMock).toHaveBeenCalledTimes(2));
    expect(analyzeMock.mock.calls[1]).toEqual(['imp-1', { horizons: [1, 2, 4] }]);

    // 對照：同一集合（順序不同）**不**重打——否則每次 render 都會打一次
    view.rerender(<EventTablesPanel importId="imp-1" horizons={[4, 2, 1]} />);
    await new Promise((r) => setTimeout(r, 0));
    expect(analyzeMock).toHaveBeenCalledTimes(2);
  });
});
