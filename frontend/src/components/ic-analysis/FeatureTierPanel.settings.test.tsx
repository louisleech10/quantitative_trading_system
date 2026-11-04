import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import FeatureTierPanel from '@/components/ic-analysis/FeatureTierPanel';
import ICRunSettingsLine from '@/components/ic-analysis/ICRunSettingsLine';
import { IC_AUTOCORR_TIPS, IC_SETTING_TIPS } from '@/components/ic-analysis/icSettingsText';
import { DEFAULT_IC_SETTINGS, IC_SETTING_KEYS } from '@/lib/icConfigOverride';

// ICPERF Task 0.4 ㊸：IC 頁方法選擇（四選單＋單調性開關）、每項一個 ⓘ、報告頂端「本次設定」一行。
// v5.58 (w)：IC 自相關改為報告表之欄（ⓘ 在表頭），設定面板與「本次設定」不再列。

afterEach(() => {
  cleanup();
});

function renderPanel(onChangeSetting = vi.fn(), settings = DEFAULT_IC_SETTINGS) {
  render(
    <FeatureTierPanel
      featureTier="intermediate"
      featureToggles={{}}
      onChangeTier={vi.fn()}
      onToggleFeature={vi.fn()}
      settings={settings}
      onChangeSetting={onChangeSetting}
    />,
  );
  return onChangeSetting;
}

describe('FeatureTierPanel 方法選擇', () => {
  it('五個設定各恰一個 ⓘ（IC 自相關不在面板）；文案皆非空且一行（無換行、≤ 80 字）', () => {
    renderPanel();
    const box = screen.getByTestId('ic-method-settings');
    for (const key of IC_SETTING_KEYS) {
      const row = within(box).getByTestId(`ic-setting-${key}`);
      expect(within(row).getAllByRole('button', { name: /說明$/ })).toHaveLength(1);
    }
    expect(within(box).queryByTestId('ic-setting-ic_autocorrelation')).toBeNull();
    for (const text of [...Object.values(IC_SETTING_TIPS), ...Object.values(IC_AUTOCORR_TIPS)]) {
      expect(text.trim().length).toBeGreaterThan(0);
      expect(text).not.toMatch(/\n/);
      expect(text.length).toBeLessThanOrEqual(80);
    }
  });

  it('IC 方法 ⓘ 揭露顯著性 p 值隨所選方法檢定（ICPERF ㊹；EWC 後重測 toggle 影響之結論）', () => {
    const tip = IC_SETTING_TIPS.ic_method_selection;
    expect(tip).toMatch(/p 值/);
    expect(tip).toMatch(/依所選方法/);
    expect(tip).toMatch(/Kendall 結果較接近預設/);
    expect(tip).toMatch(/Pearson 倖存集合變動較大/);
  });

  it('選單初值＝預設；改選即回呼（鍵, 值）', () => {
    const onChange = renderPanel();
    const select = screen.getByRole('combobox', { name: 'IC 方法' }) as HTMLSelectElement;
    expect(select.value).toBe('spearman');
    fireEvent.change(select, { target: { value: 'kendall' } });
    expect(onChange).toHaveBeenCalledWith('ic_method_selection', 'kendall');
    fireEvent.change(screen.getByRole('combobox', { name: '去重方法' }), { target: { value: 'vif' } });
    expect(onChange).toHaveBeenLastCalledWith('redundancy_method_selection', 'vif');
  });

  it('單調性門檻為可關之開關（不再鎖定）', () => {
    const onChange = renderPanel();
    const box = screen.getByTestId('ic-setting-monotonicity_test');
    fireEvent.click(within(box).getByRole('checkbox', { name: '單調性門檻' }));
    expect(onChange).toHaveBeenCalledWith('monotonicity_test', false);
  });

  it('收益率選單不含 excess（IC 頁無基準價來源）', () => {
    renderPanel();
    const select = screen.getByRole('combobox', { name: '收益率類型' }) as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toEqual(['simple', 'log', 'risk_adjusted']);
  });
});

describe('ICRunSettingsLine 本次設定', () => {
  it('無快照 ⇒ 不渲染', () => {
    const { container } = render(<ICRunSettingsLine settings={null} />);
    expect(container.textContent).toBe('');
  });

  it('列出全部設定；只有非預設項標記 changed', () => {
    render(
      <ICRunSettingsLine settings={{ ...DEFAULT_IC_SETTINGS, ic_method_selection: 'pearson', monotonicity_test: false }} />,
    );
    const line = screen.getByTestId('ic-run-settings-line');
    expect(line.textContent).toContain('本次設定');
    const changed = IC_SETTING_KEYS.filter(
      (key) => screen.getByTestId(`ic-run-setting-${key}`).getAttribute('data-changed') === 'true',
    );
    expect(changed).toEqual(['ic_method_selection', 'monotonicity_test']);
    expect(screen.getByTestId('ic-run-setting-monotonicity_test').textContent).toContain('關');
    expect(screen.queryByTestId('ic-run-setting-ic_autocorrelation')).toBeNull();
  });
});
