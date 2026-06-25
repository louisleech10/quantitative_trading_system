# Round1 — Composer 2.5 獨立版

**定位**：IC Gatekeeper 從「單機 pandas 全矩陣」升級為「L7-aware 串流管線 + 分階段物化」，在 8GB tier 可穩定處理 430K×20K 單 symbol，並支援 50–100 symbol 批次與 cross-sectional，不弱化 NaN/inf gate、不跨 symbol 污染。

**核心判斷**：現有 `compute_ic_from_l7_raw`（`ic_engine.py:104–266`）已證明「按 parquet group 串流 IC、不 concat 全矩陣」可行；UI 主路徑 `analyze()` 仍走 `_load_features_hdf5` 全量物化（`:1600–1632`），兩條路徑必須收斂。430K 欄在任一 tier 都**不可**走現行 stage0→7 全矩陣語義。

---

## 1. 記憶體 / OOM 架構

### 1.1 尺度與不可行點（實測公式）

| 物件 | 公式 | 430K×20K float32 | pandas 2.5× 開銷 |
|------|------|------------------|------------------|
| 特徵矩陣 | `C×R×4` | **34.4 GB** | **~86 GB** |
| float64 | `C×R×8` | 68.8 GB | ~172 GB |
| Spearman rank 副本 | 同矩陣 float64 | 68.8 GB | — |
| `rolling_ic` 全序列 | `C × T_win × 8`，T_win≈(20000−60)/1≈19940 | **~64 TB** 量級 | 現行 `:268–302` 必炸 |

結論：**rolling IC 全特徵全時間序列不可保留**；IC 標量 + ICIR 聚合可串流；rolling 序列只對 top-N（≤200）事後重算。

### 1.2 目標架構：三層物化

```
[L7 Parquet groups] ──stream──► [Chunk IC Worker] ──append──► [Spill: ic_scores.parquet]
                                        │
                                        ▼
                              [Row mask: event_filter.idx]
                                        │
                    survivors only ──► [Column-project load] ──► stage5b/6/deep
```

**新增 `ICMemoryGovernor`**（建議放 `momentum/Analysis/ic_memory_governor.py`，由 `PerformanceConfig` 驅動）：

| Tier | 可用 RAM（扣 OS+Python 4GB） | `chunk_cols` | `chunk_rows` | 單 chunk 峰值 |
|------|------------------------------|--------------|--------------|---------------|
| 8 GB | ~4 GB | **2,048** | 20,000（全列） | 2048×20000×4×2.5 ≈ **390 MB** |
| 16 GB | ~12 GB | **4,096** | 20,000 | ≈ 780 MB |
| 24 GB | ~18 GB | **8,192** | 20,000 | ≈ 1.56 GB |
| 32 GB | ~26 GB | **12,288** | 20,000 | ≈ 2.34 GB |

預留 40% headroom 給：label 對齊、kline `raw_data`（~20K×6 cols ≈ 1 MB）、grouped 子集副本、FDR 中間表。

**硬規則**：
1. **永不** `pd.concat` 全欄；用 `FeatureReader.load_columns_v2`（`feature_reader.py:115–160`）或 group 級 `pq.read_table(columns=…)`。
2. **永不**在 `_ic_cache`（`ic_filter_orchestrator.py:1300–1311`）存全量 `features_df`；改存 `manifest_ref` + `row_mask` + spill 路徑。
3. Rolling 窗：串流階段只累積 **Welford 統計**（IC mean/std/hit_rate），不存 `window_*` list；`report.top_n_features`（預設 30，`ic_config_schema.py:144`）通過後再對 top-N 重算完整 rolling 序列。

### 1.3 Stage0 改造：Manifest-First Ingestion

**取代** `_load_features_hdf5` 全量 `features[:]`（`:1612`）：

