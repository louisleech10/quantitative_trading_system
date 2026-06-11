# FF_FAILOPEN_UNIFIED Batch2 (Phase 2) — Task 2.1 + 2.2

**日期**: 2026-06-11  
**範圍**: `docs/FF_FAILOPEN_UNIFIED_SPEC.md` §P Phase2、`docs/FF_FAILOPEN_UNIFIED_TODO.md` Task 2.1 / 2.2

## 完成內容

### Task 2.1 — L1–L6 typed `LayerExecutionResult`
- `momentum/FeatureEngineering/feature_factory.py`：L1–L6 各層 per-engine / whole-layer `try/except`，`failed_engines` + `derive_status`；L5 reference fetch 例外 → `dependency_failed`；L3 streaming 成功但空輸出 → `offloaded_to_registry`。
- `_execute_layer1_6`：L2–L6 不再經 `_safe_execute` 吞錯；外層例外 handler 使用 `configured_engines=1`（避免 `derive_status` 誤判 `empty_disabled`）。
- `_safe_execute` 保留給 L6.5 / IC-first 等路徑。
- `_derived_operator_engine_cls()`：L2 engine class 經 module global 解析，測試可 monkeypatch `DerivedOperatorEngine`。
- 新測試 `tests/feature_engineering/test_failopen_layers.py`：optional partial、required fail、all engines failed（serial）、L2 parallel partial、whole-layer exception、Gate-A golden、zero-copy memmap spill。

### Task 2.2 — 全 caller `.data` 原子遷移
- `generate` / `_run_l1_l6_for_ic_first`：`_execute_layer1_6(...).data`。
- `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`：`_run_tf_l1_l6_results()`、`_collect_layer_counts()`（L3 offloaded 讀 registry）、serial/parallel/legacy/worker 路徑。
- 測試/腳本：`test_feature_factory_batch2b.py`、`batch2e.py`、`test_golden_output_generation.py`、`profile_gate3_to_4.py`、`profile_l23_hotspots_postopt.py`。
- Multi-TF mock：`tests/_helpers/stub_layer_execute.py` + 相關 MTF 測試 stub 更新。

## 測試結果

| 命令 | 結果 |
|------|------|
| `pytest tests/feature_engineering/test_failopen_layers.py tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_contract.py -q` | 24 passed, 2 skipped |
| `pytest` 上述 + batch2b/batch2e/golden_output | 48 passed, 2 skipped |
| `pytest` 上述 + multi_tf / mtf_align / searchsorted_perf | 29 passed |
| `grep -r "from api\." momentum/` | 0 |

全量 `pytest -q`（~737s）：44 failed / 2594 passed — 失敗多為既有（hardware、phase_d 模板缺失、config defaults、L7 persist 等），與 Batch2 無直接關聯。修復前全量 log 有 3 條 `AttributeError`（`test_l2_timing_log_emitted` + polars dummy）；修復後該測試及驗收集全綠。

## 測試斷言變更（已記 `docs/FF_FAILOPEN_FROZEN_TESTS.md`）
- `test_failopen_contract.py`：3 則 L2/L3/required-fail 期望改為 `LayerExecutionResult` + `layer_failed`。
- `test_t2b8`：registry groups L3→L1（對齊預設 `fracdiff_layers=L1,L2`）；`_fake_fracdiff` 接受 `source_layer`。
- `test_l2_timing_log_emitted`：dummy 加 `OPERATOR_CATEGORIES`；`FFACT_USE_POLARS=0`。

## 剩餘風險
- 全量 pytest 仍有非 Batch2 失敗項；未逐項歸因修復。
- Polars 啟用時，僅 patch `compute_all` 的 L2 dummy 測試需顯式關 polars 或實作 `compute_all_polars`。
- Phase 4 producer gate 未實作（依 SPEC 刻意延後）。

## 主要改動檔案
- `momentum/FeatureEngineering/feature_factory.py`
- `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`
- `tests/feature_engineering/test_failopen_layers.py`（新）
- `tests/feature_engineering/test_failopen_contract.py`
- `tests/_helpers/stub_layer_execute.py`（新）
- `tests/test_feature_factory_batch2b.py`, `batch2e.py`, `test_golden_output_generation.py`
- `tests/test_multi_tf_generator.py`, `test_primary_self_align_skip.py`, `test_multi_tf_golden_equivalence.py`, `tests/feature_engineering/test_mtf_align_golden.py`, `tests/performance/test_searchsorted_perf.py`
- `scripts/profile_gate3_to_4.py`, `scripts/profile_l23_hotspots_postopt.py`
- `docs/FF_FAILOPEN_FROZEN_TESTS.md`（新）

---

## Round2 — Codex review 6 項 BLOCKING（2026-06-11）

### 修法摘要（逐 finding）

| # | Finding | 修法 | 測試證據 |
|---|---------|------|----------|
| 1 | zero-copy 假綠（自比 shares_memory + frame_equal 放水） | `_ensure_float32` 全 float32 時 early-return 保 `result.data is original_df`；spill 測試 capture `create_temp_memmap` base 後 `shares_memory(spilled_values, memmap_base)` | `test_zero_copy_spill_preserves_memmap_sharing` PASSED |
| 2 | L6 全 sub-engine 關 → `empty_disabled` | `not sub_tasks` 時 `configured_engines=1`（layer 啟用、present=0） | `test_l6_all_subengines_disabled_empty_not_applicable` `== empty_not_applicable` |
| 3 | L5 `aligned.empty` 裸 `pd.DataFrame` | 改 `_build_layer_result(configured=1, present=0)` → `empty_not_applicable` | 含於 L5 wiring；contract 真值表已有覆蓋 |
| 4 | `compare_script.py` 漏 `.data` | `FeatureFactory.layer_data(_layer1_atomic_indicators(...))` | caller 腳本編譯路徑 |
| 5 | Gate-A 靜默 skip | `test_layer_golden_matches_baseline` subprocess 帶 `PYTHONHASHSEED=0` 重入 | 無 seed 父進程跑：37s PASSED；驗收集 27 passed **0 skipped** |
| 6 | 缺 layer-level wiring 測試 | 新增 L3 offload / L5 dependency_failed / L6 empty_not_applicable 三條 `==` 斷言 | 三測試均 PASSED |

### 驗收（Round2）

| 命令 | 結果 |
|------|------|
| `PYTHONHASHSEED=0 pytest tests/feature_engineering/test_failopen_layers.py tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_contract.py -q` | **27 passed, 0 skipped** |
| 上述 + caller bundle（batch2b/batch2e/golden_output/multi_tf/mtf_align/searchsorted） | **82 passed** |
| `pytest ...::test_layer_golden_matches_baseline`（父進程無 PYTHONHASHSEED） | PASSED（subprocess Gate-A） |
| `grep -r "from api\." momentum/` | 0 |

### Round2 改動檔
- `momentum/FeatureEngineering/feature_factory.py`（L5/L6 wiring、`_ensure_float32` early-return）
- `tests/feature_engineering/test_failopen_layers.py`（Gate-A subprocess、zero-copy、3 wiring tests）
- `_staging_to_remove/one_off_scripts/compare_script.py`（`.data` unwrap）
- `docs/FF_FAILOPEN_FROZEN_TESTS.md`（zero-copy + Gate-A 斷言變更登記）
