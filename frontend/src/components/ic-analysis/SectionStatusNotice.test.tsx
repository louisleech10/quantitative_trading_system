/**
 * ICHC Task 3.2 — 四類 fixture 測試（TODO 驗證矩陣）＋page wiring 原始碼斷言
 * （page 級守衛沿用 NetICChart.test.tsx 先例：isolated prop test 不足以證 wiring，
 *   以 page.tsx 原始碼 mount 點斷言補足）。
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SectionStatusNotice from './SectionStatusNotice';
import { isSectionStatus } from '@/lib/types';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const pageSrc = () =>
  readFileSync(resolve(__dirname, '../../app/ic-analysis/page.tsx'), 'utf8');

describe('SectionStatusNotice（ICHC 契約文案）', () => {
  it('fixture① xsec not_applicable → 契約文案非通用「暫無」', () => {
    render(
      <SectionStatusNotice
        title="分位數收益"
        status={{ status: 'not_applicable', reason: 'cross_sectional_mode' }}
      />
    );
    expect(screen.getByText('此分析模式不適用本圖表')).toBeTruthy();
    expect(screen.getByText('橫截面模式只計算逐期 IC 與跨標的矩陣')).toBeTruthy();
    expect(screen.queryByText(/暫無/)).toBeNull();
  });

  it('fixture② unknown status → fallback 通用空態＋console.warn', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(
      <SectionStatusNotice
        title="X"
        // @ts-expect-error 契約外值：測 fallback
        status={{ status: 'mystery_value' }}
      />
    );
    expect(screen.getByText('暫無數據')).toBeTruthy();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('mystery_value')
    );
  });

  it('fixture③ legacy 資料形（無 status 鍵）→ isSectionStatus false（走原圖路徑）', () => {
    expect(isSectionStatus({ featA: { quantile_mean_returns: { Q1: 0.1 } } })).toBe(false);
    expect(isSectionStatus({})).toBe(false);
    expect(isSectionStatus(undefined)).toBe(false);
  });

  it('fixture④ status 物件 → isSectionStatus true（走 notice 路徑）', () => {
    expect(isSectionStatus({ status: 'disabled', reason: 'turnover_disabled' })).toBe(true);
  });
});

describe('page wiring（原始碼斷言，NetICChart 先例）', () => {
  it('xsec 模式不渲染 FilterFunnelChart（ternary gate 存在）', () => {
    const src = pageSrc();
    const gate = src.match(
      /resultMode === 'cross_sectional' \? \([\s\S]*?SectionStatusNotice[\s\S]*?\) : \([\s\S]*?FilterFunnelChart/
    );
    expect(gate).not.toBeNull();
  });

  it('四節皆經 sectionSplit 分流（status→notice；map→chart）', () => {
    const src = pageSrc();
    for (const key of ['icDecay', 'quantile', 'grouped', 'turnover']) {
      expect(src).toMatch(new RegExp(`sectionSplit\\.${key}\\.status`));
      expect(src).toMatch(new RegExp(`sectionSplit\\.${key}\\.map`));
    }
  });

  it('FactorEquityCurve 消費已分流的 quantile map（不裸讀 report）', () => {
    const src = pageSrc();
    const mount = src.match(/<FactorEquityCurveChart[\s\S]*?\/>/);
    expect(mount).not.toBeNull();
    expect(mount![0]).toMatch(/sectionSplit\.quantile\.map/);
  });
});
