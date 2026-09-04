/**
 * GAP-3 UX **Task 7.2** — 機械閘：可操作選項集合 ＝ `selectable(path,dim)`，**且選值真的傳到落檔**。
 *
 * 三層（SPEC L2924–2936）：
 *  **①集合層**——render 後之**可操作**（`disabled === false`）選項集合 `==` `selectable(path,dim)`。
 *  **②round-trip 層**——每維度選一個**非預設值** → `buildEventContractRecords` → 落檔路徑 `===` 所選值。
 *      🔴 這層才擋得住 B5 病因（「介面有、沒傳」）；只有①時 UI 可以全對而 payload 仍是寫死預設。
 *  **③非 enum 欄**——`decision_offset_bars`：有可輸入且非唯讀之控制項、`-1` fail-closed、`k` 落檔 `=== k`。
 *
 * 🔴 **比對基準＝`selectable(path,dim)`，其兩個輸入都不是人工清單**：
 *    `accepted(dim)` 由**本檔讀進來的真契約 JSON** 導出、`pathExclusions` 由具名常數導出。
 *    ⇒ 契約增值而 UI 沒跟 ⇒ ①**自動轉紅**，該紅為設計意圖，**不得以更新人工清單消紅**。
 *
 * 🔴 **涵蓋邊界（SPEC 覆蓋風險逐字）**：本閘只保護**五個批次維度**，
 *    **不保護契約全部欄位**——Task 1.1 之 reason 與 `filters` 屬非 enum 型欄位，不在涵蓋面內。
 *    「有機械閘 ≠ 契約全欄受保護」。
 * 🔴 本閘**不擴及** `/ic-analysis`（其可操作集合由 Task 7.6 ⑤ 守、常數內容由 7.1 ⑨ 守）；
 *    若日後納入，須**同時刪除** 7.6 ⑤，不得兩處並存。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import EventDimensionFields, { type EventDimensionValues } from '@/components/case/EventDimensionFields';
import {
  ENUM_EVENT_DIMENSIONS,
  EVENT_DIMENSIONS,
  type EnumEventDimension,
  type EventDimPath,
  acceptedValues,
  contractDecisionOffsetMin,
  dimensionBatchDefaults,
  dimensionDefaultConflicts,
  selectable,
} from '@/lib/eventDimensions';
import {
  buildEventContractRecords,
  eventDimsToExportOptions,
  type EventExportOptions,
} from '@/lib/eventExport';
import type { CaseData } from '@/lib/types';

const CONTRACT = JSON.parse(readFileSync(
  resolve(__dirname, '../../../momentum/Analysis/contracts/event_import_contract.json'), 'utf8',
)) as unknown;

const UNSET: EventDimensionValues = {
  scenario: '', control_kind: '', entry_price_semantic: '', label_return_mode: '', decision_offset_bars: '',
};

/** 可操作選項值（`disabled` 一律不計入；`value === ''` 是「未選」控制項，非契約值）。 */
function enabledOptionValues(testid: string): string[] {
  const select = screen.getByTestId(testid) as HTMLSelectElement;
  return Array.from(select.querySelectorAll('option'))
    .filter((o) => !o.disabled && o.value !== '')
    .map((o) => o.value);
}

/**
 * 🔴 **刻意不傳 `contract` prop**：要讓元件走**生產組態**（`eventDimensions.ts` 之鏡像）。
 *
 * 期望值那一側才餵**真契約**（`selectable(path, dim, CONTRACT)`）。兩側來源不同是重點：
 * 把真契約也注進元件的話，契約變異時**兩邊一起變**、①永遠不紅
 * ——本檔第一版就是這樣寫的，`7.2-M1`（契約加第 5 個 scenario）當場錄到**空紅集合**。
 */
function renderPath(path: EventDimPath, allowUnset = false) {
  return render(
    <EventDimensionFields path={path} values={UNSET} onChange={() => {}} allowUnset={allowUnset} />,
  );
}

/** 落檔記錄之取值路徑（`label_return_mode` **巢狀**，其餘頂層）。 */
function landedValue(record: Record<string, unknown>, dim: string): unknown {
  if (dim === 'label_return_mode') {
    return (record.label_definition as Record<string, unknown>).label_return_mode;
  }
  return record[dim];
}

function caseRow(): CaseData {
  return {
    symbol: 'ETHUSDT', timeframe: '1h', timestamp: '2024-01-01 00:00:00',
    positive_case: true, price_change: 3.2, future_1bar_return: 0.01,
  } as unknown as CaseData;
}

function baseOpts(over: Partial<EventExportOptions> = {}): EventExportOptions {
  return {
    timeframe: '1h',
    conditions: [{ parameter: 'price_change', operator: '>=', value: 3 }],
    priceChangeMethod: 'close_to_close',
    attachedHorizons: [1],
    lookaheadBarsDeclared: { '1h': 2 },
    sourceFileText: '[]',
    sourceFileDigest: 'a'.repeat(64),
    ...over,
  };
}

