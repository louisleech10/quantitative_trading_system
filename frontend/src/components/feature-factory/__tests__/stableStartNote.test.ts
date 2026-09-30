import { describe, expect, it } from 'vitest';

import type { RunInfo } from '@/lib/types';

import { stableStartNote } from '../RunManagerPanel';

const base = {
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'abc',
  active: false,
  browse_task_id: 't',
  browse_ready: true,
} as RunInfo;

describe('stableStartNote（FF-STAT 逐欄穩定點顯示）', () => {
  it('未填起始日：顯示各欄依自身預熱期起算之最早／最晚日期', () => {
    const note = stableStartNote({
      ...base,
      output_start_source: 'per_column',
      stable_start_earliest: '2024-01-02T00:00:00+00:00',
      stable_start_latest: '2026-05-01T12:00:00+00:00',
    });
    expect(note).toBe('各欄依自身預熱期起算（最早 2024-01-02、最晚 2026-05-01）');
  });

  it('未填起始日且開平穩化：另註校準值不輸出', () => {
    const note = stableStartNote({
      ...base,
      output_start_source: 'per_column',
      stable_start_earliest: '2024-01-02T00:00:00',
      stable_start_latest: '2024-02-02T00:00:00',
      calibration_rows_withheld: true,
    });
    expect(note).toContain('每欄前 N 個穩定值保留供校準、不輸出');
  });

  it('有起始日而有歷史不足之欄：顯示欄數；無則不顯示', () => {
    expect(stableStartNote({ ...base, output_start_source: 'user', warmup_insufficient_count: 3 })).toBe(
      '3 欄歷史不足，開頭為空值',
    );
    expect(stableStartNote({ ...base, output_start_source: 'user', warmup_insufficient_count: 0 })).toBeNull();
  });

  it('舊 run 無紀錄：不顯示', () => {
    expect(stableStartNote(base)).toBeNull();
  });
});
