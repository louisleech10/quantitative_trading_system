import { describe, expect, it } from 'vitest';

import type { RunInfo } from '@/lib/types';
import { formatRunLabel } from '@/lib/runExplorer';

const baseRun = (overrides: Partial<RunInfo> = {}): RunInfo => ({
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'cfg_a',
  active: false,
  browse_task_id: 'browse_BTCUSDT_12h_cfg_a',
  browse_ready: true,
  feature_count: 10,
  row_count: 100,
  created_at: '2026-06-01T00:00:00+00:00',
  ...overrides,
});

describe('batchAlias label priority', () => {
  it('prefers per-run alias over batch_alias', () => {
    const label = formatRunLabel(baseRun({ alias: 'alpha', batch_alias: 'wave-a' }));
    expect(label).toContain('alpha');
    expect(label).not.toContain('wave-a:');
  });

  it('uses batch_alias:symbol when alias missing', () => {
    const label = formatRunLabel(baseRun({ batch_alias: 'wave-a' }));
    expect(label.startsWith('wave-a:BTCUSDT')).toBe(true);
  });

  it('falls back to symbol/timeframe/hash when no names', () => {
    const label = formatRunLabel(baseRun());
    expect(label).toContain('BTCUSDT / 12h / cfg_a');
  });
});
