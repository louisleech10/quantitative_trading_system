# Reconcile — 20260911-splitunify-b9-review-r1

**來源** 20260911-splitunify-b9-review-r1-codex.md, 20260911-splitunify-b9-review-r1-composer.md, 20260911-splitunify-b9-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

🔴 **三家全數 `blocked`**（codex 5 條 P1、composer 2 條 P1、grok 3 條 P1）。15 條歸七群，**全部採納**，
於 D-002 修訂版落實後重審。本輪**不進實作**。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| 記帳／報告鏈漏列，且 `n_train`／`n_test`／`n_purged` 在 event×TF 化後語意未定義——「15 處清單漏掉直接讀取並顯示 split count 的第 16 個 surface」／「D-002「15 處單鍵消費面」清單漏列記帳／報告鏈三處」／「D-002「15 處單鍵消費面」漏列記帳／報告鏈」 | P1 | CODEX-R1-P1-01, COMPOSER-R1-P1-01, GROK-R1-P1-01 | 採納（**三家全中**。我在 §C 寫了「事件數與列數不得混用」，卻**沒有**在 Task 9.3 指派對應修改，也沒把顯示 split count 的面列進觸及表——義務與工作項脫節。修訂：觸及面補記帳／報告／API／前端 count 面；`n_train`／`n_test`／`n_purged` 三個量逐一定義為事件數或列數並寫成驗收斷言） |
| Phase 9A 缺可執行的資料流契約，且未規定 API／前端如何揭露——「Phase 9A 的「`build_event_keys` 寫入 `EventSplitPlan.summary`」沒有可執行的資料流契約」／「Task 9.1 只列 `split_projection` 與 `EventSplitPlan.summary`，未規定 API 模型／前端型別如何揭露」／「Task 9.1 只改 `split_projection`／`EventSplitPlan.summary`，未規定 API／前端如何露出」 | P1 | CODEX-R1-P1-02, COMPOSER-R1-P2-01, GROK-R1-P2-03 | 採納（**三家全中**。9A 的目標是「消除靜默丟棄」，但我只寫到 producer 就停，沒定返回形狀、沒定跨 derive／pipeline 邊界的傳遞、沒規定使用者實際看得到的那一層 ⇒ 目標在事件批 UI 使用者面前達不成，且宣稱的「可獨立回退」無碼證。修訂：補完 9A 的資料流契約與 UI 揭露落點） |
| `timeframe` 同時承載「觸發 TF」與「feature TF」兩種語意——「D-002 的單一 `timeframe` 欄位同時碰到「觸發 TF」與「feature TF」兩種語意」 | P1 | CODEX-R1-P1-03 | 採納（**主委完全未想到**。`canonical_event_id(symbol, timeframe, t0)` 用的是**觸發** TF，而 `per_tf.timeframe` 是**feature** TF；兩者同名不同義，複合鍵、purge 換算與同簇規則都建立在它上面 ⇒ 不先命名分離，整份 SPEC 無法驗收。修訂：兩者各自具名，全檔逐處改寫） |
| Task 9.3 改法不精確：過度涵蓋 event-level 表，且漏掉真正的折疊點——「Task 9.3 的「凡 `set_index("event_id")` 改 compound/MultiIndex」過度涵蓋 event-level 表」／「Task 9.3 改法只寫「凡 `set_index("event_id")` 改 MultiIndex」，但 `feature_materialization` 的多 TF **折疊發生在** `:93` 的 `groupby("event_id")+row_vals.update`」 | P1 | CODEX-R1-P1-04, GROK-R1-P1-02 | 採納（一條指出改太多、一條指出改太少，**同一句話的兩面**：我用「凡 `set_index` 一律改」這種形狀規則取代逐處判定，既會誤改本就一事件一列的 event-level 表，又會漏掉真正折疊資料的 `groupby(...)+update`。修訂：Task 9.3 改為**逐處列名**，每處註明該處的粒度與改法） |
| §G 的 `g5` 判斷與「順道改交錯 fixture」自相矛盾——「「g5 payload 不含 timeframe、故不受影響」只足以保護現有單 TF anchor」／「§G 並陳「`g5` 不受影響」與「順道把 fixture 改為兩標的交錯（`M-SU-D1-23`）」時，未區分」 | P2 | CODEX-R1-P2-05, GROK-R1-P2-02 | 採納（兩件事被我並陳而未區分：「複合鍵不改指紋 payload」為真，但「交錯 fixture 會移動 g5 的 positions／ms／sha」也為真。修訂：§G 分別敘明，並定義多 TF 平行組中 TF 是 parent key 還是 payload 成分） |
| `M-SU-D2-01`～`06` 覆蓋不足——「M-SU-D2-01..06 的六個聚合 mutation 不足以驗證 15 個 surface」／「`M-SU-D2-01`～`06` 未覆蓋 9B 後仍會靜默錯的接線與 survivor 路徑」／「`M-SU-D2-01`～`06` 不足以覆蓋 9A／9B 靜默失效面與本輪新列之記帳／groupby／混側缺口」 | P1 | CODEX-R1-P1-06, COMPOSER-R1-P1-02, GROK-R1-P2-01 | 採納（**三家全中**。單一個 generic `set_index` mutant 不可能同時覆蓋 event-level 與 per-TF 兩種粒度，也涵蓋不到 `test_splitunify_wiring.py:103-104` 的 `dict(zip(...))` 後者覆蓋前者。修訂：mutation 逐處對應，靜默面每處各一條） |
| 同事件多 TF 未規定必須落在同一 split 側（洩漏風險）——「D-002 只規定「同事件不同 TF **同簇**」，**未**規定同事件多 TF 必須落在**同一 split 側**」 | P1 | GROK-R1-P1-03 | 採納（**主委完全未想到，且是本輪最嚴重的一條**：同簇不等於同側。1h 進 train、4h 進 test 時，仍偏事件級的消費者會把它當同一事件、靜默組成**非法 OOS 樣本**——這正是本 epic 從頭到尾要擋的東西。修訂：D-002 須明定「同事件之所有 TF 必須同側，否則整事件 purge」並配可證偽測試） |

