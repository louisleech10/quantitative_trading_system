# Feature Factory 效能優化 — 執行 TODO

> **來源 SPEC**: `docs/FEATURE_FACTORY_OPTIMIZATION_SPEC.md` V2（🔒 FROZEN 2026-04-16）  
> **生成日期**: 2026-04-15  
> **版本**: V1（Frozen）  
> **目標**: 方案 M（Hybrid — CGSA + Polars + Numba + searchsorted）  
> **約束**: 不減特徵、不降品質、數值完全等價  
> **硬體**: MacBook M1 8GB RAM

---

## 交付物 #0.5 — SPEC 正規化報告

### 檢測結果

| # | 結構要素 | 檢測方式 | 存在? | 處理 |
|---|---------|---------|-------|------|
| 1 | Task ID（如 Task N.M） | `Task \d+\.\d+` pattern | ✅ | 原有 33 個 |
| 2 | Test ID（如 TN.M） | `T\d+\.\d+` pattern | ✅ | 原有 98 個 |
| 3 | Risk ID（如 RN） | `R\d+` pattern | ✅ | 原有 25 個（R1~R25） |
| 4 | Phase 劃分 | `Phase \d+` | ✅ | 原有 6 個（Phase 0~5） |
| 5 | Phase Gate 條件 | §8 Phase Gate 決策矩陣 | ✅ | 原有 5 個 Gate（§8.1~§8.5） |
| 6 | 修改檔案路徑 | `.py` 副檔名 | ✅ | 原有 ~15 個檔案路徑 |

**結論：SPEC 結構完整（6/6），跳過正規化。**

---

## 交付物 #1 — SPEC 索引摘要

### A. Task ID 清單（共 33 個）

| # | ID | 名稱/簡述 | SPEC §位置 |
|---|-----|---------|-----------|
| 1 | Task 0.1 | L2 前後計時 log | §2.1 |
| 2 | Task 0.2 | F 段 heartbeat log | §2.1 |
| 3 | Task 0.3 | 建立 Golden Output | §2.1 |
| 4 | Task 1.1 | 實作 build_asof_index_map() | §3.1 |
| 5 | Task 1.2 | 新增 _searchsorted_align() | §3.2 |
| 6 | Task 1.3 | align_to_primary() 切換 searchsorted | §3.3 |
| 7 | Task 1.4 | 跳過 Primary TF Self-Alignment | §3.4 |
| 8 | Task 1.5 | Multi-TF 平行化 — DEFERRED Phase 5 | §3.5 |
| 9 | Task 2.1 | 建立 ColumnGroup dataclass | §4.1 |
| 10 | Task 2.2 | 建立 ColumnGroupRegistry | §4.1.3 |
| 11 | Task 2.3 | L1 per-indicator output → .npy | §4.6 |
| 12 | Task 2.4 | L2 兩階段計算 | §4.2 |
| 13 | Task 2.5 | _combine_layers() registry-based | §4.6 |
| 14 | Task 2.6 | Multi-TF column tagging via group_id | §4.6 |
| 15 | Task 2.7 | L6.5 改為 per-group 處理 | §4.3 |
| 16 | Task 2.8 | Persist per-group Parquet | §4.4 |
| 17 | Task 2.9 | manifest.json 生成 | §4.4 |
| 18 | Task 2.10 | L7 validate 改為 per-group scan | §4.5.2 |
| 19 | Task 2.11 | materialize_wide_df() 向後相容 | §4.5.2, §4.13 |
| 20 | Task 2.12 | 逐層 Golden 比對（雙軌 A/B 驗證修訂） | §4.5, §4.12 |
| 21 | Task 3.1 | fused_rolling_stats (mean/std/min/max/range/zscore) | §5.1, §5.2.1 |
| 22 | Task 3.2 | online skew/kurt (Pebay) | §5.1, §5.2.4 |
| 23 | Task 3.3 | rolling rank (sorted buffer + bisect) | §5.1, §5.2.3 |
| 24 | Task 3.4 | slope (running sums) | §5.1 |
| 25 | Task 3.5 | 整合到 RollingAggregator | §5.1 |
| 26 | Task 3.6 | 數值等價驗證 suite | §5.1 |
| 27 | Task 4.1 | L1 → Polars DataFrame | §6.1 |
| 28 | Task 4.2 | L2 → Polars with_columns() batch | §6.1 |
| 29 | Task 4.3 | L6.5 → Polars expressions | §6.1 |
| 30 | Task 4.4 | NaN 語義對齊驗證 | §6.1 |
| 31 | Task 5.1 | ProcessPoolExecutor multi-symbol | §7.1 |
| 32 | Task 5.2 | Arrow IPC column-group intermediate | §7.1 |
| 33 | Task 5.3 | FeatureReader 統一讀取介面（Parquet-only） | §7.1, V7 §11 |

### B. Test ID 清單（共 98 個）

| # | ID 範圍 | 簡述 | SPEC §位置 | 數量 |
|---|---------|------|-----------|------|
| 1 | T0.1~T0.4 | Phase 0 golden / log 驗證 | §2.2 | 4 |
| 2 | T1.1~T1.10 | Phase 1 核心正確性 | §3.6.1 | 10 |
| 3 | T1.B1~T1.B15 | Phase 1 邊界條件 | §3.6.2 | 15 |
| 4 | T1.P1~T1.P3 | Phase 1 效能驗收 | §3.6.3 | 3 |
| 5 | T2.1~T2.10 | Phase 2 單元測試 | §4.7.1 | 10 |
| 6 | T2.11~T2.17 | Phase 2 整合測試 | §4.7.2 | 7 |
| 7 | T2.B1~T2.B9 | Phase 2 邊界條件 | §4.7.3 | 9 |
| 8 | T3.1~T3.12 | Phase 3 數值正確性+融合 | §5.3 | 12 |
| 9 | T3.B1~T3.B13 | Phase 3 邊界條件 | §5.3.3 | 13 |
| 10 | T3.P1~T3.P2 | Phase 3 效能驗收 | §5.3.4 | 2 |
| 11 | T4.1~T4.4 | Phase 4 數值等價 | §6.2 | 4 |
| 12 | T4.B1~T4.B3 | Phase 4 邊界條件 | §6.2 | 3 |
| 13 | T5.1~T5.3d | Phase 5 平行正確性 + FeatureReader | §7.2, V7 §11 | 6 |
| 14 | T5.B1~T5.B3 | Phase 5 邊界條件 | §7.2 | 3 |
| | **合計** | | | **98** |

### C. Risk ID 清單（共 25 個）

| # | ID | 風險簡述 | SPEC §位置 |
|---|-----|---------|-----------|
| 1 | R1 | searchsorted ms/ns off-by-one | §10 |
| 2 | R2 | self-align skip 後 index 不一致 | §10 |
| 3 | R3 | per-group 過多小檔案 | §10 |
| 4 | R4 | Numba skew/kurt 數值不穩定 | §10 |
| 5 | R5 | Polars null ≠ NaN | §10 |
| 6 | R6 | Multi-TF TA-Lib GIL 競爭 | §10 |
| 7 | R7 | pipeline 跑不完→無完整 golden | §10 |
| 8 | R8 | .npy 中介檔案硬碟暴漲 | §10 |
| 9 | R9 | L2 新 operator 打破 per-group | §10 |
| 10 | R10 | Parquet 45 萬欄位 metadata 極大 | §10 |
| 11 | R11 | TA-Lib 非 thread-safe | §10 |
| 12 | R12 | Numba JIT cold start | §10 |
| 13 | R13 | int64 ms→ns 溢出 (year>2262) | §10 |
| 14 | R14 | A/B 同時執行→RAM 翻倍 | §10 |
| 15 | R15 | .npy 33,600+ 檔案爆炸 | §10 |
| 16 | R16 | Numba ARM64/macOS JIT 相容性 | §10 |
| 17 | R17 | Numba skew/kurt zero-variance | §10 |
| 18 | R18 | L2 O(N²) 組合爆炸 | §10 |
| 19 | R19 | ~~DuckDB Parquet footer scan overhead~~ → 已改為 FeatureReader（PyArrow） | §10, V7 §11 |
| 20 | R20 | Phase 5 磁碟 I/O 未建模 | §10 |
| 21 | R21 | L1 ThreadPool + TA-Lib 安全風險 | §10 |
| 22 | R22 | L6 _find_column fuzzy matching 失敗 | §10 |
| 23 | R23 | L3 variance_filter 非決定性 | §10 |
| 24 | R24 | MultiTFGenerator._combine_layers 未被覆蓋 | §10 |
| 25 | R25 | Polars 版本鎖定風險 | §10 |

### D. Phase Gate 條件（共 5 個）

| # | Gate | 條件摘要 | SPEC §位置 |
|---|------|---------|-----------|
| 1 | Phase 0→1 | Golden 已建立 + L2 計時 log 可見 | §8.1 |
| 2 | Phase 1→2 | T1.3/T1.6/T1.7 PASS + B2+D <50s | §8.2 |
| 3 | Phase 2→3 | T2.11/T2.13 PASS + 無 global concat | §8.3 |
| 4 | Phase 3→4 | T3.12 PASS + re-profile L2+L6.5>30% total | §8.4 |
| 5 | Phase 4/5→Done | 全量 golden PASS + <20min + RSS<2GB | §8.5 |

### E. 硬約束 IDs（共 6 個）

| ID | 約束描述 | 驗收條件 | SPEC §位置 |
|----|---------|---------|-----------|
| C1 | 數值等價（per-layer atol） | Golden output test suite | §1.1 |
| C2 | 不減特徵（453,953 cols） | `assert new_count == golden_count` | §1.1 |
| C3 | 不改 column name + 顯式排序 | `sorted(new) == sorted(golden)` + order test | §1.1 |
| C4 | RAM 峰值 ≤ 6 GB | `psutil.Process().memory_info().rss` | §1.1 |
| C5 | 無 future leakage | `validate_no_future_leak()` | §1.1 |
| C6 | NaN 語義一致 | per-column NaN mask comparison | §1.1 |

### F. 環境變數 / Feature Flag

| # | 名稱 | 用途 | SPEC §位置 |
|---|------|------|-----------|
| 1 | `FFACT_USE_SEARCHSORTED` | 0=fallback merge_asof | §0.12, §3.3 |
| 2 | `FFACT_USE_CGSA` | 0=fallback legacy concat | §0.12, §4.5 |
| 3 | `FFACT_USE_NUMBA_ROLLING` | 0=fallback pandas rolling | §0.12, §5.1 |
| 4 | `FFACT_USE_POLARS` | **預設 1**（Polars ON）；0=fallback pandas | §0.12 |
| 5 | `FFACT_LAYER1_PARALLEL` | L1 ThreadPool（預設 0） | §3.5 |
| 6 | `FFACT_L3_STREAMING` | L3 streaming mode | §5.0 |
| 7 | `FFACT_L65_CHUNK_SIZE` | L6.5 chunk 大小 | §4.14 |
| 8 | `GOLDEN_CONFIG_OVERRIDE` | Reduced config for golden | §2.1 |
| 9 | `MAX_L2_ESTIMATED_COLS` | L2 斷路器閾值（100,000） | §4.2.1 |

### G. SPEC 引用的程式碼檔案

| # | 檔案路徑 | 狀態 |
|---|---------|------|
| 1 | `momentum/FeatureEngineering/feature_factory.py` | 既有 |
| 2 | `momentum/FeatureEngineering/memmap_utils.py` | 既有 |
| 3 | `momentum/FeatureEngineering/timeframe/tf_aligner.py` | 既有 |
| 4 | `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | 既有 |
| 5 | `momentum/FeatureEngineering/operators/rolling_aggregator.py` | 既有 |
| 6 | `momentum/FeatureEngineering/operators/derived_operators.py` | 既有 |
| 7 | `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | 既有 |
| 8 | `momentum/FeatureEngineering/feature_storage.py` | 既有 |
| 9 | `momentum/FeatureEngineering/core/column_group.py` | **新建** |
| 10 | `momentum/FeatureEngineering/core/column_group_registry.py` | **新建** |
| 11 | `momentum/FeatureEngineering/core/__init__.py` | **新建** |
| 12 | `momentum/factories.py` | 既有（新增 factory） |
| 13 | `scripts/generate_golden_output.py` | **新建** |
| 14 | `scripts/validate_cgsa_ab.py` | **新建** |

---

## 交付物 #1.5 — 矛盾與過時檢測報告

### 發現的矛盾（共 3 個，均不阻塞）

| # | 類型 | 來源 A | 來源 B | 矛盾描述 | 建議 |
|---|------|-------|-------|---------|------|
| 1 | SPEC vs Code | SPEC §3.4「第 ~120-126 行」 | `multi_tf_generator.py` L208~220 | 行號不符 | 以函式名定位，不依賴行號 |
| 2 | SPEC vs Code | SPEC §3.3 `anchor_index` | Code 用 `primary_index` | 參數命名差異 | 以程式碼為準 |
| 3 | SPEC vs Code | SPEC §4.1.1 `tuple[str, ...]` | Python 3.11 | 需 `from __future__ import annotations` | SPEC 程式碼已含此 import |

### 過時風險（共 1 個）

| # | 文件 | 問題 |
|---|------|------|
| 1 | `docs/ARCHITECTURE.md` v6.0 (2026-03-15) | SPEC 為 2026-04-15，架構文件可能缺少最新模組描述 |

**結論**: 矛盾不影響功能邏輯，TODO 中以函式名定位取代行號引用。

---

# §0 全域規則與約束

## 0.1 開發規則

> 以下規則摘自 SPEC §0，為每個 Task 的**前置條件**。

### 0.1.1 解耦 7 規則（Zero Tolerance）

| 規則 | 說明 | 驗證方式 |
|------|------|----------|
| R1 | `momentum/` 不可 import `api/` | `grep -r "from api\." momentum/` → 0 |
| R2 | 跨 Domain 使用 Protocol 注入 | `from momentum.core.protocols import I*` |
| R3 | `api/services/` 透過 `momentum/factories.py` 建立 | 不可直接 `Engine()` |
| R4 | Service 之間不互相 import | — |
| R5 | Config 單一來源 | — |
| R6 | 測試設定隔離 | 測試可獨立執行 |
| R7 | DTO 不跨域 | — |

### 0.1.2 Ultra Think 3-Step

每個 Task 程式碼必須：Step 1（初始生成）→ Step 2（自我審查 checklist）→ Step 3（最終優化）。

### 0.1.3 Logging 規範

- `momentum/` 內：`from momentum.core.logging import get_logger`
- 計時 log 格式：`[L{N}] {action}: {detail} in {elapsed:.2f}s`
- Numba `@njit` 函式內不可呼叫 logger
- Hot loop 內不可逐行 log，改用摘要

### 0.1.4 Error Handling

使用 `FailureType` Enum 分類（IO_ERROR/OOM/VALIDATION/CONFIG），不可靜默吞掉異常。

### 0.1.5 命名規範

- 函式：snake_case + 動詞開頭 — 禁止 `df1`, `temp`, `x`
- 類別：PascalCase
- 常數：UPPER_SNAKE_CASE
- 所有新函式必須有完整 type annotations

### 0.1.6 Factory 注入模式

新增被 `api/services/` 使用的 class → 必須在 `momentum/factories.py` 加入 factory 函式。

### 0.1.7 Git Branch 慣例

```
perf/phase-{N}-{description}
perf(feature-factory): Phase N.M - {description}
```

## 0.2 硬約束 C1~C6

| ID | 約束 | 驗證 | Per-Layer atol |
|----|------|------|---------------|
| C1 | 數值等價 | Golden test suite | L1:1e-7, L2:1e-6, L3 mean/std/min/max:1e-6, L3 skew/kurt:**1e-4**, L3 slope:1e-5, L3 rank:1e-6, L6.5:1e-6~1e-5, 全量預設:**1e-4** |
| C2 | 不減特徵 | `new_count == golden_count` | — |
| C3 | 不改 column name + 顯式排序 | `sorted(new) == sorted(golden)` + order test | — |
| C4 | RAM ≤ 6 GB | `psutil.Process().memory_info().rss` | — |
| C5 | 無 future leakage | `validate_no_future_leak()` | — |
| C6 | NaN 語義一致 | per-column NaN mask comparison | — |

## 0.3 每 Phase 驗收流程

```
1. 建立 git branch: perf/phase-{N}-{description}
2. 完成目標修改
3. 執行 golden comparison（C1~C3, C6）
4. 執行 future leak test（C5）
5. 記錄 RSS 峰值（C4）
6. 記錄 wall-clock time
7. 全部 PASS → merge；任一 FAIL → 回退
```

回退策略：連續失敗 3 次 → 重新評估技術方案。

## 0.4 Pre-Commit 檢查清單

