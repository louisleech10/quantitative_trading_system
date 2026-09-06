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
    // 🔴 `G3-D2` D4.3：`decision_offset_bars` 已自 seeds 移除（k 是分析參數，不由匯入檔種子化）。
    declaration_seeds: {
      entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close',
    },
    batch_fact_notes: {
      control_kind_values: ['user_labeled_same_trigger'],
      // 批內**記錄**之 k 值集合（事實）；空清單＝該批沒有這個欄。
      decision_offset_bars_record_values: [0],
    },
    // 🔴 `G3-D2` D5.1：本 fixture 為**舊批形態** ⇒ 兩欄皆 null（缺席是通則）。
    //    「有落檔規則身分」之情形由 `icRandomControl.test.tsx` 覆蓋。
    receipt_batch: { label_rule: null, random_control_spec: null },
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

  it('⑤ `G3-D2` D4.2：報酬量法三選項仍在；進階直改**改為預設收起、展開後才出現**', () => {
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={detailFixture()} />);
    // (a) 三個 preset 都在
    for (const key of ['same_bar', 'follow_through', 'hold']) {
      expect(screen.getByTestId(`ic-param-return-measure-${key}`)).toBeTruthy();
    }
    // (b) 🔴 **D4.2 改寫**：原斷言「進階直改不存在」之理由（兩個 select 會列出矩陣外組合）
    //     已由 `kind: 'pair_rejected'` 解決 ⇒ 開放，但**預設收起**（preset 仍是主路徑）。
    expect(screen.queryByTestId('ic-param-entry_price_semantic')).toBeNull();
    expect(screen.queryByTestId('ic-param-label_return_mode')).toBeNull();
    fireEvent.click(screen.getByTestId('ic-param-advanced-toggle'));
    expect(screen.getByTestId('ic-param-entry_price_semantic')).toBeTruthy();
    expect(screen.getByTestId('ic-param-label_return_mode')).toBeTruthy();
    // (c) 純函式層之可選集合＝D4.2 之全矩陣投影（五值全開；成對限制由 selection 承擔）
    expect(new Set(selectable('/ic-analysis', 'entry_price_semantic'))).toEqual(new Set([
      'trigger_open', 'trigger_close', 'next_open', 'decision_bar_open', 'decision_bar_close',
    ]));
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
    // 🔴 `G3-D2` **D4.2 改寫**：k 之輸入**已解鎖**（原斷言 `max === '0'`、`readOnly === true`）。
    //    改寫理由：k 已不在支援矩陣內，其上界是**逐事件可行域**（資料決定，前端算不出來）
    //    ⇒ 前端不得再假裝有一個 `max`。下界仍取契約 `min`。
    const k = screen.getByTestId('ic-param-decision-offset-bars') as HTMLInputElement;
    expect(k.min).toBe('0');
    expect(k.max).toBe('');            // 無上界（不是「上界為 0」）
    expect(k.readOnly).toBe(false);
  });

  it('🔴 D4.2：把分析參數之 k 改成 3 ⇒ 送出之 `event_label_spec` **就是 3**（不再夾回 0）', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" labelSpec={undefined} detail={detailFixture()}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.change(screen.getByTestId('ic-param-decision-offset-bars'), { target: { value: '3' } });
    expect(spec?.decision_offset_bars).toBe(3);
    // over 向：契約下界仍守住（負值夾回 min，不是靜默接受）
    fireEvent.change(screen.getByTestId('ic-param-decision-offset-bars'), { target: { value: '-1' } });
    expect(spec?.decision_offset_bars).toBe(0);
  });

  it('🔴 D4.3：初始 k ＝契約 min 常數；批次記錄之 k 以**獨立欄**並排顯示，不當種子', () => {
    const d = detailFixture();
    d.batch_fact_notes.decision_offset_bars_record_values = [1];   // 舊批記錄了 k=1
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    // 初始值是常數 0——**不是** 1（記錄值不得種子化分析參數）
    expect((screen.getByTestId('ic-param-decision-offset-bars') as HTMLInputElement).value).toBe('0');
    // 兩個值都要看得到，且分別講清楚是什麼
    const dual = screen.getByTestId('ic-param-k-dual').textContent ?? '';
    expect(dual).toContain('批次記錄的 k ＝ 1');
    expect(dual).toContain('本次分析的 k ＝ 0');
  });

  it('🔴 D4.3：批內沒有 k 欄 ⇒ 顯示「這批沒有這個欄」，**不得**顯示成 0', () => {
    const d = detailFixture();
    d.batch_fact_notes.decision_offset_bars_record_values = [];
    render(<EventBatchDisclosurePanel importId="imp-1" labelSpec={undefined} onChangeLabelSpec={() => {}} detail={d} />);
    const dual = screen.getByTestId('ic-param-k-dual').textContent ?? '';
    expect(dual).toContain('這批沒有這個欄');
    expect(dual).toContain('本次分析的 k ＝ 0');
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
  it('🔴 `G3-D2` D4.2：`(trigger_open, close_to_close)` **改為放行**（裁定 5 之前提已解除）', () => {
    // 原條釘住的是裁定 5「UI 比支援矩陣嚴」，其**理由**逐字為：
    // 「D1 的 UI 根本產不出那一對，能出現只有偽造或程式化設值」。
    // D4.2 開放**進階直改兩欄** ⇒ UI 產得出全部 13 對，該理由消失
    // ⇒ 守衛改為 pair-aware（擋 `rejected_pairs`、放行其餘 13 對）。
    // 🔴 **這不是放寬**：擋的對象換成幾何上真的算不出來的那兩對，並在下面逐條釘住。
    expect(isSubmittableLabelSpec({
      horizon_bars: 1,
      entry_price_semantic: 'trigger_open',
      label_return_mode: 'close_to_close',
      decision_offset_bars: 0,
    })).toBe(true);
    // 🔴 對照①：三個 preset 仍須放行（preset 機制未被 D4.2 取代，只是不再是唯一入口）
    for (const p of RETURN_MEASURE_PRESETS) {
      expect(isSubmittableLabelSpec({
        horizon_bars: 1,
        entry_price_semantic: p.entry_price_semantic,
        label_return_mode: p.label_return_mode,
        decision_offset_bars: 0,
      })).toBe(true);
    }
    expect(RETURN_MEASURE_PRESETS).toHaveLength(3);
    // 🔴 對照②（**新的負例**）：兩個幾何零窗對仍被擋——沒有這一段，守衛可以改成「恆放行」而全綠
    for (const entry of ['trigger_close', 'decision_bar_close']) {
      expect(isSubmittableLabelSpec({
        horizon_bars: 1, entry_price_semantic: entry,
        label_return_mode: 'open_to_close', decision_offset_bars: 0,
      }), `${entry} × open_to_close`).toBe(false);
    }
    // 🔴 對照③：枚舉外之值仍被擋（不得對未知字面 fail-open）
    expect(isSubmittableLabelSpec({
      horizon_bars: 1, entry_price_semantic: 'bogus',
      label_return_mode: 'close_to_close', decision_offset_bars: 0,
    })).toBe(false);
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

describe('B-D1 R4 閉合 — GROK-R4-P2-01：同一個 h 在面板的**每一處**顯示都不得與後端不符', () => {
  it('🔴 未選量法 ⇒ window-note 不得寫出具體根數', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    const note = screen.getByTestId('ic-param-window-note').textContent ?? '';
    // 修正前：「本次答案窗 ＝ 1 根」——input 改空了，這行還在報 1。
    expect(note).not.toMatch(/本次答案窗 ＝ \d+ 根/);
    expect(note).toContain('由後端依這批宣告的深度決定');
  });

  it('🔴 over 向：選了量法 ⇒ window-note 報出的根數**等於** input 顯示的值', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} onChangeLabelSpec={() => {}}
        labelSpec={{
          horizon_bars: 4,
          entry_price_semantic: 'trigger_close',
          label_return_mode: 'close_to_close',
          decision_offset_bars: 0,
        }}
      />,
    );
    const h = (screen.getByTestId('ic-param-horizon-bars') as HTMLInputElement).value;
    expect(h).toBe('4');
    expect(screen.getByTestId('ic-param-window-note').textContent).toContain(`本次答案窗 ＝ ${h} 根`);
  });

  it('🔴 掃全檔之結論釘住：點 preset 後，畫面顯示的 h 與送出的 h 相同（殘留 B1-DEPTH-1 之邊界）', () => {
    let spec: ICAnalysisConfig['event_label_spec'];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined}
        onChangeLabelSpec={(next) => { spec = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-return-measure-hold'));
    // 🔴 這裡送出的是字面常數 1，**不是**該批宣告的深度 3（`detailFixture` 之陷阱值）。
    //    ⇒ 「依宣告深度之預設」只有在使用者**完全不碰面板**時才拿得到。
    //    本條**不主張那是對的**，只釘住「顯示＝送出」這件事已成立；
    //    要不要讓 preset 也跟著深度走，是殘留 `B1-DEPTH-1`（見 R5 brief）。
    expect(spec?.horizon_bars).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// `G3-D2` **Task D4.3** — k／h 掃描切換、兩上界揭露、掃描結果矩陣
//
// 🔴 **前端一律只顯示後端給的數字**：兩上界之公式住 producer 之 `feasible_bounds`，
//    在此重算就是第二份實作（本 epic 反覆付過代價的形態）。
// ═══════════════════════════════════════════════════════════════════════════

describe('D4.3 — k／h 掃描之「單值／掃到 m」切換', () => {
  it('打開 k 掃描 ⇒ 送出 `decision_offset_bars_max`；關掉 ⇒ 整個鍵回 `null`（不是空物件）', () => {
    let scan: unknown = 'untouched';
    const { rerender } = render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={{ horizon_bars: 2, decision_offset_bars: 3 }}
        onChangeLabelSpec={() => {}} labelScan={null}
        onChangeLabelScan={(next) => { scan = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-scan-k-toggle'));
    expect(scan).toEqual({ decision_offset_bars_max: 3 });   // 預設由目前的 k 帶入

    rerender(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={{ horizon_bars: 2, decision_offset_bars: 3 }}
        onChangeLabelSpec={() => {}} labelScan={{ decision_offset_bars_max: 3 }}
        onChangeLabelScan={(next) => { scan = next; }}
      />,
    );
    fireEvent.click(screen.getByTestId('ic-param-scan-k-toggle'));
    // 🔴 兩軸都關 ⇒ `null`：送空物件到後端仍代表「有掃描」（`event_label_scan is not None`）
    expect(scan).toBeNull();
  });

  it('🔴 掃描開啟時 k 之單值輸入 disabled（同一個參數不得有兩個真相源）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={{ horizon_bars: 2 }}
        onChangeLabelSpec={() => {}} labelScan={{ decision_offset_bars_max: 4 }}
        onChangeLabelScan={() => {}}
      />,
    );
    expect((screen.getByTestId('ic-param-decision-offset-bars') as HTMLInputElement).disabled)
      .toBe(true);
    expect((screen.getByTestId('ic-param-scan-k-max') as HTMLInputElement).value).toBe('4');
  });

  it('🔴 over：沒有給 `onChangeLabelScan` ⇒ 掃描區塊整個不出現（不顯示點不動的控制項）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    expect(screen.queryByTestId('ic-param-scan')).toBeNull();
  });
});

describe('D4.3／D4.2 — 兩上界之揭露（前端不自算）', () => {
  it('沒有揭露 ⇒ 明說「要分析過才知道」，**不猜數字**', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    const text = screen.getByTestId('ic-param-bounds').textContent ?? '';
    expect(text).toContain('要分析過才知道');
    expect(text).not.toMatch(/\d/);            // 一個數字都不得出現
  });

  it('有揭露 ⇒ 顯示後端給的兩個數字，且**寫明不是成功保證**（誠實邊界）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          k_max_feasible_at_h: 119, h_max_feasible_at_k: 1518,
          k_bound_status: 'bounded', h_bound_status: 'bounded',
        }}
      />,
    );
    const text = screen.getByTestId('ic-param-bounds').textContent ?? '';
    expect(text).toContain('119');
    expect(text).toContain('1518');
    expect(text).toContain('不保證');          // `D-001` D4.2 R4 之誠實邊界
  });

  it('🔴 `h_inert_for_mode`／`no_feasible_k` 各有自己的說法（不得都顯示成同一句）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          k_max_feasible_at_h: null, h_max_feasible_at_k: null,
          k_bound_status: 'no_feasible_k', h_bound_status: 'h_inert_for_mode',
        }}
      />,
    );
    const text = screen.getByTestId('ic-param-bounds').textContent ?? '';
    expect(text).toContain('沒有可行的 k');
    expect(text).toContain('不用 h');
  });
});

