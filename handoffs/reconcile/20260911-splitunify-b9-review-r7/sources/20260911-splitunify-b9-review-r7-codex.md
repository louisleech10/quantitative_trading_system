## §0 前提與必答

1. R6 closure：`CODEX-R6-P1-01/02/03/06` 與 `CODEX-R6-P2-07` 已分別由 SPEC 的三段式 gap、跨表互斥＋事件側廣播、物化事件級、匯出 Map 排除、mutation 23/26 拆分而關閉；`CODEX-R6-P1-04`（C5/Task 9.3 lookup 矛盾）與 `CODEX-R6-P1-05`（IC discarded dataflow 未具名）未關閉，於本輪以新 finding 重開。
2. C5：`receipts.event_level`、manifest、clusters、物化輸出、dedupe 保留集、tables scalar receipt/cluster、counterexample、candidate ledger、單 TF IC feed 與匯出 Map 判為事件級是正確的；但 Task 9.3 的 composite lookup 及 dedupe composite 保留集與該分類衝突，具體錯誤情境見 P1-01/P1-02。
3. 9.2b：gap 先 raise 的原 R6 缺口已補；三段在「位置」已定義後可覆蓋 train/gap/test/界外，但 SPEC 沒有定義 `decision_at_ms` 如何映射到非網格 `feature_index` 位置，故目前仍不可唯一實作。單 TF exact golden 也未被證明，cutoff 與 decision 可跨 boundary，見 P1-04/P1-05。
4. 9.1(b)：目前 IC 主線只有 `metadata.split_unify` 的 test count 產生點；`discarded_rows_by_feature_tf` 沒有 producer、service/orchestrator kwarg、response field 或畫面欄位的具名鏈，且沒有 route contract test。`ic_filter_orchestrator`／`SplitUnifyBadge` 只說「IC 主線」不足以使驗收可執行，見 P1-03。
5. 新問題：C5/Task 9.3 的 consumer 粒度矛盾（P1-01）、dedupe 保留集粒度矛盾（P1-02）、9.1(b) IC dataflow 未封（P1-03）、9.2b mapping 未封（P1-04）、decision anchor 與單 TF golden 衝突（P1-05）、baseline 的 composite row count 與事件級物化互斥（P1-06）。

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