```
□ Ultra Think 3 步完成
□ grep -r "from api\." momentum/ → 0（R1）
□ 無 hardcoded data
□ 所有函式有 type hints
□ Error handling 使用 FailureType
□ Logging 符合 §0.2 規範
□ 命名符合 §0.6 規範
□ 測試有中文 docstring
□ 測試可獨立執行
□ .npy / .parquet 不在 git track 中
□ 效能程式碼已向量化
□ Fallback env var 可切回舊行為
□ ruff check momentum/ → 0 error
□ Task 關聯測試先通過（見 §0.4.1）
□ smoke test：pytest tests/ -m "not slow and not legacy" -x -q --tb=short → 0 error
```

## 0.4.1 Task-Scoped Smoke（開發中必跑）

> 原則：開發中先跑 Task 關聯測試；日常 smoke 於 Task 區塊穩定後再跑。

- 通用命令模板
  - `./venv/bin/pytest <task-related-tests> -q --tb=short`
- Batch 1a + 1b（Task 1.1, 1.2, 1.3, 1.4）建議命令
  - `./venv/bin/pytest tests/test_searchsorted_align.py tests/test_primary_self_align_skip.py -q --tb=short`
- Batch 2a（Task 2.1, 2.2）建議命令
  - `./venv/bin/pytest tests/test_column_group.py -q --tb=short`
- 合併驗證（Batch 1a/1b + 2a）
  - `./venv/bin/pytest tests/test_searchsorted_align.py tests/test_primary_self_align_skip.py tests/test_column_group.py -q --tb=short`

## 0.4.2 Kline 檔案路徑規則

- 需要 Kline 資料時，優先使用固定檔案：
  - `/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5`
- 除非該檔案不存在或損毀，否則不要額外搜尋其他快取路徑。

## 0.5 向後相容 Fallback

| Phase | 環境變數 | 預設值 | 說明 |
|-------|---------|--------|------|
| 1 | `FFACT_USE_SEARCHSORTED` | 1 | 0=merge_asof |
| 2 | `FFACT_USE_CGSA` | 1 | 0=legacy concat |
| 3 | `FFACT_USE_NUMBA_ROLLING` | 1 | 0=pandas rolling |
| 4 | `FFACT_USE_POLARS` | 0 | 1=polars（條件性） |

舊路徑保留至下一 Phase Gate 通過。

## 0.6 三層 Baseline 策略

| Tier | 名稱 | 內容 | 環境 |
|------|------|------|------|
| Tier 1 | Full-Config Structural | 欄位數/名/排序/shape/NaN率 | ≥32GB RAM 或雲端 |
| Tier 2 | Reduced-Config Numeric | 全數值 per-layer atol | 開發機 8GB |
| Tier 3 | Per-Layer Golden | L1/L2/L3/L6.5 個別層輸出 | 開發機+大記憶體互補 |

---

# 執行策略

## 批次計畫與依賴拓撲

```
Phase 0 (觀測)
  ├── Task 0.1 (L2 計時 log)           ← 無依賴
  ├── Task 0.2 (F 段 heartbeat)        ← 無依賴
  └── Task 0.3 (Golden output)         ← 0.1, 0.2 完成後
  Gate 0→1: Golden 已建立

Phase 1 (searchsorted)
  ├── Task 1.1 (build_asof_index_map)  ← 無依賴
  ├── Task 1.2 (_searchsorted_align)   ← 1.1
  ├── Task 1.3 (align_to_primary 切換) ← 1.2
  ├── Task 1.4 (self-align skip)       ← 無依賴
  └── Task 1.5                         ← DEFERRED to Phase 5
  Gate 1→2: T1.3/T1.6/T1.7 PASS + B2+D <50s

Phase 2 (CGSA)
  ├── Task 2.1 (ColumnGroup)           ← 無依賴
  ├── Task 2.2 (Registry)              ← 2.1
  ├── Task 2.3 (L1 per-indicator)      ← 2.2
  ├── Task 2.4 (L2 兩階段)             ← 2.3
  ├── Task 2.5 (_combine_layers)       ← 2.2
  ├── Task 2.6 (Multi-TF tagging)      ← 2.2
  ├── Task 2.7 (L6.5 per-group)        ← 2.5
  ├── Task 2.8 (Persist Parquet)       ← 2.7
  ├── Task 2.9 (manifest.json)         ← 2.8
  ├── Task 2.10 (L7 per-group)         ← 2.8
  ├── Task 2.11 (materialize_wide_df)  ← 2.8
  └── Task 2.12 (逐層 A/B 驗證)        ← 2.11
  Gate 2→3: T2.11/T2.13 PASS + 無 global concat

Phase 3 (Numba Rolling)
  ├── Task 3.1 (fused_rolling_stats)   ← 無依賴
  ├── Task 3.2 (online skew/kurt)      ← 3.1
  ├── Task 3.3 (rolling rank)          ← 無依賴
  ├── Task 3.4 (slope)                 ← 無依賴
  ├── Task 3.5 (整合 RollingAggregator) ← 3.1~3.4
  └── Task 3.6 (數值等價 suite)         ← 3.5
  Gate 3→4: T3.12 PASS + re-profile

Phase 4 (Polars — 條件性，可 skip)
  ├── Task 4.1~4.4                     ← Phase 2 完成
  Gate 3→4 skip 條件: L2+L6.5 < 30% total → skip

Phase 5 (生產化)
  ├── Task 5.1 (multi-symbol)          ← Phase 2
  ├── Task 5.2 (Arrow IPC)             ← Phase 2
  ├── Task 5.3 (FeatureReader)         ← Phase 2 + V7 P0
  └── Task 1.5 (Multi-TF 平行)         ← 從 Phase 1 延遲
  Gate 5→Done: C1~C6 全通過 + <20min + RSS<2GB
```

---

## Batch 明細表

| Batch | 包含項目 | 依賴前置 | 合併理由 | 預估規模 |
|-------|---------|---------|---------|---------|
| Batch 0 | Task 0.1, 0.2 | 無 | 純 log，互不干擾 | 2 Task / ~30 行 |
| Batch 0.1 | Task 0.3 | Batch 0 | 需先有 log 才能 verify golden | 1 Task / ~80 行 |
| Batch 1a | Task 1.1, 1.4 | Phase 0 Gate | 獨立函式，可平行開發 | 2 Task / ~120 行 |
| Batch 1b | Task 1.2 → 1.3 | Batch 1a | 1.2 輸出為 1.3 輸入 | 2 Task / ~150 行 |
| Batch 2a | Task 2.1 → 2.2 | Phase 1 Gate | Registry 依賴 ColumnGroup | 2 Task / ~200 行 |
| Batch 2b | Task 2.3, 2.4, 2.5, 2.6 | Batch 2a | 全部依賴 Registry | 4 Task / ~300 行 |
| Batch 2c | Task 2.7, 2.8 | Batch 2b | per-group pipeline | 2 Task / ~150 行 |
| Batch 2d | Task 2.9, 2.10, 2.11 | Batch 2c | persist + validate + materialize | 3 Task / ~200 行 |
| Batch 2e | Task 2.12 | Batch 2d | A/B 驗證需完整 CGSA pipeline | 1 Task / ~100 行 |
| Batch 3a | Task 3.1, 3.3, 3.4 | Phase 2 Gate | 獨立 Numba 函式 | 3 Task / ~250 行 |
| Batch 3b | Task 3.2 | Batch 3a (3.1) | Pebay 依賴 Welford 基礎 | 1 Task / ~120 行 |
| Batch 3c | Task 3.5 → 3.6 | Batch 3a+3b | 整合 + 驗證 | 2 Task / ~150 行 |
| Batch 4 | Task 4.1-4.4 | Phase 3 Gate | 條件性，可整體 skip | 4 Task / ~200 行 |
| Batch 5a | Task 5.1, 5.2 | Phase 2 Gate | multi-symbol 平行 + IPC 中介 | 2 Task / ~250 行 |
| Batch 5b | Task 5.3, 1.5 | Batch 5a | FeatureReader + 延遲的 Multi-TF | 2 Task / ~200 行 |

---

## 快速執行參考（可直接複製 Prompt）

### Batch 0: 觀測 log
```
請執行 Task 0.1 和 Task 0.2。在 feature_factory.py 的 _layer2_derived_features() 前後加入 time.perf_counter 計時 log，
在 memmap_utils.py 的 concat_with_memmap() 加入每 30 秒 heartbeat log。遵循 §0.1.3 logging 規範，不改變任何業務邏輯。
```

### Batch 0.1: Golden Output
```
請執行 Task 0.3。建立 scripts/generate_golden_output.py，使用三層 fallback 策略（Tier1 → 2 → 3）
產生 golden_output.parquet + golden_columns.json。遵循 §0.6 三層 Baseline。
```

### Batch 1a: searchsorted 基礎
```
請執行 Task 1.1（build_asof_index_map）和 Task 1.4（self-align skip）。
在 tf_aligner.py 新增 build_asof_index_map() 函式（np.searchsorted + clip），
在 multi_tf_generator.py 新增 primary TF self-alignment skip 邏輯。
遵循 §0.1.1 解耦規則和 §0.5 env var fallback。
```

### Batch 1b: searchsorted 切換
```
請執行 Task 1.2（_searchsorted_align）→ Task 1.3（align_to_primary 切換）。
實作 fancy indexing 對齊函式並整合到 align_to_primary()。
使用 env var FFACT_USE_SEARCHSORTED 控制切換，預設 =1（啟用）。
```

### Batch 2a-2e: CGSA Pipeline
```
請依序執行 Task 2.1 → 2.2 → 2.3~2.6 → 2.7~2.8 → 2.9~2.11 → 2.12。
建立 ColumnGroup + ColumnGroupRegistry，將 L1/L2/L6.5 改為 per-group 處理，
persist 為 per-group Parquet，最後執行 A/B 逐層驗證。每步遵循 env var fallback（§0.5）。
```

### Batch 3a-3c: Numba Rolling
```
請執行 Task 3.1（Welford fused）、3.3（rolling rank）、3.4（slope）。
全部使用 @njit(float64[:], int64, float64[:]) 簽名，NaN-aware 跳過。
完成後執行 Task 3.2（Pebay skew/kurt）→ Task 3.5（整合）→ Task 3.6（數值等價 suite）。
```

### Batch 4: Polars（✅ 已完成）
```
Phase 3 完成後 re-profile 結果：L2+L6.5 佔比 ~60%，超過 30% 門檻，決定推進。
Task 4.1-4.4 全部完成。FFACT_USE_POLARS 預設改為 1，納入 V7 Baseline。
R5（null vs NaN）已透過三層保護消除；R25 版本釘選已寫入 requirements.txt。
```

### Batch 5: 生產化
```
請執行 Task 5.1（ProcessPoolExecutor + spawn，8 workers）、Task 5.2（Arrow IPC 中介）、
Task 5.3（FeatureReader 統一讀取介面）、Task 1.5（Multi-TF 平行化）。
使用 spawn context，Numba 主進程預熱，per-symbol 獨立 Registry。
```

---

# Phase 0 — 可觀測性基礎建設

**目標**: 不改變行為，增加觀測能力  
**風險**: 零（純 log）  
**Branch**: `perf/phase-0-observability`

---

## Task 0.1: L2 前後計時 log

- **SPEC 參考**: §2.1 Task 0.1
- **目標**: 在 `_layer2_derived_features()` 開頭與結尾加計時 log，確認 A3=307s 分布
- **輸入**: 現有 `_layer2_derived_features()` 函式
- **輸出**: 函式不改變回傳值；新增 2 行 log 輸出（`str` to logger）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory._layer2_derived_features()` | 新增計時 log |

### 實作細節

1. 在函式開頭加 `t0 = time.perf_counter()` 及 `logger.info("[L2] Starting derived features: %d L1 cols", layer1.shape[1])`
2. 在函式結尾（return 前）加 `logger.info("[L2] Completed: %d cols in %.2fs", result.shape[1], elapsed)`
3. 使用 `from momentum.core.logging import get_logger`（遵守 R1）

```python
# Pseudocode
def _layer2_derived_features(self, layer1, raw_data, config):
    import time
    t0 = time.perf_counter()
    logger.info("[L2] Starting derived features: %d L1 cols", layer1.shape[1])
    # ... existing code unchanged ...
    elapsed = time.perf_counter() - t0
    logger.info("[L2] Completed: %d cols in %.2fs", result.shape[1], elapsed)
    return result
```

### 禁止事項

- ❌ 不可修改任何計算邏輯
- ❌ 不可在 hot loop 內加 log
- ❌ 不可使用 `print()`

### 風險緩解

- 無風險（純 log）

### 驗證

- **通過條件**: 執行 pipeline 後 log 中出現 `[L2] Starting` 和 `[L2] Completed` 且時間值 >0
- **測試**: T0.1 `test_l2_timing_log_emitted`

### 邊界情況

1. L1 為空 DataFrame（0 cols）→ 仍應輸出 log，不 crash
2. _layer2_derived_features 拋出異常 → 計時 log 可能不完整（可接受）

---

## Task 0.2: F 段 heartbeat log

- **SPEC 參考**: §2.1 Task 0.2
- **目標**: 在 `concat_with_memmap()` 的 block copy loop 中每 30 秒輸出進度
- **輸入**: 現有 `concat_with_memmap()` 函式
- **輸出**: 函式不改變回傳值；每 30 秒新增 1 行 heartbeat log（`str` to logger）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/memmap_utils.py` | `concat_with_memmap()` | 新增 heartbeat log |

### 實作細節

1. 在 block copy 迴圈開始前初始化 `last_heartbeat = time.perf_counter()`
2. 每次迭代檢查 `if time.perf_counter() - last_heartbeat > 30`
3. 輸出 `logger.info("[concat_memmap] Progress: %d/%d rows copied, RSS=%.0f MB", ...)`
4. RSS 取自 `psutil.Process().memory_info().rss / 1024 / 1024`

```python
# Pseudocode — 在 block copy loop 內
import psutil

last_heartbeat = time.perf_counter()
for i, block in enumerate(blocks):
    # ... existing copy logic ...
    if time.perf_counter() - last_heartbeat > 30:
        rss_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info("[concat_memmap] Progress: %d/%d blocks copied, RSS=%.0f MB",
                    i + 1, total_blocks, rss_mb)
        last_heartbeat = time.perf_counter()
```

### 禁止事項

- ❌ 不可修改 copy 邏輯
- ❌ 不可每次迭代都 log（heartbeat 間隔 ≥30s）
- ❌ 不可 import `api.core.logging`

### 風險緩解

- 無風險（純 log + psutil 讀取是 O(1)）

### 驗證

- **通過條件**: 合成 >30s 的 concat 能看到至少 1 條 heartbeat
- **測試**: T0.2 `test_heartbeat_emitted_during_concat`

### 邊界情況

1. 小 DataFrame（<30s 完成）→ 不輸出任何 heartbeat（正常）
2. psutil 未安裝 → 用 try/except fallback 到不顯示 RSS

---

## Task 0.3: 建立 Golden Output

- **SPEC 參考**: §2.1 Task 0.3, §1.3, §1.3.1, §1.3.2
- **目標**: 執行 Feature Factory pipeline 產出 golden baseline，儲存到 `data_cache/golden_output/`
- **輸入**: ETHUSDT 1h+12h K-line 資料 + scan_config.yaml
- **輸出**: 
  - `data_cache/golden_output/ETHUSDT_1h_2tf_golden.parquet`（`pd.DataFrame` → Parquet）
  - `data_cache/golden_output/columns.json`（`List[str]` → JSON）
  - `data_cache/golden_output/nan_mask.npz`（`Dict[str, np.ndarray]` → NPZ）
  - `data_cache/golden_output/golden_structural.json`（Tier 1 structural baseline）

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `scripts/generate_golden_output.py` | Golden 生成腳本 |

### 實作細節

1. **Reduced Config**：若全量 config OOM → 使用 `GOLDEN_CONFIG_OVERRIDE`（僅 close source、trend+momentum indicators、windows=[5,21,55]、關閉 L6.5）
2. **三層 Baseline**：
   - Tier 2/3 在開發機建立（reduced config）
   - Tier 1 structural baseline 必須在大記憶體環境取得（≥32GB RAM）— 若無法取得，記錄 TODO marker
3. **循環依賴打破**：L1 golden 可直接建立（不涉及 concat）；L2/L3 用 reduced config
4. 儲存格式：parquet（數值）+ columns.json（欄位名列表）+ nan_mask.npz（NaN pattern）
5. `golden_structural.json` 包含：欄位名列表、各層 shape、NaN 率摘要
6. 連續性策略：golden 腳本預設 `--allow-data-gaps`（關閉連續性驗證以避免既有快取缺口阻塞）；若需嚴格模式可用 `--strict-continuity`

