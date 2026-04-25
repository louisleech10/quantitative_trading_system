# Stage 3 驗證報告 — TODO 自主多輪驗證（第 2 輪）

> **驗證對象**: `docs/FEATURE_FACTORY_OPTIMIZATION_TODO.md` V1 (Post-Fix)  
> **SPEC 來源**: `docs/FEATURE_FACTORY_OPTIMIZATION_SPEC.md` V2 🔒 FROZEN 2026-04-16  
> **模板**: `templates/TODO_GENERATION_PROMPT.md` Stage 3  
> **驗證日期**: 2026-04-16  
> **驗證輪次**: 第 2 次（前次修補後重新全量驗證）

---

## Pass 1：追溯完整性（Tables 1-7）

### 表 1：SPEC Task 覆蓋率

| # | SPEC Task | SPEC § | TODO 中存在? | TODO 位置 | 備註 |
|---|-----------|--------|-------------|----------|------|
| 1 | Task 0.1 | §2.1 | ✅ | Phase 0 | — |
| 2 | Task 0.2 | §2.1 | ✅ | Phase 0 | — |
| 3 | Task 0.3 | §2.1 | ✅ | Phase 0 | — |
| 4 | Task 1.1 | §3.1 | ✅ | Phase 1 | — |
| 5 | Task 1.2 | §3.2 | ✅ | Phase 1 | — |
| 6 | Task 1.3 | §3.3 | ✅ | Phase 1 | — |
| 7 | Task 1.4 | §3.4 | ✅ | Phase 1 | — |
| 8 | Task 1.5 | §3.5 | ✅ | Phase 1 (DEFERRED→5) | 標記 DEFERRED |
| 9 | Task 2.1 | §4.1 | ✅ | Phase 2 | — |
| 10 | Task 2.2 | §4.1.3 | ✅ | Phase 2 | — |
| 11 | Task 2.3 | §4.6 | ✅ | Phase 2 | — |
| 12 | Task 2.4 | §4.2 | ✅ | Phase 2 | — |
| 13 | Task 2.5 | §4.6 | ✅ | Phase 2 | — |
| 14 | Task 2.6 | §4.6 | ✅ | Phase 2 | — |
| 15 | Task 2.7 | §4.3 | ✅ | Phase 2 | — |
| 16 | Task 2.8 | §4.4 | ✅ | Phase 2 | — |
| 17 | Task 2.9 | §4.4 | ✅ | Phase 2 | — |
| 18 | Task 2.10 | §4.5.2 | ✅ | Phase 2 | — |
| 19 | Task 2.11 | §4.5.2, §4.13 | ✅ | Phase 2 | — |
| 20 | Task 2.12 | §4.5, §4.12 | ✅ | Phase 2 | — |
| 21 | Task 3.1 | §5.1, §5.2.1 | ✅ | Phase 3 | — |
| 22 | Task 3.2 | §5.1, §5.2.4 | ✅ | Phase 3 | — |
| 23 | Task 3.3 | §5.1, §5.2.3 | ✅ | Phase 3 | — |
| 24 | Task 3.4 | §5.1 | ✅ | Phase 3 | — |
| 25 | Task 3.5 | §5.1 | ✅ | Phase 3 | — |
| 26 | Task 3.6 | §5.1 | ✅ | Phase 3 | — |
| 27 | Task 4.1 | §6.1 | ✅ | Phase 4 | — |
| 28 | Task 4.2 | §6.1 | ✅ | Phase 4 | — |
| 29 | Task 4.3 | §6.1 | ✅ | Phase 4 | — |
| 30 | Task 4.4 | §6.1 | ✅ | Phase 4 | — |
| 31 | Task 5.1 | §7.1 | ✅ | Phase 5 | — |
| 32 | Task 5.2 | §7.1 | ✅ | Phase 5 | — |
| 33 | Task 5.3 | §7.1 | ✅ | Phase 5 | — |
| K | Task 5.4 | §7.1 | ⊘ 未列為獨立 Task | — | 為 benchmark 目標（「100 sym × 4 TF × 8 workers < 90 min」），已融入效能預估表 + Phase 5→Done Gate。合理 merge，非遺漏。 |
| **合計** | **33 + 1K** | | **33 ✅ / 1 ⊘ 合理** | | **PASS** |

---

### 表 2：SPEC Test 覆蓋率

| # | Phase | Test ID 範圍 | SPEC 數量 | TODO 數量 | 一致? |
|---|-------|------------|----------|----------|------|
| 1 | Phase 0 | T0.1~T0.4 | 4 | 4 | ✅ |
| 2 | Phase 1 核心 | T1.1~T1.10 | 10 | 10 | ✅ |
| 3 | Phase 1 邊界 | T1.B1~T1.B15 | 15 | 15 | ✅ |
| 4 | Phase 1 效能 | T1.P1~T1.P3 | 3 | 3 | ✅ |
| 5 | Phase 2 單元 | T2.1~T2.10 | 10 | 10 | ✅ |
| 6 | Phase 2 整合 | T2.11~T2.17 | 7 | 7 | ✅ |
| 7 | Phase 2 邊界 | T2.B1~T2.B9 | 9 | 9 | ✅ |
| 8 | Phase 3 核心 | T3.1~T3.12 | 12 | 12 | ✅ |
| 9 | Phase 3 邊界 | T3.B1~T3.B13 | 13 | 13 | ✅ |
| 10 | Phase 3 效能 | T3.P1~T3.P2 | 2 | 2 | ✅ |
| 11 | Phase 4 核心 | T4.1~T4.4 | 4 | 4 | ✅ |
| 12 | Phase 4 邊界 | T4.B1~T4.B3 | 3 | 3 | ✅ |
| 13 | Phase 5 核心 | T5.1~T5.3 | 3 | 3 | ✅ |
| 14 | Phase 5 邊界 | T5.B1~T5.B3 | 3 | 3 | ✅ |
| **合計** | | | **98** | **98** | **PASS** |

---

### 表 3：SPEC Risk 覆蓋率

