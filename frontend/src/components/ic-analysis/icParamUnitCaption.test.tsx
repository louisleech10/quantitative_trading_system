/**
 * EVTLABEL Task 1.3：h／k 輸入框旁的單位說明（使用者 2026-09-10 裁定「UI 要寫清楚」）。
 *
 * 三種情境：①12h 事件×1h 特徵 ⇒ 「1 根＝12 根」②4h×1h ⇒ 4 根
 * ③mixed timeframe 或未選 feature run ⇒ 退化成不帶換算的句子（不猜數字）。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import EventBatchDisclosurePanel from './EventBatchDisclosurePanel';
import type { EventImportDetail } from '@/lib/types';

vi.mock('@/lib/api', () => ({
  getEventImport: vi.fn(),
  createRandomControlBatch: vi.fn(),
  compareRandomControl: vi.fn(),
}));

function detailWith(timeframes: string[]): EventImportDetail {
  return {
    summary: {
      import_id: 'imp1',
      source_name: 'events.csv',
      upload_sha256: 'x'.repeat(64),
      imported_at: '2026-09-09T13:05:33Z',
      n_events: 165,
      symbols: ['ETHUSDT'],
      timeframes,
      direction: 'long',
      scenario: 'B',
    },
    batch_facts: {
      scenario: 'B',
      control_kind: 'user_labeled_same_trigger',
      direction: 'long',
      label_origin: 'search_positive_case',
      t0: [{ event_id: 'ETHUSDT:12h:1735776000000', t0_ms: 1735776000000 }],
      label: [{ event_id: 'ETHUSDT:12h:1735776000000', label: 1 }],
    },
    declaration_seeds: { entry_price_semantic: 'trigger_close', label_return_mode: 'close_to_close' },
    batch_fact_notes: {
      control_kind_values: ['user_labeled_same_trigger'],
      decision_offset_bars_record_values: [0],
    },
  } as unknown as EventImportDetail;
}

const SPEC = {
  horizon_bars: 1,
  entry_price_semantic: 'trigger_close',
  label_return_mode: 'close_to_close',
  decision_offset_bars: 0,
} as const;

afterEach(cleanup);

describe('h／k 單位說明', () => {
  it('12h 事件 × 1h 特徵 ⇒ 兩個輸入旁都寫「1 根＝1h 特徵的 12 根」', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp1"
        detail={detailWith(['12h'])}
        featureTimeframe="1h"
        labelSpec={SPEC}
        onChangeLabelSpec={() => {}}
      />,
    );
    for (const id of ['ic-param-h-unit', 'ic-param-k-unit']) {
      const text = screen.getByTestId(id).textContent ?? '';
      expect(text).toContain('單位：事件週期（12h）的根數');
      expect(text).toContain('1h 特徵的 12 根');
    }
    expect(screen.getByTestId('ic-param-h-unit').textContent).toContain('答案窗＝h 根 12h');
    const kText = screen.getByTestId('ic-param-k-unit').textContent ?? '';
    expect(kText).toContain('k=0 即在 t₀ 決策');
    expect(kText).toContain('不需調 k');
  });

  it('4h 事件 × 1h 特徵 ⇒ 4 根', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp1"
        detail={detailWith(['4h'])}
        featureTimeframe="1h"
        labelSpec={SPEC}
        onChangeLabelSpec={() => {}}
      />,
    );
    expect(screen.getByTestId('ic-param-h-unit').textContent).toContain('1h 特徵的 4 根');
  });

  it('mixed timeframe ⇒ 退化文案，不出現換算數字', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp1"
        detail={detailWith(['12h', '4h'])}
        featureTimeframe="1h"
        labelSpec={SPEC}
        onChangeLabelSpec={() => {}}
      />,
    );
    const text = screen.getByTestId('ic-param-h-unit').textContent ?? '';
    expect(text).toContain('單位：事件週期的根數');
    expect(text).not.toContain('特徵的 12 根');
  });

  it('未選 feature run（featureTimeframe 缺）⇒ 退化文案', () => {
    render(
      <EventBatchDisclosurePanel
        importId="imp1"
        detail={detailWith(['12h'])}
        labelSpec={SPEC}
        onChangeLabelSpec={() => {}}
      />,
    );
    expect(screen.getByTestId('ic-param-k-unit').textContent).toContain('單位：事件週期的根數');
  });
});
