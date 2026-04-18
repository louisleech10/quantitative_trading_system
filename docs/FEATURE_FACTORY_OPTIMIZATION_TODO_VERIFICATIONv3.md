# FEATURE_FACTORY_OPTIMIZATION_TODO 驗證報告 V3

> **驗證輪次**: Round 3（完全重新執行）  
> **驗證日期**: 2026-04-16  
> **驗證對象**: `docs/FEATURE_FACTORY_OPTIMIZATION_TODO.md`（二次修正版）  
> **參照 SPEC**: `docs/FEATURE_FACTORY_OPTIMIZATION_SPEC.md` V2 (FROZEN 2026-04-16)  
> **驗證模板**: `templates/TODO_GENERATION_PROMPT.md` Stage 3（5 Pass / 21 Tables）  
> **前次報告**: V1（8 FAIL → 修正 → 0 FAIL）、V2（3 FAIL → 修正 → 0 FAIL）  
> **本輪結果**: **0 FAIL — 全數通過**

---

## 驗證摘要

| Pass | 名稱 | Tables | FAIL 數 | 結果 |
|---|---|---|---|---|
| Pass 1 | 追溯完整性 | T1~T7 | 0 | ✅ PASS |
| Pass 2 | 結構完整性 + Task 深度 | T8~T9 | 0 | ✅ PASS |
| Pass 3 | 索引反查驗證 | 3 samples | 0 | ✅ PASS |
| Pass 4 | 20 項數值一致性 | 20 items | 0 | ✅ PASS |
| Pass 5 | 語義驗證（9 維度） | T10~T18 | 0 | ✅ PASS |
| **總計** | | **21 Tables** | **0 FAIL** | **✅ 全數通過** |

---

## Pass 1：追溯完整性

### 表 1：Task 追溯（SPEC → TODO）

| # | SPEC Task ID | SPEC 簡述 | TODO 對應位置 | 狀態 |
|---|---|---|---|---|
| 1 | Task 0.1 | L2 前後計時 log | Phase 0 / Task 0.1 | ✅ |
| 2 | Task 0.2 | F 段 heartbeat log | Phase 0 / Task 0.2 | ✅ |
| 3 | Task 0.3 | 建立 Golden Output | Phase 0 / Task 0.3 | ✅ |
| 4 | Task 1.1 | build_asof_index_map() | Phase 1 / Task 1.1 | ✅ |
| 5 | Task 1.2 | _searchsorted_align() | Phase 1 / Task 1.2 | ✅ |
| 6 | Task 1.3 | align_to_primary() 切換 | Phase 1 / Task 1.3 | ✅ |
| 7 | Task 1.4 | 跳過 Primary TF Self-Alignment | Phase 1 / Task 1.4 | ✅ |
| 8 | Task 1.5 | Multi-TF 平行化 DEFERRED | Phase 1 DEFERRED + Phase 5 延遲 | ✅ |
| 9 | Task 2.1 | ColumnGroup dataclass | Phase 2 / Task 2.1 | ✅ |
| 10 | Task 2.2 | ColumnGroupRegistry | Phase 2 / Task 2.2 | ✅ |
| 11 | Task 2.3 | L1 per-indicator → .npy | Phase 2 / Task 2.3 | ✅ |
| 12 | Task 2.4 | L2 兩階段計算 | Phase 2 / Task 2.4 | ✅ |
| 13 | Task 2.5 | _combine_layers registry | Phase 2 / Task 2.5 | ✅ |
| 14 | Task 2.6 | Multi-TF column tagging | Phase 2 / Task 2.6 | ✅ |
| 15 | Task 2.7 | L6.5 per-group preprocessing | Phase 2 / Task 2.7 | ✅ |
| 16 | Task 2.8 | Persist per-group Parquet | Phase 2 / Task 2.8 | ✅ |
| 17 | Task 2.9 | manifest.json | Phase 2 / Task 2.9 | ✅ |
| 18 | Task 2.10 | L7 per-group validate | Phase 2 / Task 2.10 | ✅ |
| 19 | Task 2.11 | materialize_wide_df() | Phase 2 / Task 2.11 | ✅ |
| 20 | Task 2.12 | 逐層 Golden 比對 | Phase 2 / Task 2.12 | ✅ |
| 21 | Task 3.1 | fused_rolling_stats (Numba) | Phase 3 / Task 3.1 | ✅ |
| 22 | Task 3.2 | online skew/kurt (Pebay) | Phase 3 / Task 3.2 | ✅ |
| 23 | Task 3.3 | rolling rank (bisect) | Phase 3 / Task 3.3 | ✅ |
| 24 | Task 3.4 | slope (running sums) | Phase 3 / Task 3.4 | ✅ |
| 25 | Task 3.5 | 整合到 RollingAggregator | Phase 3 / Task 3.5 | ✅ |
| 26 | Task 3.6 | 數值等價驗證 suite | Phase 3 / Task 3.6 | ✅ |
| 27 | Task 4.1 | L1 → Polars DataFrame | Phase 4 / Task 4.1 | ✅ |
| 28 | Task 4.2 | L2 → Polars with_columns | Phase 4 / Task 4.2 | ✅ |
| 29 | Task 4.3 | L6.5 → Polars expressions | Phase 4 / Task 4.3 | ✅ |
| 30 | Task 4.4 | NaN 語義對齊驗證 | Phase 4 / Task 4.4 | ✅ |
| 31 | Task 5.1 | ProcessPoolExecutor multi-symbol | Phase 5 / Task 5.1 | ✅ |
| 32 | Task 5.2 | Arrow IPC intermediate | Phase 5 / Task 5.2 | ✅ |
| 33 | Task 5.3 | DuckDB Parquet 下游介面 | Phase 5 / Task 5.3 | ✅ |
| 34 | Task 5.4 | 100 sym × 4 TF × 8 workers < 90 min | — | ⊘ 合理省略 |

