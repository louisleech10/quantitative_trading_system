/**
 * LA-1 B3-FE-01：render 生產 component，斷言 DOM payload 無假零 bar
 * （禁測試內複製 mapping — 還原 production ?? 0 必紅）
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import GroupedICBarChart from '@/components/ic-analysis/GroupedICBarChart';
import type { GroupedICData } from '@/lib/types';

beforeAll(() => {
  class RO {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).ResizeObserver = RO;
});

afterEach(() => {
  cleanup();
});

type ChartPoint = { group: string; ic: number | null };

function readProductionChartData(): ChartPoint[] {
  const el = screen.getByTestId('grouped-ic-chart-payload');
  const raw = el.getAttribute('data-chart');
  expect(raw).toBeTruthy();
  return JSON.parse(raw as string) as ChartPoint[];
}

describe('GroupedICBarChart NaN/null (production DOM)', () => {
  it('missing/NaN feature IC → null in production payload (not 0)', () => {
    const groupedIC: GroupedICData = {
      by_regime: {
        high_vol: { feat_a: 0.12 },
        low_vol: {}, // missing feat_a
        mid: { feat_a: Number.NaN },
      },
    };
    render(<GroupedICBarChart groupedIC={groupedIC} featureName="feat_a" />);

    const chartData = readProductionChartData();
    expect(chartData.find((d) => d.group === 'low_vol')?.ic).toBeNull();
    expect(chartData.find((d) => d.group === 'mid')?.ic).toBeNull();
    expect(chartData.find((d) => d.group === 'high_vol')?.ic).toBe(0.12);
    // 假零 bar：缺失/NaN 不得落到 0
    const zeroBars = chartData.filter(
      (d) => d.group !== 'high_vol' && d.ic === 0
    );
    expect(zeroBars).toEqual([]);
    // 明確：null 而非 0
    expect(chartData.some((d) => d.ic === null)).toBe(true);
  });
});