## 主委自評（如實記）

本輪三家全數 `blocked`，15 條全部採納、零駁回。其中**兩條是我完全沒想到的**：
`timeframe` 的雙語意（觸發 TF vs feature TF）、以及同事件多 TF 的**同側**約束。
後者是洩漏級缺口——我只想到「同簇」，沒想到「同簇但異側」照樣會組出非法 OOS 樣本。
另有一條（記帳分母）是我**自己寫了義務卻沒指派工作項**，屬於 SPEC 內部不自洽。

## 誠實邊界

D-002 為規格階段產物，本輪**無實作、無數值影響**。IC 端到端真實 run 仍未跑。

Verdict: 需修補後合併（D-002 依本收斂修訂後重審；三家之 blocked 於修訂版重審通過後解除）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: 15 處清單漏掉直接讀取並顯示 split count 的第 16 個 surface，且沒有定義 `n_train`／`n_test`／`n_purged` 在 event×TF 化後仍是事件數還是列數；這會讓 API/前端靜默展示錯誤分母。

**碼證**: `frontend/src/components/ic-analysis/EventTablesPanel.tsx:347-362` 直接讀 `resp.summary` 並顯示 `n_train/n_test/n_purged`，但 D-002 #14 只列 batch_facts 與 search `byEventId`。`api/services/case_import_service.py:1626-1628` 將 `res.summary` 原樣放入 response，`api/models/event_import_models.py:306-310` 以 `Dict[str, Any]` 接收，沒有另一個 schema gate。現行 pipeline `momentum/Analysis/event_samples/pipeline.py:760-762` 對 assignment/purge 做 `len`；實測 2 events×2 TF 為 `two_tf_row_count=4 unique_events=2`。現有 API 測試也明確把 `test_rows`（K 線列數）與 `n_test`（事件數）分開：`tests/api/test_splitunify_disclosure.py:282-300`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/Analysis/event_samples/pipeline.py#55ca7327764f; api/services/case_import_service.py#d2571793953f; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a; tests/api/test_splitunify_disclosure.py#f1bd211204f7

失效／修復／信心：多 TF 後前端可能把 4 個 event-TF rows 顯示成 4 個 test events，或新增欄位卻讓舊欄位語意漂移；修復需把此 panel、response contract、測試納入 touch surface，並明定舊欄位維持 event semantics 或新增成對的 `*_events`／`*_event_tf_rows` 欄位；可行性高，屬局部 contract/consumer 修正；信心高。