> **Task 5.4 處置**：SPEC §7.1 的 Task 5.4 為 benchmark target（「預估：100 sym × 4 TF × 8 workers < 90 min」），非獨立可執行 Task。TODO 在「效能預估對照表」與 Phase 5→Done Gate 中均涵蓋此目標。標記為「合理省略」。

**表 1 結論**：33/33 Tasks 映射完成，0 缺失。

---

### 表 2：Test 追溯（SPEC → TODO）

| # | SPEC Test ID 範圍 | 數量 | TODO 對應 Phase | 狀態 |
|---|---|---|---|---|
| 1 | T0.1~T0.4 | 4 | Phase 0 | ✅ |
| 2 | T1.1~T1.10 | 10 | Phase 1 核心 | ✅ |
| 3 | T1.B1~T1.B15 | 15 | Phase 1 邊界 | ✅ |
| 4 | T1.P1~T1.P3 | 3 | Phase 1 效能 | ✅ |
| 5 | T2.1~T2.10 | 10 | Phase 2 單元 | ✅ |
| 6 | T2.11~T2.17 | 7 | Phase 2 整合 | ✅ |
| 7 | T2.B1~T2.B9 | 9 | Phase 2 邊界 | ✅ |
| 8 | T3.1~T3.12 | 12 | Phase 3 數值 | ✅ |
| 9 | T3.B1~T3.B13 | 13 | Phase 3 邊界 | ✅ |
| 10 | T3.P1~T3.P2 | 2 | Phase 3 效能 | ✅ |
| 11 | T4.1~T4.4 | 4 | Phase 4 核心 | ✅ |
| 12 | T4.B1~T4.B3 | 3 | Phase 4 邊界 | ✅ |
| 13 | T5.1~T5.3 | 3 | Phase 5 核心 | ✅ |
| 14 | T5.B1~T5.B3 | 3 | Phase 5 邊界 | ✅ |
| **合計** | | **98** | | **0 缺失** |

---

### 表 3：Risk 追溯（SPEC §10 → TODO）