| # | Risk ID | SPEC 描述 | TODO 風險緩解總表 | 一致? |
|---|---------|----------|-----------------|------|
| 1 | R1 | searchsorted ms/ns off-by-one | ✅ T1.2, T1.B14 | ✅ |
| 2 | R2 | self-align skip 後 index 不一致 | ✅ T1.B11 | ✅ |
| 3 | R3 | per-group 過多小檔案 | ✅ 粒度 ~1,200 | ✅ |
| 4 | R4 | Numba skew/kurt 數值不穩定 | ✅ float64+校正 | ✅ |
| 5 | R5 | Polars null ≠ NaN | ✅ fill_null | ✅ |
| 6 | R6 | Multi-TF TA-Lib GIL 競爭 | ✅ ProcessPool+spawn | ✅ |
| 7 | R7 | pipeline 跑不完→無 golden | ✅ 分層 fallback | ✅ |
| 8 | R8 | .npy 中介檔案暴漲 | ✅ cleanup+finally | ✅ |
| 9 | R9 | L2 新 operator 打破 per-group | ✅ 文件記錄 | ✅ |
| 10 | R10 | Parquet metadata 極大 | ✅ per-group | ✅ |
| 11 | R11 | TA-Lib 非 thread-safe | ✅ ProcessPool | ✅ |
| 12 | R12 | Numba JIT cold start | ✅ cache=True | ✅ |
| 13 | R13 | int64 ms→ns 溢出 | ✅ T1.B15 | ✅ |
| 14 | R14 | A/B 同時→RAM 翻倍 | ✅ 不同時在 RAM | ✅ |
| 15 | R15 | .npy 33,600+ 檔案爆炸 | ✅ 粒度 ~1,200 | ✅ |
| 16 | R16 | Numba ARM64/macOS 相容 | ✅ 版本釘選 | ✅ |
| 17 | R17 | skew/kurt zero-variance | ✅ epsilon guard | ✅ |
| 18 | R18 | L2 O(N²) 組合爆炸 | ✅ 斷路器 | ✅ |
| 19 | R19 | DuckDB footer scan overhead | ✅ 粒度 ~1,200 | ✅ |
| 20 | R20 | Phase 5 磁碟 I/O 未建模 | ✅ 2-sym pilot | ✅ |
| 21 | R21 | L1 ThreadPool+TA-Lib | ✅ 預設關閉 | ✅ |
| 22 | R22 | _find_column fuzzy matching | ✅ 顯式引用 | ✅ |
| 23 | R23 | variance_filter 非決定性 | ✅ 固定閾值 | ✅ |
| 24 | R24 | _combine_layers 未被覆蓋 | ✅ Task 2.5 同改 | ✅ |
| 25 | R25 | Polars 版本鎖定 | ✅ >=0.20,<0.21 | ✅ |
| **合計** | **25/25** | | | **PASS** |

---

### 表 4：Phase Gate 覆蓋率

| # | SPEC Gate | SPEC § | TODO Gate | 條件一致? |
|---|-----------|--------|----------|----------|
| 1 | Phase 0→1 | §8.1 | ✅ Phase 0→1 Gate | ✅ Golden+L2 log |
| 2 | Phase 1→2 | §8.2 | ✅ Phase 1→2 Gate | ✅ T1.3/T1.6/T1.7+B2+D<50s |
| 3 | Phase 2→3 | §8.3 | ✅ Phase 2→3 Gate | ✅ T2.11/T2.13+無concat |
| 4 | Phase 3→4 | §8.4 | ✅ Phase 3→4 Gate | ✅ T3.12+re-profile+skip條件 |
| 5 | Phase 4/5→Done | §8.5 | ✅ Phase 5→Done Gate | ✅ C1~C6+<20min+RSS<2GB |
| **合計** | **5/5** | | | **PASS** |

---

### 表 5：硬約束覆蓋率

| # | SPEC 約束 | TODO §0.2 | atol 一致? | 驗證方式一致? |
|---|----------|----------|----------|------------|
| 1 | C1 數值等價 (per-layer atol) | ✅ C1 含 per-layer map | ✅ L1:1e-7, L3 skew:1e-4 等 | ✅ Golden test suite |
| 2 | C2 不減特徵 (453,953) | ✅ C2 | — | ✅ new==golden |
| 3 | C3 不改 column name + 排序 | ✅ C3 | — | ✅ sorted+order test |
| 4 | C4 RAM ≤ 6 GB | ✅ C4 | — | ✅ psutil.rss |
| 5 | C5 無 future leakage | ✅ C5 | — | ✅ validate_no_future_leak |
| 6 | C6 NaN 語義一致 | ✅ C6 | — | ✅ per-column NaN mask |
| **合計** | **6/6** | | | **PASS** |

---

### 表 6：§0 規範覆蓋率

| # | SPEC §0 子節 | TODO 覆蓋 | 覆蓋方式 | 判定 |
|---|-------------|----------|---------|------|
| 1 | §0.1 解耦 7 規則 | ✅ §0.1.1 | 完整 7 規則表 | PASS |
| 2 | §0.2 Logging 規範 | ✅ §0.1.3 | 4 條規範 | PASS |
| 3 | §0.3 Ultra Think | ✅ §0.1.2 | 3-step 描述 | PASS |
| 4 | §0.4 Error Handling | ✅ §0.1.4 | FailureType Enum | PASS |
| 5 | §0.5 Type Hints | ✅ §0.1.5 | 含在命名規範中 | PASS |
| 6 | §0.6 命名規範 | ✅ §0.1.5 | 完整規範 | PASS |
| 7 | §0.7 測試規範 | ✅ §0.4 | Pre-Commit 涵蓋 | PASS |
| 8 | §0.8 效能慣例 | ✅ §0.4 | Pre-Commit 涵蓋 | PASS |
| 9 | §0.9 Factory 注入 | ✅ §0.1.6 | 明確規則 | PASS |
| 10 | §0.10 Git Branch | ✅ §0.1.7 | 含 branch+commit 規範 | PASS |
| 11 | §0.11 Data Truth | ✅ §0.4 | Pre-Commit 涵蓋 | PASS |
| 12 | §0.12 向後相容 | ✅ §0.5 | 4 Phase fallback 表 | PASS |
| 13 | §0.13 Pre-Commit | ✅ §0.4 | 12 項清單 | PASS |
| **合計** | **13/13** | | | **PASS（0 缺失）** |

---

### 表 7：環境變數 / Feature Flag 覆蓋率

