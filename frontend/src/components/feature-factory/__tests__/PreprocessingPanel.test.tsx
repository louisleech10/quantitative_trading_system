import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PreprocessingPanel, { PREPROCESSING_WARNINGS } from '../PreprocessingPanel';

describe('PreprocessingPanel warnings', () => {
  it('renders yellow FracDiff and ADF warnings without blocking controls', () => {
    const { container } = render(
      <PreprocessingPanel
        config={{
          enabled: true,
          mode: 'replace',
          winsorization: {
            enabled: true,
            method: 'quantile',
            sigma_k: 3,
            quantile_range: [0.01, 0.99],
            apply_to: 'all',
          },
          adf_differencing: {
            enabled: true,
            adf_threshold: 0.1,
            max_diff: 2,
            sample_size: 500,
            apply_to: 'non_stationary',
          },
          fractional_differencing: {
            enabled: true,
            d_range: [0, 1],
            adf_threshold: 0.1,
            weight_threshold: 1e-5,
            precision: 0.02,
            apply_to: 'non_stationary',
            cache_d_star: true,
          },
          rank_transform: {
            enabled: true,
            window: 252,
            apply_to: 'all',
          },
          gaussian_normalize: {
            enabled: false,
            clip_range: [0.001, 0.999],
            apply_to: 'all',
          },
          adaptive_zscore: {
            enabled: true,
            windows: [100, 252],
            epsilon: 1e-8,
            apply_to: 'all',
          },
        }}
        onChange={vi.fn()}
      />
    );

    for (const warning of Object.values(PREPROCESSING_WARNINGS)) {
      expect(screen.getByText(warning)).toBeInTheDocument();
    }
    expect(screen.queryByText(/不可同時啟用/)).not.toBeInTheDocument();
    expect(screen.getAllByRole('checkbox').length).toBeGreaterThan(0);
    expect(container.querySelector('[data-testid="preprocessing-warnings"]')).toMatchSnapshot();
  });
});
