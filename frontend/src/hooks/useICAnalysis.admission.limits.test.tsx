/**
 * ICPERF SPEC v5.87 Task 0.6 (h) ⑤ IC 分析啟動准入（L1b；諮詢 r165 收斂檔 C3、C6）之前端驗收：同一公開契約之前端同批。
 * ① 拒收 detail 帶 need_bytes／have_bytes ⇒ 錯誤訊息顯示「需要 X GB、可用 Y GB」（不只新增 JSON 鍵）。
 * ② 任務狀態 pending 帶 wait_reason ⇒ store.waitReason ⇒ 頁面顯示排隊原因，且排隊中可取消（沿既有取消鈕）。
 * GB＝2^30 位元組，小數兩位。
 */
import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { ICAnalysisConfig } from '@/lib/types';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/ic-analysis',
}));
vi.mock('html2canvas', () => ({ default: vi.fn() }));

import ICAnalysisPage from '@/app/ic-analysis/page';

const GiB = 2 ** 30;
const config: ICAnalysisConfig = {
  features_path: '',
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'hash-a',
  mode: 'global',
  horizons: [1],
  thresholds: { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, correlation_threshold: 0.7 },
};

function stubFetch(handler: (url: string, init?: RequestInit) => { ok: boolean; status: number; body: unknown }) {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const r = handler(String(url), init);
    return { ok: r.ok, status: r.status, statusText: r.ok ? 'OK' : 'Bad Request', json: async () => r.body };
  }));
}

beforeEach(() => {
  vi.useRealTimers();
  useICAnalysisStore.setState({ config, taskId: null, status: 'idle', error: null });
  class MockWebSocket { close = vi.fn(); send = vi.fn(); onmessage = null; onerror = null; onclose = null; onopen = null; }
  vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('IC 准入 need／have 與排隊顯示 [rows:api/routes/ic_analysis.py:89:f1971768baf1,api/routes/ic_analysis.py:87:119e531ebe6f]', () => {
  it('① 400 記憶體需求逾預算（detail 帶 need／have）⇒ 錯誤訊息含需要與可用之 GB', async () => {
    // reason 字面不寫進 frontend（契約字面只經後端；前端顯示不讀 reason，見 tests/api/test_gap3_ic_feature_cap.py）
    stubFetch(() => ({
      ok: false, status: 400,
      body: { detail: { message: '估算記憶體超過本機預算',
        need_bytes: 7 * GiB, have_bytes: 1 * GiB, measurement_source: 'darwin_vm_snapshot',
        components: [{ name: 'matrix_f64', bytes: 7 * GiB }] } },
    }));
    const { result } = renderHook(() => useICAnalysis());
    let err = '';
    await act(async () => {
      await result.current.startAnalysis(config).catch((e: unknown) => { err = e instanceof Error ? e.message : String(e); });
    });
    expect(err).toContain('估算記憶體超過本機預算');
    expect(err).toContain('需要 7.00 GB');
    expect(err).toContain('可用 1.00 GB');
  });

  it('② pending＋wait_reason ⇒ store.waitReason', async () => {
    stubFetch((url) => (url.includes('/task/task-q')
      ? { ok: true, status: 200, body: { task_id: 'task-q', status: 'pending', progress: 0,
        wait_reason: { need_bytes: 2 * GiB, have_bytes: 1 * GiB, measurement_source: 'psutil' } } }
      : { ok: true, status: 200, body: {} }));
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => { await result.current.fetchTaskStatus('task-q'); });
    expect(useICAnalysisStore.getState().status).toBe('pending');
    expect(useICAnalysisStore.getState().waitReason).toEqual({ need_bytes: 2 * GiB, have_bytes: 1 * GiB, measurement_source: 'psutil' });
  });

  it('③ 頁面顯示排隊原因且可取消', () => {
    stubFetch((url) => ({ ok: true, status: 200,
      body: url.includes('/features/list') ? { total: 0, features: [] } : (url.includes('/task/') ? { task_id: 'task-q', status: 'pending', progress: 0 } : []) }));
    useICAnalysisStore.setState({ taskId: 'task-q', status: 'pending',
      waitReason: { need_bytes: 2 * GiB, have_bytes: 1 * GiB, measurement_source: 'psutil' } });
    render(<ICAnalysisPage />);
    const el = screen.getByTestId('ic-task-wait-reason');
    expect(el.textContent).toContain('排隊中');
    expect(el.textContent).toContain('需要 2.00 GB');
    expect(el.textContent).toContain('可用 1.00 GB');
    expect(screen.getByTestId('ic-task-cancel')).toBeTruthy();
  });
});