```python
# Pseudocode
GOLDEN_CONFIG_OVERRIDE = {
    "data_sources": {"enabled_sources": ["close"]},
    "atomic_indicators": {"trend": {"enabled": True}, "momentum": {"enabled": True}},
    "operators": {"derived": {"enabled": True}},
    "rolling": {"windows": [5, 21, 55], "aggregators": ["mean", "std", "rank"]},
    "preprocessing": {"enabled": False},
}

def generate_golden():
    factory = create_feature_factory(config=GOLDEN_CONFIG_OVERRIDE)
    try:
        result = factory.run("ETHUSDT", timeframes=["1h", "12h"])
    except MemoryError:
        logger.warning("Full config OOM, falling back to reduced config")
        result = factory.run("ETHUSDT", timeframes=["1h", "12h"], config_override=GOLDEN_CONFIG_OVERRIDE)
    
    result.to_parquet(GOLDEN_PATH)
    json.dump(list(result.columns), open(COLUMNS_PATH, 'w'))
    np.savez_compressed(NAN_MASK_PATH, **{col: result[col].isna().values for col in result.columns})
```

### 禁止事項

- ❌ 不可 hardcode 假數據
- ❌ 不可修改 FeatureFactory 邏輯
- ❌ 不可將 golden parquet commit 到 git

### 風險緩解

- R7（pipeline 跑不完）：分層 fallback — full config → reduced config → L1 only
- 確保 `data_cache/golden_output/` 在 `.gitignore`

### 驗證

- **通過條件**: `golden.parquet` 存在、欄位 >0、無 inf
- **測試**: T0.3 `test_golden_output_generated`, T0.4 `test_golden_columns_json_matches`

### 邊界情況

1. data_cache 無 K-line 資料 → `pytest.skip`（測試中跳過）
2. 全量 config + reduced config 都 OOM → 僅建立 L1 golden（部分 baseline）

---

## Phase 0 測試清單

| ID | 測試名稱 | 驗證內容 | SPEC 參考 |
|----|---------|---------|-----------|
| T0.1 | `test_l2_timing_log_emitted` | L2 log 包含 "Starting" 和 "Completed" | §2.2 |
| T0.2 | `test_heartbeat_emitted_during_concat` | 合成 >30s 的 concat 有 heartbeat | §2.2 |
| T0.3 | `test_golden_output_generated` | golden.parquet 存在、欄位 >0、無 inf | §2.2 |
| T0.4 | `test_golden_columns_json_matches` | columns.json 與 parquet 欄位一致 | §2.2 |

## Phase 0 → Phase 1 Gate

| 條件 | 要求 |
|------|------|
| Golden output 已建立 | `data_cache/golden_output/` 存在且可讀 |
| L2 計時 log 可見 | 確認 A3 分布 |

---

# Phase 1 — searchsorted + Multi-TF 快修

**目標**: 最低風險快速見效（B2 298s→0s, D 156s→~5s）  
**風險**: 低  
**Branch**: `perf/phase-1-searchsorted`

---

## Task 1.1: 實作 build_asof_index_map()

- **SPEC 參考**: §3.1
- **目標**: 建立 O(N log M) 的 index mapping，替代 O(N·M/chunk) 的 merge_asof
- **輸入**: `primary_ts: np.ndarray[int64]`（ms timestamps, sorted）, `source_ts: np.ndarray[int64]`（ms timestamps, sorted）, `offset_ns: int`
- **輸出**: `np.ndarray[int64]` — index map，`output[i] = j` where `source_ts[j] <= primary_ts[i] + offset`，無效為 -1

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/timeframe/tf_aligner.py` | `TimeframeAligner.build_asof_index_map()` | 新增靜態方法 |

### 實作細節

1. **ms→ns 轉換**：`primary_ns = primary_ts.astype(np.int64) * 1_000_000 + offset_ns`；`source_ns = source_ts.astype(np.int64) * 1_000_000`
2. **核心算法**：`idx = np.searchsorted(source_ns, primary_ns, side='right') - 1`；`idx[idx < 0] = -1`
3. **輸入驗證**：`source_ts` 必須升序排列，否則 `raise ValueError("source_ts must be sorted in ascending order")`
4. **safety check**：`valid = idx >= 0; mismatch = valid & (source_ns[idx[valid]] > primary_ns[valid])`
5. 完整 type hints + docstring

```python
@staticmethod
def build_asof_index_map(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    offset_ns: int = 0,
) -> np.ndarray:
    if len(source_ts) > 1 and np.any(source_ts[1:] < source_ts[:-1]):
        raise ValueError("source_ts must be sorted in ascending order")
    primary_ns = primary_ts.astype(np.int64) * 1_000_000 + offset_ns
    source_ns = source_ts.astype(np.int64) * 1_000_000
    idx = np.searchsorted(source_ns, primary_ns, side='right') - 1
    idx[idx < 0] = -1
    return idx
```

### 禁止事項

- ❌ 不可使用 pandas merge_asof（此為替代方案）
- ❌ 不可修改現有 _merge_asof_align（保留為 fallback）
- ❌ 不可使用 float 做 timestamp 比較（必須 int64）

### 風險緩解

- R1（ms/ns off-by-one）：T1.2 offset 測試 + T1.B14 邊界測試
- R13（int64 溢出）：T1.B15 overflow 測試

### 驗證

- **通過條件**: `build_asof_index_map(primary=[5,15,25], source=[0,10,20]) == [0, 1, 2]`
- **測試**: T1.1 `test_build_asof_index_map_basic`, T1.2 `test_build_asof_index_map_with_offset`

### 邊界情況

1. source_ts = []（空陣列）→ 回傳全 -1
2. primary_ts 全部早於 source_ts → 全 -1
3. source_ts 有重複 timestamp → 取最後一個（side='right'-1）
4. source_ts 未排序 → raise ValueError

---

## Task 1.2: 新增 _searchsorted_align()

- **SPEC 參考**: §3.2
- **目標**: 使用 build_asof_index_map 做 alignment，替代 _merge_asof_align_chunked
- **輸入**: `source_values: pd.DataFrame`, `source_index: pd.DatetimeIndex`, `primary_index: pd.DatetimeIndex`, `offset_ns: int`
- **輸出**: `pd.DataFrame`（aligned，index=primary_index，columns=source_values.columns）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/timeframe/tf_aligner.py` | `TimeframeAligner._searchsorted_align()` | 新增靜態方法 |

### 實作細節

1. 將 DatetimeIndex 轉 ms timestamps：`source_ms = source_index.astype(np.int64) // 1_000_000`
2. 呼叫 `build_asof_index_map(primary_ms, source_ms, offset_ns)`
3. 使用 index map 做 fancy indexing：`out[valid] = source_arr[idx_map[valid]]`；`out[~valid] = np.nan`
4. 大記憶體估計 → 若 est_bytes >= MEMMAP_THRESHOLD → 使用 memmap 輸出
5. 保存 `aligned.attrs["source_timestamps"]` 供 future leak validation

```python
@staticmethod
def _searchsorted_align(
    source_values: pd.DataFrame,
    source_index: pd.DatetimeIndex,
    primary_index: pd.DatetimeIndex,
    offset_ns: int = 0,
) -> pd.DataFrame:
    source_ms = source_index.astype(np.int64) // 1_000_000
    primary_ms = primary_index.astype(np.int64) // 1_000_000
    idx_map = TimeframeAligner.build_asof_index_map(
        primary_ms.to_numpy(), source_ms.to_numpy(), offset_ns=offset_ns)
    
    source_arr = source_values.to_numpy(dtype=np.float32, na_value=np.nan)
    out = np.empty((len(primary_index), source_values.shape[1]), dtype=np.float32)
    valid = idx_map >= 0
    out[valid] = source_arr[idx_map[valid]]
    out[~valid] = np.nan
    
    aligned = pd.DataFrame(out, index=primary_index, columns=source_values.columns, copy=False)
    # Store source timestamps for future leak validation
    source_ts_mapped = np.full(len(primary_index), np.datetime64('NaT'), dtype='datetime64[ns]')
    source_ts_mapped[valid] = source_index.to_numpy()[idx_map[valid]]
    aligned.attrs["source_timestamps"] = pd.DatetimeIndex(source_ts_mapped)
    return aligned
```

### 禁止事項

- ❌ 不可刪除 _merge_asof_align 或 _merge_asof_align_chunked
- ❌ 不可使用 float32 做 timestamp 比較

### 風險緩解

- R1：offset=-1ns 測試確保 OPEN_MINUS 語義
- 大 DataFrame 使用 memmap 避免 OOM

### 驗證

- **通過條件**: `_searchsorted_align` 結果與 `_merge_asof_align` 在真實 ETHUSDT 資料上 `np.allclose(atol=1e-6, equal_nan=True)`
- **測試**: T1.3 `test_searchsorted_vs_merge_asof_numeric_equivalence`

### 邊界情況

1. source_values 全 NaN 欄位 → aligned 也全 NaN
2. 227k columns（極寬 DataFrame）→ 不 OOM，使用 memmap

---

## Task 1.3: 修改 align_to_primary() 使用 searchsorted

- **SPEC 參考**: §3.3
- **目標**: 將 `align_to_primary()` 中的 `_merge_asof_align` 呼叫替換為 `_searchsorted_align`
- **輸入**: 現有 `align_to_primary()` 方法
- **輸出**: 方法行為不變，內部路徑切換

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/timeframe/tf_aligner.py` | `TimeframeAligner.align_to_primary()` | 條件分支切換 |

### 實作細節

1. 讀取 `FFACT_USE_SEARCHSORTED` 環境變數（預設=1）
2. 若啟用 → 呼叫 `_searchsorted_align(source_values, source_index, primary_index, offset_ns)`
3. 若停用 → 呼叫現有 `_merge_asof_align`（fallback）
4. `offset_ns = -1 if (alignment_mode == AlignmentMode.OPEN_MINUS and source_tf != primary_tf) else 0`

```python
# In align_to_primary():
use_searchsorted = os.environ.get("FFACT_USE_SEARCHSORTED", "1") == "1"
offset_ns = -1 if (alignment_mode == AlignmentMode.OPEN_MINUS and source_tf != primary_tf) else 0

if use_searchsorted:
    aligned = TimeframeAligner._searchsorted_align(
        source_values, source_index, primary_index, offset_ns=offset_ns)
else:
    aligned = TimeframeAligner._merge_asof_align(source_values, source_index, primary_index)
```

### 禁止事項

- ❌ 不可刪除舊路徑程式碼
- ❌ 不可改變函式簽名

### 風險緩解

- `FFACT_USE_SEARCHSORTED=0` 可立即切回

### 驗證

- **通過條件**: T1.10 `FFACT_USE_SEARCHSORTED=0` 走舊路徑且結果一致
- **測試**: T1.3, T1.10

### 邊界情況

1. 環境變數未設定 → 預設使用 searchsorted
2. 環境變數設為無效值 → 視為停用，走 fallback

---

## Task 1.4: 跳過 Primary TF Self-Alignment

- **SPEC 參考**: §3.4
- **目標**: Primary TF self-alignment 是 identity 操作（原地對齊），跳過可省 B2=298s
- **輸入**: `multi_tf_generator.py` 中的 `generate_multi_tf()` 方法
- **輸出**: 行為不變（數值完全等價），省去不必要的 align + memmap

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `MultiTFGenerator.generate_multi_tf()` | 條件跳過 |

### 實作細節

1. 在 `aligned = TimeframeAligner.align_to_primary(...)` 前加條件判斷
2. `if timeframe == self._primary_tf:` → 跳過 align，直接用 combined
3. **關鍵**: 必須將 `combined.index` 重設為 `primary_timestamps`（DatetimeIndex），因 combined 可能是 int64 index
4. 使用 `copy(deep=False)` 避免修改 combined 的 index

```python
combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
if timeframe == self._primary_tf:
    logger.info("[multi_tf] Skipping self-alignment for primary TF %s (%d cols)",
                timeframe, combined.shape[1])
    aligned = combined.copy(deep=False)
    aligned.index = primary_timestamps
else:
    aligned = TimeframeAligner.align_to_primary(
        combined, timeframe, primary_timestamps,
        self._primary_tf, self._config.timeframes.alignment_mode)
aligned.attrs = {}
aligned = self._apply_timeframe_tag(aligned, timeframe)
```

### 禁止事項

- ❌ 不可改變 non-primary TF 的對齊邏輯
- ❌ 不可假設 combined.index 已是 DatetimeIndex

### 風險緩解

- R2（index 不一致）：`assert len(combined) == len(primary_timestamps)`
- T1.B11 測試 index mismatch 場景

### 驗證

- **通過條件**: skip 後 vs 不 skip 的結果 `np.allclose(atol=1e-7, equal_nan=True)`
- **測試**: T1.6 `test_primary_self_align_skip_produces_same_output`

### 邊界情況

1. primary_timestamps 與 combined index 長度一致但值不同 → 正確重設
2. combined 含 NaN（L1 計算產生的）→ NaN 保留不變
3. combined 欄位順序 → skip 後不變

---

## Task 1.5: Multi-TF 平行化 — ⚠️ DEFERRED to Phase 5

- **SPEC 參考**: §3.5（V2 修訂）
- **狀態**: **DEFERRED** — Phase 1 不實作
- **原因**: TA-Lib 非 thread-safe（R11/R6），效益僅 C=37s（2.0%），成本效益不合理
- **Phase 5 實作指引**: 必須使用 `ProcessPoolExecutor + multiprocessing.get_context('spawn')`

---

## Phase 1 測試清單

### 核心正確性（T1.1~T1.10）

| ID | 測試名稱 | 驗證內容 |
|----|---------|---------|
| T1.1 | `test_build_asof_index_map_basic` | source=[0,10,20], primary=[5,15,25] → idx=[0,1,2] |
| T1.2 | `test_build_asof_index_map_with_offset` | offset=-1ns 時 primary==source → 取上一個 |
| T1.3 | `test_searchsorted_vs_merge_asof_numeric_equivalence` | 真實 ETHUSDT atol=1e-6 |
| T1.4 | `test_searchsorted_align_preserves_column_names` | 欄位名完全一致 |
| T1.5 | `test_searchsorted_align_nan_pattern` | NaN 位置一致 |
| T1.6 | `test_primary_self_align_skip_produces_same_output` | skip vs no-skip 等價 |
| T1.7 | `test_multi_tf_golden_output_equivalence` | 整個 pipeline golden 比對 |
| T1.8 | `test_no_future_leak_after_searchsorted` | validate_no_future_leak() PASS |
| T1.9 | `test_searchsorted_align_preserves_source_timestamps_attr` | attrs["source_timestamps"] 存在 |
| T1.10 | `test_env_var_fallback_to_merge_asof` | FFACT_USE_SEARCHSORTED=0 走舊路徑 |

### 邊界條件（T1.B1~T1.B15）

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T1.B1 | `test_build_asof_index_map_empty_source` | source=[] | 全 -1 |
| T1.B2 | `test_build_asof_index_map_empty_primary` | primary=[] | 空 array |
| T1.B3 | `test_build_asof_index_map_single_row` | source=[100] | [-1, 0, 0] |
| T1.B4 | `test_build_asof_index_map_primary_before_all` | primary 全早於 source | 全 -1 |
| T1.B5 | `test_build_asof_index_map_primary_after_all` | primary 全晚於 source | 全指向最後 |
| T1.B6 | `test_build_asof_index_map_duplicate_timestamps` | source 有重複 | 取最後一個 |
| T1.B7 | `test_build_asof_index_map_unsorted_source` | source 未排序 | raise ValueError |
| T1.B8 | `test_searchsorted_align_all_nan_columns` | 全 NaN 欄位 | aligned 全 NaN |
| T1.B9 | `test_searchsorted_align_mixed_dtypes` | float64+float32 | 統一 float32 |
| T1.B10 | `test_searchsorted_align_very_wide_df` | 227k columns | 不 OOM |
| T1.B11 | `test_self_align_skip_with_mismatched_index` | index 長度一致值不同 | 正確重設 |
| T1.B12 | `test_self_align_skip_with_nan_in_combined` | combined 含 NaN | NaN 保留 |
| T1.B13 | `test_self_align_skip_preserves_column_order` | 欄位順序 | 不變 |
| T1.B14 | `test_offset_ns_minus_one_at_exact_boundary` | primary==source, offset=-1 | 取上一個 |
| T1.B15 | `test_build_asof_index_map_int_overflow` | 極大 timestamp | 不溢出 |

### 效能驗收（T1.P1~T1.P3）

| ID | 測試名稱 | 驗收標準 |
|----|---------|---------|
| T1.P1 | `test_searchsorted_align_speed` | 227k cols × 12888 rows < 30s |
| T1.P2 | `test_searchsorted_align_memory` | RSS 增量 < 500 MB |
| T1.P3 | `test_self_align_skip_eliminates_memmap` | 無新 memmap 檔案建立 |

## Phase 1 → Phase 2 Gate

| 條件 | 要求 |
|------|------|
| T1.3 PASS | searchsorted vs merge_asof 數值一致 |
| T1.6 PASS | self-align skip 數值一致 |
| T1.7 PASS | 整個 multi-TF golden 等價 |
| 效能實測 | B2+D 合計 < 50s |
| re-profile | 新時間分布記錄 |

---

# Phase 2 — CGSA 架構規格與實作

**目標**: 消除所有全域 concat（B1+E+F ~9,000s）  
**風險**: 中等（核心架構重構）  
**Branch**: `perf/phase-2-cgsa`

---

## Task 2.1: 建立 ColumnGroup dataclass

- **SPEC 參考**: §4.1.1, §4.9
- **目標**: 定義 CGSA 的核心資料結構 — immutable metadata for feature column groups
- **輸入**: 無（新建）
- **輸出**: `ColumnGroup` frozen dataclass（`momentum/FeatureEngineering/core/column_group.py`）

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `momentum/FeatureEngineering/core/__init__.py` | 模組初始化 |
| `momentum/FeatureEngineering/core/column_group.py` | ColumnGroup + LayerSource Enum |

### 實作細節

1. **LayerSource Enum**: `L1, L2, L3, L4, L5, L6, L65`（str Enum）
2. **ColumnGroup frozen dataclass**: `group_id`, `layer`, `timeframe`, `data_source`, `indicator`, `columns: tuple[str, ...]`, `shape: tuple[int, int]`, `dtype`, `disk_path`
3. **Properties**: `n_rows`, `n_cols`, `est_bytes`
4. **粒度**（§4.9）：indicator level（非 window/agg level），預估 ~1,200 groups
5. 必須 `from __future__ import annotations`（Python 3.11 `tuple[str, ...]` 語法）

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import numpy as np

class LayerSource(str, Enum):
    L1 = "L1"; L2 = "L2"; L3 = "L3"; L4 = "L4"
    L5 = "L5"; L6 = "L6"; L65 = "L6.5"

@dataclass(frozen=True)
class ColumnGroup:
    group_id: str
    layer: LayerSource
    timeframe: str
    data_source: str
    indicator: str
    columns: tuple[str, ...]
    shape: tuple[int, int]
    dtype: str = "float32"
    disk_path: Optional[Path] = None

    @property
    def n_rows(self) -> int: return self.shape[0]
    @property
    def n_cols(self) -> int: return self.shape[1]
    @property
    def est_bytes(self) -> int:
        return self.n_rows * self.n_cols * (4 if self.dtype == "float32" else 8)
```

