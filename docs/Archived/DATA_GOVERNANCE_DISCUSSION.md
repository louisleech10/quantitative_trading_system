# Feature Factory 資料治理：記憶體 × 效能 × 架構討論

> **目的**：解決 Feature Factory 在 8GB M1 上的 OOM 和計算時間瓶頸  
> **狀態**：討論階段 — 未實作  
> **日期**：2026-04-10  

---

## 1. 問題定義

### 1.1 動機

Feature Factory 的設計理念是「大量生成 → IC 篩選」— 因為事前不知道哪些特徵有效，所以需要涵蓋所有 window / aggregator / indicator 組合。這是量化研究的核心邏輯，**不能因為硬體限制而砍掉搜索空間**。

但在 8GB M1 MacBook Air 上，目前的 pipeline 完全無法跑完：

| 問題 | 現象 | 根因 |
|------|------|------|
| **OOM** | L3 輸出超過物理記憶體 | 102K+ cols × 52K rows × 4 bytes = ~20 GB |
| **計算時間** | L6.5 replace 模式跑 20+ 分鐘無回應 | rank_transform 對 100K+ 欄做 rolling.rank() |
| **MultiTF 極慢** | 12h → 1h 對齊卡住 | merge_asof 對 100K+ 欄寬 DF 做排序+查找 |

### 1.2 為什麼不能簡單砍配置

| 曾提出的方案 | 為何不可行 |
|-------------|-----------|
| `apply_to: all` → 人工選定 200 個特徵 | 量化研究就是不知道哪些有用，需要全搜索 |
| 減少 windows 10→4 | 不知道哪個 window 有效，短中長期都需涵蓋 |
| 減少 aggregators 10→5 | 同上，不同 agg 捕捉不同統計特性 |

**結論：問題的解法必須在不縮減搜索空間的前提下，改變計算和儲存策略。**

### 1.3 目前的數據規模

單一 symbol（如 ETHUSDT），主框架 12h，L1 中高階未開、其餘全開：

| Layer | 描述 | 輸入 | 乘法因子 | 估算輸出欄位 |
|-------|------|------|---------|-------------|
| L0 | Data Ingestion | raw OHLCV | - | 7 sources |
| L1 | Atomic Indicators | 7 sources × fibonacci periods | ~140× | ~960 cols |
| L2 | Derived Operators | L1 | ~0.5× | ~500 cols |
| L3 | Rolling Aggregation | L1 only (960 cols) | **×100** (10w×10a) | **~96,000 cols** |
| L4 | Lag Features | raw+L1 only (apply_to=layer1_and_raw) | ×5 (fibonacci lags) | ~5,000 cols |
| L5 | Cross Sectional | disabled | 0 | 0 |
| L6 | Meta Features | L1+L2+raw | 小 | ~100 cols |
| **合計 L1-L6** | | | | **~102,000+ cols** |
| L6.5 | Preprocessing (replace) | 全部 102K cols | 1:1 | 102K cols |
| L7 | Validate & Persist | | | |

> 用戶實際量測：L2+L3+L4+L6 全開 = **208,135 個特徵**  
> L6.5 replace 模式跑 20+ 分鐘仍無回應

### 1.4 記憶體數學

```
102K cols × 52K rows × 4 bytes (float32) = ~20 GB → 8GB M1 物理不可能
208K cols × 52K rows × 4 bytes (float32) = ~40 GB → 更不可能
```

即使 `_ensure_float32` 已在每層 `_safe_execute` 後執行，float32 也存不下。

---

## 2. 效能瓶頸分析

### 2.1 記憶體瓶頸（壓力測試結果）

測試腳本：`tests/performance/test_memory_pressure.py`

| 測試規模 | Layer | 結果 |
|---------|-------|------|
| 200 cols × 10K rows | L3 (10w×10a) | 1,526 MB DF, 37s |
| 200 cols × 10K rows | L6.5 (20K cols) | 卡在 rank_transform |
| 10K rows × 5K cols | L6.5 rank_transform | **+2,087 MB RSS** |
| 52K rows 安全邊界 | L3 (10w×10a) | 最多 37 個 L1 特徵 |
| 52K rows 安全邊界 | L3 (3w×4a) | 最多 315 個 L1 特徵 |

### 2.2 計算時間瓶頸