| # | SPEC 環境變數 | SPEC § | TODO 索引 F 節 | TODO §0.5 | 一致? |
|---|-------------|--------|--------------|----------|------|
| 1 | FFACT_USE_SEARCHSORTED | §0.12, §3.3 | ✅ | ✅ Phase 1 | ✅ |
| 2 | FFACT_USE_CGSA | §0.12, §4.5 | ✅ | ✅ Phase 2 | ✅ |
| 3 | FFACT_USE_NUMBA_ROLLING | §0.12, §5.1 | ✅ | ✅ Phase 3 | ✅ |
| 4 | FFACT_USE_POLARS | §0.12 | ✅ | ✅ Phase 4 | ✅ |
| 5 | FFACT_LAYER1_PARALLEL | §3.5 | ✅ | — (Phase 5) | ✅ |
| 6 | FFACT_L3_STREAMING | §5.0 | ✅ | — | ✅ |
| 7 | FFACT_L65_CHUNK_SIZE | §4.14 | ✅ | — | ✅ |
| 8 | GOLDEN_CONFIG_OVERRIDE | §2.1 | ✅ | — | ✅ |
| 9 | MAX_L2_ESTIMATED_COLS | §4.2.1 | ✅ | — | ✅ |
| **合計** | **9/9** | | | | **PASS** |

---

### Pass 1 總結

| 維度 | SPEC 數量 | TODO 數量 | 覆蓋率 | 判定 |
|------|----------|----------|--------|------|
| Task | 33 (+1 benchmark) | 33 | 100% | ✅ PASS |
| Test | 98 | 98 | 100% | ✅ PASS |
| Risk | 25 | 25 | 100% | ✅ PASS |
| Phase Gate | 5 | 5 | 100% | ✅ PASS |
| 硬約束 | 6 | 6 | 100% | ✅ PASS |
| §0 規範 | 13 | 13 | 100% | ✅ PASS |
| Env Var | 9 | 9 | 100% | ✅ PASS |

**Pass 1 結論：7/7 全 PASS，無遺漏。**

---

## Pass 2：結構完整性 + 深度全掃描

### 表 8：模板段落完整性（13 段）

| # | 段落名稱 | 模板要求 | TODO 中存在? | 判定 |
|---|---------|---------|-------------|------|
| 1 | SPEC 正規化報告（交付物 #0.5） | 6 結構要素表 | ✅ 6/6 | PASS |
| 2 | SPEC 索引摘要（交付物 #1） | A~G 子表 | ✅ A~G 完整 | PASS |
| 3 | 矛盾/過時檢測（交付物 #1.5） | 矛盾表+過時表 | ✅ 3 矛盾+1 過時 | PASS |
| 4 | §0.1 開發規則 | 規則列表 | ✅ §0.1.1~§0.1.7 | PASS |
| 5 | §0.2 硬約束表 | C1~CN + atol | ✅ C1~C6 + per-layer atol | PASS |
| 6 | §0.3 驗收流程 | 7 步流程 | ✅ 7 步+回退策略 | PASS |
| 7 | §0.4 Pre-Commit 檢查清單 | □ checklist | ✅ 12 項 | PASS |
| 8 | §0.5 Fallback | Phase-env var 表 | ✅ 4 Phase 表 | PASS |
| 9 | §0.6 三層 Baseline | Tier 1/2/3 表 | ✅ 3 層定義 | PASS |
| 10 | 執行策略（拓撲+Batch+快速參考）| 拓撲圖+Batch 明細+Prompt | ✅ 全部存在 | PASS |
| 11 | Phase 0~5 內容 | 每 Phase: 目標/風險/Branch + Tasks + 測試 + Gate | ✅ 6 Phases | PASS |
| 12 | 風險緩解總表 | Risk-Phase-緩解-Test 表 | ✅ 25 列 | PASS |
| 13 | 附錄（測試檔案/效能預估/AI Agent） | 3 節 | ✅ 全部存在 | PASS |
| **合計** | **13/13** | | | **PASS** |

---

### 表 9：Task 欄位深度全掃描（§2.2 反敷衍機制）

> 模板要求：實作要點≥3 | 偽碼/步驟≥邏輯流 | 修改到函式名 | 不可做≥1 | Edge Case≥2 | 驗證具體可量化

