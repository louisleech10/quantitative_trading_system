/**
 * ICPERF Task 0.2 v5.58（code review r69 群集 A、B）：
 * (v) 跨標的模式之設定按模式生效——契約 `ui_stage_toggles.json` 之 `not_applicable_modes` 列為跨標的不適用之設定
 *     （縮尾、去重、單調性門檻；後端證不適用見 pytest `test_icperf_xsec_method.py` 第 4 節）：面板停用並標「此模式不適用」、
 *     送出時不帶、報告頂端「本次設定」不列；仍生效者（IC 方法、收益率類型）照常可改並送出。
 * (w) 報告表增「IC 自相關」欄：表頭一個 ⓘ、值兩位小數、無值顯示 `--` 並以原因為滑鼠提示。
 * mutation：拿掉模式判斷 ⇒ 停用／不送／不列三案紅；拿掉表格欄 ⇒ (w) 紅。
 */
import { readFileSync } from 'fs';
import path from 'path';
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import FeatureTierPanel from '@/components/ic-analysis/FeatureTierPanel';
import ICRunSettingsLine from '@/components/ic-analysis/ICRunSettingsLine';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import {
  IC_AUTOCORR_REASON_LABELS,
  IC_AUTOCORR_TIP,
  IC_SETTING_NOT_APPLICABLE_LABEL,
  IC_SETTING_NOT_APPLICABLE_TIPS,
  IC_SETTING_TIPS_XSEC,
} from '@/components/ic-analysis/icSettingsText';
import {
  applicableICSettingKeys,
  buildConfigOverride,
  IC_SETTING_KEYS,
  IC_SETTING_SPECS,
} from '@/lib/icConfigOverride';
import type { ICAnalysisConfig, ICFeatureInfo, ICMethodSettings } from '@/lib/types';

afterEach(() => cleanup());

const contract = JSON.parse(
  readFileSync(path.resolve(__dirname, '../../../../momentum/Analysis/contracts/ui_stage_toggles.json'), 'utf-8'),
) as {
  setting_keys: Record<string, { not_applicable_modes?: string[] }>;
  report_keys: Record<string, { summary_columns: string[]; reasons: string[] }>;
};

const XSEC_NA = Object.entries(contract.setting_keys)
  .filter(([, spec]) => (spec.not_applicable_modes ?? []).includes('cross_sectional'))
  .map(([key]) => key)
  .sort();

/** 每鍵皆設為非預設值（不適用者若仍送出／仍列即可被抓到）。 */
const ALL_NON_DEFAULT: ICMethodSettings = {
  ic_method_selection: 'kendall',
  winsorization_method: 'mad',
  return_type_selection: 'risk_adjusted',
  redundancy_method_selection: 'vif',
  monotonicity_test: false,
};

const base = (mode: ICAnalysisConfig['mode']): ICAnalysisConfig => ({
  features_path: '',
  mode,
  horizons: [1, 2, 3, 5, 8, 13, 21],
  thresholds: { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, monotonicity_score_min: 0.6, correlation_threshold: 0.7 },
  ic_settings: ALL_NON_DEFAULT,
});

const atPath = (obj: unknown, p: readonly string[]): unknown =>
  p.reduce<unknown>((cur, part) => (cur && typeof cur === 'object' ? (cur as Record<string, unknown>)[part] : undefined), obj);

