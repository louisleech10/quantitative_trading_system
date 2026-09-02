/**
 * G3-D16（UAT B15）：門檻不變、只有 report 身分改變 ⇒ **不得**再 refilter（原本每 600ms 迴圈一次）。
 */
import { renderHook, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAutoRefilter } from '@/hooks/useAutoRefilter';

const thresholdsA = { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, correlation_threshold: 0.7 };
const thresholdsB = { ...thresholdsA, icir_min: 0.6 };

describe('useAutoRefilter', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('report 身分改變（refilter 回寫）不再觸發下一輪；門檻改變才觸發', async () => {
    const refilter = vi.fn().mockResolvedValue({});
    const setError = vi.fn();
    const setIsRefiltering = vi.fn();
    let report: object = { a: 1 };
    let thresholds = thresholdsA;
    const { rerender } = renderHook(() => useAutoRefilter({
      taskId: 't1', status: 'completed', hasReport: Boolean(report), thresholds,
      refilter, setError, setIsRefiltering, debounceMs: 10,
    }));

    await act(async () => { vi.advanceTimersByTime(20); });
    expect(refilter).toHaveBeenCalledTimes(1);

    // 模擬 refilter 成功後 setReport ⇒ 新物件身分 ⇒ 重新 render
    for (let i = 0; i < 5; i += 1) {
      report = { a: i + 2 };
      rerender();
      await act(async () => { vi.advanceTimersByTime(20); });
    }
    expect(refilter).toHaveBeenCalledTimes(1);          // 🔴 原缺陷：這裡會是 6

    thresholds = thresholdsB;
    rerender();
    await act(async () => { vi.advanceTimersByTime(20); });
    expect(refilter).toHaveBeenCalledTimes(2);
    expect(refilter.mock.calls[1][1]).toEqual(thresholdsB);
  });

  it('未 completed 或尚無 report ⇒ 不 refilter', async () => {
    const refilter = vi.fn().mockResolvedValue({});
    renderHook(() => useAutoRefilter({
      taskId: 't1', status: 'running', hasReport: true, thresholds: thresholdsA,
      refilter, setError: vi.fn(), setIsRefiltering: vi.fn(), debounceMs: 10,
    }));
    renderHook(() => useAutoRefilter({
      taskId: 't1', status: 'completed', hasReport: false, thresholds: thresholdsA,
      refilter, setError: vi.fn(), setIsRefiltering: vi.fn(), debounceMs: 10,
    }));
    await act(async () => { vi.advanceTimersByTime(20); });
    expect(refilter).not.toHaveBeenCalled();
  });
});
