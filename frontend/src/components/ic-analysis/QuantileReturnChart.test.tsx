/**
 * ICHC Task 2.1 — QuantileReturnChart contract test。
 * 契約 fixture（攤平後形狀）餵入 → 渲染 n 個分位 bar（圖有料）；
 * 巢狀舊形（修復前病灶）→ 空態（防回歸的反向斷言）。
 * ResizeObserver/getBoundingClientRect mock 沿用 FactorReturnChart.test.tsx 慣例。
 */
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import QuantileReturnChart from './QuantileReturnChart';
import type { QuantileReturnData } from '@/lib/types';

beforeAll(() => {
  class RO {
    private cb: ResizeObserverCallback;
    constructor(cb: ResizeObserverCallback) {
      this.cb = cb;
    }
    observe(el: Element) {
      // @ts-expect-error 簡化 entry
      this.cb([
        {
          target: el,
          contentRect: { width: 500, height: 300, top: 0, left: 0, bottom: 300, right: 500, x: 0, y: 0, toJSON() {} },
        },
      ]);
    }
    unobserve() {}
    disconnect() {}
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).ResizeObserver = RO;
  HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
    return {
      width: 500,
      height: 300,
      top: 0,
      left: 0,
      bottom: 300,
      right: 500,
      x: 0,
      y: 0,
      toJSON() {},
    } as DOMRect;
  };
});

afterEach(() => {
  cleanup();
});

const FLAT_CONTRACT_FIXTURE: QuantileReturnData = {
  quantile_mean_returns: { Q1: -0.012, Q2: 0.001, Q3: 0.009, Q4: 0.014, Q5: 0.021 },
  long_short_spread: 0.033,
  long_short_tstat: 2.1,
  monotonicity_score: 0.9,
  cumulative_returns: { Q1: [-0.012], Q5: [0.021] },
};

describe('QuantileReturnChart（ICHC 契約）', () => {
  it('契約扁平 fixture → 非空態（chartData.length == 5 生效）', () => {
    render(<QuantileReturnChart data={FLAT_CONTRACT_FIXTURE} featureName="featA" />);
    expect(screen.queryByText(/暫無分位數收益數據/)).toBeNull();
  });

  it('巢狀舊形（頂層無 quantile_mean_returns）→ 空態文案', () => {
    const nestedLegacy = {
      quantile_returns: { quantile_mean_returns: { Q1: 0.1 } },
      monotonicity_score: 0.5,
    } as unknown as QuantileReturnData;
    render(<QuantileReturnChart data={nestedLegacy} featureName="featB" />);
    expect(screen.getByText(/暫無分位數收益數據/)).toBeTruthy();
  });

  it('null → 空態文案', () => {
    render(<QuantileReturnChart data={null} featureName={null} />);
    expect(screen.getByText(/暫無分位數收益數據/)).toBeTruthy();
  });
});