基於壓力測試外推（主框架 12h, 52K rows, 960 L1 cols）：

| 操作 | 估算時間 | 瓶頸原因 |
|------|---------|---------|
| **L3 rolling** (全配置) | ~60-120 min | `slope` 仍需 `rolling.apply(..., raw=True)`；`rank` 雖已向量化，但 100K+ 寬表下整體 rolling 成本仍高 |
| **L6.5 rank_transform** | 20+ min（用戶實測 / 歷史觀察） | `rolling.rank(pct=True)` 已是向量化快路徑，但在 100K+ cols 下仍昂貴，且 full-frame materialization 會放大成本 |
| **L6.5 adaptive_zscore** | ~5-10 min | 2 個 window × rolling.mean/std × 100K cols |
| **MultiTF merge_asof** | 極長（用戶反映） | `pd.merge_asof` 需排序全 DF + 逐行查找，100K+ cols 時複製開銷巨大 |
| **L4 lag** | relatively fast | 只對 raw+L1，且已 chunked |

### 2.3 L3 個別 aggregator 速度分析

| Aggregator | Pandas 實作 | 速度等級 | 原因 |
|-----------|------------|---------|------|
| mean, std, min, max | `rolling.mean()` 等 | ⚡ 快 | C-level sliding window |
| skew, kurt | `rolling.skew()` 等 | ⚡ 快 | C-level |
| range | max - min | ⚡ 快 | 已快取 max/min |
| zscore | (data - mean) / std | ⚡ 快 | 已快取 mean/std |
| **rank** | `rolling.rank(method="average", pct=True)` | ⚠️ 中等 | 已向量化，但寬表下仍昂貴 |
| **slope** | `rolling.apply(_slope_fn, raw=True)` | 🐌 慢 | per-element Python callback + np.dot |

> **目前 slope 仍是 L3 的明確慢點；rank 雖已不再走最慢的 Python callback 路徑，但在 100K+ 寬表下仍可能是總耗時大戶。**

注意：截至 2026-04-11 的 codebase，chunked 路徑會呼叫 `_apply_vectorized_aggregators_with_cache()`，因此 rank 在 chunked 路徑下也走 `rolling.rank(method="average", pct=True)`；舊版「chunked 路徑走慢路徑」的描述已不再成立。

---

## 3. Polars 評估

### 3.1 Polars vs Pandas 在本場景的比較

| 面向 | Pandas | Polars | 評估 |
|------|--------|--------|------|
| **Rolling mean/std/min/max** | C-level, 單線程 | Rust, 多核並行 | Polars ✅ 快 2-4× (M1 8核) |
| **Rolling rank** | `rolling.rank()` C-level 或 `apply` callback | `rolling.rank()` Rust-native | Polars ✅ 顯著快 |
| **Rolling slope** | `rolling.apply(raw=True)` Python callback | 需自行用 `rolling.map_batches` 或 `rolling.apply` | ⚠️ 要看實作 |
| **Wide DataFrame (100K+ cols)** | 每欄是獨立 block, 記憶體分散 | 每欄是獨立 Series, 更好的記憶體佈局 | Polars ✅ 稍優 |
| **記憶體使用** | float32 支援但 rolling 會內部升到 float64 | float32 全程保持 | Polars ✅ 省一半 |
| **merge_asof** | `pd.merge_asof` 需複製排序整張寬 DF | `pl.DataFrame.join_asof` 更高效 | Polars ✅ 快 |
| **Lazy evaluation** | 無 | `LazyFrame` — 查詢計劃優化、記憶體按需分配 | Polars ✅✅ 可以不把 100K cols 同時載入 |
| **Streaming** | 無原生支援 | `collect(streaming=True)` — 分批執行 | Polars ✅✅ 原生解決 OOM |
| **生態整合** | HDF5/TA-Lib/XGBoost/scikit 全原生 | 需 `.to_pandas()` 橋接 | Polars ❌ 額外轉換成本 |
| **學習成本** | 現有程式碼全是 pandas | API 不同，需重寫 | Polars ❌ 大量重構 |
| **TA-Lib** | 接受 numpy array | 同，Polars 可 `.to_numpy()` | 平手 |

### 3.2 Polars 能解決什麼

