# Reconcile — 20260911-splitunify-b9-consult-r1

**來源** 20260911-splitunify-b9-consult-r1-codex.md, 20260911-splitunify-b9-consult-r1-composer.md, 20260911-splitunify-b9-consult-r1-grok.md, 20260911-splitunify-b9-consult-r1-claude.md　|　**roster** claude,codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

🔴 本輪為**偵察**，findings 是 b9 SPEC 的**輸入**而非待修缺陷；處置一律為「採納（寫入 b9 SPEC）」，
唯一例外是 W1 之揭露修補可先行。四家（含主委自產）共 18 條，歸為六群。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| 跨 TF 並非 fail-closed，未選中的 TF 被靜默丟棄——「多 TF 同批時，未被 `selected_timeframe` 選中的 `per_tf` 列被**靜默丟棄**」／「現行 `receipts.per_tf → build_event_keys` 路徑沒有對「同一批含不同 timeframe」fail-closed」／「「未完成前多 TF 同批維持 fail-closed」若讀成「凡 `per_tf` 出現多個 timeframe 就擋」則為假」／「現行 fail-closed 只保證「selected timeframe 下每 event 一列 per_tf」」 | P1 | CODEX-R1-P1-01, GROK-R1-P1-03, COMPOSER-R1-P2-01 | 採納（**三家委員獨立命中同一件事，主委自產亦獨立命中**（`CLAUDE-R1-P1-01`，全文見 `handoffs/20260911-splitunify-b9-consult-r1-claude.md`；🔴 主委非受派家族，依使用者 2026-09-12 裁定**不進本收斂之 roster 與 sources**，僅以敘述引用）：主委探針 C 情形與 codex Probe A 逐值一致——4 列輸入、2 列輸出、`UNSELECTED_ROWS_DROPPED 2`。⇒ D-001 第 11／189 行「未完成前多 TF 同批維持 fail-closed」**與實況不符**，該句須在 b9 SPEC 更正。**揭露修補可先行**：在複合鍵落地前，至少讓 `build_event_keys` 把丟棄列數寫進 summary，不得無聲） |
| D-001 所列六個下游單鍵面不是完整集合——「D-001 所列六檔不是 `event_id` 單鍵消費面的全集」／「D-001 列的六個下游單鍵面**不是**完整消費面」 | P1 | COMPOSER-R1-P1-01, GROK-R1-P1-02 | 採納（合併四家盤點後約 15 處：D-001 六處＋`counterexample_classifier`／`candidate_ledger`／`event_split.build_time_clusters`／`ic_feed` survivor 六鍵／`split_projection` producer 端／`frontend/src/lib/types.ts`／`tests/golden/splitunify/splitunify_golden.json`，另主委自產補 `frontend/src/app/search/page.tsx:825-835`（以 event_id 為鍵之 Map，後者覆蓋前者）與 `tests/golden/splitunify/clusters_oracle.json`。⇒ b9 SPEC **不得沿用那六處**，須以本盤點重寫觸及面） |
| 複合鍵必須改 schema，且事件數會被誤報成 pair 列數——「複合鍵無法在「不動 `EventSplitPlan.assignments`／`clusters` schema」的前提下落地」／「b9 若把 split 結果直接展開成每 `(event_id,timeframe)` 一列，會與目前 event-level 特徵／標籤／統計鏈衝突」／「SU-RESID-2 必改 `EventSplitPlan.assignments`/`purged`/`clusters` schema」 | P1 | GROK-R1-P1-01, CODEX-R1-P1-02, COMPOSER-R1-P2-02 | 採納（`assignments`／`purged`／`clusters` 至少加 `timeframe`；`receipts.per_tf` 本就是該粒度、不必改。🔴 codex 另指出一條**誠實性**風險：pipeline／API／前端會把 pair 列數誤報成事件數——b9 SPEC 須明定「事件數」與「(事件,TF) 列數」是兩個量，報告不得混用） |
| 物化與 dedupe 會靜默折疊多 TF——「`feature_materialization` 在複合鍵下會**靜默**丟列」／「`dedupe` 的 `cluster_first` 會在複合鍵下**靜默折掉**同 event 的不同 TF」／「複合鍵落地後若未改 `feature_materialization` 的 `groupby("event_id")`＋`row_vals.update` 折疊語意」／「dedupe cluster 折疊在複合鍵下應保持 event 級」／「同一經濟事件的不同 feature TF 應共享一個事件級 time cluster」 | P1 | COMPOSER-R1-P1-02, COMPOSER-R1-P1-03, GROK-R1-P2-01, GROK-R1-P2-02, CODEX-R1-P2-03 | 採納（四家對 cluster 語意**立場一致**：時間簇按事件級 interval 合併，同一事件的不同 TF 同簇，否則等於把同一事件當多個獨立觀測、稀釋 `n_events_effective`。但 `cluster_first` 的**保留集**須改為 `(event_id, timeframe)` 粒度，否則會折掉 TF——此細節由 composer 提出，主委自產未想到，如實記錄） |
| golden 與測試只覆蓋單一 TF，多 TF 回歸會被只跑單 TF 的測試掩蓋——「現有 splitunify golden 與 wiring tests 只覆蓋單一 timeframe」／「`g1_membership`／`g3b_oracle`／`g5_answer_window` 若在複合鍵落地後仍以 event_id 字串清單比對」／「SU-RESID-2 不必重算全部 splitunify golden，但 **g1/g3b 必擴維或新增 multi-TF 組**」 | P2 | CODEX-R1-P2-04, GROK-R1-P2-03, COMPOSER-R1-P2-03 | 採納（三家一致：不必全部重算，但 `g1_membership`／`g3b_oracle` 必須擴維或新增 multi-TF 組；`g5` 指紋 payload 無 timeframe，不受影響。🔴 這正是 `M-SU-D1-23` 等待的時機——b9 既然必然動 golden，順道把 fixture 改成兩標的交錯使該 mutation 可觸發） |
| `ic_feed` 過濾本身不是主風險——「`ic_feed.build_event_ic_inputs` 已按 `timeframe` 過濾 `per_tf`（`:109`），表格鏈 IC 消費端在**單一 anchor TF** 下語意正確」 | P3 | COMPOSER-R1-P3-01 | 採納（縮小 b9 風險面：`ic_feed` 的過濾邏輯本身正確，主風險在物化／dedupe／assignments） |

