/**
 * GAP-3 UX **Task 7.6** 前端驗收（`--run icEventBatchDisclosure`；SPEC L3146–3152 之①~⑦）。
 *
 * 🔴 ③「批次事實欄不可編輯」用**render 後之 DOM 查詢**（`queryByRole`），不是讀原始碼形狀。
 * 🔴 ④／⑦「送出 payload」攔的是**真的送出去的 HTTP body**（沿用 `icEventAnalysisRequest` 之作法）
 *    ——grep 到鍵名不代表它真的被序列化進 payload。
 */
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EventBatchDisclosurePanel from './EventBatchDisclosurePanel';
import { EVENT_FIELD_FORMATTERS, IC_BATCH_FACT_FIELDS, SEARCH_DISCLOSURE_FIELDS } from '@/lib/eventFieldFormatters';
import { selectable } from '@/lib/eventDimensions';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { EventImportDetail, ICAnalysisConfig } from '@/lib/types';

/** 既有批：`label_definition.window.horizon_bars === 3`（D-7 深度宣告之殘值）——⑦之陷阱來源。 */
function detailFixture(over: Partial<EventImportDetail['batch_facts']> = {}): EventImportDetail {
  const rows = [
    { event_id: 'ETHUSDT:12h:1700000000000', t0_ms: 1700000000000, label: 1 },
    { event_id: 'ETHUSDT:12h:1700043200000', t0_ms: 1700043200000, label: 0 },
  ];
  return {
    summary: {
      import_id: 'imp-1', source_name: 'unit', upload_sha256: 'a'.repeat(64),
      imported_at: '2026-08-28T00:00:00Z', n_events: rows.length,
      symbols: ['ETHUSDT'], timeframes: ['12h'], direction: 'long', scenario: 'C',
    },
    records: [{ label_definition: { window: { horizon_bars: 3 } } }],
    batch_facts: {
      scenario: 'C',
      control_kind: 'user_labeled_same_trigger',
      direction: 'long',
      t0: rows.map((r) => ({ event_id: r.event_id, t0_ms: r.t0_ms })),
      label: rows.map((r) => ({ event_id: r.event_id, label: r.label })),
      ...over,
    },
    declaration_seeds: {
      entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close', decision_offset_bars: 0,
    },
    batch_fact_notes: { control_kind_values: ['user_labeled_same_trigger'] },
  };
}

afterEach(cleanup);

describe('Task 7.6 ①② — 批次事實欄之揭露文案由共用 formatter 產生', () => {
  it('① 各段文字皆出現，且**逐字**等於共用 registry 之輸出（不是本頁另寫一份）', () => {
    const d = detailFixture();
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    expect(screen.getByTestId('ic-batch-fact-scenario').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.scenario('C'));
    expect(screen.getByTestId('ic-batch-fact-control_kind').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.control_kind('user_labeled_same_trigger'));
    expect(screen.getByTestId('ic-batch-fact-direction').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.direction('long'));
    expect(screen.getByTestId('ic-batch-fact-t0').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.t0(d.batch_facts.t0));
    expect(screen.getByTestId('ic-batch-fact-label').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.label(d.batch_facts.label as { event_id: string; label: 0 | 1 }[]));
  });

  it('① 兩頁**共用 registry 但欄集不相等**（證明共用的是 registry 而非欄集）', () => {
    expect(new Set(IC_BATCH_FACT_FIELDS)).not.toEqual(new Set(SEARCH_DISCLOSURE_FIELDS));
    // 交集非空 ⇒ 真的有共用（欄集完全不相交的話，「共用」就是空話）
    const shared = IC_BATCH_FACT_FIELDS.filter((f) => SEARCH_DISCLOSURE_FIELDS.includes(f));
    expect(shared.length).toBeGreaterThan(0);
  });

  it('② 改批次之任一事實欄 ⇒ 顯示字串 `!==` 前值', () => {
    const first = render(
      <EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />,
    );
    const before = screen.getByTestId('ic-batch-fact-scenario').textContent;
    first.unmount();
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}}
        detail={detailFixture({ scenario: 'A' })}
      />,
    );
    expect(screen.getByTestId('ic-batch-fact-scenario').textContent).not.toBe(before);
  });
});

