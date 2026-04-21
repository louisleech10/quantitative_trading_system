# FEATURE_OPTIMIZATION_TODO 驗證報告 V1

> **驗證日期**: 2026-04-22  
> **驗證對象**: `docs/FEATURE_OPTIMIZATION_TODO.md`  
> **參照 SPEC**: `docs/FEATURE_OPTIMIZATION_SPEC.md` V1  
> **驗證範圍**: Batch 1 = Phase 0 (Task 0.1, 0.2) + Phase 1 (Task 1.1, 1.2, 1.3)  
> **驗證結論**: **Batch 1 已完成；Batch 1 直接相關驗證全數通過。全域 smoke test 仍有 1 個 Batch 1 範圍外既有失敗。**

---

## 驗證摘要

| 項目 | 狀態 | 說明 |
|---|---|---|
| Phase 0 / Task 0.1 | ✅ PASS | `hardware_utils.py` 已新增，`get_memory_tier()` 已驗證 |
| Phase 0 / Task 0.2 | ✅ PASS | `get_tier_config()` 與 tier 常數已驗證 |
| Phase 1 / Task 1.1 | ✅ PASS | CGSA 決定性路徑已實作並驗證 |
| Phase 1 / Task 1.2 | ✅ PASS | `config_hash` 已由呼叫端正確傳入 |
| Phase 1 / Task 1.3 | ✅ PASS | 損壞 manifest fallback 已驗證 |
| Batch 1 lint | ✅ PASS | 指定檔案 `ruff check` 通過 |
| Batch 1 decoupling | ✅ PASS | `grep -r "from api\." momentum/ | wc -l` = 0 |
| Batch 1 regression check | ✅ PASS | `test_full_pipeline_overhead` 通過 |
| 全域 smoke test | ⚠️ PARTIAL | 首個失敗為 Batch 1 範圍外既有失敗 |

---

## 實際修改檔案

- `momentum/FeatureEngineering/feature_factory.py`
- `momentum/FeatureEngineering/utils/__init__.py`
- `momentum/FeatureEngineering/utils/hardware_utils.py`
- `tests/test_hardware_utils.py`
- `tests/test_cgsa_resume.py`
- `docs/FEATURE_OPTIMIZATION_TODO.md`

---

## Task 完成明細

### Phase 0

#### Task 0.1 — `get_memory_tier()`

- 已新增 `momentum/FeatureEngineering/utils/hardware_utils.py`
- 已實作 `TIER_THRESHOLDS`
- 已實作 `get_memory_tier()`
- 支援 `FFACT_MEMORY_TIER=auto|8gb|16gb|24gb|32gb|其他原值`
- `psutil` 不可用時會 fallback 到 `8gb`
- 未引入 `api/` import
- 未加入 logging 或 config file 讀取副作用

#### Task 0.2 — `get_tier_config()`

- 已新增 `_WORKERS_BY_TIER`
- 已新增 `_CGSA_BUFFER_BY_TIER`
- 已新增 `_L7_WORKERS_BY_TIER`
- 已新增 `_CHUNK_BARS_BY_TIER`
- 已實作 `get_tier_config(tier)`
- 未知 tier 會回退到 8GB 的保守預設

### Phase 1

#### Task 1.1 — `_prepare_cgsa_registry()` 決定性路徑

- 已將隨機暫存路徑改為決定性路徑
- 路徑格式為 `data_cache/cgsa_work/{safe_symbol}_{safe_tf}_{hash_prefix}`
- 已對 symbol/timeframe 做安全字元清理
- 保留 `FFACT_CGSA_WORK_DIR` 最高優先權覆蓋
- 額外收斂：最終改為絕對路徑，避免 cwd 影響 manifest atomic write

#### Task 1.2 — 呼叫端補傳 `config_hash`

- `generate_features()` 已補傳 `config_hash`
- `config_hash is None` 路徑已以空字串防禦性處理

#### Task 1.3 — 損壞 manifest fallback

- manifest 存在時會優先嘗試 `resume_from_manifest()`
- 空檔、JSON 損壞、缺少必要 key、resume 過程預期錯誤時，會 warning 後 fresh start
- 不會自動刪除損壞 manifest
- 額外收斂：`force_regenerate=True` 時不重用舊 manifest，避免 fresh run 被 resume 污染

---

## 驗證命令與結果

### 1. Ruff lint

**命令**

```bash
./venv/bin/ruff check \
  momentum/FeatureEngineering/feature_factory.py \
  momentum/FeatureEngineering/utils/hardware_utils.py \
  momentum/FeatureEngineering/utils/__init__.py \
  tests/test_hardware_utils.py \
  tests/test_cgsa_resume.py
```

**結果**

- Exit code: `0`
- 結論: PASS

**通過條件**

- 指定 Batch 1 相關檔案 lint 為 0 error

---

### 2. Batch 1 指定單元測試

**命令**

```bash
./venv/bin/pytest tests/test_hardware_utils.py tests/test_cgsa_resume.py -v
```

**結果**