### Group ID 命名規則（§4.9 粒度）

| Layer | 粒度 | 命名模式 | 預估數量 |
|-------|------|---------|---------|
| L1 | per-indicator | `{tf}_L1_{category}_{indicator}` | ~200 |
| L2 | per-category | `{tf}_L2_{operator}` | ~14 |
| L3 | per-L1-indicator | `{tf}_L3_{category}_{indicator}_{source}` | ~800 |
| L4 | per-L1-indicator | `{tf}_L4_{category}_{indicator}_{source}` | ~200 |
| L5 | single | `{tf}_L5_cross_sectional` | 2 |
| L6 | per-engine | `{tf}_L6_{engine}` | ~6 |

### 禁止事項

- ❌ ColumnGroup 不可為 mutable（必須 frozen=True）
- ❌ 不可放在 `api/models/` 下（R1 violation）

### 風險緩解

- 無直接風險（純資料結構定義）

### 驗證

- **通過條件**: `ColumnGroup` 為 frozen（修改 attribute raise FrozenInstanceError）
- **測試**: T2.1 `test_column_group_immutable`, T2.2 `test_column_group_est_bytes`

### 邊界情況

1. columns 為空 tuple → est_bytes = 0
2. 極長 group_id（100+ 字元）→ 不應有長度限制

---

## Task 2.2: 建立 ColumnGroupRegistry

- **SPEC 參考**: §4.1.3, §4.10, §4.11
- **目標**: In-memory registry tracking all column groups，支援 incremental manifest 和斷點續跑
- **輸入**: `work_dir: Path`（暫存 .npy 目錄）
- **輸出**: `ColumnGroupRegistry` 類別（`momentum/FeatureEngineering/core/column_group_registry.py`）

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `momentum/FeatureEngineering/core/column_group_registry.py` | Registry class |

### 實作細節

1. **核心 API**: `register()`, `get()`, `list_by_layer()`, `list_by_timeframe()`, `load_data()`, `save_data()`, `total_columns()`, `all_column_names()`, `cleanup()`
2. **Incremental manifest**（§4.10）：每次 `save_data()` 都 atomic write manifest.json（temp + os.replace）
3. **斷點續跑**（§4.10）：`resume_from_manifest(work_dir)` 類別方法，載入已完成的 groups
4. **config_hash 正規化**（§4.11）：`compute_config_hash(config)` 使用 `json.dumps(sort_keys=True) + SHA256[:12]`
5. **all_column_names() 排序**（§4.8 Canonical Column Order）：按 timeframe → layer → category → indicator → source → window → aggregator 排序
6. **Factory**: 在 `momentum/factories.py` 新增 `create_column_group_registry(work_dir)`

```python
class ColumnGroupRegistry:
    def __init__(self, work_dir: Path):
        self._groups: dict[str, ColumnGroup] = {}
        self._work_dir = work_dir

    def register(self, group: ColumnGroup) -> None:
        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id}")
        self._groups[group.group_id] = group

    def save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup:
        path = self._work_dir / f"{group.group_id}.npy"
        np.save(path, data.astype(np.float32))
        updated = ColumnGroup(..., disk_path=path)
        self.register(updated)
        self._write_manifest()
        return updated

    def _write_manifest(self):
        tmp = self._work_dir / "manifest.json.tmp"
        with open(tmp, 'w') as f:
            json.dump(self._to_manifest_dict(), f, indent=2)
        os.replace(tmp, self._work_dir / "manifest.json")

    @classmethod
    def resume_from_manifest(cls, work_dir: Path) -> ColumnGroupRegistry:
        manifest = json.load(open(work_dir / "manifest.json"))
        registry = cls(work_dir=work_dir)
        for g in manifest['groups']:
            if (work_dir / g['npy_path']).exists():
                registry._register_from_manifest(g)
        return registry

    def cleanup(self) -> None:
        for g in self._groups.values():
            if g.disk_path and g.disk_path.exists():
                g.disk_path.unlink()
        self._groups.clear()
```

### 禁止事項

- ❌ 不可允許重複 group_id
- ❌ manifest.json 不可非 atomic write（防止 partial write corruption）
- ❌ 不可在 `api/` 下建立此檔案

### 風險緩解

- R8（.npy 暴漲）：cleanup() + finally block
- R15（檔案過多）：粒度調整至 ~1,200 groups

### 驗證

- **通過條件**: save → load roundtrip 數值完全一致
- **測試**: T2.3~T2.10

### 邊界情況

1. work_dir 不存在 → 自動建立
2. manifest.json 存在但 .npy 遺失 → log warning + 跳過該 group
3. 磁碟空間不足 → raise IOError

---

## Task 2.3: L1 per-indicator output → .npy

- **SPEC 參考**: §4.6
- **目標**: L1 輸出改為 per-indicator ColumnGroup，每個 group 儲存為 .npy
- **輸入**: 現有 `_layer1_atomic_indicators()` 輸出
- **輸出**: 每個 indicator 產出一個 ColumnGroup，透過 Registry save_data()

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory._layer1_atomic_indicators()` | 改為 per-indicator emit |

### 實作細節

1. 在 CGSA 模式下（`FFACT_USE_CGSA=1`），L1 的每個 indicator 計算後立即 `registry.save_data(group, data)`
2. L1 全量同時保留在 RAM（~87 MB），供 L2 Stage A 使用
3. Group ID: `{tf}_L1_{category}_{indicator}`
4. 非 CGSA 模式 → 走現有路徑（fallback）

### 禁止事項

- ❌ 不可在 CGSA 模式下改變 L1 計算邏輯
- ❌ L1 全量不可在 Stage A 結束前釋放

### 驗證

- **通過條件**: L1 per-indicator .npy 的 concat 結果 == legacy L1 output
- **測試**: 整合在 T2.11

### 邊界情況

1. 某 indicator 產出 0 cols → 不 register，不 save
2. 單一 indicator 產出 >1000 cols → 正常處理（group 粒度為 indicator level）

---

## Task 2.4: L2 兩階段計算

- **SPEC 參考**: §4.2, §4.2.1
- **目標**: L2 改為 per-category 分批 + 斷路器，避免 2.5GB 一次性輸出
- **輸入**: L1 全量 DataFrame + raw_data + config
- **輸出**: L2 per-category ColumnGroups（透過 Registry）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/operators/derived_operators.py` | `DerivedOperatorEngine.compute_all()` | 新增 `compute_category()` 方法 |
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory._layer2_derived_features()` | CGSA 分支 |

### 實作細節

1. **Stage A（per-category 分批）**: 對每個 category（Distance, Cross, Ratio, Momentum, BinarySignal, SignedStrength, WorldQuant）分別計算
2. 每個 category 計算後立即 `registry.save_data()` 到 disk → `del cat_result` 釋放
3. **斷路器**: `estimated = _estimate_l2_output_cols(l1_count, config)`；若 > `MAX_L2_ESTIMATED_COLS=100,000` → 強制 per-category 分批 + warning log
4. **Stage B**: L1 data 可釋放（後續 L3 只需 per-group 讀取）

```python
# CGSA L2 路徑
for category in OPERATOR_CATEGORIES:
    cat_result = engine.compute_category(l1_df, raw_data, specs, category)
    if cat_result is not None and cat_result.shape[1] > 0:
        group = ColumnGroup(group_id=f"{tf}_L2_{category}", layer=LayerSource.L2, ...)
        registry.save_data(group, cat_result.values)
    del cat_result
```

### 禁止事項

- ❌ 不可一次性計算全部 L2（在 CGSA 模式下）
- ❌ 不可在斷路器觸發後仍嘗試全量計算

### 風險緩解

- R18（L2 O(N²) 組合爆炸）：斷路器 MAX_L2_ESTIMATED_COLS
- R9（新 operator 打破 per-group）：文件記錄「跨 group operators 必須在 Stage A」

### 驗證

- **通過條件**: per-category L2 concat == legacy L2 output
- **測試**: T2.16 `test_cgsa_l2_cross_group_operators`

### 邊界情況

1. config 關閉所有 Cross/Ratio → L2 直接 per-group emit（Stage A 簡化）
2. L1 只有 1 個 indicator → Cross 無法計算，正常跳過

---

## Task 2.5: _combine_layers() 改為 registry-based

- **SPEC 參考**: §4.6, §4.14
- **目標**: CGSA 模式下不再呼叫 `pd.concat` / `concat_with_memmap`，改為 Registry 管理
- **輸入**: Registry（已包含所有 L1~L6 groups）
- **輸出**: 無 wide DataFrame（Registry 即為結果）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory._combine_layers()` | CGSA 跳過 |
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `MultiTFGenerator._combine_layers()` | **同步修改** CGSA 跳過 |

### 實作細節

1. CGSA 模式下 `_combine_layers()` 成為 no-op（所有 groups 已在 Registry 中）
2. **⚠️ 關鍵**: 必須同時修改 `multi_tf_generator.py` 中的獨立 `_combine_layers()` 靜態方法（R24）
3. 非 CGSA 模式 → 走現有 `concat_with_memmap` 路徑

### 禁止事項

- ❌ 不可只修改 feature_factory.py 的 _combine_layers 而遺漏 multi_tf_generator.py（R24）
- ❌ 不可刪除舊路徑

### 風險緩解

- R24：code review 必須確認兩處 _combine_layers 都已修改

### 驗證

- **通過條件**: T2.12 `test_cgsa_no_global_concat` — CGSA 路徑中無 `concat_with_memmap` 呼叫
- **測試**: T2.12

### 邊界情況

1. 某層 output 為空（0 groups）→ Registry 無該層 groups，正常
2. non-CGSA 模式仍正常 concat

---

## Task 2.6: Multi-TF column tagging via group_id

- **SPEC 參考**: §4.6
- **目標**: column tagging 改為 group_id 命名（TF prefix 天然包含在 group_id 中）
- **輸入**: Registry groups
- **輸出**: 無 `.rename()` 操作

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `MultiTFGenerator._apply_timeframe_tag()` | CGSA 跳過 |

### 實作細節

1. CGSA 模式下 `_apply_timeframe_tag()` 成為 no-op（group_id 已含 TF prefix）
2. 非 CGSA 模式 → 走現有 `.rename()` 路徑
3. 在函式入口處以 `if registry is not None and os.environ.get('FFACT_USE_CGSA') == '1': return df` 提前返回，避免任何 column rename 操作

### 禁止事項

- ❌ 不可在 CGSA 模式下仍做 rename

### 驗證

- **通過條件**: CGSA groups 的 column names 已含 TF prefix，且 `df.columns` 排序與 non-CGSA 一致
- **測試**: 整合在 T2.11

### 邊界情況

1. 單一 TF（無 multi-TF）→ group_id 仍含 TF prefix（一致性）
2. CGSA env var 在 pipeline 中途切換（fallback 重新啟用 rename 路徑）→ 不應殘留 no-op 狀態

---

## Task 2.7: L6.5 改為 per-group 處理

- **SPEC 參考**: §4.3
- **目標**: L6.5 preprocessing 改為 per-group 迭代（每個 group 獨立 preprocess）
- **輸入**: Registry 中的所有 L1~L6 groups
- **輸出**: preprocessed groups（覆寫 .npy 或新建 L65 groups）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | `FeaturePreprocessor` | 新增 per-group 入口 |

### 實作細節

1. CGSA 模式下遍歷 Registry 所有 groups，逐個 load → preprocess → save
2. 6 種操作（winsorization, rank_transform, adaptive_zscore, gaussian, adf_diff, fracdiff）均為 per-column → per-group 完全相容
3. CGSA per-group 取代現有 chunking 模式（`FFACT_L65_CHUNK_SIZE`）

```python
# CGSA L6.5
for group_id, group in registry.iter_all():
    data = registry.load_data(group_id)  # mmap read-only
    processed = preprocessor.preprocess_array(data, group.columns)
    registry.overwrite_data(group_id, processed)
```

### 禁止事項

- ❌ 不可實作 cross-feature rank（目前未使用，且 per-group 不相容）
- ❌ 不可修改現有 preprocessing 數學邏輯

### 風險緩解

- §4.3 已確認 6 種操作均為 per-column scope

### 驗證

- **通過條件**: per-group L6.5 output == legacy wide-table L6.5 output（per-column atol）
- **測試**: T2.17 `test_cgsa_l65_rank_matches_legacy`

### 邊界情況

1. group 全 NaN → preprocess 應保持全 NaN（不 crash）
2. fracdiff transform → 需要同列所有 rows → per-group 可行（每列有完整 12,888 rows）

---

## Task 2.8: Persist per-group Parquet

- **SPEC 參考**: §4.4
- **目標**: 最終持久化改為 per-group Parquet files
- **輸入**: Registry 中的所有 groups
- **輸出**: `data_cache/features/{symbol}/{config_hash}/*.parquet`

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_storage.py` | `FeatureStorage` | 新增 per-group Parquet persist |

### 實作細節

1. 遍歷 Registry groups → 每個 group 寫一個 Parquet file
2. 儲存路徑：`data_cache/features/{symbol}/{config_hash}/{group_id}.parquet`
3. 寫入後可刪除 .npy 中介檔案
4. 粒度 ~1,200 groups → ~1,200 Parquet files（可被 FeatureReader column projection 高效處理）

### 禁止事項

- ❌ Parquet files 不可 commit 到 git
- ❌ 不可寫入單一巨大 Parquet（失去 per-group 讀取的優勢）

### 風險緩解

- R3/R15/R19：粒度已調整至 ~1,200

### 驗證

- **通過條件**: FeatureReader 可讀取所有 Parquet 並 count columns == manifest total
- **測試**: T2.15 `test_cgsa_parquet_readable_by_feature_reader`

### 邊界情況

1. 磁碟空間不足 → raise IOError + 部分已寫入的 parquet 需清理
2. 極大 group（>1000 cols）→ 單一 Parquet 仍可處理

---

## Task 2.9: manifest.json 生成

- **SPEC 參考**: §4.4, §4.11
- **目標**: 生成完整的 manifest.json 描述所有 groups
- **輸入**: Registry 狀態
- **輸出**: `manifest.json`（JSON file）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/core/column_group_registry.py` | `ColumnGroupRegistry._write_manifest()` | 已在 Task 2.2 實作 |