| Task | 實作≥3 | 偽碼/步驟 | 函式名 | 不可做≥1 | Edge≥2 | 驗證具體 | 判定 |
|------|--------|----------|--------|---------|--------|---------|------|
| 0.1 | 3 ✅ | ✅ | ✅ `_layer2_derived_features()` | 3 ✅ | 2 ✅ | ✅ log 出現 | PASS |
| 0.2 | 4 ✅ | ✅ | ✅ `concat_with_memmap()` | 3 ✅ | 2 ✅ | ✅ heartbeat 出現 | PASS |
| 0.3 | 5 ✅ | ✅ | ⊘ 新建 script | 3 ✅ | 2 ✅ | ✅ parquet 存在 | PASS |
| 1.1 | 5 ✅ | ✅ | ✅ `build_asof_index_map()` | 3 ✅ | 4 ✅ | ✅ 具體數值 | PASS |
| 1.2 | 5 ✅ | ✅ | ✅ `_searchsorted_align()` | 2 ✅ | 2 ✅ | ✅ atol=1e-6 | PASS |
| 1.3 | 4 ✅ | ✅ | ✅ `align_to_primary()` | 2 ✅ | 2 ✅ | ✅ T1.10 | PASS |
| 1.4 | 4 ✅ | ✅ | ✅ `generate_multi_tf()` | 2 ✅ | 3 ✅ | ✅ atol=1e-7 | PASS |
| 1.5 | — | — | — | — | — | — | ⊘ DEFERRED |
| 2.1 | 5 ✅ | ✅ | ⊘ 新建 | 2 ✅ | 2 ✅ | ✅ frozen | PASS |
| 2.2 | 6 ✅ | ✅ | ⊘ 新建 | 3 ✅ | 3 ✅ | ✅ roundtrip | PASS |
| 2.3 | 4 ✅ | ✅ 步驟 | ✅ `_layer1_atomic_indicators()` | 2 ✅ | 2 ✅ | ✅ concat== | PASS |
| 2.4 | 4 ✅ | ✅ | ✅ `compute_category()` | 2 ✅ | 2 ✅ | ✅ T2.16 | PASS |
| 2.5 | 3 ✅ | ✅ 步驟 | ✅ 2 檔案 `_combine_layers()` | 2 ✅ | 2 ✅ | ✅ T2.12 | PASS |
| **2.6** | **2 ❌** | ✅ | ✅ `_apply_timeframe_tag()` | 1 ✅ | **1 ❌** | ✅ T2.11 | **FAIL** |
| 2.7 | 3 ✅ | ✅ | ✅ `FeaturePreprocessor` | 2 ✅ | 2 ✅ | ✅ atol | PASS |
| 2.8 | 4 ✅ | ✅ 步驟 | ✅ `FeatureStorage` | 2 ✅ | 2 ✅ | ✅ DuckDB | PASS |
| 2.9 | 4 ✅ | ✅ 步驟 | ✅ `_write_manifest()` | 1 ✅ | 2 ✅ | ✅ json.load | PASS |
| 2.10 | 3 ✅ | ✅ 步驟 | ✅ `_layer7_validate_and_persist()` | 1 ✅ | 2 ✅ | ✅ 一致 | PASS |
| 2.11 | 4 ✅ | ✅ | ✅ `materialize_wide_df()` | 1 ✅ | 2 ✅ | ✅ T2.11 | PASS |
| 2.12 | 5 ✅ | ✅ 步驟 | ⊘ 新建 script | 2 ✅ | 2 ✅ | ✅ per-layer | PASS |
| 3.1 | 7 ✅ | ✅ | ⊘ 新建 `numba_rolling.py` | 3 ✅ | 3 ✅ | ✅ atol=1e-6 | PASS |
| 3.2 | 4 ✅ | ✅ | ✅ `rolling_skew_kurt()` | 2 ✅ | 3 ✅ | ✅ atol=1e-4 | PASS |
| 3.3 | 4 ✅ | ✅ | ✅ `rolling_rank()` | 2 ✅ | 3 ✅ | ✅ atol=1e-6 | PASS |
| 3.4 | 3 ✅ | ✅ 步驟 | ✅ `rolling_slope()` | 1 ✅ | 2 ✅ | ✅ atol=1e-5 | PASS |
| 3.5 | 5 ✅ | ✅ 步驟 | ✅ `RollingAggregator.compute_all()` | 2 ✅ | 2 ✅ | ✅ T3.12 | PASS |
| **3.6** | **1 ❌** | **❌** | ⊘ 新建 test file | **0 ❌** | **0 ❌** | ✅ all T3 PASS | **FAIL** |
| 4.1 | 3 ✅ | ✅ | ✅ `_layer1_atomic_indicators()` | 2 ✅ | 2 ✅ | ✅ atol=1e-6 | PASS |
| 4.2 | 3 ✅ | ✅ | ✅ `compute_derived_features()` | 2 ✅ | 2 ✅ | ✅ atol=1e-6 | PASS |
| 4.3 | 4 ✅ | ✅ | ✅ `preprocess()` | 2 ✅ | 2 ✅ | ✅ atol=1e-5 | PASS |
| 4.4 | 3 ✅ | ✅ | ✅ 轉換點 | 2 ✅ | 2 ✅ | ✅ NaN count | PASS |
| **5.1** | 5 ✅ | **❌** | **❌ 無修改檔案表** | 2 ✅ | **0 ❌** | **❌ 無具體條件** | **FAIL** |
| 5.2 | 3 ✅ | ✅ | ✅ `persist_column_group()` | 2 ✅ | 2 ✅ | ✅ T5.1 間接 | PASS |
| 5.3 | 3 ✅ | ✅ | ✅ 新建 `duckdb_reader.py` | 2 ✅ | 2 ✅ | ✅ DuckDB count | PASS |
| **合計** | | | | | | | **PASS: 30 / FAIL: 3** |

**FAIL 項目**：
1. **Task 2.6**: 實作要點 2 < 3；Edge Case 1 < 2
2. **Task 3.6**: 實作要點 1 < 3；無偽碼；Edge Case 0 < 2（測試包裝 Task）
3. **Task 5.1**: 無偽碼；無修改檔案表；無驗證條件；Edge Case 0 < 2

---

## Pass 3：索引回驗

從交付物 #1 的 SPEC 位置引用，抽樣回查 SPEC 原文：

### 索引回驗報告

| # | SPEC ID | 索引記錄的位置 | 重新查找結果 | 判定 |
|---|---------|-------------|-----------|------|
| 1 | Task 0.1 | §2.1 | ✅ 找到：SPEC §2.1「Task 0.1: L2 前後計時 log」 | PASS |
| 2 | Task 1.1 | §3.1 | ✅ 找到：SPEC §3.1「Task 1.1: 實作 build_asof_index_map()」 | PASS |
| 3 | Task 2.1 | §4.1 | ✅ 找到：SPEC §4.1.1 ColumnGroup dataclass 定義 | PASS |
| 4 | Task 2.6 | §4.6 | ✅ 找到：SPEC §4.6「column tagging…group_id」描述 | PASS |
| 5 | Task 3.2 | §5.1, §5.2.4 | ✅ 找到：SPEC §5.2.4 Pebay online skew/kurt | PASS |
| 6 | Task 4.1 | §6.1 | ✅ 找到：SPEC §6 Phase 4 Polars 描述 | PASS |
| 7 | Task 5.3 | §7.1 | ✅ 找到：SPEC §7.1「DuckDB 讀取 Parquet」 | PASS |
| 8 | C1 atol | §1.1 | ✅ 找到：SPEC §1.1 C1 Per-Layer Tolerance Map | PASS |
| 9 | R15 | §10 | ✅ 找到：SPEC §10 R15「.npy 中介檔案爆炸」 | PASS |
| 10 | Gate 3→4 | §8.4 | ✅ 找到：SPEC §8.4「L2+L6.5 > 30%」skip 條件 | PASS |
| **合計** | **10/10** | | | **PASS** |

---

## Pass 4：一致性總檢（數字閉環）

