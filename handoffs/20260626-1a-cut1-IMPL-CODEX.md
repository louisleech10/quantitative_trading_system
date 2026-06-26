# 20260626-1a-cut1-IMPL-CODEX

## B1 — BLOCKED
- 批次：B1（Task 1.1-1.4）
- 狀態：未實作；驗收前置不成立
- 已讀：`HANDOFF.md`、`CLAUDE.md`、`AGENTS.md`、`docs/IC_PHASE1_1a_CUT1_SPEC.md`、`docs/IC_PHASE1_1a_CUT1_TODO.md`、`docs/DEVELOPMENT_GUIDE.md`（已讀至任務相關規範與測試/資料真實性要求）
- 查證：`rg` 找不到 B1 驗收指定測試 `test_create_ic_split_adapter_forwards_allowed_symbols`、`test_resolve_expected_freq`、`test_metadata_symbol_required`、`test_icconfig_new_fields_default_off`
- 查證：`tests/momentum/test_factories.py` 不存在；`tests/momentum/Analysis/test_ic_1a_cut1_split.py` 不存在
- 驗收命令：`source venv/bin/activate && pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_metadata_symbol_required tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_icconfig_new_fields_default_off`
- 結果：FAIL，pytest exit 4，`file or directory not found: tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols`
- 卡點：B1 派工塊允許改檔只有 `momentum/factories.py`、`momentum/Analysis/ic_filter_orchestrator.py`、`momentum/Analysis/ic_config_schema.py`；未授權新增/修改驗收測試檔，因此無法讓「每批驗收綠燈」成立
- 需擴大 scope：允許新增/修改 `tests/momentum/test_factories.py` 與 `tests/momentum/Analysis/test_ic_1a_cut1_split.py`，或提供已存在的等價驗收測試路徑
- SCOPE_CHANGES：none（未改實作碼）
- NUMERIC_OR_SCHEMA_IMPACT：none

STATUS: BLOCKED — B1 驗收測試檔不存在，且 B1 scope 未授權新增/修改測試檔；需 Claude 核准擴大 scope 或提供正確測試路徑

## B1 — PASS（本輪重啟，測試檔已獲授權）
- 批次：B1（Task 1.1-1.4）
- 改檔：`momentum/factories.py::create_ic_split_adapter`、`momentum/Analysis/ic_config_schema.py::ICConfig`、`momentum/Analysis/ic_filter_orchestrator.py` helpers、`tests/momentum/test_factories.py`、`tests/momentum/Analysis/test_ic_1a_cut1_split.py`
- 實作：factory 轉傳 `allowed_symbols`；新增 `ic_train_test_split=False`、`oos_test_size=0.2`、`embargo=0`、`min_test_rows=131`；新增 timeframe 與 metadata symbol helper
- 驗收：`pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_metadata_symbol_required tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_metadata_symbol_outside_allowlist_blocked tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_icconfig_new_fields_default_off -q`
- 結果：PASS（5 passed）
- 解耦：`grep -rE "from api\\." momentum/ | wc -l` → 0
- 問題：none

## B2 — PASS
- 批次：B2（Task 2.1-2.4）
- 改檔：`momentum/Analysis/ic_filter_orchestrator.py`、`tests/momentum/Analysis/test_ic_1a_cut1_split.py`
- 實作：flag-on 時 stage0 後解析 effective horizon、建立 positional chronological holdout、驗 `purge_gap >= horizon`、跑 `validate_split_pair_integrity`、以 time_bounds 重導 stage mask；flag-off 保持原順序
- 驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py -k 'holdout or purge or mask or pipeline or horizon' -q`
- 結果：PASS（6 passed, 6 deselected）
- 補跑：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_analyze_split_gap_blocked tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_split_valid_passes -q` → PASS（2 passed）
- 解耦：`grep -rE "from api\\." momentum/ | wc -l` → 0
- 問題：pytest `-k` 未選到 gap/valid 明列測試，已額外補跑

