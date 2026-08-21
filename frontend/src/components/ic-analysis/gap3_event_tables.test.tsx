/**
 * GAP-3 B5.2（W9）：兩張表渲染——ok ⇒ 數值列；後端 unavailable／not_computed ⇒ 顯示 reason 非空白；
 * 未選批 ⇒ empty state；前端不重算（只顯示後端數值）。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import EventTablesPanel from '@/components/ic-analysis/EventTablesPanel';
import type { EventAnalyzeResponse } from '@/lib/types';

afterEach(() => cleanup());

const OK: EventAnalyzeResponse = {
  import_id: 'imp-1',
  summary: { n_input: 10, n_aligned: 9, n_align_failures: 1, n_train: 6, n_test: 3, n_purged: 0 },
  align_failures: [{ event_id: 'e9', reason: 'label_window_incomplete' }],
  tables: {
    event_forward_return_table: {
      capability_status: 'ok',
      horizons: [1, 2],
      primary_macro: { '1': { mean: 0.0123, n_symbols: 1 }, '2': { mean: -0.002, n_symbols: 1 } },
      sensitivity_micro: {
        '1': { mean: 0.0123, median: 0.01, win_rate: 0.6, n: 9, n_effective: 7.5 },
        '2': { mean: -0.002, median: -0.001, win_rate: 0.4, n: 9, n_effective: 7.5 },
      },
    },
    binary_discrimination_table: { capability_status: 'not_computed', reason: 'no_model_scores_in_event_pipeline' },
  },
  event_timestamps: [1704067200000],
};

describe('GAP-3 事件型兩表', () => {
  it('ok ⇒ 事件後報酬表逐 horizon 顯示後端數值（不重算）', () => {
    render(<EventTablesPanel data={OK} importId="imp-1" />);
    expect(screen.getByTestId('event-fwd-table')).toBeTruthy();
    const row1 = screen.getByTestId('event-fwd-row-1');
    expect(row1.textContent).toContain('0.0123');
    expect(row1.textContent).toContain('0.600');
    expect(screen.getByTestId('event-fwd-row-2').textContent).toContain('-0.0020');
    expect(screen.getByText(/對齊失敗清單（1）/)).toBeTruthy();
  });

  it('not_computed／unavailable ⇒ 顯示 reason，非空白', () => {
    render(<EventTablesPanel data={OK} importId="imp-1" />);
    const disc = screen.getByTestId('event-disc-unavailable');
    expect(disc.textContent).toContain('not_computed');
    expect(disc.textContent).toContain('no_model_scores_in_event_pipeline');
    const un = { ...OK, tables: { ...OK.tables, event_forward_return_table: { capability_status: 'unavailable', reason: 'missing_prevalence_disclosure' } } };
    cleanup();
    render(<EventTablesPanel data={un} importId="imp-1" />);
    expect(screen.getByTestId('event-fwd-unavailable').textContent).toContain('missing_prevalence_disclosure');
  });

  it('後端缺 reason ⇒ 明示「後端未給 reason」而非空白', () => {
    const noReason = { ...OK, tables: { ...OK.tables, binary_discrimination_table: { capability_status: 'unavailable' } } };
    render(<EventTablesPanel data={noReason} importId="imp-1" />);
    expect(screen.getByTestId('event-disc-unavailable').textContent).toContain('後端未給 reason');
  });

  it('未選批 ⇒ empty state', () => {
    render(<EventTablesPanel />);
    expect(screen.getByTestId('event-tables-empty')).toBeTruthy();
  });
});
