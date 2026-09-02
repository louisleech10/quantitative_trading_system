/**
 * GAP-3 UX **Task 7.4** 驗收（`--run eventIcDecayDisclosure`；SPEC L2993–2996）。
 *
 * 「條件 IC decay 之邊界揭露」——與 Task 4.1c **同一文案來源，不得各寫一份**。
 * 🔴 邊界②之機械判準：文中每一次出現「重新匯出」，其**緊鄰前綴必須是「不需」**
 *    ——直接禁用該詞不可行（SPEC 要求說出「不需重新匯出事件批」），
 *    而只用 `not.toContain('重新匯出')` 會把正確文案判成錯的。
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { declareFromPreview, previewOf } from '@/test/lookaheadDeclarationTestUtils';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import { EVENT_IC_DECAY_DISCLOSURE } from '@/lib/eventFieldFormatters';
import { buildEventContractRecords, type EventExportOptions } from '@/lib/eventExport';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDeclarationPreviewColumns: (...a: unknown[]) => depthMock(...a) };
});

const CASE_ROW = {
  symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00',
  positive_case: true, price_change: 3.2,
  future_1bar_return: 0.01, future_3bar_return: 0.02, future_7bar_return: 0.03,
} as unknown as CaseData;

function baseOpts(over: Partial<EventExportOptions> = {}): EventExportOptions {
  return {
    timeframe: '1h',
    conditions: [{ parameter: 'price_change', operator: '>=', value: 3 }],
    priceChangeMethod: 'close_to_close',
    lookaheadBarsDeclared: { '1h': 2 },
    sourceFileText: '[]',
    sourceFileDigest: 'a'.repeat(64),
    ...over,
  };
}

beforeEach(() => {
  useSearchStore.setState({
    currentResult: {
      cases: [CASE_ROW], source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
  depthMock.mockResolvedValue(previewOf({ '1h': 2 }));
  vi.stubGlobal('alert', vi.fn());
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 7.4 — 條件 IC decay 之邊界揭露', () => {
  it('說明現於匯出面板，且**逐字**等於同一 exported 常數（4.1c 與 7.4 同一份）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-no-ic-decay')).toBeTruthy());
    expect(screen.getByTestId('export-no-ic-decay').textContent).toBe(EVENT_IC_DECAY_DISCLOSURE);
  });

  it('文案講齊四件事：decay 曲線非本批交付／future_* 不進 ic_feed／到 IC 分析頁改答案窗／之後才會做', () => {
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('decay');
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('非本批交付');
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('不進入 ic_feed');
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('IC 分析頁改答案窗');
    // 🔴 第四件事＝「這件事還沒做、之後會做」。**原本這一條斷言的是 `toContain('GAP-6')`**，
    //    也就是硬性要求畫面上出現我們的施工票號——那把錯的性質釘死了
    //    （2026-09-02 使用者：「以後使用者哪知道什麼是 GAP3？」）。
    //    這不是放寬守衛：要講的事一件沒少，只是改成守「有沒有講到」而不是「有沒有寫票號」。
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('之後');
  });

  it('🔴 文案**不得**含施工票號（全域閘見 `lib/noTicketIdInUi.test.ts`，此處再釘一次）', () => {
    expect(EVENT_IC_DECAY_DISCLOSURE).not.toMatch(/\bGAP[-_]?\d\b/);
  });

  it('邊界② 文案**不得**把重新匯出講成換答案窗之手段，且仍要講明「不必再匯出一次」', () => {
    // 🔴 沿用 4.1c 既有之**更嚴**判準（`eventExportNoIcDecay.test.tsx`）：四字一次都不得出現。
    //    不為了讓新文案過關而放寬既有斷言——那是本 epic 反覆付過代價的形態。
    expect(EVENT_IC_DECAY_DISCLOSURE).not.toContain('重新匯出');
    // 正向對照：語意沒有因為避開字面而消失
    expect(EVENT_IC_DECAY_DISCLOSURE).toContain('不必再匯出一次');
  });

  it('邊界① 選附帶欄 `[1,3,7]` ⇒ `label_definition.window.horizon_bars` **不變**', async () => {
    const one = await buildEventContractRecords([CASE_ROW], baseOpts({ attachedHorizons: [1] }));
    const many = await buildEventContractRecords([CASE_ROW], baseOpts({ attachedHorizons: [1, 3, 7] }));
    const h = (r: unknown) => ((r as { label_definition: { window: { horizon_bars: number } } })
      .label_definition.window.horizon_bars);
    expect(h(many.records[0])).toBe(h(one.records[0]));
    // 正向對照：附帶欄真的變多了（否則「不變」是因為根本沒差別）
    expect(many.attached_horizons).toEqual([1, 3, 7]);
    expect(Object.keys(many.records[0] as object)).toContain('future_7bar_return');
    expect(Object.keys(one.records[0] as object)).not.toContain('future_7bar_return');
  });
});