### 實作細節

1. manifest 包含：symbol, primary_tf, training_tfs, config_hash, total_features, total_groups, groups 列表, created_at
2. config_hash 使用 `compute_config_hash()`（§4.11：sorted keys + SHA256[:12]）
3. manifest 同時存放完整 config snapshot
4. groups 陣列按 group_id 排序（canonical order）

### 禁止事項

- ❌ config_hash 不可依賴 dict 插入順序

### 驗證

- **通過條件**: manifest.json 可被 `json.load()` 讀取，groups 數量 > 0
- **測試**: T2.14 `test_cgsa_manifest_valid`

### 邊界情況

1. 453,953 columns 的 manifest.json 大小 → 應 < 50 MB（group 粒度已調整）
2. config 含 non-serializable 值 → 需 custom JSON encoder

---

## Task 2.10: L7 validate 改為 per-group scan

- **SPEC 參考**: §4.5.2
- **目標**: L7 validate 改為遍歷 Registry groups，逐個 validate
- **輸入**: Registry 中的所有 groups
- **輸出**: validation 結果（pass/fail + 詳細報告）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory._layer7_validate_and_persist()` | CGSA 分支 |

### 實作細節

1. CGSA 模式下遍歷 Registry groups，逐個 load → validate（inf check, NaN ratio check）
2. validate 後呼叫 Task 2.8 的 persist 邏輯
3. 非 CGSA 模式 → 走現有 wide DataFrame validate 路徑

### 禁止事項

- ❌ 不可在 validate 階段 materialize wide DataFrame

### 驗證

- **通過條件**: CGSA validate 結果與 legacy validate 一致
- **測試**: 整合在 T2.11

### 邊界情況

1. 某 group 含 inf → 標記 warning，不 crash pipeline
2. 某 group NaN 比率 >90% → log warning

---

## Task 2.11: materialize_wide_df() 向後相容

- **SPEC 參考**: §4.5.2, §4.13
- **目標**: 保留一個 materialize_wide_df() 方法，從 Registry Parquet 重組 wide DataFrame
- **輸入**: Registry 或 manifest.json
- **輸出**: `pd.DataFrame`（wide table，向後相容）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/core/column_group_registry.py` | `ColumnGroupRegistry.materialize_wide_df()` | 新增方法 |

### 實作細節

1. 遍歷 Registry groups → 逐個讀入 → concat 為 wide DataFrame
2. 加上 `@deprecated` 標註 + RAM warning log
3. column 順序使用 Canonical Column Order（§4.8）
4. 目前下游模組（IC Analysis, ML Training）仍透過此方法取得 wide DataFrame

```python
def materialize_wide_df(self) -> pd.DataFrame:
    """⚠️ DEPRECATED — 僅用於向後相容。Production 應遷移到 get_group()/iter_groups()。"""
    logger.warning("[Registry] materialize_wide_df() called — consider migrating to per-group API")
    frames = []
    for group_id in self._canonical_order():
        data = self.load_data(group_id)
        group = self.get(group_id)
        frames.append(pd.DataFrame(data, columns=group.columns))
    return pd.concat(frames, axis=1)
```

### 禁止事項

- ❌ 不可在 CGSA pipeline 內部呼叫此方法（僅供下游）

### 驗證

- **通過條件**: materialize_wide_df() 結果與 legacy pipeline 輸出 column-wise 完全等價
- **測試**: 整合在 T2.11 `test_cgsa_vs_legacy_numeric_equivalence`

### 邊界情況

1. 453,953 columns materialize → RAM 估計 ~20 GB → warning log 提示可能 OOM
2. 空 Registry → 回傳空 DataFrame

---

## Task 2.12: 逐層 Golden 比對（A/B 驗證修訂）

- **SPEC 參考**: §4.5, §4.12
- **目標**: 建立逐層 Golden 比對框架，替代全量 A/B 驗證（因 legacy pipeline F 段 OOM）
- **輸入**: CGSA pipeline 輸出 + legacy per-layer golden
- **輸出**: 比對報告（pass/fail per layer）

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `scripts/validate_cgsa_ab.py` | 逐層 A/B 比對腳本 |

### 實作細節

1. **L1 比對**: `np.allclose(cgsa_l1, legacy_l1, atol=1e-7, equal_nan=True)`
2. **L2 比對**: per-category, `atol=1e-6`
3. **L3 比對**: per-aggregator atol（C1 tolerance map）
4. **Full structure 比對**: column names list + count + NaN 率 vs Tier 1 baseline
5. Phase 2 完成後用 CGSA 跑出的 full-config output 成為新 baseline

### 禁止事項

- ❌ 不要求 legacy pipeline 完成 full-config run
- ❌ 不可修改 golden output

### 風險緩解

- R14（A/B 同時 RAM）：A/B 不同時在記憶體中；legacy 先存 parquet，再跑 CGSA 比對
- R7（pipeline 跑不完）：逐層比對可部分完成

### 驗證

- **通過條件**: 所有可建立 golden 的層均 PASS（per-layer atol）
- **測試**: T2.11 `test_cgsa_vs_legacy_numeric_equivalence`

### 邊界情況

1. 某層 legacy golden 不存在（OOM 未建立）→ 跳過該層，log warning
2. column 數不同（R23 variance_filter）→ 先比 column set，用交集做數值比對

---

## 附加 Task（Phase 2 隱含需求）

### L4 快速路徑強制（§4.2.2）

**修改**: CGSA 模式下 `_layer4_lag_features()` 強制 `apply_to="layer1_and_raw"`（避免 wide materialization）。若 config 設定不同 → warning log + 自動降級。

### L5 依賴域（§4.2.3）

**確認**: L5 作為獨立 stage，產出 `{tf}_L5_cross_sectional` ColumnGroup。Reference data 透過獨立 adapter 讀取。

### L6 Stage A/B（§4.2.4）

**確認**: L6 從 Registry 讀取所需的 L1 columns（~10 個已知 columns），而非全量 L1 DataFrame。建議改 `_find_column()` 為顯式 column 引用。

### Column Ordering 驗證（§4.8）

**確認**: `all_column_names()` 按 Canonical Column Order 排序（7-key）。Golden 比對使用 `list(new_cols) == list(golden_cols)`。

---

## Phase 2 測試清單

### 單元測試（T2.1~T2.10）

| ID | 測試名稱 | 驗證內容 |
|----|---------|---------|
| T2.1 | `test_column_group_immutable` | frozen 不可修改 |
| T2.2 | `test_column_group_est_bytes` | bytes 計算正確 |
| T2.3 | `test_registry_register_and_get` | 註冊後可取回 |
| T2.4 | `test_registry_duplicate_raises` | 重複 group_id → ValueError |
| T2.5 | `test_registry_save_and_load_roundtrip` | save→load 數值一致 |
| T2.6 | `test_registry_list_by_layer` | 按 layer 過濾正確 |
| T2.7 | `test_registry_list_by_timeframe` | 按 TF 過濾正確 |
| T2.8 | `test_registry_all_column_names_order` | 按 canonical order |
| T2.9 | `test_registry_cleanup_deletes_files` | cleanup 後 .npy 全刪 |
| T2.10 | `test_registry_total_columns` | total == sum(n_cols) |

### 整合測試（T2.11~T2.17）

| ID | 測試名稱 | 驗證內容 |
|----|---------|---------|
| T2.11 | `test_cgsa_vs_legacy_numeric_equivalence` | CGSA == legacy (C1~C3, C6) |
| T2.12 | `test_cgsa_no_global_concat` | 無 concat_with_memmap 呼叫 |
| T2.13 | `test_cgsa_ram_peak_under_2gb` | RSS < 2 GB |
| T2.14 | `test_cgsa_manifest_valid` | manifest.json 格式正確 |
| T2.15 | `test_cgsa_parquet_readable_by_feature_reader` | FeatureReader count == manifest total |
| T2.16 | `test_cgsa_l2_cross_group_operators` | Cross/Ratio 結果等於 legacy |
| T2.17 | `test_cgsa_l65_rank_matches_legacy` | per-group rank == legacy |

### 邊界條件（T2.B1~T2.B9）

| ID | 邊界條件 | 預期行為 |
|----|---------|---------|
| T2.B1 | L1 只有 1 個 indicator | 正常執行 |
| T2.B2 | L2 無跨 group 操作 | 直接 per-group emit |
| T2.B3 | 某 group 全 NaN | 正常 register + persist |
| T2.B4 | group 有 0 cols | 不 register |
| T2.B5 | 磁碟空間不足 | raise IOError |
| T2.B6 | 同 group_id 不同 TF | TF prefix 不同，不衝突 |
| T2.B7 | 453,953 cols manifest | < 50 MB |
| T2.B8 | L6.5 fracdiff | per-group 可行 |
| T2.B9 | cleanup 被中斷 | .npy 殘留 → 下次自動清理 |

## Phase 2 → Phase 3 Gate

| 條件 | 要求 |
|------|------|
| T2.11 PASS | CGSA vs legacy 數值一致 |
| T2.13 PASS | RSS < 2 GB |
| T2.12 確認 | 無 global concat |
| re-profile | 確認 L3 是剩餘 top-1 瓶頸 |

---

# Phase 3 — Numba L3 融合 Rolling

**目標**: L3 掃描次數 100N → 1N（A4 385s → ~60s）  
**風險**: 中等（數值穩定性）  
**Branch**: `perf/phase-3-numba-rolling`  
**前提**: 現有 L3 已有 streaming 模式（§5.0），Phase 3 為增量改進

---

## Task 3.1: fused_rolling_stats (mean/std/min/max/range/zscore)

- **SPEC 參考**: §5.1, §5.2.1, §5.2.2
- **目標**: 實作 Numba single-pass fused rolling，一次掃描計算 6 個統計量
- **輸入**: `data: np.ndarray[float32]`（1D column）, `window: int`
- **輸出**: `np.ndarray[float32, shape=(N, 6)]` — [mean, std, min, max, range, zscore]

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `momentum/FeatureEngineering/operators/numba_rolling.py` | Numba fused rolling 實作 |

### 實作細節

1. **Welford Online Mean/Var**：`_welford_update()` + `_welford_remove()`，**float64 累加器**（硬性要求）
2. **Monotonic Deque Min/Max**：ring buffer + deque index，O(1) amortized
3. **Range = max - min**
4. **Zscore = (val - mean) / std**（std=0 → NaN）
5. **NaN 處理**：跳過 NaN 值，有效 count < min_periods → 輸出 NaN（等價 pandas `rolling(W, min_periods=W)`）
6. **必須 `@numba.njit(cache=True)`**（避免 R12 cold start）
7. 最終輸出 `.astype(np.float32)`

```python
@numba.njit(cache=True)
def fused_rolling_stats(data: np.ndarray, window: int) -> np.ndarray:
    N = len(data)
    out = np.full((N, 6), np.nan, dtype=np.float64)  # float64 累加器
    # Welford state
    count = 0; mean = 0.0; M2 = 0.0
    # Deque state for min/max
    ...
    for i in range(N):
        val = data[i]
        if not np.isnan(val):
            count, mean, M2 = _welford_update(count, mean, M2, val)
            # update deques
        if i >= window:
            old_val = data[i - window]
            if not np.isnan(old_val):
                count, mean, M2 = _welford_remove(count, mean, M2, old_val)
                # update deques
        if count >= window:
            std = np.sqrt(M2 / (count - 1)) if count > 1 else 0.0
            out[i, 0] = mean
            out[i, 1] = std
            out[i, 2] = deque_min
            out[i, 3] = deque_max
            out[i, 4] = deque_max - deque_min
            out[i, 5] = (val - mean) / std if std > 0 else np.nan
    return out.astype(np.float32)
```

### 禁止事項

- ❌ 不可使用 float32 累加器（catastrophic cancellation at W=233）
- ❌ Numba @njit 函式內不可呼叫 logger
- ❌ 不可使用 pandas rolling（此為替代方案）

### 風險緩解

- R4/R17：float64 累加器 + epsilon guard

### 驗證

- **通過條件**: `np.allclose(numba_out, pd.rolling.mean/std/min/max, atol=1e-6, equal_nan=True)`
- **測試**: T3.1~T3.6

### 邊界情況

1. 輸入全 NaN → 輸出全 NaN
2. Window=1 → mean=val, std=NaN
3. 極大/極小值交替（1e30 / 1e-30）→ 不 overflow

---

## Task 3.2: online skew/kurt (Pebay)

- **SPEC 參考**: §5.1, §5.2.4
- **目標**: 實作 Pebay online algorithm for skewness and kurtosis with 定期校正
- **輸入**: `data: np.ndarray[float32]`, `window: int`
- **輸出**: `np.ndarray[float32, shape=(N, 2)]` — [skew, kurt]

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/operators/numba_rolling.py` | 新增 `rolling_skew_kurt()` | 新增 |

### 實作細節

1. **Pebay Online 演算法**：維護 S2 (M2), S3, S4 累加器（全部 float64）
2. **定期校正**：每 `min(W, 50)` 步從 ring buffer 重新計算（batch compute 覆蓋 online state）
3. **Zero-variance guard**：`if count < 3 or M2 < 1e-30: return np.nan`（R17）
4. **NaN 處理**：同 Task 3.1
5. **atol=1e-4**（比其他 aggregator 寬鬆，因 online 與 batch 算法差異）

```python
@numba.njit(cache=True)
def rolling_skew_kurt(data, window, recalc_interval=50):
    ...
    for i in range(N):
        _pebay_update(ring_buffer, ...)
        if (i + 1) % min(window, recalc_interval) == 0:
            # 從 ring buffer 重新計算（batch exact）
            count, mean, M2, M3, M4 = _batch_compute(ring_buffer)
        if count >= window:
            skew = _compute_skew(M2, M3, count)  # with epsilon guard
            kurt = _compute_kurt(M2, M4, count)  # with epsilon guard
```

### 禁止事項

- ❌ 不可省略定期校正（必要的，非 nice-to-have）
- ❌ 不可使用 float32 累加器

### 風險緩解

- R4：定期校正 + float64 + epsilon guard
- R16（ARM64 相容）：版本釘選 `numba>=0.57,<0.60`

### 驗證

- **通過條件**: `np.allclose(numba_skew, pd.rolling.skew(), atol=1e-4, equal_nan=True)`
- **測試**: T3.7 `test_numba_rolling_skew_vs_pandas`, T3.8 `test_numba_rolling_kurt_vs_pandas`

### 邊界情況

1. 全常數序列 → skew=NaN, kurt=NaN（M2 < epsilon）
2. Window=233（最大）→ 校正仍正確
3. 連續 ±inf → 正確傳播 NaN

---

## Task 3.3: rolling rank (sorted buffer + bisect)

- **SPEC 參考**: §5.1, §5.2.3
- **目標**: 實作 rolling rank 使用 sorted buffer + bisect（average tie method，語義凍結）
- **輸入**: `data: np.ndarray[float32]`, `window: int`
- **輸出**: `np.ndarray[float32]` — percentile rank

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/operators/numba_rolling.py` | 新增 `rolling_rank()` | 新增 |

### 實作細節

1. **凍結的數學定義**：
   - `lo = bisect_left(buf, x[i]); hi = bisect_right(buf, x[i])`
   - `rank = (lo + hi - 1) / 2 + 1`（1-based average rank）
   - `pct = rank / count`
2. **Sorted buffer**: 固定大小 W，新值 insort O(W)，舊值移除 bisect+shift O(W)
3. **NaN 處理**: 不放入 sorted buffer，count 不計入
4. **總複雜度**: O(N·W) — 比 pandas O(N·W·log(W)) 快

```python
@numba.njit(cache=True)
def rolling_rank(data, window):
    N = len(data)
    out = np.full(N, np.nan, dtype=np.float64)
    buf = np.empty(window, dtype=np.float64)
    buf_len = 0
    for i in range(N):
        val = data[i]
        if not np.isnan(val):
            # insort val into buf[0:buf_len]
            pos = _bisect_left(buf, buf_len, val)
            _insert_at(buf, buf_len, pos, val)
            buf_len += 1
        if i >= window:
            old = data[i - window]
            if not np.isnan(old):
                pos = _bisect_left(buf, buf_len, old)
                _remove_at(buf, buf_len, pos)
                buf_len -= 1
        if buf_len >= window:
            lo = _bisect_left(buf, buf_len, val)
            hi = _bisect_right(buf, buf_len, val)
            rank = (lo + hi - 1) / 2 + 1
            out[i] = rank / buf_len
    return out.astype(np.float32)
```

### 禁止事項

- ❌ 不可使用 `method='min'` 或其他 tie-breaking（必須 average）
- ❌ 不可使用 scipy.stats.rankdata（Numba 內無法呼叫）

### 驗證