afterEach(cleanup);

// ───────────────────────────── ① 集合層（五維度各一條） ─────────────────────────────

describe('Task 7.2 ① 集合層 — 可操作 UI 選項集合 == selectable(path, dim)', () => {
  it.each(ENUM_EVENT_DIMENSIONS)('`%s`（/search）', (dim: EnumEventDimension) => {
    renderPath('/search');
    const ui = enabledOptionValues(`event-dim-${dim}`);
    const expected = selectable('/search', dim, CONTRACT);
    expect(new Set(ui)).toEqual(new Set(expected));
    expect(ui.length).toBe(expected.length);   // 長度亦相等 ⇒ 重複值湊不出來
  });

  it('`decision_offset_bars`（非 enum）之下界由契約 `min` 導出；鎖定路徑 `readOnly`、解鎖路徑可輸入', () => {
    renderPath('/search');
    const locked = screen.getByTestId('event-dim-decision_offset_bars') as HTMLInputElement;
    expect(locked.min).toBe(String(contractDecisionOffsetMin(CONTRACT)));
    expect(locked.readOnly).toBe(true);          // R3 群集 A：鎖 0 之路徑
    cleanup();
    renderPath('/data-preparation', true);
    const free = screen.getByTestId('event-dim-decision_offset_bars') as HTMLInputElement;
    expect(free.readOnly).toBe(false);           // over 向：解鎖路徑不得被連坐
    expect(free.min).toBe(String(contractDecisionOffsetMin(CONTRACT)));
  });
});

// ───────────────────────── ② round-trip 層（五維度各一條） ─────────────────────────

/**
 * 每維度之**非預設值**（取自契約 enum 中不等於現行預設者）。
 * 🔴 值本身由契約導出，不是人工清單：改契約之 enum 順序不影響，刪值才會讓這裡拿不到而紅。
 */
const NON_DEFAULT: Record<string, string | number> = {
  scenario: 'A',
  control_kind: 'user_labeled_other',
  entry_price_semantic: 'next_open',
  label_return_mode: 'open_to_close',
  decision_offset_bars: 3,
};

describe('Task 7.2 ② round-trip 層 — 選非預設值 ⇒ 落檔記錄之對應路徑 === 所選值', () => {
  it.each(EVENT_DIMENSIONS)('`%s` 傳進去就要落到檔裡', async (dim) => {
    const chosen = NON_DEFAULT[dim];
    // 正向對照：enum 型之非預設值必須真的在契約裡（打錯字不會靜默通過）
    if (dim !== 'decision_offset_bars') {
      expect(acceptedValues(dim as EnumEventDimension, CONTRACT)).toContain(chosen as string);
    }
    // 其餘四維度給**合法預設**，只有本維度是非預設值
    // 🔴 不得寫成 `{...DEFAULTS, ...UNSET, [dim]: chosen}`——`UNSET` 會把其餘四個灌成空字串，
    //    測試照樣綠（只斷言本維度），但落檔的其餘四欄是非法值＝假綠。tsc 於本批當場抓到。
    const opts = eventDimsToExportOptions({
      scenario: 'C',
      control_kind: 'user_labeled_same_trigger',
      entry_price_semantic: 'trigger_close',
      label_return_mode: 'close_to_close',
      decision_offset_bars: 0,
      [dim]: chosen,
    } as Parameters<typeof eventDimsToExportOptions>[0]);
    const out = await buildEventContractRecords([caseRow()], baseOpts(opts));
    expect(landedValue(out.records[0] as Record<string, unknown>, dim)).toBe(chosen);
  });
});

// ───────────────────────────── ③ 非 enum 欄（兩條） ─────────────────────────────

