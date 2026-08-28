/**
 * GAP-3 UX **Task 7.0b ⑫** 驗收（`--run icEventAnalysisRequest`；SPEC L2775–2777）＋
 * **Task 7.7 ⑦**（前端不再自算時間戳）。
 *
 * 🔴 **本檔攔的是真的送出去的那個 HTTP body**，不是原始碼形狀。
 *    §6.2 已把「用原始碼形狀證明執行期性質」列為本 epic 五度出現的同一病
 *    ——`grep` 到 `event_import_id:` 這個字串，不代表它真的被序列化進 payload
 *    （條件分支、`undefined` 被 `JSON.stringify` 丟掉、鍵名拼錯，三種都會讓 grep 綠而實際沒送）。
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import type { ICAnalysisConfig } from '@/lib/types';

const sent: { url: string; body: Record<string, unknown> }[] = [];

function baseConfig(over: Partial<ICAnalysisConfig> = {}): ICAnalysisConfig {
  return {
    ...useICAnalysisStore.getState().config,
    symbol: 'ETHUSDT',
    timeframe: '12h',
    config_hash: 'abc123',
    mode: 'event',
    ...over,
  } as ICAnalysisConfig;
}

beforeEach(() => {
  sent.length = 0;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (String(url).endsWith('/analyze')) {
      sent.push({ url: String(url), body: JSON.parse(String(init?.body ?? '{}')) });
      return new Response(JSON.stringify({ task_id: 't1', status: 'running' }), {
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
  await act(async () => {
    await result.current.startAnalysis(config);
  });
  expect(sent).toHaveLength(1);
  return sent[0].body;
}

describe('Task 7.0b ⑫ — 選批後之 /analyze payload', () => {
  it('① 選了事件批 ⇒ payload **含** `event_import_id` 與 `event_label_spec`', async () => {
    const body = await startWith(baseConfig({ event_import_id: 'imp-1' }));
    expect(body.event_import_id).toBe('imp-1');
    expect(body.event_label_spec).toBeTruthy();
  });

  it('② 只給 import_id ⇒ `event_label_spec.horizon_bars === 1`（**字面常數**，非匯出之深度欄值）', async () => {
    // 🔴 既有批之 `label_definition.window.horizon_bars` 殘值為 3。
    //    拿它種子化＝靜默給錯預設答案窗——該欄語意是 D-7 深度宣告，分析層禁止讀成答案窗。
    const body = await startWith(baseConfig({ event_import_id: 'imp-1' }));
    expect((body.event_label_spec as { horizon_bars: number }).horizon_bars).toBe(1);
    expect((body.event_label_spec as { horizon_bars: number }).horizon_bars).not.toBe(3);
  });

  it('③ 選了事件批 ⇒ payload **不得**同時帶 `event_timestamps`（後端定死互斥 ⇒ 422）', async () => {
    // 🔴 連「使用者先用 legacy 路徑選過、殘留在 config 裡」這種情況都要擋：
    //    這裡刻意把舊時間戳留在 config 上，payload 仍不得帶出去。
    const body = await startWith(baseConfig({
      event_import_id: 'imp-1', event_timestamps: [1704067200],
    }));
    expect(body.event_import_id).toBe('imp-1');
    expect('event_timestamps' in body).toBe(false);
  });

  it('④ 🔴 **over 向**：legacy 路徑（只有 `event_timestamps`、沒有 import_id）**行為不變**', async () => {
    // 這條是「新增一條路徑、不改既有語意」的證據。少了它，上面第 ③ 條可以被
    // 一個「永遠不送 event_timestamps」的實作騙過去。
    const body = await startWith(baseConfig({ event_timestamps: [1704067200, 1704110400] }));
    expect(body.event_timestamps).toEqual([1704067200, 1704110400]);
    expect(body.event_import_id).toBeUndefined();
    expect(body.event_label_spec).toBeUndefined();
  });

  it('⑤ 🔴 **over 向**：非事件模式 ⇒ 三個事件欄一個都不送', async () => {
    const body = await startWith(baseConfig({
      mode: 'global', event_import_id: 'imp-1', event_timestamps: [1704067200],
    }));
    expect(body.event_import_id).toBeUndefined();
    expect('event_timestamps' in body).toBe(false);
    expect(body.event_label_spec).toBeUndefined();
  });
});
