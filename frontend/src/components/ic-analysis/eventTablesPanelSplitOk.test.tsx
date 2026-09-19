/**
 * SPLITUNIFY `Task 10.6` 驗收：事件掃描請求之三個投影欄 ＋ 投影路徑之畫面揭露。
 *
 * 🔴 **本檔攔的是真的送出去的那個 HTTP body**，不是原始碼形狀（同
 *    `src/hooks/icEventAnalysisRequest.test.ts` 檔頭之理由：`grep` 到鍵名不代表它被序列化出去——
 *    條件分支、`undefined` 被 `JSON.stringify` 丟掉、鍵名拼錯，三種都會讓 grep 綠而實際沒送）。
 *
 * 🔴 **逐鍵相等那條不是自證**：IC 側的 payload 是**真的跑 `useICAnalysis().startAnalysis`**
 *    抓下來的，不是在測試裡重算一份期望值。兩端各自走自己的程式碼路徑，測試只比對結果——
 *    若只比「掃描端 payload 等於我在測試裡寫的 spec」，那條斷言在兩端漂移時不會紅（`M-SU-R5-24`）。
 *
 * 對照之 mutation（`docs/SPLITUNIFY_TODO.md` §D-10）：
 *   `M-SU-R5-24` 前端不帶 `event_label_spec` ⇒ 逐鍵相等那條轉紅。
 */