| # | 檢查項 | 來源 A | 來源 B | 一致? |
|---|--------|-------|-------|------|
| 1 | Task 總數 | 索引摘要 A: 33 | 表 1 SPEC: 33 | ✅ |
| 2 | Test 總數 | 索引摘要 B: 98 | 表 2 SPEC: 98 | ✅ |
| 3 | Risk 總數 | 索引摘要 C: 25 | 表 3 SPEC: 25 | ✅ |
| 4 | Gate 總數 | 索引摘要 D: 5 | 表 4 SPEC: 5 | ✅ |
| 5 | 硬約束總數 | 索引摘要 E: 6 | 表 5 SPEC: 6 | ✅ |
| 6 | §0 規範覆蓋 | 表 6 缺失數: 0 | 13/13 已覆蓋 | ✅ |
| 7 | Pass 2A 結構 | 表 8 FAIL: 0 | 13/13 PASS | ✅ |
| 8 | Pass 2B 深度 | 表 9 FAIL: 3 | — | ⚠️ 待修補 |
| 9 | Pass 3 回驗 | FAIL 數: 0 | 10/10 PASS | ✅ |
| 10 | 追溯缺失 | 表 1 K=1 (Task 5.4) | benchmark target, 合理 merge | ✅ |
| 11 | 執行策略覆蓋 | Batch 表 Task 合計: 33 | TODO Task 總數: 33 | ✅ |
| 12 | 執行策略 Gate | 每 Batch 轉換有 Gate | Gate 引用 Test ID 正確 | ✅ |
| 13 | SPEC 正規化 | 交付物 #0.5 已輸出 | 6/6 結構存在 | ✅ |
| 14 | §2.3#2 補充標記 | TODO 中 Edge Cases | 各 Task 均有段落 | ✅ |
| 15 | §2.3#6 Phase Checklist | 每 Phase 結尾 | 列出該 Phase 所有 Test ID | ✅ |
| 16 | §2.3#7 矛盾標記 | 交付物 #1.5 矛盾項: 3 | 受影響 Task 有說明 | ✅ |
| 17 | §2.4 Phase 劃分 | TODO Phase 0~5 | 遵循 SPEC Phase 0~5 | ✅ |
| 18 | §2.4 原子化 | 每個 Task | 修改 ≤ 3 檔案 | ✅ |
| 19 | §2.4 測試去重 | 跨 Phase Test ID | 各 Phase 獨立定義 | ✅ |
| 20 | §2.4 條件 Phase | Phase 4 條件性 | 有 skip 路徑說明 | ✅ |

**結論**：20 項中 19 ✅ / 1 ⚠️（Pass 2B 的 3 個 FAIL 待修補後重驗）。

---

## Pass 5：語義正確性審查

### 表 10：Cross-Task 矛盾掃描

| # | Task A | Task B | 共同目標 | 矛盾描述 | 嚴重度 |
|---|--------|--------|---------|---------|--------|
| 1 | Task 2.3 | Task 4.1 | `feature_factory.py` → L1 output | A 輸出 .npy via Registry; B 轉為 Polars | ⊘ 無矛盾（Phase 4 在 2 之後，additive branch） |
| 2 | Task 2.5 | Task 2.6 | `multi_tf_generator.py` | A 改 `_combine_layers`; B 改 `_apply_timeframe_tag` | ⊘ 無矛盾（不同函式） |
| 3 | Task 3.5 | Task 2.7 | L3/L6.5 pipeline | A 改 rolling 實作; B 改 per-group 入口 | ⊘ 無矛盾（Phase 3 在 2 之後，sequential） |
| **合計** | | | | **0 矛盾 = PASS** | |

---

### 表 11：實作可行性審查

| Task | 偽碼邏輯 | API/演算法 | Edge Case 品質 | NaN/空值 | 判定 | 問題 |
|------|---------|----------|--------------|---------|------|------|
| 0.1 | ✅ | ✅ perf_counter | ✅ 空DF+異常 | ✅ | PASS | — |
| 0.2 | ✅ | ✅ psutil fallback | ✅ 小DF+無psutil | N/A | PASS | — |
| 0.3 | ✅ | ✅ 三層 fallback | ✅ OOM降級 | ✅ | PASS | — |
| 1.1 | ✅ | ✅ searchsorted | ✅ 空/未排序/溢出 | ✅ idx<0→-1 | PASS | — |
| 1.2 | ✅ | ✅ fancy index | ✅ 全NaN/寬DF | ✅ nan fill | PASS | — |
| 1.3 | ✅ | ✅ env var | ✅ 無效env val | N/A | PASS | — |
| 1.4 | ✅ | ✅ copy(deep=False) | ✅ index mismatch | ✅ | PASS | — |
| 2.1 | ✅ | ✅ frozen dataclass | ✅ 空tuple/長id | N/A | PASS | — |
| 2.2 | ✅ | ✅ atomic write | ✅ npy遺失/磁碟不足 | N/A | PASS | — |
| 2.3 | ✅ | ✅ per-indicator | ✅ 0 cols/1000+ cols | ✅ | PASS | — |
| 2.4 | ✅ | ✅ 斷路器 | ✅ 無Cross/1 ind | ✅ | PASS | — |
| 2.5 | ✅ | ✅ no-op | ✅ 空層/non-CGSA | N/A | PASS | — |
| 2.6 | ✅ | ✅ no-op | ⚠️ 只1個 | N/A | ⚠️ | Edge不足 |
| 2.7 | ✅ | ✅ per-group | ✅ 全NaN/fracdiff | ✅ | PASS | — |
| 2.8 | ✅ | ✅ Parquet | ✅ 磁碟不足/極大group | N/A | PASS | — |
| 2.9 | ✅ | ✅ json+SHA256 | ✅ 大manifest/non-serial | N/A | PASS | — |
| 2.10 | ✅ | ✅ per-group validate | ✅ inf/高NaN | ✅ | PASS | — |
| 2.11 | ✅ | ✅ concat+deprecated | ✅ 空Registry/OOM | ✅ | PASS | — |
| 2.12 | ✅ | ✅ per-layer atol | ✅ golden不存在/R23 | ✅ | PASS | — |
| 3.1 | ✅ | ✅ Welford+deque | ✅ 全NaN/W=1/極值 | ✅ | PASS | — |
| 3.2 | ✅ | ✅ Pebay+校正 | ✅ 常數/W=233/inf | ✅ epsilon | PASS | — |
| 3.3 | ✅ | ✅ sorted buf+bisect | ✅ 全同/W=1/ties | ✅ | PASS | — |
| 3.4 | ✅ | ✅ running sums | ✅ 常數/遞增 | ✅ | PASS | — |
| 3.5 | ✅ | ✅ env var switch | ✅ 9 windows/variance | ✅ | PASS | — |
| 3.6 | ⚠️ 薄 | ⊘ test wrapper | ⚠️ 0 edge | N/A | ⚠️ | 深度不足 |
| 4.1 | ✅ | ✅ from_numpy | ✅ 空L1/全NaN | ✅ null→NaN | PASS | — |
| 4.2 | ✅ | ✅ with_columns | ✅ 除零/1欄 | ✅ fill_nan | PASS | — |
| 4.3 | ✅ | ✅ Polars expr | ✅ 全NaN/std=0 | ✅ fill_null | PASS | — |
| 4.4 | ✅ | ✅ fill_null+版本 | ✅ flat numeric | ✅ | PASS | — |
| 5.1 | ⚠️ 缺偽碼 | ✅ spawn+pool | ⚠️ 0 edge | ⚠️ | ⚠️ | 深度不足 |
| 5.2 | ✅ | ✅ Arrow IPC | ✅ 刪除/超大 | ✅ | PASS | — |
| 5.3 | ✅ | ✅ DuckDB | ✅ missing/版本 | ✅ | PASS | — |
| **合計** | | | | | **PASS: 30 / ⚠️: 3** | |

