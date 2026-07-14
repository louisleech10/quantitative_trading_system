/**
 * IC1C-FR-STOPGAP Task 2.1 — FactorReturnChart 下架
 *
 * 具名三態:shows_unavailable_notice(union) /
 * legacy_finite_payload_not_rendered / missing_key_shows_unavailable_notice /
 * test_mutation_m3_render_legacy
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import FactorReturnChart, {
  FACTOR_RETURN_UNAVAILABLE_NOTICE,
  extractFactorReturnChartPoints,
  isFactorReturnLegacyFinitePayload,
  isFactorReturnUnavailableUnion,
  shouldShowFactorReturnUnavailableNotice,
} from '@/components/ic-analysis/FactorReturnChart';
import type { FactorReturnData } from '@/lib/types';

afterEach(() => {
  cleanup();
});

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

describe('FactorReturnChart (IC1CFR Task 2.1)', () => {
  it('shows_unavailable_notice: §U union → 警示含下架文案', () => {
    render(<FactorReturnChart data={unavailableUnion} />);
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_UNAVAILABLE_NOTICE);
    expect(notice.textContent).toMatch(/1c-FR/);
    expect(notice.textContent).toMatch(/錯位序列已下架/);
    expect(screen.queryByTestId('factor-return-loading')).toBeNull();
    expect(screen.queryByTestId('factor-return-error')).toBeNull();
    // 不得出現 recharts 線圖
    expect(document.querySelector('.recharts-line')).toBeNull();
  });

  it('legacy_finite_payload_not_rendered: 無 status 有限 map → 警示空態,不畫數值', () => {
    expect(isFactorReturnLegacyFinitePayload(legacyFinitePayload)).toBe(true);
    expect(shouldShowFactorReturnUnavailableNotice(legacyFinitePayload)).toBe(true);
    expect(extractFactorReturnChartPoints(legacyFinitePayload)).toEqual([]);

    const { container } = render(
      <FactorReturnChart data={legacyFinitePayload as unknown as FactorReturnData} />
    );
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_UNAVAILABLE_NOTICE);
    // 禁 fallback 數值出現在 DOM
    expect(container.textContent).not.toMatch(/0\.042/);
    expect(container.textContent).not.toMatch(/0\.05/);
    expect(container.querySelector('.recharts-line')).toBeNull();
    expect(container.querySelector('.recharts-responsive-container')).toBeNull();
  });

  it('missing_key_shows_unavailable_notice: data null/缺鍵 → 同下架警示', () => {
    render(<FactorReturnChart data={null} />);
    const notice = screen.getByTestId('factor-return-unavailable');
    expect(notice.textContent).toContain(FACTOR_RETURN_UNAVAILABLE_NOTICE);
    expect(notice.textContent).toMatch(/1c-FR/);
    expect(notice.textContent).toMatch(/錯位序列已下架/);
    // 不得回落通用 empty「暫無」
    expect(screen.queryByTestId('factor-return-empty')).toBeNull();
    expect(document.querySelector('.recharts-line')).toBeNull();
  });

  it('loading / error 態', () => {
    const { rerender } = render(<FactorReturnChart data={null} loading />);
    expect(screen.getByTestId('factor-return-loading').textContent).toMatch(/載入中/);

    rerender(<FactorReturnChart data={null} error="deep failed" />);
    expect(screen.getByTestId('factor-return-error').textContent).toContain('deep failed');
  });

  it('types: FactorReturnData 為 §U(源碼守衛 status/value/reason)', () => {
    const typesPath = resolve(__dirname, '../../lib/types.ts');
    const src = readFileSync(typesPath, 'utf8');
    // 實際形狀改為 union,非只新增旁路型別而保留 Record feature map 為 FactorReturnData
    expect(src).toMatch(/export type FactorReturnData\s*=\s*FactorReturnDataOk\s*\|\s*FactorReturnDataUnavailable/);
    expect(src).toMatch(/status:\s*'unavailable'/);
    expect(src).toMatch(/value:\s*null/);
    expect(isFactorReturnUnavailableUnion(unavailableUnion)).toBe(true);
  });

  it('grep 錨點: 元件源碼含 1c-FR', () => {
    const chartPath = resolve(__dirname, './FactorReturnChart.tsx');
    const src = readFileSync(chartPath, 'utf8');
    const matches = src.match(/1c-FR/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  /**
   * M3 probe: 若恢復舊邏輯(從 legacy quantile_returns_summary 抽點繪圖)→本測轉紅。
   * 基線綠: production extract 恒 [];mutation 模擬舊 extract 必有點 → 與「不畫」契約衝突。
   */
  it('test_mutation_m3_render_legacy: 恢復畫 legacy→紅', () => {
    // 舊實作(pre-stopgap FactorReturnChart chartData 邏輯)
    const legacyExtract = (
      data: typeof legacyFinitePayload
    ): Array<{ name: string; value: number }> => {
      if (!data) return [];
      const firstFeature = Object.values(data)[0] as {
        quantile_returns_summary?: Record<string, number>;
      };
      const summary = firstFeature?.quantile_returns_summary || {};
      return Object.entries(summary).map(([name, value]) => ({
        name,
        value: Number(value),
      }));
    };

    const mutatedPoints = legacyExtract(legacyFinitePayload);
    // 突變路徑確實會抽出有限點
    expect(mutatedPoints.length).toBeGreaterThan(0);
    expect(mutatedPoints.some((p) => Number.isFinite(p.value))).toBe(true);

    // 契約:production 不得抽出;若有人把 extract 改回 legacy 路徑,下列會紅
    expect(extractFactorReturnChartPoints(legacyFinitePayload)).toEqual([]);
    expect(shouldShowFactorReturnUnavailableNotice(legacyFinitePayload)).toBe(true);

    // 若「恢復畫 legacy」被接上 production extract,與 empty 斷言衝突→toThrow
    expect(() => {
      const productionPoints = extractFactorReturnChartPoints(legacyFinitePayload);
      // 模擬審查斷言:任何恢復 legacy 繪圖會讓 points 非空 → 此 expect 失敗
      expect(productionPoints).toEqual(mutatedPoints);
    }).toThrow();
  });
});