## CODEX-R1-P1-02

**斷言**: Phase 9A 的「`build_event_keys` 寫入 `EventSplitPlan.summary`」沒有可執行的資料流契約；若只在 producer 計算而不明定返回形狀，discard summary 會在 derive/pipeline 邊界遺失，9A 也無法按宣告獨立回退。

**碼證**: `momentum/Analysis/event_samples/split_projection.py:256-260,274-303` 的 signature/return annotation 是 `-> pd.DataFrame`，函式只回 event-key DataFrame；`pipeline.py:745-752` 將其 inline 傳入 `derive_event_split_from_plans`，沒有接收 summary。`split_projection.py:684-734` 的 `_build_summary` 現行固定 12 keys，`pipeline.py:757-763` 才在之後另組外層 summary。既有 `tests/momentum/Analysis/test_splitunify_derive.py:594-610` 精確斷言 12-key 集合，因此任意新增欄位、tuple 回傳或 side-channel 都會改變既有契約。SPEC Task 9.1 只寫 producer「寫入 summary」，未指定 result object、tuple、callback 或 owner。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/event_samples/pipeline.py#55ca7327764f; tests/momentum/Analysis/test_splitunify_derive.py#cbcd20a668e3

失效／修復／信心：若實作者採 tuple 但 caller 仍按 DataFrame 使用，會直接破壞 pipeline；若用未宣告的屬性/全域 side-channel，summary 可能未進 `EventSplitPlan` 或 API。修復需先定一個明確結果契約（例如 result dataclass 含 event_keys 與 discarded map），由唯一 caller 接到 `_build_summary` 並更新 exact-key/rollback 測試；可行性高但需先裁定 API，信心高。

## CODEX-R1-P1-03

**斷言**: D-002 的單一 `timeframe` 欄位同時碰到「觸發 TF」與「feature TF」兩種語意；若未先命名分開，複合鍵、purge 換算與 cluster 同簇規則無法被驗收。

**碼證**: `momentum/Analysis/event_samples/keys.py:18-19,97-102` 明定 event record 的 `timeframe` 是觸發 TF，且不同於 `per_tf` 的 feature TF。現行 `build_event_keys` 在 `split_projection.py:279-301` 以 `per_tf.timeframe` 選 cutoff，卻把 `event_level.timeframe` 放入輸出；因此直接把該欄複製到 assignments 會讓不同 feature TF 的 row 看成同一 TF，直接採 per_tf 欄又需要重新定義 cluster table 的 event-level 粒度。實跑 cluster probe 以不同觸發 ID/間隔輸出 `time_cluster_id=[0,4]`；沒有合法的「同一 event 但應不同 cluster」反例，因為同一 event 的不同 feature TF 應同簇。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/Analysis/event_samples/keys.py#18daa670b6e2; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/event_samples/event_split.py#943d0721b059

失效／修復／信心：欄位誤接會造成 `(event_id,timeframe)` 不是真正的 per-TF key，或把同一事件拆成多簇而稀釋 effective event count；修復需在 SPEC/schema 明定 `trigger_timeframe` 與 `feature_timeframe` 的 owner，cluster 只在 event-level key 上計算，再由 consumer 使用明確的 compound key；可行性中等，需先裁定語意；信心高。

## CODEX-R1-P1-04

**斷言**: Task 9.3 的「凡 `set_index("event_id")` 改 compound/MultiIndex」過度涵蓋 event-level 表，會把本來一事件一列的資料與 per-TF 表混為同一粒度；直接套用會破壞 scalar lookup 與既有輸出 schema。

**碼證**: `feature_materialization.py:42,93-132` 明確以 event_id 分組、每事件合併多個 TF feature、最後輸出 `features_at_decision[index=event_id]`；`counterexample_classifier.py:52,62` 與 `candidate_ledger.py:155,160` 讀 `receipts.event_level` 後以 `.loc[eid]` 取 scalar；`tables.py:214,229,234` 同樣用 event-level receipt/cluster lookup。實測把兩列 MultiIndex 後做 `x.loc["ev0"]` 得 DataFrame、`y["t0_ms"]` 得 Series，`int(...)` 直接輸出 `TypeError: cannot convert the series to <class 'int'>`。這些不是同一個 per_tf consumer，不能用一個全域替換解決。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2; momentum/Analysis/event_samples/counterexample_classifier.py#444599323e49; momentum/Analysis/event_samples/candidate_ledger.py#b75159633935; momentum/Analysis/event_samples/tables.py#843ba7f68172

