# FF_FAILOPEN_UNIFIED Batch5 (Phase5) — 2026-06-11

## Task 5.1 Consumer gate [G-1~G-3]

- 新增 `momentum/FeatureEngineering/consumer_gate.py`：`ConsumerPolicy` strict/browse、`assert_consumer_run_status`、`assert_required_columns_present`、`intersect_columns_without_masking`、`TrainingReadError`、`is_run_status_cacheable`（僅 `complete` 可 cache）。
- `feature_reader.py`：`load_manifest_v2` / `load_columns_v2` / `stream_groups_v2` 支援 `consumer` + `allow_partial`；browse 不擋讀、strict 拒非 complete（partial 需顯式 flag）。
- `ic_engine.py`：`_validate_l7_raw_manifest` 以 `ICReadError` + `assert_consumer_run_status` fail-closed。
- `feature_library.py`：`load_for_training` / `load_multi(for_training=True)` 走 strict gate + 欄位完整性。
- `cross_symbol_training_service.py` / `xgboost_batch_service.py`：catch `TrainingReadError`；交集用 `intersect_columns_without_masking`。

## Task 5.2 Cache/resume + flag 契約 [G-4][C-1][C-2]

- `FactoryConfig` 正式 6 欄位（§C-2 docstring）；`config_hash` pop 四個 `allow_partial_*`，保留 `max_*`。
- `feature_factory._try_load_cache`：metadata + L7 manifest `run_status` 雙重 gate。
- CGSA resume（`feature_factory` ~892）：L7 `run_status` 非 complete → 跳過 resume、重生成。
- API：`FailOpenGateFlags` + `FeatureGenerateRequest.fail_open`；TS：`FailOpenGateFlags` + `FeatureFactoryConfig` 六欄位。

## Follow-up: test isolation

- `tests/feature_engineering/conftest.py`：autouse 將 `FFACT_CGSA_WORK_DIR`、`FFACT_FEATURE_REGISTRY_PATH` 導向 `tmp_path`。
- `feature_registry.py`：尊重 `FFACT_FEATURE_REGISTRY_PATH`。

## 驗收外修復（Batch4 遺留）

- `api/services/feature_factory_service.py::register_hdf5_for_browse`：`record` 未定義 → 改用 `result.metadata.quality_status`（否則 5 個 API 測試 NameError）。

## ASSUMPTIONS_VERIFIED

- Gate-A golden 58 tests 全綠（scratch 隔離不影響 baseline hash）。
- `grep -r "from api\." momentum/` → 0。
- `is_run_status_cacheable("complete")` only True。

## TESTS_RUN

- `pytest tests/feature_engineering/test_failopen_*.py -q` → **58 passed** (~195s)
- `pytest tests/api/ -q` → **205 passed**
- `cd frontend && npm run build` → **OK**

## FAILURES_SEEN

- IC 測試初版因 `label_horizon` / 空 `total_features` 失敗 → 改測 `_validate_l7_raw_manifest` + fixture 補 `total_features`。
- API 5 failures：`record` NameError（HEAD 既有）→ 修 `feature_factory_service.py`。

## SCOPE_CHANGES

- `api/services/feature_factory_service.py`（驗收阻斷；Batch4 typo，非 Batch5 設計檔）

## NUMERIC_OR_SCHEMA_IMPACT

- 無 healthy byte 變更；新增 API/TS 可選 `fail_open` 欄位；consumer 行為對 IC/training 更嚴（預設 fail-closed）。

## FROZEN_TESTS

- 未改動既有 failopen 斷言門檻；`docs/FF_FAILOPEN_FROZEN_TESTS.md` 無需更新。

---

## Round2 — Codex BLOCKING 封死（2026-06-11）

### 修復摘要

1. **Legacy reader strict gate**：`feature_reader._resolve_manifest_v2` 在 legacy adapter 後呼叫 `assert_consumer_run_status(consumer="strict")`；`run_status=legacy` 對 IC/training 拒。
2. **IC 快取 manifest gate**：`ic_engine._try_reuse_cached_ic_scores` 驗 `source_run_status`（fingerprint + cache JSON）；缺 status → unknown 拒；不再預設 `quality_status=complete`。
3. **XGBoost TrainingReadError**：`xgboost_batch_service` 分離 `TrainingReadError`（re-raise fail-closed）與 `FeatureNotFoundError`（可 fallback）；僅 `allow_partial_training` 顯式放行。
4. **CGSA resume / legacy cache**：L7 manifest 不存在 → 不 resume、不 cache hit；`quality_status=complete` 無 completeness 欄 → `unknown`（`consumer_gate.metadata_has_completeness_evidence`）。
5. **API fail_open 接線**：`feature_factory_service._merge_fail_open_flags` 併入 `config_override` 再 `_resolve_config_override`；端到端測試驗 allow_partial 放行/不帶拒。

### 改動檔

- `momentum/FeatureEngineering/consumer_gate.py`
- `momentum/FeatureEngineering/feature_reader.py`
- `momentum/Analysis/ic_engine.py`
- `momentum/FeatureEngineering/feature_factory.py`
- `api/services/xgboost_batch_service.py`
- `api/services/feature_factory_service.py`
- `tests/feature_engineering/test_failopen_consumer.py`
- `tests/api/test_failopen_api_flags.py`（新增）
- `tests/api/test_xgboost_training_gate.py`（新增）

### ASSUMPTIONS_VERIFIED

- Legacy manifest `run_status=legacy` + `consumer=strict` → `TrainingReadError`（實測 `test_legacy_reader_strict_rejects_ic_and_training`）。
- IC cache 無 `source_run_status` → miss（`test_ic_cache_rejects_missing_source_run_status`）。
- `quality_status=complete` 無 completeness 欄 → `effective_run_status=unknown`（`test_metadata_complete_without_completeness_is_unknown`）。
- `grep -r "from api\." momentum/` → 0。

### TESTS_RUN

- `pytest tests/feature_engineering/test_failopen_consumer.py tests/feature_engineering/test_failopen_producer.py tests/feature_engineering/test_failopen_manifest.py tests/feature_engineering/test_failopen_layers.py tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_contract.py tests/api/ -q` → **273 passed** (~206s)
- `cd frontend && npm run build` → **OK**（round1 已驗，round2 無前端改動）

### FAILURES_SEEN

- `test_cache_gate_partial_unknown_miss_complete_hit`：`complete` metadata 缺 completeness 欄 → 改 fixture 補齊。
- `test_legacy_reader_strict_rejects_ic_and_training`：預期 `ICReadError` 實為 `TrainingReadError` → 斷言對齊實際路徑。
- `test_failopen_api_flags` 初版 `asyncio.run()` 污染 event loop → 10 個 batch API 測試連帶失敗 → 改 `@pytest.mark.asyncio` + mock executor。

### SCOPE_CHANGES

- none（均在派工 scope 內）

### NUMERIC_OR_SCHEMA_IMPACT

- IC cache fingerprint 新增 `source_run_status` 鍵（舊 cache 自然 miss，非數值變更）。
- `ic_selected.json` 頂層寫入 `source_run_status`（schema 擴充，向後相容）。

### FROZEN_TESTS

- 未弱化既有斷言；`test_cache_gate_partial_unknown_miss_complete_hit` 的 complete case 補 completeness 欄以符合 Batch3 語義（非降門檻）。