**✅ 能解決的：**
1. **計算速度** — rolling 操作 Rust 多核並行，尤其 rank/slope 不需要 Python callback
2. **記憶體效率** — float32 全程保持不升 64；LazyFrame 不預先分配整張 DF
3. **Streaming 模式** — `collect(streaming=True)` 可以分批計算和寫出，原生防 OOM
4. **MultiTF merge_asof** — `join_asof` 實作更高效

**❌ 不能解決的：**
1. **最終輸出仍是 102K+ cols** — 如果你要同時存在記憶體裡，任何框架都裝不下
2. **生態橋接** — TA-Lib、XGBoost、scikit-learn 需要 numpy/pandas input，轉換有成本
3. **重構工作量** — 整個 FeatureEngineering 重寫，風險高

### 3.3 Polars 的兩種引入策略

#### 策略 A：Full Migration — 整體遷移到 Polars

```
優點：
  - 一致的 API，long-term 維護簡單
  - 充分利用 LazyFrame + streaming
  
缺點：
  - 大量重構（rolling_aggregator, feature_preprocessor, tf_aligner, lag_processor, ...）
  - TA-Lib 需要 numpy bridge
  - 測試全部要重寫
  - 高風險，長時間
```

#### 策略 B：Surgical Polars — 只在瓶頸處引入

```
在 pandas pipeline 的特定瓶頸處，轉為 Polars 計算再轉回：
  - L3 rolling rank/slope → Polars rolling 計算 → 轉回 pandas
  - L6.5 rank_transform → Polars rolling.rank() → 轉回 pandas
  - MultiTF merge_asof → Polars join_asof → 轉回 pandas

優點：
  - 改動範圍小，風險可控
  - 立即獲得瓶頸處的速度提升
  - 不影響其他 layer
  
缺點：
  - pandas ↔ polars 轉換有開銷（~0.5-2s per 100K cols）
  - 記憶體問題仍未根本解決（轉換時同時存在兩份 DF）
  - 維護混合框架
```

### 3.4 Polars 結論

**Polars 改善計算速度：✅ 有幫助，尤其是 rolling rank/slope 和 merge_asof**  
**Polars 改善記憶體：⚠️ 部分有幫助（float32 不升 64、streaming），但不解決根本問題**  

根本問題是：**102K 欄位 × 52K 行本身就超過 8GB 物理記憶體，不管用什麼框架都放不下。**

---

## 4. 解決方案探討

### 4.1 方案 A：IC-First Streaming Pipeline（推薦）

**核心思想**：不把全部 102K 欄位同時放在記憶體裡。逐批生成 → 即時 IC 篩選 → 只保留 survivors。

