/**
 * IC1C-FR-STOPGAP Task 2.2 — FactorEquityCurveChart 獨立下架
 *
 * 具名:equity_curve_unavailable_notice / equity_legacy_finite_not_rendered /
 * test_mutation_m4_render_legacy_equity
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import FactorEquityCurveChart, {
  FACTOR_EQUITY_UNAVAILABLE_NOTICE,
  extractFactorEquityCurvePoints,
  shouldShowFactorEquityUnavailableNotice,
} from '@/components/ic-analysis/FactorEquityCurveChart';
import type { QuantileReturnData } from '@/lib/types';

afterEach(() => {
  cleanup();
});

/** legacy finite quantile_returns(含 cumulative,可被舊圖位置相減) */
const legacyFiniteQuantile: QuantileReturnData = {
  quantile_mean_returns: { Q1: 0.01, Q5: 0.03 },
  cumulative_returns: {
    Q1: [0.0, 0.01, 0.02, 0.015],
    Q5: [0.0, 0.03, 0.06, 0.09],
  },
  long_short_spread: 0.02,
};

describe('FactorEquityCurveChart (IC1CFR Task 2.2)', () => {
  it('equity_curve_unavailable_notice: 有/無 data 皆警示下架文案', () => {
    render(
      <FactorEquityCurveChart data={legacyFiniteQuantile} featureName="feat_x" />
    );
    const notice = screen.getByTestId('factor-equity-unavailable');
    expect(notice.textContent).toContain(FACTOR_EQUITY_UNAVAILABLE_NOTICE);
    expect(notice.textContent).toMatch(/1c-FR/);
    expect(notice.textContent).toMatch(/錯位序列已下架/);
    expect(document.querySelector('.recharts-line')).toBeNull();
    expect(document.querySelector('.recharts-area')).toBeNull();
  });

  it('equity_legacy_finite_not_rendered: legacy finite 不畫 L-S / 不顯示有限指標', () => {
    expect(extractFactorEquityCurvePoints(legacyFiniteQuantile)).toEqual([]);
    expect(shouldShowFactorEquityUnavailableNotice(legacyFiniteQuantile)).toBe(true);

    const { container } = render(
      <FactorEquityCurveChart data={legacyFiniteQuantile} featureName="feat_x" />
    );
    expect(screen.getByTestId('factor-equity-unavailable').textContent).toContain(
      FACTOR_EQUITY_UNAVAILABLE_NOTICE
    );
    // 舊圖會算 Total Return / Sharpe 有限值;下架後不得出現 metrics 區數值
    expect(container.textContent).not.toMatch(/Total Return/);
    expect(container.textContent).not.toMatch(/Sharpe Ratio/);
    expect(container.querySelector('.recharts-responsive-container')).toBeNull();
    // 不得把 Q5-Q1 spread 有限值寫入 DOM
    expect(container.textContent).not.toMatch(/0\.075/);
  });

  it('loading / error / empty(null data) 三態', () => {
    const { rerender } = render(
      <FactorEquityCurveChart data={null} loading featureName="f" />
    );
    expect(screen.getByTestId('factor-equity-loading').textContent).toMatch(/載入中/);

    rerender(<FactorEquityCurveChart data={null} error="boom" featureName="f" />);
    expect(screen.getByTestId('factor-equity-error').textContent).toContain('boom');

    // null data 仍下架警示(主流程缺鍵亦不得暗示可繪)
    rerender(<FactorEquityCurveChart data={null} featureName="f" />);
    expect(screen.getByTestId('factor-equity-unavailable').textContent).toContain(
      FACTOR_EQUITY_UNAVAILABLE_NOTICE
    );
  });

  it('page 掛載: FactorEquityCurveChart 用於主流程 quantile_returns 路徑(源碼守衛)', () => {
    const pagePath = resolve(__dirname, '../../app/ic-analysis/page.tsx');
    const src = readFileSync(pagePath, 'utf8');
    expect(src).toMatch(/FactorEquityCurveChart/);
    expect(src).toMatch(/quantile_returns/);
    // 必須傳 loading/error 三態
    expect(src).toMatch(/FactorEquityCurveChart[\s\S]*?loading=\{/);
  });

  it('grep 錨點: 元件源碼含 1c-FR', () => {
    const chartPath = resolve(__dirname, './FactorEquityCurveChart.tsx');
    const src = readFileSync(chartPath, 'utf8');
    expect((src.match(/1c-FR/g) || []).length).toBeGreaterThanOrEqual(1);
  });

  /**
   * M4 probe: 若恢復舊位置相減 equity 繪圖 → 本測轉紅。
   * 舊邏輯: low=Q1 / high=Q-high 按 bar index 做 high-low spread。
   */
  it('test_mutation_m4_render_legacy_equity: 恢復畫 legacy equity→紅', () => {
    const legacyPositionSubtract = (
      data: QuantileReturnData
    ): Array<{ bar_index: number; ls_spread: number }> => {
      const cumulative = data?.cumulative_returns;
      if (!cumulative || typeof cumulative !== 'object') return [];
      const keys = Object.keys(cumulative).sort();
      if (keys.length < 2) return [];
      const low = cumulative[keys[0]] || [];
      const high = cumulative[keys[keys.length - 1]] || [];
      const length = Math.min(low.length, high.length);
      const points: Array<{ bar_index: number; ls_spread: number }> = [];
      for (let i = 0; i < length; i += 1) {
        const l = Number(low[i]);
        const h = Number(high[i]);
        if (Number.isFinite(l) && Number.isFinite(h)) {
          points.push({ bar_index: i, ls_spread: h - l });
        }
      }
      return points;
    };

    const mutated = legacyPositionSubtract(legacyFiniteQuantile);
    expect(mutated.length).toBeGreaterThan(0);
    expect(mutated.every((p) => Number.isFinite(p.ls_spread))).toBe(true);

    // production 恒空
    expect(extractFactorEquityCurvePoints(legacyFiniteQuantile)).toEqual([]);

    // 若 production 被改回位置相減,下列 equal 成立 → 外層 toThrow 不觸發 → 測失敗
    expect(() => {
      expect(extractFactorEquityCurvePoints(legacyFiniteQuantile)).toEqual(mutated);
    }).toThrow();
  });
});
