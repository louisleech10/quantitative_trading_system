# Batch 3 redfix — 跨家族 Code Review（Composer 2.5）

**Range**: `6fbc469..935b24f`（2 commits）  
**實作**: Codex | **合約**: `docs/BATCH3_TEST_TRIAGE.md` 委員會三方裁定 + B 殭屍剩餘簇  
**Reviewer**: Cursor Agent（read-only；未改 `momentum/` `api/` `frontend/` `docs/` `tests/`）

---

## 摘要

裁定項 Q1/Q3/Q4/Q5 與殭屍分簇修復**整體對齊合約**；production winsorize 路徑零 diff；未發現放寬容差或刪除核心資料正確性斷言之假綠。抽驗 **103 passed**（batch3 相關 targeted pytest，23.65s）。

**Verdict**: **APPROVE**（附 2 項 MINOR 建議，非阻擋合併）

---

## (1) Q1 — `last_generated_at` / retention

| 檢查點 | 結果 | 證據 |
|--------|------|------|
| registry add 保留 `created_at` / `alias` | ✅ | `feature_registry.py` merge 僅 preserve `("alias", "size_bytes", "created_at")` |
| 同 key upsert 刷新 recency | ✅ | `last_generated_at` 不在 preserve 列表；production `feature_factory._registry.add()` 不傳 timestamp → `setdefault(created_at, time.time())` + `setdefault(last_generated_at, …)` → merge 後 `last_generated_at` 為新 `time.time()` |
| `auto_cleanup` / `find_latest` 改依 `last_generated_at` | ✅ | `run_lifecycle.py:147-149`, `feature_registry.py:129-131` |
| legacy 無欄位 fallback | ✅ | `.get("last_generated_at", entry.get("created_at", 0))`；API `_registry_timestamp_iso(entry.get("last_generated_at", entry.get("created_at")))` |
| 非破壞遷移 | ✅ | 新 entry `setdefault("last_generated_at", created_at)`；磁碟舊 JSON 無欄位仍可用 fallback |
| RunInfo DTO | ✅ | `api/models/feature_factory_models.py` 新增 `last_generated_at`；`list_runs` 輸出 ISO |
| 測試證明重跑保留 + alias/created_at 不變 | ✅ | `test_cleanup_refreshes_regenerated_legacy_run_recency`：`created_at==1.0`, `last_generated_at==100.0`，cleanup 後 `cfg_0` 仍在；`test_phase2` upsert 斷言 split |

**MINOR-1**：刷新依賴「caller 不傳 `last_generated_at`」的 setdefault 語義，未在 `mutate()` 內顯式 `merged["last_generated_at"] = time.time()`。目前三處 production `add()` 皆不傳該欄，行為正確；建議後續小 patch 硬化防未來 caller 誤傳 stale 值。

---

## (2) Q3 — winsorize causal 拆分

| 檢查點 | 結果 | 證據 |
|--------|------|------|
| production 未改 | ✅ | `git diff 6fbc469..935b24f -- momentum/FeatureEngineering/preprocessing/` 空 |
| causal 比 rolling PIT oracle | ✅ | `test_transform_single_optimized_df_end_to_end` 使用 `rolling_quantile_2d_legacy` + `pp._rolling_window()` / `_rolling_min_periods` |
| non-causal 獨立測試 | ✅ | 新 `test_transform_single_optimized_df_noncausal_matches_full_sample`，`causal_preprocessing=False` 比 `_winsorize_2d_inplace` |
| future-perturbation 不變量 | ✅ | 末行 `perturbed[-1]=1e6` 後 `result[:-1]` vs `perturbed_result[:-1]`，`rtol=atol=1e-5` |
| 容差未放寬 | ✅ | 仍 `1e-5` / `1e-5`；舊 global-sample 比較已移除（原為錯誤 oracle） |

---

## (3) Q4 — golden schema hash only

| 檢查點 | 結果 | 證據 |
|--------|------|------|
| 僅 bump hash + schema 綁定 | ✅ | `g1_baseline_fingerprint.json` diff 僅 `schema_version: raw_v2` + `feature_schema_hash` → `93ef6756…`；其餘 `groups`/`dtype`/`row_count` 未動 |
| 測試 allowlist _extractor 同步 | ✅ | `test_v2_timestamp_golden._manifest_allowlist` 加入 `schema_version`（與 manifest 對齊，非弱化 golden） |

---

## (4) Q5 — optimization E2E 改查 manifest

| 檢查點 | 結果 | 證據 |
|--------|------|------|
| 不灌 `feature_names` 進 response | ✅ | production `feature_factory` 未改；測試改 `_manifest_columns(manifest)` 讀 CGSA/L7 manifest |
| partial failure 斷言加強 | ✅ | `test_pipeline_partial_engine_failure` 保留 `tr_` 有 / `ms_` 無，**新增** `failed_engines==("microstructure",)` + `LayerStatus.engine_partial` |
| 隔離 tmp_path | ✅ | `FFACT_CGSA_WORK_DIR` / `FFACT_FEATURE_REGISTRY_PATH` + `FeatureStorage`/`FeatureRegistry` on tmp |