```
┌─────────────────────────────────────────────────────────────────┐
│                    IC-First Streaming Pipeline                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 0: 預先計算 label（forward return）                         │
│          label = (close.shift(-N) / close - 1)                   │
│          ~1 col, 可以放在記憶體                                    │
│                                                                  │
│  Step 1: 生成 L1 全量（~960 cols × 52K = ~190 MB）✅ 放得下       │
│                                                                  │
│  Step 2: L3 streaming — 逐 (window, agg) 或 逐 chunk 生成        │
│    ┌──────────────────────────────────────────────────┐          │
│    │ for window in [3, 5, 8, 13, 21, 34, 55, 89...]: │          │
│    │   for agg in [mean, std, rank, ...]:             │          │
│    │     chunk = rolling(window).agg(L1)              │          │
│    │     # 960 cols × 52K = ~190 MB per chunk         │          │
│    │     chunk = L6.5_preprocess(chunk)               │          │
│    │     ic_scores = spearman_corr(chunk, label)      │          │
│    │     survivors = chunk[:, abs(ic) > threshold]    │          │
│    │     append_to_hdf5(survivors)                    │          │
│    │     del chunk  # 釋放記憶體                       │          │
│    └──────────────────────────────────────────────────┘          │
│    峰值記憶體: ~190 MB (L1) + ~190 MB (chunk) + overhead         │
│    = 不到 1 GB ✅                                                 │
│                                                                  │
│  Step 3: 同理處理 L2, L4, L6                                     │
│                                                                  │
│  Step 4: 載入全部 survivors（預期幾百~幾千個特徵）                   │
│          → ML training / full IC analysis                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 優點
- **記憶體**：峰值 < 1 GB，完全解決 OOM
- **計算時間**：每個 chunk 只有 960 cols，rank/slope 的 apply callback 也快
- **搜索空間**：不縮減，全部 10w × 10a 都有被計算和評估
- **早篩效果**：大量低 IC 特徵（預計 90%+）在 L3 階段就被過濾，後續 L4/L6/L6.5 處理量大幅減少
- **與 Polars 相容**：可選擇性在 chunk 內部用 Polars 加速

#### 缺點
- **需要 label 前置**：label 需在 L3 之前計算（目前 label 在 L7）— 但技術上 forward return label 只需要 raw close 價格
- **IC 閾值選擇**：太嚴會漏掉弱但有效的特徵；太鬆仍然太多
  - 解法：用寬鬆閾值（如 |IC| > 0.01）只過濾明顯無用的特徵
  - 或者：不做 IC，改用 variance filter（常數欄/近零方差直接刪）
- **改變了 pipeline 順序**：L6.5 需要在 L3 chunk 內即時執行，而非等 L6 全部完成
- **重構範圍**：FeatureFactory.generate() 的 L3 流程需大改

#### 架構影響
- `FeatureFactory.generate()` → 需要新增 streaming mode 分支
- `RollingAggregator.compute_all()` → 需要新增 `compute_streaming()` 方法
- `FeaturePreprocessor.transform()` → 需要支援 column-subset 模式
- `FeatureStorage` → 需要支援 incremental append（逐批寫入 HDF5）

### 4.2 方案 B：Disk-Backed Pipeline（HDF5 Streaming）

**核心思想**：把記憶體中放不下的中間結果寫到磁碟，用 HDF5 做虛擬記憶體。

```
┌──────────────────────────────────────────────────────────────┐
│   L3 每算完一個 (window, agg) chunk → 寫入 HDF5 dataset     │
│   L6.5 從 HDF5 逐 chunk 讀取 → preprocess → 寫回 HDF5       │
│   最後從 HDF5 直接讀取所有 102K 欄位 → 但不載入記憶體         │
│   IC 計算也用 HDF5 逐 chunk 讀取                              │
└──────────────────────────────────────────────────────────────┘
```

#### 優點
- **保留全部特徵**：不做任何篩選，102K 全存在磁碟上
- **記憶體**：峰值只有一個 chunk 的大小
- **研究靈活性**：之後想重新分析不同 IC 閾值，不需重新計算

#### 缺點
- **磁碟 I/O 慢**：HDF5 隨機讀寫速度遠低於記憶體
- **計算時間**：雖然記憶體解決了，但**總計算時間不會減少**，甚至更慢（I/O overhead）
- **HDF5 column-wise 存取效率差**：HDF5 擅長 row-major 或 chunk-based，column-wise 讀取碎片化嚴重
- **SSD 寫入量大**：102K cols × 52K rows × 4 bytes = ~20 GB 寫入量，M1 MacBook SSD lifespan 問題

### 4.3 方案 C：Polars Streaming + Lazy（Polars-native 解法）

**核心思想**：全面遷移到 Polars，利用 LazyFrame + streaming execution。

```python
# 概念程式碼
import polars as pl

lf = pl.scan_parquet("features_l1.parquet")  # LazyFrame, 不載入記憶體

for window in windows:
    # LazyFrame 只記錄操作，不執行
    rolled = lf.with_columns([
        pl.col(c).rolling_mean(window).alias(f"{c}_Mean_W{window}")
        for c in feature_cols
    ])
    # collect(streaming=True) 分批執行
    rolled.collect(streaming=True).write_parquet(f"l3_w{window}.parquet")
