import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import ICConfigPanel from '@/components/ic-analysis/ICConfigPanel';
import DeepAnalysisConfigPanel from '@/components/ic-analysis/DeepAnalysisConfigPanel';
import { ICAnalysisConfig } from '@/lib/types';

// ICPERF SPEC v5.86 Task 0.6 (h) L1a：IC 設定面板之無數學依據上下界（② 參數上界）。
// L0 機讀表（git 物件 1eeef821）落點寫在 describe 名稱之 [rows:…]（`檔:L0 行:code_sha256 前 12 碼`），
// 由 tests/momentum/Analysis/test_icperf_limit_l1_coverage.py 自 vitest 實際執行之測試名稱取用。
// f1（SPEC (h)）：預設值皆在舊界內 ⇒ 越舊界之合法值於離開輸入框時不被夾回、送出原值；數學定義域（p∈(0,1]、相關∈[0,1]、
// 個數 ≥1）仍夾；預設值不變。

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

const baseThresholds = { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, correlation_threshold: 0.7 };

function renderPanel(config: ICAnalysisConfig, onConfigChange = vi.fn()) {
  render(
    <ICConfigPanel
      config={config}
      runs={[]}
      featureTier="intermediate"
      featureToggles={{}}
      onChangeFeatureTier={vi.fn()}
      onToggleFeature={vi.fn()}
      onConfigChange={onConfigChange}
      onRunAnalysis={vi.fn()}
      isRunning={false}
    />,
  );
  return onConfigChange;
}

function numberInputByLabel(label: string): HTMLInputElement {
  const el = screen.getAllByText(label)[0].parentElement?.querySelector('input[type="number"]');
  if (!el) throw new Error(`找不到 ${label} 之輸入框`);
  return el as HTMLInputElement;
}

function configWith(thresholds: Partial<typeof baseThresholds>, diversification?: Record<string, unknown>): ICAnalysisConfig {
  return {
    features_path: '',
    mode: 'global',
    horizons: [1, 5],
    thresholds: { ...baseThresholds, ...thresholds },
    ...(diversification ? { diversification } : {}),
  } as ICAnalysisConfig;
}

describe('ICConfigPanel L1a limits [rows:frontend/src/components/ic-analysis/ICConfigPanel.tsx:351:dbcf9b2378a9,frontend/src/components/ic-analysis/ICConfigPanel.tsx:352:48c7675a1648,frontend/src/components/ic-analysis/ICConfigPanel.tsx:359:57cb9b1a85b8,frontend/src/components/ic-analysis/ICConfigPanel.tsx:360:b577ceafee05,frontend/src/components/ic-analysis/ICConfigPanel.tsx:381:a4034a8178e6,frontend/src/components/ic-analysis/ICConfigPanel.tsx:415:d6d41e913f6a,frontend/src/components/ic-analysis/ICConfigPanel.tsx:424:d6d41e913f6a]', () => {
  it.each([
    ['ICIR 最小值', 'icir_min', 5, 5],
    ['ICIR 最小值', 'icir_min', -5, -5],
    ['P-Value 最大值', 'p_value_max', 0.0001, 0.0001],
    ['P-Value 最大值', 'p_value_max', 0.9, 0.9],
  ])('%s=%s 越舊界之合法值於離開輸入框時保留原值（%s → %s）', (label, key, value, expected) => {
    const onChange = renderPanel(configWith({ [key as string]: value }));
    fireEvent.blur(numberInputByLabel(label as string));
    expect(onChange).toHaveBeenCalled();
    expect(onChange.mock.calls.at(-1)[0].thresholds[key as string]).toBe(expected);
  });

  it('p 值門檻仍受定義域上界 1 約束', () => {
    const onChange = renderPanel(configWith({ p_value_max: 1.5 }));
    fireEvent.blur(numberInputByLabel('P-Value 最大值'));
    expect(onChange.mock.calls.at(-1)[0].thresholds.p_value_max).toBe(1);
  });

  it('相關性閾值滑桿上界為定義域 1', () => {
    renderPanel(configWith({}));
    const label = screen.getAllByText('相關性閾值')[0];
    const slider = label.closest('div')?.parentElement?.querySelector('input[type="range"]') as HTMLInputElement;
    expect(slider).toBeTruthy();
    expect(slider.max).toBe('1');
  });

  it.each([
    ['最少類別數', 'min_categories'],
    ['最少資料來源數', 'min_data_sources'],
  ])('%s 越舊界 50 之合法值保留（%s=100）', (label, key) => {
    const diversification = { enabled: true, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.4, [key]: 100 };
    const onChange = renderPanel(configWith({}, diversification));
    const box = screen.getAllByTestId('diversification-settings')[0];
    const input = within(box).getAllByText(label)[0].parentElement?.querySelector('input[type="number"]') as HTMLInputElement;
    fireEvent.blur(input);
    expect(onChange.mock.calls.at(-1)[0].diversification[key]).toBe(100);
  });

  it('預設值不變（舊預設請求）', () => {
    renderPanel(configWith({}));
    expect(numberInputByLabel('ICIR 最小值').value).toBe('0.5');
    expect(numberInputByLabel('P-Value 最大值').value).toBe('0.05');
  });
});

// 審查 r163 CODEX-R163-P1-01：cost_bps 之前端同值鏡像（深度分析面板成本輸入）。下界 0.1＝顯示解析度（L0 該行裁定非需修）。
describe('DeepAnalysisConfigPanel L1a cost_bps [rows:frontend/src/components/ic-analysis/DeepAnalysisConfigPanel.tsx:142:d9e963faf487]', () => {
  const modules = {
    factor_return: false, factor_centrality: false, trend_analysis: false, parameter_sensitivity: false, rolling_oos: false,
    factor_orthogonalization: false, factor_exposure: false, long_short_analysis: false, feature_quality_diagnostics: false,
    net_ic_analysis: true,
  };

  function renderDeep(costBps: number | null, onNetIcConfigChange = vi.fn()) {
    render(
      <DeepAnalysisConfigPanel
        selectedFeatureCount={1}
        modules={modules}
        netIcConfig={{ cost_enabled: true, cost_bps: costBps }}
        neutralizationMode="none"
        onModulesChange={vi.fn()}
        onNetIcConfigChange={onNetIcConfigChange}
        onNeutralizationModeChange={vi.fn()}
        onStart={vi.fn()}
      />,
    );
    return { input: screen.getByTestId('net-ic-cost-bps') as HTMLInputElement, onNetIcConfigChange };
  }

  it('越舊界 1000 之合法成本不標溢位、照原值送出', () => {
    const { input, onNetIcConfigChange } = renderDeep(2000);
    expect(input.hasAttribute('max')).toBe(false);
    expect(input.validity.rangeOverflow).toBe(false);
    fireEvent.change(input, { target: { value: '5000' } });
    expect(onNetIcConfigChange.mock.calls.at(-1)[0].cost_bps).toBe(5000);
  });

  it('舊界內成本與下界解析度不變', () => {
    const { input } = renderDeep(10);
    expect(input.value).toBe('10');
    expect(input.min).toBe('0.1');
    expect(input.step).toBe('0.1');
  });
});