---

## (5) 防假綠 — 殭屍各簇

| 簇 | 判定 | 證據 |
|----|------|------|
| **feature_storage mixed dtype** | ✅ 未弱化 | 僅 manifest dtype `float32`→`mixed`（對齊 batch1 報告語義）；**保留** `df["btc_price_feature"].dtype==float32`、`isinf==0`、值 `[60000,70000,80000]` |
| **memory_chunking merge** | ✅ 未弱化 | 補 `source_tf`/`primary_tf` 必填參數；leakage 斷言改 `valid=~source_ts.isna()` 後比較（修正 NaN 列誤判，非放寬） |
| **cgsa_resume** | ✅ 對齊 production gate | fixture 換真 `FeatureStorage`/`FeatureRegistry`；resume 測試補 L7 complete manifest（對應 `_prepare_cgsa_registry` L7 gate，`feature_factory.py:959-988`） |
| **l7_parallel_persist + l7_persist_perf** | ✅ 簽名 lag | tuple 5 元組 + `compression_level`；`assert len(persisted_paths) <= 3` **仍在** perf 測試 |
| **hardware** | ✅ 對齊 tier config | `l65_workers` 4→2 對 `_WORKERS_BY_TIER["8gb"]=2`；API 斷言擴充 `applied_settings`/`tier_table` 等實際 response 鍵 |
| **config defaults** | ✅ 對齊 schema | `PreprocessingConfig.enabled: bool = True`（`feature_config.py:232`）；舊測試 False 為滯後 |
| **optimization_e2e** | ✅ 加強 | 見 Q5；`assert not any(ms_)` **仍保留**（L219） |
| **winsorize** | ✅ 見 Q3 | — |

未發現 BLOCKING 級假綠或資料正確性 regression。

---

## (6) phase_d 刪 7 測試

| 檢查點 | 結果 | 證據 |
|--------|------|------|
| 文件確實不在 canonical 路徑 | ✅ | `git show 6fbc469:docs/FRONTEND_INTEGRATION_GUIDE.md` → fatal（base commit 已無此檔）；現存 `docs/Archived/FRONTEND_INTEGRATION_GUIDE.md` |
| 刪除 TestD5FrontendIntegrationGuide | ✅ 合理 | 原測試 `FileNotFoundError`（triage B 表）；刪 class 而非改指向 Archived 符合合約「更新指向或刪」 |

**MINOR-2**：若仍要文件回歸覆蓋，可改測 `docs/Archived/FRONTEND_INTEGRATION_GUIDE.md`；非本次裁定必須。

---

## 測試抽驗

```text
pytest tests/feature_engineering/test_run_lifecycle.py::test_cleanup_refreshes_regenerated_legacy_run_recency \
  tests/feature_library/test_phase2.py::test_registry_upserts_same_symbol_timeframe_config_hash \
  tests/test_winsorize_partition_opt.py::test_transform_single_optimized_df_end_to_end \
  tests/test_winsorize_partition_opt.py::test_transform_single_optimized_df_noncausal_matches_full_sample \
  tests/feature_engineering/test_v2_timestamp_golden.py \
  tests/momentum/test_feature_factory_optimization_e2e.py \
  tests/momentum/test_feature_storage.py::test_cgsa_parquet_uses_float32_when_values_exceed_float16 \
  tests/momentum/test_memory_chunking.py::TestMultiTFColumnBatchMerge \
  tests/test_cgsa_resume.py tests/test_phase_d_granular_control.py \
  tests/test_feature_factory_config.py tests/test_hardware_api.py \
  tests/test_hardware_utils.py tests/test_l7_parallel_persist.py -q
→ 103 passed in 23.65s
```

未跑全 suite（sandbox 已知 API import/Binance ping 收集錯誤；與 Codex handoff 一致）。

---

## Findings 彙總

### BLOCKING
無。

### MAJOR
無。

### MINOR
1. **Q1 硬化**：`FeatureRegistry.add()` upsert 建議顯式 `merged["last_generated_at"] = time.time()`，避免未來 caller 傳 stale 值繞過刷新。
2. **phase_d**：刪測試可接受；可選 follow-up 改綁 Archived 路徑恢復文件回歸（非阻擋）。

---

## 結構化欄位

```
ASSUMPTIONS_VERIFIED: production add() 三處不傳 timestamp→last_generated_at 刷新；PreprocessingConfig.enabled 預設 True；FRONTEND_INTEGRATION_GUIDE 在 6fbc469 已不存在於 docs/ 根
TESTS_RUN: targeted batch3 pytest 103 passed (23.65s)
FAILURES_SEEN: none
SCOPE_CHANGES: none (review-only)
NUMERIC_OR_SCHEMA_IMPACT: Q1 新增 registry/API 欄位 last_generated_at（裁定內）；Q4 golden hash only；其餘 test-only
```

STATUS: APPROVE
