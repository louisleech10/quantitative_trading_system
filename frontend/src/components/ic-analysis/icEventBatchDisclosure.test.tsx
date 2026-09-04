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
import { RETURN_MEASURE_PRESETS, isSubmittableLabelSpec, selectable } from '@/lib/eventDimensions';
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
      // `G3-D2` D1.6：第六鍵。本 fixture 為 C 之舊批形態 ⇒ null（顯示「（未宣告）」）。
      label_origin: null,
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
    // 🔴 `G3-D2` D1.7：兩個枚舉 select 改為三選項 radio（combobox → radio）。
    //    改的是控制項型別，**不是**放寬「參數區必須可輸入」這條。
    expect(params.queryAllByRole('radio').length).toBeGreaterThan(0);
  });

  it('⑤ `G3-D2` D1.7：報酬量法為三選項；**不得**出現兩欄之進階直改 select', () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />);
    // (a) 三個 preset 都在
    for (const key of ['same_bar', 'follow_through', 'hold']) {
      expect(screen.getByTestId(`ic-param-return-measure-${key}`)).toBeTruthy();
    }
    // (b) 🔴 進階直改**不存在**（D-001 D1.7：兩個 select 各自列值會列出矩陣外組合，
    //     例如 `(trigger_close, open_to_close)` 幾何窗長 0；進階直改留待 D4.2）
    expect(screen.queryByTestId('ic-param-entry_price_semantic')).toBeNull();
    expect(screen.queryByTestId('ic-param-label_return_mode')).toBeNull();
    // (c) 純函式層之可選集合仍為 D1 之支援域投影（解灰之來源未被 UI 改動所遮蔽）
    expect(new Set(selectable('/ic-analysis', 'entry_price_semantic')))
      .toEqual(new Set(['trigger_open', 'trigger_close']));
    expect(new Set(selectable('/ic-analysis', 'label_return_mode')))
      .toEqual(new Set(['open_to_close', 'open_to_horizon_close', 'close_to_close']));
    // (d) 三個 preset 之三元組**全部**可送出（否則 UI 給了選不了的選項）
    for (const p of RETURN_MEASURE_PRESETS) {
      expect(isSubmittableLabelSpec({
        horizon_bars: 1,
        entry_price_semantic: p.entry_price_semantic,
        label_return_mode: p.label_return_mode,
        decision_offset_bars: 0,
      })).toBe(true);
    }
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
    // 🔴 `CODEX-R3-P2-01` 之後，h input 在**未選量法**時是 disabled ⇒ 真實使用者
    //    不可能在那個狀態下打字。本條改為從「已選續漲」起跑，才是可達的操作序列。
    //    （原版以 `labelSpec={undefined}` 對 disabled 欄位 fireEvent，測得到但使用者做不到。）
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()}
        labelSpec={{
          horizon_bars: 1,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'close_to_close',
          decision_offset_bars: 0,
        }}
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

    // (a) **面板層**：不得顯示該批落檔的深度殘值 3。
    //     🔴 `CODEX-R3-P2-01` 之修正**收緊**了本斷言：原本期望字面常數 `'1'`，
    //     但後端在未選量法時會依宣告深度導出（深度 3 就跑 h=3）⇒ 顯示 `1` 本身
    //     就是數字誤導。現在未選時顯示**空值且 disabled**，並以
    //     `ic-param-h-backend-derived` 說明由誰決定。
    //     **原意（不得顯示 3）不但保留，而且更強**：現在連任何數字都不顯示。
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    const hInput = screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement;
    expect(hInput.value).not.toBe('3');   // 本條之原始防線：不得種子化為落檔殘值
    expect(hInput.value).toBe('');
    expect(hInput.disabled).toBe(true);
    cleanup();

    // (b) **payload 層**：🔴 `CODEX-R2-P1-03` 之修正改變了這一半的形狀——
    //     前端未設定時**整個鍵省略**（不再送 `{horizon_bars: 1}`），由後端依
    //     `lookahead_bars_declared` 導出。本條之原意（「不得以匯出檔之 window.horizon_bars=3
    //     種子化」）**未放寬**：鍵不存在 ⇒ 前端連猜的機會都沒有，比送常數更強；
    //     「後端也不會讀那個窗欄」由 `tests/api -k ic_event_label_defaults` 之
    //     `…_never_reads_window_horizon_bars` 釘住（宣告深度 2、窗欄殘值 9 ⇒ h=2）。
    const body = await startWith(baseConfig({ event_import_id: 'imp-1' }));
    expect('event_label_spec' in (body as Record<string, unknown>)).toBe(false);
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

// ══════════════════════════════════════════════════════════════════════════
// `D-001` Task D1.7 — 報酬量法三選項＋送出守衛
// ══════════════════════════════════════════════════════════════════════════