describe('D4.3 — 掃描結果矩陣（行 k、列 h）', () => {
  it('逐格渲染，且 `unavailable` 之格顯示為不可用（不是空白）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          event_label_scan: {
            scan_total: 4, scan_done: 4, capability: 'available', reason: null,
            scan_results: [
              { k: 0, h: 1, capability: 'available', n_events: 7, analysis_alignment_receipt_hash: 'a', ic_summary: {} },
              { k: 0, h: 2, capability: 'available', n_events: 7, analysis_alignment_receipt_hash: 'b', ic_summary: {} },
              { k: 1, h: 1, capability: 'available', n_events: 6, analysis_alignment_receipt_hash: 'c', ic_summary: {} },
              { k: 1, h: 2, capability: 'unavailable', reason: 'scan_cell_timeout', n_events: 0, analysis_alignment_receipt_hash: null, ic_summary: null },
            ],
          },
        }}
      />,
    );
    expect(screen.getByTestId('ic-scan-cell-0-1').textContent).toContain('7 筆');
    expect(screen.getByTestId('ic-scan-cell-1-2').textContent).toContain('不可用');
    expect(screen.getByTestId('ic-param-scan-result').textContent).toContain('4/4');
  });

  it('🔴 `scan_grid_too_large` ⇒ 顯示「沒有執行」與 reason（不得靜默不畫）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          event_label_scan: {
            scan_total: 420, scan_done: 0, capability: 'unavailable',
            reason: 'scan_grid_too_large', message: '超過上限 110', scan_results: [],
          },
        }}
      />,
    );
    const text = screen.getByTestId('ic-param-scan-rejected').textContent ?? '';
    expect(text).toContain('scan_grid_too_large');
    expect(text).toContain('110');
  });

  it('🔴 k 超過建議上限 ⇒ 警示但**不擋**（上限由後端揭露，前端不硬編）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={{ horizon_bars: 2, decision_offset_bars: 12 }}
        onChangeLabelSpec={() => {}}
        disclosure={{ decision_offset_bars_scan_max: 10 }}
      />,
    );
    expect(screen.getByTestId('ic-param-k-over-scan-max').textContent).toContain('10');
    // over 向：沒超過就不警示
    cleanup();
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={{ horizon_bars: 2, decision_offset_bars: 3 }}
        onChangeLabelSpec={() => {}}
        disclosure={{ decision_offset_bars_scan_max: 10 }}
      />,
    );
    expect(screen.queryByTestId('ic-param-k-over-scan-max')).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// `G3-D2` D4.3 — **全棧連通**：掃描網格與揭露欄真的接到 hook／page
