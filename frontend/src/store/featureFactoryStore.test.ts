import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useFeatureFactoryStore } from './featureFactoryStore';

function resetStore(): void {
  useFeatureFactoryStore.setState({
    batchTask: null,
    batchStartedAtMs: null,
    batchConnectionStatus: 'idle',
    batchConnectionMessage: null,
    error: null,
  });
}

function response(status: number, payload: Record<string, unknown>): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status >= 500 ? 'Server Error' : 'OK',
    json: async () => payload,
  } as Response;
}

describe('featureFactoryStore pollBatchStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetStore();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('continues polling past 600 running responses until completion', async () => {
    let calls = 0;
    const fetchMock = vi.fn(async () => {
      calls += 1;
      return response(200, {
        task_id: 'batch-long',
        status: calls <= 601 ? 'running' : 'completed',
        total: 1,
        completed: calls <= 601 ? 0 : 1,
        failed: 0,
        progress: calls <= 601 ? 0 : 1,
        results: calls <= 601 ? {} : { BTCUSDT: '/tmp/BTCUSDT_1h.h5' },
        errors: {},
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const promise = useFeatureFactoryStore.getState().pollBatchStatus('batch-long');
    for (let idx = 0; idx < 601; idx += 1) {
      await vi.advanceTimersByTimeAsync(1200);
    }
    await promise;

    const state = useFeatureFactoryStore.getState();
    expect(fetchMock).toHaveBeenCalledTimes(602);
    expect(state.error).toBeNull();
    expect(state.batchTask?.status).toBe('completed');
  });

  it('surfaces 5xx errors and keeps polling for the terminal status', async () => {
    let calls = 0;
    const fetchMock = vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        return response(503, { detail: 'temporary backend failure' });
      }
      return response(200, {
        task_id: 'batch-retry',
        status: 'completed',
        total: 1,
        completed: 1,
        failed: 0,
        progress: 1,
        results: { BTCUSDT: '/tmp/BTCUSDT_1h.h5' },
        errors: {},
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const promise = useFeatureFactoryStore.getState().pollBatchStatus('batch-retry');
    await vi.advanceTimersByTimeAsync(1200);
    await promise;

    const state = useFeatureFactoryStore.getState();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(state.error).toBe('temporary backend failure');
    expect(state.batchTask?.status).toBe('completed');
  });
});
