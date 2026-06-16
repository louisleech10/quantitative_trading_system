import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import FeatureExplorer from '../FeatureExplorer';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import type { RunInfo } from '@/lib/types';

const browseSummary = vi.fn();
const browseFeatures = vi.fn();
const listAvailableTasks = vi.fn();

vi.mock('@/hooks/useFeatureFactory', () => ({
  useFeatureFactory: () => ({
    browseSummary,
    browseFeatures,
    listAvailableTasks,
  }),
}));

vi.mock('@/components/feature-factory/OverviewDashboard', () => ({
  default: () => null,
}));
vi.mock('@/components/feature-factory/FeatureTable', () => ({
  default: () => null,
}));
vi.mock('@/components/feature-factory/FeatureTimeSeriesChart', () => ({
  default: () => null,
}));
vi.mock('@/components/feature-factory/FeatureCorrelationHeatmap', () => ({
  default: () => null,
}));
vi.mock('@/components/feature-factory/FeatureDistributionChart', () => ({
  default: () => null,
}));
vi.mock('@/components/feature-factory/DataQualityDashboard', () => ({
  default: () => null,
}));

const mockRun = (overrides: Partial<RunInfo> = {}): RunInfo => ({
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'cfg_batch2d',
  active: false,
  browse_task_id: 'browse_BTCUSDT_12h_cfg_batch2d',
  browse_ready: true,
  browse_path: 'features/BTCUSDT/12h/cfg_batch2d/feature_manifest.json',
  feature_count: 42,
  created_at: '2026-06-01T00:00:00+00:00',
  ...overrides,
});

const runsFixture = [
  mockRun({ config_hash: 'cfg_old', browse_task_id: 'browse_BTCUSDT_12h_cfg_old' }),
  mockRun({
    symbol: 'BTCUSDT',
    config_hash: 'cfg_batch2d',
    browse_task_id: 'browse_BTCUSDT_12h_cfg_batch2d',
    browse_path: 'features/BTCUSDT/12h/cfg_batch2d/feature_manifest.json',
  }),
  mockRun({
    symbol: 'ETHUSDT',
    config_hash: 'cfg_eth',
    browse_task_id: 'browse_ETHUSDT_12h_cfg_eth',
    browse_path: 'features/ETHUSDT/12h/cfg_eth/feature_manifest.json',
  }),
];

const summaryFixture = {
  total_features: 42,
  total_rows: 100,
  by_category: {},
  by_level: {},
  by_layer: {},
  quality: {
    nan_ratio_mean: 0,
    nan_ratio_max: 0,
    nan_ratio_distribution: [],
    constant_features: [],
    high_corr_pairs_count: 0,
    stationary_ratio: 1,
  },
};

describe('FeatureExplorer unified run selector', () => {
  beforeEach(() => {
    browseSummary.mockResolvedValue(summaryFixture);
    browseFeatures.mockResolvedValue({ features: [], total: 0 });
    listAvailableTasks.mockResolvedValue([]);
    useFeatureFactoryStore.setState({
      runs: runsFixture,
      runsLoading: false,
      selectedRunKey: null,
      explorerSummaryByTask: {},
      explorerFeatureNamesByTask: {},
      validationSummaryByTask: {},
      currentTask: null,
      batchTask: null,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/api/v1/features/runs')) {
          return Promise.resolve({ ok: true, json: async () => runsFixture });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders a single explorer with searchable run list and selection', async () => {
    render(<FeatureExplorer />);

    expect(screen.getByText('Feature Explorer')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('搜尋 alias / symbol / hash…')).toBeInTheDocument();

    const selects = screen.getAllByRole('combobox');
    const runDropdown = selects[selects.length - 1];
    await waitFor(() => {
      expect(runDropdown).not.toBeDisabled();
    });

    fireEvent.change(runDropdown, {
      target: { value: 'ETHUSDT|12h|cfg_eth' },
    });

    expect(useFeatureFactoryStore.getState().selectedRunKey).toBe('ETHUSDT|12h|cfg_eth');
    await waitFor(() => {
      expect(browseSummary).toHaveBeenCalledWith('browse_ETHUSDT_12h_cfg_eth');
    });
  });

  it('auto-selects batch concrete run and overrides prior auto selection when batch completes', async () => {
    useFeatureFactoryStore.setState({
      runs: runsFixture,
      selectedRunKey: 'BTCUSDT|12h|cfg_old',
      currentTask: null,
      batchTask: null,
    });

    const view = render(<FeatureExplorer />);

    await waitFor(() => {
      expect(useFeatureFactoryStore.getState().selectedRunKey).toBe('BTCUSDT|12h|cfg_old');
    });

    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-1',
        status: 'completed',
        total: 1,
        completed: 1,
        failed: 0,
        progress: 1,
        current_timeframe: '12h',
        results: { BTCUSDT: '/tmp/btc.h5' },
        browse_task_ids: { BTCUSDT: 'browse_BTCUSDT_12h_cfg_batch2d' },
      },
    });
    view.rerender(<FeatureExplorer />);

    await waitFor(() => {
      expect(useFeatureFactoryStore.getState().selectedRunKey).toBe('BTCUSDT|12h|cfg_batch2d');
    });
  });

  it('does not override manual run selection when batch completes', async () => {
    useFeatureFactoryStore.setState({
      runs: runsFixture,
      selectedRunKey: 'ETHUSDT|12h|cfg_eth',
      currentTask: null,
      batchTask: null,
    });

    const view = render(<FeatureExplorer />);

    const selects = screen.getAllByRole('combobox');
    const runDropdown = selects[selects.length - 1];
    await waitFor(() => {
      expect(runDropdown).not.toBeDisabled();
    });
    fireEvent.change(runDropdown, {
      target: { value: 'ETHUSDT|12h|cfg_eth' },
    });

    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-1',
        status: 'completed',
        total: 1,
        completed: 1,
        failed: 0,
        progress: 1,
        current_timeframe: '12h',
        results: { BTCUSDT: '/tmp/btc.h5' },
        browse_task_ids: { BTCUSDT: 'browse_BTCUSDT_12h_cfg_batch2d' },
      },
    });
    view.rerender(<FeatureExplorer />);

    await waitFor(() => {
      expect(useFeatureFactoryStore.getState().selectedRunKey).toBe('ETHUSDT|12h|cfg_eth');
    });
  });

  it('filters runs by batch_alias in search haystack', async () => {
    useFeatureFactoryStore.setState({
      runs: [
        mockRun({ batch_alias: 'wave-alpha', config_hash: 'cfg_wave' }),
        mockRun({ symbol: 'ETHUSDT', config_hash: 'cfg_eth', browse_task_id: 'browse_ETHUSDT_12h_cfg_eth' }),
      ],
      selectedRunKey: null,
    });

    render(<FeatureExplorer />);

    const searchInput = screen.getByPlaceholderText('搜尋 alias / symbol / hash…');
    fireEvent.change(searchInput, { target: { value: 'wave-alpha' } });

    const selects = screen.getAllByRole('combobox');
    const runDropdown = selects[selects.length - 1] as HTMLSelectElement;
    const optionLabels = Array.from(runDropdown.options).map((option) => option.textContent ?? '');
    expect(optionLabels.some((label) => label.includes('wave-alpha:BTCUSDT'))).toBe(true);
    expect(optionLabels.some((label) => label.includes('ETHUSDT'))).toBe(false);
  });
});
