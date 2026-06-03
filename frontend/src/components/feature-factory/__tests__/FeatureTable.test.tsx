import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StatsWarmupBanner } from '../FeatureTable';

describe('StatsWarmupBanner', () => {
  it('shows provisional sort notice while stats warmup is incomplete', () => {
    render(
      <StatsWarmupBanner
        statsWarmup={{
          computed: 40,
          total: 100,
          pct: 40,
          complete: false,
        }}
      />,
    );

    expect(screen.getByText(/暖機 40%，排序暫定/)).toBeInTheDocument();
  });

  it('hides provisional sort notice when stats warmup is complete', () => {
    const { container } = render(
      <StatsWarmupBanner
        statsWarmup={{
          computed: 100,
          total: 100,
          pct: 100,
          complete: true,
        }}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('hides notice when stats_warmup is missing (legacy API)', () => {
    const { container } = render(<StatsWarmupBanner />);
    expect(container).toBeEmptyDOMElement();
  });
});