describe('v5.58 (v) 跨標的不適用之設定', () => {
  it('契約之跨標的不適用集合＝縮尾、去重、單調性門檻（前端導出相同）', () => {
    expect(XSEC_NA).toEqual(['monotonicity_test', 'redundancy_method_selection', 'winsorization_method']);
    const applicable = applicableICSettingKeys('cross_sectional');
    expect([...IC_SETTING_KEYS].filter((k) => !applicable.includes(k)).sort()).toEqual(XSEC_NA);
    expect(applicableICSettingKeys('global')).toEqual(IC_SETTING_KEYS);
  });

  it('面板：跨標的模式下不適用之控制項 disabled 並標「此模式不適用」；仍生效者可改；每項仍一個 ⓘ', () => {
    render(
      <FeatureTierPanel
        featureTier="intermediate"
        featureToggles={{}}
        onChangeTier={vi.fn()}
        onToggleFeature={vi.fn()}
        analysisMode="cross_sectional"
        settings={ALL_NON_DEFAULT}
        onChangeSetting={vi.fn()}
      />,
    );
    const box = screen.getByTestId('ic-method-settings');
    for (const key of IC_SETTING_KEYS) {
      const row = within(box).getByTestId(`ic-setting-${key}`);
      const control = IC_SETTING_SPECS[key].kind === 'toggle' ? within(row).getByRole('checkbox') : within(row).getByRole('combobox');
      const na = XSEC_NA.includes(key);
      expect(row.getAttribute('data-applicable')).toBe(na ? 'false' : 'true');
      expect((control as HTMLButtonElement | HTMLSelectElement).disabled).toBe(na);
      expect(within(row).queryByText(IC_SETTING_NOT_APPLICABLE_LABEL) !== null).toBe(na);
      expect(within(row).getAllByRole('button', { name: /說明$/ })).toHaveLength(1);
    }
  });

  it('面板：全域模式下五項皆可改、無「此模式不適用」', () => {
    render(
      <FeatureTierPanel
        featureTier="intermediate"
        featureToggles={{}}
        onChangeTier={vi.fn()}
        onToggleFeature={vi.fn()}
        analysisMode="global"
        settings={ALL_NON_DEFAULT}
        onChangeSetting={vi.fn()}
      />,
    );
    expect(screen.queryAllByText(IC_SETTING_NOT_APPLICABLE_LABEL)).toHaveLength(0);
  });

  it('送出：跨標的模式不帶不適用之設定、仍帶生效者；全域模式五項皆帶', () => {
    const xsec = buildConfigOverride(base('cross_sectional'));
    const glob = buildConfigOverride(base('global'));
    for (const key of IC_SETTING_KEYS) {
      const p = IC_SETTING_SPECS[key].path;
      expect(atPath(glob, p)).toBe(ALL_NON_DEFAULT[key]);
      expect(atPath(xsec, p)).toBe(XSEC_NA.includes(key) ? undefined : ALL_NON_DEFAULT[key]);
    }
  });

  it('本次設定：跨標的模式只列生效之設定', () => {
    render(<ICRunSettingsLine settings={ALL_NON_DEFAULT} mode="cross_sectional" />);
    for (const key of IC_SETTING_KEYS) {
      expect(screen.queryByTestId(`ic-run-setting-${key}`) !== null).toBe(!XSEC_NA.includes(key));
    }
  });

  it('ⓘ 文案：不適用與跨標的專句皆一行、非空、≤ 80 字', () => {
    for (const text of [...Object.values(IC_SETTING_NOT_APPLICABLE_TIPS), ...Object.values(IC_SETTING_TIPS_XSEC)]) {
      expect(text.trim().length).toBeGreaterThan(0);
      expect(text).not.toMatch(/\n/);
      expect(text.length).toBeLessThanOrEqual(80);
    }
    expect(Object.keys(IC_SETTING_NOT_APPLICABLE_TIPS).sort()).toEqual(XSEC_NA);
  });
});

describe('v5.58 (w) 報告表 IC 自相關欄', () => {
  const row = (name: string, ac: number | null, reason: string | null): ICFeatureInfo =>
    ({
      rank: 1, feature_name: name, ic_mean: 0.05, ic_std: 0.1, icir: 0.5, p_value: 0.01, p_value_adj: 0.02,
      ic_hit_rate: 0.6, monotonicity_score: 0.5, coverage: 0.99, ic_autocorr: ac, ic_autocorr_reason: reason,
    }) as unknown as ICFeatureInfo;

  it('表頭一個 ⓘ（一句說明）；有值兩位小數、無值 -- 並以原因為提示', () => {
    render(<ICSummaryTable data={[row('a', 0.734, null), row('b', null, 'constant_series')]} />);
    const head = screen.getByTestId('ic-summary-ic-autocorr-head');
    const tips = within(head).getAllByRole('img', { name: /說明$/ });
    expect(tips).toHaveLength(1);
    expect(tips[0].getAttribute('title')).toBe(IC_AUTOCORR_TIP);
    const cells = screen.getAllByTestId('ic-summary-ic-autocorr');
    expect(cells.map((c) => c.textContent)).toEqual(['0.73', '--']);
    expect(cells[1].getAttribute('title')).toBe(IC_AUTOCORR_REASON_LABELS.constant_series);
  });

  it('原因標籤之鍵集＝契約 report_keys.ic_autocorrelation.reasons', () => {
    expect(Object.keys(IC_AUTOCORR_REASON_LABELS).sort()).toEqual([...contract.report_keys.ic_autocorrelation.reasons].sort());
    expect(contract.report_keys.ic_autocorrelation.summary_columns).toEqual(['ic_autocorr', 'ic_autocorr_reason']);
  });
});
