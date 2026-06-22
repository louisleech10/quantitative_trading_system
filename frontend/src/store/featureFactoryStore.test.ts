import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  LAST_BATCH_TASK_ID_KEY,
  readLastBatchTaskId,
  useFeatureFactoryStore,
} from './featureFactoryStore';

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

describe('featureFactoryStore lastBatchTaskId persistence', () => {
  beforeEach(() => {
    resetStore();
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
    resetStore();
  });

  it('persists batch task id when polling reaches a terminal status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        response(200, {
          task_id: 'batch-persist-1',
          batch_id: 'batch-persist-1',
          status: 'completed',
          total: 1,
          completed: 1,
          failed: 0,
          progress: 1,
          results: { BTCUSDT: '/tmp/BTCUSDT_1h.h5' },
          errors: {},
        }),
      ),
    );

    await useFeatureFactoryStore.getState().pollBatchStatus('batch-persist-1');

    expect(window.localStorage.getItem(LAST_BATCH_TASK_ID_KEY)).toBe('batch-persist-1');
    expect(readLastBatchTaskId()).toBe('batch-persist-1');
  });

  it('exposes persisted id after store reset to simulate page reload', async () => {
    window.localStorage.setItem(LAST_BATCH_TASK_ID_KEY, 'batch-reload-42');
    resetStore();

    expect(useFeatureFactoryStore.getState().batchTask).toBeNull();
    expect(readLastBatchTaskId()).toBe('batch-reload-42');
  });
});

describe('featureFactoryStore batch layer field staleness', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    resetStore();
  });

  function seedRunningBatch(overrides: Record<string, unknown> = {}): void {
    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-layer',
        batch_id: 'batch-layer',
        status: 'running',
        total: 2,
        completed: 0,
        failed: 0,
        progress: 0,
        queued: 2,
        concurrent_symbols: 1,
        memory_sanity_failed: false,
        eta_seconds: 0,
        resume_available: false,
        current_symbol: 'BTCUSDT',
        current_timeframe: '1h',
        current_stage: 'layer_3',
        stage_progress: 0.5,
        current_rss_mb: 512,
        output_paths: [],
        per_item_rss: [],
        last_item_metrics: null,
        results: {},
        browse_task_ids: {},
        errors: {},
        ...overrides,
      },
      batchStartedAtMs: Date.now(),
    });
  }

  it('clears layer fields when symbol changes without fresh layer payload', () => {
    seedRunningBatch();

    useFeatureFactoryStore.getState().applyBatchEvent({
      current_symbol: 'ETHUSDT',
      current_timeframe: '1h',
    });

    const state = useFeatureFactoryStore.getState();
    expect(state.batchTask?.current_symbol).toBe('ETHUSDT');
    expect(state.batchTask?.current_stage).toBeNull();
    expect(state.batchTask?.stage_progress).toBeNull();
    expect(state.batchTask?.current_rss_mb).toBeNull();
  });

  it('clears layer fields when payload omits them on running updates', () => {
    seedRunningBatch();

    useFeatureFactoryStore.getState().applyBatchEvent({
      progress: 0.1,
    });

    const state = useFeatureFactoryStore.getState();
    expect(state.batchTask?.current_stage).toBeNull();
    expect(state.batchTask?.stage_progress).toBeNull();
    expect(state.batchTask?.current_rss_mb).toBeNull();
  });

  it('clears layer fields when status is not running', () => {
    seedRunningBatch();

    useFeatureFactoryStore.getState().applyBatchEvent({
      status: 'completed',
      completed: 2,
      progress: 1,
      current_stage: 'layer_7',
      stage_progress: 1,
      current_rss_mb: 999,
    });

    const state = useFeatureFactoryStore.getState();
    expect(state.batchTask?.status).toBe('completed');
    expect(state.batchTask?.current_stage).toBeNull();
    expect(state.batchTask?.stage_progress).toBeNull();
    expect(state.batchTask?.current_rss_mb).toBeNull();
  });
});

describe('featureFactoryStore completionQueue source', () => {
  afterEach(() => {
    useFeatureFactoryStore.setState({ completionQueue: [], batchTask: null });
  });

  it('enqueueCompletion defaults source to single', () => {
    useFeatureFactoryStore.getState().enqueueCompletion({
      symbol: 'BTCUSDT',
      timeframe: '12h',
      config_hash: 'cfg_a',
    });
    expect(useFeatureFactoryStore.getState().completionQueue).toEqual([{
      symbol: 'BTCUSDT',
      timeframe: '12h',
      config_hash: 'cfg_a',
      source: 'single',
    }]);
  });

  it('clears retention_pending when payload includes empty retention_pending key', () => {
    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-r',
        batch_id: 'batch-r',
        status: 'running',
        total: 1,
        completed: 0,
        failed: 0,
        progress: 0,
        retention_pending: [{
          symbol: 'BTCUSDT',
          timeframe: '12h',
          config_hash: 'hash_old',
          state: 'pending',
        }],
      },
      batchStartedAtMs: Date.now(),
    });

    useFeatureFactoryStore.getState().applyBatchEvent({ retention_pending: [] });

    expect(useFeatureFactoryStore.getState().batchTask?.retention_pending).toEqual([]);
  });
});