- **通過條件**: `np.allclose(numba_rank, pd.rolling.rank(pct=True), atol=1e-6)`
- **測試**: T3.9, T3.B9

### 邊界情況

1. 全同值 → pct=0.5（average of all same ranks / count）
2. Window=1 → pct=1.0
3. 重複值（ties）→ average method

---

## Task 3.4: slope (running sums)

- **SPEC 參考**: §5.1
- **目標**: 實作 rolling slope 使用 running sums 公式
- **輸入**: `data: np.ndarray[float32]`, `window: int`
- **輸出**: `np.ndarray[float32]`

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/operators/numba_rolling.py` | 新增 `rolling_slope()` | 新增 |

### 實作細節

1. 使用 running sums: `sum_x`, `sum_y`, `sum_xy`, `sum_x2` 維護滑動 window
2. `slope = (W * sum_xy - sum_x * sum_y) / (W * sum_x2 - sum_x^2)`
3. x 使用 0-based index（或 timestamp）
4. **float64 累加器**

### 禁止事項

- ❌ 不可使用 np.polyfit（在 Numba 內無法呼叫）

### 驗證

- **通過條件**: 與現有 vectorized slope 實作一致（atol=1e-5）
- **測試**: T3.10 `test_numba_rolling_slope_vs_existing`

### 邊界情況

1. 全常數 → slope ≈ 0
2. 嚴格遞增 → slope > 0

---

## Task 3.5: 整合到 RollingAggregator

- **SPEC 參考**: §5.1
- **目標**: 將 Numba fused rolling 整合到現有 RollingAggregator，維持 streaming 模式架構
- **輸入**: 現有 RollingAggregator
- **輸出**: 增加 Numba 路徑（透過 `FFACT_USE_NUMBA_ROLLING` 控制）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | `RollingAggregator.compute_all()` | 新增 Numba 分支 |

### 實作細節

1. `FFACT_USE_NUMBA_ROLLING=1`（預設）→ 使用 Numba fused rolling
2. `FFACT_USE_NUMBA_ROLLING=0` → 走現有 pandas rolling 路徑（fallback）
3. 維持現有 variance_filter + memmap 輸出
4. Per-column 呼叫 `fused_rolling_stats()` + `rolling_skew_kurt()` + `rolling_rank()` + `rolling_slope()`
5. 多 window 融合：對每個 column，一次迴圈計算所有 windows 的 stats

### 禁止事項

- ❌ 不可刪除 pandas rolling 路徑
- ❌ 不可改變 variance_filter 行為

### 風險緩解

- R23（variance_filter 非決定性）：固定閾值，不用百分位

### 驗證

- **通過條件**: T3.12 全量 golden 比對
- **測試**: T3.11 `test_fused_multi_window_equivalent`, T3.12 `test_fused_golden_output_match`

### 邊界情況

1. 全部 9 window sizes 同時融合（5,8,13,21,34,55,89,144,233）→ 正確
2. variance_filter 過濾的 column set 需與 legacy 一致

---

## Task 3.6: 數值等價驗證 suite

- **SPEC 參考**: §5.1
- **目標**: 建立完整的數值等價驗證測試套件
- **輸入**: Numba rolling 輸出 + pandas rolling 輸出
- **輸出**: 驗證報告（per-aggregator pass/fail）

### 新建檔案

| 檔案 | 用途 |
|------|------|
| `tests/test_numba_rolling.py` | Phase 3 測試集（T3.1~T3.12 + T3.B1~T3.B13 + T3.P1~T3.P2） |
| `tests/conftest_phase3.py` | Phase 3 共用 fixture（sample data generator） |

### 實作細節

1. **conftest fixture**: 建立 `sample_ohlcv(N, seed)` fixture，產生 N 筆含 NaN / inf / 常數段的測試序列
2. **parametrize 驅動**: 對每個 aggregator × window × dtype 組合使用 `@pytest.mark.parametrize`，避免手動重複
3. **比對邏輯**: 統一使用 `np.testing.assert_allclose(numba_out, pandas_out, atol=C1_MAP[agg], equal_nan=True)` 作為 assertion

```python
# tests/test_numba_rolling.py 結構示意
import pytest
import numpy as np
from momentum.FeatureEngineering.operators.numba_rolling import fused_rolling_stats

WINDOWS = [5, 20, 60, 233]
AGGS = ['mean', 'std', 'min', 'max', 'skew', 'kurt', 'rank', 'slope']

@pytest.fixture
def sample_ohlcv():
    rng = np.random.default_rng(42)
    arr = rng.standard_normal(10_000).astype(np.float32)
    arr[::500] = np.nan  # inject NaN
    return arr

@pytest.mark.parametrize("window", WINDOWS)
def test_numba_rolling_mean_vs_pandas(sample_ohlcv, window):
    result = fused_rolling_stats(sample_ohlcv, window)[:, 0]  # mean
    expected = pd.Series(sample_ohlcv).rolling(window).mean().values
    np.testing.assert_allclose(result, expected, atol=1e-6, equal_nan=True)
```

### 禁止事項

- ❌ 不可使用 `np.allclose`（不支援 equal_nan）
- ❌ 不可 hardcode 測試資料（必須透過 fixture 產生）

### 驗證

- **通過條件**: 所有 T3.1~T3.12 + T3.B1~T3.B13 + T3.P1~T3.P2 PASS（pytest 回傳 0）
- **CI 整合**: `pytest tests/test_numba_rolling.py -v --tb=short`

### 邊界情況

1. 測試資料長度 N=0（空 array）→ 所有輸出應為空 array，不可拋出異常
2. 測試資料 dtype=float64（非 float32）→ 應自動轉型並 warn，結果仍與 pandas 一致

---

## Phase 3 測試清單

### 數值正確性（T3.1~T3.12）

| ID | 測試名稱 | atol |
|----|---------|------|
| T3.1 | `test_numba_rolling_mean_vs_pandas` | 1e-6 |
| T3.2 | `test_numba_rolling_std_vs_pandas` | 1e-6 |
| T3.3 | `test_numba_rolling_min_vs_pandas` | 1e-6 |
| T3.4 | `test_numba_rolling_max_vs_pandas` | 1e-6 |
| T3.5 | `test_numba_rolling_range_vs_pandas` | 1e-6 |
| T3.6 | `test_numba_rolling_zscore_vs_pandas` | 1e-6 |
| T3.7 | `test_numba_rolling_skew_vs_pandas` | **1e-4** |
| T3.8 | `test_numba_rolling_kurt_vs_pandas` | **1e-4** |
| T3.9 | `test_numba_rolling_rank_vs_pandas` | 1e-6 |
| T3.10 | `test_numba_rolling_slope_vs_existing` | 1e-5 |
| T3.11 | `test_fused_multi_window_equivalent` | per-agg |
| T3.12 | `test_fused_golden_output_match` | C1 map |

### 邊界條件（T3.B1~T3.B13）

| ID | 邊界條件 | 預期行為 |
|----|---------|---------|
| T3.B1 | 全 NaN | 全 NaN |
| T3.B2 | 全常數 | mean=val, std=0, rank=0.5, skew/kurt=NaN |
| T3.B3 | Window=1 | mean=val, std=NaN |
| T3.B4 | N < W | 前 W-1 行 NaN |
| T3.B5 | 極大/極小交替 | 不 overflow |
| T3.B6 | Window=233 | 正確到 tail |
| T3.B7 | 連續 ±inf | 正確傳播 |
| T3.B8 | N=1 | 全 NaN |
| T3.B9 | 重複值 rank | average method |
| T3.B10 | float64 vs float32 精度 | skew/kurt 誤差 < 1e-4 |
| T3.B11 | 間歇 NaN | 跳過 NaN, count < min → NaN |
| T3.B12 | min_periods 等價 | 前 W-1 行全 NaN |
| T3.B13 | 9 windows 同時融合 | 正確 |

### 效能驗收（T3.P1~T3.P2）

| ID | 驗收標準 |
|----|---------|
| T3.P1 | 1,683 cols × 10 windows × 10 aggs × 12,888 rows < 120s |
| T3.P2 | RAM 增量 < 500 MB |

## Phase 3 → Phase 4 Gate

| 條件 | 要求 |
|------|------|
| T3.12 PASS | 融合結果 vs golden 一致 |
| re-profile | L2+L6.5 > 30% total → Phase 4；否則 skip |
| No-Phase-4 效能 | 若 total < 7 min/sym → SKIP Phase 4 |

---

# Phase 4 — Polars L2 / L6.5（條件性 — 可 SKIP）

**目標**: 利用 Polars 向量化加速 L2/L6.5  
**風險**: 中等（NaN/null 語義差異 R5, 版本鎖定 R25）  
**Branch**: `perf/phase-4-polars`  
**Skip 條件**: Phase 3 後 L2+L6.5 < 30% total → skip

---

## Task 4.1: L1 → Polars DataFrame

- **SPEC 參考**: §6.1
- **目標**: L1 output 轉為 Polars DataFrame（`pl.from_numpy` zero-copy）
- **輸入**: L1 per-indicator numpy arrays（來自 Task 2.3 的 .npy files）
- **輸出**: `pl.DataFrame`（與原 pandas DataFrame 欄位名/shape 一致）
- **實作要點**:
  1. 在 `_layer1_atomic_indicators()` 結尾，使用 `pl.from_numpy(arr, schema=column_names)` 將 L1 output 轉為 Polars DataFrame
  2. 若 env var `FFACT_USE_POLARS=0`，保持原 pandas 路徑不變
  3. 確保 `pl.from_numpy` zero-copy（不複製底層記憶體），透過 `rechunk=False` 避免額外配置
  ```python
  if use_polars:
      pl_df = pl.from_numpy(l1_array, schema=column_names)
  else:
      pd_df = pd.DataFrame(l1_array, columns=column_names)
  ```
- **修改檔案**: `feature_factory.py` → `_layer1_atomic_indicators()` L1 output 路徑
- **不可做**:
  - ❌ 不可在 Polars 路徑中使用 `pl.DataFrame(pandas_df)`（雙份記憶體）
  - ❌ 不可移除 pandas 路徑（env var fallback 必須保留）
- **風險緩解**: R5（null vs NaN）— Task 4.4 負責語義對齊
- **驗證**: T4.1 — `pl_df.to_pandas()` vs legacy pandas DataFrame, atol=1e-6
- **Edge Cases**:
  - 空 L1 output（0 欄）→ 建立空 `pl.DataFrame`
  - 全 NaN 欄位 → Polars 用 null 表示，後續 `fill_null(float('nan'))` 對齊

## Task 4.2: L2 → Polars with_columns() batch

- **SPEC 參考**: §6.1
- **目標**: DerivedOperatorEngine 改用 Polars `with_columns()` batch 計算
- **輸入**: L1 Polars DataFrame（來自 Task 4.1）
- **輸出**: L2 Polars DataFrame（含 derived features）
- **實作要點**:
  1. 將 L2 derived operators（ratio, diff, cross 等）改寫為 Polars expressions
  2. 使用 `df.with_columns([expr1, expr2, ...])` 一次批量計算，避免逐欄 loop
  3. 跨 group 操作（Stage A）先 `collect()` 所需欄位再計算
  ```python
  # 範例: ratio 操作
  ratio_exprs = [
      (pl.col(a) / pl.col(b)).alias(f"{a}_ratio_{b}")
      for a, b in ratio_pairs
  ]
  l2_df = l1_df.with_columns(ratio_exprs)
  ```
- **修改檔案**: `derived_operators.py` → `compute_derived_features()` 內部邏輯
- **不可做**:
  - ❌ 不可使用 `apply()` 或 `map_elements()`（與 Python loop 等速）
  - ❌ 不可改變 L2 的欄位命名規則
- **風險緩解**: ⊘
- **驗證**: T4.1 — Polars L2 output vs pandas L2, atol=1e-6（C1）
- **Edge Cases**:
  - 除以零 → Polars 產生 `inf`/`-inf`，需 `fill_nan(float('nan'))` 對齊 pandas 行為
  - 某 group 只有 1 欄 → ratio/diff 無法計算，跳過

## Task 4.3: L6.5 → Polars expressions

- **SPEC 參考**: §6.1
- **目標**: FeaturePreprocessor 改用 Polars expressions（rank, zscore, diff 等）
- **輸入**: per-group Polars DataFrame（來自 Task 4.2 後的 pipeline）
- **輸出**: preprocessed per-group Polars DataFrame
- **實作要點**:
  1. rank → `pl.col(c).rank(method='average') / pl.col(c).count()`
  2. zscore → `(pl.col(c) - pl.col(c).mean()) / pl.col(c).std()`
  3. diff → `pl.col(c).diff(n=1)`
  4. winsorization → `pl.col(c).clip(lower, upper)`
  ```python
  rank_exprs = [
      (pl.col(c).rank(method='average') / pl.col(c).count()).alias(f"{c}_rank")
      for c in group_columns
  ]
  ```
- **修改檔案**: `feature_preprocessor.py` → `preprocess()` 內部各 transform 函式
- **不可做**:
  - ❌ 不可改變 L6.5 output 的欄位命名
  - ❌ fracdiff 不可用 Polars（需保持 pandas/scipy 實作）
- **風險緩解**: R5 — null/NaN 語義在 Task 4.4 統一
- **驗證**: T4.2 — Polars L6.5 output vs pandas L6.5, atol=1e-5（C1）
- **Edge Cases**:
  - 全 NaN 欄位 → rank 結果為全 null（需 fill_null）
  - 常數欄位（std=0）→ zscore 為 NaN（除以零保護）

## Task 4.4: NaN 語義對齊驗證

- **SPEC 參考**: §6.1
- **目標**: 確保 Polars null 在 to_numpy/to_pandas 時統一為 NaN（C6）
- **輸入**: 所有 Polars pipeline 的中間與最終 output
- **輸出**: 驗證通過的 NaN 一致性報告
- **實作要點**:
  1. 在 Polars → numpy/pandas 轉換點加入 `.fill_null(float('nan'))` 
  2. 驗證 `pl.DataFrame.to_numpy()` 的 null → NaN 轉換是否完整
  3. 版本釘選 `polars>=0.20,<0.21`（在 `requirements.txt` 中）
  ```python
  # 轉換時確保 NaN 對齊
  numpy_arr = pl_df.fill_null(float('nan')).to_numpy()
  # 驗證
  assert np.isnan(numpy_arr).sum() == expected_nan_count
  ```
- **修改檔案**: `feature_factory.py` → Polars → numpy 轉換點; `requirements.txt` → polars 版本
- **不可做**:
  - ❌ 不可依賴 Polars 預設的 null → 0 行為
  - ❌ 不可使用 `polars>=0.21`（API 可能變更）
- **風險緩解**: R5（Polars null vs NaN）, R25（版本鎖定）
- **驗證**: T4.B1 — per-column NaN mask comparison: Polars output vs pandas output
- **Edge Cases**:
  - 巢狀 null（Polars Series 內含 null List）→ 不適用（本場景僅 flat numeric）
  - float32 精度損失 → T4.B2 驗證 < 1e-6

---

## Phase 4 測試清單

| ID | 測試名稱 | 驗證內容 |
|----|---------|---------|
| T4.1 | `test_polars_l2_vs_pandas_l2` | 全量數值等價 |
| T4.2 | `test_polars_l65_vs_pandas_l65` | 全量數值等價 |
| T4.3 | `test_polars_nan_min_periods` | NaN 行數一致 |
| T4.4 | `test_polars_division_by_zero` | NaN/inf 行為一致 |
| T4.B1 | Polars null vs NaN | 統一為 NaN |
| T4.B2 | float64→float32 | 精度損失 < 1e-6 |
| T4.B3 | Empty DataFrame | 正確處理 |

---

# Phase 5 — 生產化

**目標**: V7 P0 儲存基礎 → multi-symbol 平行化 → FeatureReader 統一讀取介面  
**風險**: 中等（多進程 + TA-Lib 安全）  
**Branch**: `perf/phase-5-production`

---

## Task 5.0: V7 P0 — 儲存基礎建設（Phase 5 前置）

- **SPEC 參考**: `docs/FEATURE_STORAGE_ARCHITECTURE_V7.md` §11, §12 P0
- **目標**: 建立 float16 + manifest + max_group_split + FeatureReader 基礎，所有 Phase 5 後續 Task 依賴此基礎
- **輸入**: V6.2 pipeline 輸出的 per-group Parquet files（float32, 708 files, 36.63 GB）
- **輸出**: 
  - `manifest.json` — 每個 symbol/config_hash 目錄下產生（groups → file/column_count 映射）
  - `columns.json.gz` — 壓縮全量 feature names（< 1 MB）
  - float16 Parquet files — 取代 float32（~18 GB）
  - `momentum/FeatureEngineering/feature_reader.py` — 新增 FeatureReader class
- **前置**: Phase 3 完成（Numba rolling）、V6.2 pipeline 可執行
- **實作要點**:
  1. **manifest.json 寫入** — 在 `persist_registry_to_parquet()` 結束後：
     ```python
     manifest = {
         "version": "7.0",
         "symbol": symbol,
         "config_hash": config_hash,
         "created_at": datetime.now().isoformat(),
         "total_features": total_col_count,
         "total_rows": n_rows,
         "dtype": "float16",
         "groups": {}  # 填入 group_name → {"file": filename, "column_count": N}
     }
     (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
     ```
  2. **columns.json.gz 寫入** — 收集所有 group 的 column names，gzip 壓縮寫入：
     ```python
     all_columns = []
     for group_name, group_info in manifest["groups"].items():
         all_columns.extend(group_info["columns"])
     with gzip.open(output_dir / "columns.json.gz", 'wt') as f:
         json.dump(all_columns, f)
     # 驗證: compressed size < 1 MB（V7 §13 決議 #1）
     ```
  3. **float16 cast** — 在 `persist_column_group()` 中 `.astype(np.float16)` 後再寫入 Parquet：
     ```python
     # 在寫入 Parquet 前
     df = df.astype(np.float16)
     # 注意：NaN/Inf 在 float16 中保留（np.float16 支援 NaN/Inf）
     table = pa.Table.from_pandas(df)
     pq.write_table(table, path, compression='zstd')
     ```
  4. **max_group_columns=5000 自動拆分** — 當某 group 的 column count > 5000：
     ```python
     MAX_GROUP_COLUMNS = 5000
     if len(columns) > MAX_GROUP_COLUMNS:
         for i, chunk_start in enumerate(range(0, len(columns), MAX_GROUP_COLUMNS)):
             chunk_cols = columns[chunk_start:chunk_start + MAX_GROUP_COLUMNS]
             part_name = f"{group_name}_part{i+1}"
             # 分別寫入 Parquet + 更新 manifest groups
     ```
  5. **FeatureReader 統一介面** — 新增 `feature_reader.py`，實作 4 種模式（見下方 API）
  6. **FeatureLibrary 改造** — `load()` / `load_multi()` 內部改為委託 FeatureReader，移除 `import h5py`
- **修改檔案**:
  | 檔案 | 函式/方法 | 修改類型 |
  |------|----------|---------|
  | `momentum/FeatureEngineering/feature_storage.py` | `persist_registry_to_parquet()` | 修改：加入 manifest 寫入 + float16 cast |
  | `momentum/FeatureEngineering/feature_storage.py` | `persist_column_group()` | 修改：float16 cast + max_group_split |
  | `momentum/FeatureEngineering/feature_storage.py` | `_write_manifest()` | 新增：manifest.json + columns.json.gz 寫入 |
  | `momentum/FeatureEngineering/feature_storage.py` | `_split_large_group()` | 新增：>5000 columns 自動拆分邏輯 |
  | `momentum/FeatureEngineering/feature_reader.py` | `FeatureReader` class（全部） | **新增檔案** |
  | `momentum/FeatureEngineering/feature_library.py` | `load()`, `load_multi()` | 修改：改用 FeatureReader，移除 h5py |
- **不可做**:
  - ❌ 不可保留 HDF5 讀取路徑（V7 決議：Parquet-only）
  - ❌ 不可在 FeatureReader 中實作寫入功能（read-only，寫入職責在 feature_storage.py）
  - ❌ 不可修改 pipeline 計算邏輯（只改 persist 層）
  - ❌ 不可跳過 float16 精度驗證直接部署（必須有 T5.0b 通過）
  - ❌ manifest.json 不可存 435K+ 完整 column names（用 columns.json.gz 壓縮另存）
- **風險緩解**:
  - R10（Parquet 45 萬欄位 metadata 開銷）→ manifest.json 避免讀 Parquet metadata
  - R19（讀取效能）→ PyArrow column projection 直接讀指定欄，不需全檔掃描
- **驗證**: T5.0a, T5.0b, T5.0c, T5.0d, T5.0e, T5.0f, T5.0g
  - **通過條件**: 
    1. persist 後 `manifest.json` + `columns.json.gz` 自動存在且內容正確
    2. 所有 Parquet 檔 dtype == float16
    3. float16 vs float32 數值差異 < `np.finfo(np.float16).eps * 10`（relative），NaN 位置完全一致
    4. >5000 columns group 自動拆分為 part1/part2，manifest 正確記錄
    5. FeatureReader 4 模式全部可用，結果與 `materialize_wide_df()` 一致
    6. FeatureLibrary.load() 走 FeatureReader，`import h5py` 不再出現

### FeatureReader API（V7 §11）

```python
class FeatureReader:
    """V7 統一特徵讀取介面 — 只支援 Parquet，不支援 HDF5"""
    
    def __init__(self, feature_base_path: str = "data_cache/features"):
        self._base = Path(feature_base_path)
    
    # Mode 1: Metadata-Only（零資料 I/O）
    def load_manifest(self, symbol: str, config_hash: str) -> dict:
        """載入 manifest.json"""
        path = self._base / symbol / config_hash / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"manifest.json not found: {path}")
        return json.loads(path.read_text())
    
    def list_features(self, symbol: str, config_hash: str) -> list[str]:
        """列出所有 feature names（不載入資料）"""
        path = self._base / symbol / config_hash / "columns.json.gz"
        if not path.exists():
            # Fallback: 逐 group 讀 Parquet schema
            return self._list_features_from_parquet(symbol, config_hash)
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    
    # Mode 2: Column-Projected（只讀指定 columns）
    def load_columns(self, symbol: str, config_hash: str, 
                     columns: list[str]) -> pd.DataFrame:
        """Column projection — 只讀指定 columns"""
        manifest = self.load_manifest(symbol, config_hash)
        frames = []
        for group_name, group_info in manifest["groups"].items():
            group_cols = group_info.get("columns", [])
            needed = [c for c in columns if c in group_cols]
            if not needed:
                continue
            path = self._base / symbol / config_hash / group_info["file"]
            table = pq.read_table(str(path), columns=needed)
            frames.append(table.to_pandas())
        if not frames:
            logger.warning(f"No columns matched in any group: {columns[:5]}...")
            return pd.DataFrame()
        return pd.concat(frames, axis=1)
    
    # Mode 3: Per-Group Streaming（逐 group 串流，計算完釋放記憶體）
    def stream_groups(self, symbol: str, config_hash: str
                      ) -> Iterator[tuple[str, pd.DataFrame]]:
        """逐 group 串流"""
        manifest = self.load_manifest(symbol, config_hash)
        for group_name, group_info in manifest["groups"].items():
            path = self._base / symbol / config_hash / group_info["file"]
            df = pq.read_table(str(path)).to_pandas()
            yield group_name, df
            del df
    
    # Mode 4: Cross-Symbol（跨 symbol 載入同一組 columns）
    def load_cross_symbol(self, symbols: list[str], config_hash: str,
                          columns: list[str]) -> pd.DataFrame:
        """跨 symbol 載入 → MultiIndex"""
        frames = []
        for sym in symbols:
            df = self.load_columns(sym, config_hash, columns)
            df["_symbol"] = sym
            frames.append(df)
        result = pd.concat(frames)
        return result.set_index("_symbol", append=True)