import { act, cleanup, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EventTablesPanel from '@/components/ic-analysis/EventTablesPanel';
import { buildEventScanRequest } from '@/lib/api';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import {
  REASON_HOLDOUT_DISABLED,
  REASON_HOLDOUT_INSUFFICIENT_ROWS,
  REASON_NO_UNIVERSE,
  REASON_UNVERIFIABLE_LOOKAHEAD,
  splitCapabilityView,
} from '@/lib/splitCapability';
import type { EventAnalyzeResponse, ICAnalysisConfig } from '@/lib/types';

/** 兩條路徑的 URL 都以 `/analyze` 結尾，故一律以 `/case/events/` 區分（IC＝`/api/v1/ic/analyze`）。 */
const icSent: Record<string, unknown>[] = [];
const scanSent: Record<string, unknown>[] = [];

function baseConfig(over: Partial<ICAnalysisConfig> = {}): ICAnalysisConfig {
  return {
    ...useICAnalysisStore.getState().config,
    symbol: 'ETHUSDT',
    timeframe: '1h',
    config_hash: '5ea074390e98405cb83d602fe7b7fb00',
    mode: 'event',
    event_import_id: 'imp-1',
    ...over,
  } as ICAnalysisConfig;
}

/** 投影成功（`split: ok`）之回應：四個新欄齊備。 */
function projectedResponse(over: Partial<EventAnalyzeResponse> = {}): EventAnalyzeResponse {
  return {
    import_id: 'imp-1',
    summary: {
      n_input: 144,
      n_aligned: 132,
      n_align_failures: 0,
      n_train: 88,
      n_test: 22,
      n_purged: 0,
      split: {
        discarded_rows_by_feature_tf: {},
        insufficient_events_in_test: [],
      },
    },
    align_failures: [],
    capability: { split: 'ok', reason: null },
    embargo: { applied_ms: null, source: 'canonical_holdout_rows' },
    tables: {
      event_forward_return_table: {
        capability_status: 'ok',
        horizons: [1],
        primary_macro: { '1': { mean: 0.01, n_symbols: 1 } },
        sensitivity_micro: { '1': { mean: 0.01, median: 0.01, win_rate: 0.5, n: 22, n_effective: 22 } },
      },
      binary_discrimination_table: { capability_status: 'not_computed', reason: 'no_model_scores_in_event_pipeline' },
    },
    event_timestamps: [1704067200000],
    split_unify: {
      n_test: 22,
      split_authority: 'canonical_holdout',
      boundary_hash: 'ab12cd34ef56aa99',
      per_symbol_counts: { ETHUSDT: 22 },
      reason: null,
    },
    period_alignment: {
      dropped_in_alignment: { count: 12, ids: ['ETHUSDT:12h:1'] },
      dropped_by_coverage: { count: 22, ids: ['ETHUSDT:12h:2'] },
      dropped_outside_post_trim_index: { count: 0, ids: [] },
      post_trim_index_bounds_ms: [1704067200000, 1735689600000],
    },
    excluded_by_symbol: { BCHUSDT: { count: 3, event_ids: ['BCHUSDT:12h:9'] } },
    event_label_spec: {
      spec: { horizon_bars: 6, entry_price_semantic: 'trigger_open', label_return_mode: 'open_to_horizon_close', decision_offset_bars: 1 },
      seed_note: 'derived_from_declaration_depth',
    },
    ...over,
  } as unknown as EventAnalyzeResponse;
}

beforeEach(() => {
  icSent.length = 0;
  scanSent.length = 0;
  vi.stubGlobal('WebSocket', class {
    onopen: (() => void) | null = null;
    onmessage: ((e: unknown) => void) | null = null;
    onerror: (() => void) | null = null;
    onclose: (() => void) | null = null;
    close() {}
  });
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const u = String(url);
    const body = JSON.parse(String(init?.body ?? '{}'));
    if (u.includes('/case/events/') && u.endsWith('/analyze')) {
      scanSent.push(body);
      return new Response(JSON.stringify(projectedResponse()), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    }
    if (u.endsWith('/analyze')) {
      icSent.push(body);
      return new Response(JSON.stringify({ task_id: 't1', status: 'running' }), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    }
    return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** 真的跑 IC 送出路徑，回傳它實際 POST 出去的 body。 */
async function icPayload(config: ICAnalysisConfig): Promise<Record<string, unknown>> {
  const { result } = renderHook(() => useICAnalysis());
  await act(async () => {
    await result.current.startAnalysis(config);
  });
  expect(icSent).toHaveLength(1);
  return icSent[0];
}

/** 真的掛載面板，回傳事件掃描端實際 POST 出去的 body。 */
async function scanPayload(config: ICAnalysisConfig): Promise<Record<string, unknown>> {
  render(
    <EventTablesPanel
      importId={config.event_import_id}
      horizons={config.horizons}
      scanRequest={buildEventScanRequest(config)}
    />,
  );
  await waitFor(() => expect(scanSent).toHaveLength(1));
  return scanSent[0];
}

describe('Task 10.6 — 事件掃描請求之三個投影欄', () => {
  it('選了 run ⇒ payload 帶 `feature_run` 三欄（逐字等於已選 run，前端不 auto-discover）', async () => {
    const config = baseConfig();
    const body = await scanPayload(config);
    expect(body.feature_run).toEqual({
      symbol: 'ETHUSDT',
      timeframe: '1h',
      config_hash: '5ea074390e98405cb83d602fe7b7fb00',
    });
  });

  it('選了 run ⇒ payload 帶 `config_override`，且與 IC 分析請求之同名欄逐鍵相等', async () => {
    const config = baseConfig();
    const scan = await scanPayload(config);
    const ic = await icPayload(config);
    // IC 側另疊 `feature_tiers`（只在 effectiveConfig 有值時）——比對 `buildConfigOverride`
    // 共同產出的三個鍵，證明兩端吃的是同一份門檻與 horizon，而不是各自重算。
    const icOverride = ic.config_override as Record<string, unknown>;
    const scanOverride = scan.config_override as Record<string, unknown>;
    expect(scanOverride.thresholds).toEqual(icOverride.thresholds);
    expect(scanOverride.redundancy).toEqual(icOverride.redundancy);
    expect(scanOverride.labels).toEqual(icOverride.labels);
  });

  it('🔴 邊界④：使用者**未改**標籤參數 ⇒ 兩端皆**不帶** `event_label_spec`（逐鍵相等＝兩邊都沒有這個鍵）', async () => {
    const config = baseConfig({ event_label_spec: undefined });
    const scan = await scanPayload(config);
    const ic = await icPayload(config);
    expect('event_label_spec' in scan).toBe(false);
    expect('event_label_spec' in ic).toBe(false);
  });

  it('🔴 邊界④ over 向：使用者**改了**標籤參數 ⇒ 兩端送出之 `event_label_spec` 逐鍵相等（`M-SU-R5-24`）', async () => {
    const spec = {
      horizon_bars: 6,
      entry_price_semantic: 'trigger_open',
      label_return_mode: 'open_to_horizon_close',
      decision_offset_bars: 1,
    };
    const config = baseConfig({ event_label_spec: spec });
    const scan = await scanPayload(config);
    const ic = await icPayload(config);
    expect(scan.event_label_spec).toEqual(ic.event_label_spec);
    expect(scan.event_label_spec).toEqual(spec);
    expect(Object.keys(scan.event_label_spec as object).sort())
      .toEqual(Object.keys(ic.event_label_spec as object).sort());
  });

  it('🔴 邊界①：未選 run（`config_hash` 空）⇒ **不送** `feature_run`，連帶不送 `config_override`', async () => {
    const config = baseConfig({ config_hash: '' });
    const body = await scanPayload(config);
    expect('feature_run' in body).toBe(false);
    expect('config_override' in body).toBe(false);
  });

  it('🔴 邊界①：run 三欄只給兩欄 ⇒ 整個鍵省略（不得送半套讓後端 422）', async () => {
    const body = await scanPayload(baseConfig({ timeframe: undefined }));
    expect('feature_run' in body).toBe(false);
  });
});

describe('Task 10.6／R5-C5 — 投影路徑之畫面揭露', () => {
  it('`split: ok` ⇒ 顯示驗證段事件數與切分來源', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse()} />);
    const line = screen.getByTestId('event-split-unify');
    expect(line.textContent ?? '').toContain('22');
    expect(line.textContent ?? '').toContain('canonical_holdout');
  });

  it('🔴 `n_test` 為 `null` ⇒ **不顯示任何計數**，只顯示具名原因（`0` 與「沒切」是兩件事）', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse({
      capability: { split: 'unavailable', reason: REASON_HOLDOUT_DISABLED },
      summary: { n_input: 144, n_aligned: 132, n_align_failures: 0, split: null },
      split_unify: { n_test: null, split_authority: null, boundary_hash: null, per_symbol_counts: null, reason: REASON_HOLDOUT_DISABLED },
    })} />);
    const line = screen.getByTestId('event-split-unify');
    expect(line.getAttribute('data-split-unify-reason')).toBe(REASON_HOLDOUT_DISABLED);
    expect(line.textContent ?? '').toContain('未執行');
    // 🔴 兩層：①不得出現計數欄位之字面（改成從 `summary` 撈數字來補也會被這條抓到）；
    //    ②整行不得出現任何數字（`null` 印成字串也算違規，但它不是數字，故兩條都要）。
    expect(line.textContent ?? '').not.toContain('驗證段事件數');
    expect(line.textContent ?? '').not.toMatch(/\d/);
  });

  it('被排除事件三段與他標的排除皆顯示（計數取自後端，前端不重算）', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse()} />);
    const pa = screen.getByTestId('event-period-alignment').textContent ?? '';
    expect(pa).toContain('12');
    expect(pa).toContain('22');
    expect(screen.getByTestId('event-excluded-by-symbol').textContent ?? '').toContain('BCHUSDT');
  });

  it('顯示**解析後實際使用**之標籤參數與其預設來源說明', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse()} />);
    const t = screen.getByTestId('event-label-spec-used').textContent ?? '';
    expect(t).toContain('horizon_bars=6');
    expect(t).toContain('decision_offset_bars=1');
    expect(t).toContain('derived_from_declaration_depth');
  });

  it('🔴 邊界②：`discarded_rows_by_feature_tf` 為空 ⇒ **不顯示該列**', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse()} />);
    expect(screen.queryByTestId('event-discarded-rows')).toBeNull();
  });

  it('🔴 邊界② over 向：有丟棄列 ⇒ 顯示（證明上一條不是「一律不顯示」）', () => {
    render(<EventTablesPanel importId="imp-1" data={projectedResponse({
      summary: {
        n_input: 144, n_aligned: 132, n_align_failures: 0, n_train: 88, n_test: 22, n_purged: 0,
        split: { discarded_rows_by_feature_tf: { '1h': 7 }, insufficient_events_in_test: ['ETHUSDT'] },
      },
    })} />);
    expect(screen.getByTestId('event-discarded-rows').textContent ?? '').toContain('1h 7');
    expect(screen.getByTestId('event-insufficient-test').textContent ?? '').toContain('ETHUSDT');
  });

  it('event-study-only（四欄整個不存在）⇒ 揭露區**不渲染**（不是渲染成 0）', () => {
    const noProjection = {
      import_id: 'imp-1',
      summary: { n_input: 4, n_aligned: 4, n_align_failures: 0, split: null, execution_mode: 'event_study_only' },
      align_failures: [],
      capability: { split: 'unavailable', reason: REASON_NO_UNIVERSE },
      tables: {
        event_forward_return_table: { capability_status: 'not_computed', reason: 'no_split' },
        binary_discrimination_table: { capability_status: 'not_computed', reason: 'no_model_scores_in_event_pipeline' },
      },
      event_timestamps: [],
    } as unknown as EventAnalyzeResponse;
    render(<EventTablesPanel importId="imp-1" data={noProjection} />);
    expect(screen.queryByTestId('event-projection-disclosure')).toBeNull();
  });
});