describe('Task 7.6 ③⑤ — 唯讀 vs 可設定', () => {
  it('③ 批次事實欄之 DOM 節點**無**任何可輸入控制項', () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />);
    const facts = within(screen.getByTestId('ic-batch-facts'));
    expect(facts.queryByRole('combobox')).toBeNull();
    expect(facts.queryByRole('textbox')).toBeNull();
    expect(facts.queryByRole('spinbutton')).toBeNull();
  });

  it('🔴 over：分析參數區**必須**有可輸入控制項（不得因為③把整頁做成唯讀）', () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />);
    const params = within(screen.getByTestId('ic-analysis-params'));
    expect(params.queryAllByRole('spinbutton').length).toBeGreaterThan(0);
    expect(params.queryAllByRole('combobox').length).toBeGreaterThan(0);
  });

  it('⑤ 三元組之**可操作**選項集合 == §F-1′ 之唯一三元組；其餘 disabled 且顯示理由', () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />);
    for (const dim of ['entry_price_semantic', 'label_return_mode'] as const) {
      const sel = screen.getByTestId(`ic-param-${dim}`) as HTMLSelectElement;
      const enabled = Array.from(sel.querySelectorAll('option')).filter((o) => !o.disabled).map((o) => o.value);
      expect(new Set(enabled)).toEqual(new Set(selectable('/ic-analysis', dim)));
      // 其餘值 disabled，且各自看得到理由
      for (const o of Array.from(sel.querySelectorAll('option')).filter((x) => x.disabled)) {
        expect(o.title).not.toBe('');
        expect(screen.getByTestId(`ic-param-blocked-${dim}-${o.value}`).textContent).toContain(o.title);
      }
    }
    expect(new Set(selectable('/ic-analysis', 'entry_price_semantic'))).toEqual(new Set(['trigger_close']));
    expect(new Set(selectable('/ic-analysis', 'label_return_mode'))).toEqual(new Set(['close_to_close']));
    // `k` 之可輸入範圍鎖定（§F-1′ 之 k=0）
    const k = screen.getByTestId('ic-param-decision-offset-bars') as HTMLInputElement;
    expect(k.min).toBe('0');
    expect(k.max).toBe('0');
    // 🔴 R3 群集 A：`min`／`max` 只是提示，鎖定路徑必須 `readOnly`，且程式化設值要被夾回
    expect(k.readOnly).toBe(true);
  });

  it('🔴 under（R3 群集 A）：把分析參數之 k 改成 3 ⇒ 送出之 `event_label_spec` 仍為 0', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={undefined} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.change(screen.getByTestId('ic-param-decision-offset-bars'), { target: { value: '3' } });
    expect(spec?.decision_offset_bars).toBe(0);
  });

  it('🔴 under（R3 群集 A）：既有批之種子 `k=2` 也要被夾回 0（載入當下就不能落在鎖定範圍外）', () => {
    const d = detailFixture();
    d.declaration_seeds.decision_offset_bars = 2;   // 舊批宣告過非 F-1′ 之值
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    expect((screen.getByTestId('ic-param-decision-offset-bars') as HTMLInputElement).value).toBe('0');
  });
});

// ───────── ④⑥⑦：真的送出去的 payload ＋「不回寫事件批」之執行期證明 ─────────

const sent: { url: string; method: string; body: Record<string, unknown> }[] = [];

function baseConfig(over: Partial<ICAnalysisConfig> = {}): ICAnalysisConfig {
  return {
    ...useICAnalysisStore.getState().config,
    symbol: 'ETHUSDT', timeframe: '12h', config_hash: 'abc123', mode: 'event',
    ...over,
  } as ICAnalysisConfig;
}

beforeEach(() => {
  sent.length = 0;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const method = String(init?.method ?? 'GET').toUpperCase();
    sent.push({ url: String(url), method, body: init?.body ? JSON.parse(String(init.body)) : {} });
    if (String(url).endsWith('/analyze')) {
      return new Response(JSON.stringify({ task_id: 't1', status: 'running' }), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    }
    if (String(url).includes('/case/events/')) {
      return new Response(JSON.stringify(detailFixture()), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    }
    return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function startWith(config: ICAnalysisConfig) {
  const { result } = renderHook(() => useICAnalysis());
  await act(async () => { await result.current.startAnalysis(config); });
  const analyze = sent.filter((s) => s.url.endsWith('/analyze'));
  expect(analyze).toHaveLength(1);
  return analyze[0].body;
}

describe('Task 7.6 ④⑥⑦ — 分析參數之送出與「不回寫」', () => {
  it('④ `horizon_bars` 輸入 `7` ⇒ 送出 payload 之 `event_label_spec.horizon_bars === 7`', async () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={undefined} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.change(screen.getByTestId('ic-param-horizon-bars'), { target: { value: '7' } });
    expect(spec?.horizon_bars).toBe(7);

    const body = await startWith(baseConfig({ event_import_id: 'imp-1', event_label_spec: spec }));
    expect((body.event_label_spec as { horizon_bars: number }).horizon_bars).toBe(7);
  });

  it('⑦ 🔴 既有批之 `window.horizon_bars === 3` 且使用者未改 ⇒ h `=== 1`（**非** 3），面板與 payload 兩層皆是', async () => {
    const d = detailFixture();
    expect(
      ((d.records[0].label_definition as { window: { horizon_bars: number } }).window.horizon_bars),
    ).toBe(3);   // 正向對照：fixture 真的帶著那個陷阱值

    // (a) **面板層**：分析參數區顯示的初始值是字面常數 1，不是該批落檔的深度殘值 3
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    expect((screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement).value).toBe('1');
    cleanup();

    // (b) **payload 層**：真的送出去的 body 亦為 1（兩層各有守衛，故兩層都要驗）
    const body = await startWith(baseConfig({ event_import_id: 'imp-1' }));
    expect((body.event_label_spec as { horizon_bars: number }).horizon_bars).toBe(1);
  });

  it('⑥ 改分析參數**不回寫**事件批：對 `/case/events/` 只有 GET，且重查之 records 不變', async () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} />);
    await waitFor(() => expect(screen.getByTestId('ic-batch-facts')).toBeTruthy());
    fireEvent.change(screen.getByTestId('ic-param-horizon-bars'), { target: { value: '9' } });
    await startWith(baseConfig({ event_import_id: 'imp-1', event_label_spec: { horizon_bars: 9 } }));

    const batchCalls = sent.filter((s) => s.url.includes('/case/events/'));
    expect(batchCalls.length).toBeGreaterThan(0);       // 正向對照：真的有碰過那個端點
    for (const c of batchCalls) {
      expect(c.method, `不得對事件批發 ${c.method}`).toBe('GET');
    }
    // 重查 detail：落檔記錄之 `window.horizon_bars` 仍為 3（分析參數沒有寫回去）
    const { getEventImport } = await import('@/lib/api');
    const again = await getEventImport('imp-1');
    expect(
      (again.records[0].label_definition as { window: { horizon_bars: number } }).window.horizon_bars,
    ).toBe(3);
  });
});