## 主委自產的獨立貢獻與漏項（如實記）

**自產抓到而三家未列**：`frontend/src/app/search/page.tsx:825-835` 的 event_id Map 覆蓋、
`tests/golden/splitunify/clusters_oracle.json`。
🔴 **自產漏掉而委員抓到**：①`feature_materialization:132` 的 `set_index` **靜默**只留最後一列
（我誤判成只會 loud 報錯）②`cluster_first` 保留集的粒度問題 ③事件數被誤報成 pair 列數的誠實性風險。

## 家族裁決

| 家族 | VERDICT | 說明 |
|---|---|---|
| claude（自產） | proceed | 偵察完成，一條 P1 |
| composer | proceed | 三條 BLOCKING P1，皆為 b9 SPEC 輸入 |
| grok | proceed | 三條 P1、三條 P2 |
| codex | **blocked** | `BLOCKED-BY: CODEX-R1-P1-01, CODEX-R1-P1-02` —— 語意為「不得就現況直接進 b9 實作」，與偵察輪目的一致；於 b9 SPEC 依本收斂定案後解除 |

## roster 與 sources 的區分（避免後人誤以為漏了一家）

`sources.lock` 的 `expected_roster` 為**三家委員**（codex／composer／grok），因為 roster 的語意是
「本輪**受派**的家族」，而主委不是受派方；但 `sources` 陣列**含四份**，因為主委自產版
（`-claude.md`）確實被納入本次收斂並逐條歸戶。兩者語意不同，不是漏列。

## 誠實邊界

IC 端到端真實 run **未跑**（四家皆同此限縮）。`api/services/` 未逐檔讀，僅型樣 grep。

Verdict: 需修補後合併（b9 SPEC 須依本收斂重寫觸及面與範圍；codex 之 blocked 於 SPEC 定案後解除）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: 現行 `receipts.per_tf → build_event_keys` 路徑沒有對「同一批含不同 timeframe」fail-closed；它會在 selected-timeframe filter 後靜默遺失未選 TF，故 D-001 所述的多 TF fail-closed 並未在實際 producer 邊界成立。

