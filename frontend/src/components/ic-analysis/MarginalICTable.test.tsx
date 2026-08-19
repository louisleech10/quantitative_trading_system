/**
 * GAP-2 Task 5.1 — MarginalICTable
 * ok 表格／disabled 文字／degraded 警語／空 survivors／節缺席不渲染／文案禁含「獨立 OOS 驗證」／page.tsx 實際掛載（A1-5 補正：basic tab）。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import MarginalICTable, { MARGINAL_IC_DISCLOSURE } from '@/components/ic-analysis/MarginalICTable';
import type { MarginalICSection } from '@/lib/types';

afterEach(() => cleanup());

const row = (over: Partial<MarginalICSection['per_feature'][string]> = {}) => ({
  status: 'ok' as const,
  reason: null,
  conditioning_set: ['b'],
  marginal_ic: 0.1234,
  gross_ic: 0.2,
  ic_retained_ratio: 0.617,
  marginal_ic_train_insample: 0.15,
  ci95: [0.05, 0.2] as [number, number],
  condition_number: 1.2,
  r2_train: 0.3,
  n_used_train: 100,
  n_used_test: 50,
  ...over,
});

const okSection = (over: Partial<MarginalICSection> = {}): MarginalICSection => ({
  status: 'ok',
  reason: null,
  fit_scope: 'train',
  oos_guarantees: true,
  pass_class: 'oos',
  statistic: 'semi_partial_rank_ic',
  projection_space: 'rank_normal',
  independent_oos_validation: false,
  selection_sample: 'test',
  oos_semantics: 'preprocessing_and_fit_excluded_test;selection_used_test;not_independent_oos',
  algorithm_version: 'gap2_marginal_ic_v1',
  views: { loo: { status: 'ok' }, sequential: { status: 'ok' }, removed_candidates: { status: 'not_applicable', reason: 'no_removed_candidates' } },
  per_feature: { a: row(), b: row({ ci95: null, marginal_ic: -0.05 }) },
  sequential: [],
  removed_candidates: {},
  train_ic: { a: 0.2, b: 0.1 },
  n_train: 100,
  n_test: 50,
  n_regressions: 4,
  budget: { max_survivors_for_loo: 200, max_removed_candidates: 200, n_survivors: 2, n_removed_candidates: 0 },
  composite: { status: 'ok', reason: null, method: 'equal', composite_ic: 0.25, top_train_single: 'a', top_train_single_test_ic: 0.2, delta_vs_top_train_single: 0.05, delta_ci95: [0.01, 0.09], oos_guarantees: true },
  ...over,
});

describe('MarginalICTable', () => {
  it('ok 節 → 表格（列數＝倖存者數、ci95 null ⇒ —、composite 一列）', () => {
    render(<MarginalICTable section={okSection()} />);
    expect(screen.getByTestId('marginal-ic-table')).toBeTruthy();
    expect(screen.getByTestId('marginal-ic-row-a').textContent).toContain('0.1234');
    expect(screen.getByTestId('marginal-ic-row-b').textContent).toContain('—');
    expect(screen.getByTestId('marginal-ic-composite').textContent).toContain('0.2500');
    expect(screen.queryByTestId('marginal-ic-degraded')).toBeNull();
  });

  it('disabled 節 → 只顯示 status 文字，不畫表', () => {
    render(<MarginalICTable section={{ status: 'disabled', reason: 'disabled_by_config' }} />);
    expect(screen.getByTestId('marginal-ic-status')).toBeTruthy();
    expect(screen.queryByTestId('marginal-ic-table')).toBeNull();
  });

  it('oos_guarantees=false → degraded 警語', () => {
    render(<MarginalICTable section={okSection({ oos_guarantees: false, pass_class: 'full_sample_research_only' })} />);
    expect(screen.getByTestId('marginal-ic-degraded').textContent).toContain('full_sample_research_only');
  });

  it('空 survivors → 無倖存者列；節缺席 → 不渲染', () => {
    render(<MarginalICTable section={okSection({ per_feature: {}, composite: { status: 'not_applicable', reason: 'no_survivors' } })} />);
    expect(screen.getByTestId('marginal-ic-empty')).toBeTruthy();
    cleanup();
    const { container } = render(<MarginalICTable section={undefined} />);
    expect(container.innerHTML).toBe('');
  });

  it('D3′：揭露文案恆顯示且不含「獨立 OOS 驗證」子字串', () => {
    render(<MarginalICTable section={okSection()} />);
    const text = document.body.textContent ?? '';
    expect(text).toContain(MARGINAL_IC_DISCLOSURE);
    expect(text).not.toContain('獨立 OOS 驗證');
    expect(MARGINAL_IC_DISCLOSURE).not.toContain('獨立 OOS 驗證');
  });

  it('A1-5：page.tsx 於 basic TabsContent 內實際掛載 MarginalICTable', () => {
    const src = readFileSync(resolve(__dirname, '../../app/ic-analysis/page.tsx'), 'utf-8');
    expect((src.match(/MarginalICTable/g) ?? []).length).toBeGreaterThanOrEqual(2);
    const basicStart = src.indexOf('<TabsContent value="basic"');
    const deepStart = src.indexOf('<TabsContent value="deep"');
    const mount = src.indexOf('<MarginalICTable section={report?.marginal_ic}');
    expect(basicStart).toBeGreaterThan(-1);
    expect(mount).toBeGreaterThan(basicStart);
    expect(mount).toBeLessThan(deepStart);
  });
});
