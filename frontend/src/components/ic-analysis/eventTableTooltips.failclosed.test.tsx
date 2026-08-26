/**
 * GAP-3 UX Task 5.2 邊界②（`--run eventTableTooltips` 亦命中本檔）。
 *
 * **glossary 缺該鍵 ⇒ 畫面顯示 fail-closed 佔位，不是空字串。**
 *
 * 🔴 走的是 render 出來的畫面：定義表被抽掉一鍵之後，那個表頭的 `title` 要變成佔位。
 *    受測邏輯仍是**真的** `tooltipFrom`（只是餵它一份少一鍵的表），不是替身自己編的行為。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EventTablesPanel from '@/components/ic-analysis/EventTablesPanel';
import { GLOSSARY_MISSING_PREFIX } from '@/lib/eventMetricsGlossary';
import type { EventAnalyzeResponse } from '@/lib/types';

// 🔴 `vi.mock` 之 factory 被 hoist 到檔首 ⇒ 裡面**不得**引用頂層變數（會 ReferenceError）。
//    故被抽掉的鍵在 factory 內以字面寫死；下方 `DROPPED_KEY` 只供斷言使用，兩者以本條測試自身綁住
//    （若兩處不一致，① 會因為 `event-metric-<DROPPED_KEY>` 之 title 仍是正常定義而轉紅）。
vi.mock('@/lib/eventMetricsGlossary', async (orig) => {
  const actual = await orig<typeof import('@/lib/eventMetricsGlossary')>();
  const reduced = { ...actual.EVENT_METRIC_DEFINITIONS };
  delete reduced.n_eff;
  return { ...actual, metricTooltip: (key: string) => actual.tooltipFrom(reduced, key) };
});

/** 被抽掉的鍵（須與上方 factory 內之字面相同）。 */
const DROPPED_KEY = 'n_eff';

const RESP = {
  import_id: 'imp-failclosed',
  summary: { n_input: 1, n_aligned: 1, n_align_failures: 0, n_train: 1, n_test: 0, n_purged: 0 },
  align_failures: [],
  tables: {
    event_forward_return_table: {
      capability_status: 'ok',
      horizons: [1],
      primary_macro: { '1': { mean: 0.1, n_symbols: 1 } },
      sensitivity_micro: { '1': { mean: 0.1, median: 0.1, win_rate: 0.5, n: 4, n_effective: 3 } },
    },
    binary_discrimination_table: { capability_status: 'not_computed', reason: 'one_class_test_segment' },
    all_bars_evaluation: { capability_status: 'not_computed', reason: 'one_class_test_segment' },
  },
  event_timestamps: [],
  event_timestamps_ic_seconds: [],
} as unknown as EventAnalyzeResponse;

afterEach(() => cleanup());

describe('Task 5.2 邊界② — glossary 缺鍵之 fail-closed 佔位', () => {
  it('① 缺鍵之表頭顯示佔位（含鍵名），**不是**空字串', () => {
    render(<EventTablesPanel importId="imp-failclosed" data={RESP} />);
    const title = screen.getByTestId(`event-metric-${DROPPED_KEY}`).getAttribute('title');
    expect(title).toBe(`${GLOSSARY_MISSING_PREFIX}${DROPPED_KEY}`);
    expect(title).not.toBe('');
    expect(title).toContain(DROPPED_KEY);
  });

  it('② 同一畫面上沒被抽掉的表頭仍是正常定義（證明佔位不是恆顯示）', () => {
    render(<EventTablesPanel importId="imp-failclosed" data={RESP} />);
    const other = screen.getByTestId('event-metric-macro_mean').getAttribute('title');
    expect(other).not.toContain(GLOSSARY_MISSING_PREFIX);
    expect((other ?? '').length).toBeGreaterThan(0);
  });
});
