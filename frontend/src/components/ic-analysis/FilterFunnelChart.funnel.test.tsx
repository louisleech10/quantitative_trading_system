/**
 * ICRESULT_PAGING Task 2.3：漏斗改讀後端 `filter_log_funnel`；null ⇒ 該 stage「不適用」，不補 0；`_` 開頭合成 stage 不畫。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import FilterFunnelChart from '@/components/ic-analysis/FilterFunnelChart';

vi.mock('recharts', async (orig) => {
  const actual = await orig<typeof import('recharts')>();
  return { ...actual, ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="rc">{children}</div> };
});

afterEach(() => cleanup());

describe('FilterFunnelChart — funnel adapter', () => {
  it('null 段列為不適用；有值段畫圖；_adapter_probe 不畫', () => {
    render(
      <FilterFunnelChart
        funnel={{
          stage0_ingestion: { input: 39400, output: null },
          stage1_preprocessing: { input: null, output: null },
          feature_filter: { input: 39398, output: 39346 },
          stage5_thresholds: { input: 39346, output: 0 },
          _adapter_probe: { input: 1, output: 2 },
        }}
      />
    );
    const na = screen.getByTestId('funnel-not-applicable').textContent || '';
    expect(na).toContain('stage0_ingestion');
    expect(na).toContain('stage1_preprocessing');
    expect(na).not.toContain('feature_filter');
    expect(na).not.toContain('_adapter_probe');
    expect(screen.getByTestId('rc')).toBeTruthy();
  });

  it('無 funnel ⇒ 暫無漏斗數據', () => {
    render(<FilterFunnelChart funnel={null} />);
    expect(screen.getByText('暫無漏斗數據')).toBeTruthy();
  });
});

describe('FilterFunnelChart — B2 review CODEX-R1-P1-03', () => {
  it('input=null、output=7 ⇒ 不適用（不以 output 回填 input）', () => {
    render(<FilterFunnelChart funnel={{ s: { input: null, output: 7 } }} />);
    expect(screen.getByTestId('funnel-not-applicable').textContent).toContain('s');
    expect(screen.getByText('暫無漏斗數據')).toBeTruthy();
  });
});
