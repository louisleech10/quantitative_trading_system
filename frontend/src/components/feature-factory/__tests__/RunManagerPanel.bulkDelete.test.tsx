import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { BulkDeleteResponse, OrphanEntry, RunInfo } from '@/lib/types';

const API_BASE = 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

const mockFetchRuns = vi.fn();
const mockUpdateRunAlias = vi.fn();
const mockSetBatchAlias = vi.fn();
const mockDeleteRun = vi.fn();

const storeState = vi.hoisted(() => ({
  runs: [] as RunInfo[],
  bulkDeleteRuns: vi.fn(),
  scanOrphans: vi.fn(),
  cleanOrphans: vi.fn(),
}));

vi.mock('@/store/featureFactoryStore', () => ({
  useFeatureFactoryStore: () => ({
    runs: storeState.runs,
    runsLoading: false,
    runsError: null,
    fetchRuns: mockFetchRuns,
    updateRunAlias: mockUpdateRunAlias,
    setBatchAlias: mockSetBatchAlias,
    deleteRun: mockDeleteRun,
    bulkDeleteRuns: storeState.bulkDeleteRuns,
    scanOrphans: storeState.scanOrphans,
    cleanOrphans: storeState.cleanOrphans,
  }),
}));

import RunManagerPanel from '@/components/feature-factory/RunManagerPanel';

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

function bulkDeleteUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/bulk-delete`;
}

function orphansUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/orphans`;
}

function orphansCleanUrl(): string {
  return `${API_BASE}${API_PREFIX}/runs/orphans/clean`;
}