//
// 🔴 本段存在的理由：D4.2／D4.3 之元件層測試全綠**不代表**功能可達。
//    本 epic 已為同型「兩端都有、但沒接上」付過兩次代價
//    （幽靈 feature_filter；`CODEX-R2-P1-03` 之 `{horizon_bars:1}` 讓後端預設不可達）。
// ═══════════════════════════════════════════════════════════════════════════

describe('D4.3 全棧連通 — `event_label_scan` 真的進 payload', () => {
  it('🔴 設定掃描 ⇒ 送出 body 之**頂層**有 `event_label_scan`（不在 `event_label_spec` 內）', async () => {
    const body = await startWith(baseConfig({
      event_import_id: 'imp-1',
      event_label_spec: { horizon_bars: 2, entry_price_semantic: 'trigger_open', label_return_mode: 'open_to_horizon_close', decision_offset_bars: 0 },
      event_label_scan: { decision_offset_bars_max: 2, horizon_bars_max: 3 },
    }));
    expect(body.event_label_scan).toEqual({ decision_offset_bars_max: 2, horizon_bars_max: 3 });
    // 🔴 它**不得**混進 spec——後端 normalizer 對多一鍵 fail-closed
    expect('event_label_scan' in (body.event_label_spec as Record<string, unknown>)).toBe(false);
    expect(Object.keys(body.event_label_spec as Record<string, unknown>).sort()).toEqual([
      'decision_offset_bars', 'entry_price_semantic', 'horizon_bars', 'label_return_mode',
    ]);
  });

  it('🔴 沒設定掃描 ⇒ 整個鍵**省略**（送 `{}` 在後端仍代表「有掃描」）', async () => {
    const body = await startWith(baseConfig({ event_import_id: 'imp-1' }));
    expect('event_label_scan' in (body as Record<string, unknown>)).toBe(false);
  });

  it('🔴 非事件路徑 ⇒ 不得出現 `event_label_scan`（legacy 呼叫形狀逐字不變）', async () => {
    const body = await startWith(baseConfig({
      mode: 'global', event_import_id: undefined,
      event_label_scan: { horizon_bars_max: 3 },
    } as Partial<ICAnalysisConfig>));
    expect('event_label_scan' in (body as Record<string, unknown>)).toBe(false);
  });
});

