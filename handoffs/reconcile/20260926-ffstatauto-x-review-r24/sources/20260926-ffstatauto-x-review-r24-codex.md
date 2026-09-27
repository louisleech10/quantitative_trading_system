## CODEX-R24-P1-01

**斷言**: Task 2.3 ② 要求 NaN inventory 覆蓋 L2–L6.5 與多週期對齊的實際步驟函式；目前 AST 列舉只收 `compute`／`_apply_`／`apply`／`align` 前綴，沒有把實際生產 call path 的 private rolling／alignment 方法列成可分類步驟。

**碼證**: AST selector and production call-path anchors; inventory probe output follows.
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:187
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:200
CODE-ANCHOR: momentum/FeatureEngineering/operators/rolling_aggregator.py:140
CODE-ANCHOR: momentum/FeatureEngineering/timeframe/tf_aligner.py:68
CODE-ANCHOR: momentum/FeatureEngineering/timeframe/tf_aligner.py:77
MUTATION: 在 `_searchsorted_align` 或 `_merge_asof_align` 返回前加入 `aligned = aligned.fillna(0.0)`，再執行 inventory；目前列舉不會產生該 private path 的獨立分類與碼證列。
實跑 `/tmp/ffstat-r24-E0zwLs/venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r24-E0zwLs/inventory.json` → rc=1、`unclassified_count=44`；其中未分類清單包含 `RollingAggregator._apply_vectorized_aggregators_with_cache`、`RollingAggregator._compute_all_streaming` 與 `TimeframeAligner.align_to_primary`，而 `_compute_all_streaming*`、`_searchsorted_align`、`_merge_asof_align` 不是列舉器的獨立輸出。
修法與可行性證據：直接擴大同一 AST source-of-truth 的 call-path 選取，並讓每個實際 private branch 在 `nan_propagation_classes.json` 有一列；隔離複本的 AST broaden probe 以同一 repo tree 找到 `_compute_all_streaming`、`_searchsorted_align`、`_merge_asof_align` 三個目標，rc=0，故不需新增旁路機制即可補齊。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#753f6ed4b3d9; momentum/FeatureEngineering/operators/rolling_aggregator.py#cf448d635077; momentum/FeatureEngineering/timeframe/tf_aligner.py#3c30c600ffc1; handoffs/run_receipts/ffstat_probes/stable_start_receipts.py#e3d9443a73e6

## CODEX-R24-P1-02

**斷言**: Task 2.3 ⑪ 的 frame、CGSA serial、CGSA parallel、resume 沒有各自的 stable-start 具名驗收；manifest 以「由 ①④⑤ run 路徑涵蓋、實作時補 parametrize」代替可執行映射，因此一個只在 parallel 或 resume 分支跳過 stable mask 的回歸可以避開本批次的 stable-start 斷言。

**碼證**: manifest path matrix and fixed execution environment; existing path tests follow.
CODE-ANCHOR: docs/manifests/FFSTAT.json:236
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:110
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:216
CODE-ANCHOR: tests/feature_engineering/test_ffstat_calibration.py:697
MUTATION: 在 `FFACT_MULTI_TF_PARALLEL=1` 的 worker 分支將 stable-mask 呼叫替換為 identity，然後只執行 manifest 所列的 stable-start 測試；既有固定環境為 `FFACT_USE_CGSA=1`、`FFACT_MULTI_TF_PARALLEL=0`，不會觸發該分支。
現況證據：`FIXED_ENV` 固定 CGSA 開啟且 multi-TF parallel 關閉；`test_no_start_stationarity_off_stable_values_unchanged` 等具名測試透過同一預設環境執行。既有 `test_resume_calibrates_completed_timeframes` 是 Task 2.1 測試，並非 manifest 所承諾的 Task 2.3 ①④⑤ stable-start 同值驗證。
修法與可行性證據：在既有 stable-start 測試或同檔新增具名 parametrization，明確列出四個 execution mode 並讓 resume 走第二次同設定 run；`prepare_stat_env` 已接受環境覆寫（`_apply_fixed_env` 逐項設置），而現有 calibration 測試已能建立 parallel／resume 實例，故可直接把同一穩定點與遮罩斷言套到各路徑。

**類別**: code-contract

**來源摘要**: docs/manifests/FFSTAT.json#b6a07501343c; tests/feature_engineering/ff_truncation_mr_helpers.py#f56a1395624f; tests/feature_engineering/test_ffstat_stable_start.py#753f6ed4b3d9; tests/feature_engineering/test_ffstat_calibration.py#c55a57a55f57

## CODEX-R24-P1-03

**斷言**: Task 2.3 ⑧ 要求 12h 欄在對齊後的首個有效值時間等於其 12h `stable_start` 可被 1h 取用的時間；`test_multi_tf_mask_applied_before_alignment` 只斷言 `first >= stable[column]`，不能區分對齊前遮罩與對齊後延遲一個以上週期才遮罩。

