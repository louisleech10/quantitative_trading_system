/**
 * GAP-3 B5.2（W9）：事件模式入口——EventImportPicker 只在 event 模式出現；未匯入任何事件批 ⇒ empty state；
 * 🔴 Task 7.7 ⑦ 起：選批**只**交出 importId，映射由後端依 receipt 產生。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EventImportPicker from '@/components/ic-analysis/EventImportPicker';

import type { EventImportSummary } from '@/lib/types';

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return {
    ...actual,
    listEventImports: vi.fn(async () => ({ total: 0, imports: [] })),
    getEventImport: vi.fn(async (id: string) => ({
      summary: { import_id: id } as EventImportSummary,
      records: [{ t0: 1704067200000 }, { t0: 1704110400000 }, { t0: 'bad' }],
    })),
  };
});

afterEach(() => cleanup());

const IMPORTS: EventImportSummary[] = [
  { import_id: 'imp-1', source_name: 'a.csv', upload_sha256: 'x', imported_at: '2026-08-21T00:00:00Z', n_events: 2, symbols: ['ETHUSDT'], timeframes: ['12h'], direction: 'long', scenario: 'C' },
];

describe('GAP-3 事件模式入口', () => {
  it('未匯入任何事件批 ⇒ empty state（不渲染下拉）', async () => {
    render(<EventImportPicker onPick={() => undefined} />);
    await waitFor(() => expect(screen.getByTestId('event-import-picker-empty')).toBeTruthy());
    expect(screen.queryByTestId('event-import-select')).toBeNull();
  });

  it('🔴 **Task 7.7 ⑦ 改寫**：選批後 onPick **只**收到 importId，不再收時間戳', async () => {
    // 歷史：本條原本斷言 `onPick('imp-1', [1704067200, 1704110400])`——
    // 也就是前端把整批 records 抓下來、`t0 ÷ 1000` 當成 IC 的 event_timestamps。
    // 那個映射用的是**原始 t0**，而正確的 feature sample key 是 receipt 之 decision_at_ms；
    // `decision_offset_bars > 0` 時兩者不同，差額會把特徵取樣點推到**決策時點之後**（洩漏）。
    // 保留本條為**回歸**：任何形式的「前端自算時間戳」都不得回來。
    const onPick = vi.fn();
    render(<EventImportPicker imports={IMPORTS} onPick={onPick} />);
    const select = screen.getByTestId('event-import-select') as HTMLSelectElement;
    expect(select.options.length).toBe(2);
    fireEvent.change(select, { target: { value: 'imp-1' } });
    await waitFor(() => expect(onPick).toHaveBeenCalled());
    expect(onPick).toHaveBeenCalledWith('imp-1');
    expect(onPick.mock.calls[0]).toHaveLength(1);  // 🔴 第二個引數不得復活
  });

  it('🔴 `eventT0MsToIcTimestamps` 已自 `api.ts` **移除**（Task 7.7 ⑦），不得復活', async () => {
    const api = await import('@/lib/api');
    expect('eventT0MsToIcTimestamps' in api).toBe(false);
    // 連改名復活都擋：任何把 t0 直接換算成 IC 時間戳的匯出都不該存在
    const src = readFileSync(resolve(__dirname, '../../lib/api.ts'), 'utf-8');
    expect(src.includes('export function eventT0MsToIcTimestamps')).toBe(false);
  });

  it('ICAnalysisConfig 型別含 event_import_id（頁面接線：只在 event 模式掛 picker）', () => {
    const src = readFileSync(resolve(__dirname, 'ICConfigPanel.tsx'), 'utf-8');
    expect(src.includes("config.mode === 'event'")).toBe(true);
    expect(src.includes('<EventImportPicker')).toBe(true);
    const page = readFileSync(resolve(__dirname, '../../app/ic-analysis/page.tsx'), 'utf-8');
    expect(page.includes("config.mode === 'event' && (")).toBe(true);
    expect(page.includes('<EventTablesPanel')).toBe(true);
    // Task 4.2：面板要真的收到使用者選的 horizon 集合（此前恆不傳 ⇒ 後端永遠用預設 [1,2,4]）
    expect(page.includes('horizons={config.horizons}')).toBe(true);
  });

  // 🔴 **`COMPOSER-R1-P2-01` 指出並已改**：本條原本是**原始碼形狀**斷言
  //    （`readFileSync` ＋ `toContain('event_timestamps:')`），與 §6.2「不要用原始碼形狀
  //    證明執行期性質」直接牴觸——`grep` 到那個字串不代表它真的被序列化進 payload。
  //    執行期的等價驗收已移到 `frontend/src/hooks/icEventAnalysisRequest.test.ts`
  //    （攔真的 HTTP body，含 legacy 路徑之 over 向）。本處不再保留第二份形狀斷言。
});