describe('D4.2 R2 閉合 — `CODEX-R2-P2-03`：bounds scope 之 null 語意必須說出來', () => {
  it('🔴 `bounds_scope_symbol` 為 `null`（未指定 run symbol）⇒ 顯示「對整批計算」', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          decision_offset_bars_capability: 'available',
          bounds_scope_symbol: null, bounds_scope_excluded_events: 0,
          k_max_feasible_at_h: 119, h_max_feasible_at_k: 1518,
          k_bound_status: 'bounded', h_bound_status: 'bounded',
        }}
      />,
    );
    const text = screen.getByTestId('ic-param-bounds-scope').textContent ?? '';
    expect(text).toContain('整批');
    expect(text).toContain('沒有指定 run symbol');
  });

  it('🔴 有 run symbol ⇒ 顯示「只對該 symbol」與被排除筆數（兩種 scope 各有自己的句子）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{
          decision_offset_bars_capability: 'available',
          bounds_scope_symbol: 'ETHUSDT', bounds_scope_excluded_events: 3,
          k_max_feasible_at_h: 119, h_max_feasible_at_k: 1518,
          k_bound_status: 'bounded', h_bound_status: 'bounded',
        }}
      />,
    );
    const text = screen.getByTestId('ic-param-bounds-scope').textContent ?? '';
    expect(text).toContain('ETHUSDT');
    expect(text).toContain('3 筆');
    expect(text).not.toContain('整批');
  });

  it('🔴 over 向：capability 非 available（或欄位整組缺席）⇒ **不說**（不對舊 task 亂講）', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
        disclosure={{ decision_offset_bars_capability: 'unavailable' }}
      />,
    );
    expect(screen.queryByTestId('ic-param-bounds-scope')).toBeNull();
    cleanup();
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()} labelSpec={undefined} onChangeLabelSpec={() => {}}
      />,
    );
    expect(screen.queryByTestId('ic-param-bounds-scope')).toBeNull();
  });
});