```

### manifest.json 格式範例（V7 §13 決議 #1）

```json
{
  "version": "7.0",
  "symbol": "ETHUSDT",
  "config_hash": "18228376bf79e867590ecee84f1f3a16",
  "created_at": "2026-04-19T12:00:00",
  "total_features": 435389,
  "total_rows": 17928,
  "dtype": "float16",
  "groups": {
    "12h_L2_momentum": {
      "file": "12h_L2_momentum.parquet",
      "column_count": 312,
      "columns": ["12h_L2_momentum_ema_5", "12h_L2_momentum_ema_10", "..."]
    },
    "1h_L65_WorldQuant101_part1": {
      "file": "1h_L65_WorldQuant101_part1.parquet",
      "column_count": 5000,
      "columns": ["..."]
    },
    "1h_L65_WorldQuant101_part2": {
      "file": "1h_L65_WorldQuant101_part2.parquet",
      "column_count": 3421,
      "columns": ["..."]
    }
  }
}
```

### 禁止事項

- ❌ 不可保留 HDF5 讀取路徑（V7 決議：Parquet-only）
- ❌ 不可在 FeatureReader 中實作寫入功能（read-only）
- ❌ 不可修改 pipeline 計算邏輯（只改 persist 層）
- ❌ 不可跳過 float16 精度驗證直接部署
- ❌ manifest.json 不可存完整 column names（用 columns.json.gz 壓縮另存）

### 風險緩解

- R10（Parquet metadata 開銷）→ manifest.json 完全避開 Parquet 原生 metadata
- R19（讀取效能）→ PyArrow column projection 取代全檔掃描

### 邊界情況

1. **空 group（0 columns）** → 不寫入 Parquet，不計入 manifest groups
2. **全 NaN column** → float16 保留 NaN，manifest 仍記錄該 column
3. **columns.json.gz 缺失（舊版 output 相容）** → `list_features()` fallback 逐 group 讀 Parquet schema
4. **manifest.json 損壞/缺失** → raise FileNotFoundError，不嘗試修復
5. **Group 恰好 5000 columns** → 不拆分（只有 > 5000 才觸發拆分）
6. **float16 溢出（|value| > 65504）** → cast 後為 Inf，T5.0b 需記錄溢出位置
7. **磁碟空間不足** → persist 中途失敗時清理不完整的 manifest + Parquet

### ⚠️ 注意事項

- 完成後須**刪除舊 float32 資料**重新跑 pipeline（V7 §13 決議 #3）
- `columns.json.gz` 須 < 1 MB（V7 §13 決議 #1）
- FeatureReader 不支援 HDF5，只支援 Parquet（V7 設計決策）

---

## Task 5.1: ProcessPoolExecutor multi-symbol

- **SPEC 參考**: §7.1, §7.0
- **目標**: multi-symbol 平行處理（8 workers），使用 `ProcessPoolExecutor + spawn`
- **輸入**: symbols list (e.g. `['ETHUSDT', 'SOLUSDT', ...]`) + per-symbol K-line DataFrames + BTCUSDT reference data (Arrow IPC)
- **輸出**: per-symbol feature outputs（與 single-symbol pipeline golden 數值等價）
- **前置**: Numba JIT 預熱（§7.0.1）+ spawn context（§7.0.2）

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | `FeatureFactory.run_multi_symbol()` | 新增方法 |
| `momentum/FeatureEngineering/feature_factory.py` | `_worker_entry(symbol, config, ref_ipc_path)` | 新增 module-level 函式（picklable） |
| `momentum/factories.py` | `create_multi_symbol_runner()` | 新增 factory |

### 實作細節

1. **Numba 預熱**: main process 先呼叫所有 @njit 函式一次（fused_rolling_stats, rolling_skew_kurt 等），確保 cache 已建立
2. **spawn context**: `multiprocessing.get_context('spawn')`（不可用 fork，避免 TA-Lib GIL + CUDA 衝突）
3. **Reference data 共享**: BTCUSDT raw data 序列化為 Arrow IPC，workers read-only 讀取
4. 每個 worker 獨立 Registry（per-symbol scope，無 crosstalk）
5. 某 symbol 失敗 → 不影響其他 symbols，error 記錄到 `{symbol}_error.log`

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_multi_symbol(symbols: list[str], config: dict, ref_ipc_path: str, max_workers: int = 8):
    # Step 1: Numba warm-up in main process
    _warmup_numba_functions()
    
    # Step 2: spawn context
    ctx = mp.get_context('spawn')
    results = {}
    errors = {}
    
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as pool:
        futures = {
            pool.submit(_worker_entry, sym, config, ref_ipc_path): sym
            for sym in symbols
        }
        for future in as_completed(futures):
            sym = futures[future]
            try:
                results[sym] = future.result(timeout=600)
            except Exception as e:
                errors[sym] = str(e)
                logger.error(f"Symbol {sym} failed: {e}")
    
    return results, errors
```

### 禁止事項

- ❌ 不可使用 `fork()` context（R6, R11）
- ❌ 不可使用 ThreadPoolExecutor（TA-Lib 非 thread-safe）
- ❌ worker 間不可共享 mutable state（Registry 必須 per-worker 獨立建立）

### 風險緩解

- R6（GIL 競爭）→ ProcessPool + spawn 完全隔離
- R11（TA-Lib 非 thread-safe）→ 每個 worker 獨立 process
- R12（JIT cold start）→ main process 預熱 + `cache=True`
- R20（磁碟 I/O）→ 先 2-symbol pilot 測試

### 驗證

- **通過條件**: 8-symbol 平行結果與各 symbol 單獨 pipeline 執行結果 `np.allclose(atol=C1_MAP)` 全 PASS
- **測試**: T5.1（golden 比對）+ T5.2（crosstalk 驗證：symbol A 結果不含 symbol B 資料）

### 邊界情況

1. worker 數 > symbol 數（如 2 symbols, 8 workers）→ 只啟動 2 個 worker，不浪費資源
2. 單一 worker OOM → 該 symbol 記錄 error，其餘 symbols 繼續完成（graceful degradation）

---

## Task 5.2: Arrow IPC column-group intermediate

- **SPEC 參考**: §7.1
- **目標**: 使用 Arrow IPC 作為 column-group 中介格式（替代 .npy），worker 間透過 Arrow IPC 共享 reference data
- **輸入**: per-group numpy array / Polars DataFrame（來自 Task 2.3/2.8 的 per-group 儲存）
- **輸出**: Arrow IPC files（`.arrow`），可被 worker 直接 mmap 讀取
- **實作要點**:
  1. 在 persist_column_group() 中新增 Arrow IPC 寫入路徑：`pa.ipc.new_file(sink, schema)` + `write_batch`
  2. worker 內以 `pa.ipc.open_file(mmap)` zero-copy 讀取 reference data（BTCUSDT）
  3. 最終 output 仍可產生 Parquet（Task 2.8），Arrow IPC 僅為中間傳輸格式
  ```python
  # 寫入
  table = pa.table({col: arr for col, arr in zip(names, arrays)})
  with pa.ipc.new_file(path, table.schema) as writer:
      writer.write_table(table)
  # 讀取（worker 內）
  with pa.memory_map(path, 'r') as mmap:
      reader = pa.ipc.open_file(mmap)
      table = reader.read_all()
  ```
- **修改檔案**: `feature_storage.py` → `persist_column_group()` 新增 IPC 寫入; 新建 `arrow_ipc_utils.py`（讀寫工具）
- **不可做**:
  - ❌ 不可移除 Parquet 最終持久化路徑（FeatureReader 需要 Parquet）
  - ❌ 不可使用 Arrow Stream format（需 random access for mmap）
- **風險緩解**: ⊘（Arrow IPC 為 well-tested 格式）
- **驗證**: T5.1 — multi-symbol golden 比對間接驗證 IPC 正確性
- **Edge Cases**:
  - worker 讀取期間 IPC 檔案被刪除 → FileNotFoundError catch + retry
  - 超大 group（>1GB）→ 改為 chunked IPC 寫入

## Task 5.3: FeatureReader 統一讀取介面（Parquet-only）

- **SPEC 參考**: §7.1, V7 §11
- **目標**: 建立統一的 FeatureReader 介面，取代所有下游的 HDF5/DuckDB 讀取路徑，支援 4 種載入模式
- **輸入**: per-group Parquet files（來自 Task 2.8）+ manifest.json（Task 2.9）
- **輸出**: FeatureReader API — 所有下游（IC Analysis, ML Training, Feature Browser, SHAP）的唯一入口
- **設計依據**: V7 FEATURE_STORAGE_ARCHITECTURE_V7.md §11 分層儲存架構

### 修改檔案

| 檔案 | 函式/方法 | 修改類型 |
|------|----------|---------|
| `momentum/FeatureEngineering/feature_reader.py` | `FeatureReader` class | **新增** |
| `momentum/FeatureEngineering/feature_library.py` | `load()` / `load_multi()` | 改用 FeatureReader，移除 h5py |
| `api/services/feature_browser_service.py` | `_load_features_df()` + 12 個分析函式 | 改用 FeatureReader 三種模式 |
| `api/services/ic_analysis_service.py` | cross-sectional IC | 改用 FeatureReader per-feature streaming |
| `momentum/Analysis/coverage_analyzer.py` | `_resolve_feature_file_path()` | 移除 HDF5 路徑，改用 FeatureReader |

### 4 種載入模式

