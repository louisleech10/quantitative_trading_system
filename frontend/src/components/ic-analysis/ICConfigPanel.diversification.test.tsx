import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import ICConfigPanel from '@/components/ic-analysis/ICConfigPanel';
import { ICAnalysisConfig } from '@/lib/types';

// ICPERF Task 0.4 ㊲：設定面板之多元化約束（開關＋三數值）。

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

const baseConfig: ICAnalysisConfig = {
  features_path: '',
  mode: 'global',
  horizons: [1, 5],
  thresholds: { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, correlation_threshold: 0.7 },
};

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

describe('ICConfigPanel diversification settings', () => {
  it('shows backend defaults with toggle off and number inputs disabled when unset', () => {
    renderPanel(baseConfig);
    const box = screen.getAllByTestId('diversification-settings')[0];
    const toggle = within(box).getByRole('checkbox', { name: '啟用多元化約束' }) as HTMLInputElement;
    expect(toggle.checked).toBe(false);
    const inputs = box.querySelectorAll('input[type="number"]');
    expect(Array.from(inputs).map((el) => (el as HTMLInputElement).value)).toEqual(['3', '2', '0.4']);
    expect(Array.from(inputs).every((el) => (el as HTMLInputElement).disabled)).toBe(true);
  });

  it('toggling on emits the full diversification object with enabled=true', () => {
    const onChange = renderPanel(baseConfig);
    const box = screen.getAllByTestId('diversification-settings')[0];
    fireEvent.click(within(box).getByRole('checkbox', { name: '啟用多元化約束' }));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange.mock.calls[0][0].diversification).toEqual({
      enabled: true, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.4,
    });
    expect(onChange.mock.calls[0][0].thresholds).toEqual(baseConfig.thresholds);
  });

  it('editing a value when enabled keeps the other three keys', () => {
    const onChange = renderPanel({
      ...baseConfig,
      diversification: { enabled: true, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.4 },
    });
    const box = screen.getAllByTestId('diversification-settings')[0];
    const inputs = box.querySelectorAll('input[type="number"]');
    fireEvent.change(inputs[2], { target: { value: '0.3' } });
    expect(onChange.mock.calls.at(-1)?.[0].diversification).toEqual({
      enabled: true, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.3,
    });
    fireEvent.change(inputs[0], { target: { value: '4' } });
    expect(onChange.mock.calls.at(-1)?.[0].diversification.min_categories).toBe(4);
  });
});
