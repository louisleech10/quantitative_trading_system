import { describe, expect, it } from 'vitest';

import { readPeriodAlignment, summarizePeriodAlignment } from './icPeriodAlignment';

describe('period_alignment 揭露（EVTALIGN Task 3.1）', () => {
  it('沒有鍵 ⇒ null（不顯示「裁 0 根」假揭露）', () => {
    expect(readPeriodAlignment({})).toBeNull();
    expect(readPeriodAlignment(undefined)).toBeNull();
    expect(summarizePeriodAlignment({ trimmed_bars: { head: 0, tail: 0 } })).toBeNull();
  });

  it('裁切：頭尾根數與採用區間', () => {
    const s = summarizePeriodAlignment({
      used: { start: '2024-01-06', end: '2024-03-10', bars: 131 },
      trimmed_bars: { head: 10, tail: 16 },
      kline_period: { start: '2024-01-06', end: '2024-03-10', bars: 131 },
    })!;
    expect(s.trimmed).toEqual({ head: 10, tail: 16 });
    expect(s.used).toEqual({ start: '2024-01-06', end: '2024-03-10', bars: 131 });
    expect(s.lines[0]).toContain('開頭 10 根、結尾 16 根');
    expect(s.lines[1]).toContain('131 根');
  });

  it('丟事件：ID 必列、原因翻成白話', () => {
    const s = summarizePeriodAlignment({
      dropped_events: { count: 2, ids: ['ev-out-early', 'ev-out-late'], reason: 'outside_feature_run' },
      feature_run: { start_ms: 1, end_ms: 2 },
    })!;
    expect(s.droppedIds).toEqual(['ev-out-early', 'ev-out-late']);
    expect(s.lines[0]).toContain('2 個事件沒有進分析');
    expect(s.lines[0]).toContain('ev-out-early、ev-out-late');
    expect(s.lines[0]).toContain('落在特徵 run 的期間之外');
  });

  it('只有 count 沒有 ids ⇒ 不顯示丟事件行（只報數不算揭露）', () => {
    expect(summarizePeriodAlignment({ dropped_events: { count: 3, ids: [] } })).toBeNull();
  });
});