> ⚠️ 項均為 Pass 2B 已識別的 FAIL（Task 2.6, 3.6, 5.1），將在修補階段處理。

---

### 表 12：程式碼引用驗證

| # | Task | 引用的路徑/函式 | 確認結果 | 判定 |
|---|------|---------------|---------|------|
| 1 | 0.1 | `feature_factory.py` → `_layer2_derived_features()` | ✅ 既有函式 | PASS |
| 2 | 0.2 | `memmap_utils.py` → `concat_with_memmap()` | ✅ 既有函式 | PASS |
| 3 | 0.3 | `scripts/generate_golden_output.py` | ⊘ 新建 | PASS |
| 4 | 1.1 | `tf_aligner.py` → `build_asof_index_map()` | ⊘ 新建方法 | PASS |
| 5 | 1.2 | `tf_aligner.py` → `_searchsorted_align()` | ⊘ 新建方法 | PASS |
| 6 | 1.3 | `tf_aligner.py` → `align_to_primary()` | ✅ 既有方法 | PASS |
| 7 | 1.4 | `multi_tf_generator.py` → `generate_multi_tf()` | ✅ 既有方法 | PASS |
| 8 | 2.1 | `core/column_group.py` | ⊘ 新建 | PASS |
| 9 | 2.2 | `core/column_group_registry.py` | ⊘ 新建 | PASS |
| 10 | 2.3 | `feature_factory.py` → `_layer1_atomic_indicators()` | ✅ 既有方法 | PASS |
| 11 | 2.4 | `derived_operators.py` → `compute_all()` | ✅ 既有方法 | PASS |
| 12 | 2.5 | `feature_factory.py` + `multi_tf_generator.py` → `_combine_layers()` | ✅ 兩處既有 | PASS |
| 13 | 2.6 | `multi_tf_generator.py` → `_apply_timeframe_tag()` | ✅ 既有方法 | PASS |
| 14 | 2.7 | `feature_preprocessor.py` → `FeaturePreprocessor` | ✅ 既有類別 | PASS |
| 15 | 2.8 | `feature_storage.py` → `FeatureStorage` | ✅ 既有類別 | PASS |
| 16 | 3.1~3.4 | `operators/numba_rolling.py` | ⊘ 新建 | PASS |
| 17 | 3.5 | `rolling_aggregator.py` → `compute_all()` | ✅ 既有方法 | PASS |
| 18 | 3.6 | `tests/test_numba_rolling.py` | ⊘ 新建 test | PASS |
| 19 | 5.2 | `feature_storage.py` → `persist_column_group()` | ⊘ 新增方法 | PASS |
| 20 | 5.3 | `duckdb_reader.py` | ⊘ 新建 | PASS |
| **合計** | | | | **0 FAIL = PASS** |

---

### 表 13：規則合規審查

| Task 群組 | §0.1 相關規則 | §0.1 合規? | §0.2 相關約束 | §0.2 合規? | 違規 |
|----------|------------|----------|------------|----------|------|
| 0.1~0.3 | Logging(§0.1.3), R1(§0.1.1), Data Truth | ✅ | — | — | 0 |
| 1.1~1.4 | R1, Type Hints, 命名 | ✅ | C1, C5, C6 | ✅ | 0 |
| 2.1~2.12 | R1, R3(Factory), 命名 | ✅ | C1~C4, C6 | ✅ | 0 |
| 3.1~3.6 | Logging禁止(@njit內), 效能 | ✅ | C1(per-layer atol) | ✅ | 0 |
| 4.1~4.4 | R1, 效能(Polars expr) | ✅ | C1, C6 | ✅ | 0 |
| 5.1~5.3 | R1, R3, spawn context | ✅ | C1~C6, C4 | ✅ | 0 |
| **合計** | | | | **0 違規 = PASS** | |

---

### 表 14：資料流銜接驗證

| # | 上游 Task | 輸出格式 | 下游 Task | 期望輸入 | 一致? |
|---|----------|---------|----------|---------|------|
| 1 | 0.3 | golden.parquet (DataFrame) | 1.7, 2.11, 2.12, 3.12 | parquet / DataFrame | ✅ |
| 2 | 1.1 | np.ndarray[int64] (index map) | 1.2 | index map | ✅ |
| 3 | 1.2 | pd.DataFrame (aligned) | 1.3 | pd.DataFrame | ✅ |
| 4 | 2.1 | ColumnGroup dataclass | 2.2 | ColumnGroup (register) | ✅ |
| 5 | 2.2 | ColumnGroupRegistry | 2.3~2.12 | Registry 操作 | ✅ |
| 6 | 2.3 | per-indicator .npy | 2.4 | L1 DataFrame (RAM) | ✅ |
| 7 | 2.4 | per-category .npy | 2.7 | Registry groups | ✅ |
| 8 | 2.7 | preprocessed .npy | 2.8 | Registry groups | ✅ |
| 9 | 2.8 | per-group .parquet | 5.3 | Parquet files | ✅ |
| 10 | 2.9 | manifest.json | 5.3, 2.11 | JSON file | ✅ |
| 11 | 3.1 | np.ndarray[float32, (N,6)] | 3.5 | fused output | ✅ |
| 12 | 3.2 | np.ndarray[float32, (N,2)] | 3.5 | skew/kurt output | ✅ |
| 13 | 3.3 | np.ndarray[float32] | 3.5 | rank output | ✅ |
| 14 | 3.4 | np.ndarray[float32] | 3.5 | slope output | ✅ |
| **合計** | | | | | **0 不一致 = PASS** |

