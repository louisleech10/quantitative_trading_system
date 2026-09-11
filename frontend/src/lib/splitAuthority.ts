/**
 * SPLITUNIFY Task 4.1：切分權威與 canonical 驗證段揭露之前端唯一出口。
 *
 * 🔴 值集自 `momentum/Analysis/contracts/split_unify.json` 讀，**前端不手打第二份**（SPEC C-8）。
 * 🔴 `n_test` 為 `null` ⇒ 顯示「無」，**永遠不顯示 0**：0 讀起來是「算過，結果是零個」，
 *    那正是本票要消滅的假數字（原始症狀＝同一批事件兩個互相矛盾的驗證段數字，實測 31 vs 33）。
 */
import splitUnify from '../../../momentum/Analysis/contracts/split_unify.json';

const CONTRACT = splitUnify as {
  split_authority_values: string[];
  fail_closed_reasons: string[];
  split_unify_keys: string[];
};

/** canonical 切分權威之封閉值集（自契約讀）。 */
export const SPLIT_AUTHORITY_VALUES: readonly string[] = CONTRACT.split_authority_values;

/** `metadata.split_unify` 之必填鍵（自契約讀）。 */
export const SPLIT_UNIFY_KEYS: readonly string[] = CONTRACT.split_unify_keys;

export interface SplitUnifyDisclosure {
  n_test: number | null;
  split_authority: string;
  boundary_hash: string | null;
  per_symbol_counts: Record<string, number>;
  reason: string | null;
}

/** 權威值 → 給使用者看的中文標籤；未知值照原字面顯示（不吞成「其他」）。 */
export function splitAuthorityLabel(authority: string | undefined | null): string {
  if (authority === 'kline_holdout') return 'K 線時間切分（holdout）';
  return authority ? String(authority) : '未提供';
}

export interface SplitUnifyView {
  /** 有沒有一個可顯示的數字（`false` ⇒ 顯示「無」，**不得**顯示 0） */
  hasCount: boolean;
  /** 顯示用文字：有數字時為該數字，否則「無」 */
  countText: string;
  /** 來源標籤（一律顯示——數字沒有來源就無法判斷可不可信） */
  authorityText: string;
  /** fail-closed 時的原因字面（原樣帶出，供搜尋） */
  reason: string | null;
  /** 已知的全域 run（設計上就不寫這塊）⇒ 顯示「不適用」，與「算不出來」是兩件事 */
  notApplicable?: boolean;
  /** 🔴 事件批**應該**有這塊卻沒有 ⇒ 後端漏寫（回歸），不得顯示成「不適用」 */
  missingOnEventRun?: boolean;
}

/**
 * 由 `metadata.split_unify` 導出畫面該顯示什麼。
 *
 * 🔴 缺整塊有**兩種**情形，B4 review R1（`CODEX-R1-P2-04`）指出不能混為一談：
 *   ①**已知的全域 run**（報告有 `ic_train_test_split` 但沒有 `split_unify`）
 *     ⇒ 明說「全域 run：不適用」——這是設計上就不寫，不是遺漏；
 *   ②**舊／不完整 artifact**（連 `ic_train_test_split` 都沒有）⇒ 回 `null`，呼叫端不渲染。
 * 兩者都**不得**顯示 0：0 讀起來是「算過，結果是零個」。
 *
 * 🔴 **第三種**（閉合確認輪 `COMPOSER-R2-P2-02`；我在 N5 宣稱已處理、其實只做一半）：
 *   ③**事件批卻缺這塊**（`event_filter.label_source === 'event_label_value'`——正是後端寫
 *     `split_unify` 的同一條件）⇒ 那是**後端漏寫**，顯示琥珀警示「後端未揭露」。
 *     原本會落進①顯示「全域分析：不適用」，把後端回歸掩蓋成「設計如此」。
 */
export function splitUnifyView(
  disclosure: SplitUnifyDisclosure | undefined | null,
  options?: { hasSplitMetadata?: boolean; isEventRun?: boolean },
): SplitUnifyView | null {
  if (!disclosure) {
    if (options?.isEventRun) {
      return {
        hasCount: false,
        countText: '未揭露',
        authorityText: splitAuthorityLabel('kline_holdout'),
        reason: '事件批應有 split_unify 揭露，後端未寫入（回歸）',
        missingOnEventRun: true,
      };
    }
    if (options?.hasSplitMetadata) {
      return {
        hasCount: false,
        countText: '不適用',
        authorityText: splitAuthorityLabel('kline_holdout'),
        reason: null,
        notApplicable: true,
      };
    }
    return null;
  }
  const n = disclosure.n_test;
  const hasCount = typeof n === 'number' && Number.isFinite(n);
  return {
    hasCount,
    countText: hasCount ? String(n) : '無',
    authorityText: splitAuthorityLabel(disclosure.split_authority),
    reason: disclosure.reason ?? null,
  };
}
