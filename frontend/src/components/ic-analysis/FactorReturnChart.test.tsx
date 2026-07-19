/**
 * IC1C-FR-FULL F3.1 / F3-FIX — FactorReturnChart ok 上架 + 正名 + discriminator fail-closed
 *
 * 具名 test(SPEC §P F3 + 雙審回修):
 *   renders_ok_series / legacy_finite_payload_rejected / equity_stays_unavailable
 *   + malformed-union 不繪 / 真 Line dataKey wiring(非 hidden mirror)
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

/** recharts props 擷取(production 不留 hidden mirror;測試斷言真 Line/LineChart props) */
const rechartsCapture = vi.hoisted(() => ({
  lineDataKeys: [] as string[],
  chartData: [] as unknown[],
  reset() {
    this.lineDataKeys = [];
    this.chartData = [];
  },
}));

vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  // 完整 stub Line/LineChart 以暴露 props(包一層 actual 會破壞 recharts children 軸辨識)
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', { className: 'recharts-responsive-container', 'data-testid': 'recharts-rc' }, children),
    LineChart: ({ data, children }: { data?: unknown; children?: React.ReactNode }) => {
      rechartsCapture.chartData.push(data);
      return React.createElement(
        'div',
        { 'data-testid': 'recharts-linechart-probe', className: 'recharts-wrapper' },
        children
      );
    },
    Line: ({ dataKey }: { dataKey?: string | number }) => {
      if (typeof dataKey === 'string') {
        rechartsCapture.lineDataKeys.push(dataKey);
      }
      return React.createElement('div', {
        'data-testid': 'recharts-line-probe',
        className: 'recharts-line',
        'data-datakey': String(dataKey ?? ''),
      });
    },
    // 軸/裝飾不影響 wiring 斷言
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
  };
});

import FactorReturnChart, {
  FACTOR_RETURN_CHART_TITLE,
  FACTOR_RETURN_LEGACY_REJECTED_NOTICE,
  FACTOR_RETURN_UNAVAILABLE_NOTICE,
  extractFactorReturnChartPoints,
  isFactorReturnLegacyFinitePayload,
  isFactorReturnOkUnion,
  isFactorReturnUnavailableUnion,
  shouldShowFactorReturnUnavailableNotice,
} from '@/components/ic-analysis/FactorReturnChart';
import FactorEquityCurveChart, {
  extractFactorEquityCurvePoints,
  shouldShowFactorEquityUnavailableNotice,
} from '@/components/ic-analysis/FactorEquityCurveChart';
import type { FactorReturnData } from '@/lib/types';

beforeAll(() => {
  // recharts ResponsiveContainer 依賴 RO contentRect + getBoundingClientRect
  class RO {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private cb: (entries: any[]) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    constructor(cb: (entries: any[]) => void) {
      this.cb = cb;
    }
    observe(el: Element) {
      this.cb([
        {
          target: el,
          contentRect: { width: 500, height: 300, top: 0, left: 0, bottom: 300, right: 500, x: 0, y: 0, toJSON() {} },
        },
      ]);
    }
    unobserve() {}
    disconnect() {}
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).ResizeObserver = RO;
  HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
    return {
      width: 500,
      height: 300,
      top: 0,
      left: 0,
      bottom: 300,
      right: 500,
      x: 0,
      y: 0,
      toJSON() {},
    } as DOMRect;
  };
});

beforeEach(() => {
  rechartsCapture.reset();
});

afterEach(() => {
  cleanup();
});

const LS_CUMULATIVE = [0, 0, -0.03, -0.0494, -0.0494, -0.020882, 0.0280739];

/** SPEC §P F3 L99 寫死 ok union fixture(含 return_transform:"identity") */
const okUnionFixture: FactorReturnData = {
  status: 'ok',
  value: {
    schema_version: 'fr_full_v1',
    semantics: 'single_asset_factor_timing_ls',
    quantile_fit: 'pit_expanding',
    return_transform: 'identity',
    features: {
      f1: {
        long_short_mean_return: 0.0042857,
        ls_cumulative_sampled: LS_CUMULATIVE,
        risk_metrics: { sharpe_ratio: 1.2 },
      },
    },
  },
  reason: null,
};

const unavailableUnion: FactorReturnData = {
  status: 'unavailable',
  value: null,
  reason: 'ls_returns_timestamp_misaligned (1c-FR-FULL)',
};

/** legacy 有限 feature map(無 status 鍵) */
const legacyFinitePayload = {
  feat_a: {
    quantile_returns_summary: { Q1: 0.01, Q5: 0.05 },
    long_short_mean_return: 0.042,
    risk_metrics: { sharpe: 1.2, max_drawdown: -0.1 },
  },
};

