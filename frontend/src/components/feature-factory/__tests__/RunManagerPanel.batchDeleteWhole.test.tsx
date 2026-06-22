import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { RunInfo } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

import RunManagerPanel from '../RunManagerPanel';

const API_BASE = 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

function bulkDeleteUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/bulk-delete`;
}

function runsUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs`;
}

function response(status: number, payload: Record<string, unknown>) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

const baseRun = (overrides: Partial<RunInfo> = {}): RunInfo => ({
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'cfg_a',
  active: false,
  browse_task_id: 'browse_BTCUSDT_12h_cfg_a',
  browse_ready: true,
  created_at: '2026-06-01T00:00:00+00:00',
  size_bytes: 1024,
  ...overrides,
});

function resetStore(): void {
  useFeatureFactoryStore.setState({
    runs: [],
    runsLoading: false,
    runsError: null,
  });
}

describe('RunManagerPanel delete whole batch (real store)', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('delete whole batch B does not pollute selection from batch A', async () => {
    const batchARuns = [
      baseRun({
        symbol: 'BTCUSDT',
        config_hash: 'hash_a1',
        batch_id: 'batch-A',
        batch_alias: 'wave-a',
        browse_task_id: 'browse_BTCUSDT_12h_hash_a1',
      }),
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'hash_a2',
        batch_id: 'batch-A',
        batch_alias: 'wave-a',
        browse_task_id: 'browse_ETHUSDT_12h_hash_a2',
      }),
    ];
    const batchBRuns = [
      baseRun({
        symbol: 'SOLUSDT',
        config_hash: 'hash_b1',
        batch_id: 'batch-B',
        batch_alias: 'wave-b',
        browse_task_id: 'browse_SOLUSDT_12h_hash_b1',
      }),
      baseRun({
        symbol: 'XRPUSDT',
        config_hash: 'hash_b2',
        batch_id: 'batch-B',
        batch_alias: 'wave-b',
        browse_task_id: 'browse_XRPUSDT_12h_hash_b2',
      }),
    ];
    const allRuns = [...batchARuns, ...batchBRuns];

    const fetchCalls: Array<{ url: string; init?: RequestInit }> = [];
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      fetchCalls.push({ url, init });
      if (url === runsUrl()) {
        return response(200, allRuns);
      }
      if (url === bulkDeleteUrl() && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as {
          runs: Array<{ symbol: string; config_hash: string }>;
        };
        return response(200, {
          deleted: body.runs.map((run) => ({
            symbol: run.symbol,
            timeframe: '12h',
            config_hash: run.config_hash,
            bytes: 1024,
          })),
          failed: [],
          skipped: [],
        });
      }
      return response(404, {});
    });
    vi.stubGlobal('fetch', fetchMock);

    useFeatureFactoryStore.setState({ runs: allRuns });

    render(<RunManagerPanel />);

    await waitFor(() => {
      expect(screen.getByLabelText('選取 hash_a1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('選取 hash_a1'));
    fireEvent.click(screen.getByLabelText('選取 hash_a2'));

    const deleteBatchBButtons = screen.getAllByRole('button', { name: /刪除整批 wave-b/ });
    fireEvent.click(deleteBatchBButtons[0]);

    const dialog = await screen.findByRole('dialog', { name: /確認批次刪除/ });
    expect(within(dialog).getByText(/SOLUSDT\/12h/)).toBeInTheDocument();
    expect(within(dialog).getByText(/XRPUSDT\/12h/)).toBeInTheDocument();
    expect(within(dialog).queryByText(/BTCUSDT\/12h/)).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '確認刪除' }));

    await waitFor(() => {
      const bulkCall = fetchCalls.find((call) => call.url === bulkDeleteUrl());
      expect(bulkCall).toBeDefined();
      const body = JSON.parse(String(bulkCall?.init?.body)) as {
        runs: Array<{ symbol: string; config_hash: string }>;
      };
      expect(body.runs.map((r) => r.symbol).sort()).toEqual(['SOLUSDT', 'XRPUSDT']);
    });

    expect(screen.getByLabelText('選取 hash_a1')).toBeChecked();
    expect(screen.getByLabelText('選取 hash_a2')).toBeChecked();
  });

  it('shows message when whole batch has only active runs', async () => {
    const activeOnly = [
      baseRun({
        symbol: 'BTCUSDT',
        config_hash: 'active_only',
        batch_id: 'batch-active',
        batch_alias: 'all-active',
        active: true,
      }),
    ];

    const fetchMock = vi.fn(async (url: string) => {
      if (url === runsUrl()) {
        return response(200, activeOnly);
      }
      return response(404, {});
    });
    vi.stubGlobal('fetch', fetchMock);

    useFeatureFactoryStore.setState({ runs: activeOnly });

    render(<RunManagerPanel />);

    const deleteBtn = await screen.findByRole('button', { name: /刪除整批 all-active/ });
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(screen.getByText(/此批次無可刪除的 Run/)).toBeInTheDocument();
    });
    expect(screen.queryByRole('dialog', { name: /確認批次刪除/ })).not.toBeInTheDocument();
  });
});
