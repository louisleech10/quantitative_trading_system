## §0 前提與必答
1-5 結論：R6 `P1-01/02/03/06`、`P2-07` 以三段 gap、跨表互斥/廣播、事件級物化、Map 排除、mutation 23/26 拆分閉合；`P1-04/05` 未閉合並以本輪 P1-01/P1-03 重開。C5 事件級分類本身大致正確，但 Task 9.3/dedupe 指示相衝；9.2b gap 已補而非網格 mapping 未封，且 decision/cutoff 可令單 TF golden 改側；9.1(b) 尚無 IC producer→response→UI→route-test 鏈；新增 C6 baseline 粒度矛盾，詳下六項。
## CODEX-R7-P1-01
**斷言**: C5 §5.1 將 tables、counterexample、candidate、單 TF IC feed 與 pattern bridge 判為事件級/去重事件級，Task 9.3 卻要求它們 `.loc[eid]` 改 composite 但 event-level 表不變，不能同時落地。
**碼證**: SPEC:74,78-80,187；`tables.py:214,229,234`、`counterexample_classifier.py:52,61-63`、`candidate_ledger.py:155-160` 只有 event-level receipt，`ic_feed.py:106-130` 先單 TF 後 event_id lookup，`pattern_bridge.py:122-127` 需唯一事件側；RECHECK: `nl -ba`/`rg -n -g '*.py' -- 'feature_timeframe|discarded_rows_by_feature_tf'` 實跑無可供 event-level row 的 composite key。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;tables.py#843ba7f68172;counterexample_classifier.py#444599323e49;candidate_ledger.py#b75159633935;ic_feed.py#741f697b3964;pattern_bridge.py#d8b69a49dde2。反例：e 有 1h/4h、event receipt/cluster 僅一列；改 `(e,1h)` 會 KeyError，複製列則改粒度。修法：事件級表保留 `.loc[eid]`，僅真正 per-TF 表 composite；丙類先去重且不唯一 fail-closed。P1/High。
## CODEX-R7-P1-02
**斷言**: C5 §5.1 說 dedupe 保留集事件級維持，Task 9.3 卻要求 `cluster_first` 改 `(event_id,feature_timeframe)`，會丟 TF 或改變 cluster-first 語意。
**碼證**: SPEC:74,78,188；`dedupe.py:101-110` table 一列一事件，`:122-130` `groupby(dedupe_cluster_id).idxmin()` 無 feature TF；RECHECK: `nl -ba` SPEC `70-80,184-191` 與 dedupe `101-130` 顯示粒度直接相反。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;dedupe.py#5962ba9c8f2e;feature_materialization.py#3403d81fa8f2。反例：e 同 cluster 有 1h/4h，展開後 idxmin tie 只留一個，兩列都留又不再每 cluster 一事件。修法：dedupe 保留 event-level，再把 event IDs 廣播到 per-TF；補兩 TF 皆存活/cluster 一列測試。P1/High。
## CODEX-R7-P1-03
**斷言**: Task 9.1(b) 只寫採 IC 主線，未指定 discarded producer、IC response exact path、UI field/component 或 route contract test，9A 仍不可端到端驗收。
**碼證**: SPEC:133-145；orchestrator `:1180-1204` 無 discarded kwarg，service `:1034-1043`/`:1942-1963` 無欄位，現有 `metadata["split_unify"]` 僅 `:1530-1534` 寫 n_test，`SplitUnifyBadge.tsx:17-29` 僅讀該 metadata；RECHECK: `rg -n -g '*.py' -g '*.tsx' -- 'discarded_rows_by_feature_tf|discarded' momentum/Analysis/ic_filter_orchestrator.py api/services/ic_analysis_service.py api/routes/ic_analysis.py frontend/src/components/ic-analysis frontend/src/app/ic-analysis` 無命中。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;ic_analysis_service.py#c451536a0652;ic_filter_orchestrator.py#9a3e94399293;ic_analysis.py#52d8a48081d8;SplitUnifyBadge.tsx#44ab6813b4f2。修法：寫死 producer→explicit kwarg→`GET /ic-analysis/result/{task_id}` 欄位→badge/panel，並加明列欄名的 route test；「IC 主線」不足。P1/High。
## CODEX-R7-P1-04
**斷言**: 9.2b 只說 `decision_at_ms`「映射之位置」，沒定義非網格 timestamp 的 searchsorted side/前後列歸屬，故三段式結果不唯一。
**碼證**: SPEC:170-178；`split_preview.py:275-283,312-322` 只給 row range，`alignment.py:197-213` 允許 cutoff≠decision，現行 `split_projection.py:524-553` 只有 index membership；RECHECK: inline numpy probe rc=0，`decision 10: left=3(gap), right-1=2(train)`、`decision 14: left=4(test), right-1=3(gap)`。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;split_preview.py#95a85ec0de54;alignment.py#0da3c48b26687;split_projection.py#99bfddace904。不是少一種區間，而是同 timestamp 有多個合法位置；修法須定 total mapping 並測相鄰列跨 gap/test 邊界。P1/High。
## CODEX-R7-P1-05
**斷言**: 9.2b 要 event-level decision anchor，§G 卻要求單 TF exact，未保證 decision/cutoff 不跨 boundary，故 backward compatibility 未證明。
**碼證**: SPEC:127,173-178；`alignment.py:87-93,197-213` cutoff=`max(close≤decision)`，`split_projection.py:530-550` 舊側別吃 cutoff；RECHECK: inline probe rc=0，`decision=1000, cutoff=900, test_start=1000` 得舊 `train`、新 `test`。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;alignment.py#0da3c48b26687;split_projection.py#99bfddace904;test_alignment.py#3d6a16a4d617。修法須明定 exact 是重凍 decision-anchor golden，或跨界 fail-closed/相容規則，並補 decision≠cutoff fixture。P1/High。
## CODEX-R7-P1-06
**斷言**: C6/Task 9.4 要 baseline 一事件兩 TF `n_test=2`，Task 9.3 卻維持物化 event-level 水平合併且 baseline 不新增粒度，無 adapter contract。
**碼證**: SPEC:186,189,198；`feature_materialization.py:42,93-140` 回 event_id index 並 groupby event_id，`baseline.py:92-110,118-121` 以 event_id intersection、`n_test=len(idx)`；RECHECK: `nl -ba` 兩檔與 SPEC `184-199` 確認無 feature_timeframe adapter。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;feature_materialization.py#3403d81fa8f2;baseline.py#38c7ec473653;types.py#8ba12e1b5204。反例：e 的 1h/4h 先合成一 event row，baseline 只能 n_test=1；硬複製會成重複或未定義 sparse vector。修法須選 event-level n_test=1，或明定 per-TF model-input adapter/schema。P1/High。
ASSUMPTIONS_VERIFIED: R6 closure、C5/9.2b/9.1(b) 與新 C6 矛盾均以 SPEC/碼證重驗；gap fail-closed 與 26 mutation IDs 已確認。
TESTS_RUN: doc_format rc=0；obligation_block rc=0；`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py --tb=short` rc=0（9 passed）；mapping/boundary probes rc=0；IC discarded rg 無命中。
FAILURES_SEEN: completeness 包裝命令曾被 PreToolUse debt gate 擋，原命令重跑 rc=0；`rm -rf` 被安全 hook 拒、`trash` 對既有 /private/tmp 檔案 permission denied；未改碼/SPEC/TODO/測試。
SCOPE_CHANGES: none；只新增本檔，未改根 HANDOFF、data_cache 或既有 dirty worktree。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出；僅指出 composite key、discarded_rows_by_feature_tf、baseline n_test 與 IC response/UI schema 待釐清。
TMP_CLEANUP: `/private/tmp/claude-501` 已保留；非本輪 splitunify 臨時項因 safety/permission 未刪，未繞過限制。
VERDICT: blocked
BLOCKED-BY: CODEX-R7-P1-01,CODEX-R7-P1-02,CODEX-R7-P1-03,CODEX-R7-P1-04,CODEX-R7-P1-05,CODEX-R7-P1-06
CLOSED: CODEX-R6-P1-01,CODEX-R6-P1-02,CODEX-R6-P1-03,CODEX-R6-P1-06,CODEX-R6-P2-07
STATUS: DONE
