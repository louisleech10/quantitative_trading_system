import { describe, expect, it } from 'vitest';

import type { BatchTaskStatus, FeatureTask, RunInfo } from '@/lib/types';
import { formatRunLabel, identityFromBrowseTaskId, pickDefaultRun, runsToRegistryEntries } from '@/lib/runExplorer';

const baseRun = (overrides: Partial<RunInfo> = {}): RunInfo => ({
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'cfg_a',
  active: false,
  browse_task_id: 'browse_BTCUSDT_12h_cfg_a',
  browse_ready: true,
  browse_path: 'features/BTCUSDT/12h/cfg_a/feature_manifest.json',
  feature_count: 10,
  row_count: 100,
  created_at: '2026-06-01T00:00:00+00:00',
  ...overrides,
});

describe('runExplorer', () => {
  it('runsToRegistryEntries keeps only browse-ready runs', () => {
    const entries = runsToRegistryEntries([
      baseRun(),
      baseRun({
        symbol: 'ETHUSDT',
        config_hash: 'cfg_b',
        browse_task_id: 'browse_ETHUSDT_12h_cfg_b',
        browse_ready: false,
      }),
    ]);
    expect(entries).toHaveLength(1);
    expect(entries[0].symbol).toBe('BTCUSDT');
  });

  it('formatRunLabel prefers alias and appends feature count', () => {
    const label = formatRunLabel(baseRun({ alias: 'alpha run' }));
    expect(label).toContain('alpha run');
    expect(label).toContain('10');
  });

  it('formatRunLabel uses batch_alias:symbol when alias missing', () => {
    const label = formatRunLabel(baseRun({ batch_alias: 'wave-a' }));
    expect(label.startsWith('wave-a:BTCUSDT')).toBe(true);
  });

  it('pickDefaultRun prefers completed current task identity over same symbol/timeframe', () => {
    const runs = [
      baseRun({ config_hash: 'cfg_old', browse_task_id: 'browse_BTCUSDT_12h_cfg_old' }),
      baseRun({ config_hash: 'cfg_new', browse_task_id: 'browse_BTCUSDT_12h_cfg_new' }),
    ];
    const currentTask = {
      task_id: 'task-1',
      status: 'completed',
      progress: 1,
      current_stage: null,
      completed_stages: [],
      run_identity: { symbol: 'BTCUSDT', timeframe: '12h', config_hash: 'cfg_new' },
    } as FeatureTask;
    expect(pickDefaultRun(runs, currentTask, null)?.config_hash).toBe('cfg_new');
  });

  it('pickDefaultRun uses batch browse_task_ids for concrete run when multiple share symbol/timeframe', () => {
    const runs = [
      baseRun({ config_hash: 'cfg_old', browse_task_id: 'browse_BTCUSDT_12h_cfg_old' }),
      baseRun({ config_hash: 'cfg_new', browse_task_id: 'browse_BTCUSDT_12h_cfg_new' }),
    ];
    const batchTask = {
      task_id: 'batch-1',
      status: 'completed',
      total: 1,
      completed: 1,
      failed: 0,
      progress: 1,
      current_timeframe: '12h',
      results: { BTCUSDT: '/tmp/btc.h5' },
      browse_task_ids: { BTCUSDT: 'browse_BTCUSDT_12h_cfg_new' },
    } as BatchTaskStatus;
    expect(pickDefaultRun(runs, null, batchTask)?.config_hash).toBe('cfg_new');
  });

  it('pickDefaultRun falls back to first batch symbol via browse_task_id identity', () => {
    const runs = [
      baseRun({ symbol: 'ETHUSDT', config_hash: 'cfg_eth', browse_task_id: 'browse_ETHUSDT_12h_cfg_eth' }),
      baseRun(),
    ];
    const batchTask = {
      task_id: 'batch-1',
      status: 'completed',
      total: 1,
      completed: 1,
      failed: 0,
      progress: 1,
      current_timeframe: '12h',
      results: { BTCUSDT: '/tmp/btc.h5' },
      browse_task_ids: { BTCUSDT: 'browse_BTCUSDT_12h_cfg_a' },
    } as BatchTaskStatus;
    expect(pickDefaultRun(runs, null, batchTask)?.symbol).toBe('BTCUSDT');
  });

  it('identityFromBrowseTaskId parses stable browse ids', () => {
    expect(identityFromBrowseTaskId('browse_BTCUSDT_12h_cfg_a')).toEqual({
      symbol: 'BTCUSDT',
      timeframe: '12h',
      config_hash: 'cfg_a',
    });
  });
});
