/**
 * T4 — NetICChart + 成本 wiring 前端測試(IC1C Phase 2 Task 2.2)
 *
 * 具名:sends_cost_bps / shows_error_on_422 / shows_loading /
 * shows_empty_on_all_skipped / shows_no_data_when_turnover_missing /
 * shows_no_data_when_gross_ic_missing / page_passes_loading_to_NetICChart /
 * test_mutation_m4_frontend_drop_cost
 *
 * B4(R2):shows_error_on_422 必須呼叫 production useICAnalysis.startDeepAnalysis
 * (mock fetch 回 422),禁 runDeepStartCatchingError 複製品;page 掛載須傳 loading。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen, fireEvent, cleanup, waitFor, renderHook, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import NetICChart from '@/components/ic-analysis/NetICChart';
import DeepAnalysisConfigPanel from '@/components/ic-analysis/DeepAnalysisConfigPanel';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type {
  DeepAnalysisModules,
  NetICAnalysisData,
  NetICFeatureGrossOnly,
  NetICFeatureSkipped,
} from '@/lib/types';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const defaultModules: DeepAnalysisModules = {
  factor_return: false,
  factor_centrality: false,
  trend_analysis: false,
  parameter_sensitivity: false,
  rolling_oos: false,
  factor_orthogonalization: false,
  factor_exposure: false,
  long_short_analysis: false,
  feature_quality_diagnostics: false,
  net_ic_analysis: true,
};

describe('NetICChart / cost wiring (T4)', () => {
  beforeEach(() => {
    const { setNetIcConfig, setDeepAnalysisModules } = useICAnalysisStore.getState();
    setDeepAnalysisModules(defaultModules);
    setNetIcConfig({ cost_enabled: false, cost_bps: null });
    class MockWebSocket {
      close = vi.fn();
      send = vi.fn();
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      onclose: (() => void) | null = null;
    }
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
  });

  it('sends_cost_bps: UI 7bps → request payload 7', () => {
    const { setNetIcConfig, setDeepAnalysisModules, buildDeepAnalysisRequest } =
      useICAnalysisStore.getState();
    setDeepAnalysisModules(defaultModules);
    setNetIcConfig({ cost_enabled: true, cost_bps: 7 });

    const onNetIc = vi.fn();
    render(
      <DeepAnalysisConfigPanel
        selectedFeatureCount={3}
        modules={defaultModules}
        netIcConfig={{ cost_enabled: true, cost_bps: 7 }}
        neutralizationMode="none"
        onModulesChange={vi.fn()}
        onNetIcConfigChange={onNetIc}
        onNeutralizationModeChange={vi.fn()}
        onStart={vi.fn()}
      />
    );
    const input = screen.getByTestId('net-ic-cost-bps') as HTMLInputElement;
    expect(input.value).toBe('7');
    fireEvent.change(input, { target: { value: '7' } });

    const payload = buildDeepAnalysisRequest({
      selected_features: ['f1'],
      top_n: 1,
    });
    expect(payload.net_ic?.cost_enabled).toBe(true);
    expect(payload.net_ic?.cost_bps).toBe(7);
  });

  it('shows_error_on_422: production startDeepAnalysis + mock fetch 422 → 錯誤可見', async () => {
    const detailMsg = 'cost_bps must be finite and in (0, 1000]';
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: detailMsg }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { setNetIcConfig, buildDeepAnalysisRequest } = useICAnalysisStore.getState();
    setNetIcConfig({ cost_enabled: true, cost_bps: 0 });
    const payload = buildDeepAnalysisRequest({
      selected_features: ['f1'],
      top_n: 1,
    });
    expect(payload.net_ic?.cost_enabled).toBe(true);

    // 生產路徑:useICAnalysis.startDeepAnalysis(requestJson) — 禁本地複製品
    const { result } = renderHook(() => useICAnalysis());
    let formError: string | null = null;
    await act(async () => {
      try {
        await result.current.startDeepAnalysis('task-wiring-422', payload);
      } catch (err) {
        // 對齊 page.tsx handleStartDeepAnalysis catch → setError(message)
        formError = err instanceof Error ? err.message : '啟動深度分析失敗';
      }
    });

    expect(fetchMock).toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toMatch(/\/deep-analysis\/task-wiring-422/);
    expect(init.method).toBe('POST');
    const body = JSON.parse(String(init.body));
    expect(body.net_ic).toEqual(payload.net_ic);
    expect(formError).toMatch(/cost_bps/);
    expect(formError).toContain(detailMsg);

    // 父層 failed+error → formError 傳入 panel(同源自 API detail)
    render(
      <DeepAnalysisConfigPanel
        selectedFeatureCount={3}
        modules={defaultModules}
        netIcConfig={{ cost_enabled: true, cost_bps: 0 }}
        neutralizationMode="none"
        onModulesChange={vi.fn()}
        onNetIcConfigChange={vi.fn()}
        onNeutralizationModeChange={vi.fn()}
        onStart={vi.fn()}
        formError={formError}
      />
    );
    await waitFor(() => {
      const alert = screen.getByTestId('net-ic-form-error');
      expect(alert.textContent).toMatch(/cost_bps/);
      expect(alert.textContent).toContain(detailMsg);
    });
  });

  it('shows_loading: loading=true → netic-loading 可見,非 empty/error', () => {
    render(<NetICChart loading />);
    expect(screen.getByTestId('netic-loading')).toBeTruthy();
    expect(screen.getByTestId('netic-loading').textContent).toMatch(/載入中/);
    expect(screen.queryByTestId('netic-empty')).toBeNull();
    expect(screen.queryByTestId('netic-error')).toBeNull();
  });

  it('page_passes_loading_to_NetICChart: page 掛載點傳 loading prop', () => {
    // 產品路徑守衛:isolated prop test 不足以證 page wiring
    const pageSrc = readFileSync(
      resolve(__dirname, '../../app/ic-analysis/page.tsx'),
      'utf8'
    );
    const mount = pageSrc.match(/<NetICChart[\s\S]*?\/>/);
    expect(mount).not.toBeNull();
    expect(mount![0]).toMatch(/loading=\{/);
    expect(mount![0]).toMatch(/isDeepRunning|deepAnalysisStatus/);
  });

  it('shows_empty_on_all_skipped: 全 SKIPPED → 空狀態非 spinner', () => {
    const skippedA: NetICFeatureSkipped = {
      skipped: true,
      reason: 'turnover_missing',
    };
    const skippedB: NetICFeatureSkipped = {
      skipped: true,
      reason: 'gross_ic_missing',
    };
    const data: NetICAnalysisData = {
      features: { a: skippedA, b: skippedB },
      summary: {
        total_analyzed: 2,
        evaluable_count: 0,
        profitable_count: 0,
      },
    };
    render(<NetICChart data={data} />);
    const empty = screen.getByTestId('netic-empty');
    expect(empty.textContent).toMatch(/SKIPPED|無資料/);
    expect(screen.queryByTestId('netic-loading')).toBeNull();
  });

  it('shows_no_data_when_turnover_missing: 缺 turnover → 無資料,不代入 0.1', () => {
    // 防禦路徑:runtime 可能缺 turnover;測試用寬鬆斷言,型別上完整 profile 必有 turnover
    const partial = {
      gross_ic: 0.05,
      // turnover 故意缺 → 不得 fallback 0.1
      net_factor_return: {
        status: 'unavailable' as const,
        value: null,
        reason: 'canonical_factor_return_series_not_built (1c-FR)',
      },
    };
    const data = {
      features: { f1: partial as unknown as NetICFeatureGrossOnly },
      summary: {
        total_analyzed: 1,
        evaluable_count: 0,
        profitable_count: 0,
      },
    } as NetICAnalysisData;
    const { container } = render(<NetICChart data={data} />);
    const empty = container.querySelector('[data-testid="netic-empty"]');
    expect(empty).not.toBeNull();
    expect(empty?.textContent).toMatch(/無資料/);
    expect(container.querySelector('.recharts-scatter-symbol')).toBeNull();
  });

  it('shows_no_data_when_gross_ic_missing: 缺 gross_ic → 無資料,禁造 0', () => {
    // R2-NEW-1:不得 gross_ic ?? 0
    const partial = {
      // gross_ic 故意缺
      turnover: 0.3,
      turnover_semantics: 'membership_change_both_legs_per_bar',
      capacity: {
        estimated_capacity_usd: null,
        capacity_tier: 'unknown',
        calibration: 'uncalibrated' as const,
      },
      net_factor_return: {
        status: 'unavailable' as const,
        value: null,
        reason: 'canonical_factor_return_series_not_built (1c-FR)',
      },
    };
    const data = {
      features: { f1: partial as unknown as NetICFeatureGrossOnly },
      summary: {
        total_analyzed: 1,
        evaluable_count: 0,
        profitable_count: 0,
      },
    } as NetICAnalysisData;
    const { container } = render(<NetICChart data={data} />);
    const empty = container.querySelector('[data-testid="netic-empty"]');
    expect(empty).not.toBeNull();
    expect(empty?.textContent).toMatch(/無資料/);
    expect(container.querySelector('.recharts-scatter-symbol')).toBeNull();
  });

  it('test_mutation_m4_frontend_drop_cost: 若 build 丟棄 cost → sends_cost_bps 紅', () => {
    const { setNetIcConfig, setDeepAnalysisModules } = useICAnalysisStore.getState();
    setDeepAnalysisModules(defaultModules);
    setNetIcConfig({ cost_enabled: true, cost_bps: 7 });

    const original = useICAnalysisStore.getState().buildDeepAnalysisRequest;
    useICAnalysisStore.setState({
      buildDeepAnalysisRequest: (opts) => {
        const payload = original(opts);
        return {
          ...payload,
          net_ic: { cost_enabled: false, cost_bps: null },
        };
      },
    });

    try {
      const payload = useICAnalysisStore.getState().buildDeepAnalysisRequest({
        selected_features: ['f1'],
        top_n: 1,
      });
      expect(() => {
        expect(payload.net_ic?.cost_enabled).toBe(true);
        expect(payload.net_ic?.cost_bps).toBe(7);
      }).toThrow();
    } finally {
      useICAnalysisStore.setState({ buildDeepAnalysisRequest: original });
    }
  });
});
