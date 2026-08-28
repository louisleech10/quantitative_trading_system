/**
 * GAP-3 UX **Task 7.3** 驗收（`--run eventExportDisclosure`；SPEC L2971–2975 之①②③）。
 *
 * 7.3 **取代** Task 4.1b 之獨立實作（後者為其真子集）⇒ 本檔另釘住覆蓋風險所要求之
 * 「移除 4.1b 獨立實作前須逐項比對兩邊揭露項集合並斷言 **4.1b ⊆ 7.3**」。
 * 🔴 4.1b 之**執行期**驗收（`eventExportDisclosureLegacy.test.tsx`）刻意保留且仍須全綠
 *    ——那是「⊆」在真實 DOM 上的證明，比集合字面更難造假。
 */
import fs from 'node:fs';
import path from 'node:path';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import {
  EVENT_FIELD_FORMATTERS, IC_BATCH_FACT_FIELDS, SEARCH_DISCLOSURE_FIELDS, searchDisclosureLines,
} from '@/lib/eventFieldFormatters';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();
const blobs: string[] = [];

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
});

const CASE_ROW = {
  symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00',
  positive_case: true, price_change: 3.2, future_1bar_return: 0.01,
} as unknown as CaseData;

beforeEach(() => {
  blobs.length = 0;
  useSearchStore.setState({
    currentResult: {
      cases: [CASE_ROW], source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
  depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 2 } });
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
  vi.stubGlobal('URL', {
    createObjectURL: (b: Blob) => {
      void (b as Blob & { text?: () => Promise<string> });
      return 'blob:x';
    },
    revokeObjectURL: () => {},
  });
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 7.3 ① — 揭露七項且全部由實際設定導出', () => {
  it('七項欄集皆有對應之顯示節點（含 4.1b 原本沒有的三項）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());
    expect(screen.getByTestId('export-disclosure-scenario')).toBeTruthy();
    expect(screen.getByTestId('export-disclosure-control-kind')).toBeTruthy();
    expect(screen.getByTestId('export-disclosure-entry-price-semantic')).toBeTruthy();
    expect(screen.getByTestId('export-disclosure-label-return-mode')).toBeTruthy();
    expect(screen.getByTestId('export-disclosure-decision-offset-bars')).toBeTruthy();
    expect(screen.getByTestId('export-disclosure-purge-1h')).toBeTruthy();
  });

  it('① 改任一維度 ⇒ 顯示字串隨之改變（前後 `!==`）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());
    const before = screen.getByTestId('export-disclosure-control-kind').textContent;
    fireEvent.change(screen.getByTestId('event-dim-control_kind'), { target: { value: 'user_labeled_other' } });
    expect(screen.getByTestId('export-disclosure-control-kind').textContent).not.toBe(before);
  });

  it('② 顯示值逐字等於共用 formatter 之輸出（本頁不另寫一份文案）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());
    fireEvent.change(screen.getByTestId('event-dim-control_kind'), { target: { value: 'platform_same_trigger_rule' } });
    expect(screen.getByTestId('export-disclosure-control-kind').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.control_kind('platform_same_trigger_rule'));
    expect(screen.getByTestId('export-disclosure-scenario').textContent)
      .toBe(EVENT_FIELD_FORMATTERS.scenario('C'));
  });
});

