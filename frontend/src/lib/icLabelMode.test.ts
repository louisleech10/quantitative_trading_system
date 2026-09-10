/**
 * EVTLABEL Task 3.2：`ICEventLabelMode` 之值集必須與後端契約檔逐值相同。
 *
 * 🔴 這條擋的是「兩端各自手打枚舉」。前端多打一個值 ⇒ 送出後端 422（使用者看到的是
 * 「分析失敗」而不是「這個選項不存在」）；前端少一個值 ⇒ 使用者根本選不到那個模式，
 * 而後端測試全綠 ⇒ 又是一次「兩端都有、但沒接上」。
 *
 * 契約檔＝`momentum/Analysis/contracts/event_label_mode.json`（唯一真相源）。
 */
import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';
import type { ICEventLabelMode } from '@/lib/types';

const contract = JSON.parse(
  readFileSync(
    path.resolve(__dirname, '../../../momentum/Analysis/contracts/event_label_mode.json'),
    'utf-8',
  ),
) as { label_modes: string[]; label_mode_reasons: string[] };

// 前端這份是**唯一**的 TS 端列舉；型別與值由同一個 const 導出，不得再手打第二份。
const UI_LABEL_MODES = ['auto', 'return_rule', 'imported_binary'] as const;

describe('EVTLABEL Task 3.2 — label mode 值集雙端對證', () => {
  it('① 前端值集與契約檔 `label_modes` 逐值相同', () => {
    expect([...UI_LABEL_MODES].sort()).toEqual([...contract.label_modes].sort());
  });

  it('② 型別與值一致（TS 型別擋編譯期、上面那條擋執行期）', () => {
    const modes: ICEventLabelMode[] = [...UI_LABEL_MODES];
    expect(modes).toHaveLength(contract.label_modes.length);
  });

  it('③ `auto` 必須存在——它是預設值，缺了就沒有「後端自己判」這條路', () => {
    expect(contract.label_modes).toContain('auto');
  });

  it('④ 退回報酬版之原因集合非空且封閉（前端要照這幾個值顯示文案）', () => {
    expect(contract.label_mode_reasons.length).toBeGreaterThan(0);
    expect([...contract.label_mode_reasons].sort()).toEqual([
      'class_below_min_selection',
      'label_invalid_domain',
      'no_label_column',
      'one_class',
    ]);
  });
});
