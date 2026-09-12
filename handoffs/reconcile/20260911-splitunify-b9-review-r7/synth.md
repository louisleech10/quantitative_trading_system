# Reconcile — 20260911-splitunify-b9-review-r7

**來源** 20260911-splitunify-b9-review-r7-codex.md, 20260911-splitunify-b9-review-r7-composer.md, 20260911-splitunify-b9-review-r7-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **J1 `(5.1)` 分類已改、`Task 9.3` 施工單未同步（三家獨立撞題）**——「D-002-C5§5.1把`tables」「`Task9.3`L187要求`tabl」「第七次修訂的`D-002-C5`(5.1」 | P1 | CODEX-R7-P1-01, COMPOSER-R7-P1-02, GROK-R7-P1-01 | 採納（`Task 9.3` 逐條改寫為與 `(5.1)` 同文：甲類寫「維持、加防誤改回歸」、丙類寫「去重取唯一側、不唯一 fail-closed」；`(5.3)`／`(5.4)` 之「靜默／須改」舊敘事一併改為現況描述並指向 `(5.1)`；主委已逐條查出六處漂移） |
| **J2 `dedupe` 保留集粒度矛盾**——「C5§5.1將`dedupe`保留集列為」「`Task9.3`L188要求`dedu」 | P1 | CODEX-R7-P1-02, COMPOSER-R7-P1-03 | 採納（刪除 `Task 9.3` 之複合鍵保留集要求；改寫為「`dedupe` 維持事件級保留，保留之 `event_id` **廣播**到該事件所有 per-TF 列」，並配「一事件兩 TF 皆存活而簇仍一列」之值與計數測試） |
| **J3 `Task 9.1` (b) 的 dataflow 仍未封（三家獨立撞題）**——「Task9.1(b)雖寫「採(b)」並指」「`Task9.1`定案採(b)並指`ic」「Task9.1雖已定案採(b)，但把終端」 | P1 | CODEX-R7-P1-03, COMPOSER-R7-P1-01, GROK-R7-P1-03 | 採納（🔴 主委改採 **具名殘留**：`api/` 對 `EventSamplePipeline.run` 之呼叫點為 **0**、`ic_filter_orchestrator` 只有 `holdout_boundary` 而無 `build_event_keys` ⇒ **投影路徑本身尚無生產接線**，那是前批「接線」留下的既有狀態、不在本延伸範圍。`Task 9.1` 改為只交付 producer 層 `discarded` 回傳 ＋ `EventSplitPlan.summary` 鍵 ＋ `metadata.split_unify` 欄位；**終端可見性**具名為殘留，理由類別 `blocked-by`，並於 §N 寫明。R8 須專攻此決策） |
| **J4 `Task 9.2b` 之位置映射未定義**——「9.2b三段式只描述「`decision」「`Task9.2b`三段式步驟1依「`d」 | P1 | CODEX-R7-P1-04, COMPOSER-R7-P2-01 | 採納（改以**時間域**判準，不再依賴「映射之位置」：`train_last_ms < decision_at_ms < test_start_ms` ⇒ 隔離帶；`decision_at_ms <= train_last_ms` ⇒ train；`decision_at_ms >= test_start_ms` ⇒ test；早於 `index_ms[0]` 或晚於末列 ⇒ fail-closed。主委已驗 `train_last_ms = int(index_ms[train_rows[-1]])` 為一行可得、與既有 `test_start_ms` 取法對稱） |
| **J5 隔離帶處置與 §G exact 互斥，且換錨本身就會讓邊界事件改側**——「`Task9.2b`把隔離帶從現行`PU」「SPEC同時要求9.2b以event-l」 | P1 | GROK-R7-P1-02, CODEX-R7-P1-05 | 採納（①隔離帶處置由 raise 改回 **`purged`**（沿用既有 reason 字面），主委已自驗 golden 之 `gap1`／`gap2` 刻意造在隔離帶且現值為 purged；②🔴 **codex 指出更根本的一層**：`alignment.py:87-93` 之 cutoff 定義允許 `cutoff < decision`，故即使不碰隔離帶，換錨本身就會使邊界事件改側（`test_start=1000, decision=1000, cutoff=900` ⇒ 舊 train／新 test）⇒ §G「單 TF 逐值不變」與 `(3.1)` 事件級錨定**本質互斥**，第八次修訂須二擇一寫死：改 §G 為「decision-anchor 後重凍 golden」，或明定跨界時之相容規則，並補 `decision != cutoff` 之單 TF 邊界 fixture） |
| **J6 `baseline` 之列數語意與事件級物化互斥**——「D-002-C6要求baseline一事」 | P1 | CODEX-R7-P1-06 | 採納（`D-002-C6` 與 `Task 9.4` 之 baseline 例外須改寫：物化既維持事件級橫向合併，`baseline` 吃的就是**事件級**向量 ⇒ 其 `n_test` 應為**事件數**；原「一事件兩列 fixture 斷言 n_test=2」作廢。若日後要 per-TF 模型輸入，須另立 adapter 與 schema，不在本延伸） |
| **J7 `M-SU-D2-11` 與 `Task 9.5` 排除遷移互斥**——「`M-SU-D2-11`定義「前端`by」 | P2 | COMPOSER-R7-P2-02 | 採納（`M-SU-D2-11` 改為**反向** mutation：「前端 `byEventId` Map **被誤改為複合鍵**致匯出 extras 全數 miss」，應紅測試為匯出附帶欄位值斷言；與 `M-SU-D2-04`／`06`–`10` 之反向改寫同批處理） |
| **J8 §V `Task 9.1` 仍指已作廢之三層**——「§V`Task9.1`L207仍要求「s」 | P2 | COMPOSER-R7-P2-03 | 採納（§V 之 `Task 9.1` 斷言改寫為與 J3 之殘留決策一致：只驗 producer 回傳與 summary 鍵與 `metadata.split_unify` 欄位；`M-SU-D2-02`／`03` 之應紅測試同步改指該三層，不得再指作廢 route） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **`(5.1)` 改了分類卻沒同步施工單與 mutation**（J1／J2／J7／J8 共四群）——這是同一個病：**改了結論，沒回頭改所有依賴那個結論的條目**。三家全部撞到。
2. **我對 I1 選錯補救方向**（J5 前半）——採納「不等式會把隔離帶收成 train」是對的，但改成 raise 撞上 golden 刻意造的 `gap1`／`gap2`。**採納指控 ≠ 選對補救**。
3. 🔴 **codex 揭出一層我與另兩家都沒想到的**（J5 後半）：**換錨本身**就會讓邊界事件改側，與 §G「單 TF 逐值不變」本質互斥——這不是補 fixture 能解決的，必須在「改 §G」與「定相容規則」之間**明確二選一**。
4. **`Task 9.1` 我連續兩輪給出走不到的落點**（J3）——第四次修訂指事件掃描端、第七次修訂指 IC 主線，兩者都沒有 `discarded` 來源。本輪改採**具名殘留**並說明理由類別，不再硬塞。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R7-P1-01
**斷言**: D-002-C5 §5.1 把 `tables`、`counterexample_classifier`、`candidate_ledger`、單一 TF `ic_feed` 與 `pattern_bridge` 的答案判為事件級／去重事件級，但 Task 9.3 卻要求這些 `.loc[eid]` scalar lookup 改成 composite lookup並保留 event-level 表粒度；兩條不能同時落地。
**碼證**: SPEC:74,78-80,187；`tables.py:214,229,234` 以 event-level receipt/cluster `.loc[eid]`，`counterexample_classifier.py:52,61-63`、`candidate_ledger.py:155-160` 同樣只有 event-level receipt，`ic_feed.py:106-130` 先選單一 TF 再以 event_id lookup，`pattern_bridge.py:122-127` 需把 assignment 去重成唯一事件側。RECHECK: `nl -ba` 上述檔案與 `rg -n 'discarded_rows_by_feature_tf|split_unify'` 實跑；碼證輸出確認沒有可供這些 event-level rows 使用的 feature TF key。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/counterexample_classifier.py#444599323e49;momentum/Analysis/event_samples/candidate_ledger.py#b75159633935;momentum/Analysis/event_samples/ic_feed.py#741f697b3964;momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2
具體反例：事件 `e` 有 `1h`／`4h` 兩 per-TF rows，但 `receipts.event_level` 與 `clusters` 各只有 `e` 一列；把 `tables` lookup 改成 `(e,1h)` 會在 event-level index 取不到列，複製成兩個 composite row 又會改變 event-level table 粒度。`pattern_bridge` 若不先證明兩 TF split side 唯一，composite assignment 會有兩列；若直接 `.loc[(e,tf)]`，則違反 §5.1 的事件級答案契約。修法須逐函式明定輸入：事件級表維持 `.loc[eid]`，只有真正 per-TF 表使用 composite；pattern bridge 及 IC survivor 依 §5.1 的丙類先去重且不唯一即 fail-closed。此為 P1，信心度 High。

## CODEX-R7-P1-02
**斷言**: C5 §5.1 將 `dedupe` 保留集列為事件級維持，但 Task 9.3 又要求 `cluster_first` 保留集改成 `(event_id, feature_timeframe)`；這會在同事件多 TF 時靜默丟 TF 或改變 cluster-first 語意。
**碼證**: SPEC:74,78,188；`dedupe.py:101-110` 建立一列一事件的 table，`dedupe.py:122-130` 以 `dedupe_cluster_id` 的 `idxmin` 產生保留集，沒有 `feature_timeframe`；`event_split` 的 clusters 也由 event-level manifest 建立。RECHECK: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '70,80p;184,191p'` 與 `nl -ba momentum/Analysis/event_samples/dedupe.py | sed -n '101,130p'`；兩處粒度要求直接相反。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2
具體反例：`e` 同 cluster 有 `1h`／`4h` 兩列。若先把一事件 manifest row 展開成兩 composite rows，`idxmin` tie 只保留一個 TF；若不展開，根本沒有可供 composite retention 使用的 key；若兩列都保留，`cluster_first` 就不再是每 cluster 一事件，effective count 與 downstream weights 改變。修法是保留 dedupe event-level retention，將保留 event IDs 廣播到 per-TF rows，並刪除／改寫 Task 9.3 的 composite retention 指示；補一事件兩 TF 皆存活且 cluster 仍一列的 value/count test。此為 P1，信心度 High。

## CODEX-R7-P1-03
**斷言**: Task 9.1(b) 雖寫「採 (b)」並指向 IC 主線，仍未指定 discarded 從哪個 producer 進入 IC、response 的 exact path、UI component/field 或 route contract test；因此 9A 仍不可端到端驗收。
**碼證**: SPEC:133-145；`ICFilterOrchestrator.analyze` 只有 `event_timestamps`／`event_context` 等 kwargs（`momentum/Analysis/ic_filter_orchestrator.py:1180-1204`），service staging 的回傳欄位在 `api/services/ic_analysis_service.py:1034-1043` 沒有 discarded，主分析呼叫 `:1942-1963` 也沒傳；現有 `metadata["split_unify"]` 只在 `momentum/Analysis/ic_filter_orchestrator.py:1530-1534` 寫 n_test，前端 `SplitUnifyBadge.tsx:17-29` 只讀該 metadata。RECHECK: `rg -n -g '*.py' -g '*.tsx' -- 'discarded_rows_by_feature_tf|discarded' momentum/Analysis/ic_filter_orchestrator.py api/services/ic_analysis_service.py api/routes/ic_analysis.py frontend/src/components/ic-analysis frontend/src/app/ic-analysis` stdout 只有標題、無命中；`rg` 另確認 route 是 `/result/{task_id}` 而 UI 是 `SplitUnifyBadge`，SPEC 未把 discarded 接上。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;api/services/ic_analysis_service.py#c451536a0652;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;api/routes/ic_analysis.py#52d8a48081d8;frontend/src/components/ic-analysis/SplitUnifyBadge.tsx#44ab6813b4f2
不修時，實作者可完成 `build_event_keys` 的 dict 卻仍讓 IC result 完全看不到它，或自行把欄位塞進寬鬆 `metadata` 而沒有契約。修法須寫死 producer→service/orchestrator explicit kwarg→`GET /ic-analysis/result/{task_id}` 的 exact response path→`SplitUnifyBadge`（或具名新 panel）的 exact field，並新增 route-level contract test 明列 `discarded_rows_by_feature_tf`；僅寫「IC 主線」不構成落點。此為 P1，信心度 High。

## CODEX-R7-P1-04
**斷言**: 9.2b 三段式只描述「`decision_at_ms` 映射之位置」，沒有規定非網格 timestamp 的 mapping（`searchsorted` side、前後列歸屬或半開 interval）；在觸發 TF 與 feature TF 不同時，三段式的結果不唯一。
**碼證**: SPEC:170-178；`split_preview.py:275-283,312-322` 只給 row ranges 與 train/test timestamps；`alignment.py:197-213` 明確允許 per-TF cutoff 與 decision 不同；目前 `split_projection.py:524-553` 仍只能以 feature-index membership 判定。RECHECK: `venv/bin/python -c 'import numpy as np; idx=np.array([0,4,8,12,16]); ...'` stdout：`decision 10 -> left 3 (gap), right-1 2 (train)`；`decision 14 -> left 4 (test), right-1 3 (gap)`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/core/split_preview.py#95a85ec0de54;momentum/Analysis/event_samples/alignment.py#0da3c48b26687;momentum/Analysis/event_samples/split_projection.py#99bfddace904
因此目前不是「四種位置少一種」，而是同一 timestamp 可合法得到不同位置，驗收 oracle 也無法唯一判斷 raise/train/test。修法須在 9.2b 明定一個 total mapping contract，並補至少兩個落在相鄰 feature rows 之間、分別跨 gap/test 邊界的 fixture；不得只重述三段順序。此為 P1，信心度 High。

## CODEX-R7-P1-05
**斷言**: SPEC 同時要求 9.2b 以 event-level `decision_at_ms` 定側、§G 單 TF 路徑逐值 exact，但沒有保證 `decision_at_ms` 與 `feature_cutoff_ms` 不跨 canonical boundary；所以單 TF golden 可能改側，原 R6 gap 修法不能證明 backward compatibility。
**碼證**: SPEC:127,173-178；`alignment.py:87-93,197-213` 的 cutoff 是 `max(close_ms <= decision_at_ms)`，可早於 decision；現行 `split_projection.py:530-550` 以 cutoff membership 定側。RECHECK: `venv/bin/python -c 'test_start=1000; decision=1000; cutoff=900; print(...)'` stdout=`{'current_cutoff_membership': 'train', 'new_decision_inequality': 'test', 'decision_at_ms': 1000, 'feature_cutoff_ms': 900, 'test_start_ms': 1000}`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/alignment.py#0da3c48b26687;momentum/Analysis/event_samples/split_projection.py#99bfddace904;tests/momentum/event_samples/test_alignment.py#3d6a16a4d617
具體邊界事件可同時滿足現行 PIT（cutoff=900 ≤ decision=1000）與 canonical boundary（test_start=1000），舊路徑是 train、新路徑是 test；現有 alignment test 只驗 cutoff 數值，沒有此切分邊界對照。修法須二選一並寫進 §G：把 exact 定義改成 decision-anchor 後重凍 golden，或明定 cutoff/decision 跨界時的 fail-closed/相容規則；並加入 decision≠cutoff 的單 TF boundary fixture。此為 P1，信心度 High。

## CODEX-R7-P1-06
**斷言**: D-002-C6 要求 baseline 一事件兩 TF 時 `n_test=2`（composite model rows），但 Task 9.3 又要求 feature materialization 維持事件級水平合併、baseline 隨上游 index 且不新增粒度；兩者沒有可執行的 adapter contract。
**碼證**: SPEC:186,189,198；`feature_materialization.py:42,93-140` 回傳 `features_at_decision` 之 event_id index，並以 `groupby("event_id")` 合併；`baseline.py:92-110` 明定 event_id index 並以 event ID intersection 取 X；`baseline.py:118-121` 的 `n_test` 是 `len(idx)`。RECHECK: `nl -ba` 上述兩檔與 SPEC:184-199；現有 input contract 沒有 feature_timeframe 或 composite adapter。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2;momentum/Analysis/event_samples/baseline.py#38c7ec473653;momentum/Analysis/event_samples/types.py#8ba12e1b5204
具體反例：一事件 `e` 的 1h/4h 特徵先按現行物化規則拼成一個 event-level row，baseline 的 `idx` 只能得到一個 test sample，故 `n_test=1`；強行複製兩列又會產生重複水平向量或未定義的稀疏向量，且與「baseline 不新增粒度」矛盾。修法須明定 baseline 是吃事件級水平向量（則驗收 n_test 應為 1），或新增 per-TF model-input adapter 並定義 features/labels/weights/schema；不能只在 C6 寫一事件兩列 fixture。此為 P1，信心度 High。

ASSUMPTIONS_VERIFIED: R6 closure 狀態以 SPEC 第七修訂的逐條落點重驗；doc format rc=0、obligation block rc=0、mutation unique IDs=26；gap mapping、cutoff/decision 跨 boundary、IC discarded grep、現行 event-level consumer contracts 均有命令或碼證。
TESTS_RUN: `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py --tb=short` rc=0（9 passed）；兩個 inline mapping/boundary probes rc=0；IC discarded rg 無命中。
FAILURES_SEEN: none（審查期間未修改碼、SPEC、TODO 或測試；現有 wiring test 的 selected_timeframe=None 舊斷言是待實作替換項，未擅改）。
SCOPE_CHANGES: none；僅新增本交接檔；根 `HANDOFF.md`、`data_cache/` 與既有 dirty worktree 均未改動。
NUMERIC_OR_SCHEMA_IMPACT: 未改執行輸出；本審查指出待釐清的 `(event_id, feature_timeframe)`、`discarded_rows_by_feature_tf`、baseline n_test 粒度與 IC response/UI schema，未自行變更。
VERDICT: blocked
BLOCKED-BY: CODEX-R7-P1-01,CODEX-R7-P1-02,CODEX-R7-P1-03,CODEX-R7-P1-04,CODEX-R7-P1-05,CODEX-R7-P1-06
CLOSED: CODEX-R6-P1-01,CODEX-R6-P1-02,CODEX-R6-P1-03,CODEX-R6-P1-06,CODEX-R6-P2-07
STATUS: DONE
## COMPOSER-R7-P1-01

**斷言**: `Task 9.1` 定案採 (b) 並指 `ic_filter_orchestrator` 為投影消費者，但該模組只對 `features_df` 呼叫 `holdout_boundary`，**從不**呼叫 `build_event_keys`／`EventSamplePipeline.run`；repo 內 split 語境 `discarded` 零實作、`.run()` 僅見於測試 ⇒ 9A 仍無可執行生產路徑。

**碼證**: `ic_filter_orchestrator.py:604-609` 僅 `holdout_boundary(_feature_dt_index,...)`；`pipeline.py:747` 之 `build_event_keys` 只在 `EventSamplePipeline.run` 內；`rg 'EventSamplePipeline\(\)\.run' --glob '*.py'` 非測試命中 0（僅 `handoffs/` probe）。`case_import_service.py:1592-1609` 仍 event-study-only。RECHECK: 對讀 `Task 9.1` L144 與上述三路徑 call graph。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/pipeline.py#99bfddace904

[BLOCKING] 信心度=High。實作者按 (b) 在 `ic_filter_orchestrator` 加 summary 鍵也拿不到 `build_event_keys` 的 `discarded` dict，9A 驗收只能寫 unit test 假綠。**修法**：`Task 9.1` 補**具名** IC route（例 `api/routes/ic_analysis.py` 哪個 handler）、response 鍵、前端面板，並要求該路徑實際呼叫 `EventSamplePipeline.run`（或把 `discarded` 從 `build_event_keys` 接到已存在的投影鏈）；§V 9.1 斷言改指向該 route 之契約測試命令。**可行性**：`test_splitunify_wiring.py` 已有 `.run()` 端到端樣板，缺的是生產接線規格。

## COMPOSER-R7-P1-02

**斷言**: `Task 9.3` L187 要求 `tables`／`counterexample_classifier`／`candidate_ledger` 之 `.loc[eid]` 改複合鍵 lookup，與 `D-002-C5` (5.1) 將三者列於 **(甲) 事件級——維持不動** 互斥；三處碼證皆只讀 `receipts.event_level`／`manifest.table`（一列＝一事件），改複合鍵會誤導實作者改 event-level 索引。

**碼證**: SPEC L74 (甲) 逐字列名三者＋ `tables` 之 `.loc[eid]`；L187 要求改複合鍵 lookup。`tables.py:214,234` `ev.loc[eid]` on event_level；`counterexample_classifier.py:52,62`；`candidate_ledger.py:155,160`。RECHECK: 對讀 L74 vs L187 ＋ 上列三檔 `set_index`／`.loc`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/counterexample_classifier.py#444599323e49;momentum/Analysis/event_samples/candidate_ledger.py#b75159633935

[BLOCKING] 信心度=High。Agent 照 L187 改 tables 會破壞事件級 forward-return 表（`manifest.table` 一列一事件），與 R6 I3／I4 方向相反。**修法**：刪除 L187 中三者（保留 `pattern_bridge` 於 (丙) 去重敘述，或移至獨行指向 `Task 9.3`／(5.1) (丙)）；§V Task 9.3 測試改為「event-level `.loc[eid]` 值不變」而非複合鍵。**可行性**：純 SPEC 同步，無需改碼。

## COMPOSER-R7-P1-03

**斷言**: `Task 9.3` L188 要求 `dedupe` 之 `cluster_first` 保留集改 `(event_id, feature_timeframe)` 粒度，與 `D-002-C5` (5.1) 將 `dedupe` 之保留集列於 **(甲) 事件級維持** 互斥；`build_event_manifest` 只吃 `receipts.event_level`，無 `feature_timeframe` 維度。

**碼證**: L74 (甲) 含 `dedupe` 之保留集；L188 要求複合鍵粒度。`dedupe.py:39` `ev = receipts.event_level.copy()`；`:125-128` `groupby("dedupe_cluster_id")` 於事件級 table。RECHECK: 對讀 L74 vs L188 ＋ `dedupe.py:39,125-128`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[BLOCKING] 信心度=High。照 L188 實作會要求 manifest 按 feature TF 複製列，直接衝突 `Task 9.2a` clusters 維持事件級與 `w=1/n` 語意。**修法**：刪除 L188 或改為「dedupe 維持事件級；複合鍵只影響下游消費 assignments 之處」。**可行性**：SPEC 一字刪除即可對齊 R6 I4。

## COMPOSER-R7-P2-01

**斷言**: `Task 9.2b` 三段式步驟 1 依「`decision_at_ms` 映射之位置」判隔離帶，但未定義離 `feature_index` 網格之 `decision_at_ms` 的位置映射演算法，實作者無法寫出單一 deterministic 實作或 §V 反例。

**碼證**: L174–177 三次出現「映射之位置」／「落在 train 或 test 覆蓋區」但無 `searchsorted`／最近鄰／fail-closed 擇一；L174 承認大量 `decision_at_ms ∉ index_ms`。現行 `:531-533` 用 `feature_cutoff_ms in train_ms/test_ms`（集合成員）。RECHECK: 構造 `decision_at_ms` 不在 `index_ms`、cutoff 在 train 之單 TF 事件，比對三種映射下步驟 1–3 結果是否一致。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=High。Task 9.2b 實作時會各自選映射規則，gap／界外與不等式優先再次分歧；單 TF golden 可能因 gap 由 purge 改 raise 而位移。**修法**：在 `Task 9.2b` 增可操作映射定義（建議：先將 `decision_at_ms` 映射到 `feature_index` 最近 **不晚於** decision 的 bar 位置，再套三段式；離網格且無法映射 ⇒ fail-closed）；§V 增單 TF gap 事件 purge vs raise 成對 ASSERT。**可行性**：與 R6 I1 三段式同區塊增補，不動切分數學。

## COMPOSER-R7-P2-02

**斷言**: `M-SU-D2-11` 定義「前端 `byEventId` Map 鍵退回 `event_id`」為缺陷，與 `Task 9.5` L203／`D-002-C5` (5.1) **排除於複合鍵遷移之外**（維持 event-level 鍵）矛盾——正確實作恰恰是維持 `event_id`／`canonicalEventId` 鍵。

**碼證**: L203 與 L74 (甲) 搜尋頁匯出 Map；mutation L230 `M-SU-D2-11`「鍵退回 `event_id`」應紅。`eventExport.ts` record 無 `feature_timeframe`（R6 碼證）。RECHECK: 對讀 L203 vs mutation 表 `M-SU-D2-11`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd

[MAJOR] 信心度=High。實作者為通過 mutation 11 會把已排除的 Map 改成複合鍵，重現 R6 I6 匯出 miss。**修法**：刪除 `M-SU-D2-11` 或改為反向 mutation「**錯誤**改成複合鍵導致 export miss」；應紅測試對齊 `Task 9.5` 排除敘述。**可行性**：mutation 表一行改寫。

## COMPOSER-R7-P2-03

**斷言**: §V `Task 9.1` L207 仍要求「summary／**API 回應**／**前端型別**三層皆帶該欄」，但 `Task 9.1` L143–144 已作廢 `case.py`／`EventTablesPanel` 落點且改掛未指名的 IC 路徑 ⇒ §V 與正文互斥，`M-SU-D2-02`／`03` 應紅測試仍指向作廢路徑。

**碼證**: L207 三層 ASSERT；L143「上列四個落點…全部作廢」；L144 僅抽象「IC 投影路徑之回應欄位、其前端顯示位置」無 route 名。mutation L221–222 仍寫 API／前端契約測試。RECHECK: `sed -n '143,144,207p' docs/SPLITUNIFY_SPEC.D-002.md` ＋ mutation 表 01–03。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd

[MAJOR] 信心度=High。驗收會逼實作者去寫已作廢 route 的契約測試而假綠，或與 (b) 裁定衝突。**修法**：§V 9.1 改寫為 IC 主線三層（待 P1-01 指名後逐字填入）；`M-SU-D2-02`／`03` 應紅測試同步改指向該 route。**可行性**：依賴 P1-01 先定落點，可同批修。

## GROK-R7-P1-01

**斷言**: 第七次修訂的 `D-002-C5` (5.1) 已把 `dedupe`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger` 列為 **(甲) 維持事件級**、`pattern_bridge` 列為 **(丙) 去重取唯一**，但 `Task 9.3` L187–188 與 mutation `M-SU-D2-04`～`11` 仍要求（或假設）這些處改複合鍵／改 groupby——施工單與分類互斥，實作者照 Task 9.3 會破壞甲／丙定案。

**碼證**: SPEC L74 (5.1) 甲含 `dedupe`／`tables`／`ic_feed`／`counterexample`／`candidate_ledger`，丙含 `pattern_bridge`；L187 逐字「改為複合鍵 lookup」；L188 逐字「`cluster_first` 保留集改 `(event_id, feature_timeframe)`」；L223 `M-SU-D2-04`「不改 groupby 折疊」＝缺陷；L230 `M-SU-D2-11`「Map 鍵退回 event_id」＝缺陷，但 L203 Task 9.5 已排除 Map 遷移。碼：`dedupe.py:124-129`、`tables.py:214,229`、`ic_feed.py:109`、`pattern_bridge.py:125-127`、`feature_materialization.py:93-140`。RECHECK: 對讀 L74↔L186-188↔mutation 表 04–11。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e;momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。不改則 Task 9.3 實作時：(a) 把事件級表改複合鍵 → `.loc`／去重／簇權重語意壞；(b) 或照 (5.1) 維持不動 → mutation 04–11 無法紅／假綠；(c) `M-SU-D2-04`／`11` 與新定案方向相反。**修法**：Task 9.3 逐條改寫為與 (5.1) 同文——甲處寫「維持、加回歸防誤改」；丙處寫「去重取唯一側、不唯一 raise」；mutation 04 改為「誤把物化改成每 TF 一列／MultiIndex」才紅；05 對齊丙；06–10 改為反向 mutation（誤改複合鍵才紅）或刪除；11 刪除或改為「誤改複合鍵致匯出 miss」。**可行性**：分類表已寫好，只是施工單／mutation 未同步；無需新架構。

## GROK-R7-P1-02

**斷言**: `Task 9.2b` 把隔離帶從現行 `PURGED_else` 改成 fail-closed raise，會改變單 TF 切分成員集，並與 §G「單 TF 路徑逐值不變（exact）」及 golden 具名 `gap1`／`gap2`（現行在 `purged`）直接衝突；且 `decision_at_ms ∉ index_ms` 時「映射之位置」未定義。

**碼證**: VERIFY: `PYTHONPATH=. venv/bin/python` 探針 → golden `gap1 pos 140 PURGED_else`、`gap2 pos 141 PURGED_else`；`freeze_splitunify_golden.py` `OOS, PURGE, EMBARGO = 0.3, 2, 2`；`g1_membership.purged` 長度 3。SPEC L175 隔離帶 raise；§G L127「單 TF 路徑逐值不變（exact）」。另：`n=20,purge=2,embargo=1` 時 `COVER True`（無第四落點），但 `decision=1h` 對 4h `index` 時 `exact_member False`、`searchsorted_pos=1`。RECHECK: 重跑 golden keys 分類＋對讀 L175↔L127。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;scripts/freeze_splitunify_golden.py#e331623163d2;momentum/core/split_preview.py#95a85ec0de54;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。照字面實作 Task 9.2b：(a) 現有 golden／wiring 在 gap 事件上由「入 purged」變「raise」⇒ 單 TF exact 失敗；(b) 粗網格下映射未定義 ⇒ 實作者可走出 searchsorted 誤收 train、或精確成員大量 raise 兩歧路。**修法**（須寫死其一並改 §G／fixture）：建議 **隔離帶維持事件級 purge（reason 沿用或分名），不得收成 train**——滿足 R6「不等於 train」且保留單 TF purged 集合；§V 成對 ASSERT「gap ⇒ purged 且非 train、非 raise」；另用時間域定義 gap（`train_last_ms < decision_at_ms < test_start_ms`）避免依賴 `∈ index_ms`。若堅持 raise，則 §G 必須明文豁免 gap 行為變更，並重凍／移除 `gap1`／`gap2` 錨。**可行性**：現行 else 分支已是 purge；改「不等式＋gap 時間窗 ⇒ purge」比改 golden 全鏈成本低，且不把隔離帶收成 train。

## GROK-R7-P1-03

**斷言**: Task 9.1 雖已定案採 (b)，但把終端揭露掛在「IC 主線＝`holdout_boundary` 呼叫點」是範疇錯置——`discarded` 只可能出自 `build_event_keys`（經 `EventSamplePipeline.run`），而 `api/` 目前零 `run()` 呼叫、`ic_filter_orchestrator` 不含 `build_event_keys`；替代 route／回應欄／前端仍寫「實作須指名」，§V 仍用已作廢的「三層」句式 ⇒ 9A 仍無可執行驗收命令。

**碼證**: L144「IC 主線（`ic_filter_orchestrator` 為 `holdout_boundary` 之生產呼叫點）」＋「實作須指名…」；`ic_filter_orchestrator.py:604` 僅 `holdout_boundary(...)`；`pipeline.py:747` 為非測唯一 `build_event_keys` 呼叫；`grep` 於 `api/`：`EventSamplePipeline().run`／`create_event_sample_pipeline().run` 命中 0；`case_import_service.py:1592-1609` 仍 event-study-only。§V L207 仍 `ASSERT summary／API 回應／前端型別三層皆帶該欄`。RECHECK: `grep -rn 'build_event_keys\|EventSamplePipeline().run' api momentum --include='*.py'`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;api/services/case_import_service.py#d2571793953f

[BLOCKING] 信心度=High。Agent 無法寫出單一「打哪條 HTTP、期望哪個 JSON 鍵」的契約測試；若硬掛 IC report metadata，那裡根本沒有 `discarded` 來源。**修法**：在 Task 9.1 **具名一條確實呼叫 `EventSamplePipeline.run`（或等價投影）的生產／準生產路徑**——若尚無，則 (b) 必須含「新增／恢復」該路徑的 route＋service＋前端面板檔案:行；§V 改寫為可複製命令（含 fixture 與鍵名 `discarded_rows_by_feature_tf`）；刪除「實作須指名」與對已作廢三層的獨立回退句，改指新三層。**可行性**：測試面 `test_splitunify_wiring.py` 已是 `run()`＋投影的可跑範本；把同級路徑升成 API 揭露面即可，不必碰 `holdout_boundary`。

---