describe('Task 7.2 ③ 非 enum 欄 — decision_offset_bars', () => {
  it('under：`-1` ⇒ fail-closed（契約 `min: 0`），一列都不落', async () => {
    await expect(buildEventContractRecords([caseRow()], baseOpts({ decisionOffsetBars: -1 })))
      .rejects.toThrow(/decision_offset_bars/);
  });

  it('🔴 over：`k = 0` 與正整數 `k` 皆須成功且落檔 `=== k`（不該擋的不得被誤擋）', async () => {
    for (const k of [0, 1, 3, 12]) {
      const out = await buildEventContractRecords([caseRow()], baseOpts({ decisionOffsetBars: k }));
      expect(out.records).toHaveLength(1);
      expect((out.records[0] as Record<string, unknown>).decision_offset_bars, `k=${k}`).toBe(k);
    }
  });

  it('🔴 R3 群集 D：**解鎖路徑之 UI→payload 回合**——在 /data-preparation 打 k=3 ⇒ 批次預設帶 3', () => {
    // `GROK-R3-P2-02`：③ 原本只有函式層，而裁定 A 把「輸入 k ⇒ 落檔 === k」的
    // 使用者路徑指向 /data-preparation ⇒ 那條路徑本身必須有機械閘，否則裁定 A 是空頭支票。
    let current: EventDimensionValues = { ...UNSET };
    const { rerender } = render(
      <EventDimensionFields
        path="/data-preparation" values={current} allowUnset
        onChange={(next) => { current = next; }}
      />,
    );
    const input = screen.getByTestId('event-dim-decision_offset_bars') as HTMLInputElement;
    expect(input.readOnly).toBe(false);                       // 正向對照：這條路徑真的是解鎖的
    fireEvent.change(input, { target: { value: '3' } });
    expect(current.decision_offset_bars).toBe(3);             // UI → state
    rerender(
      <EventDimensionFields path="/data-preparation" values={current} allowUnset onChange={() => {}} />,
    );
    // state → 送給後端的批次預設（`dimensionBatchDefaults` 是 CSV 匯入路徑之唯一組裝點）
    expect(dimensionBatchDefaults(current, undefined).decision_offset_bars).toBe(3);
  });

  it('🔴 R4 `CODEX-R4-P2-01`：小數 `k` **不得被靜默截斷**，且送出前顯式擋下', () => {
    let current: EventDimensionValues = { ...UNSET };
    render(
      <EventDimensionFields
        path="/data-preparation" values={current} allowUnset
        onChange={(next) => { current = next; }}
      />,
    );
    fireEvent.change(screen.getByTestId('event-dim-decision_offset_bars'), { target: { value: '1.9' } });
    // 原缺陷：`Math.trunc` 讓 1.9 靜默變成 1——使用者以為填了 1.9、系統收了 1，
    // 而契約那條「必須是 int」的拒絕永遠不會被看到。
    expect(current.decision_offset_bars).toBe(1.9);
    // 取而代之：送出前**顯式**擋下並說出原因
    const problems = dimensionDefaultConflicts(current, undefined, []);
    expect(problems.some((p) => /整數/.test(p) && /decision_offset_bars/.test(p))).toBe(true);
    // over 向：整數不得被這條誤擋
    expect(dimensionDefaultConflicts({ ...current, decision_offset_bars: 3 }, undefined, [])).toEqual([]);
  });

  it('🔴 R4 over：鎖定路徑之 clamp 只夾範圍（`5` ⇒ `0`），不改變整數性判準', () => {
    let current: EventDimensionValues = { ...UNSET, decision_offset_bars: 0 };
    render(
      <EventDimensionFields
        path="/search" values={current} onChange={(next) => { current = next; }}
      />,
    );
    // `readOnly` 擋使用者；本條走的是程式化設值那層
    fireEvent.change(screen.getByTestId('event-dim-decision_offset_bars'), { target: { value: '5' } });
    expect(current.decision_offset_bars).toBe(0);
  });
});

// ─────────────────────────── 路徑對照（兩條；over 向） ───────────────────────────

describe('Task 7.2 路徑對照 — 同一維度之限制只在該路徑成立', () => {
  it('🔴 over：`scenario` 於 /data-preparation 四值**全部**可操作（不得被 /search 之排除誤及）', () => {
    renderPath('/data-preparation', true);
    const ui = enabledOptionValues('event-dim-scenario');
    const all = acceptedValues('scenario', CONTRACT);
    expect(new Set(ui)).toEqual(new Set(all));
    expect(ui.length).toBe(all.length);
    expect(ui.length).toBeGreaterThan(selectable('/search', 'scenario', CONTRACT).length);
  });

  it('🔴 over：`entry_price_semantic` 於 /data-preparation 為契約 enum 全集，/search 為 D1 之兩值', () => {
    renderPath('/data-preparation', true);
    const prep = enabledOptionValues('event-dim-entry_price_semantic');
    expect(new Set(prep)).toEqual(new Set(acceptedValues('entry_price_semantic', CONTRACT)));
    cleanup();
    renderPath('/search');
    // 🔴 `G3-D2` D1.5：`trigger_open` 解灰 ⇒ 由一值變兩值。
    //    **順序沿用契約 enum 順序**（`selectable` 不另排），故 trigger_open 在前。
    //    仍為**嚴格相等**（非 toContain）：其餘三值若被誤解灰，本條照樣紅。
    expect(enabledOptionValues('event-dim-entry_price_semantic'))
      .toEqual(['trigger_open', 'trigger_close']);
  });
});

// 🔴 ② 之**呼叫端**半邊（page.tsx 真的把五維度逐一傳出去；SPEC mutation (c) 之錨點）
//    在 `src/app/search/contractEnumWiringPage.test.tsx`——`vi.mock` 是**檔案層 hoist**，
//    與本檔之「真的呼叫 `buildEventContractRecords`」無法共存於同一檔。
//    兩檔皆命中 `--run contractEnumWiring` 之檔名選擇器。