**碼證**: SPEC equality requirement and current multi-timeframe assertion.
CODE-ANCHOR: docs/FFSTAT_SPEC.md:131
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:426
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:436
CODE-ANCHOR: docs/manifests/FFSTAT.json:240
MUTATION: 將 12h stable mask 從 alignment 前移到 alignment 後，並在對齊結果再延後一個 12h bar 才遮罩；`first` 變晚仍滿足現有 `first >= stable[column]`，所以目前具名測試不會紅。
修法與可行性證據：把斷言改為預期對齊時間的精確等式，並以同一個 12h stable point 驗證遮罩列未被對齊填值延續；測試已取得 `stable` metadata 與 public series，增加等式及一個真實列邊界斷言即可直接否證上述 mutation，不需改變資料或門檻。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#7e8c0622c8e5; tests/feature_engineering/test_ffstat_stable_start.py#753f6ed4b3d9; docs/manifests/FFSTAT.json#b6a07501343c

## CODEX-R24-P1-04

**斷言**: Task 2.3 ⑫ 的 TODO 映射只寫「沿用 `test_ffstat_calibration.py` 既有測試」，沒有具名測試驗證 A/B output window 的 `start_date`／`end_date`、拒收 `config_hash`、以及前置失敗／L1–L6 失敗／成功三種結束後還原 `_current_output_window` 與 `_current_config_hash`；現有測試反而依賴前一次生成留下的 window。

**碼證**: SPEC run_ic_first contract, manifest mapping, and existing stale-window test.
CODE-ANCHOR: docs/FFSTAT_SPEC.md:131
CODE-ANCHOR: docs/FFSTAT_SPEC.md:132
CODE-ANCHOR: docs/manifests/FFSTAT.json:236
CODE-ANCHOR: tests/feature_engineering/test_ffstat_calibration.py:520
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2384
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2420
MUTATION: 將 `run_ic_first` 的本次 window/hash 來源固定為既有的 `self._current_output_window`／`self._current_config_hash`，忽略呼叫端 A window；現有 `test_three_entries_same_decisions` 仍沿用前次生成的 output window，無法否證此 mutation。
現況證據：SPEC 明定 `run_ic_first` 必須自行解析本次起訖、拒收 supplied hash，且成功與各類失敗都還原兩個 state；現有 production signature 尚無 `start_date`／`end_date`，既有測試於 `h.ic_first_to_l65(...)` 前先以 generate path 建立並沿用 factory window。
修法與可行性證據：在 manifest 直接列出具名的 run_ic_first v29–v31 測試，使用同一 factory 的 W0/W1 或 A/B 真實 K 線窗口，分別斷言三種前置／中途／成功結束的 state identity；現有 factory 已有 `_current_output_window`／`_current_config_hash` 狀態與 calibration gate，故測試可在同一入口驗證不沿用與 finally 還原。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#7e8c0622c8e5; docs/manifests/FFSTAT.json#b6a07501343c; tests/feature_engineering/test_ffstat_calibration.py#c55a57a55f57; momentum/FeatureEngineering/feature_factory.py#47f362f67de2

## CODEX-R24-P2-05

**斷言**: 「每條 SPEC boundary 恰一具名測試」不成立於 user-start source：`test_boundary_11_user_start_source_is_user` 與新 `test_boundary_25_user_start_source_user` 都驗 `output_start_source == "user"` 及 effective start 等於使用者起始日，而 manifest 只把 boundary④ 指到後者。

**碼證**: `tests/feature_engineering/test_ffstat_calibration.py:375-379` 與 `tests/feature_engineering/test_ffstat_stable_start.py:523-528` 的 predicate 相同；`docs/manifests/FFSTAT.json:237` 只映射 `boundary④ → test_boundary_25_user_start_source_user`。

**類別**: doc-sync

**來源摘要**: tests/feature_engineering/test_ffstat_calibration.py#c55a57a55f57; tests/feature_engineering/test_ffstat_stable_start.py#753f6ed4b3d9; docs/manifests/FFSTAT.json#b6a07501343c

修法：選定一個 canonical boundary test，另一個明確改為不同可證偽行為或列入退役映射；同步 manifest 的 boundary 編號與 retired table，避免同一 assertion 佔兩個追溯落點。

（1a）本家 r23 的 `CODEX-R23-P2-01` 已閉合。（1b）SPEC v44 的 `docs/FFSTAT_SPEC.md:4-5` 已明寫長歷史 12h 使用 `validate_continuity=False` 並記缺口；`handoffs/run_receipts/20260927-ffstat-longhist-download.json:15-18` 記錄真實 BTC/ETH 12h 缺口與 6656 列；隔離複本實跑預設讀取得到 `ValueError`（缺口 `2018-02-08 12:00:00 UTC`），顯式 `validate_continuity=False` 讀得 6656 列。

