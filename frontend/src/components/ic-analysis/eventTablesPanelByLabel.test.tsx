/**
 * GAP-3 UX **Task 7.5 ⑪** 驗收（`--run eventTablesPanelByLabel`；SPEC L3043–3046）。
 *
 * 🔴 **為什麼一定要有這一條**：後端通過 Task 7.5 之 pytest，前端仍可能顯示舊的單一組
 *    ——那是**靜默失效**，backend-only 的驗收看不見。本檔在真實 DOM 上驗三組確實出現。
 * 🔴 `all` 為 `not_computed` 時**顯示 reason，不是空表**（空表＝使用者以為「算出來是 0」）。
 * 🔴 資料由 `data` prop 注入（元件既有的測試注入口），不打網路。
 */
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import EventTablesPanel from './EventTablesPanel';
import type { EventAnalyzeResponse } from '@/lib/types';

const HORIZONS = [1, 2];

function block(mean: number) {
  return Object.fromEntries(
    HORIZONS.map((h) => [String(h), {
      // 🔴 mean 與 median 刻意不同值：兩格同值時「讀錯欄」不可分辨（本 epic 之 mutation 教訓③）
      mean: mean * h, median: mean / 2, win_rate: 0.5, n: 4, n_effective: 3.5, ci: 'unavailable',
    }]),
  );
}

function response(allGroup: unknown): EventAnalyzeResponse {
  return {
    import_id: 'imp-1',
    summary: { n_input: 4, n_aligned: 4, n_align_failures: 0, n_train: 2, n_test: 2, n_purged: 0 },
    align_failures: [],
    tables: {
      event_forward_return_table: {
        capability_status: 'ok',
        statistic_kind: 'event_return',
        horizons: HORIZONS,
        primary_macro: Object.fromEntries(HORIZONS.map((h) => [String(h), { mean: 0.01, n_symbols: 1 }])),
        sensitivity_micro: block(0.02),
        strata: {
          by_label: {
            positive: block(0.03),
            negative: block(-0.04),
            all: allGroup,
          },
        },
      },
    },
  } as unknown as EventAnalyzeResponse;
}

afterEach(cleanup);

describe('Task 7.5 ⑪ — EventTablesPanel 讀 strata.by_label 並垂直排列三組', () => {
  it('①三組都出現，且順序為 正例 → 反例 → 全體（垂直排列）', () => {
    render(<EventTablesPanel data={response(block(0.02))} />);
    const container = screen.getByTestId('event-fwd-by-label');
    const ids = Array.from(container.querySelectorAll('[data-testid^="event-fwd-group-"]'))
      .map((el) => el.getAttribute('data-testid'))
      .filter((id): id is string => !!id && /^event-fwd-group-(positive|negative|all)$/.test(id));
    expect(ids).toEqual(['event-fwd-group-positive', 'event-fwd-group-negative', 'event-fwd-group-all']);
  });

  it('②各組之數值來自**該組自己的** by_label 區塊（不是共用 sensitivity_micro）', () => {
    render(<EventTablesPanel data={response(block(0.02))} />);
    // positive h=1 → 0.03；negative h=1 → -0.04；all h=1 → 0.02。三者互不相同 ⇒ 讀錯來源必紅。
    expect(within(screen.getByTestId('event-fwd-group-positive-row-1')).getByText('0.0300')).toBeTruthy();
    expect(within(screen.getByTestId('event-fwd-group-negative-row-1')).getByText('-0.0400')).toBeTruthy();
    expect(within(screen.getByTestId('event-fwd-group-all-row-1')).getByText('0.0200')).toBeTruthy();
    // 逐 horizon 都有列（每組各自跑完所有 horizon）
    for (const h of HORIZONS) {
      for (const g of ['positive', 'negative', 'all']) {
        expect(screen.getByTestId(`event-fwd-group-${g}-row-${h}`)).toBeTruthy();
      }
    }
  });

  it('③`all` 為 not_computed ⇒ 顯示其 reason，**不顯示空表**', () => {
    render(<EventTablesPanel data={response({ status: 'not_computed', reason: 'mixed_control_kind_in_batch' })} />);
    const note = screen.getByTestId('event-fwd-group-all-not-computed');
    expect(note.textContent).toContain('not_computed');
    expect(note.textContent).toContain('mixed_control_kind_in_batch');
    // 該組**沒有**表格（空表會讓使用者以為「算出來是 0」）
    expect(screen.queryByTestId('event-fwd-group-all-table')).toBeNull();
    // 🔴 over 向：另兩組**不得**被連坐——它們與 control_kind 無關
    expect(screen.getByTestId('event-fwd-group-positive-table')).toBeTruthy();
    expect(screen.getByTestId('event-fwd-group-negative-table')).toBeTruthy();
  });

  it('④後端沒給 by_label ⇒ 明說沒拿到，**不得**默默退回顯示單一組', () => {
    const resp = response(block(0.02));
    delete (resp.tables.event_forward_return_table as { strata?: unknown }).strata;
    render(<EventTablesPanel data={resp} />);
    expect(screen.getByTestId('event-fwd-by-label-missing')).toBeTruthy();
    expect(screen.queryByTestId('event-fwd-group-positive')).toBeNull();
  });
});
