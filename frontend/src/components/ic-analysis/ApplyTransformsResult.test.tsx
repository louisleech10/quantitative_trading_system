/**
 * ICPOSTLEAK Task 2.2（docs/ICPOSTLEAK_SPEC.md v4）——IC 頁「套用後處理」結果區之被排除欄顯示。
 *
 * 邊界①：excluded_features 非空 ⇒ 渲染每個欄名與原因。
 * 邊界②：excluded_features 為空或缺 ⇒ 不渲染被排除段（防恆顯示而失去鑑別力）。
 * 🔴 段落標題字面在本檔硬寫，不從元件 import 常數——兩邊一起動時 mutation 改壞字面本檔照樣綠。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import ApplyTransformsResult from '@/components/ic-analysis/ApplyTransformsResult';

const HEADING = '已排除之特徵';

const base = {
  selected_feature_count: 2,
  output_rows: 3000,
  output_cols: 2,
  transforms_applied: ['rank', 'gaussian', 'zscore'],
  output_path: 'data_cache/reports/post_ic_transforms_x.h5',
};

describe('ApplyTransformsResult', () => {
  afterEach(() => cleanup());

  it('lists excluded features with reason when non-empty', () => {
    render(
      <ApplyTransformsResult
        result={{ ...base, excluded_features: [{ name: 'ohlc_pattern_CDLDOJI', reason: 'ratio_unsafe:pattern' }] }}
      />,
    );
    expect(screen.getByText(HEADING, { exact: false })).toBeTruthy();
    expect(screen.getByText('ohlc_pattern_CDLDOJI', { exact: false })).toBeTruthy();
    expect(screen.getByText('ratio_unsafe:pattern', { exact: false })).toBeTruthy();
  });

  it('does not render excluded section when empty or missing', () => {
    render(<ApplyTransformsResult result={{ ...base, excluded_features: [] }} />);
    expect(screen.queryByText(HEADING, { exact: false })).toBeNull();
    cleanup();
    render(<ApplyTransformsResult result={base} />);
    expect(screen.queryByText(HEADING, { exact: false })).toBeNull();
  });

  it('keeps existing summary (counts and order joined by arrow)', () => {
    render(<ApplyTransformsResult result={base} />);
    expect(screen.getByText('rank → gaussian → zscore', { exact: false })).toBeTruthy();
  });
});
