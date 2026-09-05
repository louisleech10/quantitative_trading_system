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
    onopen: (() => void) | null = null;

    constructor(url: string) {
      this.url = url;
      MockWebSocket.instances.push(this);
    }

    emitMessage(payload: unknown) {
      this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
    }

    emitOpen() {
      this.onopen?.();
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

  it('G3-D11：任務在訂閱前已 failed ⇒ 連上時拉一次現況即收斂為 failed，不停在執行中', async () => {
    vi.useRealTimers();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ task_id: 'task-1', status: 'failed', progress: 1, error: 'feature_coverage_unknown_legacy_run: …' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());

    act(() => {
      result.current.connectProgress('task-1');
    });
    expect(useICAnalysisStore.getState().status).not.toBe('failed');   // 尚未收到任何訊息
    await act(async () => {
      MockWebSocket.instances[0].emitOpen();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalled();
    expect(String(fetchMock.mock.calls[0][0])).toContain('/task/task-1');
    expect(useICAnalysisStore.getState().status).toBe('failed');
    expect(useICAnalysisStore.getState().error).toContain('feature_coverage_unknown_legacy_run');
    expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
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

// ═══════════════════════════════════════════════════════════════════════════
// `G3-D2` B-D4 **R1 閉合** — WS 快樂路徑之揭露欄回填
//
// 🔴 三家全員之 P1（`CODEX-R1-P1-02`／`COMPOSER-R1-P1-01`／`GROK-R1-P1-01`）：
//    WS 是**生產預設通道**，輪詢只在重連失敗 ≥3 次後才啟動；原版 `ws.onmessage` 之
//    `completed` 分支只 `fetchResult`（設 report、不碰揭露欄）⇒ 掃描矩陣與兩上界
//    **在主路徑上永遠到不了畫面**。與 `7904c0dd` 要修的「幽靈功能」同病，
//    層次從「props 沒傳」移到「store 沒刷新」。
// ═══════════════════════════════════════════════════════════════════════════

describe('G3-D2 B-D4 R1 閉合 — WS 快樂路徑必須 hydrate eventScanDisclosure', () => {
  class MockWS {
    static instances: MockWS[] = [];
    url: string;
    close = vi.fn();
    send = vi.fn();
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onopen: (() => void) | null = null;

    constructor(url: string) {
      this.url = url;
      MockWS.instances.push(this);
    }

    emitMessage(payload: unknown) {
      this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
    }
  }

  const TASK_STATUS_WITH_SCAN = {
    task_id: 'task-scan', status: 'completed', progress: 1,
    decision_offset_bars_capability: 'available',
    decision_offset_bars_record_values: [0, 2],
    decision_offset_bars_analysis: 0,
    k_max_feasible_at_h: 119, h_max_feasible_at_k: 1518,
    k_bound_status: 'bounded', h_bound_status: 'bounded',
    bounds_scope_symbol: 'ETHUSDT', bounds_scope_excluded_events: 0,
    event_label_scan: {
      scan_total: 2, scan_done: 2, capability: 'available', reason: null,
      scan_results: [
        { k: 0, h: 1, capability: 'available', n_events: 3, analysis_alignment_receipt_hash: 'a', ic_summary: {} },
        { k: 0, h: 2, capability: 'available', n_events: 3, analysis_alignment_receipt_hash: 'b', ic_summary: {} },
      ],
    },
  };

  beforeEach(() => {
    MockWS.instances = [];
    useICAnalysisStore.setState({
      taskId: null, status: 'idle', progress: 0, currentStage: null,
      error: null, report: null, eventScanDisclosure: null,
    });
    vi.stubGlobal('WebSocket', MockWS as unknown as typeof WebSocket);
  });

  afterEach(() => { vi.unstubAllGlobals(); });

  it('🔴 WS `completed` ⇒ 揭露欄被 hydrate（原版只 fetchResult ⇒ 永遠是 null）', async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => (String(url).includes('/task/')
        ? TASK_STATUS_WITH_SCAN
        : { summary: {} }),
    }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());

    act(() => { result.current.connectProgress('task-scan'); });
    await act(async () => {
      MockWS.instances[0].emitMessage({
        event: 'progress',
        data: { status: 'completed', progress: 1, stage: 'completed' },
      });
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    });

    const d = useICAnalysisStore.getState().eventScanDisclosure;
    expect(d, 'WS 完成後揭露欄不得為 null').not.toBeNull();
    expect(d?.k_max_feasible_at_h).toBe(119);
    expect(d?.event_label_scan?.scan_results).toHaveLength(2);
    // 對照：report 也還是有拉（`fetchTaskStatus` 於 completed 分支會呼叫 `fetchResult`）
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes('/result/'))).toBe(true);
  });

  it('🔴 WS `progress` 帶 `scan_done/scan_total` ⇒ 進行中就看得到格數（不必等終態）', () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({}) })));
    const { result } = renderHook(() => useICAnalysis());
    act(() => { result.current.connectProgress('task-scan'); });
    act(() => {
      MockWS.instances[0].emitMessage({
        event: 'progress',
        data: { status: 'running', progress: 0.5, stage: 'event_label_scan', scan_done: 3, scan_total: 9 },
      });
    });
    const scan = useICAnalysisStore.getState().eventScanDisclosure?.event_label_scan;
    expect(scan?.scan_done).toBe(3);
    expect(scan?.scan_total).toBe(9);
    // 🔴 **不猜上界**：進行中只有格數，其餘欄位不得被填假值
    expect(useICAnalysisStore.getState().eventScanDisclosure?.k_max_feasible_at_h ?? null).toBeNull();
  });

  it('🔴 `CODEX-R1-P2-03`：WS `failed` ⇒ 清掉上一次的揭露欄（不得把舊矩陣掛在失敗任務上）', () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({}) })));
    useICAnalysisStore.getState().setEventScanDisclosure({ k_max_feasible_at_h: 42 });
    const { result } = renderHook(() => useICAnalysis());
    act(() => { result.current.connectProgress('task-scan'); });
    act(() => {
      MockWS.instances[0].emitMessage({
        event: 'progress',
        data: { status: 'failed', progress: 1, message: 'boom' },
      });
    });
    expect(useICAnalysisStore.getState().eventScanDisclosure).toBeNull();
    expect(useICAnalysisStore.getState().error).toBe('boom');
  });
});