```

#### 優點
- **原生 streaming**：Polars 的 `collect(streaming=True)` 自動分批
- **計算速度**：Rust 多核，rolling 操作快 2-8×
- **Query optimization**：LazyFrame 會優化查詢計劃（消除冗餘計算）
- **float32 全程保持**：不像 pandas rolling 內部升 float64

#### 缺點
- **全面重構**：整個 FeatureEngineering 模塊需要重寫
- **Polars rolling 限制**：`rolling.apply()` 自訂函式（slope）仍需 Python callback
- **TA-Lib 整合**：需要 pandas/numpy 橋接
- **風險高**：大量程式碼改動 + 行為差異（NaN handling, index alignment）
- **Polars streaming 對 wide DF 支援**：100K 欄的 LazyFrame streaming 是否真的能逐批處理欄位，需要驗證
- **學習曲線**：Polars API 與 pandas 差異大（無 index、expression-based）

### 4.4 方案 D：混合方案 — IC-First + Surgical Polars

**推薦方案**。結合方案 A 的架構改動和方案 B/C 的局部優化。

```
Phase 1: IC-First Streaming（架構層，解決記憶體）
  - 不改底層框架，仍用 pandas
  - L3 改為逐 (window, agg) 生成
  - 每 chunk 即時 IC/variance filter
  - 峰值記憶體 < 1 GB

Phase 2: Surgical Polars（效能層，解決計算速度）
  - 只在 3 個瓶頸處引入 Polars：
    ① L3 rolling rank → pl.Series.rolling_rank()
    ② L3 rolling slope → Polars rolling.map_batches + numpy
    ③ MultiTF merge_asof → pl.DataFrame.join_asof()
  - 不改 pipeline 架構，只替換內部實作

Phase 3: L6.5 Column Chunking（效能層，解決 20 分鐘卡住）
  - FeaturePreprocessor.transform() 加入 column_chunk_size
  - 每次只處理 1000-2000 cols → 結果拼回
  - 完全安全：winsorization/rank/zscore 都是 column-independent
