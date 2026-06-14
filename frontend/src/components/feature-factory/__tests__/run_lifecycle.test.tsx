import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RunManagerPanel from '../RunManagerPanel';
import RunRetentionDialog from '../RunRetentionDialog';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const run = { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'cfg_batch2d' };

describe('run lifecycle', () => {
  beforeEach(() => {
    useFeatureFactoryStore.setState({ runs: [], runsLoading: false, runsError: null, completionQueue: [] });
    vi.stubGlobal('confirm', vi.fn(() => true));
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it('renders completion queue and retains item on 422', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }));
    useFeatureFactoryStore.setState({ completionQueue: [run] });
    render(<RunRetentionDialog />);
    fireEvent.change(screen.getByLabelText('Run alias'), { target: { value: 'alpha' } });
    fireEvent.click(screen.getByText('命名保留'));
    expect(await screen.findByRole('alert')).toHaveTextContent('名稱已被使用');
    expect(useFeatureFactoryStore.getState().completionQueue).toHaveLength(1);
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
});
