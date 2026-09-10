/**
 * SPLITUNIFY Task 3.3 ④：切分 capability 之文案對應（前端唯一出口）。
 *
 * 🔴 reason **字面**來自 `momentum/Analysis/contracts/split_unify.json` 與
 * `event_import_contract.json`，本檔**不手打**——這正是本票要消滅的「兩份真相源」形態。
 * 文案（給使用者看的中文）住這裡，字面（機器比對用）住契約。
 *
 * 🔴 兩條 reason 必須有**可分辨**的文案（B2c／B3 收斂之 R2 之 D5）：
 * 使用者看到「沒有驗證段」時要能分出「我沒填答案窗宣告」與「這條路徑本來就拿不到特徵宇宙」，
 * 前者他自己能修，後者不是他的問題。給同一句話等於把可修的事情講成不可修。
 */
import splitUnify from '../../../momentum/Analysis/contracts/split_unify.json';
import eventContract from '../../../momentum/Analysis/contracts/event_import_contract.json';

const FAIL_CLOSED_REASONS: string[] = (splitUnify as { fail_closed_reasons: string[] }).fail_closed_reasons;

/** 「拿不到 canonical feature universe」之字面（自契約讀）。 */
export const REASON_NO_UNIVERSE: string = (() => {
  const found = FAIL_CLOSED_REASONS.find((r) => r === 'canonical_feature_universe_unavailable');
  if (!found) throw new Error('split_unify.json 缺 canonical_feature_universe_unavailable');
  return found;
})();

/**
 * 「深度不可證」之字面（自事件匯入契約之**具名綁定**讀，與 Python
 * `lookahead_gate.split_blocked_reason()` 同一條解析路徑：綁定鍵 → 字面 → 封閉集合驗證）。
 */
export const REASON_UNVERIFIABLE_LOOKAHEAD: string = (() => {
  const c = eventContract as {
    capability_reason_bindings?: Record<string, string>;
    capability_unavailable_reasons?: string[];
  };
  const value = c.capability_reason_bindings?.l3_lookahead_unverifiable;
  if (!value) throw new Error('event_import_contract.json 之 capability_reason_bindings 缺 l3_lookahead_unverifiable');
  if (!(c.capability_unavailable_reasons ?? []).includes(value)) {
    throw new Error(`綁定值 ${value} 不在 capability_unavailable_reasons 封閉集合內（漂移 fail-closed）`);
  }
  return value;
})();

export interface SplitCapabilityView {
  /** 是否有切分（`false` ⇒ 畫面**禁止**顯示 train／test／purge 計數） */
  hasSplit: boolean;
  /** 給使用者看的一句話；不同 reason 必須不同 */
  text: string;
}

/**
 * 由後端 `capability` 導出畫面該說什麼。
 *
 * 未知 reason ⇒ **照原字面顯示**，不吞成「其他原因」——看不懂的字面至少可以被搜尋，
 * 吞掉之後連「後端出現了沒人處理的新原因」這件事都看不見。
 */
export function splitCapabilityView(
  capability: { split?: string; reason?: string } | undefined | null,
): SplitCapabilityView {
  if (!capability || capability.split === 'ok') return { hasSplit: true, text: '' };
  const reason = capability.reason ?? '';
  if (reason === REASON_UNVERIFIABLE_LOOKAHEAD) {
    return {
      hasSplit: false,
      text: '本批未執行切分：答案窗深度不可證（未完成宣告），只做事件研究，沒有訓練／驗證段。補上答案窗宣告後可重跑。',
    };
  }
  if (reason === REASON_NO_UNIVERSE) {
    return {
      hasSplit: false,
      text: '本批未執行切分：事件掃描路徑取不到 K 線切分所依據的特徵宇宙，只做事件研究（全樣本，非 OOS），沒有訓練／驗證段。',
    };
  }
  return {
    hasSplit: false,
    text: `本批未執行切分（後端原因：${reason || '未提供'}），只做事件研究，沒有訓練／驗證段。`,
  };
}
