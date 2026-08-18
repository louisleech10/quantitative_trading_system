/**
 * PA-CUMSUM（2026-08-18）——NaiveStrategyEquityChart 單利／複利切換
 * 具名 test：預設複利顯示 strategy_compound 終值；點「單利」後顯示 strategy_simple（兩值不同 ⇒ 切換有效）；
 * 圖表資料真的切到 *_simple 序列；多標的等權組合註記顯示；a11y tab/tabpanel 連結。
 */
import React from 'react';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { EquityCurveData } from '@/lib/patternTypes';

const chartCapture = vi.hoisted(() => ({ chartData: [] as unknown[], reset() { this.chartData = []; } }));

vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => React.createElement('div', null, children),
    LineChart: ({ data, children }: { data?: unknown; children?: React.ReactNode }) => {
      chartCapture.chartData.push(data);
      return React.createElement('div', { 'data-testid': 'linechart-probe' }, children);
    },
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
  };
});
vi.mock('../shared/ChartExportButton', () => ({ default: () => null }));

import NaiveStrategyEquityChart from './NaiveStrategyEquityChart';

const DATA: EquityCurveData = {
  timestamps: [1, 2],
  strategy_returns_simple: [0.5, 0.0], // +50%, −50% 單利
  benchmark_returns_simple: [0.5, 0.0],
  strategy_returns_compound: [0.5, -0.25], // 複利 −25%
  benchmark_returns_compound: [0.5, -0.25],
  threshold: 0.75,
  final_return_pct: { strategy_simple: 0.0, benchmark_simple: 0.0, strategy_compound: -25.0, benchmark_compound: -25.0 },
  n_symbols: 1,
  aggregation: 'single_series',
};

afterEach(() => {
  cleanup();
  chartCapture.reset();
});

describe('NaiveStrategyEquityChart 單利／複利切換', () => {
  it('default_compound_shows_compound_final_and_series', () => {
    render(<NaiveStrategyEquityChart data={DATA} />);
    expect(screen.getByTestId('equity-final-strategy').textContent).toBe('-25.00%');
    const last = chartCapture.chartData.at(-1) as Array<{ strategy: number }>;
    expect(last.map((d) => d.strategy)).toEqual([0.5, -0.25]);
    expect(screen.getByRole('tab', { name: '複利（全額滾入）' }).getAttribute('aria-selected')).toBe('true');
  });

  it('click_simple_switches_final_and_series', () => {
    render(<NaiveStrategyEquityChart data={DATA} />);
    fireEvent.click(screen.getByTestId('equity-mode-simple'));
    expect(screen.getByTestId('equity-final-strategy').textContent).toBe('0.00%');
    const last = chartCapture.chartData.at(-1) as Array<{ strategy: number }>;
    expect(last.map((d) => d.strategy)).toEqual([0.5, 0.0]);
    expect(screen.getByRole('tabpanel').getAttribute('aria-labelledby')).toBe('equity-tab-simple');
  });

  it('arrow_key_toggles_mode', () => {
    render(<NaiveStrategyEquityChart data={DATA} />);
    fireEvent.keyDown(screen.getByTestId('equity-mode-compound'), { key: 'ArrowRight' });
    expect(screen.getByTestId('equity-final-strategy').textContent).toBe('0.00%');
  });

  it('multi_symbol_shows_equal_weight_note', () => {
    render(<NaiveStrategyEquityChart data={{ ...DATA, n_symbols: 3, aggregation: 'equal_weight_by_timestamp' }} />);
    expect(screen.getByTestId('equity-aggregation-note').textContent).toContain('3 個標的');
    cleanup();
    render(<NaiveStrategyEquityChart data={DATA} />);
    expect(screen.queryByTestId('equity-aggregation-note')).toBeNull();
  });
});
