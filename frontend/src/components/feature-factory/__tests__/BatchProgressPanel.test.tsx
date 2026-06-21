import '@testing-library/jest-dom/vitest';

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import BatchProgressPanel from '../BatchProgressPanel';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(payload: string): void {
    this.sent.push(payload);
  }

  close(): void {
    this.onclose?.();
  }

  emitOpen(): void {
    this.onopen?.();
  }

  emitMessage(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
  }

  emitClose(): void {
    this.onclose?.();
  }
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

describe('BatchProgressPanel', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    resetStore();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    resetStore();
  });

  it('renders progress, per-symbol outputs, RSS metrics, and resume action', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        batch_id: 'batch-1',
        status: 'running',
        skipped_items: 1,
        queued_items: 1,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <BatchProgressPanel
        batchTask={{
          task_id: 'batch-1',
          batch_id: 'batch-1',
          status: 'failed',
          total: 2,
          completed: 1,
          failed: 1,
          progress: 0.5,
          current_symbol: 'ETHUSDT',
          current_timeframe: '1h',
          eta_seconds: 120,
          resume_available: true,
          output_paths: [{ symbol: 'BTCUSDT', timeframe: '1h', path: '/tmp/BTCUSDT_1h.h5' }],
          per_item_rss: [{ symbol: 'BTCUSDT', timeframe: '1h', rssPeakMB: 512, rssAfterGcMB: 256 }],
          results: { BTCUSDT: '/tmp/BTCUSDT_1h.h5' },
          errors: { ETHUSDT: 'boom' },
        }}
        symbols={['BTCUSDT', 'ETHUSDT']}
      />
    );

    expect(screen.getAllByText('50%').length).toBeGreaterThan(0);
    expect(screen.getByText('完成：1')).toBeInTheDocument();
    expect(screen.getByText('失敗：1')).toBeInTheDocument();
    expect(screen.getByText('ETA：2m 0s')).toBeInTheDocument();
    expect(screen.getByText('/tmp/BTCUSDT_1h.h5')).toBeInTheDocument();
    expect(screen.getByText(/Peak 512MB/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Resume Batch/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Resume Batch/ }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/features/batch/batch-1/resume',
        { method: 'POST' }
      );
    });
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('applies WebSocket batch_progress events and retries disconnected sockets', async () => {
    vi.useFakeTimers();
    useFeatureFactoryStore.setState({
      batchTask: {
        task_id: 'batch-2',
        batch_id: 'batch-2',
        status: 'running',
        total: 2,
        completed: 0,
        failed: 0,
        progress: 0,
        current_timeframe: '12h',
        results: {},
        errors: {},
      },
      batchStartedAtMs: Date.now() - 10_000,
    });

    render(<BatchProgressPanel batchTask={null} symbols={['BTCUSDT', 'ETHUSDT']} />);

    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8000/ws/features/batch/batch-2');

    act(() => {
      MockWebSocket.instances[0].emitOpen();
      MockWebSocket.instances[0].emitMessage({
        event: 'batch_progress',
        data: {
          task_id: 'batch-2',
          status: 'running',
          total: 2,
          completed: 1,
          failed: 0,
          progress: 0.5,
          current_symbol: 'ETHUSDT',
          current_timeframe: '12h',
          results: { BTCUSDT: '/tmp/BTCUSDT_12h.h5' },
          last_item_metrics: {
            current_symbol: 'BTCUSDT',
            current_timeframe: '12h',
            rss_peak_item_mb: 640,
            rss_after_gc_mb: 320,
          },
        },
      });
    });

    expect(screen.getAllByText('50%').length).toBeGreaterThan(0);
    expect(screen.getByText('/tmp/BTCUSDT_12h.h5')).toBeInTheDocument();
    expect(screen.getByText(/Peak 640MB/)).toBeInTheDocument();

    act(() => {
      MockWebSocket.instances[0].emitClose();
    });
    expect(screen.getAllByText(/WebSocket 斷線/).length).toBeGreaterThan(0);

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it('renders layer stage and rss for running symbol with graceful fallback', () => {
    render(
      <BatchProgressPanel
        batchTask={{
          task_id: 'batch-layer',
          batch_id: 'batch-layer',
          status: 'running',
          total: 2,
          completed: 0,
          failed: 0,
          progress: 0,
          current_symbol: 'ETHUSDT',
          current_timeframe: '1h',
          current_stage: 'layer_3',
          stage_progress: 0.42,
          current_rss_mb: 768,
          results: {},
          errors: {},
        }}
        symbols={['BTCUSDT', 'ETHUSDT']}
      />
    );

    expect(screen.getByTestId('layer-status-ETHUSDT')).toHaveTextContent(
      'layer_3 (42%) · (批)worker RSS 768MB'
    );
    expect(screen.queryByTestId('layer-status-BTCUSDT')).not.toBeInTheDocument();
  });

  it('falls back gracefully when layer fields are absent', () => {
    render(
      <BatchProgressPanel
        batchTask={{
          task_id: 'batch-layer-fallback',
          batch_id: 'batch-layer-fallback',
          status: 'running',
          total: 1,
          completed: 0,
          failed: 0,
          progress: 0,
          current_symbol: 'BTCUSDT',
          current_timeframe: '4h',
          results: {},
          errors: {},
        }}
        symbols={['BTCUSDT']}
      />
    );

    expect(screen.getAllByText('running').length).toBeGreaterThan(0);
    expect(screen.queryByTestId('layer-status-BTCUSDT')).not.toBeInTheDocument();
  });
});