describe('G3-D2 D1.7 — 報酬量法三選項', () => {
  it('選「當根」⇒ spec 恰四鍵、entry/mode 為 (trigger_open, open_to_close)、h 為 inert 哨兵 1', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={{ horizon_bars: 5 }} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-return-measure-same_bar'));
    expect(spec?.entry_price_semantic).toBe('trigger_open');
    expect(spec?.label_return_mode).toBe('open_to_close');
    // 🔴 「當根」之 h 不參與計算 ⇒ 一律送 1（不是沿用使用者原本的 5）
    expect(spec?.horizon_bars).toBe(1);
  });

  it('選「持有」⇒ (trigger_open, open_to_horizon_close)，且 h **保留**使用者原值', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={{ horizon_bars: 5 }} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-return-measure-hold'));
    expect(spec?.entry_price_semantic).toBe('trigger_open');
    expect(spec?.label_return_mode).toBe('open_to_horizon_close');
    expect(spec?.horizon_bars).toBe(5);   // 持有會用到 h ⇒ 不得覆寫成 1
  });

  it('選「續漲」⇒ (trigger_close, close_to_close)', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={{ horizon_bars: 3 }} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-return-measure-follow_through'));
    expect(spec?.entry_price_semantic).toBe('trigger_close');
    expect(spec?.label_return_mode).toBe('close_to_close');
    expect(spec?.horizon_bars).toBe(3);
  });

  it('🔴 非 preset 之組合 ⇒ 面板顯示警示（不靜默改寫使用者的值）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 1,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'open_to_close',   // 幾何窗長 0，矩陣外
        }}
      />,
    );
    expect(screen.getByTestId('ic-param-return-measure-invalid')).toBeTruthy();
    // 🔴 對照：合法 preset 下**不得**顯示警示（否則本條恆綠）
    cleanup();
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 1,
          entry_price_semantic: 'trigger_open',
          label_return_mode: 'open_to_close',
        }}
      />,
    );
    expect(screen.queryByTestId('ic-param-return-measure-invalid')).toBeNull();
  });
});

describe('G3-D2 D1.7 — 送出守衛', () => {
  it('🔴 偽造 (trigger_close, open_to_close) ⇒ 擋下，`fetch` **0 次**', async () => {
    const { result } = renderHook(() => useICAnalysis());
    const before = sent.length;
    await act(async () => {
      await expect(result.current.startAnalysis(baseConfig({
        event_import_id: 'imp-1',
        event_label_spec: {
          horizon_bars: 1,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'open_to_close',
        },
      }))).rejects.toThrow(/報酬量法/);
    });
    expect(sent.filter((s) => s.url.endsWith('/analyze')).length).toBe(0);
    expect(sent.length).toBe(before);
  });

  it('🔴 over 向：三個 preset 都送得出去（守衛不是「一律擋」）', async () => {
    for (const p of RETURN_MEASURE_PRESETS) {
      cleanup();
      sent.length = 0;
      const body = await startWith(baseConfig({
        event_import_id: 'imp-1',
        event_label_spec: {
          horizon_bars: 2,
          entry_price_semantic: p.entry_price_semantic,
          label_return_mode: p.label_return_mode,
          decision_offset_bars: 0,
        },
      }));
      const s = body.event_label_spec as Record<string, unknown>;
      expect(s.entry_price_semantic).toBe(p.entry_price_semantic);
      expect(s.label_return_mode).toBe(p.label_return_mode);
    }
  });

  it('🔴 兩欄皆缺 ⇒ **放行**（由後端依宣告深度導出，不在前端算第二份預設）', async () => {
    sent.length = 0;
    const body = await startWith(baseConfig({
      event_import_id: 'imp-1', event_label_spec: { horizon_bars: 4 },
    }));
    expect((body.event_label_spec as { horizon_bars: number }).horizon_bars).toBe(4);
  });

  it('🔴 只給一半（有 entry 無 mode）⇒ 擋下（半組值會與後端導出的另一半拼成未預期組合）', () => {
    expect(isSubmittableLabelSpec({ horizon_bars: 1, entry_price_semantic: 'trigger_open' })).toBe(false);
    expect(isSubmittableLabelSpec({ horizon_bars: 1, label_return_mode: 'open_to_close' })).toBe(false);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// B-D1 R2 閉合輪 — 三家 review 命中之缺陷（前端半邊）
// ══════════════════════════════════════════════════════════════════════════

describe('B-D1 R2 閉合 — CODEX-R2-P1-03：前端不得送預設 spec', () => {
  it('🔴 未設定 spec ⇒ payload **完全沒有** `event_label_spec` 鍵（讓後端依深度導出）', async () => {
    sent.length = 0;
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.startAnalysis(baseConfig({ event_import_id: 'imp-1' }));
    });
    const analyze = sent.filter((s) => s.url.endsWith('/analyze'));
    expect(analyze).toHaveLength(1);
    // 🔴 修正前：這裡是 `{ horizon_bars: 1 }`，而後端 `setdefault` 壓不過它
    //    ⇒ 宣告深度 3 的批「持有」實際跑成 h=1。鍵必須**不存在**，不是存在但為 undefined。
    expect('event_label_spec' in (analyze[0].body as Record<string, unknown>)).toBe(false);
  });

  it('🔴 over 向：有設定 spec ⇒ 照原樣送出（證明上一條不是「一律不送」）', async () => {
    sent.length = 0;
    const spec = {
      horizon_bars: 3,
      entry_price_semantic: 'trigger_open',
      label_return_mode: 'open_to_horizon_close',
      decision_offset_bars: 0,
    };
    const body = await startWith(baseConfig({ event_import_id: 'imp-1', event_label_spec: spec }));
    expect(body.event_label_spec).toEqual(spec);
  });
});

describe('B-D1 R2 閉合 — CODEX-R2-P1-03 後半：「當根」之 h 不可編輯', () => {
  it('選「當根」⇒ h 輸入框 disabled 且顯示原因；其他量法可編輯', () => {
    const { rerender } = render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 1,
          entry_price_semantic: 'trigger_open',
          label_return_mode: 'open_to_close',
        }}
      />,
    );
    const h = screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement;
    expect(h.disabled).toBe(true);
    expect(screen.getByTestId('ic-param-h-inert')).toBeTruthy();

    // 🔴 over 向：「持有」下 h **必須**可編輯（否則就是把整個欄位鎖死）
    rerender(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 3,
          entry_price_semantic: 'trigger_open',
          label_return_mode: 'open_to_horizon_close',
        }}
      />,
    );
    expect((screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement).disabled).toBe(false);
    expect(screen.queryByTestId('ic-param-h-inert')).toBeNull();
  });
});