**碼證**: `split_projection.py:256-303` 先以 `per_tf["timeframe"] == selected_timeframe` 篩選，再對篩後資料做 duplicate check 與 merge。實跑探針 stdout：`input_per_tf_rows 4 output_rows 2 output_timeframes ['1h'] output_ids ['e1', 'e2']`、`UNSELECTED_ROWS_DROPPED 2`。同一檔未來 pair rows 直接進 derive 則 stdout：`ValueError: ... event_keys 之 event_id 重複 ['ev-mtf']...`，顯示目前是 producer 靜默丟列、projection 只接受 event-level 唯一性的兩段形狀。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f; docs/SPLITUNIFY_TODO.md#e44da6448b01

[BLOCKING] 信心度=High。失敗是使用者餵入多 TF 後只得到 selected TF 的分析，且沒有 receipt/summary 說明被丟掉的列；這不是可接受的「多 TF 已被擋下」。修法需二選一並寫入 b9 契約：在 pair-aware 實作完成前，producer 於 filter 前明確拒絕並列出未選 TF；或定義 pair-keyed event input 後一路完成 fold/consumer 遷移。不能只移除 duplicate guard。RECHECK: 重跑同一 producer probe，並加上「未選 TF 存在時必須 raise 或完整輸出 pair rows」的執行期斷言。

## CODEX-R1-P1-02

**斷言**: b9 若把 split 結果直接展開成每 `(event_id,timeframe)` 一列，會與目前 event-level 特徵／標籤／統計鏈衝突；若事件的不同 TF 落在不同 split，現有下游沒有可證明安全的單一事件歸屬，pipeline/API/frontend 還會把 pair row 數誤報成事件數。

**碼證**: `types.py:87-92` 的 `EventSplitPlan` 只有 DataFrame 容器；`split_projection.py:545-556` 產出 `assignments=[event_id,symbol,split_label]`、`purged=[event_id,reason]`，且 `:438-445` 以 event_id duplicate 為 hard guard。另一方面，`feature_materialization.py:93-132` 按 event_id 合併多 TF 取列並輸出 `index=event_id`（同名 feature 欄衝突在 `:22-31` 已 loud）；`baseline.py:105-110`、`pattern_bridge.py:122-127`、`tables.py:326,372-373` 都以 event_id 交集／索引。具體反例 stdout：`baseline_intersection ['e'] test_rows 2 reported_sample_count 1`；`pattern_lookup_type Series`、`pattern_boolean_type Series`；tables 的 duplicate reindex 為 `ValueError: cannot reindex on an axis with duplicate labels`。額外第七個消費面是 `pipeline.py:760-762` 直接 count assignment rows；前端 `EventTablesPanel.tsx:356-362` 把 `n_train/n_test/n_purged` 以未標註單位顯示，API `EventAnalyzeResponse.summary` 仍是 `Dict[str, Any]`。

**來源摘要**: momentum/Analysis/event_samples/types.py#8ba12e1b5204; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2; momentum/Analysis/event_samples/baseline.py#38c7ec473653; momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2; momentum/Analysis/event_samples/tables.py#843ba7f68172; momentum/Analysis/event_samples/pipeline.py#55ca7327764f; api/models/event_import_models.py#82c83da611f5; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。若一事件的 1h cutoff 在 train、12h cutoff 在 test，pair assignments 不能直接餵給 event-level features；選 first/any 會靜默把混合時序當成一個 OOS 樣本，選 all/any 的實作也未在現行契約定義。若保留現有 event-level chain，保守修法是先以 `(event_id,timeframe)` 做內部邊界投影，再要求同一事件所有生效 TF 同側；混側、跨界或任一不可證者整事件 purge/拒絕並使用明確 reason，`EventSplitPlan` 對既有 consumer 仍維持 event-level。若產品要 per-TF sample，則必須另定 pair-index features/labels、assignments/purged schema、tables/bridge/model API，並把 summary 明確拆成 event counts 與 pair counts。RECHECK: 用一事件兩 TF 分別落 train/test 的 fixture，驗證不得產生未標示的 event-level OOS 值。

## CODEX-R1-P2-03

