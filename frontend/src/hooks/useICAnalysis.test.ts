import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { ICAnalysisConfig } from '@/lib/types';

const config: ICAnalysisConfig = {
  features_path: '',
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'hash-a',
  mode: 'global',
  horizons: [1],
  thresholds: {
    ic_mean_min: 0.02,
    icir_min: 0.5,
    p_value_max: 0.05,
    correlation_threshold: 0.7,
  },
};

describe('useICAnalysis payload', () => {
  beforeEach(() => {
    vi.useRealTimers();
    useICAnalysisStore.setState({
      config,
      taskId: null,
      status: 'idle',
      error: null,
      featureFilter: {
        include_pattern: '',
        include_categories: [],
        include_data_sources: [],
        include_families: [],
        max_features: undefined,
      },
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ task_id: 'task-1', status: 'running' }),
      })
    );
    class MockWebSocket {
      close = vi.fn();
      send = vi.fn();
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      onclose: (() => void) | null = null;
    }
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('sends config_hash in analyze payload', async () => {
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.startAnalysis(config);
    });

    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.config_hash).toBe('hash-a');
    expect(body.feature_filter).toBeUndefined();
  });
});

describe('useICAnalysis progress errors', () => {
  class MockWebSocket {
    static instances: MockWebSocket[] = [];
    url: string;
    close = vi.fn();
    send = vi.fn();
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: (() => void) | null = null;
    onclose: (() => void) | null = null;

    constructor(url: string) {
      this.url = url;
      MockWebSocket.instances.push(this);
    }

    emitMessage(payload: unknown) {
      this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
    }

    emitClose() {
      this.onclose?.();
    }
  }

  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.useFakeTimers();
    useICAnalysisStore.setState({
      taskId: null,
      status: 'idle',
      progress: 0,
      currentStage: null,
      error: null,
      report: null,
    });
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('sets backend message from failed websocket payload', () => {
    const { result } = renderHook(() => useICAnalysis());

    act(() => {
      result.current.connectProgress('task-1');
    });
    act(() => {
      MockWebSocket.instances[0].emitMessage({
        event: 'progress',
        data: {
          status: 'failed',
          progress: 1,
          message: 'backend exploded',
        },
      });
    });

    expect(useICAnalysisStore.getState().status).toBe('failed');
    expect(useICAnalysisStore.getState().error).toBe('backend exploded');
  });

  it('clears stale connection error when a healthy progress message arrives', () => {
    const { result } = renderHook(() => useICAnalysis());

    act(() => {
      result.current.connectProgress('task-1');
    });
    // 模擬先前 transient「連線失敗」誤報殘留在 store
    act(() => {
      useICAnalysisStore.setState({ error: 'WebSocket 連線失敗' });
    });
    // 收到健康進度 → 應清除 stale error
    act(() => {
      MockWebSocket.instances[0].emitMessage({
        event: 'progress',
        data: { status: 'running', progress: 0.4, current_stage: 'ic_calculation' },
      });
    });

    expect(useICAnalysisStore.getState().error).toBeNull();
    expect(useICAnalysisStore.getState().currentStage).toBe('ic_calculation');
  });

  it('does not set a generic error on transient websocket onerror', () => {
    const { result } = renderHook(() => useICAnalysis());

    act(() => {
      result.current.connectProgress('task-1');
    });
    act(() => {
      MockWebSocket.instances[0].onerror?.();
    });

    // onerror 不再喊通用「連線失敗」；交給 onclose retry / poll fallback
    expect(useICAnalysisStore.getState().error).toBeNull();
  });

  it('sets poll error from failed task status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          task_id: 'task-1',
          status: 'failed',
          progress: 1,
          current_stage: 'failed',
          error: 'poll backend failed',
        }),
      })
    );
    const { result } = renderHook(() => useICAnalysis());

    await act(async () => {
      await result.current.fetchTaskStatus('task-1');
    });

    expect(useICAnalysisStore.getState().status).toBe('failed');
    expect(useICAnalysisStore.getState().error).toBe('poll backend failed');
  });

  it('falls back to polling after three websocket reconnects', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        task_id: 'task-1',
        status: 'failed',
        progress: 1,
        current_stage: 'failed',
        error: 'poll fallback failed',
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());

    act(() => {
      result.current.connectProgress('task-1');
    });

    for (let idx = 0; idx < 4; idx += 1) {
      act(() => {
        MockWebSocket.instances[idx].emitClose();
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });
    }

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/ic/task/task-1',
      expect.any(Object)
    );
    expect(useICAnalysisStore.getState().error).toBe('poll fallback failed');
  });
});
