/**
 * GAP-3 B5.2（W9）：事件模式入口——EventImportPicker 只在 event 模式出現；未匯入任何事件批 ⇒ empty state；
 * 選批 ⇒ 以 t0(ms)→秒 帶入 event_timestamps。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EventImportPicker from '@/components/ic-analysis/EventImportPicker';
import { eventT0MsToIcTimestamps } from '@/lib/api';
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

  it('有事件批 ⇒ 下拉可選；選批後 onPick 收到 ms→秒 timestamps（壞值剔除）', async () => {
    const onPick = vi.fn();
    render(<EventImportPicker imports={IMPORTS} onPick={onPick} />);
    const select = screen.getByTestId('event-import-select') as HTMLSelectElement;
    expect(select.options.length).toBe(2);
    fireEvent.change(select, { target: { value: 'imp-1' } });
    await waitFor(() => expect(onPick).toHaveBeenCalled());
    expect(onPick).toHaveBeenCalledWith('imp-1', [1704067200, 1704110400]);
  });

  it('t0 橋接：ms ÷1000 取整、非數值剔除', () => {
    expect(eventT0MsToIcTimestamps([{ t0: 1704067200000 }, { t0: '1704110400000' }, { t0: null }, { t0: -5 }])).toEqual([1704067200, 1704110400]);
  });

  it('ICAnalysisConfig 型別含 event_import_id（頁面接線：只在 event 模式掛 picker）', () => {
    const src = readFileSync(resolve(__dirname, 'ICConfigPanel.tsx'), 'utf-8');
    expect(src.includes("config.mode === 'event'")).toBe(true);
    expect(src.includes('<EventImportPicker')).toBe(true);
    const page = readFileSync(resolve(__dirname, '../../app/ic-analysis/page.tsx'), 'utf-8');
    expect(page.includes("config.mode === 'event' && <EventTablesPanel")).toBe(true);
  });
});