**斷言**: 同一經濟事件的不同 feature TF 應共享一個事件級 time cluster；把現有 event-level manifest／cluster／dedupe 直接展開成每 TF，會使去重與 cluster lookup 變成非唯一，或在改為每 TF 留樣時把同一事件當成多個獨立觀測。

**碼證**: `event_split.py:40-75` 的 `build_time_clusters` 依 manifest 的 `decision_at_ms` 每事件產一列；`tables.py:214,229,257` 以 event_id 對 receipts/clusters 做 scalar lookup；`dedupe.py:39-49,101-127` 是 event-level interval 去重，context merge 使用 `validate="one_to_one"`，`cluster_first` 依 cluster 只保留一筆。具體 pandas probe stdout：`dedupe_merge MergeError: Merge keys are not unique in right dataset; not a one-to-one merge`；duplicate cluster index 在 tables 的 scalar reindex 為 `ValueError: cannot reindex on an axis with duplicate labels`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#943d0721b059; momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2; momentum/Analysis/event_samples/tables.py#843ba7f68172

[MAJOR] 信心度=High。cluster 的統計單位是事件的 decision/label interval，不是描述該事件的 feature TF；按 TF 分簇會改變簇內樣本語意與 CI 分母，直接複製 cluster rows 也會使現有 scalar join 不可證。修法是 dedupe/manifest 先保留 event-level，所有同事件 TF fold 到同一 cluster；若另開 per-TF sample mode，建立獨立且有權重定義的 pair-level cluster relation，不覆寫既有 `clusters` 語意。RECHECK: 加入同 event 兩 TF、同 decision/label interval 的 fixture，逐值驗 cluster id、保留集與 cluster CI 的觀測單位。

## CODEX-R1-P2-04

**斷言**: 現有 splitunify golden 與 wiring tests 只覆蓋單一 timeframe、event_id 集合與 event-count 語意；b9 若新增 pair rows 或 event-level fold，沒有新增 multi-TF golden 就能讓單 TF 綠測試掩蓋多 TF 回歸。

**碼證**: `tests/golden/splitunify/splitunify_golden.json:3-41,43-108` 的 G1/G4/G5 以 event_id 陣列、per-symbol event count、單一 row fingerprint fixture 保存；`scripts/freeze_splitunify_golden.py:80-118` 固定 `timeframe="1h"` 的 12 筆 fixture；`test_splitunify_wiring.py:113-114` 仍斷言三態計數合計 `len(records)`。目前 `venv/bin/python scripts/freeze_splitunify_golden.py` stdout 為 `GOLDEN OK`，但這只證明單 TF。`EventTablesPanel.tsx` 及 `EventAnalyzeResponse.summary` 沒有 pair-count 型別／顯示單位。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98; scripts/freeze_splitunify_golden.py#e331623163d2; tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e; tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a; api/models/event_import_models.py#82c83da611f5

[MAJOR] 信心度=High。單 TF golden 本身應保留，作為既有 byte/集合回歸；b9 需新增真正含同 event 多 TF、同側、混側、跨界 purge 的 fixture，並選定輸出語意後固定 pair key 或 event fold 的逐值 oracle。若 summary 同時揭露兩種計數，需更新 API/TS 型別與 report integer-key inventory；不能只重凍既有 golden。RECHECK: 跑新增 multi-TF golden、pair uniqueness、混側 fail-closed 與 summary unit assertions；目前未實作，故未宣稱通過。

## COMPOSER-R1-P1-01

**斷言**: D-001 所列六檔不是 `event_id` 單鍵消費面的全集；至少 `counterexample_classifier`、`candidate_ledger`、`build_time_clusters`、IC `event_context_from_windows`、前端 batch_facts、splitunify golden 仍假設唯一。

**碼證**: `rg 'set_index\("event_id"\)' momentum/Analysis/event_samples/` ⇒ 10 檔；D-001 只列 6。`counterexample_classifier.py:52`；`candidate_ledger.py:139,155`；`event_split.py:70-74`；`ic_feed.py:56-60`；`frontend/src/lib/types.ts:2932-2933`。RECHECK: 同上 rg + 讀行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。b9 SPEC 若只列六檔，複合鍵放行後 classifier／ledger／前端會靜默錯或 MergeError，測試未覆蓋。**修法**：延伸檔觸及面增列 7–13，或 b9 維持 fail-closed 直到全部改完。

---

