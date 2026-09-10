/**
 * EVTLABEL Task 1.2：隔離區下方「本次 label 怎麼算」區塊之渲染條件。
 *
 * 三種情境：①事件 run（兩塊都在）②切分未套用（只有 label 規則、無隔離區）③全域 run（都沒有 ⇒ 不渲染）。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import IsolationNote from './IsolationNote';
import { useICAnalysisStore } from '@/store/icAnalysisStore';

const RULE = {
  label_source: 'event_label_value',
  statistic_kind: 'conditional_ic',
  horizon_bars: 1,
  decision_offset_bars: 0,
  entry_price_semantic: 'trigger_close',
  label_return_mode: 'close_to_close',
  h_unit: 'event_timeframe_bars',
  event_timeframe: '12h',
  feature_timeframe: '1h',
  feature_bars_per_event_bar: 12,
  ratio_integral: true,
  label_window_feature_bars: 12,
  return_formula: 'close[t0+h] / close[t0] - 1 × direction_sign',
  imported_binary_label: { present: true, n_pos: 136, n_neg: 29, used: false },
  n_events_consumed: 165,
  uniqueness: { mean: 1, min: 1, n_eff: 165, n_overlapping_pairs: 0 },
};

const ISOLATION = {
  purge: { bars: 12, source: 'event_label_window', effective_horizon: 5 },
  embargo: { bars: 144, source: 'event_lookahead_depth', event_purge_rows: 144, config_embargo: 0 },
  total_bars: 156,
};

function setReport(metadata: Record<string, unknown> | null) {
  useICAnalysisStore.setState({ report: metadata ? ({ metadata } as never) : null });
}

afterEach(() => {
  cleanup();
  setReport(null);
});

describe('IsolationNote 之 label 規則區塊', () => {
  it('事件 run：隔離區與 label 規則兩塊都渲染', () => {
    setReport({ isolation: ISOLATION, event_label_rule: RULE });
    render(<IsolationNote />);
    expect(screen.getByTestId('isolation-note')).toBeTruthy();
    expect(screen.getByTestId('label-rule-note')).toBeTruthy();
    expect(screen.getByTestId('label-rule-line-0').textContent).toContain('第 12 根');
    expect(screen.getByTestId('label-rule-line-3').textContent).toContain('正 136／反 29');
    expect(screen.getByTestId('isolation-line-0').textContent).toContain('purge 12 根');
  });

  it('切分未套用（無 isolation）：label 規則仍渲染', () => {
    setReport({ event_label_rule: RULE });
    render(<IsolationNote />);
    expect(screen.getByTestId('label-rule-note')).toBeTruthy();
    expect(screen.queryByTestId('isolation-line-0')).toBeNull();
  });

  it('全域 run（兩鍵皆無）：整個區塊不渲染', () => {
    setReport({ timeframe: '1h' });
    const { container } = render(<IsolationNote />);
    expect(container.firstChild).toBeNull();
  });
});