---

### 表 15：Test-Task 對齊驗證

| Task | 核心輸出/行為 | 對應 Test | Test 驗證的內容 | 對齊? |
|------|-------------|----------|---------------|------|
| 0.1 | log 輸出 | T0.1 | ✅ 檢查 log 含 "Starting" + "Completed" | ✅ |
| 0.3 | golden parquet | T0.3, T0.4 | ✅ parquet 存在 + columns.json 一致 | ✅ |
| 1.1 | index map | T1.1, T1.2 | ✅ 具體數值驗證 + offset 驗證 | ✅ |
| 1.2 | aligned DataFrame | T1.3 | ✅ atol=1e-6 vs merge_asof | ✅ |
| 1.4 | skip 等價 | T1.6 | ✅ skip vs no-skip atol=1e-7 | ✅ |
| 2.1 | frozen dataclass | T2.1, T2.2 | ✅ 不可修改 + bytes 計算 | ✅ |
| 2.2 | Registry CRUD | T2.3~T2.10 | ✅ 8 個 unit test 覆蓋所有 API | ✅ |
| 2.4 | per-category L2 | T2.16 | ✅ Cross-group 結果等於 legacy | ✅ |
| 2.7 | per-group L6.5 | T2.17 | ✅ rank matches legacy | ✅ |
| 2.11 | wide DataFrame | T2.11 | ✅ CGSA vs legacy numeric eq | ✅ |
| 3.1 | 6 rolling stats | T3.1~T3.6 | ✅ 逐 stat vs pandas | ✅ |
| 3.2 | skew/kurt | T3.7, T3.8 | ✅ atol=1e-4 vs pandas | ✅ |
| 3.3 | rank pct | T3.9 | ✅ atol=1e-6 vs pandas | ✅ |
| 3.5 | 整合 fused | T3.11, T3.12 | ✅ multi-window eq + golden | ✅ |
| 4.1 | Polars DataFrame | T4.1 | ✅ vs pandas atol=1e-6 | ✅ |
| 5.1 | parallel exec | T5.1, T5.2 | ✅ golden一致 + 無crosstalk | ✅ |
| 5.3 | DuckDB query | T5.3 | ✅ count == manifest total | ✅ |
| **合計** | | | | **PASS** |

---

### 表 16：驗證條件可執行性

| # | Task | 驗證條件 | 前置依賴 | 可執行? | 問題 |
|---|------|---------|---------|---------|------|
| 1 | 0.1 | log 中出現 [L2] Starting/Completed | 執行 pipeline | ✅ | — |
| 2 | 0.3 | golden.parquet 存在 | K-line 資料 | ✅ pytest.skip | — |
| 3 | 1.1 | `build_asof_index_map([5,15,25],[0,10,20])==[0,1,2]` | 無依賴 | ✅ | — |
| 4 | 1.3 | T1.10 env var fallback | T1.2 完成 | ✅ | — |
| 5 | 1.7 | 整個 pipeline golden 比對 | Task 0.3 golden | ✅ | — |
| 6 | 2.11 | CGSA vs legacy numeric eq | golden + CGSA pipeline | ✅ | — |
| 7 | 2.12 | per-layer golden 比對 | Task 0.3 golden | ✅ | — |
| 8 | 3.12 | fused vs golden output match | Task 0.3 golden | ✅ | — |
| 9 | 4.1 | `pl_df.to_pandas()` vs legacy | Phase 2 完成 | ✅ Phase 4 在 3 之後 | — |
| 10 | 5.1 | T5.1 multi-symbol golden | Phase 2+ 完成 | ✅ | — |
| **合計** | | | | **0 FAIL = PASS** | |

---

### 表 17：副作用與回歸風險

| # | Task | 修改目標 | 修改類型 | 已知呼叫者 | 風險 |
|---|------|---------|---------|----------|------|
| 1 | 1.3 | `align_to_primary()` | 內部邏輯切換（簽名不變） | `multi_tf_generator.py` | 🟢 低（env var fallback） |
| 2 | 1.4 | `generate_multi_tf()` | 條件跳過（簽名不變） | `feature_factory.py` | 🟢 低 |
| 3 | 2.3 | `_layer1_atomic_indicators()` | 新增 CGSA 分支 | pipeline 內部 | 🟢 低（env var） |
| 4 | 2.4 | `DerivedOperatorEngine` | 新增 `compute_category()` | pipeline 內部 | ⊘ 無（新方法） |
| 5 | 2.5 | `_combine_layers()` ×2 | CGSA no-op 分支 | pipeline 內部 | 🟡 中（env var） |
| 6 | 2.7 | `FeaturePreprocessor` | 新增 per-group 入口 | pipeline 內部 | 🟢 低（env var） |
| 7 | 3.5 | `RollingAggregator.compute_all()` | 新增 Numba 分支 | `feature_factory.py` | 🟡 中（env var） |
| 8 | 4.2 | `compute_derived_features()` | Polars expr 分支 | pipeline 內部 | 🟡 中（Phase 4 條件） |
| **合計** | | | | | **🔴: 0, 🟡: 3, 🟢: 4, ⊘: 1** |

> 所有 🟡 風險均有 env var fallback 保護，且 TODO 中已安排對應 Test（T1.10, T2.12, T3.11）。**PASS**。

---

### 表 18-21：全棧整合完整性