| # | Risk ID | 風險簡述 | TODO 緩解位置 | 狀態 |
|---|---|---|---|---|
| 1 | R1 | searchsorted ms/ns off-by-one | Task 1.1 + T1.2, T1.B14 | ✅ |
| 2 | R2 | self-align skip 後 index 不一致 | Task 1.4 + T1.B11 | ✅ |
| 3 | R3 | per-group 過多小檔案 | Task 2.8 + T2.B7 | ✅ |
| 4 | R4 | Numba skew/kurt 數值不穩定 | Task 3.1, 3.2 + T3.7, T3.8, T3.B2 | ✅ |
| 5 | R5 | Polars null ≠ NaN | Task 4.4 + T4.B1 | ✅ |
| 6 | R6 | Multi-TF TA-Lib GIL 競爭 | Task 5.1 (ProcessPool + spawn) | ✅ |
| 7 | R7 | pipeline 跑不完→無完整 golden | Task 0.3 (三層 baseline) | ✅ |
| 8 | R8 | .npy 中介檔案硬碟暴漲 | Task 2.2 (persist 後刪除) | ✅ |
| 9 | R9 | L2 新 operator 打破 per-group | Task 2.4 (分批 + 斷路器) | ✅ |
| 10 | R10 | Parquet 45 萬欄位 metadata | Task 2.8 (粒度 ~1,200) | ✅ |
| 11 | R11 | TA-Lib 非 thread-safe | Task 5.1 (ProcessPool + spawn) | ✅ |
| 12 | R12 | Numba JIT cold start | Task 3.1 禁止事項 + Task 5.1 預熱 | ✅ |
| 13 | R13 | int64 ms→ns 溢出 | Task 1.1 + T1.B15 | ✅ |
| 14 | R14 | A/B 同時執行→RAM 翻倍 | Task 2.12 (逐層比對) | ✅ |
| 15 | R15 | .npy 33,600+ 檔案爆炸 | Task 2.2, 2.8 (粒度降至 ~1,200) | ✅ |
| 16 | R16 | Numba ARM64/macOS JIT 相容性 | Task 3.2 (fallback env var) | ✅ |
| 17 | R17 | Numba skew/kurt zero-variance | Task 3.2 (epsilon guard) | ✅ |
| 18 | R18 | L2 O(N²) 組合爆炸 | Task 2.4 (斷路器 100K) | ✅ |
| 19 | R19 | DuckDB Parquet footer scan | Task 2.8 (粒度 ~1,200) | ✅ |
| 20 | R20 | Phase 5 磁碟 I/O 未建模 | Task 5.1 (2-symbol pilot) | ✅ |
| 21 | R21 | L1 ThreadPool + TA-Lib 安全風險 | 風險緩解總表 Phase 5 | ✅ |
| 22 | R22 | L6 _find_column fuzzy matching 失敗 | 附加 Task L6 Stage A/B | ✅ |
| 23 | R23 | L3 variance_filter 非決定性 | Task 3.5 | ✅ |
| 24 | R24 | MultiTFGenerator._combine_layers 未覆蓋 | Task 2.5 | ✅ |
| 25 | R25 | Polars 版本鎖定風險 | Task 4.4 | ✅ |

**表 3 結論**：25/25 Risks 全部有緩解措施。

---

### 表 4：Phase Gate 追溯

| # | Gate | SPEC §8 條件 | TODO 對應段 | 狀態 |
|---|---|---|---|---|
| 1 | Phase 0→1 | Golden 已建立 + L2 計時 log 可見 + T0.1~T0.4 PASS | Phase 0→1 Gate | ✅ |
| 2 | Phase 1→2 | T1.3/T1.6/T1.7 PASS + B2+D < 50s | Phase 1→2 Gate | ✅ |
| 3 | Phase 2→3 | T2.11/T2.13 PASS + 無 global concat | Phase 2→3 Gate | ✅ |
| 4 | Phase 3→4 | T3.12 PASS + re-profile L2+L6.5 > 30% | Phase 3→4 Gate | ✅ |
| 5 | Phase 4/5→Done | 全量 golden PASS + <20min + RSS<2GB | Phase 5→Done Gate | ✅ |

**表 4 結論**：5/5 Gates 全部映射。

---

### 表 5：硬約束追溯（C1~C6）

| # | Constraint | SPEC §1.1 | TODO §0.2 | 狀態 |
|---|---|---|---|---|
| 1 | C1 | 數值等價 per-layer atol | ✅ 含完整 per-layer atol map (12 operations) | ✅ |
| 2 | C2 | 不減特徵 453,953 cols | ✅ | ✅ |
| 3 | C3 | 不改 column name + 顯式排序 | ✅ | ✅ |
| 4 | C4 | RAM ≤ 6 GB | ✅ | ✅ |
| 5 | C5 | 無 future leakage | ✅ | ✅ |
| 6 | C6 | NaN 語義一致 | ✅ | ✅ |

---

### 表 6：§0 Agent 規範追溯