## B3 — BLOCKED
- 批次：B3（Task 3.1-3.5）
- 改檔：`momentum/Analysis/data_preprocessor.py`、`momentum/Analysis/ic_filter_orchestrator.py::_stage1_preprocessing`、`tests/momentum/Analysis/test_ic_1a_cut1_leakage.py`
- 已實作：`fit_mask` 介面；winsorize/standardize/coverage/remove_constant 使用 train-only fit；mask 長度不符或全 False fail-closed；`_stage1_preprocessing` 透傳 `fit_mask`
- 驗收第 1 輪：`pytest tests/momentum/Analysis/test_ic_1a_cut1_leakage.py -k 'train_only or legacy_no_mask' -q` → FAIL collection，Python 3.9 不支援 `dict | None`
- 第 1 輪改動：測試型別改 `Optional[dict]`
- 驗收第 2 輪：同命令 → FAIL，3 passed / 2 failed
- 第 2 輪失敗摘要：`test_coverage_from_train_only`、`test_preprocess_legacy_no_mask_unchanged` 皆因測試 helper 設 `max_fill_forward=0` 觸發 pandas `ValueError: Limit must be greater than 0`
- 解耦：`grep -rE "from api\\." momentum/ | wc -l` → 0
- 卡點：派工限制「≤2 輪卡關即停手」，未進第三輪修正

STATUS: BLOCKED — B3 第二輪驗收仍 failed；疑似測試 helper 的 `max_fill_forward=0` 與 pandas `ffill(limit=0)` 不相容，需 Claude 核准後續處置

## B3 — PASS（續做，fixture 根因修正）
- 批次：B3（Task 3.1-3.5）
- 改檔：`tests/momentum/Analysis/test_ic_1a_cut1_leakage.py`
- 修正：測試 fixture 將無效 `max_fill_forward=0` 改為真實有效預設 `3`；coverage 測試仍用 test 段注入 NaN 驗 train-only 判據
- 驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_leakage.py -k 'train_only or legacy_no_mask' -q`
- 結果：PASS（5 passed）
- 解耦：`grep -rE "from api\." momentum/ | wc -l` → 0
- 問題：none

## B4 — PASS
- 批次：B4（Task 4.1-4.4）
- 改檔：`momentum/Analysis/ic_filter_orchestrator.py`、`tests/momentum/Analysis/test_ic_1a_cut1_oos.py`
- 實作：flag-on OOS scope；rolling 使用 train+test warmup 後只保留 test end-index；stage5 metrics/summary/threshold 用 test subset；stage6 redundancy/corr 用 test rows；report metadata 標 scope
- 驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q`
- 結果：PASS（5 passed）
- 解耦：`grep -rE "from api\." momentum/ | wc -l` → 0
- 問題：none

## B5 — PASS
- 批次：B5（Task 5.1/5.2/6.1/6.2）
- 改檔：`momentum/Analysis/ic_filter_orchestrator.py`、`tests/momentum/Analysis/test_ic_1a_cut1_oos.py`、`tests/momentum/Analysis/test_ic_1a_cut1_golden.py`
- 實作：flag 仍預設 OFF；flag-on path 與 config_override 驗證；G-OLD flag-off deep-equal baseline（僅 pop `generated_at`）；未重凍 baseline；解耦驗證通過
- 驗收第 1 輪：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py -q` → FAIL（24 passed / 1 failed；`test_flag_toggles_path` 測試 helper 用錯無 `close` 欄資料）
- 第 1 輪修正：測試改用同檔 `_label(features)` 產生 labels，不改生產碼
- 驗收第 2 輪：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py -q` → PASS（25 passed；含 G-OLD deep-equal）
- 解耦：`grep -rE "from api\." momentum/ | wc -l` → 0；`./scripts/check_decoupling_phase4.sh` → PASS（含 135 strategy tests）
- data_cache：`git diff --name-only -- data_cache` → empty
- 問題：none

STATUS: DONE — B1-B5 complete, flag default OFF, G-OLD deep-equal PASS
