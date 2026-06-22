import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import BatchRetentionPanel from '../BatchRetentionPanel';
import RunRetentionDialog from '../RunRetentionDialog';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import type { BatchRetentionItem } from '@/lib/types';

const API_BASE = 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';
const BATCH_ID = 'batch-ret-1';

const pendingItems: BatchRetentionItem[] = [
  {
    symbol: 'BTCUSDT',
    timeframe: '12h',
    config_hash: 'hash_btc',
    state: 'pending',
    hdf5_path: '/tmp/BTCUSDT_12h.h5',
  },
  {
    symbol: 'ETHUSDT',
    timeframe: '12h',
    config_hash: 'hash_eth',
    state: 'pending',
    hdf5_path: '/tmp/ETHUSDT_12h.h5',
  },
];

function seedBatchPending(items: BatchRetentionItem[] = pendingItems): void {
  useFeatureFactoryStore.setState({
    batchTask: {
      task_id: BATCH_ID,
      batch_id: BATCH_ID,
      status: 'running',
      total: 2,
      completed: 1,
      failed: 0,
      progress: 0.5,
      retention_pending: items,
    },
    batchConnectionStatus: 'connected',
  });
}

function resetStore(): void {
  useFeatureFactoryStore.setState({
    batchTask: null,
    batchConnectionStatus: 'idle',
    completionQueue: [],
  });
}

function batchDecisionUrl(symbol: string, timeframe: string, configHash: string): string {
  return `${API_BASE}${API_PREFIX}/batch/${BATCH_ID}/retention/${symbol}/${timeframe}/${configHash}`;
}

function bulkRetentionUrl(): string {
  return `${API_BASE}${API_PREFIX}/batch/${BATCH_ID}/retention/bulk`;
}

function deleteRunUrl(symbol: string, timeframe: string, configHash: string): string {
  return `${API_BASE}${API_PREFIX}/runs/${symbol}/${timeframe}/${configHash}`;
}

