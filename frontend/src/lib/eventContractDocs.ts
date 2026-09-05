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
  scenario: 'D2 分路徑鍵。決策時點恆為 t₀−k 之 open（D2-2 單一表示法）。B＝預測型（原 A 已併入；有無用未來根由 lookahead_bars_declared 之深度宣告區分，非由 scenario 值區分）。C＝確認型，語意上等於深度 0 之事件；🔴 **「收盤後才決策」（decision_at = t₀ close、事件已知可進特徵）在 D2-2 下不可表示**，殘留 G3-R13 待使用者裁定。A／B＝事件相對決策為未來 ⇒ event_known_at_decision=false。two_stage＝兩段式，深度取兩段較大者；**兩段各自之 label_value 未交付**（殘留）',
  control_kind:
    '四值閉集，四值皆 accepted。platform_same_trigger_rule 自 B3.2 起由產生器產出、過同一 validator；platform_random_bars 自 D-001 D5.1 解禁（原 rejected_with_reason.platform_random_bars=not_implemented_platform_random_bars 已移除；該 reason 字面**保留登記**於 import_failure_reasons，因其為封閉集合且 receipt_schema/reason registry 之既有前綴不得刪值）。隨機批之抽樣契約住 receipt_schema.batch.random_control_spec，由 validate_event_import 之 random_control_spec keyword 強制：批帶 platform_random_bars 而缺 spec ⇒ random_control_spec_missing；非隨機批帶 spec 或帶 label_origin=platform_random ⇒ random_control_mixed_batch',
  // ── Task 7.1（本批）：五維度接出 UI 後，另三個維度也要有白話說明；
  //    「取自契約 `doc` 欄（不另寫）」是 SPEC 明文 ⇒ 沿用同一鏡像機制，不另開第二份文案來源。
  entry_price_semantic: 'entry bar/price 唯一映射見 SPEC D1-6；事件頂層欄，不住 label_definition。default 為**前端誠實預設之唯一來源**（原檔 §F-3′；D-001 D1.1 契約字面總表／D4.2 pair 重設亦讀本值），前端禁硬編字面。🔴 validator **不讀** default：本欄仍為 required_fields，缺欄一律 missing_required_field（default 只服務 UI 之初始值與 pair 重設）',
  // `G3-D2` D4.2：契約 doc 補上成對限制之指路（鏡像逐字同步，由本檔之測試對證）。
  label_return_mode:
    'label 錨 mode-scoped 機械唯一（SPEC D1-5）；open_to_* 顯式宣告才合法（白話閘裁決②）；'
    + '與 entry_price_semantic 之成對限制見 rejected_pairs',
  decision_offset_bars:
    '決策時點＝t0 往前第 k 根錨定 TF bar 之 open；研究參數非訊號標註（白話閘裁決③）',
  // `G3-D2` D1.5：provenance 欄之白話同樣取自契約 `doc`（不另寫第二份文案來源）。
  label_origin: 'label 之 provenance（這批的答案是怎麼來的）。search_positive_case=搜尋頁匯出之正例；user_csv=使用者自標 CSV；platform_generator=平台產生器；platform_random=隨機對照組；search_unlabeled=搜尋頁之未標籤匯出（**不可匯入**，只走 two_stage 之未標籤路徑）。🔴 值屬 not_importable ⇒ label_origin_not_importable；scenario ∈ {A,B,two_stage} 而缺本欄 ⇒ conditional_required_missing。**舊批（scenario=C 且無本欄）不受條件必填約束、不補值**，讀路徑回 null',
} as const;

/** 契約檔中對應之取值路徑（供比對測試用；改欄位時兩邊一起改，測試會擋）。 */
export const EVENT_CONTRACT_DOC_PATHS: Record<keyof typeof EVENT_CONTRACT_DOCS, readonly string[]> = {
  scenario: ['required_fields', 'scenario', 'doc'],
  control_kind: ['required_fields', 'control_kind', 'doc'],
  entry_price_semantic: ['required_fields', 'entry_price_semantic', 'doc'],
  label_return_mode: ['required_fields', 'label_definition', 'fields', 'label_return_mode', 'doc'],
  decision_offset_bars: ['required_fields', 'decision_offset_bars', 'doc'],
  // 🔴 住 `optional_fields`（不是 `required_fields`）——路徑寫錯時逐字比對測試會紅。
  label_origin: ['optional_fields', 'label_origin', 'doc'],
};
