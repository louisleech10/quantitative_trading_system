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