## COMPOSER-R1-P1-02

**斷言**: `feature_materialization` 在複合鍵下會**靜默**丟列——`pd.DataFrame(out_rows).set_index("event_id")` 對重複 `event_id` 只保留最後一列，不 raise。

**碼證**: `feature_materialization.py:93-132`（按 event_id groupby 多 TF 後仍單 index）；VERIFY: 兩列同 event_id → `set_index` 後 `{'feat_x': {'a': 2.0}}`（後者勝）。RECHECK: 跑 brief 必答 2 反例腳本。

**來源摘要**: momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。SU-RESID-2 若只改 `build_event_keys` 不改物化，特徵表會少 TF 且記帳守恆 `:138-140` 可能仍 pass（failures 少算）。**修法**：index 改 `(event_id, timeframe)` 或 MultiIndex；assert index 唯一。

---

## COMPOSER-R1-P1-03

**斷言**: `dedupe` 的 `cluster_first` 會在複合鍵下**靜默折掉**同 event 的不同 TF——與 SU-RESID-2「各 TF 記帳」直接衝突；且 events context merge `validate="one_to_one"` 對重複 event_id 會 MergeError。

**碼證**: `dedupe.py:120`（one_to_one）；`:124-127`（cluster 內 idxmin 一列）；VERIFY: 同 event_id 雙列同 cluster ⇒ 只留 index 0；events 雙列 merge ⇒ `MergeError`。RECHECK: brief 必答 4 腳本。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[BLOCKING] 信心度=High。投影端若輸出多 TF 列，dedupe 在 scenario C 會先折疊再進 tables/baseline。**修法**：`retained` 分組鍵改 `(dedupe_cluster_id, timeframe)` 或 `(event_id, timeframe)`；manifest 一 event 多 TF 時改 merge 鍵。

---

## COMPOSER-R1-P2-01

**斷言**: 現行 fail-closed 只保證「selected timeframe 下每 event 一列 per_tf」；**不**阻擋「同批多 TF 共存」，故 brief 前提「多 TF 同批維持 fail-closed」對**跨 TF** 尚未成立——僅對**同 TF 重複**成立。

**碼證**: `build_event_keys:279-288`（dup 檢查在 filter 後）；`test_build_event_keys_picks_selected_timeframe_only`（`:933-942`）實跑多 TF 取 12h 成功。VERIFY: pytest + python 腳本（必答 5）。RECHECK: 必答 5 三命令。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=High。規格若寫「多 TF 同批全擋」會與現碼不符；實際是「每 event 只投影 selected TF 一列」。**修法**：SPEC 區分 (a) 同 TF 重複 (b) 多 TF 同批；b9 目標是 (b) 的複合鍵記帳。

---

## COMPOSER-R1-P2-02

**斷言**: SU-RESID-2 必改 `EventSplitPlan.assignments`/`purged`/`clusters` schema（至少加 `timeframe`）；`receipts.per_tf` 不必改形狀。

**碼證**: `types.py:87-93`（assignments DataFrame 無 timeframe）；`split_projection.py:545-556`（列構造）；`build_time_clusters:70-74`（clusters 一 event_id 一列）。RECHECK: 讀三處 + `splitunify_golden.json` g1。

**來源摘要**: momentum/Analysis/event_samples/types.py#（EventSplitPlan dataclass 同 commit）

[MAJOR] 信心度=High。只改 producer keys 不改 plan 欄位 ⇒ downstream `set_index("event_id")` 全線假綠。**修法**：assignments 加 `timeframe`；clusters 改 `(event_id,timeframe)` 或 duplicate event_id 明示；更新 freeze 腳本。

---

## COMPOSER-R1-P2-03

**斷言**: SU-RESID-2 不必重算全部 splitunify golden，但 **g1/g3b 必擴維或新增 multi-TF 組**；g5 指紋可不動。

**碼證**: `splitunify_golden.json:3-41`（event_id 列表）；`test_splitunify_golden.py` g5 重算不含 timeframe；closeout recon `:63-64` 同判。RECHECK: `pytest tests/momentum/Analysis/test_splitunify_golden.py -q`。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98

[MINOR] 信心度=High。若只改碼不增 golden，單 TF 五組仍綠但 multi-TF 路徑無回歸。**修法**：`freeze_splitunify_golden.py` 增 `g6_multi_tf_membership`（或 g1 改 dict[event_id→tf list]）。

