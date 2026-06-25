import { describe, expect, it, vi, beforeEach } from 'vitest';
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
    useICAnalysisStore.setState({
      config,
      taskId: null,
      status: 'idle',
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

  it('sends config_hash in analyze payload', async () => {
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.startAnalysis(config);
    });

    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.config_hash).toBe('hash-a');
  });
});