> **⋅ 純後端 SPEC，跳過 5i**
>
> 本 SPEC 為純後端效能優化（`momentum/FeatureEngineering/` 內部重構），不涉及 API 端點變更、前端 UI 變更、或 WebSocket 協議變更。`materialize_wide_df()` 作為向後相容介面保留（Task 2.11），下游模組（IC Analysis, ML Training）的消費方式不變。
>
> **判定：自動 PASS（純單層 SPEC）**

---

### Pass 5 語義正確性總結

| 檢查項 | 結果 | FAIL 數 |
|--------|------|---------|
| 5a Cross-Task 矛盾（表 10） | ✅ | 0 |
| 5b 實作可行性（表 11） | ⚠️ | 3（同 Pass 2B）|
| 5c 程式碼引用（表 12） | ✅ | 0 |
| 5d 規則合規（表 13） | ✅ | 0 |
| 5e 資料流銜接（表 14） | ✅ | 0 |
| 5f Test-Task 對齊（表 15） | ✅ | 0 |
| 5g 驗證條件可執行（表 16） | ✅ | 0 |
| 5h 副作用/回歸（表 17） | ✅ | 0 |
| 5i 全棧整合（表 18-21） | ⋅ 跳過 | 0 |
| **總計** | | **3（均為 Pass 2B 同源）** |

---

## 驗證總結

| Pass | 結果 | FAIL 數 | 說明 |
|------|------|---------|------|
| Pass 1 追溯完整性 | ✅ PASS | 0 | 7/7 維度 100% |
| Pass 2A 結構完整性 | ✅ PASS | 0 | 13/13 段落 |
| Pass 2B 深度掃描 | ⚠️→✅ | **3→0** | Task 2.6, 3.6, 5.1 已修補 |
| Pass 3 索引回驗 | ✅ PASS | 0 | 10/10 抽樣 |
| Pass 4 一致性總檢 | ✅ PASS | 0 | 20/20 ✅ |
| Pass 5 語義正確性 | ✅ PASS | 0 | 8/9 ✅ + 1 跳過 |

### 修補前發現（共 3 個，均為深度不足，已全部修補）

| # | Task | 問題 | 嚴重度 | 修補方式 |
|---|------|------|--------|---------|
| 1 | **Task 2.6** | 實作要點 2<3; Edge Case 1<2 | 🟢 低 | 補 1 條實作要點 + 1 個 Edge Case |
| 2 | **Task 3.6** | 實作要點 1<3; 無偽碼; Edge Case 0<2 | 🟢 低 | 補測試框架步驟 + conftest fixture + 2 Edge Cases |
| 3 | **Task 5.1** | 無偽碼/修改檔案表/驗證條件/Edge Cases | 🟡 中 | 補完整 Task 結構（輸入/輸出/偽碼/修改檔案/驗證/Edge） |

### 與前次驗證對比

| 維度 | V1 報告（修補前） | V2 報告（本次） | 改善 |
|------|-----------------|----------------|------|
| Pass 1 FAIL | 0 | 0 | — |
| Pass 2B FAIL | 8 | 3 → **0**（修補後） | ✅ 修復全部 |
| Pass 2 結構 FAIL | 2（Batch表+快速參考） | 0 | ✅ 修復 2 項 |
| Pass 5 FAIL | 同 Pass 2B | 同 Pass 2B → 0 | ✅ |
| **總 FAIL** | **10** | **0** | **↓ 100%** |

---

## 修補記錄

### 修補 1: Task 2.6（實作要點 + Edge Case）

- **新增實作要點 #3**: env var 入口處 early return 邏輯描述
- **新增 Edge Case #2**: CGSA env var 中途切換的 fallback 行為
- **判定**: 實作 3 ≥ 3 ✅; Edge 2 ≥ 2 ✅ → **PASS**

### 修補 2: Task 3.6（完整測試框架描述）

- **新增**: conftest fixture (`sample_ohlcv`) + 新建檔案表 (2 files)
- **新增**: 3 條實作要點（fixture + parametrize + assert_allclose）
- **新增**: 偽碼（test 結構示意）
- **新增**: 禁止事項（2 條）
- **新增**: 2 個 Edge Cases（空 array + float64 dtype）
- **判定**: 實作 3 ≥ 3 ✅; 偽碼 ✅; Edge 2 ≥ 2 ✅ → **PASS**

### 修補 3: Task 5.1（完整 Task 結構）

- **新增**: 輸入/輸出明確定義
- **新增**: 修改檔案表（3 行，含函式名）
- **新增**: 偽碼（ProcessPoolExecutor + as_completed 完整流程）
- **新增**: 風險緩解（R6, R11, R12, R20 映射）
- **新增**: 驗證條件（8-symbol golden 比對 + crosstalk 檢查）
- **新增**: 2 個 Edge Cases（worker>symbol + OOM graceful degradation）
- **判定**: 全欄位滿足 §2.2 → **PASS**

---

## 修補後 Pass 2B 重驗

| Task | 實作≥3 | 偽碼/步驟 | 函式名 | 不可做≥1 | Edge≥2 | 驗證具體 | 判定 |
|------|--------|----------|--------|---------|--------|---------|------|
| 2.6 | 3 ✅ | ✅ | ✅ `_apply_timeframe_tag()` | 1 ✅ | 2 ✅ | ✅ | **PASS** |
| 3.6 | 3 ✅ | ✅ | ⊘ 新建 | 2 ✅ | 2 ✅ | ✅ pytest=0 | **PASS** |
| 5.1 | 5 ✅ | ✅ | ✅ `run_multi_symbol()` | 3 ✅ | 2 ✅ | ✅ golden+crosstalk | **PASS** |

**Pass 2B 修補後結論: 33/33 Task 全 PASS（含 1 DEFERRED）。**

---

## 最終驗證結論

| Pass | 結果 | FAIL 數 |
|------|------|---------|
| Pass 1 追溯完整性 | ✅ PASS | 0 |
| Pass 2A 結構完整性 | ✅ PASS | 0 |
| Pass 2B 深度掃描 | ✅ PASS（修補後） | 0 |
| Pass 3 索引回驗 | ✅ PASS | 0 |
| Pass 4 一致性總檢 | ✅ PASS | 0 |
| Pass 5 語義正確性 | ✅ PASS | 0 |

**🟢 全 5 Pass × 21 表 = 0 FAIL。TODO 文件已達交付品質。**
