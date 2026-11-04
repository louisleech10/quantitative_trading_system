/**
 * ICPERF SPEC v5.63 ㊹：縱向顯著性之資料不足警示與無法計算文案（p／q 欄），及「本次設定」行之顯著性揭露兩分支。
 * mutation：拿掉警示圖示、無法計算改回數值、文案漏 detail 任一鍵 ⇒ 對應案紅。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import { significanceSegment } from '@/components/ic-analysis/ICRunSettingsLine';
import type { HacDataWarningDetail, ICFeatureInfo } from '@/lib/types';

afterEach(() => cleanup());

const DETAIL: HacDataWarningDetail = {
  n_obs: 339,
  horizon: 24,
  approx_independent_n: 339 / 24,
  phi_hat: 0.991,
  alpha: 0.05,
  estimated_null_reject_rate: 0.112,
  reference_reject_rate: 0.061,
  replications: 1000,
};

const row = (name: string, extra: Partial<ICFeatureInfo>): ICFeatureInfo =>
  ({
    rank: 1, feature_name: name, ic_mean: 0.05, ic_std: 0.1, icir: 0.5, p_value: 0.0123, p_value_adj: 0.0456,
    ic_hit_rate: 0.6, monotonicity_score: 0.5, coverage: 0.99, ...extra,
  }) as unknown as ICFeatureInfo;

describe('ICSummaryTable — 資料不足警示與無法計算（㊹）', () => {
  it('small_effective_sample ⇒ 照常顯示 p／q 並加警示；ⓘ 含 n_obs、horizon、approx_independent_n、phi_hat、alpha、estimated_null_reject_rate（detail 封閉八鍵皆讀得到）', () => {
    render(
      <ICSummaryTable
        data={[row('w', { inference_status: 'ok', data_warning: 'small_effective_sample', data_warning_detail: DETAIL })]}
        analysisMode="global"
      />,
    );
    expect(screen.getByText('0.0123')).toBeTruthy();
    expect(screen.getByText('0.0456')).toBeTruthy();
    const tip = screen.getByTestId('hac-data-warning-p_value').getAttribute('title') ?? '';
    expect(screen.getByTestId('hac-data-warning-p_value_adj')).toBeTruthy();
    expect(tip).toContain('339 根');
    expect(tip).toContain('標籤 24 根');
    expect(tip).toContain('約相當於 14 筆獨立資料');
    expect(tip).toContain('0.991（中位數不偏估計）');
    expect(tip).toContain('顯著水準 0.05');
    expect(tip).toContain('11.2%');
    expect(tip).toContain('6.1%');
    expect(tip).toContain('1000 次');
    expect(tip).toContain('模型近似、非此特徵之實測誤判率');
  });

  it('insufficient_sample ⇒「無法計算：樣本不足」', () => {
    render(
      <ICSummaryTable
        data={[row('s', { p_value: null, p_value_adj: null, inference_status: 'insufficient_sample' })]}
        analysisMode="global"
      />,
    );
    expect(screen.getByTestId('hac-not-computable-p_value').textContent).toBe('無法計算：樣本不足');
    expect(screen.getByTestId('hac-not-computable-p_value_adj').textContent).toBe('無法計算：樣本不足');
  });

  it('degenerate ⇒「無法計算：序列退化」', () => {
    render(
      <ICSummaryTable
        data={[row('d', { p_value: null, p_value_adj: null, inference_status: 'degenerate' })]}
        analysisMode="global"
      />,
    );
    expect(screen.getByTestId('hac-not-computable-p_value').textContent).toBe('無法計算：序列退化');
  });

  it('persistence_not_estimable ⇒ 照常顯示 p 並標「無法評估資料是否足夠」', () => {
    render(
      <ICSummaryTable
        data={[row('pn', { inference_status: 'ok', data_warning: 'persistence_not_estimable', data_warning_detail: null })]}
        analysisMode="global"
      />,
    );
    expect(screen.getByText('0.0123')).toBeTruthy();
    const tip = screen.getByTestId('hac-persistence-not-estimable-p_value').getAttribute('title') ?? '';
    expect(tip).toContain('無法評估資料是否足夠');
    expect(screen.queryByTestId('hac-data-warning-p_value')).toBeNull();
  });

  it('warning_not_evaluated ⇒ 照常顯示 p 並標「判定未執行、可重跑」', () => {
    render(
      <ICSummaryTable
        data={[row('ne', { inference_status: 'ok', data_warning: 'warning_not_evaluated', data_warning_detail: null })]}
        analysisMode="global"
      />,
    );
    expect(screen.getByText('0.0123')).toBeTruthy();
    const tip = screen.getByTestId('hac-warning-not-evaluated-p_value').getAttribute('title') ?? '';
    expect(tip).toContain('判定未執行');
    expect(tip).toContain('重跑');
  });

  it('無警示且可計算 ⇒ 無警示圖示、無無法計算文案', () => {
    render(<ICSummaryTable data={[row('ok', { inference_status: 'ok', data_warning: null })]} analysisMode="global" />);
    expect(screen.queryByTestId('hac-data-warning-p_value')).toBeNull();
    expect(screen.queryByTestId('hac-not-computable-p_value')).toBeNull();
  });
});

describe('ICRunSettingsLine — 顯著性檢定揭露（㊹）', () => {
  it('ewc_llsw2018 ⇒ EWC（Lazarus 等 2018）與 h、n、ν、警示欄數', () => {
    const text = significanceSegment({
      hac_method: 'ewc_llsw2018', horizon: 24, n_obs_range: [339, 4070], ewc_dof_range: [19, 101], data_warning_count: 3,
    });
    expect(text).toBe('顯著性 EWC（Lazarus 等 2018）h＝24、n＝339–4070、ν＝19–101、資料不足警示 3 欄');
  });

  it('newey_west_fixed ⇒ Newey–West 固定落後 maxlags、h、n', () => {
    const text = significanceSegment({ hac_method: 'newey_west_fixed', maxlags: 30, horizon: 5, n_obs_range: [500, 500] });
    expect(text).toBe('顯著性 Newey–West 固定落後 maxlags＝30、h＝5、n＝500');
  });

  it('缺 hac_method（舊報告）⇒ 不列', () => {
    expect(significanceSegment(undefined)).toBeNull();
    expect(significanceSegment({})).toBeNull();
  });
});
