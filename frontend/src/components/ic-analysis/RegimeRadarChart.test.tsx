/**
 * LA-1 B3-FE-01：render 生產 component，斷言 DOM payload 無假零 point
 * （禁測試內複製 mapping — 還原 production ?? 0 必紅）
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import RegimeRadarChart from '@/components/ic-analysis/RegimeRadarChart';
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

type ChartPoint = { regime: string; value: number | null };

function readProductionChartData(): ChartPoint[] {
  const el = screen.getByTestId('regime-radar-chart-payload');
  const raw = el.getAttribute('data-chart');
  expect(raw).toBeTruthy();
  return JSON.parse(raw as string) as ChartPoint[];
}

describe('RegimeRadarChart NaN/null (production DOM)', () => {
  it('missing/NaN feature IC → null in production payload (not 0)', () => {
    const groupedIC: GroupedICData = {
      by_regime: {
        high_vol: { feat_a: 0.2 },
        low_vol: { feat_a: Number.NaN },
        mid_vol: {}, // missing
      },
    };
    render(<RegimeRadarChart groupedIC={groupedIC} featureName="feat_a" />);

    const chartData = readProductionChartData();
    expect(chartData.find((d) => d.regime === 'low_vol')?.value).toBeNull();
    expect(chartData.find((d) => d.regime === 'mid_vol')?.value).toBeNull();
    expect(chartData.find((d) => d.regime === 'high_vol')?.value).toBe(0.2);
    const zeroPoints = chartData.filter(
      (d) => d.regime !== 'high_vol' && d.value === 0
    );
    expect(zeroPoints).toEqual([]);
    expect(chartData.some((d) => d.value === null)).toBe(true);
  });
});
