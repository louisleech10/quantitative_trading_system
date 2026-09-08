import { describe, expect, it } from 'vitest';

import { isolationLines, readIsolation } from './icIsolation';

describe('isolation 揭露（EVTALIGN Task 5.1）', () => {
  it('沒鍵 ⇒ null（未切分不顯示 0 根）', () => {
    expect(readIsolation({})).toBeNull();
    expect(isolationLines(null)).toBeNull();
    expect(isolationLines({ purge: { bars: 5 } })).toBeNull();
  });

  it('兩塊來源分開講、總數相加', () => {
    const lines = isolationLines({
      purge: { bars: 5, source: 'global_default_horizon', effective_horizon: 5 },
      embargo: { bars: 12, source: 'event_lookahead', event_purge_rows: 12, config_embargo: 0 },
      total_bars: 17,
    })!;
    expect(lines[0]).toContain('purge 5 根');
    expect(lines[0]).toContain('與你在事件 label 設的 h 無關');
    expect(lines[1]).toContain('embargo 12 根');
    expect(lines[1]).toContain('look-ahead');
    expect(lines[2]).toContain('總隔離 17 根');
  });

  it('未知來源原樣顯示，不吞', () => {
    const lines = isolationLines({ purge: { bars: 1, source: 'weird' }, embargo: { bars: 2, source: 'config_embargo' } })!;
    expect(lines[0]).toContain('weird');
    expect(lines[2]).toContain('總隔離 3 根');
  });
});