```python
# 新語義（偽代碼）
row_index = reader.load_row_index_v2(symbol, tf, config_hash)  # feature_reader.py:162
column_manifest = reader.list_columns_v2(...)  # 只讀名稱+group，不讀值
metadata = load_meta_json(meta_path)  # 或 manifest sidecar
nan_gate = per_group_nan_ratio_scan(groups)  # 逐 group 算 col mean isna，不物化
```

- **HDF5 legacy 路徑**：僅 `foundation` tier + `C×R×dtype ≤ budget` 時允許全載；否則 **fail-closed** 要求 materialize 到 L7 V2（與 run-selector `config_hash` 對齊）。
- **NaN gate**（現行 `:1348–1350` 全矩陣 `isna().mean()`）：改為逐 group `nanmean` 累積，閾值 0.9 不變。

### 1.4 Spill / Resume 契約

每個 analyze task 寫入  
`data_cache/ic_runs/{task_id}/`（**不 commit**）：

| 檔案 | 內容 | Resume 用途 |
|------|------|-------------|
| `checkpoint.json` | stage、completed_groups、config_hash、fingerprint | 重啟續跑 |
| `ic_scores.parquet` | feature, ic, ic_mean, ic_std, icir, … | stage5 輸入 |
| `row_mask.npz` | event filter 後 boolean index | 對齊 |
| `passed_features.json` | stage5 輸出 | stage6 輸入 |

`data_fingerprint` 沿用 `compute_ic_from_l7_raw` 的 `_build_data_fingerprint`（`:188–195`）；hash 不符 → 拒絕 resume（防 stale cache）。

### 1.5 多 Symbol（50–100）

- **單 symbol 分析**：每 symbol 獨立 `task_id` 子目錄；`config_hash` + `symbol` 隔離 key（準則 2、3）。
- **Cross-sectional**：不物化 `(T×N_sym)×C`；改 **long panel 串流**——每 timestamp 只載 `N_sym × C_survivor` 切片（C_survivor 先經 per-symbol IC 粗篩至 ≤500）。
- **批次調度**：外層 `ICBatchOrchestrator` 限制 concurrent symbols = `floor(usable_ram / per_symbol_budget)`；8GB tier 預設 **1 symbol 並行**。

---

## 2. 逐 Stage / 模組改造

### Stage 0 — Ingestion（`ic_filter_orchestrator.py:986–1014`）

| 現狀 | 改造 |
|------|------|
| HDF5 全載 `:1612` | V2 manifest-first；HDF5 gated |
| 全矩陣 NaN 剔除 | 逐 group 統計 |
| metadata 全欄校驗 `:1337–1346` | 改抽樣 + manifest 完整性檢查；缺 meta 的欄 **fail-closed**（不 silent skip） |

**可串流**：✅ 100%  
**需全矩陣**：❌ 無

### Stage 1 — Preprocessing（`:1016–1019`, `data_preprocessor.py:22`）

| 現狀 | 改造 |
|------|------|
| `features_df.copy()` + 全欄 winsorize | **兩遍掃描**：Pass-1 逐 chunk 估 global p1/p99；Pass-2 逐 chunk clip；或 **直接消費 L7 `processed` artifact**（FF 已做則跳過，byte-faithful 驗證） |
| 標準化 | 同兩遍；或延後到 stage5b 只對 passed_features |

**可串流**：✅（兩遍）  
**需全矩陣**：❌

### Stage 2 — Label（`:1021–1055`）

- 維持單列 `label_series`（20K×8B ≈ 160 KB）。
- kline 讀取：只保留 `close` + timestamp 欄；**禁止**把完整 kline 掛在 cache。
- **PIT**：label 必須 `shift(-horizon)`（`ic_engine.py:987–994`）；串流 IC 時 label 預先對齊 `row_index`，禁止在 chunk 內重算未來收益。

### Stage 3 — Event Filter（`:1057–1090`）

- 輸出 **`row_mask: pd.Index`**，不 `features_df.loc[idx]` 複製（現行 `:1090` 會複製全矩陣）。
- `insufficient` tier fallback 保留（`:1085–1087`）。