describe('BatchRetentionPanel', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('renders pending retention items in a single expandable panel', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }),
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    expect(await screen.findByTestId('batch-retention-panel')).toBeInTheDocument();
    expect(screen.getByTestId('batch-retention-item-BTCUSDT')).toBeInTheDocument();
    expect(screen.getByTestId('batch-retention-item-ETHUSDT')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Retain / })).toHaveLength(2);
    expect(screen.queryAllByRole('dialog')).toHaveLength(0);
  });

  it('calls batch retention endpoint on retain', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/retention/pending')) {
        return { ok: true, json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }) };
      }
      if (url === batchDecisionUrl('BTCUSDT', '12h', 'hash_btc')) {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({ decision: 'retain' });
        return {
          ok: true,
          json: async () => ({
            batch_id: BATCH_ID,
            symbol: 'BTCUSDT',
            timeframe: '12h',
            config_hash: 'hash_btc',
            state: 'retained',
          }),
        };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    fireEvent.click(within(screen.getByTestId('batch-retention-panel')).getByRole('button', { name: 'Retain BTCUSDT' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        batchDecisionUrl('BTCUSDT', '12h', 'hash_btc'),
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('calls batch retention endpoint on discard (not deleteRun DELETE /runs)', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/retention/pending')) {
        return { ok: true, json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }) };
      }
      if (url === batchDecisionUrl('ETHUSDT', '12h', 'hash_eth')) {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({ decision: 'discard' });
        expect(url).not.toBe(deleteRunUrl('ETHUSDT', '12h', 'hash_eth'));
        return {
          ok: true,
          json: async () => ({
            batch_id: BATCH_ID,
            symbol: 'ETHUSDT',
            timeframe: '12h',
            config_hash: 'hash_eth',
            state: 'discarded',
          }),
        };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    fireEvent.click(within(screen.getByTestId('batch-retention-panel')).getByRole('button', { name: 'Discard ETHUSDT' }));

    await waitFor(() => {
      const decisionCalls = fetchMock.mock.calls.filter(
        ([url, init]) => typeof url === 'string'
          && url.includes('/retention/')
          && (init as RequestInit | undefined)?.method === 'POST',
      );
      expect(decisionCalls).toHaveLength(1);
      const [url, init] = decisionCalls[0] as [string, RequestInit];
      expect(url).toBe(batchDecisionUrl('ETHUSDT', '12h', 'hash_eth'));
      expect(url).not.toContain('/runs/');
      expect(init.method).toBe('POST');
      expect(fetchMock.mock.calls.some(
        ([calledUrl, calledInit]) => calledUrl === deleteRunUrl('ETHUSDT', '12h', 'hash_eth')
          && (calledInit as RequestInit | undefined)?.method === 'DELETE',
      )).toBe(false);
    });
  });

  it('does not render when pending queue is empty', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batch_id: BATCH_ID, pending: [] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending([]);
    const { container } = render(<BatchRetentionPanel />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByTestId('batch-retention-panel')).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it('keeps multiple items in one panel and blocks batch completionQueue modal', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }),
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    useFeatureFactoryStore.setState({
      completionQueue: [{
        symbol: 'BTCUSDT',
        timeframe: '12h',
        config_hash: 'hash_btc',
        source: 'batch',
      }],
    });

    render(
      <>
        <BatchRetentionPanel />
        <RunRetentionDialog />
      </>,
    );

    expect(await screen.findByTestId('batch-retention-panel')).toBeInTheDocument();
    expect(screen.getAllByTestId(/batch-retention-item-/)).toHaveLength(2);
    expect(screen.queryAllByRole('dialog')).toHaveLength(0);
    expect(screen.queryByText('保留這次產生的 Run？')).not.toBeInTheDocument();
  });

  it('retain all calls bulk endpoint and clears pending on success', async () => {
    let pendingState = [...pendingItems];
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/retention/pending')) {
        return { ok: true, json: async () => ({ batch_id: BATCH_ID, pending: pendingState }) };
      }
      if (url === bulkRetentionUrl() && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { decision: string; runs: unknown[] };
        expect(body.decision).toBe('retain');
        expect(body.runs).toHaveLength(2);
        pendingState = [];
        return {
          ok: true,
          json: async () => ({
            results: pendingItems.map((item) => ({
              symbol: item.symbol,
              timeframe: item.timeframe,
              config_hash: item.config_hash,
              status: 'succeeded',
              state: 'retained',
            })),
          }),
        };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    fireEvent.click(await screen.findByRole('button', { name: '全部保留' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        bulkRetentionUrl(),
        expect.objectContaining({ method: 'POST' }),
      );
    });
    await waitFor(() => {
      expect(useFeatureFactoryStore.getState().batchTask?.retention_pending ?? []).toHaveLength(0);
    });
  });

  it('multi-select discard shows confirm dialog and calls bulk discard', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/retention/pending')) {
        return { ok: true, json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }) };
      }
      if (url === bulkRetentionUrl() && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as {
          decision: string;
          runs: Array<{ symbol: string }>;
        };
        expect(body.decision).toBe('discard');
        expect(body.runs).toEqual([
          expect.objectContaining({ symbol: 'BTCUSDT' }),
        ]);
        return {
          ok: true,
          json: async () => ({
            results: [{
              symbol: 'BTCUSDT',
              timeframe: '12h',
              config_hash: 'hash_btc',
              status: 'succeeded',
              state: 'discarded',
            }],
          }),
        };
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    fireEvent.click(await screen.findByLabelText('選取 BTCUSDT'));
    fireEvent.click(screen.getByRole('button', { name: '丟棄選取' }));

    const dialog = await screen.findByRole('dialog', { name: /確認丟棄/ });
    expect(within(dialog).getByText(/BTCUSDT\/12h/)).toBeInTheDocument();
    expect(within(dialog).queryByText(/ETHUSDT/)).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '確認丟棄' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        bulkRetentionUrl(),
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('select all checks all pending items', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batch_id: BATCH_ID, pending: pendingItems }),
    });
    vi.stubGlobal('fetch', fetchMock);

    seedBatchPending();
    render(<BatchRetentionPanel />);

    fireEvent.click(await screen.findByLabelText('全選待決項目'));
    expect(screen.getByLabelText('選取 BTCUSDT')).toBeChecked();
    expect(screen.getByLabelText('選取 ETHUSDT')).toBeChecked();
  });
});