失效／修復／信心：部分路徑會 loud 失敗，部分路徑則拿到 Series 後在條件/轉型處產生錯誤或錯綁；修復需按資料粒度分流：只有 assignment/purged/per_tf-derived 表使用 `(event_id, feature_timeframe)`，event_level、features_at_decision、labels、事件報表維持 event_id 並加唯一性 assertion；可行性高，信心高。

## CODEX-R1-P2-05

**斷言**: 「g5 payload 不含 timeframe、故不受影響」只足以保護現有單 TF anchor，不能證明新增 multi-TF parallel group 能辨認 TF；SPEC 沒有定義 TF 是 parent key 還是 fingerprint payload 的成分。

**碼證**: `momentum/core/split_preview.py:146-176` 的 producer 參數只有 `positions/feature_ts_ms/symbol/base_universe_hash`，payload 固定四欄，沒有 timeframe。`tests/momentum/Analysis/test_splitunify_golden.py:66-89` 與 `scripts/freeze_splitunify_golden.py:170-203` 目前只凍結單一 1h fixture。實跑同一組 positions/timestamps/symbol/hash 在不同語意 TF 標籤下只能得到同一 digest（`g5_payload_same_for_semantic_tf_labels=True`），因函式根本沒有 TF 參數。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/core/split_preview.py#95a85ec0de54; scripts/freeze_splitunify_golden.py#e331623163d2; tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e

失效／修復／信心：若兩個 feature-TF runs 共享 row grid 與 base hash，交換 TF 仍可重用相同 g5，multi-TF golden 會假綠；修復可選擇明定 g5 是 row-universe identity 並把 `(symbol, feature_timeframe, base_hash)` 放在外層 golden key，或在新 multi-TF fingerprint 加 TF 同時保留舊單 TF anchor；可行性中等，需裁定 g5 identity；信心中高。

## CODEX-R1-P1-06

