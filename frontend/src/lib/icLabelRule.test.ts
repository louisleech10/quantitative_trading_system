/**
 * EVTLABEL Task 1.2／1.3：label 規則揭露行與 h／k 單位文案。
 * 值取自受理 run（165 事件、12h×1h、h=1 close_to_close ⇒ 視窗 12 根、label 136/29）。
 */
import { describe, expect, it } from 'vitest';

import {
  hHintCaption,
  kHintCaption,
  labelRuleLines,
  readLabelRule,
  unitCaption,
  type ICEventLabelRule,
} from './icLabelRule';

const RULE: ICEventLabelRule = {
  label_source: 'event_label_value',
  statistic_kind: 'conditional_ic',
  horizon_bars: 1,
  decision_offset_bars: 0,
  entry_price_semantic: 'trigger_close',
  label_return_mode: 'close_to_close',
  h_unit: 'event_timeframe_bars',
  event_timeframe: '12h',
  feature_timeframe: '1h',
  feature_bars_per_event_bar: 12,
  ratio_integral: true,
  label_window_feature_bars: 12,
  return_formula: 'close[t0+h] / close[t0] - 1 × direction_sign',
  imported_binary_label: { present: true, n_pos: 136, n_neg: 29, used: false },
  n_events_consumed: 165,
  uniqueness: { mean: 1, min: 1, n_eff: 165, n_overlapping_pairs: 0 },
};

describe('labelRuleLines', () => {
  it('受理 run：四行＋重疊度，含「第 12 根」與正反數', () => {
    const lines = labelRuleLines(RULE)!;
    expect(lines[0]).toContain('h=1 根');
    expect(lines[0]).toContain('第 12 根');
    expect(lines[1]).toContain('k=0 根');
    expect(lines[2]).toContain('trigger_close');
    expect(lines[2]).toContain('close[t0+h]');
    expect(lines[3]).toContain('正 136／反 29');
    expect(lines[3]).toContain('本次未用');
    expect(lines[4]).toContain('有效樣本 165.0');
  });

  it('used=true ⇒ 第四行改講「已用」', () => {
    const lines = labelRuleLines({
      ...RULE,
      imported_binary_label: { ...RULE.imported_binary_label!, used: true },
    })!;
    expect(lines[3]).toContain('本次已用');
    expect(lines[3]).toContain('0/1 標籤');
  });

  it('mixed timeframe（ratio 未知）⇒ 退化為不帶換算，仍不空白', () => {
    const lines = labelRuleLines({
      ...RULE,
      event_timeframe: 'mixed',
      feature_bars_per_event_bar: null,
      ratio_integral: false,
    })!;
    expect(lines[0]).toContain('單位＝事件週期的根數');
    expect(lines[0]).not.toContain('第 12 根');
  });

  it('沒有匯入 0/1 ⇒ 第四行講「無」', () => {
    const lines = labelRuleLines({
      ...RULE,
      imported_binary_label: { present: false, n_pos: 0, n_neg: 0, used: false },
    })!;
    expect(lines[3]).toContain('：無；');
  });

  it('return_formula 缺 ⇒ 明說未揭露，不留空白', () => {
    const lines = labelRuleLines({ ...RULE, return_formula: null })!;
    expect(lines[2]).toContain('報酬算法未揭露');
  });

  it('沒有 event_label_rule ⇒ null（不渲染）', () => {
    expect(labelRuleLines(null)).toBeNull();
    expect(readLabelRule({})).toBeNull();
    expect(readLabelRule({ event_label_rule: RULE })).toEqual(RULE);
  });
});

describe('h／k 單位文案（Task 1.3）', () => {
  it('12h 事件×1h 特徵 ⇒ 1 根＝12 根', () => {
    expect(unitCaption('12h', '1h', 12)).toBe('單位：事件週期（12h）的根數；1 根＝1h 特徵的 12 根');
    expect(unitCaption('4h', '1h', 4)).toContain('1h 特徵的 4 根');
  });

  it('非整數倍或缺 tf ⇒ 退化文案', () => {
    expect(unitCaption('1h', '4h', 0.25)).toBe('單位：事件週期的根數');
    expect(unitCaption(null, '1h', 12)).toBe('單位：事件週期的根數');
    expect(unitCaption('12h', null, null)).toBe('單位：事件週期的根數');
  });

  it('k 旁第二句講清楚粗細粒度誤解', () => {
    const text = kHintCaption('1h');
    expect(text).toContain('k=0 即在 t₀ 決策');
    expect(text).toContain('Lag');
    expect(text).toContain('不需調 k');
  });

  it('h 旁第二句講答案窗', () => {
    expect(hHintCaption('12h')).toContain('答案窗＝h 根 12h');
    expect(hHintCaption(null)).toContain('事件週期');
  });
});