| # | SPEC §0 子節 | 主題 | TODO 涵蓋方式 | 狀態 |
|---|---|---|---|---|
| 1 | §0.1 | 解耦 7 規則 | §0.1.1 完整表格 | ✅ |
| 2 | §0.2 | Logging 規範 | §0.1.3 | ✅ |
| 3 | §0.3 | Ultra Think 開發流程 | §0.1.2 | ✅ |
| 4 | §0.4 | Error Handling 模式 | §0.1.4 | ✅ |
| 5 | §0.5 | Type Hints 要求 | §0.1.5 + §0.4 Pre-Commit | ✅ |
| 6 | §0.6 | 命名規範 | §0.1.5 | ✅ |
| 7 | §0.7 | 測試規範 | §0.4 Pre-Commit (中文 docstring、獨立執行) | ✅ |
| 8 | §0.8 | 效能程式碼慣例 | §0.4 Pre-Commit (效能已向量化) | ✅ |
| 9 | §0.9 | Factory 注入模式 | §0.1.6 | ✅ |
| 10 | §0.10 | Git Branch 與 Commit 慣例 | §0.1.7 | ✅ |
| 11 | §0.11 | Data Truth Principle | §0.4 Pre-Commit (無 hardcoded data) | ✅ |
| 12 | §0.12 | 向後相容原則 | §0.5 Fallback 表 | ✅ |
| 13 | §0.13 | Pre-Commit 檢查清單 | §0.4 (12 項) | ✅ |

**表 6 結論**：13/13 子節全部涵蓋。

---

### 表 7：補充項目清單

| # | 補充項目 | 類型 | TODO 位置 | 補充理由 |
|---|---|---|---|---|
| 1 | 附加 Task: L4 快速路徑強制 | SPEC §4.2.2 隱含需求 | Phase 2 附加 Task | 需具體修改但 SPEC 未獨立成 Task |
| 2 | 附加 Task: L5 依賴域定義 | SPEC §4.2.3 確認項 | Phase 2 附加 Task | 架構確認 |
| 3 | 附加 Task: L6 Stage A/B | SPEC §4.2.4 確認項 | Phase 2 附加 Task | 架構確認 + R22 緩解 |
| 4 | 附加 Task: Column Ordering 驗證 | SPEC §4.8 確認項 | Phase 2 附加 Task | C3 約束衍生 |

**Pass 1 結論**：**全部 SPEC ID 均在 TODO 中映射。0 缺失。**

---

## Pass 2：結構完整性 + Task 深度

### 表 8：模板段落完整性（13 必要段落）

| # | 必要段落 | 存在? | 內容品質 |
|---|---|---|---|
| 1 | TODO header（版本/狀態/SPEC ref/日期） | ✅ | V1 Frozen / SPEC V2 / 2026-04-15 / 方案 M |
| 2 | §0.1 必遵開發規則 | ✅ | 7 條規則各有程式碼範例/表格+影響描述 |
| 3 | §0.2 硬約束表 | ✅ | ID+約束+驗證+per-layer atol |
| 4 | §0.3 通用驗收流程 | ✅ | 7 步驟流程 + 回退策略 |
| 5 | §0.4 Pre-Commit Checklist | ✅ | 12 個具體檢查項 |
| 6 | §0.5 全域前置條件 | ✅ | Fallback 環境變數表（4 env vars） |
| 7 | 執行策略 — 依賴拓撲 | ✅ | 完整 ASCII 圖含 Phase 0~5 全 33 Tasks |
| 8 | 執行策略 — 批次明細表 | ✅ | 15 Batches 含預估規模 |
| 9 | 執行策略 — Gate 檢查表 | ✅ | 5 Gates 引用 Test ID + 條件 |
| 10 | 執行策略 — 快速執行參考 | ✅ | 8 prompt blocks（可複製） |
| 11 | Phase 目標與驗收標準 | ✅ | 每 Phase 有摘要 |
| 12 | Phase 測試三層結構 | ✅ | 核心+邊界+效能 |
| 13 | Phase Gate 段落 | ✅ | 5 Gate 段落齊全 |

**表 8 結論**：13/13 段落齊全。

---

### 表 9：Task 深度全掃描（33 Tasks × 6 欄位）