describe('G3-D2 B-D4 R1 閉合 — 新任務啟動即清掉上一次的揭露欄', () => {
  it('🔴 `COMPOSER-R1-P2-01`：`startAnalysis` 之後、首次 /task 回應之前，不得殘留舊上界', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true, json: async () => ({ task_id: 'task-new', status: 'pending' }),
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', class { constructor() {} close() {} } as unknown as typeof WebSocket);
    // 前一次分析留下的值
    useICAnalysisStore.getState().setEventScanDisclosure({
      k_max_feasible_at_h: 999, k_bound_status: 'bounded',
    });
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.startAnalysis({
        ...useICAnalysisStore.getState().config,
        symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'hash-a',
      });
    });
    expect(useICAnalysisStore.getState().eventScanDisclosure).toBeNull();
    vi.unstubAllGlobals();
  });
});

describe('G3-D2 B-D4 R2 閉合 — codex 三條 P2', () => {
  class MockWS2 {
    static instances: MockWS2[] = [];
    url: string; close = vi.fn(); send = vi.fn();
    onmessage: ((e: MessageEvent) => void) | null = null;
    onerror: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onopen: (() => void) | null = null;
    constructor(url: string) { this.url = url; MockWS2.instances.push(this); }
    emitMessage(payload: unknown) { this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent); }
  }

  beforeEach(() => {
    MockWS2.instances = [];
    useICAnalysisStore.setState({
      taskId: null, status: 'idle', progress: 0, currentStage: null,
      error: null, report: null, eventScanDisclosure: null,
    });
    vi.stubGlobal('WebSocket', MockWS2 as unknown as typeof WebSocket);
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('🔴 `CODEX-R2-P2-01`：running 之 `/task` 回應**不得**把 WS 已併入的格數清成 null', async () => {
    // running 回應：**沒有** event_label_scan（那要跑完才有），只有頂層 scan_done/scan_total
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => (String(url).includes('/task/')
        ? { task_id: 't', status: 'running', progress: 0.4, scan_done: 4, scan_total: 9 }
        : {}),
    }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { result.current.connectProgress('t'); });

    // 先由 WS 併入 3/9
    act(() => {
      MockWS2.instances[0].emitMessage({
        event: 'progress',
        data: { status: 'running', progress: 0.3, scan_done: 3, scan_total: 9 },
      });
    });
    expect(useICAnalysisStore.getState().eventScanDisclosure?.event_label_scan?.scan_done).toBe(3);

    // 再讓 /task 的 running 回應到達（順序交錯）——格數只能前進，不得被清成 null
    await act(async () => {
      await result.current.fetchTaskStatus('t');
    });
    const scan = useICAnalysisStore.getState().eventScanDisclosure?.event_label_scan;
    expect(scan, '/task running 回應把掃描進度清掉了').not.toBeNull();
    expect(scan?.scan_total).toBe(9);
    expect(scan?.scan_done).toBe(4);
  });

  it('🔴 `CODEX-R2-P2-02`：`/task` 失敗但 `/result` 成功 ⇒ 報告仍在，且**說出**揭露欄沒拿到', async () => {
    const fetchMock = vi.fn(async (url: string) => (String(url).includes('/task/')
      ? { ok: false, statusText: 'Internal Server Error', json: async () => ({ detail: 'boom-task' }) }
      : { ok: true, json: async () => ({ summary: { ok: true } }) }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { result.current.connectProgress('t'); });
    await act(async () => {
      MockWS2.instances[0].emitMessage({
        event: 'progress', data: { status: 'completed', progress: 1 },
      });
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    });
    expect(useICAnalysisStore.getState().report).not.toBeNull();
    const err = useICAnalysisStore.getState().error ?? '';
    expect(err, '降級必須說出來，不得靜默').toContain('揭露欄');
    expect(err).toContain('boom-task');
  });

  it('🔴 `CODEX-R2-P2-02` 之另一半：兩端都失敗 ⇒ 顯示錯誤（不得是 unhandled rejection）', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false, statusText: 'Internal Server Error', json: async () => ({ detail: 'boom-both' }),
    }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { result.current.connectProgress('t'); });
    await act(async () => {
      MockWS2.instances[0].emitMessage({
        event: 'progress', data: { status: 'completed', progress: 1 },
      });
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    });
    expect(useICAnalysisStore.getState().error).toContain('boom-both');
  });
});