// ══════════════════════════════════════════════════════════════════════════
// `GAP3_EVENT_DISCLOSURE` — 2026-09-06 UAT B21/B22 回報之閉合
// ══════════════════════════════════════════════════════════════════════════

const SPEC_SAME_BAR = {
  horizon_bars: 1, entry_price_semantic: 'trigger_open',
  label_return_mode: 'open_to_close', decision_offset_bars: 0,
} as const;
const SPEC_HOLD = {
  horizon_bars: 3, entry_price_semantic: 'trigger_open',
  label_return_mode: 'open_to_horizon_close', decision_offset_bars: 0,
} as const;

function renderWithSpec(
  spec: unknown,
  extra: Record<string, unknown> = {},
) {
  return render(
    <EventBatchDisclosurePanel
      importId="imp-1"
      detail={detailFixture()}
      labelSpec={spec as never}
      onChangeLabelSpec={() => {}}
      {...extra}
    />,
  );
}

describe('Task 1.1 — 當根（open_to_close）時 h 掃描不適用', () => {
  it('🔴 選當根 ⇒ h 掃描之勾選與上限皆 disabled，並顯示理由', () => {
    renderWithSpec(SPEC_SAME_BAR, { labelScan: null, onChangeLabelScan: () => {} });
    const toggle = screen.getByTestId('ic-param-scan-h-toggle') as HTMLInputElement;
    const max = screen.getByTestId('ic-param-scan-h-max') as HTMLInputElement;
    expect(toggle.disabled).toBe(true);
    expect(max.disabled).toBe(true);
    expect(screen.getByTestId('ic-param-scan-h-inapplicable')).toBeTruthy();
  });

  it('正向對照：選「持有」⇒ h 掃描可用且**不**顯示理由（防恆常 disable）', () => {
    renderWithSpec(SPEC_HOLD, { labelScan: null, onChangeLabelScan: () => {} });
    expect((screen.getByTestId('ic-param-scan-h-toggle') as HTMLInputElement).disabled).toBe(false);
    expect(screen.queryByTestId('ic-param-scan-h-inapplicable')).toBeNull();
  });

  it('正向對照：k 掃描**不受**本規則影響（k 對當根仍有意義）', () => {
    renderWithSpec(SPEC_SAME_BAR, { labelScan: null, onChangeLabelScan: () => {} });
    expect((screen.getByTestId('ic-param-scan-k-toggle') as HTMLInputElement).disabled).toBe(false);
  });

  it('尚未選量法（labelSpec undefined）⇒ **不** disable（還沒決定就鎖會讓人以為壞了）', () => {
    renderWithSpec(undefined, { labelScan: null, onChangeLabelScan: () => {} });
    expect((screen.getByTestId('ic-param-scan-h-toggle') as HTMLInputElement).disabled).toBe(false);
  });

  it('🔴 切到當根時**清掉**既有的 h 上限（留著會送出一個不會被用到的值）', () => {
    const calls: (unknown)[] = [];
    const { rerender } = render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()}
        labelSpec={SPEC_HOLD as never} onChangeLabelSpec={() => {}}
        labelScan={{ horizon_bars_max: 5 }} onChangeLabelScan={(n) => calls.push(n)}
      />,
    );
    rerender(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()}
        labelSpec={SPEC_SAME_BAR as never} onChangeLabelSpec={() => {}}
        labelScan={{ horizon_bars_max: 5 }} onChangeLabelScan={(n) => calls.push(n)}
      />,
    );
    expect(calls.length).toBeGreaterThan(0);
    // 兩軸都空 ⇒ 整個鍵回 null（既有語意）
    expect(calls[calls.length - 1]).toBeNull();
  });
});

