/**
 * GAP-3 UX Task 4.1c 驗收（`--run eventExportNoIcDecay`；SPEC L2006–2023）。
 *
 * 釘死「換答案窗**不需要**重新匯出事件批」這個正確心智模型。
 *
 * 🔴 邊界②之判準是**否定式**（文案不得出現「重新匯出」作為換 h 之手段）——
 *    否定式斷言最容易假綠（元素根本沒 render 也會過），故每條都配一個**正向對照**。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SearchPage from '@/app/search/page';
import { useSearchStore } from '@/store/searchStore';
import type { CaseData, SearchResultData } from '@/lib/types';

const depthMock = vi.fn();

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, fetchLookaheadDepth: (...a: unknown[]) => depthMock(...a) };
});

const blobs: string[] = [];

function seed() {
  const base = {
    symbol: 'ETHUSDT', timeframe: '1h', positive_case: true, price_change: 3.2,
    ...Object.fromEntries([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((h) => [`future_${h}bar_return`, h / 100])),
  };
  useSearchStore.setState({
    currentResult: {
      cases: [
        { ...base, timestamp: '2024-01-01 00:00:00' },
        { ...base, timestamp: '2024-01-01 01:00:00', positive_case: false },
      ] as unknown as CaseData[],
      source_file_text: '[]', source_file_digest: 'a'.repeat(64),
    } as unknown as SearchResultData,
    isLoading: false, error: null,
  });
}

function selectOnly(keep: number[]) {
  for (const h of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) {
    const box = screen.getByTestId(`export-attached-h${h}`) as HTMLInputElement;
    if (box.checked !== keep.includes(h)) fireEvent.click(box);
  }
}

async function exportRecords(): Promise<Record<string, unknown>[]> {
  fireEvent.click(screen.getByTestId('export-gap3-events'));
  await waitFor(() => expect(blobs.length).toBeGreaterThan(0));
  return (JSON.parse(blobs[0]) as { records: Record<string, unknown>[] }).records;
}

beforeEach(() => {
  seed();
  depthMock.mockResolvedValue({ depth_by_timeframe: { '1h': 5 } });
  blobs.length = 0;
  const RealBlob = globalThis.Blob;
  vi.stubGlobal('Blob', class extends RealBlob {
    _text: string;
    constructor(parts: BlobPart[], opts?: BlobPropertyBag) {
      super(parts, opts);
      this._text = String(parts[0] ?? '');
    }
  });
  vi.stubGlobal('URL', {
    createObjectURL: (b: Blob & { _text?: string }) => { blobs.push(b._text ?? ''); return 'blob:x'; },
    revokeObjectURL: () => {},
  });
  vi.stubGlobal('alert', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  depthMock.mockReset();
  vi.unstubAllGlobals();
});

describe('Task 4.1c — 明文標示本批不提供 IC decay', () => {
  it('說明出現於匯出面板，且講的是「到 IC 分析頁改答案窗重跑」', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-no-ic-decay')).toBeTruthy());
    const text = screen.getByTestId('export-no-ic-decay').textContent ?? '';
    expect(text).toContain('IC decay');
    expect(text).toContain('ic_feed');
    expect(text).toContain('IC 分析頁');
  });

  it('🔴 邊界②：文案**不得**出現「重新匯出」作為換 h 之手段，也不得殘留「主答案窗」', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(screen.getByTestId('export-no-ic-decay')).toBeTruthy());
    const text = screen.getByTestId('export-no-ic-decay').textContent ?? '';
    // 正向對照：元素真的有內容（否則「空字串」也會讓下面兩條否定式斷言綠）
    expect(text.length).toBeGreaterThan(20);
    expect(text).not.toContain('重新匯出');
    expect(text).not.toContain('主答案窗');
  });

  it('🔴 邊界①：改附帶欄之選擇 ⇒ `window.horizon_bars` **不變**（附帶欄不是答案窗）', async () => {
    render(<SearchPage />);
    await waitFor(() => expect(depthMock).toHaveBeenCalled());

    selectOnly([1, 3, 7]);
    const a = (await exportRecords())[0];
    blobs.length = 0;
    selectOnly([2, 12]);
    const b = (await exportRecords())[0];

    const hb = (r: Record<string, unknown>) =>
      (r.label_definition as { window: { horizon_bars: number } }).window.horizon_bars;
    expect(hb(b)).toBe(hb(a));
    expect(hb(a)).toBe(5);                                   // ＝深度 5（不是附帶欄之 max 7 或 12）
    // 對照：附帶欄確實換過了（否則本條在比兩份一樣的東西）
    expect(Object.keys(a).filter((k) => k.startsWith('future_')))
      .not.toEqual(Object.keys(b).filter((k) => k.startsWith('future_')));
  });

  it('SPEC 仍載有 IC decay 之邊界說明（`grep -c "IC decay" >= 1`）', () => {
    const spec = readFileSync(
      resolve(__dirname, '../../../../docs/GAP3_EVENT_UX_SPEC.md'), 'utf-8',
    );
    expect((spec.match(/IC decay/g) ?? []).length).toBeGreaterThanOrEqual(1);
  });
});
