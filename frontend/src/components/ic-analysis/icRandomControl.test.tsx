/**
 * `G3-D2` D5.3 前端驗收：隨機對照組入口。
 *
 * 🔴 **接線優先**：B-D4 踩過「元件做好而沒有任何呼叫端傳值 ⇒ 按不到」。
 *    本檔之核心是**攔截真實 HTTP body**——證明按鈕真的把純函式組出來的 spec
 *    送到 `/case/import-events/random-control`，而不是只在元件內畫出一個表單。
 */
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EventBatchDisclosurePanel from '@/components/ic-analysis/EventBatchDisclosurePanel';
import {
  RANDOM_CONTROL_ALLOCATION,
  batchHorizonBars,
  buildRandomControlSpec,
} from '@/lib/randomControlSpec';
import type { EventImportDetail } from '@/lib/types';

const T0_A = 1700000000000;
const T0_B = 1700043200000;

function detailFixture(over: Partial<EventImportDetail> = {}): EventImportDetail {
  const rows = [
    { event_id: 'ETHUSDT:12h:1700000000000', t0_ms: T0_A, label: 1 },
    { event_id: 'ETHUSDT:12h:1700043200000', t0_ms: T0_B, label: 0 },
  ];
  return {
    summary: {
      import_id: 'imp-1', source_name: 'unit', upload_sha256: 'a'.repeat(64),
      imported_at: '2026-09-05T00:00:00Z', n_events: rows.length,
      symbols: ['ETHUSDT'], timeframes: ['12h'], direction: 'long', scenario: 'C',
    },
    records: rows.map((r) => ({
      event_id: r.event_id, symbol: 'ETHUSDT', timeframe: '12h', t0: r.t0_ms,
      label_definition: { window: { horizon_bars: 3 } },
    })),
    batch_facts: {
      scenario: 'C', control_kind: 'user_labeled_same_trigger', direction: 'long',
      label_origin: null,
      t0: rows.map((r) => ({ event_id: r.event_id, t0_ms: r.t0_ms })),
      label: rows.map((r) => ({ event_id: r.event_id, label: r.label })),
    },
    declaration_seeds: { entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close' },
    batch_fact_notes: { control_kind_values: ['user_labeled_same_trigger'], decision_offset_bars_record_values: [0] },
    receipt_batch: { label_rule: null, random_control_spec: null },
    ...over,
  };
}

const PARAMS = { nRequested: 100, seed: 20260905, neighborhoodBars: 2, embargoBars: 6, threshold: 0.02 };

function renderPanel(detail: EventImportDetail) {
  return render(
    <EventBatchDisclosurePanel
      importId="imp-1" detail={detail}
      labelSpec={{ horizon_bars: 3, entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close', decision_offset_bars: 0 }}
      onChangeLabelSpec={() => {}}
    />,
  );
}

afterEach(cleanup);

// ── 純函式：抽樣契約之導出規則 ─────────────────────────────────────────────

describe('buildRandomControlSpec — 導出規則', () => {
  it('由批次事實導出 universe／strata／period，並只產出**輸入**鍵', () => {
    const out = buildRandomControlSpec(detailFixture(), PARAMS);
    expect(out.ok).toBe(true);
    if (!out.ok) return;
    expect(out.spec.universe).toEqual({ symbol: 'ETHUSDT', timeframe: '12h', start_ms: T0_A, end_ms: T0_B });
    expect(out.spec.strata).toEqual({
      symbol: 'ETHUSDT', timeframe: '12h', period: { start_ms: T0_A, end_ms: T0_B }, direction: 'long',
    });
    expect(out.spec.allocation).toBe(RANDOM_CONTROL_ALLOCATION);
    expect(out.spec.replacement).toBe(false);
    // 🔴 收據鍵一個都不得出現（送產出當輸入 ⇒ 後端覆寫，值被無視而沒人知道）
    for (const k of ['n_drawn', 'per_stratum', 'candidate_count', 'sample_ids_digest',
      'data_snapshot_digest', 'generator_version']) {
      expect(Object.keys(out.spec)).not.toContain(k);
    }
  });

  it('批有落檔 label_rule ⇒ **以它為準**（不用使用者輸入的門檻）', () => {
    const d = detailFixture({ receipt_batch: { label_rule: { threshold: 0.07, horizon_bars: 5 }, random_control_spec: null } });
    const out = buildRandomControlSpec(d, PARAMS);
    expect(out.ok).toBe(true);
    if (!out.ok) return;
    expect(out.spec.label_rule).toEqual({ threshold: 0.07, horizon_bars: 5 });
    expect(out.usedBatchLabelRule).toBe(true);
  });

  it('批無 label_rule ⇒ 用使用者門檻＋批之答案窗長度，並標記無法對證', () => {
    const out = buildRandomControlSpec(detailFixture(), PARAMS);
    expect(out.ok).toBe(true);
    if (!out.ok) return;
    expect(out.spec.label_rule).toEqual({ threshold: 0.02, horizon_bars: 3 });
    expect(out.usedBatchLabelRule).toBe(false);
  });

  it('跨 symbol／direction 非單值／答案窗混值 ⇒ 具名拒絕（不猜）', () => {
    const mixedSymbol = detailFixture();
    mixedSymbol.records[1].symbol = 'BTCUSDT';
    expect(buildRandomControlSpec(mixedSymbol, PARAMS).ok).toBe(false);

    const noDirection = detailFixture();
    noDirection.batch_facts.direction = null;
    expect(buildRandomControlSpec(noDirection, PARAMS).ok).toBe(false);

    const mixedHorizon = detailFixture();
    (mixedHorizon.records[1].label_definition as { window: { horizon_bars: number } }).window.horizon_bars = 9;
    expect(batchHorizonBars(mixedHorizon)).toBeNull();
    expect(buildRandomControlSpec(mixedHorizon, PARAMS).ok).toBe(false);
  });
});

// ── 接線：按鈕 → 真實 HTTP body ────────────────────────────────────────────

describe('隨機對照組入口之接線（攔 HTTP body）', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('按下「產生隨機對照批」⇒ POST /case/import-events/random-control，body 逐鍵等於純函式之輸出', async () => {
    const detail = detailFixture();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ accepted: true, import_id: 'rc-1', n_rows: 40, n_valid: 40 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    renderPanel(detail);
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/case/import-events/random-control');
    const body = JSON.parse(String((init as RequestInit).body));
    expect(body.event_import_id).toBe('imp-1');
    const expected = buildRandomControlSpec(detail, PARAMS);
    expect(expected.ok).toBe(true);
    if (!expected.ok) return;
    expect(body.random_control_spec).toEqual(expected.spec);

    await screen.findByTestId('ic-random-control-result');
  });

  it('改參數會改送出的 body（不是把預設值寫死送出）', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ accepted: true, import_id: 'rc-2', n_rows: 7, n_valid: 7 }),
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPanel(detailFixture());

    fireEvent.change(screen.getByTestId('ic-random-control-seed'), { target: { value: '42' } });
    fireEvent.change(screen.getByTestId('ic-random-control-embargo'), { target: { value: '11' } });
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body.random_control_spec.seed).toBe(42);
    expect(body.random_control_spec.exclusion.embargo_bars).toBe(11);
  });

  it('n_drawn < n_requested ⇒ 揭露缺額（不是靜默成功）', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ accepted: true, import_id: 'rc-3', n_rows: 12, n_valid: 12 }),
    }));
    renderPanel(detailFixture());
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));
    const note = await screen.findByTestId('ic-random-control-result');
    expect(note.textContent).toContain('少於想抽的 100 筆');
  });

  it('後端拒收 ⇒ 顯示錯誤，不假裝成功', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 422,
      json: async () => ({ detail: { kind: 'pipeline_rejected', message: 'random_control_period_mismatch: 無交集' } }),
    }));
    renderPanel(detailFixture());
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));
    const err = await screen.findByTestId('ic-random-control-error');
    expect(err.textContent).toContain('random_control_period_mismatch');
    expect(screen.queryByTestId('ic-random-control-result')).toBeNull();
  });

  it('批無落檔 label_rule ⇒ 面板明講「無法確認兩批用同一把尺」', () => {
    renderPanel(detailFixture());
    expect(screen.getByTestId('ic-random-control-rule-unverifiable')).toBeTruthy();
  });

  it('批有落檔 label_rule ⇒ 不顯示該警語（正向對照，防恆顯示）', () => {
    renderPanel(detailFixture({
      receipt_batch: { label_rule: { threshold: 0.02, horizon_bars: 3 }, random_control_spec: null },
    }));
    expect(screen.queryByTestId('ic-random-control-rule-unverifiable')).toBeNull();
  });

  it('無法組出 spec ⇒ 顯示具名理由且**沒有**送出按鈕', () => {
    const d = detailFixture();
    d.batch_facts.direction = null;
    renderPanel(d);
    expect(screen.getByTestId('ic-random-control-blocked')).toBeTruthy();
    expect(screen.queryByTestId('ic-random-control-generate')).toBeNull();
  });
});