| Task | 實作≥3? | 偽碼? | 函式名? | 不可做? | Edge≥2? | 驗證具體? | 判定 |
|---|---|---|---|---|---|---|---|
| 0.1 | ✅ 3 | ✅ | ✅ `_layer2_derived_features()` | ✅ 3禁止 | ✅ 2 | ✅ T0.1 | PASS |
| 0.2 | ✅ 4 | ✅ | ✅ `concat_with_memmap()` | ✅ 3禁止 | ✅ 2 | ✅ T0.2 | PASS |
| 0.3 | ✅ 5 | ✅ | ✅ `generate_golden_output.py` | ✅ 3禁止 | ✅ 2 | ✅ T0.3, T0.4 | PASS |
| 1.1 | ✅ 5 | ✅ | ✅ `build_asof_index_map()` | ✅ 3禁止 | ✅ 4 | ✅ T1.1, T1.2 | PASS |
| 1.2 | ✅ 5 | ✅ | ✅ `_searchsorted_align()` | ✅ 2禁止 | ✅ 2 | ✅ T1.3 atol | PASS |
| 1.3 | ✅ 4 | ✅ | ✅ `align_to_primary()` | ✅ 2禁止 | ✅ 2 | ✅ T1.3, T1.10 | PASS |
| 1.4 | ✅ 4 | ✅ | ✅ `generate_multi_tf()` | ✅ 2禁止 | ✅ 3 | ✅ T1.6 | PASS |
| 1.5 | — DEFERRED — | — | — | — | — | — | PASS |
| 2.1 | ✅ 5 | ✅ | ✅ `column_group.py` | ✅ 2禁止 | ✅ 2 | ✅ T2.1, T2.2 | PASS |
| 2.2 | ✅ 6 | ✅ | ✅ `column_group_registry.py` | ✅ 3禁止 | ✅ 3 | ✅ T2.3~T2.10 | PASS |
| 2.3 | ✅ 4 | ⊘ | ✅ `_layer1_atomic_indicators()` | ✅ 2禁止 | ✅ 2 | ✅ T2.11 | PASS |
| 2.4 | ✅ 4 | ✅ | ✅ `compute_all()` | ✅ 2禁止 | ✅ 2 | ✅ T2.16 | PASS |
| 2.5 | ✅ 3 | ⊘ | ✅ `_combine_layers()` ×2 | ✅ 2禁止 | ✅ 2 | ✅ T2.12 | PASS |
| 2.6 | ✅ 3 | ⊘ | ✅ `_apply_timeframe_tag()` | ✅ 1禁止 | ✅ 2 | ✅ T2.11 | PASS |
| 2.7 | ✅ 3 | ✅ | ✅ `FeaturePreprocessor` | ✅ 2禁止 | ✅ 2 | ✅ T2.17 | PASS |
| 2.8 | ✅ 4 | ⊘ | ✅ `FeatureStorage` | ✅ 2禁止 | ✅ 2 | ✅ T2.15 | PASS |
| 2.9 | ✅ 4 | ⊘ | ✅ `_write_manifest()` | ✅ 1禁止 | ✅ 2 | ✅ T2.14 | PASS |
| 2.10 | ✅ 3 | ⊘ | ✅ `_layer7_validate_and_persist()` | ✅ 1禁止 | ✅ 2 | ✅ T2.11 | PASS |
| 2.11 | ✅ 4 | ✅ | ✅ `materialize_wide_df()` | ✅ 1禁止 | ✅ 2 | ✅ T2.11 | PASS |
| 2.12 | ✅ 5 | ⊘ | ✅ `validate_cgsa_ab.py` | ✅ 2禁止 | ✅ 2 | ✅ T2.11 | PASS |
| 3.1 | ✅ 7 | ✅ | ✅ `numba_rolling.py` | ✅ 3禁止 | ✅ 3 | ✅ T3.1~T3.6 | PASS |
| 3.2 | ✅ 4 | ✅ | ✅ `rolling_skew_kurt()` | ✅ 2禁止 | ✅ 3 | ✅ T3.7, T3.8 | PASS |
| 3.3 | ✅ 4 | ✅ | ✅ `rolling_rank()` | ✅ 2禁止 | ✅ 3 | ✅ T3.9, T3.B9 | PASS |
| 3.4 | ✅ 3 | ⊘ | ✅ `rolling_slope()` | ✅ 1禁止 | ✅ 2 | ✅ T3.10 | PASS |
| 3.5 | ✅ 5 | ⊘ | ✅ `RollingAggregator.compute_all()` | ✅ 2禁止 | ✅ 2 | ✅ T3.11, T3.12 | PASS |
| 3.6 | ✅ 3 | ✅ | ✅ `test_numba_rolling.py` + `conftest` | ✅ 2禁止 | ✅ 2 | ✅ pytest PASS | PASS |
| 4.1 | ✅ 3 | ✅ | ✅ `_layer1_atomic_indicators()` | ✅ 2禁止 | ✅ 2 | ✅ T4.1 | PASS |
| 4.2 | ✅ 3 | ✅ | ✅ `compute_derived_features()` | ✅ 2禁止 | ✅ 2 | ✅ T4.1 | PASS |
| 4.3 | ✅ 4 | ✅ | ✅ `preprocess()` | ✅ 2禁止 | ✅ 2 | ✅ T4.2 | PASS |
| 4.4 | ✅ 3 | ✅ | ✅ `feature_factory.py` + `requirements.txt` | ✅ 2禁止 | ✅ 2 | ✅ T4.B1 | PASS |
| 5.1 | ✅ 5 | ✅ | ✅ `run_multi_symbol()`, `_worker_entry()` | ✅ 3禁止 | ✅ 2 | ✅ T5.1, T5.2 | PASS |
| 5.2 | ✅ 3 | ✅ | ✅ `persist_column_group()` + `arrow_ipc_utils.py` | ✅ 2禁止 | ✅ 2 | ✅ T5.1 | PASS |
| 5.3 | ✅ 3 | ✅ | ✅ `duckdb_reader.py` + `feature_storage.py` | ✅ 2禁止 | ✅ 2 | ✅ T5.3 | PASS |