describe('Task 1.2 — 主結果與掃描矩陣之關係', () => {
  const scanDisclosure = {
    event_label_scan: {
      capability: 'available',
      reason: null,
      message: null,
      scan_done: 4,
      scan_total: 4,
      scan_results: [
        { k: 0, h: 1, capability: 'available', n_events: 10, reason: null },
        { k: 0, h: 2, capability: 'available', n_events: 10, reason: null },
        { k: 1, h: 1, capability: 'available', n_events: 9, reason: null },
        { k: 1, h: 2, capability: 'available', n_events: 9, reason: null },
      ],
    },
  };

  function renderScan(spec: unknown) {
    return render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={detailFixture()}
        labelSpec={spec as never} onChangeLabelSpec={() => {}}
        labelScan={{ decision_offset_bars_max: 1, horizon_bars_max: 2 }}
        onChangeLabelScan={() => {}}
        disclosure={scanDisclosure as never}
      />,
    );
  }

  it('說明行帶**當前**的 k 與 h（改 spec 之後跟著變，不是寫死字串）', () => {
    renderScan({ ...SPEC_HOLD, horizon_bars: 2, decision_offset_bars: 1 });
    const note = screen.getByTestId('ic-scan-primary-note');
    expect(note.textContent).toContain('k＝1');
    expect(note.textContent).toContain('h＝2');
    cleanup();
    renderScan({ ...SPEC_HOLD, horizon_bars: 1, decision_offset_bars: 0 });
    const note2 = screen.getByTestId('ic-scan-primary-note');
    expect(note2.textContent).toContain('k＝0');
    expect(note2.textContent).toContain('h＝1');
  });

  it('🔴 矩陣中**恰有一格**被標為主結果，且就是框裡那組 (k,h)', () => {
    renderScan({ ...SPEC_HOLD, horizon_bars: 2, decision_offset_bars: 1 });
    const primary = document.querySelectorAll('[data-primary="true"]');
    expect(primary.length).toBe(1);
    expect(primary[0].getAttribute('data-testid')).toBe('ic-scan-cell-1-2');
  });

  it('🔴 主結果落在掃描範圍外 ⇒ 零格標示，且說明行明講（不得靜默）', () => {
    renderScan({ ...SPEC_HOLD, horizon_bars: 9, decision_offset_bars: 5 });
    expect(document.querySelectorAll('[data-primary="true"]').length).toBe(0);
    expect(screen.getByTestId('ic-scan-primary-note').textContent).toContain('不在下表範圍內');
  });

  it('未開掃描 ⇒ 整區不 render（不得出現孤兒說明行）', () => {
    renderWithSpec(SPEC_HOLD, { labelScan: null, onChangeLabelScan: () => {} });
    expect(screen.queryByTestId('ic-scan-primary-note')).toBeNull();
  });
});

