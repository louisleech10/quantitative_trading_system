# Batch3 委員會技術調查 — Composer 獨立版

**日期**: 2026-06-15  
**性質**: 讀取型調查（未改任何產品/測試檔）  
**背景**: `docs/BATCH3_TEST_TRIAGE.md`  
**驗證命令**: 見各問 `TESTS_RUN`

---

## Q1 — Retention：`created_at` merge-preserve vs `auto_cleanup` 排序

### 結論

**建議選 B**：新增 `last_generated_at`（或等價欄位），`auto_cleanup` /「最近未命名」語義改依此排序；`created_at` 維持 batch2 決策的「首次註冊時間」並繼續 merge-preserve。  
**不建議 C**（現狀）：重跑同 `config_hash` 不刷新 recency，剛用過的 run 可能被當舊的刪除。  
**不建議 A**（重刷 `created_at`）：能修 retention，但會破壞「首次建立」語義，且與 `find_latest()` 等「created_at = 歷史錨點」的既有契約混淆。

### 證據

| 位置 | 內容 |
|------|------|
| `momentum/FeatureEngineering/feature_registry.py:86-104` | `add()` merge-preserve 明確保留既有 `alias` / `size_bytes` / **`created_at`** |
| `momentum/FeatureEngineering/run_lifecycle.py:141-148` | `auto_cleanup()` 對未命名 entry 依 **`created_at` 降序**，第 6 名起刪除 |
| `momentum/FeatureEngineering/feature_registry.py:124-128` | `find_latest()` 同樣用 **`created_at` 最大** |
| `docs/BATCH2_RUN_LIFECYCLE_DECISION.md:13` | batch2 決策：rerun 不清 `alias/created_at` |
| `tests/feature_library/test_phase2.py:25-56` | 測試仍斷言 upsert 會把 `created_at` 覆寫為 200 → **與現行 merge-preserve 衝突**（triage A1） |

### 建議修法

1. `FeatureRegistry.add()`：merge-preserve `created_at` + `alias`；每次 upsert 寫入/更新 `last_generated_at = time.time()`。
2. `RunLifecycleManager.auto_cleanup()`：排序鍵改 `last_generated_at`（缺欄時 fallback `created_at` 以相容舊 registry）。
3. （可選一致化）`find_latest()` 是否改依 `last_generated_at` 需產品定義；若「最新」=「最後生成」則一併改。
4. 更新 `test_phase2.py::test_registry_upserts_*` 與 lifecycle 測試，覆蓋「重跑同 hash → `created_at` 不變、`last_generated_at` 變大 → 不被誤清」。

### 信心度

**8/10** — 程式路徑與 batch2 文件一致；`last_generated_at` 為常見雙時間戳模式，需一次 API/前端 list 欄位決策（是否暴露給 UI）。

---

## Q3 — Winsorize：`test_transform_single_optimized_df_end_to_end` 數值分歧

### 結論

**非 production bug；測試設計錯誤（過時假設）**。  
Production L6.5 在 `causal_preprocessing=True`（預設）下，winsor quantile 走 **rolling causal** 路徑；該測試卻把 `_winsorize_2d_legacy_equivalent`（causal）與裸調用的 `_winsorize_2d_inplace`（**全域** nanquantile）比較，兩者本就不應等價。  
同檔案其餘 11 個測試通過；partition vs `np.nanquantile` 等價性已覆蓋。

### 證據

| 位置 | 內容 |
|------|------|
| `tests/test_winsorize_partition_opt.py:295-325` | e2e 測試：`arr_ref` 用 `_winsorize_2d_inplace`；`result` 用 `_winsorize_2d_legacy_equivalent` |
| `momentum/.../feature_preprocessor.py:141` | `causal_preprocessing` 預設 **True** |
| `momentum/.../feature_preprocessor.py:2331-2356` | quantile + causal → `rolling_quantile_2d`；非 causal 才 `_winsorize_2d_inplace` |
| `momentum/.../feature_preprocessor.py:2417-2418` | Production `_transform_single_optimized_df` 呼叫 **`_winsorize_2d_legacy_equivalent`**（正確入口） |
| 實測 | `causal=False` 時兩路徑 max abs diff ≈ **1.18e-7**；預設 causal=True 時 max abs diff ≈ **1.16**（與失敗報告 0.82 / 2.71% 同量級） |
| `TESTS_RUN` | `pytest tests/test_winsorize_partition_opt.py` → **11 passed, 1 failed**（僅 `test_transform_single_optimized_df_end_to_end`） |