**表 9 結論**：33/33 Tasks 全部達到深度標準。**0 FAIL**。

---

## Pass 3：索引反查驗證

### 抽樣 1：Task 0.1（第一個）

| 驗證項 | Index A 記載 | TODO 本體 | 一致? |
|---|---|---|---|
| Phase | 0 | Phase 0 段 | ✅ |
| 描述 | L2 前後計時 log | 「在 `_layer2_derived_features()` 前後各加…」 | ✅ |
| 依賴 | — | 無 | ✅ |
| 修改檔案 | feature_factory.py | 修改檔案表含 feature_factory.py | ✅ |
| 測試引用 | T0.1 | Phase 0 測試含 T0.1 | ✅ |

### 抽樣 2：Task 2.7（中間 #15）

| 驗證項 | Index A 記載 | TODO 本體 | 一致? |
|---|---|---|---|
| Phase | 2 | Phase 2 段 | ✅ |
| 描述 | L6.5 per-group preprocessing | 「修改 FeaturePreprocessor」 | ✅ |
| 依賴 | 2.1 | 「依賴：Task 2.1（ColumnGroup）」 | ✅ |
| 修改檔案 | preprocessing/ | 修改檔案表含 preprocessing/ | ✅ |
| 測試引用 | T2.17 | Phase 2 測試含 T2.17 | ✅ |

### 抽樣 3：Task 5.3（最後一個）

| 驗證項 | Index A 記載 | TODO 本體 | 一致? |
|---|---|---|---|
| Phase | 5 | Phase 5 段 | ✅ |
| 描述 | DuckDB Parquet 下游介面 | 「新建 duckdb_reader.py + 修改 feature_storage.py」 | ✅ |
| 依賴 | Phase 2 | 「依賴：Task 2.8（Parquet persist）」 | ✅ |
| 修改檔案 | feature_storage.py + duckdb_reader.py | 修改檔案表一致 | ✅ |
| 測試引用 | T5.3 | Phase 5 測試含 T5.3 | ✅ |

**Pass 3 結論**：3/3 抽樣全部一致。**0 FAIL**。

---

## Pass 4：20 項數值一致性

| # | 檢查項 | 左側值 | 右側值 | 一致? |
|---|---|---|---|---|
| 1 | Index A Task 數 | 33 | TODO 本體 Task 數 = 33 | ✅ |
| 2 | Index B Test 數 | 98 | TODO 本體 Test 數 = 98 | ✅ |
| 3 | Index C Risk 數 | 25 | TODO 風險緩解總表 = 25 | ✅ |
| 4 | Index D Gate 數 | 5 | TODO Gate 段落 = 5 | ✅ |
| 5 | Index E Constraint 數 | 6 | TODO §0.2 C1~C6 = 6 | ✅ |
| 6 | Index F Env Var 數 | 9 | TODO Env Var 引用 = 9 | ✅ |
| 7 | Index G Code File 數 | 14 | TODO 修改檔案集合 = 14 | ✅ |
| 8 | Phase 0 Task IDs | {0.1,0.2,0.3} | 3 Tasks in Phase 0 | ✅ |
| 9 | Phase 1 Task IDs | {1.1,1.2,1.3,1.4,1.5} | 5 Tasks (1.5 DEFERRED) | ✅ |
| 10 | Phase 2 Task IDs | {2.1~2.12} | 12 Tasks in Phase 2 | ✅ |
| 11 | Phase 3 Task IDs | {3.1~3.6} | 6 Tasks in Phase 3 | ✅ |
| 12 | Phase 4 Task IDs | {4.1~4.4} | 4 Tasks in Phase 4 | ✅ |
| 13 | Phase 5 Task IDs | {5.1~5.3, 1.5} | 3+1 Tasks in Phase 5 | ✅ |
| 14 | Batch 數 | 15 | Batch 明細表 = 15 | ✅ |
| 15 | ΣBatch Tasks | 33 | Batch union = 33 | ✅ |
| 16 | Prompt 數 | 8 | 快速執行參考 = 8 | ✅ |
| 17 | 測試檔案數 | 11+3 | 功能 11 + 效能 3 = 14 | ✅ |
| 18 | 風險緩解行數 | 25 | R1~R25 = 25 | ✅ |
| 19 | 效能預估列數 | 6 | 現行→+Phase1~5 = 6 | ✅ |
| 20 | 矛盾筆數 | 3+1 | Deliverable #1.5 = 3+1 | ✅ |