**斷言**: M-SU-D2-01..06 的六個聚合 mutation 不足以驗證 15 個 surface、額外的 EventTablesPanel/count path、9A summary propagation，以及 g5 的多 TF keying；尤其一個 generic `set_index` mutant 不能同時覆蓋 event-level 與 per-TF 分支。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:125-131` 只列 6 個 mutation；對 exact IDs 執行 `rg -n 'M-SU-D2-[0-9]{2}' docs/SPLITUNIFY_SPEC.D-002.md tests momentum api frontend scripts` 未找到測試對應項。現行 source scan 找到 14 個 Python 檔含 `set_index("event_id")`（其中 8 個在 event-sample production/tests 以不同粒度使用），且 count pattern 掃描跨 API、frontend、momentum、tests；現有 baseline suite 雖然通過，沒有 D2-specific named mutant。Task 9.3 自己要求每一處 consumer 有改壞即紅，與目前六項不等價。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32; momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2; momentum/Analysis/event_samples/ic_feed.py#741f697b3964; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a; tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e

失效／修復／信心：summary 不傳遞、表格取錯值、dedupe 折 TF、UI key 覆蓋、n_events 取列數、golden set 去重等錯誤可能互相獨立而被聚合 mutation 掩蓋；修復需按 surface 增加可觀測 mutation（至少 9A propagation、5/7/8/9/10/11/12/14、EventTablesPanel count、g5 multi-TF），每條都實跑 baseline→mutant red；可行性中等，信心高。

## COMPOSER-R1-P1-01

**斷言**: D-002「15 處單鍵消費面」清單漏列記帳／報告鏈三處；9B 落地後 `n_train`/`n_test`/`n_purged` 將變成 (event,TF) **列數**卻仍被當**事件數**顯示與斷言，與 §C「不得混用」直接衝突且 Task 9.3 未指派修改。

**碼證**: `pipeline.py:758-762` `n_train`/`n_test`/`n_purged` 皆對 `plan.assignments`/`purged` **行數**求和；`EventTablesPanel.tsx:356-361` 無單位地顯示三數；`test_splitunify_wiring.py:113` `assert res.summary["n_train"]+...+== len(records)`。VERIFY 探針：2 事件×2 TF ⇒ `records=2 assignment_rows=4 wiring_assert_would_fail False`。RECHECK: 重跑上述 python 片段＋讀三處行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。Task 9.x 實作若只改 15 處表，pipeline 摘要與前端事件表仍會把列數當事件數——使用者看到 train/test 數字膨脹一倍而無標註。**修法**：觸及面表增第四層「記帳／報告」三行；Task 9.2 同時提供 `n_event_tf_rows` 與事件級 `n_events`，Task 9.3/9.4 改 `pipeline._base_summary` 鍵名或加 `_rows` 後綴＋前端 `MetricLabel` 標單位；`test_splitunify_wiring.py:113` 改為對 `n_events` 或複合鍵列數斷言。**可行性**：`EventTablesPanel` 已有 `MetricLabel` 模式；pipeline summary 為 dict 可加鍵不破舊 API（新鍵必填、舊鍵標 deprecated 一個 phase）。

## COMPOSER-R1-P1-02

**斷言**: `M-SU-D2-01`～`06` 未覆蓋 9B 後仍會靜默錯的接線與 survivor 路徑；尤其 `test_splitunify_wiring.py:103-104` 以 `dict(zip(event_id,...))` 對 cutoff／split_label 建映射，同 `event_id` 多 TF 時後者覆蓋前者，mutation 無對應項。

**碼證**: `test_splitunify_wiring.py:103-104` `cutoffs=dict(zip(per_tf event_id,...))`、`labels=dict(zip(assignments event_id,...))`；觸及面 #13 `ic_feed.py:142-145` survivor `manifest_hash` 仍按排序後 `event_id` 列雜湊，多 TF manifest 語意會變但無 `M-SU-D2-*`。§V mutation 僅列 `01`～`06`（`docs/SPLITUNIFY_SPEC.D-002.md:131`）。RECHECK: 讀 wiring 103-104 與 §V 表；對 #13 構造雙 TF 同 event 之 hash 前後對照（實作前標 needs-research）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617;momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[BLOCKING] 信心度=High。實作者照 §V 做完 6 條 mutation 自證即可標綠，但 wiring 接線與 IC survivor hash 仍可靜默錯／假綠。**修法**：增 `M-SU-D2-07`（wiring dict-zip 改回單鍵應紅 `test_splitunify_wiring`）、`M-SU-D2-08`（`pipeline` 用列數填 `n_train` 應紅記帳測試）、`M-SU-D2-09`（`ic_feed` survivor hash 改回 event_id-only 應紅 conditional_ic 契約測試）；各指名應紅測試名。**可行性**：b8 已有 22 條 `M-SU-D1-*` 自證先例；wiring 測試已存在，mutation 只需改一行 zip 邏輯即可觸發。

## COMPOSER-R1-P2-01

**斷言**: Task 9.1 只列 `split_projection` 與 `EventSplitPlan.summary`，未規定 API 模型／前端型別如何揭露 `discarded_per_tf_rows_by_timeframe`，9A「消除靜默丟棄」在目標使用者（事件批 UI）可能達不成。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:103-107` Task 9.1 檔案清單無 `api/`／`frontend/`；`EventTablesPanel.tsx` 現只顯示 `n_train`/`n_test`/`n_purged`（`:356-361`），無 discarded 欄位；`frontend/src/lib/types.ts` 之 event summary 型別亦無該鍵（grep 0 命中）。RECHECK: `rg discarded_per_tf` 全 repo 僅 D-002 規格檔。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[MAJOR] 信心度=High。9A 合併後 momentum 有欄、API 未透傳 ⇒ 產品層仍靜默。**修法**：Task 9.1 增子任務——`api/models`＋event pipeline 回傳 summary 透傳該鍵；`types.ts`＋`EventTablesPanel` 或 `EventBatchDisclosurePanel` 顯示「未選 TF 丟棄 N 列（按 TF 分組）」；驗收加 API test 斷言 JSON 含鍵。**可行性**：`tests/api/test_splitunify_disclosure.py` 已有 split_unify 揭露測試骨架，可平行加 case。

## GROK-R1-P1-01

**斷言**: D-002「15 處單鍵消費面」漏列記帳／報告鏈；9B 後 `pipeline` 的 `n_train`／`n_test`／`n_purged` 會變成 (event,TF) 列數，卻仍被前端與 wiring 測試當事件數使用，與 §C「不得混用」衝突且 Task 9.3 未指派修改。

