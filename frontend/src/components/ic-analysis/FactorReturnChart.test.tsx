/**
 * IC1C-FR-FULL F3.1 — FactorReturnChart ok 上架 + 正名
 *
 * 具名三 test(SPEC §P F3):
 *   renders_ok_series / legacy_finite_payload_rejected / equity_stays_unavailable
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
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

afterEach(() => {
  cleanup();
});

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
        ls_cumulative_sampled: [0, 0, -0.03, -0.0494, -0.0494, -0.020882, 0.0280739],
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

describe('FactorReturnChart (IC1CFR F3.1)', () => {
  it('renders_ok_series: ok union → 繪 7 點 + title 含「單標的擇時」', () => {
    expect(isFactorReturnOkUnion(okUnionFixture)).toBe(true);
    const points = extractFactorReturnChartPoints(okUnionFixture);
    expect(points).toHaveLength(7);
    expect(points.map((p) => p.f1)).toEqual([
      0, 0, -0.03, -0.0494, -0.0494, -0.020882, 0.0280739,
    ]);

    const { container } = render(<FactorReturnChart data={okUnionFixture} />);
    // title 含「單標的擇時」(正名)
    expect(container.textContent).toContain('單標的擇時');
    expect(container.textContent).toContain(FACTOR_RETURN_CHART_TITLE);
    expect(screen.getByTestId('factor-return-chart')).toBeTruthy();
    // production payload: 7 點(來自 ls_cumulative_sampled)
    const payloadEl = screen.getByTestId('factor-return-chart-payload');
    const chartPayload = JSON.parse(payloadEl.getAttribute('data-chart') || '[]') as Array<{
      index: number;
      f1?: number | null;
    }>;
    expect(chartPayload).toHaveLength(7);
    expect(chartPayload.map((p) => p.f1)).toEqual([
      0, 0, -0.03, -0.0494, -0.0494, -0.020882, 0.0280739,
    ]);
    expect(container.querySelector('.recharts-responsive-container')).toBeTruthy();
    expect(screen.queryByTestId('factor-return-unavailable')).toBeNull();
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

  it('types: FactorReturnData 為 §U(源碼守衛 status/value/reason + schema_version)', () => {
    const typesPath = resolve(__dirname, '../../lib/types.ts');
    const src = readFileSync(typesPath, 'utf8');
    expect(src).toMatch(
      /export type FactorReturnData\s*=\s*FactorReturnDataOk\s*\|\s*FactorReturnDataUnavailable/
    );
    expect(src).toMatch(/status:\s*'unavailable'/);
    expect(src).toMatch(/value:\s*null/);
    expect(src).toMatch(/schema_version/);
    expect(src).toMatch(/return_transform/);
    expect(src).toMatch(/single_asset_factor_timing_ls/);
    expect(isFactorReturnUnavailableUnion(unavailableUnion)).toBe(true);
  });

  it('grep 錨點: 元件源碼含 1c-FR + 正名 title', () => {
    const chartPath = resolve(__dirname, './FactorReturnChart.tsx');
    const src = readFileSync(chartPath, 'utf8');
    const matches = src.match(/1c-FR/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(src).toContain('單標的因子擇時多空');
    // user-facing 禁舊文案(字串拆寫以免 deny-list rg 誤命中 test 本體)
    const bannedA = ['C13 Fact', 'or Ret', 'urn'].join('');
    const bannedB = ['分', '位收', '益'].join('');
    expect(src.includes(bannedA)).toBe(false);
    expect(src.includes(bannedB)).toBe(false);
  });
});
