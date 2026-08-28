/**
 * GAP-3 UX Task 4.1b — 匯出面板揭露文案之**契約鏡像**。
 *
 * 🔴 **這些字串不是在這裡寫的**：它們逐字取自
 * `momentum/Analysis/contracts/event_import_contract.json` 之 `_doc` 欄。
 * 契約沒有對前端開放的端點，故沿用本 repo 既有作法（見 `eventId.ts` 之
 * `EVENT_ID_TEMPLATE` 與 `canonicalSourceCoverage.test.ts`）：
 * **前端持鏡像常數，另以 vitest 讀契約檔逐字比對**——漂移會在測試轉紅，不靠人眼同步。
 *
 * 🔴 值（本批實際的 scenario／control_kind／深度）**一律由實際設定導出**，不在本檔；
 * 本檔只有「那個值是什麼意思」的白話，這部分才是契約的。
 */

/** 契約 `_doc` 之鏡像；鍵＝契約中的欄名，值＝該欄 `doc` 逐字。 */
export const EVENT_CONTRACT_DOCS = {
  scenario: 'A/B 預測型（事件在未來、不進特徵）／C 確認型／兩段式；D2 分路徑鍵',
  control_kind:
    '四值閉集；platform_random_bars 恆拒（SPEC §N-7 解除前）；platform_same_trigger_rule 自 B3.2 起由產生器產出、過同一 validator',
  // ── Task 7.1（本批）：五維度接出 UI 後，另三個維度也要有白話說明；
  //    「取自契約 `doc` 欄（不另寫）」是 SPEC 明文 ⇒ 沿用同一鏡像機制，不另開第二份文案來源。
  entry_price_semantic: 'entry bar/price 唯一映射見 SPEC D1-6；事件頂層欄，不住 label_definition',
  label_return_mode:
    'label 錨 mode-scoped 機械唯一（SPEC D1-5）；open_to_* 顯式宣告才合法（白話閘裁決②）',
  decision_offset_bars:
    '決策時點＝t0 往前第 k 根錨定 TF bar 之 open；研究參數非訊號標註（白話閘裁決③）',
} as const;

/** 契約檔中對應之取值路徑（供比對測試用；改欄位時兩邊一起改，測試會擋）。 */
export const EVENT_CONTRACT_DOC_PATHS: Record<keyof typeof EVENT_CONTRACT_DOCS, readonly string[]> = {
  scenario: ['required_fields', 'scenario', 'doc'],
  control_kind: ['required_fields', 'control_kind', 'doc'],
  entry_price_semantic: ['required_fields', 'entry_price_semantic', 'doc'],
  label_return_mode: ['required_fields', 'label_definition', 'fields', 'label_return_mode', 'doc'],
  decision_offset_bars: ['required_fields', 'decision_offset_bars', 'doc'],
};