describe('RunManagerPanel bulk delete & orphan cleanup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState.runs = [];
    storeState.bulkDeleteRuns.mockReset();
    storeState.scanOrphans.mockReset();
    storeState.cleanOrphans.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('multi-select bulk delete calls bulkDeleteRuns with deduped payload', async () => {
    storeState.runs = [
      baseRun({ symbol: 'BTCUSDT', config_hash: 'hash_one', alias: 'alpha-run' }),
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'hash_two',
        browse_task_id: 'browse_ETHUSDT_12h_hash_two',
        size_bytes: 2048,
      }),
    ];
    const bulkResponse: BulkDeleteResponse = {
      deleted: [
        { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_one', bytes: 1024 },
        { symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'hash_two', bytes: 2048 },
      ],
      failed: [],
      skipped: [],
    };
    storeState.bulkDeleteRuns.mockResolvedValue({ ok: true, data: bulkResponse });

    render(<RunManagerPanel />);

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);

    fireEvent.click(screen.getByRole('button', { name: /批次刪除 \(2\)/ }));

    const dialog = await screen.findByRole('dialog', { name: /確認批次刪除/ });
    expect(within(dialog).getByText('alpha-run')).toBeInTheDocument();
    expect(within(dialog).getAllByText('hash_one').length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getAllByText('hash_two').length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getByText(/總計：2 筆/)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '確認刪除' }));

    await waitFor(() => {
      expect(storeState.bulkDeleteRuns).toHaveBeenCalledTimes(1);
    });
    expect(storeState.bulkDeleteRuns).toHaveBeenCalledWith([
      { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'hash_one' },
      { symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'hash_two' },
    ]);
    expect(mockDeleteRun).not.toHaveBeenCalled();
  });

  it('shows failed per-run results after partial bulk delete failure', async () => {
    storeState.runs = [
      baseRun({ config_hash: 'ok_hash' }),
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'bad_hash',
        browse_task_id: 'browse_ETHUSDT_12h_bad_hash',
      }),
    ];
    storeState.bulkDeleteRuns.mockResolvedValue({
      ok: true,
      data: {
        deleted: [{ symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'ok_hash', bytes: 512 }],
        failed: [{
          symbol: 'ETHUSDT',
          timeframe: '12h',
          config_hash: 'bad_hash',
          bytes: 0,
          error: 'delete_partial',
        }],
        skipped: [],
      } satisfies BulkDeleteResponse,
    });

    render(<RunManagerPanel />);
    fireEvent.click(screen.getByLabelText('選取 ok_hash'));
    fireEvent.click(screen.getByLabelText('選取 bad_hash'));
    fireEvent.click(screen.getByRole('button', { name: /批次刪除 \(2\)/ }));
    const dialog = await screen.findByRole('dialog', { name: /確認批次刪除/ });
    fireEvent.click(within(dialog).getByRole('button', { name: '確認刪除' }));

    await waitFor(() => {
      expect(screen.getByText(/批次刪除結果/)).toBeInTheDocument();
    });
    expect(screen.getByText(/失敗: delete_partial/)).toBeInTheDocument();
    expect(screen.getByText('已刪除')).toBeInTheDocument();
    expect(screen.getByText(/部分刪除失敗/)).toBeInTheDocument();
  });

  it('disables active run selection and shows alias plus full hash in confirm dialog', async () => {
    storeState.runs = [
      baseRun({
        config_hash: 'fullhash_active_12345678',
        alias: 'my-alias',
        active: true,
      }),
      baseRun({
        symbol: 'SOLUSDT',
        config_hash: 'fullhash_idle_abcdefgh',
        alias: 'idle-alias',
        browse_task_id: 'browse_SOLUSDT_12h_fullhash_idle_abcdefgh',
        batch_id: 'batch-wave-1',
        batch_alias: 'wave-one',
      }),
    ];

    render(<RunManagerPanel />);

    expect(screen.getByLabelText('選取 my-alias')).toBeDisabled();
    expect(screen.getByLabelText('選取 idle-alias')).not.toBeDisabled();

    fireEvent.click(screen.getByLabelText('選取 idle-alias'));
    fireEvent.click(screen.getByRole('button', { name: /批次刪除 \(1\)/ }));

    const dialog = await screen.findByRole('dialog', { name: /確認批次刪除/ });
    expect(within(dialog).getByText('idle-alias')).toBeInTheDocument();
    expect(within(dialog).getByText('fullhash_idle_abcdefgh')).toBeInTheDocument();
    expect(within(dialog).getByText('wave-one')).toBeInTheDocument();
    expect(within(dialog).queryByText('my-alias')).not.toBeInTheDocument();
  });

  it('excludes runs that became active after selection from bulk delete payload', async () => {
    const idleRun = baseRun({
      symbol: 'SOLUSDT',
      config_hash: 'was_idle_hash',
      alias: 'was-idle',
      browse_task_id: 'browse_SOLUSDT_12h_was_idle_hash',
    });
    storeState.runs = [
      idleRun,
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'still_idle',
        alias: 'eth-idle',
        browse_task_id: 'browse_ETHUSDT_12h_still_idle',
      }),
    ];
    storeState.bulkDeleteRuns.mockResolvedValue({
      ok: true,
      data: {
        deleted: [{ symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'still_idle', bytes: 1024 }],
        failed: [],
        skipped: [],
      },
    });

    const { rerender } = render(<RunManagerPanel />);

    fireEvent.click(screen.getByLabelText('選取 was-idle'));
    fireEvent.click(screen.getByLabelText('選取 eth-idle'));

    storeState.runs = [
      { ...idleRun, active: true },
      storeState.runs[1],
    ];
    rerender(<RunManagerPanel />);

    fireEvent.click(screen.getByRole('button', { name: /批次刪除 \(1\)/ }));
    const dialog = await screen.findByRole('dialog', { name: /確認批次刪除/ });
    expect(within(dialog).getByText(/已排除 1 筆使用中 Run/)).toBeInTheDocument();
    expect(within(dialog).getByText(/was-idle/)).toBeInTheDocument();
    expect(within(dialog).getByText('eth-idle')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '確認刪除' }));

    await waitFor(() => {
      expect(storeState.bulkDeleteRuns).toHaveBeenCalledTimes(1);
    });
    expect(storeState.bulkDeleteRuns).toHaveBeenCalledWith([
      { symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'still_idle' },
    ]);
  });

  it('orphan scan then clean calls correct endpoints', async () => {
    const orphans: OrphanEntry[] = [
      {
        kind: 'registry_without_leaf',
        symbol: 'ADAUSDT',
        timeframe: '4h',
        config_hash: 'orphan_cfg',
        leaf_kind: 'features',
      },
    ];
    storeState.scanOrphans.mockResolvedValue({ ok: true, data: { orphans, count: 1 } });
    storeState.cleanOrphans.mockResolvedValue({
      ok: true,
      data: {
        orphans: [],
        cleaned_registry: 1,
        cleaned_leaves: 0,
        errors: [],
        dry_run: false,
      },
    });

    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === orphansUrl() && (!init || init.method === undefined || init.method === 'GET')) {
        return { ok: true, json: async () => ({ orphans, count: 1 }) };
      }
      if (url === orphansCleanUrl() && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { dry_run: boolean };
        expect(body.dry_run).toBe(false);
        return {
          ok: true,
          json: async () => ({
            orphans: [],
            cleaned_registry: 1,
            cleaned_leaves: 0,
            errors: [],
            dry_run: false,
          }),
        };
      }
      if (url === bulkDeleteUrl()) {
        return { ok: true, json: async () => ({ deleted: [], failed: [], skipped: [] }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchMock);

    storeState.runs = [baseRun()];
    storeState.scanOrphans.mockImplementation(async () => {
      const response = await fetch(orphansUrl());
      const data = await response.json();
      return { ok: true, data };
    });
    storeState.cleanOrphans.mockImplementation(async (dryRun: boolean) => {
      const response = await fetch(orphansCleanUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun }),
      });
      const data = await response.json();
      return { ok: true, data };
    });

    render(<RunManagerPanel />);
    fireEvent.click(screen.getByRole('button', { name: '孤兒清理' }));

    const dialog = await screen.findByRole('dialog', { name: /孤兒清理/ });
    await waitFor(() => {
      expect(within(dialog).getByText('orphan_cfg')).toBeInTheDocument();
    });
    expect(storeState.scanOrphans).toHaveBeenCalledTimes(1);

    fireEvent.click(within(dialog).getByRole('button', { name: '清理孤兒' }));
    fireEvent.click(within(dialog).getByRole('button', { name: '確認清理' }));

    await waitFor(() => {
      expect(storeState.cleanOrphans).toHaveBeenCalledWith(false);
    });
    expect(fetchMock).toHaveBeenCalledWith(
      orphansCleanUrl(),
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