### 建議修法

- **測試**：在 `_make_preprocessor()` 設 `causal_preprocessing: False` 再比對兩路徑；或改與 `rolling_quantile_2d` 結果比對；或刪除此 e2e、依賴已有 §9–§11 等價測試。
- **產品**：無需改 winsor 實作（除非另有 causal rolling 正確性議題，本測試未涵蓋）。

### 信心度

**9/10** — 因果/非因果路徑差異已用實測隔離證實。

---

## Q4 — Golden G1/G2：`feature_schema_hash` 漂移

### 結論

**刻意 schema 版本變更導致的 manifest 雜湊漂移，非特徵資料回歸**。  
Parquet 欄位 `a`/`b`、指紋 stats、`groups` 結構在失敗 diff 中**完全一致**；僅 `feature_schema_hash` 因 `schema_version` 字串從 **`raw_v1` → `raw_v2`** 而變。應 **更新 golden baseline**，不是修 `FeatureStorage` 邏輯。

### 證據

| 位置 | 內容 |
|------|------|
| `tests/feature_engineering/test_v2_timestamp_golden.py:129-136` | 第一次 `write_raw` 後 `baseline_manifest` 與 committed baseline 比對即失敗 |
| `tests/_golden/v2_ts/g1_baseline_fingerprint.json:25` | baseline hash = `d04e1ae0...` |
| 實測 `write_raw` 輸出 | 現行 hash = `93ef6756...`，`schema_version` = **`raw_v2`** |
| 實測 brute | `schema_version: "raw_v1"` + `groups: {g: [a,b]}` → hash **`d04e1ae0...`**（與 baseline 吻合） |
| `momentum/.../feature_storage.py:682,1848-1860` | `L7_RAW_SCHEMA_VERSION = "raw_v2"`；hash = SHA256(`schema_version` + sorted groups/columns) |
| `git log` | baseline 檔 `fd3ce6a`（V2 timestamp）；`raw_v2` 語義見 `7427c72` fail-open batch |
| `TESTS_RUN` | `pytest tests/feature_engineering/test_v2_timestamp_golden.py::test_g1_g2_*` → 僅 `feature_schema_hash` 不符 |

### 建議修法

1. 重跑 `test_g1_g2_*` 產物，更新 `tests/_golden/v2_ts/g1_baseline_fingerprint.json` 的 `manifest_allowlist.feature_schema_hash` 為 `93ef6756...`（保留 `feature_fingerprint` 若仍通過）。
2. 在 golden 註記：hash 綁定 `schema_version`，版本 bump 需同步 baseline（避免再被當資料回歸）。

### 信心度

**9/10** — 雜湊可從 `raw_v1`/`raw_v2` 字串單獨復現；parquet 指紋未變。

---

## Q5 — E2E：`test_pipeline_partial_engine_failure` 無 `tr_` 欄

### 結論

**非 tail_risk 引擎關閉、非 `tr_` 改名**。  
在預設 **CGSA + `persist=False`** 路徑下，`metadata["feature_names"]` 被**硬編碼為 `[]`**，而 `features_df` 為空；測試 helper `_result_columns()` 讀不到欄名。Registry 內實際有 26 個 `tr_*` 欄（tail_risk 正常）。  
`FFACT_USE_CGSA=0` 時同測試 **PASS**（欄名前綴為 `tr_12h_*`，與 CGSA 命名不同）。

### 證據

