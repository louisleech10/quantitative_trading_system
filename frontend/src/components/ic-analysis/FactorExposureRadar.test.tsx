/**
 * B5 remediation：FactorExposureRadar
 * - legacy：byte-faithful 真 p0 舊 stub 形（null 數值、無 intercept、有 factor_betas、無 status）
 * - unavailable：專屬文案唯一斷言 + 通用空態反向基線
 * - source-selection：exposure 來自 portfolio_exposure，非幽靈 factor_betas
 */
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import FactorExposureRadar from '@/components/ic-analysis/FactorExposureRadar';
import type { FactorAttributionLegacy, FactorExposureData } from '@/lib/types';

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

describe('FactorExposureRadar (B5)', () => {
  it('legacy_factor_attribution_p0_shape_renders_without_throw', () => {
    // 忠實 p0_before.json results.factor_exposure.factor_attribution 舊形
    // （數值 null、無 intercept、有 factor_betas、無 status）
    const legacyAttribution: FactorAttributionLegacy = {
      alpha: null,
      r_squared: null,
      unexplained: null,
      attribution: {},
      factor_betas: {
        close_sma_ratio_20: 0.001969437944089369,
        hl_range: 0.034738096417277126,
        log_return_1: -0.00035502629354596134,
        log_return_3: -0.0002965122461318988,
        oc_return: -0.00011807513423264034,
        rvol_20: 0.021602262293091222,
        zscore_20: -0.04120575088059686,
      },
    };
    const legacy: FactorExposureData = {
      portfolio_exposure: {
        momentum: 0.4,
        value: 0.25,
      },
      factor_attribution: legacyAttribution,
    };

    expect(() => render(<FactorExposureRadar data={legacy} />)).not.toThrow();
    expect(screen.getByText('C20 Factor Exposure Radar')).toBeTruthy();
    expect(screen.queryByTestId('factor-exposure-radar-empty')).toBeNull();
  });

  it('unavailable_factor_attribution_renders_unique_empty_notice', () => {
    const unavailable: FactorExposureData = {
      factor_attribution: {
        status: 'unavailable',
        value: null,
        reason: 'OLS attribution not wired (stub)',
      },
    };

    expect(() => render(<FactorExposureRadar data={unavailable} />)).not.toThrow();
    const empty = screen.getByTestId('factor-exposure-radar-empty');
    expect(empty).toBeTruthy();
    // ⑥ 唯一斷言：unavailable 專屬文案（非通用「暫無曝險」寬匹配）
    expect(empty.textContent).toMatch(/因子歸因不可用/);
  });

  it('generic_empty_state_does_not_show_unavailable_notice', () => {
    // ⑥ 反向基線：無 portfolio_exposure、非 unavailable → 通用空態，不得出現專屬文案
    const genericEmpty: FactorExposureData = {};

    render(<FactorExposureRadar data={genericEmpty} />);
    const empty = screen.getByTestId('factor-exposure-radar-empty');
    expect(empty.textContent).toMatch(/暫無曝險/);
    expect(empty.textContent).not.toMatch(/因子歸因不可用/);
  });

  it('exposure_source_is_portfolio_exposure_not_factor_betas', () => {
    // ⑥ source-selection：兩來源鍵/值刻意不同；渲染只應出現 portfolio_exposure 的 factor
    const bothPresent: FactorExposureData = {
      portfolio_exposure: {
        pe_momentum: 0.55,
        pe_value: 0.22,
      },
      factor_attribution: {
        status: 'ok',
        alpha: 0.01,
        r_squared: 0.5,
        intercept: 0.01,
        unexplained: 0.5,
        // 值/鍵與 portfolio 不同；不得被當成 exposure source
        factor_betas: {
          ghost_beta_a: 0.99,
          ghost_beta_b: 0.11,
        },
        attribution: { ghost_beta_a: 0.8, ghost_beta_b: 0.2 },
      },
    };

    const { unmount } = render(<FactorExposureRadar data={bothPresent} />);
    expect(screen.queryByTestId('factor-exposure-radar-empty')).toBeNull();
    // recharts 在 jsdom 不畫軸標；以 data-active-factors 觀測實際 exposure source keys
    const chart = screen.getByTestId('factor-exposure-radar-chart');
    const active = chart.getAttribute('data-active-factors') ?? '';
    expect(active.split('|').sort()).toEqual(['pe_momentum', 'pe_value'].sort());
    expect(active).not.toMatch(/ghost_beta/);
    unmount();

    // 無 portfolio_exposure 時不得 fallback 到 factor_betas（重加 || factor_betas → 紅）
    const onlyGhostBetas: FactorExposureData = {
      factor_attribution: {
        status: 'ok',
        alpha: 0.01,
        r_squared: 0.5,
        intercept: 0.01,
        unexplained: 0.5,
        factor_betas: {
          ghost_beta_a: 0.99,
          ghost_beta_b: 0.11,
        },
        attribution: { ghost_beta_a: 0.8, ghost_beta_b: 0.2 },
      },
    };
    render(<FactorExposureRadar data={onlyGhostBetas} />);
    expect(screen.getByTestId('factor-exposure-radar-empty')).toBeTruthy();
    expect(screen.queryByTestId('factor-exposure-radar-chart')).toBeNull();
  });
});


