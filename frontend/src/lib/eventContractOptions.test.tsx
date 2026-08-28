/**
 * GAP-3 UX **Task 7.1** 驗收（SPEC L2870–2884，①~⑩）。
 *
 * 🔴 **比對基準一律由契約／具名常數導出**，本檔**不寫第二份期望清單**（SPEC「不可做」）。
 *    ①~⑤ 之「可操作選項集合」由**實際 render 後之 DOM** 取得（`getAllByRole('option')` 濾 `disabled`），
 *    不是讀原始碼形狀——「宣告了」不等於「執行期有」（本 epic 之 §6.2）。
 * 🔴 ⑩ 之 golden byte 級不變由後端 `scripts/gap3_freeze_golden.py --check` 守（收案關卡），
 *    本檔以「五維度維持預設 ⇒ 落檔記錄逐鍵等於 Task 7.0 之常數」對應其前件。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import EventDimensionFields, { type EventDimensionValues } from '@/components/case/EventDimensionFields';
import {
  ENUM_EVENT_DIMENSIONS,
  EVENT_DIM_CONTRACT_MIRROR,
  EVENT_DIM_CONTRACT_PATHS,
  EVENT_DIM_PATH_EXCLUSIONS,
  type EnumEventDimension,
  type EventDimPath,
  acceptedValues,
  contractDecisionOffsetMin,
  dimContractNode,
  selectable,
} from '@/lib/eventDimensions';
import {
  EVENT_EXPORT_CONTROL_KIND,
  EVENT_EXPORT_DECISION_OFFSET_BARS,
  EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
  EVENT_EXPORT_LABEL_RETURN_MODE,
  EVENT_EXPORT_SCENARIO,
  buildEventContractRecords,
  eventDimsToExportOptions,
} from '@/lib/eventExport';
import type { CaseData } from '@/lib/types';

const CONTRACT_PATH = resolve(__dirname, '../../../momentum/Analysis/contracts/event_import_contract.json');
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, 'utf8')) as unknown;

const UNSET: EventDimensionValues = {
  scenario: '', control_kind: '', entry_price_semantic: '', label_return_mode: '', decision_offset_bars: '',
};

/**
 * render 後之**可操作**選項值集合。
 *
 * 🔴 `disabled` 一律不計入 ⇒ 放一個 disabled 的值湊數不會讓斷言變綠。
 * 🔴 `value === ''` 是「未選」控制項（`allowUnset`），**不是契約的值**，故排除；
 *    這是本檔唯一一條與契約無關的過濾規則，其判準是「空字串」而非任何值的白名單。
 */
function enabledOptionValues(testid: string): string[] {
  const select = screen.getByTestId(testid) as HTMLSelectElement;
  return Array.from(select.querySelectorAll('option'))
    .filter((o) => !o.disabled && o.value !== '')
    .map((o) => o.value);
}

/**
 * 🔴 **刻意不傳 `contract` prop**：元件走**生產組態**（鏡像），期望值那側才餵真契約。
 * 兩側同源的話「契約加值而 UI 沒跟」永遠不會紅（`7.2-M1` 錄到空紅集合之根因）。
 */
function renderPath(path: EventDimPath, allowUnset = false) {
  return render(
    <EventDimensionFields path={path} values={UNSET} onChange={() => {}} allowUnset={allowUnset} />,
  );
}

afterEach(cleanup);

describe('Task 7.1 ①~⑤ — 每維度之可操作 UI 選項集合 == selectable(path, dim)', () => {
  it.each(ENUM_EVENT_DIMENSIONS)('`%s` 於 /search', (dim: EnumEventDimension) => {
    renderPath('/search');
    const ui = enabledOptionValues(`event-dim-${dim}`);
    const expected = selectable('/search', dim, CONTRACT);
    expect(new Set(ui)).toEqual(new Set(expected));
    expect(ui.length).toBe(expected.length);
  });

  it('⑤ `decision_offset_bars` 非 enum：有控制項，且 /search 之可輸入範圍鎖定契約下界（SPEC L2864）', () => {
    renderPath('/search');
    const input = screen.getByTestId('event-dim-decision_offset_bars') as HTMLInputElement;
    const min = contractDecisionOffsetMin(CONTRACT);
    expect(input.min).toBe(String(min));
    expect(input.max).toBe(String(min));
    expect(input.readOnly).toBe(false);
  });
});

describe('Task 7.1 ⑦ — 契約恆拒者 disabled 且顯示契約 reason 字面', () => {
  it('`control_kind` 之 platform_random_bars 為 disabled 且帶契約 reason', () => {
    renderPath('/search');
    const select = screen.getByTestId('event-dim-control_kind') as HTMLSelectElement;
    const node = dimContractNode(CONTRACT, 'control_kind');
    const rejected = node?.rejected_with_reason ?? {};
    const names = Object.keys(rejected);
    expect(names.length).toBeGreaterThan(0);   // 正向對照：契約真的有恆拒值（不是路徑打錯）
    for (const value of names) {
      const opt = Array.from(select.querySelectorAll('option')).find((o) => o.value === value);
      expect(opt, `契約恆拒值 ${value} 應出現在 UI（要顯示為 disabled，不是不顯示）`).toBeTruthy();
      expect(opt!.disabled).toBe(true);
      expect(opt!.title).toBe(rejected[value]);
      // 理由亦以可見文字呈現（`title` 之外還要看得到）
      expect(screen.getByTestId(`event-dim-blocked-control_kind-${value}`).textContent)
        .toContain(rejected[value]);
    }
  });
});