/** 以 ok fixture 為底,覆寫 value 一鍵(malformed-union 用) */
function withValueOverride(
  override: Partial<FactorReturnData['value'] extends infer V ? (V extends null ? never : V) : never> &
    Record<string, unknown>
): unknown {
  return {
    status: 'ok',
    reason: null,
    value: {
      schema_version: 'fr_full_v1',
      semantics: 'single_asset_factor_timing_ls',
      quantile_fit: 'pit_expanding',
      return_transform: 'identity',
      features: {
        f1: { ls_cumulative_sampled: LS_CUMULATIVE },
      },
      ...override,
    },
  };
}

describe('FactorReturnChart (IC1CFR F3.1 / F3-FIX)', () => {
  it('renders_ok_series: ok union → 繪 7 點 + title 含「單標的擇時」+ 真 Line wiring', () => {
    expect(isFactorReturnOkUnion(okUnionFixture)).toBe(true);
    const points = extractFactorReturnChartPoints(okUnionFixture);
    expect(points).toHaveLength(7);
    // 點值來自 ls_cumulative_sampled(非假 wiring)
    expect(points.map((p) => p.f1)).toEqual(LS_CUMULATIVE);

    const { container } = render(<FactorReturnChart data={okUnionFixture} />);
    // title 含「單標的擇時」(正名)
    expect(container.textContent).toContain('單標的擇時');
    expect(container.textContent).toContain(FACTOR_RETURN_CHART_TITLE);
    expect(screen.getByTestId('factor-return-chart')).toBeTruthy();
    // production 禁 hidden mirror / test-only payload DOM
    expect(screen.queryByTestId('factor-return-chart-payload')).toBeNull();
    expect(container.querySelector('[hidden]')).toBeNull();
    expect(container.querySelector('.recharts-responsive-container')).toBeTruthy();
    expect(screen.queryByTestId('factor-return-unavailable')).toBeNull();

    // 真 <Line dataKey> 繫到 feature 名;LineChart data 值 = ls_cumulative_sampled
    expect(rechartsCapture.lineDataKeys).toEqual(['f1']);
    expect(rechartsCapture.chartData.length).toBeGreaterThanOrEqual(1);
    const chartRows = rechartsCapture.chartData[0] as Array<{ index: number; f1?: number | null }>;
    expect(chartRows).toHaveLength(7);
    expect(chartRows.map((r) => r.f1)).toEqual(LS_CUMULATIVE);
  });

  it('malformed_union_rejected: 缺任一 required metadata → 不繪(legacy/空態)', () => {
    const cases: Array<{ label: string; payload: unknown }> = [
      { label: 'missing_schema_version', payload: withValueOverride({ schema_version: undefined }) },
      { label: 'wrong_schema_version', payload: withValueOverride({ schema_version: 'legacy_v0' }) },
      { label: 'missing_semantics', payload: withValueOverride({ semantics: undefined }) },
      {
        label: 'wrong_semantics',
        payload: withValueOverride({ semantics: 'cross_section_ls' }),
      },
      { label: 'missing_quantile_fit', payload: withValueOverride({ quantile_fit: undefined }) },
      {
        label: 'wrong_quantile_fit',
        payload: withValueOverride({ quantile_fit: 'full_sample' }),
      },
      {
        label: 'missing_return_transform',
        payload: withValueOverride({ return_transform: undefined }),
      },
      {
        label: 'wrong_return_transform',
        payload: withValueOverride({ return_transform: 'log' }),
      },
      { label: 'empty_features', payload: withValueOverride({ features: {} }) },
      { label: 'missing_features', payload: withValueOverride({ features: undefined }) },
    ];

    for (const { label, payload } of cases) {
      rechartsCapture.reset();
      expect(isFactorReturnOkUnion(payload), label).toBe(false);
      expect(extractFactorReturnChartPoints(payload), label).toEqual([]);
      expect(shouldShowFactorReturnUnavailableNotice(payload), label).toBe(true);

      const { container, unmount } = render(
        <FactorReturnChart data={payload as FactorReturnData} />
      );
      expect(screen.getByTestId('factor-return-unavailable'), label).toBeTruthy();
      expect(container.querySelector('.recharts-line'), label).toBeNull();
      expect(container.querySelector('.recharts-responsive-container'), label).toBeNull();
      expect(rechartsCapture.lineDataKeys, label).toEqual([]);
      unmount();
      cleanup();
    }
  });

  it('legacy_finite_payload_rejected: 裸 map → 空態警示不繪', () => {
    expect(isFactorReturnLegacyFinitePayload(legacyFinitePayload)).toBe(true);
    expect(shouldShowFactorReturnUnavailableNotice(legacyFinitePayload)).toBe(true);
    expect(extractFactorReturnChartPoints(legacyFinitePayload)).toEqual([]);

    const { container } = render(
      <FactorReturnChart data={legacyFinitePayload as unknown as FactorReturnData} />
    );
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_LEGACY_REJECTED_NOTICE);
    // 禁 fallback 數值出現在 DOM
    expect(container.textContent).not.toMatch(/0\.042/);
    expect(container.textContent).not.toMatch(/0\.05/);
    expect(container.querySelector('.recharts-line')).toBeNull();
    expect(container.querySelector('.recharts-responsive-container')).toBeNull();
  });

  it('equity_stays_unavailable: Equity 圖保持 unavailable(禁 quantile 位置相減)', () => {
    const legacyQuantile = {
      quantile_mean_returns: { Q1: 0.01, Q5: 0.05 },
      long_short_spread: 0.04,
      cumulative_returns: {
        high: [0.01, 0.02, 0.03],
        low: [0.0, -0.01, -0.02],
      },
    };
    expect(extractFactorEquityCurvePoints(legacyQuantile as never)).toEqual([]);
    expect(shouldShowFactorEquityUnavailableNotice(legacyQuantile as never)).toBe(true);

    const { container } = render(
      <FactorEquityCurveChart data={legacyQuantile as never} featureName="feat_x" />
    );
    expect(screen.getByTestId('factor-equity-unavailable')).toBeTruthy();
    expect(container.querySelector('.recharts-line')).toBeNull();
    expect(container.querySelector('.recharts-responsive-container')).toBeNull();
  });

  it('shows_unavailable_notice: §U unavailable → 警示', () => {
    render(<FactorReturnChart data={unavailableUnion} />);
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_UNAVAILABLE_NOTICE);
    expect(notice.textContent).toMatch(/1c-FR/);
    expect(document.querySelector('.recharts-line')).toBeNull();
  });

  it('missing_key_shows_unavailable_notice: data null → 下架警示', () => {
    render(<FactorReturnChart data={null} />);
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_UNAVAILABLE_NOTICE);
    expect(document.querySelector('.recharts-line')).toBeNull();
  });

  it('loading / error 態', () => {
    const { rerender } = render(<FactorReturnChart data={null} loading />);
    expect(screen.getByTestId('factor-return-loading').textContent).toMatch(/載入中/);

    rerender(<FactorReturnChart data={null} error="deep failed" />);
    expect(screen.getByTestId('factor-return-error').textContent).toContain('deep failed');
  });

  it('types: FactorReturnData 為 §U + literal 鎖死(無 | string 放寬)', () => {
    const typesPath = resolve(__dirname, '../../lib/types.ts');
    const src = readFileSync(typesPath, 'utf8');
    expect(src).toMatch(
      /export type FactorReturnData\s*=\s*FactorReturnDataOk\s*\|\s*FactorReturnDataUnavailable/
    );
    expect(src).toMatch(/status:\s*'unavailable'/);
    expect(src).toMatch(/value:\s*null/);
    expect(src).toMatch(/schema_version:\s*'fr_full_v1'/);
    expect(src).toMatch(/semantics:\s*'single_asset_factor_timing_ls'/);
    expect(src).toMatch(/quantile_fit:\s*'pit_expanding'/);
    expect(src).toMatch(/return_transform:\s*'identity'/);
    // 禁 `| string` 放寬(composer-4)
    expect(src).not.toMatch(/schema_version:\s*'fr_full_v1'\s*\|\s*string/);
    expect(src).not.toMatch(/semantics:\s*'single_asset_factor_timing_ls'\s*\|\s*string/);
    expect(src).not.toMatch(/quantile_fit:\s*'pit_expanding'\s*\|\s*string/);
    expect(src).not.toMatch(/return_transform:\s*'identity'\s*\|\s*string/);
    expect(isFactorReturnUnavailableUnion(unavailableUnion)).toBe(true);
  });

  it('grep 錨點: 元件源碼含 1c-FR + 正名 title + 無 production hidden mirror', () => {
    const chartPath = resolve(__dirname, './FactorReturnChart.tsx');
    const src = readFileSync(chartPath, 'utf8');
    const matches = src.match(/1c-FR/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(src).toContain('單標的因子擇時多空');
    // production 禁 test-only hidden mirror
    expect(src).not.toMatch(/factor-return-chart-payload/);
    expect(src).not.toMatch(/data-chart=\{/);
    expect(src).not.toMatch(/\bhidden\b/);
    // user-facing 禁舊文案(字串拆寫以免 deny-list rg 誤命中 test 本體)
    const bannedA = ['C13 Fact', 'or Ret', 'urn'].join('');
    const bannedB = ['分', '位收', '益'].join('');
    expect(src.includes(bannedA)).toBe(false);
    expect(src.includes(bannedB)).toBe(false);
  });
});