describe('Task 10.6 邊界③ — 四條 reason 之文案兩兩可分辨', () => {
  it('四條文案互不相同且皆非空', () => {
    const reasons = [
      REASON_NO_UNIVERSE,
      REASON_UNVERIFIABLE_LOOKAHEAD,
      REASON_HOLDOUT_DISABLED,
      REASON_HOLDOUT_INSUFFICIENT_ROWS,
    ];
    const texts = reasons.map((r) => splitCapabilityView({ split: 'unavailable', reason: r }).text);
    texts.forEach((t) => expect(t.length).toBeGreaterThan(0));
    expect(new Set(texts).size).toBe(4);
  });

  it('🔴 「拿不到 universe」與「拿得到但這次不切」必須讓使用者分得出誰能自己修', () => {
    const noUniverse = splitCapabilityView({ split: 'unavailable', reason: REASON_NO_UNIVERSE }).text;
    const disabled = splitCapabilityView({ split: 'unavailable', reason: REASON_HOLDOUT_DISABLED }).text;
    const insufficient = splitCapabilityView({ split: 'unavailable', reason: REASON_HOLDOUT_INSUFFICIENT_ROWS }).text;
    expect(noUniverse).toContain('取不到');
    expect(disabled).toContain('關閉');
    expect(insufficient).toContain('列數不足');
  });
});