- Exit code: `0`
- 統計: `17 passed`
- 結論: PASS

**涵蓋內容**

- `T0.1` 自動偵測記憶體 tier
- `T0.2` 環境變數覆蓋
- `T0.3` tier config key 完整性
- `T0.4` unknown tier fallback
- `T0.B1` `FFACT_MEMORY_TIER=auto`
- `T0.B2` `FFACT_MEMORY_TIER=""`
- `T0.B3` psutil unavailable fallback
- `T1.1` 決定性 CGSA 路徑
- `T1.2` manifest 存在時 resume
- `T1.3` `config_hash` 傳遞
- `T1.4` corrupt manifest fallback
- `T1.B1` empty config hash
- `T1.B2` 特殊字元 symbol 清理
- `T1.B3` `FFACT_CGSA_WORK_DIR` 覆蓋
- `T1.B4` empty manifest fallback
- `T1.B5` missing `.npy` in manifest fallback
- 額外回歸: `force_regenerate=True` 時跳過 resume

**非 PASSED 項目說明**

- 無 failed
- 無 skipped
- 無 deselected
- 測試中出現的 warning 屬預期 fallback 行為，例如 corrupt manifest 與 missing `.npy` 被安全跳過

---

### 3. Batch 1 回歸效能檢查

**命令**

```bash
./venv/bin/pytest tests/momentum/test_feature_factory_optimization_perf.py::test_full_pipeline_overhead -q
```

**結果**

- Exit code: `0`
- 統計: `1 passed`
- 結論: PASS

**通過條件**

- Batch 1 的 CGSA 路徑修補不得破壞 pipeline overhead / perf 檢查

**驗證到的回歸點**

- fresh run 不會誤吃舊 manifest
- 絕對路徑下 manifest atomic write 正常

**非 PASSED 項目說明**

- 測試過程存在大量指標參數 default warning 與高 NaN ratio warning
- 這些 warning 為既有測試資料/現有 feature pipeline 行為，不影響本測試 PASS 判定

---

### 4. 解耦規則 R1 檢查

**命令**

```bash
grep -r 'from api\.' momentum/ | wc -l
```

**結果**

- Exit code: `0`
- 輸出: `0`
- 結論: PASS

**通過條件**

- `momentum/` 內不得新增 `from api.` import

---

### 5. 全域 smoke test

**命令**

```bash
./venv/bin/pytest tests/ -m "not slow" -x -q
```

**結果**

- Exit code: `1`
- 統計: `1 failed, 884 passed, 24 skipped, 19 deselected, 294 warnings`
- 首個失敗:

```text
tests/momentum/test_feature_preprocessor.py::test_transform_fixed_order FAILED
```

**失敗判定**

- 這個失敗不屬於 Batch 1 範圍
- 本輪未修改 `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- 因使用者約束「只允許在 TODO 範圍內修補」，未對此失敗進行越界修補

**失敗內容摘要**

- 測試期待固定呼叫順序以 `_apply_winsorization` 起始，並包含 `_apply_adaptive_zscore`
- 實際呼叫順序以 `_apply_rank_transform` 起始

**非 PASSED 項目說明**

- `failed`: 1 個，為 `tests/momentum/test_feature_preprocessor.py::test_transform_fixed_order`
- `skipped`: 24 個，屬既有測試選擇結果
- `deselected`: 19 個，來自 `-m "not slow"` 的正常測試篩選
- `warnings`: 294 個，主要類型如下：
  - pandas `fillna(method=...)` FutureWarning
  - `.shift().fillna(False)` 的 downcasting FutureWarning
  - Optuna ExperimentalWarning / deprecated warning
  - sklearn / shap / numpy runtime warnings

**結論**

- Smoke test 未全綠
- 但首個失敗已定位為 Batch 1 範圍外既有問題

---

## Batch 1 Gate 判定

### 已通過

- `T0.1~T0.4`
- `T0.B1~T0.B3`
- `T1.1~T1.4`
- `T1.B1~T1.B5`
- `grep -r "from api\." momentum/` = 0

### 尚未勾選 / 未驗證

- `C1` 正常執行 pipeline 與 V7 Baseline 數值等價
- 手動中斷 L6.5 後 resume 的真實場景驗證

### Gate 結論

- **若以 Batch 1 直接要求判定：PASS**
- **若以全域 smoke 0 error 判定：未達成，且阻塞點為 Batch 1 範圍外既有失敗**

---

## 文件同步狀態

- `docs/FEATURE_OPTIMIZATION_TODO.md` 已同步勾選 Batch 1 內已完成且已驗證的 checkbox
- 未驗證項目維持未勾，避免文件狀態失真

---

## 最終結論

Batch 1 的實作、指定驗證、回歸檢查與解耦檢查都已完成並通過。  
目前唯一未通過的是全域 smoke test 的既有失敗 `tests/momentum/test_feature_preprocessor.py::test_transform_fixed_order`，不屬於 Batch 1 / Phase 0 / Phase 1 的 TODO 修補範圍。