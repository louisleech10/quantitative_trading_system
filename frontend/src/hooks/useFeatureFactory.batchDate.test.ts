import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

import { useFeatureFactory } from './useFeatureFactory';

function response(status: number, payload: Record<string, unknown>): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status >= 200 && status < 300 ? 'OK' : 'Server Error',
    json: async () => payload,
  } as Response;
}

function resetStore(): void {
  useFeatureFactoryStore.setState({
    batchTask: null,
    batchStartedAtMs: null,
    batchConnectionStatus: 'idle',
    batchConnectionMessage: null,
    error: null,
  });
}

describe('useFeatureFactory startBatchGeneration date payload', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('sends start_date and end_date when provided', async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      return response(200, { task_id: 'batch-with-dates', status: 'pending', total: 2 });
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useFeatureFactory());

    await act(async () => {
      await result.current.startBatchGeneration({
        symbols: ['BTCUSDT', 'ETHUSDT'],
        timeframe: '12h',
        start_date: '2025-01-01',
        end_date: '2025-06-21',
      });
    });

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.start_date).toBe('2025-01-01');
    expect(body.end_date).toBe('2025-06-21');
  });

  it('omits undefined dates when not provided', async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      return response(200, { task_id: 'batch-no-dates', status: 'pending', total: 2 });
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useFeatureFactory());

    await act(async () => {
      await result.current.startBatchGeneration({
        symbols: ['BTCUSDT', 'ETHUSDT'],
        timeframe: '12h',
      });
    });

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.start_date).toBeUndefined();
    expect(body.end_date).toBeUndefined();
  });
});