### Stage 4 — IC Calculation（`:1092–1152`）

**4a 主 IC（必做，串流）**

擴展 `compute_ic_from_l7_raw` 模式至 `analyze()` 主路：

```text
for group in manifest.groups:
    df = pq.read_table(path, columns=group_cols).to_pandas()
  df = df.loc[row_mask]
  ic_chunk = vectorized_ic(df, label)      # ic_engine.py:1183
  rolling_stats = welford_update(...)       # 新：取代全 rolling_ic dict
  append to ic_scores.parquet
  del df; gc.collect()                      # 已有模式 :220-222
```

- `parallel_ic_calculation`（`ic_config_schema.py:156`）：**group 級** `ProcessPoolExecutor`，非欄級（避免 430K task）。
- `n_jobs`：8GB→2，16GB→4，24GB→6，32GB→8。

**4b IC Decay（`:1122–1131`, `ic_engine.py:331–363`）**

| 現狀問題 | 改造 |
|----------|------|
| 每 horizon 全欄 `compute_ic` | 僅對 **stage4a 後 ICIR top 500**（可配置） |
| 每特徵 `_fit_exponential_decay` + warning（`:943–947`） | 熱迴圈 **零 log**；結束輸出 `{"low_r2_count": N, "fit_failed_count": M}` |
| O(features×horizons) | 向量化：每 chunk 一次算多 horizon label |

**4c Grouped IC（`:1133–1140`）**

- **立即修**：`config.ic_calculation.grouped_analysis.model_dump()`（崩潰點 `:1139` / `ic_engine.py:377`）。
- **補實** `by_volatility`（schema `:80` 預設 true 但 `compute_grouped_ic` 無分支）：在 `_compute_regime_groups_rule` 加 volatility quintile，或 **8GB tier 預設關閉** 並在 report 標 `not_implemented`。
- **記憶體**：每個 time group 只做 `compute_ic` on **survivors ≤500**，禁止對 430K 欄重算。
- **`_get_time_index` ms 假設**（`ic_engine.py:1024–1025`）：改為 `infer_timestamp_unit(values)`——實測 median 判斷 s/ms/us；golden 覆蓋秒級 kline。

### Stage 5 — Statistical Validation（`:1154–1202`）

**兩階段**：

| 階段 | 輸入 | 模組 |
|------|------|------|
| 5a | `ic_scores.parquet` only | FDR、p-value on rolling **aggregates**、threshold（`:1187–1191`） |
| 5b | `load_columns_v2(passed_features[:K])`，K=min(2000, len(passed)) | monotonicity `:1173`、coverage `:1174`、turnover `:1175` |

- `compute_all` 三個 analyzer 現皆全矩陣 → **僅對 K 欄投影**。
- FDR：對 430K p-values 用 BH 向量化（O(C) 記憶體，可接受）。

### Stage 6 — Redundancy（`:1204–1240`, `redundancy_filter.py`）

- 輸入上限：`min(len(passed), performance.max_features_for_correlation)` = **200**（`:155`）。
- Greedy/hierarchical：200×200 corr ≈ 320 KB，安全。
- VIF（`:50–56`）：O(n²) 迭代 regression；**硬 cap n≤100**（8GB）/ ≤200（32GB）。
- 輸出 `filtered_df`：只物化 **≤200 欄** × 20K ≈ 16 MB，可進 cache。

### Stage 7 — Report（`:1242–1316`）

- `summary_table`：全量 430K 列 **不進 JSON**；spill 為 parquet，API 只返 `top_n`（`:144` 預設 30）+ `total_features` + filter_log。
- `correlation_matrix`：僅 stage6 子集（≤200×200）。
- `grouped_ic`：只含 top-N 特徵的 regime 摘要，非全表。

### Cross-Sectional（`:162–220`）

