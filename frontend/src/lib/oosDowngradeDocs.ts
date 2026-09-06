/**
 * `metadata.oos_downgrade.reason` 的**逐條白話**——單一來源。
 *
 * ## 出生事故（`CODEX-R2-P1-06`，2026-09-06 R2）
 *
 * R1 我補了一段「這條路徑沒有列數可報」的文案，內文寫死一句
 * 「它代表本次分析**沒有保留獨立的測試集**」。那句話對 `event_filter_fallback`
 * 是**假的**——`_downgrade_branch` 先看 event fallback 才看 split，
 * 而 `ICConfig.ic_train_test_split` 預設為 `true`，
 * 所以那條路可以「事件樣本不足退回全樣本」**且同時有已套用的 holdout**。
 * 使用者照那句話會去建測試集，真正缺的卻是事件樣本。
 *
 * ⇒ 文案**必須依 reason 分流**，且每句只陳述該 reason 真正蘊含的事。
 *
 * ## fail-closed
 *
 * 認不得的 reason **不猜**：`REASON_UNKNOWN_FALLBACK` 只說「降級了、原因碼是 X」，
 * 不替它編一套解釋。後端新增 reason 時畫面會退化成保守敘述，而不是說錯話。
 * 鍵集與後端 `_downgrade_branch` 之回傳值由 `oosDowngradeDocs.test.ts` 機械對證。
 */

export interface OosDowngradeDoc {
  /** 這個 reason 實際代表什麼（只講 metadata 已證實的事）。 */
  what: string;
  /** 使用者要怎麼做才可能拿回 OOS 保證。 */
  next: string;
}

/** 後端 `_downgrade_branch` 之五個回傳值 ＋ full-sample fallback 之兩個 reason。 */
export const OOS_DOWNGRADE_DOCS: Record<string, OosDowngradeDoc> = {
  event_filter_fallback: {
    what:
      '事件樣本不足，已退回全樣本分析——你看到的不是事件條件下的結果。'
      + '🔴 這條路徑「有沒有獨立測試集」是另一回事：切分可能照常跑過，'
      + '降級的原因是事件條件沒有生效，不是缺 holdout。',
    next: '要拿回事件條件下的結果，得增加符合條件的事件筆數，或放寬事件定義；建測試集不會解決這條。',
  },
  rolling_warmup_insufficient: {
    what: '切分後測試集的列數不足以跑滾動 IC（滾動窗要先吃掉一段暖身期，剩下的才算得出值）。',
    next: '要讓測試集的列數過門檻——加長資料期間，或縮小滾動窗。列數不等於事件數。',
  },
  insufficient_data: {
    what: '資料列數太少，切分本身跑不起來。',
    next: '加長資料期間或降低取樣頻率（例如 1h 改 15m），讓總列數足以切分。',
  },
  fit_mode_full_sample: {
    what: '設定裡直接指定了全樣本擬合（`fit_mode=full_sample`）——這是請求的結果，不是資料不足。',
    next: '把 `fit_mode` 改回 PIT／expanding，就會恢復 OOS 保證。',
  },
  split_not_applied: {
    what: '請求了訓練／測試切分，但實際上沒有套用。',
    next: '看 `metadata.ic_train_test_split.reason` 找出被擋下的原因，那裡有具體的失敗理由。',
  },
  meta_oos_guarantees_false: {
    what: '這份報告的 metadata 明確標記 `oos_guarantees=false`。',
    next: '這是上游已下的結論；請看同一份 metadata 裡的切分與擬合欄位找出是哪一步造成的。',
  },
  no_holdout_evidence: {
    what: '報告裡找不到任何「保留了獨立測試集」的證據——沒有切分紀錄，也沒有 OOS 標記。',
    next: '開啟 `ic_train_test_split` 重跑；在那之前這份結果只能當研究用。',
  },
};

/** 認不得的 reason：只承認降級，不編解釋。 */
export const REASON_UNKNOWN_FALLBACK: OosDowngradeDoc = {
  what: '本次分析被降級，但這個原因碼是畫面還不認得的（後端新增了 reason）。',
  next: '請把上面的原因碼回報；在畫面補上說明之前，這份結果一律不可當 out-of-sample 使用。',
};

export function oosDowngradeDoc(reason: string | null | undefined): OosDowngradeDoc {
  if (!reason) return REASON_UNKNOWN_FALLBACK;
  return OOS_DOWNGRADE_DOCS[reason] ?? REASON_UNKNOWN_FALLBACK;
}

export const OOS_DOWNGRADE_REASON_KEYS = Object.keys(OOS_DOWNGRADE_DOCS);
