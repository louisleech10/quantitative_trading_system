/**
 * ICPERF Task 0.4 ㊺ B(6)／驗收 B⑧ — TrendDashboard 不可判定之中性呈現
 * b2b 已施工：「資訊不足」與未知值用中性色、缺 recommendation 不預設「正常」。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import TrendDashboard from '@/components/ic-analysis/TrendDashboard';
import type { TrendAnalysisData } from '@/lib/types';

afterEach(() => {
  cleanup();
});

const insufficient: TrendAnalysisData = {
  feat_a: {
    ic_trend: { trend: 'down' },
    centrality_trend: { trend: 'indeterminate' },
    combined_signal: {
      recommendation: '資訊不足',
      reason: 'IC 下降；中心性不可判定：insufficient_points',
      action: '補足資料後重跑',
    },
  },
};

describe('TrendDashboard ㊺', () => {
  it('資訊不足 → 中性色（非綠）且顯示原因', () => {
    render(<TrendDashboard data={insufficient} />);
    const badge = screen.getByText('資訊不足');
    expect(badge.className).not.toMatch(/emerald/);
    expect(badge.className).toMatch(/slate/);
    expect(screen.getByText(/中心性不可判定/)).toBeTruthy();
  });

  it('缺 recommendation 時不得預設顯示「正常」', () => {
    render(<TrendDashboard data={{ feat_b: { ic_trend: { trend: 'indeterminate' } } }} />);
    expect(screen.queryByText('正常')).toBeNull();
  });

  it('各維揭露：非 ok 狀態列短原因、資料不足警示 ⚠ 附內容、無警示之 ok 維不列', () => {
    const detail = {
      n_obs: 23,
      horizon: 1,
      approx_independent_n: 23,
      phi_hat: 0.951,
      alpha: 0.05,
      estimated_null_reject_rate: 0.27,
      reference_reject_rate: 0.08,
      replications: 1000,
    };
    render(
      <TrendDashboard
        data={{
          feat_c: {
            ic_trend: { trend: 'up', inference_status: 'ok', data_warning: 'small_effective_sample', data_warning_detail: detail },
            centrality_trend: { trend: 'indeterminate', inference_status: 'insufficient_points' },
            ls_spread_trend: { trend: 'flat', inference_status: 'ok', data_warning: null },
            combined_signal: { recommendation: '資訊不足' },
          },
        }}
      />,
    );
    const ic = screen.getByTestId('trend-note-ic_trend');
    expect(ic.textContent).toBe('IC：⚠ 資料不足');
    expect(ic.getAttribute('title')).toMatch(/不重疊子序列 23 點.*0\.951.*27\.0%/);
    expect(screen.getByTestId('trend-note-centrality_trend').textContent).toBe('中心性：不重疊點不足 3 點');
    expect(screen.queryByTestId('trend-note-ls_spread_trend')).toBeNull();
  });
});
