/**
 * ICPERF Task 0.2 v5.59（code review r70 群集 L、E）：
 * (aj) 報告表「IC 自相關」ⓘ 依分析模式分句——縱向（滾動窗重疊時多近 1）、跨標的（逐時點截面 IC 之持續性）、
 *      事件型（事件序，非日曆時間）；`ICSummaryTable` 依 `analysisMode` 取用。
 * (ae) 跨標的「收益率類型」ⓘ：主 IC 標籤與 IC 衰減同依此設定（改前文案寫「主 IC 標籤固定為一根 K 線對數報酬」）。
 * mutation：表頭改回單一常數 ⇒ 三模式 title 相同而紅；文案改回「固定」⇒ (ae) 紅。
 */
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import { IC_AUTOCORR_TIPS, IC_SETTING_TIPS_XSEC, icAutocorrTip } from '@/components/ic-analysis/icSettingsText';
import type { ICAnalysisConfig, ICFeatureInfo } from '@/lib/types';

afterEach(() => cleanup());

const MODES: ICAnalysisConfig['mode'][] = ['global', 'event', 'cross_sectional'];

const row = (name: string): ICFeatureInfo =>
  ({
    rank: 1, feature_name: name, ic_mean: 0.05, ic_std: 0.1, icir: 0.5, p_value: 0.01, p_value_adj: 0.02,
    ic_hit_rate: 0.6, monotonicity_score: 0.5, coverage: 0.99, ic_autocorr: 0.42, ic_autocorr_reason: null,
  }) as unknown as ICFeatureInfo;

describe('v5.59 (aj) IC 自相關 ⓘ 分模式', () => {
  it('三模式各一句（非空、一行、≤ 80 字）且兩兩不同', () => {
    const texts = MODES.map((m) => IC_AUTOCORR_TIPS[m]);
    for (const text of texts) {
      expect(text.trim().length).toBeGreaterThan(0);
      expect(text).not.toMatch(/\n/);
      expect(text.length).toBeLessThanOrEqual(80);
    }
    expect(new Set(texts).size).toBe(MODES.length);
  });

  it('縱向講滾動窗重疊；跨標的講逐時點截面 IC、不講滾動窗；事件型註明事件序非日曆時間', () => {
    expect(IC_AUTOCORR_TIPS.global).toMatch(/滾動窗重疊/);
    expect(IC_AUTOCORR_TIPS.cross_sectional).toMatch(/截面 IC/);
    expect(IC_AUTOCORR_TIPS.cross_sectional).not.toMatch(/滾動窗/);
    expect(IC_AUTOCORR_TIPS.event).toMatch(/事件/);
    expect(IC_AUTOCORR_TIPS.event).toMatch(/非日曆時間/);
  });

  it('未知或未給模式 ⇒ 縱向句（ICSummaryTable 之 analysisMode 預設 global）', () => {
    expect(icAutocorrTip(undefined)).toBe(IC_AUTOCORR_TIPS.global);
    expect(icAutocorrTip('global')).toBe(IC_AUTOCORR_TIPS.global);
  });

  it.each(MODES)('ICSummaryTable analysisMode=%s ⇒ 表頭 ⓘ 取該模式之句', (mode) => {
    render(<ICSummaryTable data={[row('a')]} analysisMode={mode} />);
    const head = screen.getByTestId('ic-summary-ic-autocorr-head');
    const tips = within(head).getAllByRole('img', { name: /說明$/ });
    expect(tips).toHaveLength(1);
    expect(tips[0].getAttribute('title')).toBe(IC_AUTOCORR_TIPS[mode]);
  });
});

describe('v5.59 (ae) 跨標的收益率類型 ⓘ', () => {
  it('主 IC 標籤與衰減同依此設定（不再寫主標籤固定）', () => {
    const text = IC_SETTING_TIPS_XSEC.return_type_selection ?? '';
    expect(text).toMatch(/主 IC/);
    expect(text).not.toMatch(/固定/);
    expect(text).not.toMatch(/\n/);
    expect(text.length).toBeLessThanOrEqual(80);
  });
});