describe('Task 1.4 — 參數說明文案接線', () => {
  it('🔴 DOM 實際 render 的 doc 鍵集，等於 EVENT_PARAM_DOCS 扣掉 h_scan_inapplicable', async () => {
    const { EVENT_PARAM_DOC_KEYS } = await import('@/lib/eventParamDocs');
    // 🔴 本檔之 `detailFixture` 之 `records` 只有 `label_definition`（是為別條測試設計的），
    //    缺 symbol／timeframe／t0 ⇒ 隨機對照組那一區會顯示「無法產生」而不 render 三個參數。
    //    本條要驗的是**六個 doc 全部接上**，故在此補齊 records（不動共用 fixture）。
    const full = detailFixture();
    full.records = [
      { event_id: 'ETHUSDT:12h:1700000000000', symbol: 'ETHUSDT', timeframe: '12h',
        t0: 1700000000000, label_definition: { window: { horizon_bars: 3 } } },
      { event_id: 'ETHUSDT:12h:1700043200000', symbol: 'ETHUSDT', timeframe: '12h',
        t0: 1700043200000, label_definition: { window: { horizon_bars: 3 } } },
    ];
    render(
      <EventBatchDisclosurePanel
        importId="imp-1" detail={full}
        labelSpec={SPEC_HOLD as never} onChangeLabelSpec={() => {}}
        labelScan={null} onChangeLabelScan={() => {}}
      />,
    );
    const rendered = Array.from(document.querySelectorAll('[data-testid^="ic-param-doc-"]'))
      .map((el) => el.getAttribute('data-testid')!.replace('ic-param-doc-', ''));
    const expected = EVENT_PARAM_DOC_KEYS.filter((k) => k !== 'h_scan_inapplicable');
    expect(new Set(rendered)).toEqual(new Set(expected));
  });

  it('文字**逐字等於** EVENT_PARAM_DOCS（不是另寫一份）', async () => {
    const { EVENT_PARAM_DOCS } = await import('@/lib/eventParamDocs');
    renderWithSpec(SPEC_HOLD, { labelScan: null, onChangeLabelScan: () => {} });
    const el = screen.getByTestId('ic-param-doc-horizon_bars');
    expect(el.textContent).toBe(
      `${EVENT_PARAM_DOCS.horizon_bars.what} ${EVENT_PARAM_DOCS.horizon_bars.effect}`,
    );
  });
});