```

#### 優點
- **漸進式實施**：Phase 1 先解決 OOM（最急迫），Phase 2/3 再優化速度
- **風險可控**：每個 phase 獨立，可逐步驗證
- **不縮減搜索空間**：全部特徵都有被計算和評估
- **記憶體 + 速度都改善**

#### 缺點
- **仍有重構工作量**：Phase 1 需要改 FeatureFactory 的 L3 流程
- **混合框架**：pandas + polars 共存，長期維護負擔

### 4.5 方案比較彙總

| 面向 | A: IC-First | B: Disk-Backed | C: Full Polars | D: 混合（推薦） |
|------|-----------|---------------|---------------|----------------|
| **記憶體** | ✅ < 1 GB | ✅ < 1 GB | ✅ streaming | ✅ < 1 GB |
| **計算時間** | ⚡ 基於 chunk size 快 | ❌ I/O overhead | ⚡⚡ Rust 多核 | ⚡⚡ streaming + polars 瓶頸 |
| **搜索空間** | ✅ 全保留 | ✅ 全保留 | ✅ 全保留 | ✅ 全保留 |
| **保留全部特徵** | ⚠️ 只保留 survivors | ✅ 全部在磁碟 | ✅ 全部 | ⚠️ 只保留 survivors |
| **重構範圍** | 中（L3 pipeline） | 中（storage layer） | 大（全部重寫） | 中（分階段） |
| **風險** | 低-中 | 低 | 高 | 低-中 |
| **MultiTF 改善** | ⚠️ 需額外處理 | ⚠️ 需額外處理 | ✅ join_asof | ✅ surgical polars |
| **M1 可行性** | ✅ | ✅ | ✅ | ✅ |

---

## 5. 需要決策的問題

### Q1: IC Gate 的時機和閾值

如果選方案 A/D（IC-First），需要決定：

- **Label 前置計算**：forward return label 只需 raw close 價格，可以在 L0 後立即計算。是否可接受？
- **IC 閾值**：建議用寬鬆閾值（|IC| > 0.01 或 0.02），只踢掉明顯無效的。或者用更簡單的 variance filter（標準差 < epsilon 的直接刪）。
- **是否保留 IC 分數**：每個被篩掉的特徵，記錄其 IC 分數到 metadata，方便之後回顧。

### Q2: 是否引入 Polars

選項：
- **不引入**：純 pandas，靠 IC-First streaming 解決記憶體，計算速度靠 chunking 改善
- **Surgical 引入**：只替換 L3 rank/slope 和 MultiTF merge_asof（3 處改動）
- **全面遷移**：長期目標，但非當前優先

### Q3: 「保留全部特徵」vs「只保留 survivors」

- 方案 A/D：IC filter 後只存 survivors → 如果之後想改 IC 閾值，需要重新跑 pipeline
- 方案 B：全部存磁碟 → 靈活但慢
- 折衷：**全部特徵的 IC 分數存到 metadata JSON**，只有 survivors 的完整 data 存到 HDF5。回顧分析時看 metadata，不需要重新計算

### Q4: MultiTF 的處理策略

目前 MultiTF 的問題是 merge_asof 對 100K+ cols 太慢。選項：
- **Column-batch merge_asof**：每次只 merge 1000 cols → concat
- **Polars join_asof**：轉 Polars 做 merge，再轉回
- **在每個 TF 內先 IC filter**：先篩再 merge，merge 的 DF 只有幾千列

### Q5: 實施優先順序

建議順序：
1. **L6.5 column chunking** — 最簡單，立即解決 20 分鐘卡住的問題
2. **L3 IC-First streaming** — 解決 OOM 核心問題
3. **Surgical Polars（rank/slope/merge_asof）** — 再提升計算速度
4. **MultiTF lazy alignment** — 處理跨時間框架問題

---

## 6. 補充資料

### 6.1 已確認事實

- ✅ `_ensure_float32` 已在每層 `_safe_execute` 後執行 — float32 已實作
- ✅ L6.5 的 winsorization / rank_transform / adaptive_zscore **全部是 column-independent** — 分批處理不會錯亂
- ✅ L3 只吃 L1（960 cols），不吃 L2 — 已在程式碼中確認（`_layer3_rolling_aggregation` 的 `_combine_layers([layer1])` ）
- ✅ L4 的 apply_to = `layer1_and_raw` — 不會對 L3 output 做 lag
- ✅ 截至 2026-04-11，L3 chunked 路徑也會走 `_apply_vectorized_aggregators_with_cache()`，因此 rank 在 chunked 與 non-chunked 兩條路徑都已使用 `rolling.rank(pct=True)` 快路徑；slope 仍保留 `rolling.apply(..., raw=True)` 慢路徑

### 6.2 壓力測試腳本

`tests/performance/test_memory_pressure.py` — 4 階段測試：
- Phase 1: 純數學估算
- Phase 2: L3 micro-bench（50 cols × 5K rows，不同配置）
- Phase 3: L6.5 子步驟剖析（500/2K/5K cols × 10K rows）
- Phase 4: OOM 邊界探測

### 6.3 關鍵程式碼位置

| 模塊 | 檔案 | 關鍵方法 |
|------|------|---------|
| L3 Rolling | `momentum/FeatureEngineering/operators/rolling_aggregator.py` | `compute_all()`, `_apply_vectorized_aggregators_with_cache()` |
| L6.5 Preprocess | `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | `transform()`, `_apply_rank_transform()` |
| Pipeline | `momentum/FeatureEngineering/feature_factory.py` | `generate()`, `_layer3_rolling_aggregation()` |
| MultiTF | `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `generate_multi_tf()` |
| TF Alignment | `momentum/FeatureEngineering/timeframe/tf_aligner.py` | `align_to_primary()`, `_merge_asof_align()` |
| Storage | `momentum/FeatureEngineering/feature_storage.py` | `save_factory_output()`, `load_factory_output()` |
| Lag | `momentum/FeatureEngineering/operators/lag_processor.py` | `compute_all()` |

---

## 7. 修訂歷史

| 日期 | 修訂內容 |
|------|---------|
| 2026-04-10 | 初版 — 記錄問題定義、壓力測試結果、方案探討 |
| 2026-04-10 | Gemini 評估與架構建議補充 |
| 2026-04-11 | GPT 評論重寫 — 僅聚焦記憶體與計算效能結論 |

---

## 8. Gemini 評論與建議 (重點精簡版)

針對 M1 8GB 記憶體限制與 100K+ 巨量特徵生成管線，以下是本方案的核心決策建議：

### 8.1 架構與實作建議
1. **Streaming (Chunking)** 是唯一且正確的解法：面臨物理記憶體上限，採用 Chunking 策略用時間換取空間是首選。
2. **高 C/P 值的第一步突破 (Quick Win)**：
   - **L6.5 垂直切割 (Column Chunking)**：`rank_transform` 與 `zscore` 為獨立欄位運算，逐批處理可立刻解決卡死問題。
   - **分段 Polars 延後考慮**：若透過純 Pandas Chunking 已經把時間降至合理範圍（如 10 分鐘內），可考慮不引入中介轉換 (Pandas ↔ Polars)，避免零拷貝問題、維護技術債以及潛在的記憶體二度翻倍。

### 8.2 量化業界警語：極度慎用「提早 IC 篩選」
您的擔憂**非常正確**！在特徵工廠階段直接用「線性 IC (Spearman/Pearson)」砍掉特徵，在量化界是**致命操作**，因為會導致：
- 錯失非線性 Alpha（很多極強特徵單看 IC=0，但在樹模型如 XGBoost 卻具備關鍵交互作用）
- 過分擬合單一市場狀態，抹殺抗微結構雜訊的好變數。

👉 **替代 IC-First 的安全做法 (Safe Pre-filtering)**：
若 Chunking 出來還是太大必須砍掉部分特徵，建議從以下「無損/低損」的方式去篩：
1. **Variance Filter (零方差 / 變異數過濾)**：直接剔除全為常數、NaN、或數值幾乎無變化的死特徵。
2. **Correlation Filter (去高共線性過濾)**：砍相似特徵！若兩個 EMA 視窗週期相似且相關性高於 0.98，僅保留其一，能減少 30%-50% 以上空間而不丟失任何模型資訊。
3. **Mutual Information / 淺層樹過濾**：如果非得評估效用，應透過互資訊或是訓練極淺的 3 層樹模型觀察分歧增益，取代死板的線性 IC 篩選。

---

## 9. GPT 評論與結論（只聚焦記憶體與計算效能）

### 9.1 GPT 評論：目前真正的瓶頸

- [GPT 評論] 根本問題不是單一 operator 太慢，而是 pipeline 目前仍以 full-materialization 為預設。L3、L6.5、MultiTF 都傾向先把寬表完整展開，再做後續處理；在 8GB M1 上，100K+ cols × 52K rows 這個量級本身就超出可承受範圍。
- [GPT 評論] 目前程式碼裡，rank 已比文件早期假設更快：L3 chunked 路徑和 L6.5 rank_transform 都已使用 rolling.rank 的向量化路徑。因此現在最值得優先處理的慢點，已經更偏向 `slope` 的 raw=True rolling.apply、L6.5 的 repeated full-frame copy，以及 MultiTF 的寬表 merge_asof。
- [GPT 評論] Polars 可以加速，但不是根解。若 pipeline 仍先產生完整寬表，再快的框架也只是把爆炸點延後，不會真正解決 OOM。

### 9.2 GPT 結論：簡單版

1. [GPT 結論] **記憶體優先級最高**：先解決「不要一次把全部特徵放進記憶體」；這比優化單一函式更重要。
2. [GPT 結論] **L6.5 column chunking 是第一個 quick win**：因為它改動小、風險低，能直接改善 20+ 分鐘無回應與高 RSS 問題。
3. [GPT 結論] **L3 streaming / chunked output 是真正根解**：只要 L3 還是整批 materialize，96K~200K 欄位級別的寬表就會持續壓垮記憶體。
4. [GPT 結論] **MultiTF 應排在第三優先**：因為 merge_asof 的痛點會在寬表變大後被放大，但它不是最前面的主因。
5. [GPT 結論] **Polars 是第二階段加速器，不是第一階段救火工具**：先把 chunking / streaming 架構定好，再決定是否用 Polars 替換熱點。

### 9.3 GPT 建議：實作優先順序

1. [GPT 建議] 先做 L6.5 column chunking，優先覆蓋 winsorization 和 adaptive_zscore，因為目前這兩段的 copy 與 rolling 中間結果會直接放大記憶體壓力。
2. [GPT 建議] 再做 L3 streaming 化，目標不是把某個 aggregator 再加速 20%，而是避免 L3 一次產出完整寬表。
3. [GPT 建議] 然後再處理 MultiTF，做 column-batch merge_asof 或局部替換為更適合寬表對齊的實作。
4. [GPT 建議] 最後才評估是否引入 Polars，優先替換 `slope` 與 MultiTF 對齊這兩個熱點。

### 9.4 GPT 最短結論

- [GPT 結論] **先切批，再談加速**。
- [GPT 結論] **先解決 L6.5，再重構 L3，最後才處理 MultiTF/Polars**。
- [GPT 結論] **不改 full-materialization 架構，任何框架優化都只是延後 OOM。**
