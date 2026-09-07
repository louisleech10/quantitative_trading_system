import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeAll } from 'vitest';
import ICConfigPanel from '@/components/ic-analysis/ICConfigPanel';
import { ICAnalysisConfig, RunInfo } from '@/lib/types';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const baseConfig: ICAnalysisConfig = {
  features_path: '',
  mode: 'global',
  horizons: [1, 5],
  thresholds: {
    ic_mean_min: 0.02,
    icir_min: 0.5,
    p_value_max: 0.05,
    correlation_threshold: 0.7,
  },
};

const sampleRun: RunInfo = {
  symbol: 'BTCUSDT',
  timeframe: '12h',
  config_hash: 'hash-a',
  batch_id: 'batch-1',
  batch_alias: 'wave-a',
  training_timeframes: ['12h', '1h'],
  active: false,
  browse_task_id: 'browse-1',
  browse_ready: true,
};

describe('ICConfigPanel run selector', () => {
  it('disables run button when config_hash missing', () => {
    render(
      <ICConfigPanel
        config={baseConfig}
        runs={[sampleRun]}
        featureTier="intermediate"
        featureToggles={{}}
        onChangeFeatureTier={vi.fn()}
        onToggleFeature={vi.fn()}
        onConfigChange={vi.fn()}
        onRunAnalysis={vi.fn()}
        isRunning={false}
      />
    );

    const runButton = screen.getAllByRole('button', { name: '啟動 IC 分析' })[0];
    expect(runButton.hasAttribute('disabled')).toBe(true);
  });

  it('enables run button when config_hash selected', () => {
    const { container } = render(
      <ICConfigPanel
        config={{
          ...baseConfig,
          symbol: 'BTCUSDT',
          timeframe: '12h',
          config_hash: 'hash-a',
        }}
        runs={[sampleRun]}
        featureTier="intermediate"
        featureToggles={{}}
        onChangeFeatureTier={vi.fn()}
        onToggleFeature={vi.fn()}
        onConfigChange={vi.fn()}
        onRunAnalysis={vi.fn()}
        isRunning={false}
      />
    );

    const runButton = container.querySelector('button:last-of-type');
    expect(runButton?.hasAttribute('disabled')).toBe(false);
  });

  it('does not render legacy path inputs', () => {
    render(
      <ICConfigPanel
        config={baseConfig}
        runs={[sampleRun]}
        featureTier="intermediate"
        featureToggles={{}}
        onChangeFeatureTier={vi.fn()}
        onToggleFeature={vi.fn()}
        onConfigChange={vi.fn()}
        onRunAnalysis={vi.fn()}
        isRunning={false}
      />
    );

    expect(screen.queryByPlaceholderText(/features/)).toBeNull();
  });

  it('shows runs loading state', () => {
    render(
      <ICConfigPanel
        config={baseConfig}
        runs={[]}
        runsLoading
        featureTier="intermediate"
        featureToggles={{}}
        onChangeFeatureTier={vi.fn()}
        onToggleFeature={vi.fn()}
        onConfigChange={vi.fn()}
        onRunAnalysis={vi.fn()}
        isRunning={false}
      />
    );

    expect(screen.getByText('載入 runs...')).toBeTruthy();
  });
});

// ══════════════════════════════════════════════════════════════════════════
// UAT（2026-09-07）：單獨一個 run 在選單裡消失
// ══════════════════════════════════════════════════════════════════════════

/** 使用者實機那一個：無 batch_id、該週期只有它一個。 */
const soloRun: RunInfo = {
  symbol: 'ETHUSDT',
  timeframe: '1h',
  config_hash: 'c32097ad35133dd83cfa44b6dbcbadfa',
  batch_id: null,
  batch_alias: null,
  alias: 'ETHUSDT 1h for IC',
  training_timeframes: ['1h'],
  active: false,
  browse_task_id: 'browse-solo',
  browse_ready: true,
} as RunInfo;

function renderPanel(runs: RunInfo[], config: ICAnalysisConfig = baseConfig) {
  return render(
    <ICConfigPanel
      config={config}
      runs={runs}
      featureTier="intermediate"
      featureToggles={{}}
      onChangeFeatureTier={vi.fn()}
      onToggleFeature={vi.fn()}
      onConfigChange={vi.fn()}
      onRunAnalysis={vi.fn()}
      isRunning={false}
    />
  );
}

describe('UAT：單獨一個 run 也必須選得到', () => {
  it('🔴 該週期只有一個 browse_ready 的 run ⇒ 選單**不得**是「無可選 run」', () => {
    renderPanel([soloRun]);
    // 出生事故：`groupRunsByBatch` 尾端無條件 `.filter(items.length >= 2)`
    // ——那條是為橫截面（至少兩個 symbol）設的，卻套用在單一 run 選單上。
    // 實測 13 個 browse_ready 的 run 只有這一個被丟掉。
    expect(screen.queryByText('無可選 run，請先去 Feature Factory 生成')).toBeNull();
  });

  it('選單觸發器不得為 disabled（有東西可選）', () => {
    const { container } = renderPanel([soloRun]);
    const trigger = container.querySelector('[role="combobox"]');
    expect(trigger).not.toBeNull();
    expect(trigger!.hasAttribute('disabled')).toBe(false);
  });

  it('🔴 橫截面仍需 ≥2 symbol——單一 run 不得被當成可做橫截面', () => {
    renderPanel([soloRun], { ...baseConfig, mode: 'cross_sectional' });
    // 批次選單在只有一個 symbol 時應為「無可用批次」
    // （用 getAllBy：placeholder 與 SelectValue 各出現一次，非重複渲染缺陷）
    expect(screen.getAllByText('無可用批次').length).toBeGreaterThan(0);
    // 啟動鍵必須是 disabled——橫截面在一個 symbol 上不成立
    const runButton = screen.getAllByRole('button', { name: '啟動 IC 分析' })[0];
    expect(runButton.hasAttribute('disabled')).toBe(true);
  });
});
