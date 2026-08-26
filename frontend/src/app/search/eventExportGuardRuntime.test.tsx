/**
 * `D-004 A-021` 驗收⑤ — 下界守衛之 **page runtime 執行期計數**（`--run eventExportGuardRuntime`）。
 *
 * 為什麼要有這一條：`A-021(c)` 保留 `withExportLowerBoundGuard` 之 `proceed` 包裹，
 * 而**包裹的價值是結構保證**——只驗述詞（`exportAllowedByLowerBoundState` 回 false）
 * 抓不到「有人把包裹拆掉、改寫成裸 `if (…) return;`」。
 * 故本檔在 `/search` **真的 render、真的按匯出鍵**，數 `buildEventContractRecords` 的呼叫次數。
 *
 * 🔴 **誠實邊界（主委自陳，已寫進 review brief）**：
 *    「拆成裸 `if (…) return;`」若寫得正確（守衛仍在所有 `await` 之前），**執行期行為相同**
 *    ⇒ 本檔會維持綠，抓到它的是 `lookaheadDepthLock.page.test.ts` 之③
 *    （「該函式內每一個 `await` 都落在 `proceed` 之內」）。兩條分工不同、缺一不可：
 *    ③ 擋形狀退化，本檔擋行為退化（例如守衛被搬到 `await` 之後）。
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

vi.mock('@/lib/eventExport', async (orig) => {
  const actual = await orig<typeof import('@/lib/eventExport')>();
  return { ...actual, buildEventContractRecords: (...a: unknown[]) => buildRecordsMock(...a) };
});

function seed() {
  useSearchStore.setState({
    currentResult: {
      cases: [
        { symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00', positive_case: true,
          price_change: 3.2, future_2bar_return: 1.1 },
        { symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 01:00:00', positive_case: false,
          price_change: -1.0, future_2bar_return: -0.3 },
      ] as unknown as CaseData[],
      source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
}

/** 加一條篩選條件（讓下界查詢真的被觸發）。 */
function addCondition(column: string, value: string) {
  fireEvent.click(screen.getByTestId('export-filter-add'));
  fireEvent.change(screen.getByTestId('export-filter-column-0'), { target: { value: column } });
  fireEvent.change(screen.getByTestId('export-filter-value-0'), { target: { value } });
}

beforeEach(() => {
  seed();
  buildRecordsMock.mockResolvedValue({
    records: [], skipped: [], n_cases: 0, n_records: 0,
    source_file_digest: 'a'.repeat(64), source_file_text: '[]',
    missing_by_horizon: {}, attached_horizons: [], lookahead_bars_declared: {},
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

describe('A-021 驗收⑤ — page runtime：未就緒時匯出組裝器一次都不被呼叫', () => {
  it('⑤a `error`（深度算不出來）⇒ `buildEventContractRecords` 呼叫次數 == 0', async () => {
    depthMock.mockRejectedValue(new Error('boom'));
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-error')).toBeTruthy());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);
  });

  it('⑤b `pending`（深度還沒回來）⇒ 呼叫次數 == 0', async () => {
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

  it('⑤d 🔴 R1 三家一致 P1：**無篩選條件**且深度 in-flight ⇒ 呼叫次數 == 0', async () => {
    // 這是主委「拿不到 ⇒ 擋」之宣稱被攻破的那條：舊版只在有條件時打 `pending`，
    // 無條件批次在 API 飛的那段時間狀態仍是初始的 `unconstrained`＝可匯出，
    // 於是產出 `lookahead_bars_declared: {}` 的檔（三家各自實跑 calls=1）。
    let release: ((v: unknown) => void) | undefined;
    depthMock.mockImplementation(() => new Promise((res) => { release = res; }));
    render(<SearchPage />);          // 🔴 **不加任何篩選條件**

    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);
    release?.({ depth_by_timeframe: { '1h': 0 } });
  });

  it('⑤e 🔴 R1 `GROK-R1-P1-01`：清掉條件後第二輪 in-flight ⇒ 不得沿用**過期** map', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');
    await waitFor(() => expect(screen.getByTestId('export-lower-bound')).toBeTruthy());

    // 第二輪：清掉條件 ⇒ 重新查；讓它卡住不 resolve
    let release: ((v: unknown) => void) | undefined;
    depthMock.mockImplementation(() => new Promise((res) => { release = res; }));
    fireEvent.click(screen.getByTestId('export-filter-remove-0'));

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-pending')).toBeTruthy());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);   // 不得拿舊的 {1h:2} 去匯出
    release?.({ depth_by_timeframe: { '1h': 0 } });
  });

  it('⑤f 🔴 R1 `CODEX-R1-P1-02`：深度回傳未覆蓋本批週期（空 map／缺鍵／非法值）⇒ 擋', async () => {
    for (const bad of [{}, { '12h': 0 }, { '1h': -1 }, { '1h': 1.5 }, { '1h': '0' }]) {
      cleanup();
      buildRecordsMock.mockClear();
      (alert as unknown as ReturnType<typeof vi.fn>).mockClear?.();
      depthMock.mockResolvedValue({ depth_by_timeframe: bad });
      render(<SearchPage />);
      await waitFor(() => expect(screen.getByTestId('export-lower-bound-error')).toBeTruthy());
      fireEvent.click(screen.getByTestId('export-gap3-events'));
      await waitFor(() => expect(alert).toHaveBeenCalled());
      expect(buildRecordsMock, `bad=${JSON.stringify(bad)}`).toHaveBeenCalledTimes(0);
    }
  });

  it('⑤g 🔴 R2 `CODEX-R2-P1-01`：結果集讀不到週期（`timeframes` 為空）⇒ 擋，且看得見原因', async () => {
    // codex 實跑反例：舊版在 `timeframes.length === 0` **直接 return** ⇒ 狀態停在初始的
    // `unconstrained`＝可匯出；`windowHorizonBarsFor` 會在 proceed 內拋錯，而按鈕是 `void` 呼叫
    // ⇒ 使用者按了什麼都沒發生、也沒有任何訊息（錯被吞掉）。
    useSearchStore.setState({
      currentResult: {
        cases: [
          { symbol: 'ETHUSDT', timeframe: '', timestamp: '2024-01-01 00:00:00', positive_case: true },
        ] as unknown as CaseData[],
        source_file_text: '[]', source_file_digest: 'a'.repeat(64),
      } as unknown as SearchResultData,
      isLoading: false, error: null,
    });
    // searchParams.timeframe 預設 '12h' 會補上 ⇒ 這裡要連那個也拿掉才構造得出空集合
    render(<SearchPage />);
    fireEvent.change(screen.getByDisplayValue('12小時'), { target: { value: '' } });

    await waitFor(() => expect(screen.getByTestId('export-lower-bound-error')).toBeTruthy());
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect(buildRecordsMock).toHaveBeenCalledTimes(0);
  });

  it('⑤c 對照組：就緒 ⇒ 呼叫次數 == 1（否則「恆擋」也會讓 ⑤a／⑤b 綠）', async () => {
    depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
    render(<SearchPage />);
    addCondition('future_2bar_return', '0.5');

    await waitFor(() => expect(depthMock).toHaveBeenCalled());
    // 🔴 送出鍵刻意保持可按（B4 教訓：disabled 的話這個 click 什麼都沒觸發、恆綠）
    expect((screen.getByTestId('export-gap3-events') as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByTestId('export-gap3-events'));
    await waitFor(() => expect(buildRecordsMock).toHaveBeenCalledTimes(1));
    expect(alert).not.toHaveBeenCalled();
  });
});
