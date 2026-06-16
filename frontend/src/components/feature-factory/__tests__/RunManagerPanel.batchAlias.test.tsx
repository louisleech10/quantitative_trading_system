import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { RunInfo } from '@/lib/types';

const mockFetchRuns = vi.fn();
const mockUpdateRunAlias = vi.fn();
const mockSetBatchAlias = vi.fn();
const mockDeleteRun = vi.fn();

const storeState = vi.hoisted(() => ({
  runs: [] as RunInfo[],
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
  ...overrides,
});

describe('RunManagerPanel batch grouping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storeState.runs = [];
  });

  afterEach(() => {
    cleanup();
  });

  it('renders batch group headers with disambiguation short ids', () => {
    storeState.runs = [
      baseRun({ symbol: 'BTCUSDT', batch_id: 'batch-alpha-001', batch_alias: 'wave-a' }),
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'cfg_b',
        batch_id: 'batch-alpha-001',
        batch_alias: 'wave-a',
        browse_task_id: 'browse_ETHUSDT_12h_cfg_b',
      }),
      baseRun({
        symbol: 'SOLUSDT',
        config_hash: 'cfg_c',
        batch_id: 'batch-beta-002',
        batch_alias: 'wave-a',
        browse_task_id: 'browse_SOLUSDT_12h_cfg_c',
      }),
    ];

    render(<RunManagerPanel />);

    expect(screen.getAllByText(/批次：wave-a/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/batch-alp/)).toBeInTheDocument();
    expect(screen.getByText(/batch-bet/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /重命名整批/ })).toHaveLength(2);
  });

  it('keeps runs without batch_id as single rows', () => {
    storeState.runs = [baseRun()];

    render(<RunManagerPanel />);
    expect(screen.queryByText(/批次：/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /重命名 cfg_a/ })).toBeInTheDocument();
  });
});
