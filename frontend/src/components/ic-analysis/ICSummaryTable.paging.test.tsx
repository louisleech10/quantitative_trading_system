/**
 * ICRESULT_PAGING Task 2.2：伺服器分頁表格——DOM 列數 ≤ limit、勾選 O(1)（不呼叫 Array.includes）、
 * 排序 callback offset:0、翻頁 skeleton 且舊列保留、跨頁勾選保留、搜尋 300 ms 去抖只送一次。
 */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import type { ICFeatureInfo, ICSummaryPage, SummaryPageParams } from '@/lib/types';

afterEach(() => { cleanup(); vi.useRealTimers(); });

const row = (i: number): ICFeatureInfo => ({ rank: i + 1, feature_name: `feat_${i}`, ic_mean: 0.01 * i, icir: 0.1 * i } as ICFeatureInfo);
const page = (offset = 0, limit = 50, total = 39346): ICSummaryPage => ({
  total, offset, limit, sort_by: 'icir', sort_order: 'desc', result_revision: 1,
  rows: Array.from({ length: Math.min(limit, total - offset) }, (_, i) => row(offset + i)),
});
const params: SummaryPageParams = { sort_by: 'icir', sort_order: 'desc', offset: 0, limit: 50, search: '' };

describe('ICSummaryTable — 伺服器分頁', () => {
  it('total=39346、rows=50 ⇒ <tr> == 51（表頭＋50 列）', () => {
    render(<ICSummaryTable page={page()} params={params} onParamsChange={() => undefined} />);
    expect(document.querySelectorAll('tr').length).toBe(51);
    expect(screen.getByTestId('ic-summary-range').textContent).toContain('共 39346 列');
  });

  it('多次勾選不對 selectedFeatures 呼叫 includes（Set，O(1)）', () => {
    // React／testing-library 內部也用 Array.prototype.includes，全域 spy 無法區分；改把傳入陣列的 includes 換成會拋錯的版本：
    // 元件只要對 selectedFeatures 呼叫一次 includes 就會炸。
    const trap = (names: string[]) => Object.assign([...names], { includes: () => { throw new Error('includes on selectedFeatures'); } });
    let selected: string[] = [];
    const onSelectFeatures = (names: string[]) => { selected = names; };
    const props = { page: page(0, 200), params: { ...params, limit: 200 }, onParamsChange: () => undefined, selectable: true, onSelectFeatures };
    const { rerender } = render(<ICSummaryTable {...props} selectedFeatures={trap(selected)} />);
    for (let i = 0; i < 40; i += 1) {
      const boxes = document.querySelectorAll('tbody [role="checkbox"]');
      fireEvent.click(boxes[i]);
      rerender(<ICSummaryTable {...props} selectedFeatures={trap(selected)} />);
    }
    expect(selected.length).toBe(40);
  }, 20000);

  it('排序點擊 ⇒ onParamsChange 收 {sort_by, sort_order, offset:0}', () => {
    const onParamsChange = vi.fn();
    render(<ICSummaryTable page={page()} params={params} onParamsChange={onParamsChange} />);
    fireEvent.click(document.querySelector('[data-sort-field="ic_mean"]')!);
    expect(onParamsChange).toHaveBeenCalledWith({ sort_by: 'ic_mean', sort_order: 'desc', offset: 0 });
    fireEvent.click(document.querySelector('[data-sort-field="icir"]')!);
    expect(onParamsChange).toHaveBeenLastCalledWith({ sort_by: 'icir', sort_order: 'asc', offset: 0 });
    expect(onParamsChange.mock.calls.every((c) => !('order' in c[0]))).toBe(true);
  });

  it('翻頁 loading 中：舊列仍在 DOM 且出現 skeleton；下一頁 ⇒ offset+limit', () => {
    const onParamsChange = vi.fn();
    const { rerender } = render(<ICSummaryTable page={page()} params={params} onParamsChange={onParamsChange} />);
    fireEvent.click(screen.getByTestId('ic-summary-next'));
    expect(onParamsChange).toHaveBeenCalledWith({ offset: 50 });
    rerender(<ICSummaryTable page={page()} params={{ ...params, offset: 50 }} onParamsChange={onParamsChange} loading />);
    expect(screen.getByTestId('ic-summary-skeleton')).toBeTruthy();
    expect(document.querySelectorAll('tbody tr').length).toBe(50);
    expect(screen.getByText('feat_0')).toBeTruthy();
  });

  it('跨頁勾選：翻頁後回前頁仍勾（selectedFeatures 不因換頁而丟）', () => {
    let selected: string[] = [];
    const onSelectFeatures = (names: string[]) => { selected = names; };
    const { rerender } = render(<ICSummaryTable page={page(0)} params={params} onParamsChange={() => undefined} selectable selectedFeatures={selected} onSelectFeatures={onSelectFeatures} />);
    fireEvent.click(document.querySelectorAll('tbody [role="checkbox"]')[0]);
    expect(selected).toEqual(['feat_0']);
    rerender(<ICSummaryTable page={page(50)} params={{ ...params, offset: 50 }} onParamsChange={() => undefined} selectable selectedFeatures={selected} onSelectFeatures={onSelectFeatures} />);
    fireEvent.click(document.querySelectorAll('tbody [role="checkbox"]')[0]);
    expect(selected).toEqual(['feat_0', 'feat_50']);
    rerender(<ICSummaryTable page={page(0)} params={params} onParamsChange={() => undefined} selectable selectedFeatures={selected} onSelectFeatures={onSelectFeatures} />);
    expect((document.querySelectorAll('tbody [role="checkbox"]')[0] as HTMLElement).getAttribute('data-state')).toBe('checked');
  });

  it('搜尋框 300 ms 去抖：連打 5 字 ⇒ 一次 onParamsChange({search, offset:0})', () => {
    vi.useFakeTimers();
    const onParamsChange = vi.fn();
    render(<ICSummaryTable page={page()} params={params} onParamsChange={onParamsChange} />);
    const input = screen.getByTestId('ic-summary-search') as HTMLInputElement;
    for (const v of ['c', 'cl', 'clo', 'clos', 'close']) fireEvent.change(input, { target: { value: v } });
    expect(onParamsChange).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(299); });
    expect(onParamsChange).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(onParamsChange).toHaveBeenCalledTimes(1);
    expect(onParamsChange).toHaveBeenCalledWith({ search: 'close', offset: 0 });
  });

  it('失敗 ⇒ 顯示錯誤與重試按鈕，點擊呼叫 onRetry', () => {
    const onRetry = vi.fn();
    render(<ICSummaryTable page={page()} params={params} onParamsChange={() => undefined} error="載入表格失敗" onRetry={onRetry} />);
    fireEvent.click(screen.getByTestId('ic-summary-retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
