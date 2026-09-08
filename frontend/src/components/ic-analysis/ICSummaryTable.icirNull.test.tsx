/**
 * EVTWARMUP Task 2.1（R2 CODEX-R2-P2-01）：事件路徑 `icir` 可為 null——表格顯示 `--`、排序不炸。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import type { ICFeatureInfo } from '@/lib/types';

afterEach(() => cleanup());

const row = (name: string, icir: number | null, ic_mean = 0.05): ICFeatureInfo => ({
  rank: 1, feature_name: name, ic_mean, ic_std: 0.1, icir, p_value: 0.01, p_value_adj: 0.02,
  ic_hit_rate: 0.6, monotonicity_score: 0.5, coverage: 0.99, turnover_rate: 0.1, long_short_spread: 0.01,
} as unknown as ICFeatureInfo);

describe('ICSummaryTable — icir null（事件路徑診斷欄）', () => {
  it('icir=null 不炸、顯示 --；有值者照常', () => {
    render(<ICSummaryTable data={[row('a', null), row('b', 0.8), row('c', Number.NaN)]} />);
    expect(screen.getByText('a')).toBeTruthy();
    expect(screen.getByText('b')).toBeTruthy();
    expect(screen.getAllByText('--').length).toBeGreaterThanOrEqual(1);
  });
});
