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

  it('ICHC 4.1：事件 fallback → 副文案（含 reason）', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
      metadata: {
        event_filter: { fallback: true, reason: 'insufficient_events' },
      },
    } as unknown as ICReport);
    render(<DegradedBanner />);
    expect(screen.getByTestId('degraded-banner-event')).toBeTruthy();
    expect(screen.getByText(/事件樣本不足，已退回全樣本分析/)).toBeTruthy();
    expect(screen.getByText('insufficient_events')).toBeTruthy();
  });

  it('ICHC 4.1：degraded 但無事件 fallback → 無副文案（主文案不變）', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
      metadata: { event_filter: { mode: 'none' } },
    } as unknown as ICReport);
    render(<DegradedBanner />);
    expect(screen.getByTestId('degraded-banner')).toBeTruthy();
    expect(screen.queryByTestId('degraded-banner-event')).toBeNull();
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

// ══════════════════════════════════════════════════════════════════════════
// `GAP3_EVENT_DISCLOSURE` Task 1.3 — 降級之原因與門檻（2026-09-06 UAT B22-9）
// ══════════════════════════════════════════════════════════════════════════

describe('Task 1.3 — oos_downgrade 之具體原因與門檻', () => {
  it('🔴 有 oos_downgrade ⇒ 顯示 reason 與三個數字（不只籠統警語）', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
      metadata: {
        oos_downgrade: {
          reason: 'rolling_warmup_insufficient',
          train_rows: 82,
          test_rows: 30,
          min_test_rows: 131,
        },
      },
    } as unknown as ICReport);
    render(<DegradedBanner />);
    const el = screen.getByTestId('ic-oos-downgrade');
    expect(el.textContent).toContain('rolling_warmup_insufficient');
    expect(el.textContent).toContain('82');
    expect(el.textContent).toContain('30');
    expect(el.textContent).toContain('131');
    // 🔴 必須講清楚「列數 ≠ 事件數」——否則使用者會直接拿事件數去對 131
    expect(el.textContent).toContain('列數不等於事件數');
  });

  it('🔴 正向對照：降級但**沒有** oos_downgrade ⇒ 不 render 該行（不得填假值）', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
    } as ICReport);
    render(<DegradedBanner />);
    expect(screen.getByTestId('degraded-banner')).toBeTruthy();
    expect(screen.queryByTestId('ic-oos-downgrade')).toBeNull();
  });

  it('🔴 正向對照：ok_oos ⇒ 整個 banner 都不出現（本欄不得讓 banner 恆顯示）', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'ok_oos',
      oos_guarantees: true,
      metadata: { oos_downgrade: null },
    } as unknown as ICReport);
    const { container } = render(<DegradedBanner />);
    expect(container.firstChild).toBeNull();
  });
});

describe('R1 閉合 — 有 reason 但沒有列數（非 fallback 之四條降級分支）', () => {
  it('🔴 列數為 null ⇒ **不得**印「null 列」，改講這個 reason 的意思', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
      metadata: {
        oos_downgrade: {
          reason: 'event_filter_fallback',
          train_rows: null, test_rows: null, min_test_rows: null,
        },
      },
    } as unknown as ICReport);
    render(<DegradedBanner />);
    const el = screen.getByTestId('ic-oos-downgrade');
    expect(el.textContent).toContain('event_filter_fallback');
    expect(el.textContent).not.toContain('null');
    expect(screen.getByTestId('ic-oos-downgrade-no-rows')).toBeTruthy();
  });

  it('正向對照：三個列數齊全 ⇒ 顯示列數段，且**不**顯示「沒有列數」那段', () => {
    useICAnalysisStore.getState().setReport({
      analysis_status: 'degraded_full_sample',
      oos_guarantees: false,
      metadata: {
        oos_downgrade: {
          reason: 'rolling_warmup_insufficient',
          train_rows: 82, test_rows: 30, min_test_rows: 131,
        },
      },
    } as unknown as ICReport);
    render(<DegradedBanner />);
    expect(screen.getByTestId('ic-oos-downgrade').textContent).toContain('131');
    expect(screen.queryByTestId('ic-oos-downgrade-no-rows')).toBeNull();
  });
});
