import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import BatchQualityOverview, { BatchRecoverableSelect } from '../BatchQualityOverview';

describe('BatchQualityOverview', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('shows 批次已失效 on 404 and notifies parent once', async () => {
    const onBatchExpired = vi.fn();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({}),
      })),
    );

    render(
      <BatchQualityOverview batchTaskId="batch-expired" onBatchExpired={onBatchExpired} />,
    );

    await waitFor(() => {
      expect(screen.getByText('批次已失效')).toBeInTheDocument();
    });
    expect(onBatchExpired).toHaveBeenCalledTimes(1);
  });

  it('fetches quality summary for persisted batch id after reload', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        batch_task_id: 'batch-reload-42',
        summaries: [
          {
            symbol: 'BTCUSDT',
            bar_count: 500,
            feature_count: 2,
            nan_ratio_mean: 0.01,
            nan_ratio_max: 0.02,
            constant_feature_count: 0,
            alert_count: 0,
            grade: 'pass',
          },
        ],
        total_symbols: 1,
        pass_count: 1,
        watch_count: 0,
        reject_count: 0,
        computed_at: '2026-06-03T00:00:00.000Z',
      }),
    }));
    vi.stubGlobal('fetch', fetchMock);

    render(<BatchQualityOverview batchTaskId="batch-reload-42" />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/features/batch/batch-reload-42/quality'),
      );
    });
    expect(await screen.findByText('BTCUSDT')).toBeInTheDocument();
  });
});

describe('BatchRecoverableSelect + batch discovery flow', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('renders recoverable batches in dropdown', () => {
    const onChange = vi.fn();
    render(
      <BatchRecoverableSelect
        batches={[
          {
            batch_id: 'batch-a',
            symbols: ['BTCUSDT', 'ETHUSDT'],
            timeframe: '1h',
            completed_count: 2,
            updated_at: '2026-06-03T10:00:00',
          },
          {
            batch_id: 'batch-b',
            symbols: ['DOGEUSDT'],
            timeframe: '4h',
            completed_count: 1,
            updated_at: '2026-06-02T10:00:00',
          },
        ]}
        value=""
        onChange={onChange}
      />,
    );

    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByText(/最近批次 \(2\)/)).toBeInTheDocument();
    expect(screen.getByText(/BTCUSDT, ETHUSDT/)).toBeInTheDocument();
  });

  it('loads quality summary after selecting a recoverable batch', async () => {
    const onChange = vi.fn();
    const { unmount: unmountSelect } = render(
      <BatchRecoverableSelect
        batches={[
          {
            batch_id: 'hist-batch-1',
            symbols: ['BTCUSDT'],
            timeframe: '1h',
            completed_count: 1,
            updated_at: '2026-06-03T00:00:00',
          },
        ]}
        value=""
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'hist-batch-1' } });
    expect(onChange).toHaveBeenCalledWith('hist-batch-1');
    unmountSelect();

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        batch_task_id: 'hist-batch-1',
        summaries: [
          {
            symbol: 'BTCUSDT',
            bar_count: 400,
            feature_count: 10,
            nan_ratio_mean: 0.05,
            nan_ratio_max: 0.1,
            constant_feature_count: 0,
            alert_count: 0,
            grade: 'pass',
          },
        ],
        total_symbols: 1,
        pass_count: 1,
        watch_count: 0,
        reject_count: 0,
        computed_at: '2026-06-03T00:00:00.000Z',
      }),
    }));
    vi.stubGlobal('fetch', fetchMock);

    render(<BatchQualityOverview batchTaskId="hist-batch-1" />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/features/batch/hist-batch-1/quality'),
      );
    });
    expect(await screen.findByText('BTCUSDT')).toBeInTheDocument();
  });
});