const API_BASE = 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

function bulkDeleteUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/bulk-delete`;
}

function runsUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs`;
}

function orphansUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/orphans`;
}

function orphansCleanUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/orphans/clean`;
}

function retentionPendingUrl(batchId: string): string {
  return `${API_BASE}${API_PREFIX}/batch/${encodeURIComponent(batchId)}/retention/pending`;
}

describe('featureFactoryStore bulkDeleteRuns', () => {
  beforeEach(() => {
    resetStore();
    useFeatureFactoryStore.setState({ runs: [], batchTask: null });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('POSTs deduped runs to bulk-delete, then refreshes runs and retention pending', async () => {
    const bulkResponse = {
      deleted: [{ symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_a', bytes: 100 }],
      failed: [],
      skipped: [],
    };
    const fetchCalls: Array<{ url: string; init?: RequestInit }> = [];
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      fetchCalls.push({ url, init });
      if (url === bulkDeleteUrl() && init?.method === 'POST') {
        return response(200, bulkResponse);
      }
      if (url === runsUrl()) {
        return response(200, []);
      }
      if (url === retentionPendingUrl('batch-42')) {
        return response(200, { pending: [] });
      }
      return response(404, {});
    });
    vi.stubGlobal('fetch', fetchMock);

    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-42',
        batch_id: 'batch-42',
        status: 'completed',
        total: 1,
        completed: 1,
        failed: 0,
        progress: 1,
        results: {},
        errors: {},
      },
    });

    const result = await useFeatureFactoryStore.getState().bulkDeleteRuns([
      { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_a' },
      { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_a' },
      { symbol: 'ETHUSDT', timeframe: '4h', config_hash: 'hash_b' },
    ]);

    expect(result.ok).toBe(true);
    const bulkCall = fetchCalls.find((call) => call.url === bulkDeleteUrl());
    expect(bulkCall).toBeDefined();
    expect(bulkCall?.init?.method).toBe('POST');
    const body = JSON.parse(String(bulkCall?.init?.body)) as {
      runs: Array<{ symbol: string; timeframe: string; config_hash: string }>;
    };
    expect(body.runs).toEqual([
      { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_a' },
      { symbol: 'ETHUSDT', timeframe: '4h', config_hash: 'hash_b' },
    ]);
    expect(fetchCalls.some((call) => call.url === runsUrl())).toBe(true);
    expect(fetchCalls.some((call) => call.url === retentionPendingUrl('batch-42'))).toBe(true);
  });
});

describe('featureFactoryStore scanOrphans', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('GETs the orphans scan endpoint', async () => {
    const scanPayload = {
      orphans: [{
        kind: 'registry_without_leaf',
        symbol: 'ADAUSDT',
        timeframe: '4h',
        config_hash: 'orphan_cfg',
        leaf_kind: 'features',
      }],
      count: 1,
    };
    const fetchMock = vi.fn(async (url: string) => {
      if (url === orphansUrl()) {
        return response(200, scanPayload);
      }
      return response(404, {});
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await useFeatureFactoryStore.getState().scanOrphans();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data).toEqual(scanPayload);
    }
    expect(fetchMock).toHaveBeenCalledWith(orphansUrl());
  });
});

describe('featureFactoryStore cleanOrphans', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('POSTs dry_run flag to orphans clean endpoint', async () => {
    const cleanPayload = {
      orphans: [],
      cleaned_registry: 0,
      cleaned_leaves: 0,
      errors: [],
      dry_run: true,
    };
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === orphansCleanUrl() && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { dry_run: boolean };
        return response(200, { ...cleanPayload, dry_run: body.dry_run });
      }
      if (url === runsUrl()) {
        return response(200, []);
      }
      return response(404, {});
    });
    vi.stubGlobal('fetch', fetchMock);

    const dryResult = await useFeatureFactoryStore.getState().cleanOrphans(true);
    expect(dryResult.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      orphansCleanUrl(),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ dry_run: true }),
      }),
    );

    fetchMock.mockClear();

    const liveResult = await useFeatureFactoryStore.getState().cleanOrphans(false);
    expect(liveResult.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      orphansCleanUrl(),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ dry_run: false }),
      }),
    );
    expect(fetchMock).toHaveBeenCalledWith(runsUrl());
  });
});