```python
class FeatureReader:
    """V7 統一特徵讀取介面 — 只支援 Parquet，不支援 HDF5"""
    
    def __init__(self, feature_base_path: str = "data_cache/features"):
        self._base = Path(feature_base_path)
    
    # Mode 1: Metadata-Only（零資料 I/O）
    def load_manifest(self, symbol: str, config_hash: str) -> dict:
        """載入 manifest.json"""
        path = self._base / symbol / config_hash / "manifest.json"
        return json.loads(path.read_text())
    
    def list_features(self, symbol: str, config_hash: str) -> list[str]:
        """列出所有 feature names（不載入資料）"""
        # 從 columns.json.gz 讀取（V7 §13 決議 #1）
        path = self._base / symbol / config_hash / "columns.json.gz"
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    
    # Mode 2: Column-Projected（只讀指定 columns）
    def load_columns(self, symbol: str, config_hash: str, 
                     columns: list[str]) -> pd.DataFrame:
        """Column projection — 只讀指定 columns"""
        manifest = self.load_manifest(symbol, config_hash)
        frames = []
        for group_name, group_info in manifest["groups"].items():
            needed = [c for c in columns if c in group_info["columns"]]
            if not needed:
                continue
            path = self._base / symbol / config_hash / group_info["file"]
            table = pq.read_table(str(path), columns=needed)
            frames.append(table.to_pandas())
        return pd.concat(frames, axis=1) if frames else pd.DataFrame()
    
    # Mode 3: Per-Group Streaming（逐 group 串流，計算完釋放記憶體）
    def stream_groups(self, symbol: str, config_hash: str
                      ) -> Iterator[tuple[str, pd.DataFrame]]:
        """逐 group 串流"""
        manifest = self.load_manifest(symbol, config_hash)
        for group_name, group_info in manifest["groups"].items():
            path = self._base / symbol / config_hash / group_info["file"]
            df = pq.read_table(str(path)).to_pandas()
            yield group_name, df
            del df
    
    # Mode 4: Cross-Symbol（跨 symbol 載入同一組 columns）
    def load_cross_symbol(self, symbols: list[str], config_hash: str,
                          columns: list[str]) -> pd.DataFrame:
        """跨 symbol 載入 → MultiIndex"""
        frames = []
        for symbol in symbols:
            df = self.load_columns(symbol, config_hash, columns)
            df["_symbol"] = symbol
            frames.append(df)
        result = pd.concat(frames)
        return result.set_index("_symbol", append=True)
```

### 下游函式 → 載入模式映射

| 下游函式 | 載入模式 | 說明 |
|----------|---------|------|
| Feature Browser `get_overview()` | Metadata-Only | manifest.json 即可 |
| Feature Browser `get_catalog()` | Metadata-Only | columns.json.gz |
| Feature Browser `get_ic_dashboard()` | Per-Group Streaming | 逐 group IC |
| Feature Browser `get_rolling_ic()` | Column-Projected | 單 feature |
| Feature Browser `get_quality_scorecard()` | Per-Group Streaming | 逐 group stats |
| Feature Browser `get_correlation_matrix()` | Column-Projected | top 200 |
| Feature Browser `get_vif()` | Column-Projected | top 200 |
| Feature Browser `get_drift_monitor()` | Per-Group Streaming | 逐 group |
| Feature Browser `get_coverage_matrix()` | Cross-Symbol | 多 symbols |
| IC Analysis (single) | Per-Group Streaming | 逐 group IC |
| IC Analysis (cross-sectional) | Cross-Symbol | per-feature × N symbols |
| LightGBM/XGBoost | Column-Projected | selected features |
| SHAP (cross-symbol) | Cross-Symbol | per-symbol iteration |

### 禁止事項

- ❌ 不可保留任何 h5py / HDF5 讀取路徑（V7 決議：Parquet-only）
- ❌ 不可新增 DuckDB 依賴（PyArrow column projection 已足夠）
- ❌ 不可在 FeatureReader 中寫入資料（read-only，寫入由 feature_storage.py 負責）
- ❌ 不可要求下游必須改用 FeatureReader 才能工作（`materialize_wide_df()` 保持可用作 fallback）

### 風險緩解

- R19：~~DuckDB footer scan overhead~~ → PyArrow column projection 無此問題
- R10：Parquet 45 萬欄位 metadata → manifest.json + columns.json.gz 完全避開

### 驗證

- **通過條件**: 
  1. FeatureReader 4 種模式都能正確讀取 V6.2+ 輸出
  2. `load_columns()` 結果與 `materialize_wide_df()` 的 column subset 數值一致
  3. `stream_groups()` 遍歷所有 groups 後 column count == manifest total
- **測試**: 
  - T5.3a `test_feature_reader_metadata_only` — manifest + list_features
  - T5.3b `test_feature_reader_column_projection` — selected columns 數值等價
  - T5.3c `test_feature_reader_stream_groups` — 全 groups 遍歷 count 一致
  - T5.3d `test_feature_reader_cross_symbol` — 2 symbols × same columns

### 邊界情況

1. manifest 引用的 Parquet 不存在 → raise FileNotFoundError with missing paths
2. columns.json.gz 缺失（舊版 output）→ fallback 到逐 group 讀 Parquet metadata
3. 指定 column 不在任何 group 中 → return empty DataFrame + log warning
4. 極大 group（>5000 cols，舊版未拆分）→ Per-Group Streaming 仍可處理（只是記憶體較高）

## Task 1.5（延遲到此）: Multi-TF 平行化

- **原 SPEC 參考**: §3.5
- **使用 ProcessPoolExecutor + spawn**（非 ThreadPoolExecutor）

---

## Phase 5 測試清單

| ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|----|---------|---------|---------|---------|
| T5.0a | `test_manifest_written_after_persist` | persist 後 manifest.json + columns.json.gz 存在且正確 | manifest["total_features"] == 實際 column 數; columns.json.gz < 1 MB | V7 §12 P0#1 |
| T5.0b | `test_float16_storage_precision` | float16 與 float32 差異 + NaN 保留 | relative diff < `np.finfo(np.float16).eps * 10`; NaN 位置完全一致; 溢出記錄 | V7 §12 P0#2 |
| T5.0c | `test_max_group_split` | >5000 columns 自動拆分 | part1 有 5000 cols, part2 有餘數; manifest groups 正確記錄 | V7 §12 P0#2 |
| T5.0d | `test_feature_reader_metadata_only` | `list_features()` 回傳正確 names | len == manifest["total_features"]; 與實際 Parquet columns 一致 | V7 §11 |
| T5.0e | `test_feature_reader_column_projection` | `load_columns()` 只讀指定 columns | 結果與 `materialize_wide_df()[columns]` 數值 `np.allclose` | V7 §11 |
| T5.0f | `test_feature_reader_stream_groups` | `stream_groups()` 逐 group 產出 | sum(group.shape[1]) == manifest["total_features"]; RSS < 2 GB | V7 §11 |
| T5.0g | `test_feature_library_uses_reader` | FeatureLibrary.load() 走 FeatureReader | `grep -r "import h5py" momentum/FeatureEngineering/feature_library.py` == 0 | V7 §12 P0#4 |
| T5.1 | `test_multi_symbol_parallel_correctness` | 2 sym × 2 TF 各自 golden 一致 | `np.allclose(atol=C1_MAP)` 全 PASS | §7.1 |
| T5.2 | `test_multi_symbol_no_crosstalk` | 無共享 Registry 污染 | symbol A 結果不含 symbol B 任何 column | §7.1 |
| T5.3a | `test_feature_reader_metadata_only` | manifest + list_features 正確 | 同 T5.0d | V7 §11 |
| T5.3b | `test_feature_reader_column_projection` | selected columns 數值等價 | 同 T5.0e | V7 §11 |
| T5.3c | `test_feature_reader_stream_groups` | 全 groups count == manifest total | 同 T5.0f | V7 §11 |
| T5.3d | `test_feature_reader_cross_symbol` | 2 symbols × same columns | MultiIndex 正確; per-symbol 數值與單獨 load 一致 | V7 §11 |
| T5.B1 | `test_multi_symbol_single_failure` | 某 symbol 失敗 | 其他 symbols 正常完成 + error log 記錄 | §7.1 |
| T5.B2 | `test_worker_oom_handling` | Worker OOM killed | 主進程捕獲 BrokenProcessPool exc + 記錄 | §7.1 |
| T5.B3 | `test_disk_full_mid_persist` | 磁碟空間不足 mid-run | 提前失敗 + 清理不完整檔案 | V7 §12 |

## Phase 5 → Done Gate

| 條件 | 要求 |
|------|------|
| C1~C6 全通過 | 全量 golden 比對 |
| 1 sym × 2 TF | < 20 min（Phase 2 後）或 < 7 min（Phase 3 後）|
| RSS 峰值 | < 2 GB |

---

# 風險緩解總表

| Risk | Phase | 緩解措施 | 驗證測試 |
|------|-------|---------|---------|
| R1 | 1 | ms→ns 轉換 + offset 測試 | T1.2, T1.B14 |
| R2 | 1 | assert len(combined)==len(primary_timestamps) | T1.B11 |
| R3 | 2 | 粒度調整至 ~1,200 | T2.B7 |
| R4 | 3 | float64 累加器 + 定期校正 + epsilon guard | T3.7, T3.8, T3.B2 |
| R5 | 4 | pl.fill_null(float('nan')) | T4.B1 |
| R6 | 5 | ProcessPoolExecutor + spawn | T5.1 |
| R7 | 0 | 分層 fallback golden | T0.3 |
| R8 | 2 | cleanup() + finally block | T2.B9 |
| R9 | 2 | 文件記錄跨 group ops 在 Stage A | T2.16 |
| R10 | 2 | per-group Parquet | T2.15 |
| R11 | 5 | ProcessPoolExecutor + spawn | Phase 5 |
| R12 | 3 | @njit(cache=True) | Phase 3 |
| R13 | 1 | int64 overflow test | T1.B15 |
| R14 | 2 | A/B 不同時在 RAM | T2.11 |
| R15 | 2 | 粒度 ~1,200 | T2.B7 |
| R16 | 3 | numba>=0.57,<0.60 | T3.B10 |
| R17 | 3 | epsilon guard M2<1e-30 | T3.B2 |
| R18 | 2 | 斷路器 MAX_L2_ESTIMATED_COLS | T2.B2 |
| R19 | 2 | ~~DuckDB footer scan~~ → FeatureReader PyArrow | T2.15 |
| R20 | 5 | 2-symbol pilot benchmark | T5.1 |
| R21 | 5 | FFACT_LAYER1_PARALLEL=0 直到 Phase 5 | Phase 5 |
| R22 | 2 | L6 顯式 column 引用 | T2.16 |
| R23 | 3 | 固定 variance 閾值 | T3.12 |
| R24 | 2 | Task 2.5 同時修改兩處 _combine_layers | T2.12 |
| R25 | 4 | polars>=0.20,<0.21 | T4.1 |

---

# 測試檔案結構

```
tests/
├── test_golden_output_generation.py      # T0.1~T0.4
├── test_searchsorted_align.py            # T1.1~T1.5, T1.8~T1.10, T1.B1~T1.B10, T1.B14~T1.B15
├── test_primary_self_align_skip.py       # T1.6, T1.B11~T1.B13
├── test_multi_tf_golden_equivalence.py   # T1.7
├── test_golden_equivalence.py            # 通用 golden comparison
├── test_column_group.py                  # T2.1~T2.10
├── test_cgsa_pipeline.py                 # T2.11~T2.17, T2.B1~T2.B9
├── test_numba_rolling.py                 # T3.1~T3.12, T3.B1~T3.B13
├── test_polars_engines.py                # T4.1~T4.4, T4.B1~T4.B3
├── test_multi_symbol_parallel.py         # T5.1~T5.3, T5.B1~T5.B3
├── performance/
│   ├── test_searchsorted_perf.py         # T1.P1~T1.P3
│   ├── test_numba_rolling_perf.py        # T3.P1~T3.P2
│   └── test_cgsa_memory.py              # T2.13
```

---

# 效能預估對照表

| 場景 | 現行 | +Phase 1 | +Phase 2 | +Phase 3 | +Phase 4 | +Phase 5 |
|------|------|---------|---------|---------|---------|---------|
| 1 sym × 2 TF | 170+ min ❌ | ~163 min | ~20 min | ~7 min | ~3.3 min | ~3.3 min |
| 1 sym × 4 TF | OOM ❌ | OOM | ~40 min | ~14 min | ~6.5 min | ~6.5 min |
| 100 sym × 2 TF | OOM ❌ | OOM | ~33 hrs | ~12 hrs | ~5.5 hrs | ~41 min |

---

# 附錄：AI Agent 執行清單

```
Phase 0:
  ☑ Task 0.1  L2 計時 log
  ☑ Task 0.2  heartbeat log
  ☑ Task 0.3  Golden output 腳本與測試建立
  ☑ T0.1~T0.4 PASSED；實資料已成功產出 golden（Tier2 reduced, allow-data-gaps）
  ☑ Gate 0→1

Phase 1:
  ☑ Task 1.1  build_asof_index_map()
  ☑ Task 1.2  _searchsorted_align()
  ☑ Task 1.3  align_to_primary() 切換
  ☑ Task 1.4  self-align skip
  ☑ T1.1~T1.10 + T1.B1~T1.B15 + T1.P1~T1.P3（29 passed）
  ☑ Gate 1→2（B2+D < 50s：test_phase1_gate_b2_plus_d_under_50s）

Phase 2:
  ☑ Task 2.1   ColumnGroup dataclass
  ☑ Task 2.2   ColumnGroupRegistry
  ☑ Task 2.3   L1 per-indicator output
  ☑ Task 2.4   L2 兩階段計算
  ☑ Task 2.5   _combine_layers registry（含 multi_tf_generator）
  ☑ Task 2.6   Multi-TF column tagging
  ☑ Task 2.7   L6.5 per-group
  ☑ Task 2.8   Persist Parquet
  ☑ Task 2.9   manifest.json
  ☑ Task 2.10  L7 per-group validate
  ☑ Task 2.11  materialize_wide_df()
  ☑ Task 2.12  逐層 A/B 驗證（scripts/validate_cgsa_ab.py + T2.11/T2.12/T2.13 smoke）
  ☑ L4/L5/L6 依賴域確認（L4 fast-path + L5/L6 domain tests）
  ☑ Column Ordering 確認（T2.8 + phase2 ordering confirmation）
  ☑ T2.1~T2.10（單元測試）
  ☑ T2.1~T2.17 + T2.B1~T2.B9
  ☑ Gate 2→3（T2.11 PASS, T2.12 PASS, T2.13 PASS）
  ☑ re-profile（真實 h5：/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5；results/l56_golden_baseline/l23_hotspots_postopt_1run.json；L2=20.028377s、L3=17.82218675s；L2 top-1=worldquant 19.204239833s；L3 top-1=rank 6.499211666s；目前 top-1 bottleneck 為 L2）

Phase 3:
  ☑ Task 3.1  fused_rolling_stats（float64 累加器）
  ☑ Task 3.2  online skew/kurt（Pebay + 校正）
  ☑ Task 3.3  rolling rank（average tie）
  ☑ Task 3.4  slope
  ☑ Task 3.5  整合 RollingAggregator（FFACT_USE_NUMBA_ROLLING 分流 + fallback）
  ☑ Task 3.6  數值等價 suite（T3.11/T3.12 + T3.P1/T3.P2 補齊）
  ☑ Batch 3a smoke（T3.1~T3.6, T3.9, T3.10 + 邊界子集）
  ☑ Batch 3b smoke（T3.7, T3.8, T3.B2）
  ☑ T3.1~T3.12 + T3.B1~T3.B13 + T3.P1~T3.P2（39 passed）
  ☑ Gate 3→4（re-profile: results/l56_golden_baseline/phase3_gate_compare_eth_1run.json；L2=90.822s、L6.5=0.0s、pipeline_total=303.848s、(L2+L6.5)/total=29.89%）

Phase 4 (條件性):
  ☑ SKIP（條件未觸發：L2+L6.5=29.89% < 30%，且 No-Phase-4 pipeline_total=303.848s < 7 min/sym）

Phase 5:
  ☑ Numba JIT 預熱
  ☑ Task 5.0  V7 P0 儲存基礎建設（manifest.json + columns.json.gz + float16 + max_group_split + FeatureReader）
  ☑ Task 5.1  multi-symbol ProcessPoolExecutor
  ☑ Task 5.2  Arrow IPC intermediate
  ☑ Task 5.3  FeatureReader 統一讀取介面
  ☑ Task 1.5  Multi-TF 平行（延遲）
  ☑ T5.0a~T5.0g + T5.1~T5.3d + T5.B1~T5.B3（26 passed）
  □ 最終 C1~C6 全量驗證
```

---

> **文件狀態**: V1（Frozen）  
> **SPEC 來源**: `FEATURE_FACTORY_OPTIMIZATION_SPEC.md` V2 🔒  
> **統計**: 33 Tasks | 98 Tests | 25 Risks | 6 Constraints | 5 Phase Gates