---

## COMPOSER-R1-P3-01

**斷言**: `ic_feed.build_event_ic_inputs` 已按 `timeframe` 過濾 `per_tf`（`:109`），表格鏈 IC 消費端在**單一 anchor TF** 下語意正確；SU-RESID-2 主風險在物化／dedupe／assignments，不在 ic_feed 過濾本身。

**碼證**: `ic_feed.py:109,126-132`（按 keep event_id 迭代 + per_tf.loc）；同 TF 雙列才會炸。RECHECK: 讀 `:109-132`。

**來源摘要**: momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[MINOR] 信心度=Medium。複合鍵後若 `keep` manifest 仍一 event 一列而 per_tf 多列，ic_feed 仍 OK；若 manifest 也展開多列，`:118` `ev.loc[keep["event_id"]]` 需改。**修法**：b9 先釘 manifest 是否展開 multi-TF。

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
## GROK-R1-P1-01

**斷言**: 複合鍵無法在「不動 `EventSplitPlan.assignments`／`clusters` schema」的前提下落地；現欄契約以 `event_id` 為唯一身分，缺少 `timeframe` 就無法表達同事件異 TF 的不同 split／簇列。

**碼證**: assignments 建構欄＝`["event_id","symbol","split_label"]`（`split_projection.py:555`；`event_split.py:161`）；clusters＝`event_id, time_cluster_id, cluster_weight`（`event_split.py:70-74`）。derive 入口對 `event_keys`／`manifest.table` 做 `event_id` 重複 fail-closed（`split_projection.py:441-447`）。RECHECK：在 assignments 不加 tf 的情況下寫一筆「同 eid、兩 tf、兩 split_label」的往返測試——唯一性閘必紅或第二列被 set 語意吃掉。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。失敗模式：SPEC 若寫「只改下游六檔、assignments 相容 default」⇒ 實作無法表達複合鍵或被迫用字串拼接假鍵。修法：b9 SPEC 明示 assignments／clusters／（視需要）purged 的新欄位契約＋遷移／golden 擴維；禁止「schema 不動」假設。可行性：`per_tf` 已有 timeframe 欄可 join；改的是 EventSplitPlan 列契約與所有 `set_index("event_id")` 消費端。

## GROK-R1-P1-02

**斷言**: D-001 列的六個下游單鍵面**不是**完整消費面；至少 `candidate_ledger.py`、`counterexample_classifier.py`、以及投影／切分本體與匯入閘亦依賴 `event_id` 唯一，漏改會在未列路徑上 raise 或錯位。

**碼證**: `candidate_ledger.py:139,155` `set_index("event_id")`；`counterexample_classifier.py:52` 同；`import_contract.py:861-865` `duplicate_event_id`；`split_projection.py:441-447` 唯一性閘。掃描：`api/` 無對應 pandas 單鍵 merge；`frontend` 無 set_index 但 id 模板含觸發 tf。RECHECK：對 `momentum/Analysis/event_samples` 再跑 `set_index\("event_id"\)|on="event_id"|validate=.*one_to`，差集須納入 b9 TODO。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。失敗模式：只改六檔 ⇒ ledger／反例分類／匯入在多 TF 批上 MergeError 或 Series.loc 爆掉，或更糟用 iloc[0] 假修。修法：b9 消費面清單以本輪差集為準，至少含六處＋ledger＋counterexample＋投影閘改寫＋import 唯一性語意；api／frontend 列為「無 pandas 單鍵、但 id 字串契約要對讀」。

## GROK-R1-P1-03

**斷言**: 「未完成前多 TF 同批維持 fail-closed」若讀成「凡 `per_tf` 出現多個 timeframe 就擋」則為假；異 TF 多列是對齊常態且 `build_event_keys` 放行，真正 fail-closed 的是「selected TF 下 event_id 重複」與 derive 的 `event_id` 重複。

