/**
 * ICRESULT_PAGING Task 2.3 page 整合（八案例；fixture＝**不含 summary_table** 之 light 報告＋summary_page{total:39346, rows:50}）：
 * ①表格 <tr>==51 且不讀 report.summary_table ②排序 ⇒ 打 /summary?sort_by&sort_order&offset=0 ③點列 ⇒ 打 /feature/{name}
 * ④初始 featureDetail=null ⇒「載入中」不 throw ⑤detail（含非空 rolling）⇒ 六圖渲染且 RollingICChart 收到序列
 * ⑥funnel 含 null ⇒ 不適用 ⑦切換特徵中 ⇒ 舊 detail 仍在 DOM＋overlay ⑧detail 失敗 ⇒ 重試按鈕、點擊再呼叫
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { ICFeatureDetail, ICFeatureInfo, ICReportLight } from '@/lib/types';

let urlParams = '';
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(urlParams),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/ic-analysis',
}));
vi.mock('html2canvas', () => ({ default: vi.fn() }));
vi.mock('recharts', async (orig) => {
  const actual = await orig<typeof import('recharts')>();
  return { ...actual, ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="rc">{children}</div> };
});
vi.mock('@/components/ic-analysis/RollingICChart', () => ({
  default: ({ series, featureName }: { series: Record<string, number[]> | null; featureName: string | null }) => (
    <div data-testid="rolling-chart" data-feature={featureName ?? ''} data-windows={series ? Object.keys(series).join(',') : ''} />
  ),
}));

import ICAnalysisPage from '@/app/ic-analysis/page';

const N = 39346;
const row = (i: number): ICFeatureInfo => ({ rank: i + 1, feature_name: `feat_${i}`, ic_mean: 0.01, icir: 0.5 } as ICFeatureInfo);
const summaryPage = (offset = 0, limit = 50, sort_by = 'icir', sort_order: 'asc' | 'desc' = 'desc') => ({
  total: N, offset, limit, sort_by, sort_order, result_revision: 1,
  rows: Array.from({ length: limit }, (_, i) => row(offset + i)),
});
const light: ICReportLight = {
  view: 'light',
  total_features: N,
  result_revision: 1,
  summary_page: summaryPage(),
  filter_log_funnel: { stage0_ingestion: { input: 39400, output: null }, feature_filter: { input: 39398, output: 39346 } },
  metadata: { symbol: 'BTCUSDT', timeframe: '1h', config_hash: 'h' },
  filter_log: {},
  analysis_status: 'degraded_full_sample',
  oos_guarantees: false,
} as ICReportLight;
const detail = (name: string): ICFeatureDetail => ({
  feature_name: name,
  summary_row: row(0),
  result_revision: 1,
  ic_decay: { horizons: [1, 2], ic_values: [0.1, 0.05] },
  quantile_returns: { quantiles: [1, 2], mean_returns: [0.1, 0.2] } as never,
  turnover_analysis: { quantile_turnover: 0.1 } as never,
  rolling_ic_series: { window_252: [0.1, 0.2], window_756: [0.1], window_1512: [] },
  grouped_ic: { by_year: { '2024': 0.1 } },
});

type Handler = (url: string, init?: RequestInit) => Promise<unknown> | unknown;
let handler: Handler;
const calls: string[] = [];

function installFetch(h: Handler) {
  handler = h;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(String(url));
    const body = await handler(String(url), init);
    if (body instanceof Error) return { ok: false, status: (body as Error & { status?: number }).status ?? 500, statusText: body.message, json: async () => ({ detail: body.message }) };
    return { ok: true, status: 200, json: async () => body };
  }));
}

const defaultHandler: Handler = (url) => {
  if (url.includes('/summary')) {
    const u = new URL(url);
    return summaryPage(Number(u.searchParams.get('offset') || 0), Number(u.searchParams.get('limit') || 50), u.searchParams.get('sort_by') || 'icir', (u.searchParams.get('sort_order') as 'asc' | 'desc') || 'desc');
  }
  if (url.includes('/feature/')) return detail(decodeURIComponent(url.split('/feature/')[1].split('?')[0]));
  if (url.includes('/result/')) return light;
  if (url.includes('/runs') || url.includes('/features/list') || url.includes('/presets') || url.includes('/indicators') || url.includes('/data-sources')) return [];
  return {};
};

describe('IC 分析頁 — ICRESULT_PAGING 整合', () => {
  beforeEach(() => {
    calls.length = 0;
    useICAnalysisStore.getState().resetReport();
    useICAnalysisStore.setState({ taskId: 'task-x', status: 'completed', error: null, selectedFeature: null, selectedFeatures: [] });
    useICAnalysisStore.getState().setReport(light);
    class MockWebSocket { close = vi.fn(); send = vi.fn(); onmessage = null; onerror = null; onclose = null; onopen = null; }
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
    installFetch(defaultHandler);
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); });

  it('①表格 <tr>==51（fixture 無 summary_table 仍渲染 50 列）＋ ⑥漏斗 null stage 顯示不適用', async () => {
    render(<ICAnalysisPage />);
    await waitFor(() => expect(document.querySelectorAll('tbody tr').length).toBe(50));
    expect(document.querySelectorAll('tr').length).toBeGreaterThanOrEqual(51);
    expect('summary_table' in light).toBe(false);
    expect(screen.getByTestId('funnel-not-applicable').textContent).toContain('stage0_ingestion');
  });

  it('②排序 ⇒ 重打 /summary 帶 sort_by／sort_order／offset=0', async () => {
    render(<ICAnalysisPage />);
    await waitFor(() => expect(document.querySelectorAll('tbody tr').length).toBe(50));
    calls.length = 0;
    fireEvent.click(document.querySelector('[data-sort-field="ic_mean"]')!);
    await waitFor(() => expect(calls.some((u) => u.includes('/summary') && u.includes('sort_by=ic_mean') && u.includes('sort_order=desc') && u.includes('offset=0'))).toBe(true));
  });

  it('③點列 ⇒ 打 /feature/{name}；⑤detail 到 ⇒ RollingICChart 收到序列（含 rolling）', async () => {
    vi.useFakeTimers();
    render(<ICAnalysisPage />);
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    fireEvent.click(screen.getByText('feat_3'));
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(calls.some((u) => u.includes('/feature/feat_3'))).toBe(true);
    const chart = screen.getByTestId('rolling-chart');
    expect(chart.getAttribute('data-feature')).toBe('feat_3');
    expect(chart.getAttribute('data-windows')).toContain('window_252');
  });

  it('④初始 featureDetail=null ⇒ 顯示「載入中」且不 throw', () => {
    installFetch((url) => (url.includes('/feature/') ? new Promise(() => undefined) : defaultHandler(url)));
    render(<ICAnalysisPage />);
    // 掛載即觸發 detail 拉取 ⇒ 初始為 loading 遮罩（或尚未觸發時的 initial 文案）；兩者皆為「載入中」且不 throw
    const charts = screen.getByTestId('ic-feature-charts');
    expect(charts.getAttribute('aria-busy') === 'true' || screen.queryByTestId('ic-feature-charts-initial') !== null).toBe(true);
    expect(charts.textContent).toContain('載入');
    expect(screen.queryByTestId('rolling-chart')?.getAttribute('data-windows') ?? '').toBe('');
  });

  it('⑦切換特徵中 ⇒ 舊 detail 仍在 DOM＋overlay，未清空', async () => {
    vi.useFakeTimers();
    let hold = false;
    installFetch((url) => {
      if (url.includes('/feature/') && hold) return new Promise(() => undefined);
      return defaultHandler(url);
    });
    render(<ICAnalysisPage />);
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(screen.getByTestId('rolling-chart').getAttribute('data-feature')).toBe('feat_0');
    hold = true;
    fireEvent.click(screen.getByText('feat_5'));
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(screen.getByTestId('ic-feature-charts-overlay')).toBeTruthy();
    expect(screen.getByTestId('rolling-chart').getAttribute('data-windows')).toContain('window_252'); // 舊 detail 仍在
  });

  it('⑧detail 失敗 ⇒ 重試按鈕，點擊再呼叫一次', async () => {
    vi.useFakeTimers();
    let fail = true;
    installFetch((url) => {
      if (url.includes('/feature/') && fail) return Object.assign(new Error('boom'), { status: 500 });
      return defaultHandler(url);
    });
    render(<ICAnalysisPage />);
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(screen.getByTestId('ic-feature-charts-error').textContent).toContain('boom');
    const before = calls.filter((u) => u.includes('/feature/')).length;
    fail = false;
    fireEvent.click(screen.getByTestId('ic-feature-charts-retry'));
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(calls.filter((u) => u.includes('/feature/')).length).toBe(before + 1);
    expect(screen.queryByTestId('ic-feature-charts-error')).toBeNull();
  });
});

describe('IC 分析頁 — URL limit clamp（B2 review R2 CODEX-R2-P2-01）', () => {
  beforeEach(() => {
    calls.length = 0;
    urlParams = 'limit=99999&page=1';
    useICAnalysisStore.getState().resetReport();
    useICAnalysisStore.setState({ taskId: 'task-x', status: 'completed', error: null });
    useICAnalysisStore.getState().setReport(light);
    class MockWebSocket { close = vi.fn(); send = vi.fn(); onmessage = null; onerror = null; onclose = null; onopen = null; }
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
    installFetch(defaultHandler);
  });
  afterEach(() => { urlParams = ''; cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); });

  it('?limit=99999 ⇒ clamp 為 500，請求 limit=500，可翻頁', async () => {
    render(<ICAnalysisPage />);
    await waitFor(() => expect(calls.some((u) => u.includes('/summary') && u.includes('limit=500'))).toBe(true));
    expect(useICAnalysisStore.getState().summaryParams.limit).toBe(500);
    expect(calls.some((u) => u.includes('limit=99999'))).toBe(false);
  });
});