| 現狀 | 改造 |
|------|------|
| `features.copy()` 全 panel | 按 timestamp 分塊；每塊 `rank corr` 向量化 |
| 多 symbol 一次載入 | 外層迴圈 symbol → `load_columns_v2` 投影共通欄名交集 |

共通欄：以 `config_hash` + feature **canonical name** 對齊；跨 symbol 不同 hash → **fail-closed**（run-selector 已鋪路）。

### Deep 10 模組（`run_deep_analysis` `:558–620`）

**前置條件**：stage6 `filtered_df` 存在且 `len(cols)≤200`；否則 skip + 明確 log。

| 模組 | 複雜度 | 策略 |
|------|--------|------|
| factor_return | O(T×N_q) | ✅ 直接跑，N≤200 |
| factor_centrality | O(T×C²) PCA | C≤50（`n_components` `:169`）；rolling PCA 用 incremental |
| trend_analysis | O(modules×T) | ✅ on ICIR series（已聚合） |
| parameter_sensitivity | O(families) | metadata 驅動，不讀全矩陣 |
| rolling_oos | O(splits×T×C) | C≤50；walk-forward 嚴守時間切分 |
| factor_orthogonalization | O(T×C²) QR/SVD | **C≤30**；`advanced` tier only |
| factor_exposure | O(T×C) | C≤100 |
| long_short | O(T×C) | C≤100 |
| feature_quality_diagnostics | O(T×C) | C≤200 |
| net_ic | O(T×C) | C≤200 |

`foundation` preset 已關 deep（`:284–287`）；建議 **8GB 強制 `foundation`**，16GB `intermediate`，24GB+ `advanced`。

### API / Event Loop

- `ic_analysis_service.py:209` 同步 `analyzer.analyze()` → `asyncio.to_thread(...)` + 進度 queue。
- **幽靈 `max_features`**：API `FeatureFilterConfig.max_features`（`ic_models.py:15`）經 `config_override.feature_filter`（`:967–970`）傳入，但 `ICConfig` **無此欄**、orchestrator **零處理**。
  - **修法**：orchestrator stage0 後新增 `_apply_feature_filter`：
    1. metadata include/exclude/pattern 先濾（零成本）；
    2. `max_features` 作用於 **stage5a 後** `summary_table` 取 top-N（**非 stage0 截斷**，避免漏高 IC 冷門因子）；
    3. 若使用者要「硬 cap 互動式」：UI 明示「粗篩模式」並寫入 filter_log。

---

## 3. 數據品質 / 無洩漏

| 風險 | 保護措施 |
|------|----------|
| Look-ahead in label | label 只在 stage2 計算一次；chunk IC 禁止重算 returns；`selection_window` / `split_id` 強制（`ic_engine.py:446–454`） |
| Train/val/test 洩漏 | `selection_window` 過濾 row_mask；rolling_oos / deep 模組只讀 mask 內時間軸 |
| 跨 symbol 污染 | cache key = `{symbol, tf, config_hash, task_id}`；cross-sectional 禁止共享 preprocessor 狀態 |
| Stale cache | `data_fingerprint` + manifest `mtime`；resume 校驗 |
| NaN/inf gate | 維持 0.9 NaN 剔除；chunk 內 `np.isfinite` gate；**不**放寬 float16 |
| Timestamp 單位 | `_get_time_index` 單位推斷 + `row_index_v2` 為 canonical 軸 |
| 假資料 | spill 只寫真實計算結果；測試用 byte-faithful fixture，禁 ms/秒混用 |
| PIT preprocessing | winsorize 分位數來自 **train window only**（`selection_window` 內 Pass-1） |

---

## 4. 算時 / 輸出優化

### 4.1 向量化 / 並行

