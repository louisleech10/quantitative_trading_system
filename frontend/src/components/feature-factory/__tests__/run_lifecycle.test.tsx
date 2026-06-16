import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RunManagerPanel from '../RunManagerPanel';
import RunRetentionDialog from '../RunRetentionDialog';
import GenerationProgress from '../GenerationProgress';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import type { FeatureTask } from '@/lib/types';

const run = {
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'cfg_batch2d',
  active: false,
  browse_task_id: 'browse_BTCUSDT_12h_cfg_batch2d',
  browse_ready: true,
};
const completionPayload = {
  status: 'completed',
  stage: 'completed',
  current_stage: 'completed',
  progress: 1,
  retention_prompt: true,
  run_identity: run,
};

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(_url: string) {
    void _url;
    MockWebSocket.instances.push(this);
  }

  close() {}
}

const task: FeatureTask = {
  task_id: 'task-1',
  status: 'running',
  progress: 0,
  current_stage: null,
  completed_stages: [],
};

describe('run lifecycle', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem('ff-run-manager-expanded', 'true');
    MockWebSocket.instances = [];
    useFeatureFactoryStore.setState({
      runs: [], runsLoading: false, runsError: null, completionQueue: [],
      currentTask: null, progress: null,
    });
    vi.stubGlobal('confirm', vi.fn(() => true));
    vi.stubGlobal('WebSocket', MockWebSocket);
  });
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

  it('queues the same completion payload from WebSocket and polling', async () => {
    const wsView = render(<GenerationProgress task={task} />);
    const ws = MockWebSocket.instances[0];
    ws.onmessage?.({
      data: JSON.stringify({ event: 'progress', data: completionPayload }),
    } as MessageEvent);
    expect(useFeatureFactoryStore.getState().completionQueue).toEqual([run]);
    wsView.unmount();

    useFeatureFactoryStore.setState({ completionQueue: [], currentTask: null, progress: null });
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => completionPayload,
    }));
    render(<GenerationProgress task={task} />);
    const pollingWs = MockWebSocket.instances[1];
    pollingWs.onerror?.();
    await vi.advanceTimersByTimeAsync(2000);
    expect(useFeatureFactoryStore.getState().completionQueue).toEqual([run]);
  });

  it('renders completion queue and retains item on 422', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }));
    useFeatureFactoryStore.setState({ completionQueue: [run] });
    render(<RunRetentionDialog />);
    fireEvent.change(screen.getByLabelText('Run alias'), { target: { value: 'alpha' } });
    fireEvent.click(screen.getByText('命名並保留'));
    expect(await screen.findByRole('alert')).toHaveTextContent('名稱已被使用');
    expect(useFeatureFactoryStore.getState().completionQueue).toHaveLength(1);
  });

  it('lists runs newest-first by last_generated_at then created_at', async () => {
    const runsFixture = [
      {
        ...run,
        config_hash: 'hash_old',
        alias: 'run-old',
        created_at: '2026-01-01T00:00:00Z',
        last_generated_at: null,
        active: false,
        size_bytes: 1,
      },
      {
        ...run,
        config_hash: 'hash_new',
        alias: 'run-new',
        created_at: '2026-05-01T00:00:00Z',
        last_generated_at: '2026-06-15T00:00:00Z',
        active: false,
        size_bytes: 2,
      },
      {
        ...run,
        config_hash: 'hash_mid',
        alias: 'run-mid',
        created_at: '2026-03-01T00:00:00Z',
        last_generated_at: '2026-04-01T00:00:00Z',
        active: false,
        size_bytes: 3,
      },
    ];
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => runsFixture }),
    );
    useFeatureFactoryStore.setState({
      runsLoading: false,
      runsError: null,
      runs: runsFixture,
    });
    render(<RunManagerPanel />);
    await waitFor(() => expect(screen.getByText('run-new')).toBeInTheDocument());
    const dataRows = screen.getAllByRole('row').slice(1);
    expect(dataRows[0]).toHaveTextContent('run-new');
    expect(dataRows[1]).toHaveTextContent('run-mid');
    expect(dataRows[2]).toHaveTextContent('run-old');
  });

  it('toggles collapsed state and persists preference', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    useFeatureFactoryStore.setState({ runsLoading: false, runsError: null, runs: [] });
    render(<RunManagerPanel />);
    await waitFor(() => expect(screen.getByText('尚無 Runs')).toBeInTheDocument());
    const toggle = screen.getByRole('button', { expanded: true });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('尚無 Runs')).not.toBeInTheDocument();
    expect(window.localStorage.getItem('ff-run-manager-expanded')).toBe('false');
  });

  it('renders loading, empty, error retry, and busy delete state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    useFeatureFactoryStore.setState({ runsLoading: true });
    const view = render(<RunManagerPanel />);
    expect(screen.getByText('載入 Runs…')).toBeInTheDocument();
    useFeatureFactoryStore.setState({ runsLoading: false, runsError: 'boom' });
    view.rerender(<RunManagerPanel />);
    expect(screen.getByRole('alert')).toHaveTextContent('boom');
    useFeatureFactoryStore.setState({ runsError: null, runs: [{ ...run, active: true, size_bytes: 5 }] });
    view.rerender(<RunManagerPanel />);
    expect(screen.getByText('刪除')).toBeDisabled();
    useFeatureFactoryStore.setState({ runs: [] });
    view.rerender(<RunManagerPanel />);
    await waitFor(() => expect(screen.getByText('尚無 Runs')).toBeInTheDocument());
  });

  it('keeps run visible and reports 409/delete_partial', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [{ ...run, active: false, size_bytes: 5 }] })
      .mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({ detail: { code: 'run_busy' } }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<RunManagerPanel />);
    await screen.findByText('cfg_batch2d');
    fireEvent.click(screen.getByText('刪除'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Run 正在使用中');
    expect(screen.getByText('cfg_batch2d')).toBeInTheDocument();
  });

  it('renders delete_partial errors returned by the API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [{ ...run, active: false, size_bytes: 5 }] })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: { code: 'delete_partial', errors: ['features: denied', 'cgsa: busy'] } }),
      });
    vi.stubGlobal('fetch', fetchMock);
    render(<RunManagerPanel />);
    await screen.findByText('cfg_batch2d');
    fireEvent.click(screen.getByText('刪除'));
    expect(await screen.findByRole('alert')).toHaveTextContent('features: denied, cgsa: busy');
    expect(screen.getByText('cfg_batch2d')).toBeInTheDocument();
  });
});