**碼證**: 實跑 CASE A（1h+12h 選 12h）→ PASS；CASE B（1h 兩列）→ `build_event_keys` RAISE（訊息含 SU-RESID-2）；H2 手組同 eid 異 tf 之 event_keys → `derive` RAISE 於唯一性閘。pytest 2 passed（`picks_selected`／`rejects_duplicate_per_tf`）。文件原文：`docs/SPLITUNIFY_SPEC.D-001.md:11,189`；`docs/SPLITUNIFY_SPEC.md:185-189`。RECHECK：重跑本檔必答 5 之 A／B／H2 三命令，結果應同文。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。失敗模式：b9 SPEC 作者按「多 TF 批現在跑不起來」設計遷移，忽略「多 feature TF + 單一 selected_timeframe」生產路徑已在跑 ⇒ 誤改對齊／materialize 的多 TF 合併行為。修法：文件改寫為「擋的是 selected-TF 歧義列與 event_id 鍵空間衝突；異 TF 多列＋單選 TF 為現行支援路徑」；複合鍵目標態＝允許同 eid 多 selected 列進入 assignments，而不是禁止 per_tf 多 TF。

## GROK-R1-P2-01

**斷言**: 複合鍵落地後若未改 `feature_materialization` 的 `groupby("event_id")`＋`row_vals.update` 折疊語意，多 TF 會**靜默**併成單列寬表，驗收只看「有 features」會假綠。

**碼證**: `feature_materialization.py:93-130` 對每個 eid 遍歷該事件全部 per_tf 列並 `update` 欄位；`:132` `set_index("event_id")`；記帳用 `nunique`（`:138`）。本輪未改碼；靜默性由控制流直接讀出（無 per-tf 唯一性 raise）。RECHECK：造兩 TF 特徵欄名不衝突之 fixture，assert 輸出列數＝事件數而非 (事件×TF) 數——現行必為前者。

**來源摘要**: momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[MAJOR] 信心度=High。失敗模式：assignments 已是複合鍵，features 仍單鍵 ⇒ join 丟 TF 或錯對。修法：二選一寫進 SPEC——(A) 維持「決策特徵寬表 per event」並誠實聲明複合鍵不延伸到 materialize；(B) 改 index 為 MultiIndex(event_id, timeframe) 且與 assignments 同鍵。禁止默認「改六檔就自然對」。

## GROK-R1-P2-02

**斷言**: dedupe cluster 折疊在複合鍵下應保持 event 級（同一 event_id 的多 feature TF 不得各算一次 overlap）；若 SPEC 把 cluster 列直接升成 (event_id, tf) 而不重定義 uniqueness，會稀釋 `n_events_effective`／cluster-robust 推論。

**碼證**: `dedupe.py:39-120` 只讀 `event_level` 建簇與 `validate="one_to_one"` merge；overlap 成員是 event_id 字串清單（`:89-94`）。`build_time_clusters` 同樣一列一 event_id（`event_split.py:70-74`）。RECHECK：把同一 label 窗複製成兩列 (eid,1h)/(eid,12h) 丟進現行 `build_event_manifest`——在改 schema 前會先被 `one_to_one` 擋；放寬後若各自進 overlap，weight 必變。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[MAJOR] 信心度=High。失敗模式：複合鍵「圖省事」讓 manifest 變長 ⇒ A/B 情境有效樣本與顯著性全偏。修法：SPEC 分開兩層——dedupe／答案窗簇＝event 級；assignments／評分＝可 (event_id, tf)；time-cluster bootstrap 用 event 級重抽鍵。

## GROK-R1-P2-03

**斷言**: `g1_membership`／`g3b_oracle`／`g5_answer_window` 若在複合鍵落地後仍以 event_id 字串清單比對，多 TF 路徑會因 set 去重而假綠；不必五組全重算，但这三組必須擴維或加平行多 TF golden。

**碼證**: `tests/golden/splitunify/splitunify_golden.json`：`g1`／`g3b` 為 `{train,test,purged: [event_id, …]}`；`g5_answer_window` 同為 id 清單結構。`g5_row_fingerprint_*`／`g4_per_symbol_n` 與 event 複合鍵無直接耦合。RECHECK：freeze 腳本 dump 時對同 eid 兩 tf 只寫 eid ⇒ 與單 TF 集合相等。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MAJOR] 信心度=High。失敗模式：b9 標 done、多 TF 從未打紅。修法：擴 golden 結構為複合鍵或新增 `g1_multi_tf` 平行組；單 TF 舊值可保留作回歸錨。

---


