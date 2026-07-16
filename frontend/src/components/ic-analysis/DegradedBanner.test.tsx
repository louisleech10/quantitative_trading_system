/**
 * LA-1 B3 Task 3.3 — DegradedBanner
 * degraded → render；ok → null；欄位缺 → null 不炸
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import DegradedBanner from '@/components/ic-analysis/DegradedBanner';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { ICReport } from '@/lib/types';

afterEach(() => {
  cleanup();
  useICAnalysisStore.getState().setReport(null);
});

describe('DegradedBanner', () => {
  it('degraded → render banner', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
    } as ICReport);
    render(<DegradedBanner />);
    expect(screen.getByTestId('degraded-banner')).toBeTruthy();
    expect(screen.getByText(/research-only/i)).toBeTruthy();
  });

  it('ok_oos → null', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'ok_oos',
      oos_guarantees: true,
    } as ICReport);
    const { container } = render(<DegradedBanner />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId('degraded-banner')).toBeNull();
  });

  it('欄位缺 → null 不炸', () => {
    useICAnalysisStore.getState().setReport({ version: '1.0' } as ICReport);
    const { container } = render(<DegradedBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('report null → null', () => {
    useICAnalysisStore.getState().setReport(null);
    const { container } = render(<DegradedBanner />);
    expect(container.firstChild).toBeNull();
  });
});