**碼證**: `pipeline.py:760-762` 對 `plan.assignments`／`purged` 列數求和；`EventTablesPanel.tsx:361` 無單位顯示三數；`test_splitunify_wiring.py:113` 斷言三數之和＝`len(records)`。VERIFY 探針：`PIPELINE_MIXUP {'n_train': 2, 'n_test': 2, 'n_events': 2, 'records': 2, 'wiring_eq': False, 'row_sum': 4}`。RECHECK: 讀三處行號＋重跑同形探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617

[BLOCKING] 信心度=High。實作者若只改 15 處表，摘要與 UI 會把事件數膨脹為 pair 列數且無標註。**修法**：觸及面增「第四層—記帳／報告」列 `pipeline.py:760-762`、`EventTablesPanel.tsx`、`test_splitunify_wiring.py:113`；Task 9.2 讓 pipeline summary **同時**寫事件級計數與 `n_event_tf_rows`（或 `n_train_rows` 後綴），禁止再用裸 `n_train` 表示列數；前端加單位；wiring 斷言改對事件級或明示列級。**可行性**：summary 已是 `Dict`（`EventAnalyzeResponse.summary`），加鍵不破既有 Pydantic；`EventTablesPanel` 已有 `MetricLabel` 可標單位；wiring 測試改一行等式即可。

---

## GROK-R1-P1-02

**斷言**: Task 9.3 改法只寫「凡 `set_index("event_id")` 改 MultiIndex」，但 `feature_materialization` 的多 TF **折疊發生在** `:93` 的 `groupby("event_id")+row_vals.update`；只改 `:132` 的 `set_index` 仍會先併成一列，靜默面 #5 假修。

**碼證**: `feature_materialization.py:93-130` 按 `event_id` groupby 後 `row_vals.update`，`:132` 才 `set_index("event_id")`；D-002 觸及面 #5 與 Task 9.3 改法均只提 `set_index`。VERIFY：兩列同 eid 異 TF → `GROUPBY_FOLD_NROWS 1`；對 raw 直接 `set_index` → `n=2 unique?=False`（證明折疊在 groupby，不在 set_index）。RECHECK: 讀 `:93-132`＋重跑 groupby 探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。Agent 依字面改 `set_index` 並加「索引唯一」斷言時，groupby 已輸出一列／事件 ⇒ 斷言仍綠、多 TF 特徵列仍消失。**修法**：Task 9.3／觸及面 #5 明示必須拆掉（或改寫）`groupby("event_id")` 折疊，改為每 `(event_id, timeframe)` 一列後再 MultiIndex；§V 對 #5 的「改壞就要變紅」測試須斷言 **列數＝pair 數**（不只 index 唯一）。**可行性**：函式已逐 `per_tf` record 取列（`:96-126`），去掉 groupby 外殼改 append `(eid, tf)` 即可；記帳守恆 `:137-139` 改比對 `len(per_tf)` 而非 `nunique(event_id)`。

---

## GROK-R1-P1-03

**斷言**: D-002 只規定「同事件不同 TF **同簇**」，**未**規定同事件多 TF 必須落在**同一 split 側**（或混側整事件 purge／fail-closed）；9B 放行 pair assignments 後，1h=train／4h=test 會讓仍偏事件級的消費者靜默組成非法 OOS 樣本。

**碼證**: D-002 Task 9.3 僅有同簇句（約 L119）；全文無「混側／同側／同一 split_label」約束（本輪 `SPEC_HAS_MIXED_SIDE_RULE False`）。上游偵察 `CODEX-R1-P1-02` 已指出混側不可證，synth 採納時偏重 schema／列數誠實性，**混側契約未寫入 D-002**。探針：同事件異 TF 異 `split_label` 仍同 `time_cluster_id`——同簇**不能**代替同側。RECHECK: `grep -n '混側\|同側\|split_label' docs/SPLITUNIFY_SPEC.D-002.md`；構造 1h train／4h test fixture 餵 baseline／`test_ids` 交集。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md#2ac4e7432169;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。缺此契約時，實作者可「合法」產出混側 pair 列；`baseline`／`tables` 的 `test_ids = assignments…event_id` 會把該事件當 test，train 側 TF 特徵被吃掉或交錯——不 raise。**修法**：在 D-002-C1／Task 9.2 或 9.3 加硬規則——同一 `event_id` 之所有生效 TF **必須**同一 `split_label`；若 cutoff 落在不同段 ⇒ 整事件 purge（具名 reason）或 fail-closed；並加 §V 斷言＋`M-SU-D2-xx`（混側未擋應紅）。**可行性**：投影迴圈已逐事件看 cutoff∈train_ms／test_ms（`split_projection.py` 成員判定）；改為「同事件多 TF 先收集 label 再一致化／purge」不需新架構；b8 已有 purge reason 字串先例。