// ── R1 閉合：compare 接線（三家獨立命中「閘在測面綠、產品面不可達」）──────────

describe('產完對照批立刻跑規則身分閘並顯示結論', () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  function twoCallFetch(verdict: Record<string, unknown>) {
    return vi.fn()
      .mockResolvedValueOnce({
        ok: true, json: async () => ({ accepted: true, import_id: 'rc-9', n_rows: 20, n_valid: 20 }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => verdict });
  }

  it('產生後**第二個** request 打 compare 端點，body 帶兩個 import_id', async () => {
    const fetchMock = twoCallFetch({
      status: 'ok', reason: null, message: null,
      trigger_prevalence: 0.25, random_prevalence: 0.1, lift: 2.5,
      n_trigger: 4, n_random: 20, sample_design: 'unconditional_random',
      n_requested: 100, n_drawn: 20,
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPanel(detailFixture());
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [url, init] = fetchMock.mock.calls[1];
    expect(String(url)).toContain('/case/events/compare-random-control');
    expect(JSON.parse(String((init as RequestInit).body)))
      .toEqual({ trigger_import_id: 'imp-1', random_import_id: 'rc-9' });

    const line = await screen.findByTestId('ic-random-control-prevalence');
    expect(line.textContent).toContain('25.0%');
    expect(line.textContent).toContain('10.0%');
    expect(line.textContent).toContain('2.50×');
    expect(line.textContent).toContain('unconditional_random');
  });

  it('`unavailable` ⇒ 顯示具名 reason，且**不顯示**任何 prevalence 數字', async () => {
    vi.stubGlobal('fetch', twoCallFetch({
      status: 'unavailable', reason: 'random_control_rule_identity_unverifiable',
      message: '觸發批沒有落檔 receipt.batch.label_rule',
      trigger_prevalence: null, random_prevalence: null, lift: null,
      n_trigger: 0, n_random: 0, sample_design: 'unconditional_random',
      n_requested: 100, n_drawn: 20,
    }));
    renderPanel(detailFixture());
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));

    const note = await screen.findByTestId('ic-random-control-compare-unavailable');
    expect(note.textContent).toContain('random_control_rule_identity_unverifiable');
    expect(screen.queryByTestId('ic-random-control-prevalence')).toBeNull();
  });

  it('`lift` 為 null（對照基準 0）⇒ 寫「無定義」而不是印 0 或 Infinity', async () => {
    vi.stubGlobal('fetch', twoCallFetch({
      status: 'ok', reason: null, message: null,
      trigger_prevalence: 0.5, random_prevalence: 0.0, lift: null,
      n_trigger: 4, n_random: 20, sample_design: 'unconditional_random',
      n_requested: 20, n_drawn: 20,
    }));
    renderPanel(detailFixture());
    fireEvent.click(screen.getByTestId('ic-random-control-generate'));
    const line = await screen.findByTestId('ic-random-control-prevalence');
    expect(line.textContent).toContain('無定義');
    expect(line.textContent).not.toContain('Infinity');
    expect(line.textContent).not.toContain('NaN');
  });
});