**Pass 4 結論**：20/20 全部閉合。**0 FAIL**。

---

## Pass 5：語義驗證（9 維度）

### 表 10 — 5a Cross-Task 矛盾

| # | Task A | Task B | 潛在矛盾 | 判定 |
|---|---|---|---|---|
| 1 | 2.5 (combine_layers) | 2.11 (materialize_wide_df) | 2.5 消除 global concat，2.11 重組？ | ✅ PASS — 2.11 為 @deprecated 相容層 |
| 2 | 1.3 (searchsorted) | 2.5 (CGSA) | Phase 2 後 searchsorted 是否仍需？ | ✅ PASS — 標記 transitional，non-primary TF 仍有價值 |
| 3 | 3.5 (RollingAggregator) | 2.7 (L6.5 per-group) | 時序依賴？ | ✅ PASS — Phase 2 先於 Phase 3 |
| 4 | 4.1~4.4 (Polars) | 3.1~3.5 (Numba) | 技術衝突？ | ✅ PASS — 不同 Layer 不重疊 |

**5a 結論**：0 真實矛盾。

### 表 11 — 5b 實作可行性

| # | Task | 風險 | 判定 |
|---|---|---|---|
| 1 | 3.1 | Numba ARM64 macOS | ✅ — R16 fallback |
| 2 | 3.2 | Pebay catastrophic cancellation | ✅ — float64 + epsilon + 校正 |
| 3 | 5.1 | ProcessPool TA-Lib segfault | ✅ — spawn + per-process import |
| 4 | 2.4 | L2 斷路器足夠？ | ✅ — 48,591 << 100,000 |
| 5 | 5.3 | DuckDB footer scan | ✅ — 粒度 ~1,200 |

**5b 結論**：0 不可行。

### 表 12 — 5c 程式碼引用

| # | 檔案 | 型別 | 判定 |
|---|---|---|---|
| 1 | feature_factory.py | 修改既有 | ✅ |
| 2 | multi_tf_generator.py | 修改既有 | ✅ |
| 3 | preprocessing/ | 修改既有 | ✅ |
| 4 | feature_storage.py | 修改既有 | ✅ |
| 5 | column_group.py | 新建 | ✅ |
| 6 | column_group_registry.py | 新建 | ✅ |
| 7 | numba_rolling.py | 新建 | ✅ |
| 8 | arrow_ipc_utils.py | 新建 | ✅ |
| 9 | duckdb_reader.py | 新建 | ✅ |
| 10 | generate_golden_output.py | 新建 | ✅ |
| 11 | validate_cgsa_ab.py | 新建 | ✅ |
| 12 | factories.py | 修改既有 | ✅ |
| 13 | config_manager.py | 修改既有 | ✅ |
| 14 | feature_extractor.py | 修改既有 | ✅ |

**5c 結論**：14 引用全部合理。

### 表 13 — 5d 規則合規

| # | 規則 | 判定 |
|---|---|---|
| 1 | Rule 1: momentum/ 不 import api/ | ✅ |
| 2 | Rule 2: 跨 Domain Protocol | ✅ |
| 3 | Rule 3: services 用 factories | ✅ |
| 4 | Rule 4: services 不互相 import | ✅ |
| 5 | Rule 5: config 單一來源 | ✅ |
| 6 | Rule 6: 測試獨立 | ✅ |
| 7 | Rule 7: DTO 不跨域 | ✅ |
| 8 | C1~C6 per-Phase 驗證 | ✅ |
| 9 | §0.2 Logging | ✅ |
| 10 | §0.12 Fallback | ✅ |

