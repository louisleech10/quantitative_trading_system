/**
 * ICPERF SPEC v5.87 Task 0.6 (h) L1b U2（諮詢 r165 收斂檔 C7）：IC 預過濾「最大因子數」越舊界 500 之值穿過頁面送出請求。
 * 元件層見 `FeatureFilterPanel.limits.test.tsx`；本檔驗頁面來源狀態 → HTTP 請求：預過濾套用 501 個 ⇒
 * 「套用後處理」之 POST /apply-transforms/{task} 請求體 selected_features 恰為該 501 個（後端消費見
 * tests/api/test_icperf_limit_l1b_ic_admission_route.py）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { FeatureListItem, ICReportLight } from '@/lib/types';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/ic-analysis',
}));
vi.mock('html2canvas', () => ({ default: vi.fn() }));
vi.mock('recharts', async (orig) => {
  const actual = await orig<typeof import('recharts')>();
  return { ...actual, ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="rc">{children}</div> };
});

import ICAnalysisPage from '@/app/ic-analysis/page';

const N_AVAILABLE = 600;
const available: FeatureListItem[] = Array.from({ length: N_AVAILABLE }, (_, i) => ({
  feature_name: `feat_${String(i).padStart(4, '0')}`,
  category: 'momentum',
  data_source: 'kline',
}));
const light = {
  view: 'light',
  total_features: N_AVAILABLE,
  result_revision: 1,
  summary_page: { total: 0, offset: 0, limit: 50, sort_by: 'icir', sort_order: 'desc', result_revision: 1, rows: [] },
  filter_log_funnel: {},
  metadata: { symbol: 'BTCUSDT', timeframe: '1h', config_hash: 'h' },
  filter_log: {},
} as unknown as ICReportLight;

const posted: { url: string; body: unknown }[] = [];

function installFetch() {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url);
    if (init?.method === 'POST') posted.push({ url: u, body: init.body ? JSON.parse(String(init.body)) : null });
    let body: unknown = {};
    if (u.includes('/deep-analysis/')) {
      body = { task_id: 'task-x', status: 'running' };
    } else if (u.includes('/apply-transforms/')) {
      body = { task_id: 'task-x', selected_feature_count: 501, transforms_applied: ['rank'], output_path: 'x', output_rows: 1, output_cols: 501 };
    } else if (u.includes('/summary')) {
      body = light.summary_page;
    } else if (u.includes('/result/')) {
      body = light;
    } else if (u.includes('/features/list')) {
      body = { total: N_AVAILABLE, features: available };
    } else if (u.includes('/runs') || u.includes('/presets') || u.includes('/indicators') || u.includes('/data-sources')) {
      body = [];
    }
    return { ok: true, status: 200, json: async () => body };
  }));
}

describe('IC 分析頁 L1b 預過濾 max_features 穿過請求 [rows:frontend/src/components/ic-analysis/FeatureFilterPanel.tsx:99:343dd1a589c8]', () => {
  beforeEach(() => {
    posted.length = 0;
    useICAnalysisStore.getState().resetReport();
    useICAnalysisStore.setState({ taskId: 'task-x', status: 'completed', error: null, selectedFeature: null, selectedFeatures: [] });
    useICAnalysisStore.getState().setReport(light);
    // 頁面自 /features/list 載入可選特徵（產品路徑，page.tsx 之 fetchAvailableFeatures effect）
    const cfg = useICAnalysisStore.getState().config;
    useICAnalysisStore.getState().setConfig({ ...cfg, symbol: 'BTCUSDT', timeframe: '1h', config_hash: 'h' });
    class MockWebSocket { close = vi.fn(); send = vi.fn(); onmessage = null; onerror = null; onclose = null; onopen = null; }
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
    installFetch();
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it('預過濾最大因子數 501 ⇒ 套用後處理請求帶 501 個 selected_features', async () => {
    render(<ICAnalysisPage />);
    await waitFor(() => expect(useICAnalysisStore.getState().availableFeatures).toHaveLength(N_AVAILABLE));
    fireEvent.click(screen.getByText('Feature 預過濾'));
    const input = screen.getByPlaceholderText('最大因子數') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '501' } });
    fireEvent.click(screen.getByText('套用預過濾'));
    await waitFor(() => expect(useICAnalysisStore.getState().selectedFeatures).toHaveLength(501));
    fireEvent.click(screen.getByText('套用後處理（501 個特徵）'));
    await waitFor(() => expect(posted.some((p) => p.url.includes('/apply-transforms/task-x'))).toBe(true));
    const req = posted.find((p) => p.url.includes('/apply-transforms/task-x'))!.body as { selected_features: string[] };
    expect(req.selected_features).toEqual(available.slice(0, 501).map((f) => f.feature_name));
    // 舊界 500 之 UI 約束：501 不得標溢位（刪 max 後綠）
    expect(input.hasAttribute('max')).toBe(false);
    expect(input.validity.rangeOverflow).toBe(false);
  });

  it('預過濾最大因子數 501 ⇒ 深度分析請求帶 501 個 selected_features（與後端 deep 消費端測試對接；審查 r166 CODEX-R166-P1-01）', async () => {
    render(<ICAnalysisPage />);
    await waitFor(() => expect(useICAnalysisStore.getState().availableFeatures).toHaveLength(N_AVAILABLE));
    fireEvent.click(screen.getByText('Feature 預過濾'));
    const input = screen.getByPlaceholderText('最大因子數') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '501' } });
    fireEvent.click(screen.getByText('套用預過濾'));
    await waitFor(() => expect(useICAnalysisStore.getState().selectedFeatures).toHaveLength(501));
    expect(useICAnalysisStore.getState().selectedFeaturesSource).toBe('manual');
    fireEvent.click(screen.getByText(/^分析 501 個因子/));
    await waitFor(() => expect(posted.some((p) => p.url.includes('/deep-analysis/task-x'))).toBe(true));
    const req = posted.find((p) => p.url.includes('/deep-analysis/task-x'))!.body as { selected_features: string[]; top_n: number };
    expect(req.selected_features).toEqual(available.slice(0, 501).map((f) => f.feature_name));
    expect(req.top_n).toBe(501);
    expect(input.hasAttribute('max')).toBe(false);
  });
});
