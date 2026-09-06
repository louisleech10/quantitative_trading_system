/**
 * 掃描結果瀏覽器（`SCANCUBE` Task 4.1）之測試。
 *
 * ## 這批測試在防什麼
 *
 * 本 epic 已為「元件做了沒接上」付過三次代價，也為「畫面顯示假東西」付過兩次。
 * 這個瀏覽器的同型失敗是：
 *   · 沒有 taskId 卻 render 出空表（使用者以為分析沒結果）
 *   · Tier B 沒保存卻顯示空圖（使用者以為圖表壞了）
 *   · 跨格表少了比較限制（使用者拿不同 h 的 IC 比大小）
 *   · 被排除的節靜默消失（使用者不知道少看了什麼）
 *
 * 每一條都要求「改壞會紅」。
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ScanCubeBrowser from './ScanCubeBrowser';
import { ScanCubeTierNotStored } from '@/lib/api';
import { SCAN_CUBE_DOCS } from '@/lib/scanCubeDocs';

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  return {
    ...actual,
    getScanCubeManifest: vi.fn(),
    getScanCubeRows: vi.fn(),
    getScanCubeCharts: vi.fn(),
  };
});

const api = await import('@/lib/api');
const mockManifest = api.getScanCubeManifest as unknown as ReturnType<typeof vi.fn>;
const mockRows = api.getScanCubeRows as unknown as ReturnType<typeof vi.fn>;
const mockCharts = api.getScanCubeCharts as unknown as ReturnType<typeof vi.fn>;

const METRICS = ['ic_mean', 'icir', 'p_value'];

function manifest(over: Record<string, unknown> = {}) {
  return {
    task_id: 't1', symbol: 'ETHUSDT', timeframe: '12h',
    created_at: '2026-09-07T00:00:00Z',
    k_axis: [0, 1], h_axis: [1, 2],
    metrics: METRICS,
    chart_sections: ['ic_decay', 'grouped_ic'],
    excluded_sections: ['correlation_matrix'],
    tier_a: { stored: true, truncated: false, reason: null },
    tier_b: { stored: true, truncated: false, reason: null },
    cells: [],
    ...over,
  };
}

function page(n = 3, total = 3) {
  return {
    total, offset: 0, limit: 50,
    rows: Array.from({ length: n }, (_, i) => ({
      k: 0, h: 1, feature_name: `feat_${i}`,
      ic_mean: 0.1 + i * 0.01, icir: 0.5, p_value: 0.01,
    })),
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockManifest.mockResolvedValue(manifest());
  mockRows.mockResolvedValue(page());
  mockCharts.mockResolvedValue({
    k: 0, h: 1, feature_name: 'feat_0',
    sections: { ic_decay: { feat_0: { half_life: 4 } }, grouped_ic: { bull: { feat_0: 0.1 } } },
  });
});

afterEach(cleanup);

describe('接線', () => {
  it('🔴 沒有 taskId ⇒ 整個區塊不 render（不是空表）', () => {
    render(<ScanCubeBrowser taskId={undefined} />);
    expect(screen.queryByTestId('ic-cube')).toBeNull();
    expect(mockManifest).not.toHaveBeenCalled();
  });

  it('🔴 沒有掃描（單值模式）⇒ 不 render', () => {
    render(<ScanCubeBrowser taskId="t1" hasScan={false} />);
    expect(screen.queryByTestId('ic-cube')).toBeNull();
    expect(mockManifest).not.toHaveBeenCalled();
  });

  it('有 taskId 且有掃描 ⇒ 取 manifest 並顯示', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => expect(screen.getByTestId('ic-cube')).toBeTruthy());
    expect(mockManifest).toHaveBeenCalledWith('t1');
  });
});

describe('分頁', () => {
  it('顯示「共 N 筆，正在看 X–Y」，且 N 用的是 total 不是本頁筆數', async () => {
    mockRows.mockResolvedValue({ ...page(50, 1200), limit: 50 });
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => {
      const text = screen.getByTestId('ic-cube-paging').textContent || '';
      expect(text).toContain('1200');
      expect(text).toContain('1');
      expect(text).toContain('50');
    });
  });

  it('最後一頁時「下一頁」為 disabled', async () => {
    mockRows.mockResolvedValue(page(3, 3));
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => {
      expect((screen.getByTestId('ic-cube-next') as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it('第一頁時「上一頁」為 disabled', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => {
      expect((screen.getByTestId('ic-cube-prev') as HTMLButtonElement).disabled).toBe(true);
    });
  });
});

describe('跨格視圖', () => {
  it('🔴 必須顯示跨 h 之比較限制', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'feature' } });

    await waitFor(() => {
      const warn = screen.getByTestId('ic-cube-cross-h-warning');
      expect(warn.textContent).toContain('不能直接比大小');
    });
  });

  it('🔴 不得提供跨格排名／自動選最佳格', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'feature' } });

    await waitFor(() => screen.getByTestId('ic-cube-cross-table'));
    // 跨格視圖不得出現排序按鈕（排序只在單格內）
    for (const m of METRICS) {
      expect(screen.queryByTestId(`ic-cube-sort-${m}`)).toBeNull();
    }
    const html = document.body.innerHTML;
    expect(html).not.toContain('最佳組合');
    expect(html).not.toContain('推薦');
  });

  it('跨格矩陣有 k×h 個格子', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'feature' } });
    await waitFor(() => {
      for (const k of [0, 1]) {
        for (const h of [1, 2]) {
          expect(screen.getByTestId(`ic-cube-cross-${k}-${h}`)).toBeTruthy();
        }
      }
    });
  });
});

describe('單格視圖之排序', () => {
  it('點欄頭會帶 sort 參數，且只在單格內排（不跨格）', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-sort-icir'));
    fireEvent.click(screen.getByTestId('ic-cube-sort-icir'));

    await waitFor(() => {
      const last = mockRows.mock.calls[mockRows.mock.calls.length - 1][1];
      expect(last.sort).toBe('icir:desc');
      // 🔴 單格：k/h 都被鎖定成單一值 ⇒ 排序不可能跨格
      expect(last.k).toEqual([0]);
      expect(last.h).toEqual([1]);
    });
  });

  it('再點一次切換升冪', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-sort-icir'));
    fireEvent.click(screen.getByTestId('ic-cube-sort-icir'));
    await waitFor(() => screen.getByTestId('ic-cube-sort-icir'));
    fireEvent.click(screen.getByTestId('ic-cube-sort-icir'));
    await waitFor(() => {
      const last = mockRows.mock.calls[mockRows.mock.calls.length - 1][1];
      expect(last.sort).toBe('icir:asc');
    });
  });
});

describe('fail-closed 之呈現', () => {
  it('🔴 Tier A 未保存 ⇒ 明講原因，不是空表', async () => {
    mockManifest.mockResolvedValue(manifest({
      tier_a: { stored: false, truncated: true, reason: 'scan_cube_rows_exceeded' },
    }));
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => {
      const el = screen.getByTestId('ic-cube-not-saved');
      expect(el.textContent).toContain('scan_cube_rows_exceeded');
    });
    expect(screen.queryByTestId('ic-cube-cell-table')).toBeNull();
  });

  it('🔴 Tier B 未保存 ⇒ 顯示說明＋fits_hint，且**不發** charts 請求', async () => {
    mockManifest.mockResolvedValue(manifest({
      tier_b: {
        stored: false, truncated: true, reason: 'scan_cube_chart_bytes_exceeded',
        fits_hint: {
          bytes_per_feature: 36808, max_feature_cells: 5697,
          examples: [{ cells: 12, features_per_cell: 474 }],
        },
      },
    }));
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'charts' } });

    await waitFor(() => {
      const el = screen.getByTestId('ic-cube-charts-not-stored');
      expect(el.textContent).toContain('scan_cube_chart_bytes_exceeded');
      // 數字由後端 fits_hint 帶入，前端不寫死
      expect(el.textContent).toContain('12 格 × 474 特徵');
    });
    expect(mockCharts).not.toHaveBeenCalled();
  });

  it('🔴 Tier B 掛掉不得影響 Tier A（指標表照顯示）', async () => {
    mockManifest.mockResolvedValue(manifest({
      tier_b: { stored: false, truncated: true, reason: 'scan_cube_chart_bytes_exceeded' },
    }));
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => expect(screen.getByTestId('ic-cube-cell-table')).toBeTruthy());
  });

  it('查詢時才發現未保存（409）⇒ 同樣走 not-saved 分支', async () => {
    mockRows.mockRejectedValue(new ScanCubeTierNotStored({ reason: 'scan_cube_rows_exceeded' }));
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => expect(screen.getByTestId('ic-cube-not-saved')).toBeTruthy());
  });
});

describe('圖表視圖', () => {
  it('沒填特徵名 ⇒ 提示，不發請求', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'charts' } });
    await waitFor(() => expect(screen.getByTestId('ic-cube-charts-pick-feature')).toBeTruthy());
    expect(mockCharts).not.toHaveBeenCalled();
  });

  it('填了特徵名 ⇒ 取該格該特徵之節並逐節列出', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-view'));
    fireEvent.change(screen.getByTestId('ic-cube-feature'), { target: { value: 'feat_0' } });
    fireEvent.change(screen.getByTestId('ic-cube-view'), { target: { value: 'charts' } });

    await waitFor(() => {
      expect(mockCharts).toHaveBeenCalledWith('t1', 0, 1, 'feat_0');
      expect(screen.getByTestId('ic-cube-section-ic_decay')).toBeTruthy();
      expect(screen.getByTestId('ic-cube-section-grouped_ic')).toBeTruthy();
    });
  });
});

describe('被排除的節', () => {
  it('🔴 `correlation_matrix` 之排除必須明講，不得靜默省略', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => {
      const el = screen.getByTestId('ic-cube-corr-excluded');
      expect(el.textContent).toContain('correlation_matrix');
    });
  });
});

describe('說明覆蓋閘（沿用揭露票 R2 之一對一模型）', () => {
  it('🔴 每個可編輯控制項都要帶 `data-doc` 且對應說明在場', async () => {
    render(<ScanCubeBrowser taskId="t1" />);
    await waitFor(() => screen.getByTestId('ic-cube-cell-table'));

    const controls = Array.from(
      document.querySelectorAll('#__nonexistent__, [data-testid^="ic-cube-"] input[type="number"], [data-testid^="ic-cube-"], select'),
    ).filter((el) => el.tagName === 'SELECT'
      || (el.tagName === 'INPUT' && (el as HTMLInputElement).type === 'number')
      || (el.tagName === 'INPUT' && (el as HTMLInputElement).type === 'text'));

    expect(controls.length).toBeGreaterThanOrEqual(4);
    const missingAttr = controls
      .filter((el) => !el.getAttribute('data-doc'))
      .map((el) => el.getAttribute('data-testid') ?? el.tagName);
    expect(missingAttr, `這些控制項沒有 data-doc：${missingAttr.join('、')}`).toEqual([]);

    const missingDoc = controls
      .map((el) => el.getAttribute('data-doc') as string)
      .filter((key) => document.querySelector(`[data-testid="ic-cube-doc-${key}"]`) === null);
    expect(missingDoc, `這些欄位的說明不在畫面上：${missingDoc.join('、')}`).toEqual([]);
  });

  it('文案來源唯一：元件不得自寫說明字面', () => {
    // 每個 doc 鍵在 SCAN_CUBE_DOCS 都要有非空的兩欄
    for (const [key, doc] of Object.entries(SCAN_CUBE_DOCS)) {
      expect(doc.what.length, `${key}.what 空`).toBeGreaterThan(10);
      expect(doc.effect.length, `${key}.effect 空`).toBeGreaterThan(10);
    }
  });
});