（2a）本版 TODO 對 SPEC v44 的追溯不完整。（2b）缺漏為 Task 2.3 ② 的 private call-path inventory、⑪ 四 execution modes、⑫ run_ic_first A/B window 與 state restore；重複為 boundary④ 的 user-start source assertion（P2-05）。Task 2.3 ⑧ 的具名測試存在但斷言弱於 SPEC，列為 P1-03。

（3a）第一條 assumed「每條 validation/boundary 恰一具名測試或 not_executable」不成立；上述缺漏與重複為否證。第二條 assumed「正確實作後三個目前先綠 mutation 會翻轉」判成立（以可觀察呼叫路徑核對）。（3b）`test_mutation_calibration_rows_not_masked_is_caught` 直接呼叫 `test_boundary_22` 的 calibration helper；dead-filter mutant 直接替換同一純函式；config-hash mutant 以固定 policy 使主測試 hash 等值。選定 mutation 命令收集 7 支：3 passed（這三支），4 failed 為預期 pre-implementation 的 `KeyError period_keys`／`NotImplementedError`，沒有把失敗改寫成假綠。

（4a）「我沒查」① 命中 P1-01；② `dual_start_report` 全設定 8 GB 可行性與耗時未查，沒有據此新增 finding；③ `freeze_baseline_nostart.py` 舊 worktree API 相容性未查，沒有據此新增 finding；④ 未命中，contract 已列 `stable_start`、`warmup_doubling`、`start_dependent_columns`、`column_set_reasons`（`tests/_golden/ffstat/contract.json:42-67`）；⑤ 未命中，`_layer1_atomic_indicators(self, data, config)` 簽名與呼叫 `.data` 對位（`momentum/FeatureEngineering/feature_factory.py:931-933`、`tests/feature_engineering/test_ffstat_stable_start.py:479-480`）。

（5a）v44 事實更正成立。（5b）SPEC v44 header 與未填起始日條文均保留 `effective_output_start`，只在 `output_start_source == "user"` 寫入；既有 `test_boundary_11_user_start_source_is_user` 與新 boundary test 都驗該 predicate，且 contract／測試未要求 per-column 寫入該鍵。

（6a）不可放行實作，因有 P1 blocker；P2-05 單獨不阻擋。（6b）阻擋項只有 `CODEX-R24-P1-01`、`CODEX-R24-P1-02`、`CODEX-R24-P1-03`、`CODEX-R24-P1-04`。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、SPEC v44、manifest、TODO template、r23 reconcile、R1–R9 rulings；Assumption A 判不成立，Assumption B 以 3 個目前先綠 mutation 的同一路徑核對判成立；v44 更正與 r23 continuity 修法已由條文、收據及真實長歷史成對探針確認。
TESTS_RUN: 隔離複本三支 `mutation_probe_static.py` → 各 rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → `TODOFMT PASS`；三個新增檔＋既有 ffstat/b6 `pytest --collect-only` → 236 collected；7 支 mutation 選集 → 3 passed、4 expected pre-implementation failures；`stable_start_receipts.py inventory` → rc=1、44 unclassified；AST broaden probe → rc=0；真實 BTCUSDT/12h continuity probe → default `ValueError`、explicit false `6656` rows；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r24-codex.md --family codex --round-id 39c1976f-fd83-4260-8fe7-3ad31cf99b0c` → `COMPLETENESS PASS(single)`、rc=0。依 brief 未跑全設定 FF／§G⑦ 全設定雙起點／frontend build。
FAILURES_SEEN: 4 個純函式 mutation 選集在 pre-implementation 因 `NotImplementedError`／倍數表缺 `period_keys` 失敗，屬 brief 已預期的紅；inventory 因 44 個未分類項 rc=1，支援 P1-01；completeness 首次因 **碼證** 標籤同行為空 rc=1，補上同行摘要後同一命令 rc=0；清理命令 `rm -rf /tmp/ffstat-r24-E0zwLs` 在執行前被 PreToolUse／環境安全閘拒絕，未改寫命令形式或繞過。
SCOPE_CHANGES: none；本輪未改 momentum、api、scripts、tests、docs、templates、config、SPEC、manifest、git history 或 data_cache；只新增本交件檔與 append-only 狀態交接檔。
NUMERIC_OR_SCHEMA_IMPACT: none；未修改數值、schema、輸出大小或既有測試斷言。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r24-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTAUTO-X-REVIEW-R24.md
TMP_CLEANUP: `/tmp/ffstat-r24-E0zwLs` 約 859M，清理命令被拒絕而尚存；`/tmp/claude-501` 保留且未列入刪除目標。

VERDICT: blocked
BLOCKED-BY: CODEX-R24-P1-01,CODEX-R24-P1-02,CODEX-R24-P1-03,CODEX-R24-P1-04
CLOSED: CODEX-R23-P2-01
STATUS: DONE