| 位置 | 內容 |
|------|------|
| `tests/momentum/test_feature_factory_optimization_e2e.py:80-84` | `features_df` 空 → fallback `metadata.feature_names` |
| `tests/momentum/test_feature_factory_optimization_e2e.py:177-191` | partial failure：monkeypatch microstructure；仍期望 `tr_` |
| `momentum/.../feature_factory.py:3111-3113` | CGSA `_layer7_raw_from_cgsa_pipeline`：`"feature_names": []` **硬編碼** |
| `momentum/.../feature_factory.py:3244-3273` | 另一 CGSA finalize 路徑正確使用 `all_column_names()`（本測試未走此路） |
| `momentum/.../column_group_registry.py:1135-1143` | `all_column_names()` 可列出 `tr_gpr_100` 等 |
| 實測 CGSA partial failure | `feature_count=26`，registry 26 欄含 `tr_*`；`feature_names len=0` |
| `TESTS_RUN` | 預設 CGSA：`test_pipeline_partial_engine_failure` **FAIL**；`test_pipeline_with_tail_risk` **FAIL** |
| `TESTS_RUN` | `FFACT_USE_CGSA=0 pytest ...::test_pipeline_partial_engine_failure` → **PASS** |

### 建議修法

1. **產品（建議）**：`feature_factory.py:3112` 改為 `self._cgsa_registry.all_column_names()`（與 3244 行一致），使 `persist=False` 的 in-memory 結果可 introspect。
2. **測試**：E2E 在 CGSA 預設下應斷言 `metadata.feature_names` 或 `tr_` / `tr_{tf}_` 雙模式；或文件化 `persist=False` 僅保證 `feature_count`。
3. **非必要**：tail_risk 引擎與 `tr_` 前綴在 `tail_risk_indicators.py:117+` 仍正常。

### 信心度

**8/10** — 根因在 metadata 空列表已定位；需確認是否有意不暴露 names（效能/契約）再改產品。

---

## 交叉摘要

| 問 | 性質 | 建議處置 |
|----|------|----------|
| Q1 | 產品語義缺口 + 測試滯後 | **B** + 修 phase2/lifecycle 測試 |
| Q3 | 測試錯比對 | 修測試或設 `causal_preprocessing=False` |
| Q4 | 刻意 schema_version bump | **更新 golden** |
| Q5 | CGSA metadata 缺口 | **填 `feature_names`** + 調整 E2E 斷言 |

---

## ASSUMPTIONS_VERIFIED

- merge-preserve 欄位與 auto_cleanup 排序鍵（讀碼 + phase2 失敗語境）
- winsor causal vs inplace 分歧（`causal_preprocessing` 開關實測）
- `feature_schema_hash` 由 `raw_v1`→`raw_v2` 解釋（hash 復現）
- CGSA `persist=False` 時 `feature_names=[]`（讀碼 + 實跑 partial failure / tail_risk）

## TESTS_RUN

- `pytest tests/test_winsorize_partition_opt.py` → 11 passed, 1 failed
- `pytest tests/feature_engineering/test_v2_timestamp_golden.py::test_g1_g2_feature_parquet_and_manifest_allowlist_unchanged` → failed (hash only)
- `pytest tests/momentum/test_feature_factory_optimization_e2e.py::test_pipeline_partial_engine_failure` → failed (CGSA on)
- `FFACT_USE_CGSA=0 pytest ...::test_pipeline_partial_engine_failure` → passed
- `pytest tests/momentum/test_feature_factory_optimization_e2e.py::test_pipeline_with_tail_risk` → failed (CGSA on)

## FAILURES_SEEN

none（調查預期失敗，未嘗試修復）

## SCOPE_CHANGES

none（讀取型）

## NUMERIC_OR_SCHEMA_IMPACT

無程式變更。報告標記：Q4 為 manifest `schema_version` 雜湊語義；Q5 為 metadata `feature_names` 契約缺口。

HANDOFF_NOT_UPDATED: 讀取型委員會調查，依合約不覆寫根 HANDOFF.md

STATUS: DONE