| 熱點 | 現狀 | 優化 |
|------|------|------|
| `compute_ic` | 全矩陣 `np.corrcoef`（`:1194–1198`） | 保持；但 **chunked** |
| `compute_rolling_ic` | 全欄 rank + rolling corr（`:288–301`） | Welford 串流；top-N 才重算 |
| `compute_ic_decay` | Python 雙迴圈（`:342–347`） | horizon 外迴圈 + chunk 內向量化 |
| decay fit | `scipy.optimize.curve_fit` ×14K | 僅 top-500；低 R² 不 fit |
| grouped IC | 每組全欄 `compute_ic` | survivors only |
| log | 14,090 warnings | 單行摘要 |

### 4.2 Numba 候選

- `_rolling_corr_matrix`（`:1259–1299`）已向量化 NumPy；可 Numba 化內層若 profiling 顯示瓶頸。
- Spearman chunk：rank 用 `scipy.stats.rankdata` axis=0 對 **cols≤4096** 子矩陣。

### 4.3 輸出最小化

| 輸出 | 策略 |
|------|------|
| API JSON | `top_n=30` 摘要 + spill 檔案 URI |
| `rolling_ic` | 預設 **不返**；`?include_rolling=true` 且 features≤50 |
| `ic_decay` | 只返 top-N |
| `grouped_ic` | 每 regime 只返 top-10 |
| HDF5 filtered | 只寫 stage6 子集（≤200 欄） |
| WS 進度 | 每完成 1 manifest group 報一次（~200–500 次/run，可接受） |

### 4.4 粗估算時（430K 欄，20K 列，8GB tier，2K chunk）

- 220 groups ×（讀 parquet + IC + Welford）≈ **15–40 min**（視磁碟）
- decay off、grouped off、deep off
- +decay top-500：+5–10 min
- stage6 on 200 欄：+2 min

---

## 5. 正確性代價與 Golden 需求

| 優化 | 語義變更？ | Golden / 驗證 |
|------|-----------|---------------|
| 串流 IC vs 全矩陣 IC | **不變**（結合律） | 小 fixture 10 欄 byte 比對 `compute_ic` |
| Welford rolling ICIR vs 全序列 | ICIR 應一致；完整 rolling 曲線可能略異（stride 相同則一致） | 固定 seed 20 欄 × 5K 列，atol=1e-10 |
| 兩遍 winsorize vs 全矩陣 | 若 Pass-1 用全樣本，**一致**；僅 train window 則 **刻意不同**（更正確） | 標註 split_id 的 golden |
| stage5b 只算 passed | **不變**（未通過本就不進 redundancy） | 回歸 passed 集合 |
| decay 只算 top-500 | **變**：非 top-500 無 decay 欄位 | report 標 `decay_scope=top_500`；UI 明示 |
| grouped 只算 survivors | **變** | 同上 |
| `max_features=30` 後置 | **變**（可能漏第 31–500 名） | 與使用者契約 + filter_log |
| early-skip decay fit | 只影響 half_life 等衍生欄，不影響 IC 本身 | 可選；預設關 |
| 8GB 關 orthogonalize | **不變**（本來就該 tier-gated） | tier preset 測試 |

**必做 golden**：
1. `test_ic_streaming_equivalence` — 全載 vs 串流 IC scores
2. `test_grouped_ic_groupedconfig` — `model_dump()` 不崩潰
3. `test_timestamp_unit_inference` — 秒/毫秒 kline
4. `test_feature_filter_max_features_applied` — 端到端 passed 數量
5. 既有 `tests/feature_engineering/test_ic_first_pipeline.py` 擴展至 UI analyze 路徑

---

## 6. Epic 切分與優先序