describe('Task 7.1 ⑧ — /search 之 scenario 限制只在該路徑', () => {
  it('/search 之 A／B／two_stage 皆 disabled 且顯示排除理由', () => {
    renderPath('/search');
    const excluded = EVENT_DIM_PATH_EXCLUSIONS['/search|scenario'];
    const select = screen.getByTestId('event-dim-scenario') as HTMLSelectElement;
    for (const value of excluded.values) {
      const opt = Array.from(select.querySelectorAll('option')).find((o) => o.value === value);
      expect(opt!.disabled).toBe(true);
      expect(screen.getByTestId(`event-dim-blocked-scenario-${value}`).textContent).toContain(excluded.reason);
    }
  });

  it('🔴 over 向：同一維度在 /data-preparation 之 selectable == 契約 enum 全集（不得被 /search 之排除誤及）', () => {
    renderPath('/data-preparation', true);
    const ui = enabledOptionValues('event-dim-scenario');
    const all = acceptedValues('scenario', CONTRACT);
    expect(new Set(ui)).toEqual(new Set(all));
    expect(ui.length).toBe(all.length);
  });
});

describe('Task 7.1 ⑨ — EVENT_DIM_PATH_EXCLUSIONS 之內容（集合相等，不用計數字面）', () => {
  it('內容集合相等於 SPEC L2854–2860 之五列', () => {
    const actual = Object.fromEntries(
      Object.entries(EVENT_DIM_PATH_EXCLUSIONS).map(([k, v]) => [k, new Set(v.values)]),
    );
    expect(actual).toEqual({
      '/search|scenario': new Set(['A', 'B', 'two_stage']),
      '/search|entry_price_semantic':
        new Set(['trigger_open', 'next_open', 'decision_bar_open', 'decision_bar_close']),
      '/search|label_return_mode': new Set(['open_to_close', 'open_to_horizon_close']),
      '/ic-analysis|entry_price_semantic':
        new Set(['trigger_open', 'next_open', 'decision_bar_open', 'decision_bar_close']),
      '/ic-analysis|label_return_mode': new Set(['open_to_close', 'open_to_horizon_close']),
    });
  });

  it('每個理由字串皆非空', () => {
    for (const [key, row] of Object.entries(EVENT_DIM_PATH_EXCLUSIONS)) {
      expect(row.reason, `${key} 之理由`).not.toBe('');
      expect(row.reason.trim().length, `${key} 之理由`).toBeGreaterThan(0);
    }
  });

  it('🔴 排除之值必須是契約裡真的存在的值（打錯字不會靜默變成「沒排除」）', () => {
    for (const [key, row] of Object.entries(EVENT_DIM_PATH_EXCLUSIONS)) {
      const dim = key.split('|')[1] as EnumEventDimension;
      const all = dimContractNode(CONTRACT, dim)?.enum ?? [];
      for (const v of row.values) expect(all, `${key} 之 ${v}`).toContain(v);
    }
  });
});

describe('Task 7.1 ⑩ — 五維度維持預設 ⇒ 接出 UI 這件事不動任何數值', () => {
  it('UI 初始值走 eventDimsToExportOptions 之落檔 == 完全不傳五維度之落檔（逐鍵相同）', async () => {
    const row = {
      symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00',
      positive_case: true, future_1bar_return: 0.01,
    } as unknown as CaseData;
    const base = {
      timeframe: '1h',
      conditions: [{ parameter: 'price_change', operator: '>=', value: 3 }],
      priceChangeMethod: 'close_to_close',
      attachedHorizons: [1],
      lookaheadBarsDeclared: { '1h': 2 },
      sourceFileText: '[]',
      sourceFileDigest: 'a'.repeat(64),
    };
    // 完全不傳（Task 7.0 之前的實況）
    const before = await buildEventContractRecords([row], { ...base });
    // `/search` 頁之初始 state ＝ Task 7.0 之常數，經同一對映函式傳入
    const after = await buildEventContractRecords([row], {
      ...base,
      ...eventDimsToExportOptions({
        scenario: EVENT_EXPORT_SCENARIO,
        control_kind: EVENT_EXPORT_CONTROL_KIND,
        entry_price_semantic: EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
        label_return_mode: EVENT_EXPORT_LABEL_RETURN_MODE,
        decision_offset_bars: EVENT_EXPORT_DECISION_OFFSET_BARS,
      }),
    });
    expect(after.records).toEqual(before.records);
  });
});

describe('Task 7.1 — 契約鏡像防漂移（前端無契約端點，沿用 eventContractDocs 之作法）', () => {
  it.each(['scenario', 'control_kind', 'entry_price_semantic', 'label_return_mode', 'decision_offset_bars'] as const)(
    '`%s` 之鏡像節點逐鍵等於契約', (dim) => {
      const real = dimContractNode(CONTRACT, dim);
      const mirror = dimContractNode(EVENT_DIM_CONTRACT_MIRROR, dim);
      expect(real, `契約路徑 ${EVENT_DIM_CONTRACT_PATHS[dim].join('.')} 應存在`).toBeTruthy();
      expect(mirror).toBeTruthy();
      for (const key of ['enum', 'accepted', 'rejected_with_reason', 'min'] as const) {
        expect(mirror![key], `${dim}.${key}`).toEqual(real![key]);
      }
    },
  );
});
