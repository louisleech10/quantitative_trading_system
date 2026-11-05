/**
 * ICPERF Task 0.4 ㊻（SPEC v5.81；諮詢 r113）：深度分析候選來源之揭露與請求欄位。
 *
 * 具名：auto_request_omits_selected_features / manual_request_sends_selected / diagnostic_banner_and_disclosure /
 * manual_mixed_marks_failed_rows / survivors_mode_no_banner / screening_not_run_label /
 * store_auto_fill_marks_auto_and_user_action_marks_manual
 */
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import DeepCandidateNotice from '@/components/ic-analysis/DeepCandidateNotice';
import { buildDeepCandidateFields, DEEP_TOP_N_OPTIONS } from '@/lib/deepCandidates';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { DeepCandidateFeature, DeepCandidateSelection } from '@/lib/types';

afterEach(() => cleanup());

function feat(name: string, rank: number, passed: boolean | null, p: number, q: number): DeepCandidateFeature {
  return { feature_name: name, filter_passed: passed, global_rank: rank, p_value: p, p_value_adj: q,
    mw_p_value: null, mw_p_value_adj: null };
}

function selection(over: Partial<DeepCandidateSelection>): DeepCandidateSelection {
  return {
    source: 'diagnostic_top_n', diagnostic_mode: true, top_n_requested: 30, n_selected: 2, n_survivors: 0,
    n_ranked: 430000, n_tests: 429876, fdr: { method: 'bh', enabled: true }, sort_key: 'icir_aligned',
    features: [feat('f_a', 1, false, 0.0123, 0.9876), feat('f_b', 2, false, 0.05, 0.99)],
    ...over,
  };
}

describe('buildDeepCandidateFields', () => {
  it('auto_request_omits_selected_features', () => {
    const fields = buildDeepCandidateFields('auto', ['page_row_1', 'page_row_2'], 50);
    expect(fields).toEqual({ top_n: 50 });
    expect('selected_features' in fields).toBe(false);
  });

  it('manual_request_sends_selected', () => {
    expect(buildDeepCandidateFields('manual', ['x', 'y', 'z'], 30)).toEqual({ selected_features: ['x', 'y', 'z'], top_n: 3 });
    // 手選但清空 ⇒ 同自動（不送空清單）
    expect(buildDeepCandidateFields('manual', [], 100)).toEqual({ top_n: 100 });
  });

  it('offers 30/50/100 with default 30 first', () => {
    expect([...DEEP_TOP_N_OPTIONS]).toEqual([30, 50, 100]);
  });
});

describe('DeepCandidateNotice', () => {
  it('diagnostic_banner_and_disclosure', () => {
    render(<DeepCandidateNotice selection={selection({})} />);
    const banner = screen.getByTestId('deep-candidate-banner');
    expect(banner.textContent).toContain('未通過篩選、Top_30僅供診斷參考');
    const notice = screen.getByTestId('deep-candidate-notice');
    expect(notice.textContent).toContain('430000');
    expect(notice.textContent).toContain('429876');
    expect(notice.textContent).toContain('icir_aligned');
    expect(notice.textContent).toContain('bh');
    expect(notice.textContent).not.toContain('期望偽發現');
    const rows = within(screen.getByTestId('deep-candidate-table')).getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(rows[1].textContent).toContain('f_a');
    expect(rows[1].textContent).toContain('未通過');
    expect(rows[1].textContent).toContain('0.0123');
    expect(rows[1].textContent).toContain('0.9876');
  });

  it('manual_mixed_marks_failed_rows', () => {
    render(<DeepCandidateNotice selection={selection({
      source: 'manual', diagnostic_mode: false, top_n_requested: null, n_selected: 3, n_survivors: 5,
      features: [feat('p1', 3, true, 0.001, 0.01), feat('u1', 900, false, 0.4, 0.95), feat('p2', 4, true, 0.002, 0.02)],
    })} />);
    expect(screen.getByTestId('deep-candidate-banner').textContent).toContain('有 1 個未通過 IC 篩選');
    const rows = within(screen.getByTestId('deep-candidate-table')).getAllByRole('row');
    expect(rows.map((r) => r.textContent)).toEqual(expect.arrayContaining([
      expect.stringContaining('u1'),
    ]));
    expect(rows[2].textContent).toContain('未通過');
    expect(rows[1].textContent).toContain('通過');
  });

  it('survivors_mode_no_banner', () => {
    render(<DeepCandidateNotice selection={selection({
      source: 'survivors', diagnostic_mode: false, n_survivors: 2,
      features: [feat('s1', 1, true, 0.001, 0.01), feat('s2', 2, true, 0.002, 0.02)],
    })} />);
    expect(screen.queryByTestId('deep-candidate-banner')).toBeNull();
    expect(screen.queryByTestId('deep-candidate-table')).toBeNull();
  });

  it('screening_not_run_label', () => {
    render(<DeepCandidateNotice selection={selection({
      n_survivors: null, features: [feat('f_a', 1, null, 0.1, 0.5)],
    })} />);
    const notice = screen.getByTestId('deep-candidate-notice');
    expect(notice.textContent).toContain('未執行篩選');
    expect(within(screen.getByTestId('deep-candidate-table')).getAllByRole('row')[1].textContent).not.toContain('未通過');
  });

  it('renders nothing without selection', () => {
    const { container } = render(<DeepCandidateNotice selection={null} />);
    expect(container.innerHTML).toBe('');
  });
});

describe('icAnalysisStore selection source', () => {
  it('store_auto_fill_marks_auto_and_user_action_marks_manual', () => {
    const store = useICAnalysisStore.getState();
    store.setSelectedFeatures(['a', 'b'], 'auto');
    expect(useICAnalysisStore.getState().selectedFeaturesSource).toBe('auto');
    store.setSelectedFeatures(['a']);
    expect(useICAnalysisStore.getState().selectedFeaturesSource).toBe('manual');
    expect(useICAnalysisStore.getState().deepTopN).toBe(30);
    store.setDeepTopN(100);
    expect(useICAnalysisStore.getState().deepTopN).toBe(100);
  });
});