| Epic | 範圍 | 命中準則 | 預估 |
|------|------|----------|------|
| **E0 Hotfix** | GroupedConfig `.model_dump()`；decay log 聚合；`asyncio.to_thread`；timestamp unit | 1,4 | 1–2 d |
| **E1 Streaming IC Core** | stage0 manifest-first；stage4a 串流 + spill + resume；`_ic_cache` 瘦身 | 1,2,3,4 | 1–2 w |
| **E2 Gated Materialization** | stage5b/6 欄投影；feature_filter 接線；報告 top-N only | 1,3,4,5 | 1 w |
| **E3 Regime/Decay Tiering** | grouped survivors-only；by_volatility 實作或關閉；decay top-K | 1,4,6 | 3–5 d |
| **E4 Cross-Symbol** | batch orchestrator；cross-sectional 分塊；100 symbol resume | 2,3,6 | 1–2 w |
| **E5 Deep Module Caps** | centrality/orthogonalize 硬上限；incremental PCA | 1,4,6 | 1 w |
| **E6 Golden + Perf Bench** | 430K 合成 parquet benchmark；per-tier CI gate | 3,6 | 持續 |

**建議執行順序**：E0 → E1 → E2 → E3 → E4 → E5 → E6（E0 不擋 E1，可並行但 E0 先合併減少使用者痛點）

---

## 7. 風險與不確定點（供另兩家詰問）

1. **L7 manifest 是否總有 `row_index`？** 舊 run 無 `row_index`（`feature_reader.py:171`）時，串流軸從何而來？需實測 orphan run 比例與 fallback 策略（讀 parquet 首欄 index vs fail-closed）。

2. **兩遍 winsorize 與 FF processed artifact 語義是否一致？** 若 FF L6.5 已 winsorize，IC 再做的正確性/重複處理需三方簽核（準則 3）。

3. **Welford rolling ICIR 在 stride>1、window 邊界** 是否與現行 `_rolling_corr_matrix` 逐點輸出完全一致？需數學推導 + golden；我假設 ICIR 只用 mean/std，可合併統計。

4. **`max_features` 後置 vs 前置**：量化上是否存在「IC 低但 monotonicity 高」的因子被漏？這是產品決策，不是純工程問題。

5. **430K 欄 run 是否為 FF 配置錯誤？** 若根因是 indicator 笛卡爾積爆炸，僅優化 IC 治標；需委員會判定是否 FF 側加 hard cap。

6. **HDF5 materialize 路徑**（`ic_analysis_service._materialize_features_for_ic`）是否仍會產出 34GB 中間檔？串流 IC 應 **跳過 materialize**，直接讀 L7 parquet；否則磁碟/時間瓶頸仍在。

7. **ProcessPool group 並行** 在 macOS spawn 下的 h5py/pandas 開銷可能反增；需 microbench（`scripts/b7_l65_threadpool_microbench.py` 模式）。

8. **`by_volatility` 實作** 與 `by_regime` rule 的 `high_vol_percentile` 是否重複？需避免雙計算同一分組。

9. **Cross-sectional 欄名對齊**：不同 symbol 同一 canonical feature 是否保證同列名？取決於 FF registry；未驗證前 cross-sectional 應 fail-closed on mismatch。

10. **Resume 與 WS 任務生命週期**：API server restart 後 `task_id` checkpoint 是否可發現並續跑？需持久化 task registry（現 `_tasks` 記憶體內）。

11. **合規**：spill 目錄在 `data_cache/` 不 commit 已符合；但長期 430K×N symbol spill 磁碟用量需 retention policy（準則 5）。

12. **我未實測** 真實 430K×20K parquet 的 group 數與單 group 欄數分佈；`chunk_cols=2048` 可能需按 group 邊界對齊（避免跨 group read 碎片化）。需讀一份真實 manifest 再定。

---

**獨立主張摘要**：不要試圖讓 430K×20K 在 pandas 裡「跑得動」，而要讓 **IC 管線永遠不物化超過 `chunk_cols×rows` 的子矩陣**；現成藍本是 `compute_ic_from_l7_raw`，缺的是 orchestrator 全面 adopt + 下游 stage 改為「先篩後載」+ API/正確性債務清償（GroupedConfig、max_features、timestamp、log）。

HANDOFF_NOT_UPDATED: READ-ONLY 任務，依 `.cursorrules` 不覆寫根 `HANDOFF.md`。