---

## GROK-R1-P2-01

**斷言**: `M-SU-D2-01`～`06` 不足以覆蓋 9A／9B 靜默失效面與本輪新列之記帳／groupby／混側缺口；`02` 單條 set_index mutation 無法代替靜默面 5／7／8／9／11／12 的逐處值斷言。

**碼證**: D-002 §V L131 僅列 01–06；靜默面清單在 §C／觸及面；wiring `dict(zip)`（`:103-104`）與 pipeline 記帳無對應 M-SU-D2；無混側、無 groupby 折疊 mutation。RECHECK: 對照 §V 與觸及面靜默項逐條打勾。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617

[MAJOR] 信心度=High。照表做完 6 條 mutation 自證仍可能假綠。**修法**：至少增——`07` pipeline 用列數填事件級 `n_train` 應紅；`08` wiring `dict(zip(event_id))` 應紅；`09` materialize 保留 groupby 折疊應紅（列數≠pair）；`10` 混側未 purge 應紅；`11` #13 survivor 仍只按 `event_id` 雜湊應紅；並要求 01–06 各**指名**應紅測試。靜默面每項保留 Task 9.3 的值斷言（不得只「不報錯」）。

---

## GROK-R1-P2-02

**斷言**: §G 並陳「`g5` 不受影響」與「順道把 fixture 改為兩標的交錯（`M-SU-D1-23`）」時，未區分「複合鍵不改指紋 payload」與「交錯 fixture 會移動 g5 positions／ms／sha」；Agent 可能誤刪單標的錨或拒絕對 g5 做必要重凍。

**碼證**: D-002 §G L95–97；`freeze_splitunify_golden.py` 現為單標的、`row_index_local` 逐值等於 `row_index`；`build_row_time_fingerprint` 含 `positions`＋`feature_ts_ms`——交錯兩標的必改 positions／ms。本輪 `G5_SAME True` 且源碼無 `timeframe` ⇒ 複合鍵公式面成立。RECHECK: 讀 §G 兩句＋`freeze_splitunify_golden.py` 單標的假設註解。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/core/split_preview.py#95a85ec0de54;scripts/freeze_splitunify_golden.py#e331623163d2

[MAJOR] 信心度=High。**修法**：§G 改寫為兩句——①複合鍵**不**改 g5 payload 欄位／算法；②`M-SU-D1-23` 之交錯 fixture 為**新增**平行組（或具名重凍），單標的單 TF 之 g5 舊值保留為回歸錨，不得覆蓋刪除。Task 9.4 ASSERT 與此對齊。

---

## GROK-R1-P2-03

**斷言**: Task 9.1 只改 `split_projection`／`EventSplitPlan.summary`，未規定 API／前端如何露出 `discarded_per_tf_rows_by_timeframe`；9A「消除靜默丟棄的誠實性缺陷」對事件批 UI 使用者可能達不成。

**碼證**: D-002 L103-107 檔案清單無 `api/`／`frontend/`；`rg discarded_per_tf` 全 repo 僅 D-002；`EventTablesPanel` 現只渲 `n_train`／`n_test`／`n_purged`。pipeline `:759` 雖會把 plan.summary 鍵拷進 response，但無型別／UI 契約。RECHECK: `rg discarded_per_tf`；讀 Task 9.1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[MAJOR] 信心度=Medium（若產品接受「僅 API JSON 即算揭露」可降 NON-BLOCKING；SPEC 自述目標含消除誠實性缺陷）。**修法**：Task 9.1 增 API 透傳＋`types.ts`＋面板一行「未選 TF 丟棄：{…}」；驗收加 API／元件測試。**可行性**：`tests/api/test_splitunify_disclosure.py` 已有揭露測試骨架可平行加 case。

---

