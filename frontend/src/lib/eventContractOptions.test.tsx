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
  contractDefault,
  dimContractNode,
  dimOptions,
  isSubmittableLabelSpec,
  resolvePairConflict,
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

  it('⑤ 🔴 `G3-D2` D4.3：`decision_offset_bars` 之控制項**已自 /search 移除**，改顯示指路文字', () => {
    // 原斷言（`/search` 鎖定為契約下界且 `readOnly`）之前提是 k 由匯出畫面填。
    // 裁定②把 k 改為分析參數 ⇒ 控制項移除；「鎖定」這件事在 DOM 上不再有承載體。
    renderPath('/search');
    expect(screen.queryByTestId('event-dim-decision_offset_bars')).toBeNull();
    const moved = screen.getByTestId('event-dim-decision_offset_bars-moved');
    expect(moved.textContent).toContain('k 於 IC 分析頁設定');
    expect(moved.textContent).toContain(String(contractDecisionOffsetMin(CONTRACT)));
  });

  it('🔴 D4.3 over：`/data-preparation` 亦無 k 控制項，但契約 doc 仍顯示（欄位仍存在於檔案裡）', () => {
    renderPath('/data-preparation', true);
    expect(screen.queryByTestId('event-dim-decision_offset_bars')).toBeNull();
    expect(screen.getByTestId('event-dim-decision_offset_bars-moved')).toBeTruthy();
    expect(screen.getByTestId('event-dim-doc-decision_offset_bars').textContent)
      .not.toBe('');
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
    // 🔴 `G3-D2` D1.5（2026-09-04）：`B`／`trigger_open`／兩個 `open_to_*` 解灰。
    //    集合相等**未放寬**——多排除或少排除任一值仍會紅（本條之防偽價值就在此）。
    //    `/search|label_return_mode` 與 `/ic-analysis|label_return_mode` 之值集合現為**空**，
    //    但鍵保留（刪鍵會讓「從未考慮過」與「考慮過且全開」在碼上無從區分）。
    // 🔴 `G3-D2` D3.1（2026-09-05）：`two_stage` 解灰 ⇒ `/search|scenario` 只剩 `A`。
    //    **未放寬**：集合相等，少排除 `A`（或多排除任何值）仍會紅。
    // 🔴 `G3-D2` D4.2（2026-09-05）：兩個 `entry_price_semantic` 之排除集合**清空**
    //    （後端矩陣擴為 13 對）。仍不可選的兩個組合改由 `kind: 'pair_rejected'` 表達
    //    ——那是**成對**限制，塞進本表會把「trigger_close 這個值不能用」講錯。
    //    集合相等**未放寬**：任一路徑多排除或少排除任何值仍會紅。
    expect(actual).toEqual({
      '/search|scenario': new Set(['A']),
      '/search|entry_price_semantic': new Set([]),
      '/search|label_return_mode': new Set([]),
      '/ic-analysis|entry_price_semantic': new Set([]),
      '/ic-analysis|label_return_mode': new Set([]),
    });
  });

  it('🔴 D1.5／D3.1／D4.2 解灰之正面驗收：可選集合恰為預期（不只驗排除表，驗導出結果）', () => {
    // (i) scenario：`B`／`C`／`two_stage` 可選（D3.1 解灰 `two_stage`；SPEC D3.1 驗證第一條）
    expect(new Set(selectable('/search', 'scenario'))).toEqual(new Set(['B', 'C', 'two_stage']));
    // (ii) entry_price_semantic：D4.2 起**五值全開**（無 selection 時；pair 限制需要 selection）
    expect(new Set(selectable('/search', 'entry_price_semantic'))).toEqual(new Set([
      'trigger_open', 'trigger_close', 'next_open', 'decision_bar_open', 'decision_bar_close',
    ]));
    // (iii) label_return_mode：三種報酬選項全開（裁定② v2）
    expect(new Set(selectable('/search', 'label_return_mode')))
      .toEqual(new Set(['open_to_close', 'open_to_horizon_close', 'close_to_close']));
    // 🔴 over 向：`A` 仍**不可選**（否則「全部解灰」也會讓上面三條綠）。
    expect(selectable('/search', 'scenario')).not.toContain('A');
    // 🔴 D4.2 之 over 向搬家：`next_open` 已解灰 ⇒ 原 over 向改由**成對**限制承擔
    //    （選了 `open_to_close` 之後，`trigger_close`／`decision_bar_close` 仍不可選）。
    expect(new Set(selectable('/search', 'entry_price_semantic', undefined,
      { label_return_mode: 'open_to_close' }))).toEqual(new Set([
      'trigger_open', 'next_open', 'decision_bar_open',
    ]));
  });

  it('🔴 `G3-D2` D4.2：`pair_rejected` **雙向** disabled，且理由由契約導出', () => {
    // 方向①：選了 entry=trigger_close ⇒ mode=open_to_close 被擋
    const modes = dimOptions('/search', 'label_return_mode', undefined,
      { entry_price_semantic: 'trigger_close' });
    const blockedMode = modes.find((o) => o.value === 'open_to_close');
    expect(blockedMode?.disabled).toBe(true);
    expect(blockedMode?.kind).toBe('pair_rejected');
    expect(blockedMode?.reason).toContain('答案窗長度為 0');
    // 方向②（反向）：選了 mode=open_to_close ⇒ entry=trigger_close／decision_bar_close 被擋
    const entries = dimOptions('/search', 'entry_price_semantic', undefined,
      { label_return_mode: 'open_to_close' });
    const blockedEntries = entries.filter((o) => o.kind === 'pair_rejected').map((o) => o.value);
    expect(new Set(blockedEntries)).toEqual(new Set(['trigger_close', 'decision_bar_close']));
    // 🔴 兩方向之 disabled 集合互為映射（Task 7.2 之 pair 對稱性閘）
    for (const entry of blockedEntries) {
      const back = dimOptions('/search', 'label_return_mode', undefined,
        { entry_price_semantic: entry }).find((o) => o.value === 'open_to_close');
      expect(back?.kind, `${entry} 之反向`).toBe('pair_rejected');
    }
    // over 向：**未選另一維**時不得擋（還沒選就先擋，使用者連進去的路都沒有）
    expect(dimOptions('/search', 'label_return_mode', undefined, {})
      .every((o) => o.kind !== 'pair_rejected')).toBe(true);
    expect(dimOptions('/search', 'label_return_mode')
      .every((o) => o.kind !== 'pair_rejected')).toBe(true);
    // over 向②：合法對不得被擋
    expect(dimOptions('/search', 'label_return_mode', undefined,
      { entry_price_semantic: 'trigger_open' })
      .every((o) => o.kind !== 'pair_rejected')).toBe(true);
  });

  it('🔴 `G3-D2` D4.2：既選非法 pair ⇒ 另一維重設（契約 default 優先；不合法時取 enum 首個可用值）', () => {
    // 方向①（改 entry 使 mode 落入拒收對）⇒ 重設 mode 為契約 default（D-001 原文之情形）
    const b = resolvePairConflict(
      { entry_price_semantic: 'decision_bar_close', label_return_mode: 'open_to_close' },
      'entry_price_semantic',
    );
    expect(b.reset?.dim).toBe('label_return_mode');
    expect(b.reset?.to).toBe(contractDefault('label_return_mode'));
    expect(b.reset?.disclosure).toContain('契約預設');

    // 方向②（改 mode 成 open_to_close 而 entry 落入拒收對）⇒ **契約 default 本身不合法**
    // 🔴 `entry_price_semantic.default = "trigger_close"` 就在 `open_to_close` 的拒收對裡
    //    ⇒ D-001「重設為契約 default」在這個方向無解（本測試當場打穿）。
    //    細化規則：取契約 **enum 順序**中第一個合法值，並在揭露字串裡明說原因。
    const a = resolvePairConflict(
      { entry_price_semantic: 'trigger_close', label_return_mode: 'open_to_close' },
      'label_return_mode',
    );
    expect(a.reset?.dim).toBe('entry_price_semantic');
    expect(a.reset?.to).not.toBe(contractDefault('entry_price_semantic'));
    // 值由契約 enum 順序導出，不是硬編：`enum` 第一個非拒收值
    const firstLegal = (acceptedValues('entry_price_semantic') as string[])
      .find((v) => !['trigger_close', 'decision_bar_close'].includes(v));
    expect(a.reset?.to).toBe(firstLegal);
    expect(a.selection.entry_price_semantic).toBe(firstLegal);
    expect(a.reset?.disclosure).toContain('因 pair 拒收已重設');
    expect(a.reset?.disclosure).toContain('在這個組合下也不合法');
    // 🔴 重設之後必須真的合法（否則「重設」只是換一個非法值）
    expect(isSubmittableLabelSpec({
      horizon_bars: 1,
      entry_price_semantic: a.selection.entry_price_semantic,
      label_return_mode: a.selection.label_return_mode,
      decision_offset_bars: 0,
    })).toBe(true);

    // over 向：合法組合不得被重設
    expect(resolvePairConflict(
      { entry_price_semantic: 'trigger_open', label_return_mode: 'open_to_close' },
      'label_return_mode',
    ).reset).toBeUndefined();
  });

  it('🔴 `G3-D2` D4.2：送出守衛擋 `rejected_pairs`，放行其餘 13 對', () => {
    for (const entry of ['trigger_close', 'decision_bar_close']) {
      expect(isSubmittableLabelSpec({
        horizon_bars: 1, entry_price_semantic: entry, label_return_mode: 'open_to_close',
        decision_offset_bars: 0,
      }), `${entry} × open_to_close 應被擋`).toBe(false);
    }
    // over 向：13 對全部放行（含 D1 之 UI 曾誤擋的 `(trigger_open, close_to_close)`）
    let allowed = 0;
    for (const entry of ['trigger_open', 'trigger_close', 'next_open',
      'decision_bar_open', 'decision_bar_close']) {
      for (const mode of ['open_to_close', 'open_to_horizon_close', 'close_to_close']) {
        const ok = isSubmittableLabelSpec({
          horizon_bars: 2, entry_price_semantic: entry, label_return_mode: mode,
          decision_offset_bars: 2,
        });
        if (ok) allowed += 1;
      }
    }
    expect(allowed).toBe(13);
  });

  it('🔴 D1.5 `contractDefault`：預設值由契約導出，且與真契約一致', () => {
    expect(contractDefault('entry_price_semantic')).toBe('trigger_close');
    expect(contractDefault('label_return_mode')).toBe('close_to_close');
    // 對**真契約**（非鏡像）取同一值 ⇒ 鏡像漂移會在此紅
    expect(contractDefault('entry_price_semantic', CONTRACT))
      .toBe(contractDefault('entry_price_semantic'));
    expect(contractDefault('label_return_mode', CONTRACT))
      .toBe(contractDefault('label_return_mode'));
    // 🔴 缺 default ⇒ **拋錯，不回退字面**（回退＝第二份預設值）
    expect(() => contractDefault('scenario')).toThrow();
    // 🔴 default 落在枚舉外 ⇒ 拋錯
    const bad = { required_fields: { entry_price_semantic: { enum: ['a', 'b'], default: 'zzz' } } };
    expect(() => contractDefault('entry_price_semantic', bad)).toThrow();
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
      // 🔴 `GROK-R1-P2-01`（R1 閉合）：原鍵集只有四個，**不含** `rejected_pairs` 與 `default`
      //    ⇒ 契約新增／刪除幾何零窗對時，前端鏡像可**靜默漂移**而本測試仍綠，
      //    「三份表同時守住」不成立（producer↔契約另有測試，但前端那一環會單獨漏）。
      //    失敗模式：UI 放行後端算不出的新零窗對，或反過來拒收已支援的對。
      for (const key of [
        'enum', 'accepted', 'rejected_with_reason', 'min', 'rejected_pairs', 'default',
      ] as const) {
        expect(mirror![key], `${dim}.${key}`).toEqual(real![key]);
      }
    },
  );

  it('🔴 `GROK-R1-P2-01` 之可證偽性：鏡像之 `rejected_pairs` 改一個字即紅', () => {
    const real = dimContractNode(CONTRACT, 'label_return_mode');
    expect(real?.rejected_pairs).toBeTruthy();          // 正向對照：契約真的有這個鍵
    const drifted = {
      ...dimContractNode(EVENT_DIM_CONTRACT_MIRROR, 'label_return_mode'),
      rejected_pairs: { open_to_close: ['trigger_close'] },   // 少一個 entry
    };
    expect(drifted.rejected_pairs).not.toEqual(real!.rejected_pairs);
  });
});