**5d 結論**：全部合規。

### 表 14 — 5e 資料流銜接

| # | 上游 | 下游 | 中間格式 | 判定 |
|---|---|---|---|---|
| 1 | Task 0.3 → Task 2.12 | Golden Parquet | ✅ |
| 2 | Task 2.3 → Task 2.4 | .npy memmap | ✅ |
| 3 | Task 2.4 → Task 2.7 | ColumnGroup Registry | ✅ |
| 4 | Task 2.8 → Task 5.3 | Parquet + manifest | ✅ |
| 5 | Task 3.1~3.4 → Task 3.5 | numpy array | ✅ |
| 6 | Phase 2 → Task 5.1 | ProcessPool spawn | ✅ |

**5e 結論**：資料流全部正確。

### 表 15 — 5f Test-Task 對齊

| # | Test | Task | 判定 |
|---|---|---|---|
| 1 | T0.1 → Task 0.1 | ✅ |
| 2 | T0.3 → Task 0.3 | ✅ |
| 3 | T1.3 → Task 1.2 | ✅ |
| 4 | T2.11 → Tasks 2.3~2.12 | ✅ |
| 5 | T3.7 → Task 3.2 | ✅ |
| 6 | T3.12 → Tasks 3.5+3.6 | ✅ |
| 7 | T4.B1 → Task 4.4 | ✅ |
| 8 | T5.1 → Task 5.1 | ✅ |
| 9 | T5.3 → Task 5.3 | ✅ |

**5f 結論**：抽樣 9/98 全部對齊。

### 表 16 — 5g 驗證條件可執行性

| # | Test | 條件 | 可自動化? |
|---|---|---|---|
| 1 | T0.1 | `"L2" in log and "elapsed" in log` | ✅ pytest |
| 2 | T1.6 | `np.allclose(atol=1e-10)` | ✅ pytest |
| 3 | T2.11 | `sorted(new_cols) == sorted(golden_cols)` | ✅ pytest |
| 4 | T3.7 | `np.allclose(atol=1e-4)` | ✅ pytest |
| 5 | T3.P1 | `elapsed < baseline * 0.5` | ✅ pytest |
| 6 | T4.B1 | `polars_nan == pandas_nan` | ✅ pytest |
| 7 | T5.1 | `np.allclose(per_layer_atol)` | ✅ pytest |

**5g 結論**：全部可自動化。

### 表 17 — 5h 副作用回歸

| # | Task | 副作用 | 緩解 | 判定 |
|---|---|---|---|---|
| 1 | 1.3 | 對齊行為改變 | fallback + T1.3 | ✅ |
| 2 | 2.3 | .npy 磁碟空間 | R8 清理 + T2.B7 | ✅ |
| 3 | 2.5 | global concat 移除 | materialize @deprecated + T2.11 | ✅ |
| 4 | 3.5 | L3 引擎替換 | Task 3.6 等價測試 | ✅ |
| 5 | 4.1~4.4 | NaN/null 差異 | R5 + T4.B1 | ✅ |
| 6 | 5.1 | Registry 污染 | T5.2 + per-process | ✅ |

**5h 結論**：全部有緩解。

### 表 18 — 5i 全棧整合

| 判定 | 說明 |
|---|---|
| ⊘ 自動 PASS | 純後端（momentum/）效能優化 SPEC，不涉及 frontend/API/WebSocket。全棧整合不適用。 |

---

## 最終結論

| 指標 | 值 |
|---|---|
| 驗證輪次 | Round 3 |
| 總 FAIL 數 | **0** |
| 總 PASS 數 | 21 Tables 全部 PASS |
| 修正行為 | 無需修正（Round 2 修正已生效） |
| TODO 狀態 | **✅ 通過驗證 — 可進入實作階段** |

### 歷史修正記錄

| 輪次 | 發現 FAIL | 修正內容 | 最終狀態 |
|---|---|---|---|
| V1 (Round 1) | 8 | Tasks 4.1-4.4 展開、Tasks 5.2/5.3 展開、新增 Batch 明細表 + 快速執行參考 | 0 FAIL |
| V2 (Round 2) | 3 | Tasks 2.6/3.6/5.1 深度不足修正 | 0 FAIL |
| **V3 (Round 3)** | **0** | **無需修正** | **0 FAIL** |

---

*報告產生時間：2026-04-16 | 驗證模板：Stage 3 五輪自主驗證（21 Tables）*