describe('Task 7.3 ③ — 兩頁共用同一 registry，欄集各自選取', () => {
  const read = (p: string) => fs.readFileSync(path.resolve(__dirname, p), 'utf8');

  it('③(a) 兩頁皆自 `@/lib/eventFieldFormatters` 取用 `EVENT_FIELD_FORMATTERS`（同一模組＝同一參考）', () => {
    const pages = {
      '/search': read('./page.tsx'),
      '/ic-analysis': read('../../components/ic-analysis/EventBatchDisclosurePanel.tsx'),
    };
    for (const [name, src] of Object.entries(pages)) {
      // 🔴 R3 群集 B 後：`/search` 改為經**同一模組**之 `searchDisclosureLines` 取用 registry
      //    （`/ic-analysis` 仍直接用 `EVENT_FIELD_FORMATTERS`）⇒ 判準改為「來自同一模組」，
      //    而不是「一定要 import 那個特定符號」。
      expect(src, `${name} 未自共用模組取用 registry`).toMatch(
        /import\s*\{[\s\S]*?\}\s*from\s*'@\/lib\/eventFieldFormatters'/,
      );
      // 🔴 禁止「自己再寫一份 formatter」：本頁不得出現 `const EVENT_FIELD_FORMATTERS =`
      expect(src, `${name} 自己宣告了第二份 registry`).not.toMatch(/const\s+EVENT_FIELD_FORMATTERS\s*=/);
    }
    // 🔴 執行期補強（原始碼正則之誠實邊界，見 brief「我沒查的」第五列）：
    //    `/search` 之揭露文字**逐字**等於 registry 之輸出，由本檔 ② 驗；
    //    IC 頁同樣由 `icEventBatchDisclosure` ① 驗。兩者合起來才排除「re-export 再包一層」。
    expect(typeof EVENT_FIELD_FORMATTERS.scenario).toBe('function');
  });

  it('🔴 R3 群集 B：DOM 之揭露節點集合**由常數導出**（拿掉一欄 ⇒ 該節點消失）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-disclosure-depth-1h')).toBeTruthy());
    // 實際 render 出來的 testid 集合
    const actual = new Set(
      Array.from(screen.getByTestId('export-disclosure').querySelectorAll('[data-testid]'))
        .map((el) => el.getAttribute('data-testid')!),
    );
    // 期望值由**常數**導出（不是人工清單）：一欄至少貢獻一個節點
    const expected = new Set(
      SEARCH_DISCLOSURE_FIELDS.flatMap((f) => searchDisclosureLines(f, {
        dims: {
          scenario: 'C', control_kind: 'user_labeled_same_trigger',
          entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close',
          decision_offset_bars: 0,
        },
        depthByTimeframe: { '1h': 2 },
        referencedColumns: [],
      })).map((l) => l.testid),
    );
    expect(actual).toEqual(expected);
    // 正向對照：欄集真的有七欄，且每欄都在 DOM 裡留下痕跡（不是兩邊都空而相等）
    expect(SEARCH_DISCLOSURE_FIELDS.length).toBe(7);
    expect(actual.size).toBeGreaterThanOrEqual(SEARCH_DISCLOSURE_FIELDS.length);
  });

  it('🔴 R3 群集 B：欄集加了沒接線的欄 ⇒ **fail-loud**，不靜默少顯示一項', () => {
    expect(() => searchDisclosureLines(
      'direction' as (typeof SEARCH_DISCLOSURE_FIELDS)[number],
      {
        dims: {
          scenario: 'C', control_kind: 'user_labeled_same_trigger',
          entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close',
          decision_offset_bars: 0,
        },
        depthByTimeframe: {}, referencedColumns: [],
      },
    )).toThrow(/尚未接線/);
  });

  it('③(b) 兩頁之欄集**不相等**，且交集非空（共用的是 registry，不是欄集）', () => {
    expect(new Set(SEARCH_DISCLOSURE_FIELDS)).not.toEqual(new Set(IC_BATCH_FACT_FIELDS));
    expect(SEARCH_DISCLOSURE_FIELDS.filter((f) => IC_BATCH_FACT_FIELDS.includes(f)).length)
      .toBeGreaterThan(0);
  });

  it('🔴 覆蓋風險：4.1b 之揭露項集合 ⊆ 7.3 之欄集（取代者須為嚴格超集）', () => {
    // 4.1b 明列之四項（SPEC L1979–2005）：scenario／lookahead 深度／purge 下界／control_kind
    const legacy = ['scenario', 'control_kind', 'lookahead_depth', 'purge_bars'] as const;
    for (const f of legacy) expect(SEARCH_DISCLOSURE_FIELDS).toContain(f);
    expect(SEARCH_DISCLOSURE_FIELDS.length).toBeGreaterThan(legacy.length);
  });
});