describe('B-D1 R2 閉合 — GROK-R2-P2-03：裁定 5「UI 比支援矩陣嚴」須被具名釘住', () => {
  it('🔴 `(trigger_open, close_to_close)` 雖在後端矩陣內，UI 守衛**仍拒**', () => {
    // grok 指出：既有測試（preset 可送／矩陣外不可送／半組擋／兩缺放行）在
    // 把守衛改成「鏡像後端四對」時**全綠** ⇒ 裁定 5 會靜默消失而 CI 不紅。
    // 本條就是那個缺的負例：它是矩陣內、非 preset 的那一對。
    expect(isSubmittableLabelSpec({
      horizon_bars: 1,
      entry_price_semantic: 'trigger_open',
      label_return_mode: 'close_to_close',
      decision_offset_bars: 0,
    })).toBe(false);
    // 🔴 對照：同樣是矩陣內、但**是** preset 的那三對須放行
    for (const p of RETURN_MEASURE_PRESETS) {
      expect(isSubmittableLabelSpec({
        horizon_bars: 1,
        entry_price_semantic: p.entry_price_semantic,
        label_return_mode: p.label_return_mode,
        decision_offset_bars: 0,
      })).toBe(true);
    }
    // 🔴 三個 preset 之外，`RETURN_MEASURE_PRESETS` 不得悄悄長出第四個
    //    （若日後要放寬到矩陣四對，必須改本條，而不是「順手」改守衛）
    expect(RETURN_MEASURE_PRESETS).toHaveLength(3);
  });
});

describe('B-D1 R3 準備期自查 — 「還沒選」與「選了非法組合」不得共用同一個紅字', () => {
  it('🔴 `labelSpec` 未設定 ⇒ **不**顯示「送出會被擋下」，改顯示中性提示', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    // 修正前：這裡是紅字「送出會被擋下」——而 `useICAnalysis` 的守衛在 spec 未設定時
    // 根本不跑，送得出去且後端會依宣告深度導出預設 ⇒ **畫面與事實相反**。
    expect(screen.queryByTestId('ic-param-return-measure-invalid')).toBeNull();
    expect(screen.getByTestId('ic-param-return-measure-unset')).toBeTruthy();
  });

  it('🔴 over 向：使用者**選了**非 preset 的組合 ⇒ 紅字照舊、不得退化成中性提示', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 1,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'open_to_close',   // 幾何窗長 0，矩陣外
        }}
      />,
    );
    expect(screen.getByTestId('ic-param-return-measure-invalid')).toBeTruthy();
    expect(screen.queryByTestId('ic-param-return-measure-unset')).toBeNull();
  });
});

describe('B-D1 R3 閉合 — CODEX-R3-P2-01：未選量法時不得顯示會與後端不符的 h', () => {
  it('🔴 `labelSpec` 未設定 ⇒ h input 為空且 disabled，並說明由後端依深度決定', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    const h = screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement;
    // 修正前：value 是 fallback 的 `1`，而後端對宣告深度 3 的批實際跑 h=3 ⇒ 數字誤導。
    expect(h.value).toBe('');
    expect(h.disabled).toBe(true);
    expect(screen.getByTestId('ic-param-h-backend-derived')).toBeTruthy();
  });

  it('🔴 over 向：選了量法之後 h 可編輯且顯示實際值（不得因上一條把欄位鎖死）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 5,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'close_to_close',
          decision_offset_bars: 0,
        }}
      />,
    );
    const h = screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement;
    expect(h.value).toBe('5');
    expect(h.disabled).toBe(false);
    expect(screen.queryByTestId('ic-param-h-backend-derived')).toBeNull();
  });
});
