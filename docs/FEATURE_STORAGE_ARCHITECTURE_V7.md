# Feature Storage Architecture V7 — 分析與設計

> **Date**: 2026-04-19  
> **Status**: Draft / 待討論  
> **Scope**: V6.2 CGSA Pipeline 產出格式、下游相容性、Multi-symbol 擴展、儲存策略  
> **Context**: V6.2 pipeline 已完成，需解決輸出格式與下游服務的銜接問題

---

## 目錄

1. [V6.2 Pipeline 現況](#1-v62-pipeline-現況)
2. [問題一：下游服務全部不相容](#2-問題一下游服務全部不相容)
3. [問題二：Float 精度與儲存空間](#3-問題二float-精度與儲存空間)
4. [問題三：L3 vs L6.5 Rolling Rank 不可省略](#4-問題三l3-vs-l65-rolling-rank-不可省略)
5. [問題四：Multi-symbol 擴展到百/千級](#5-問題四multi-symbol-擴展到百千級)
6. [問題五：IC 篩選必須同時跨 Symbol × 跨 Group](#6-問題五ic-篩選必須同時跨-symbol--跨-group)
7. [問題六：SHAP 需要多 Symbol 分析維度](#7-問題六shap-需要多-symbol-分析維度)
8. [問題七：Feature Browser 完整整合](#8-問題七feature-browser-完整整合)
9. [問題八：Immutable Artifact 儲存策略](#9-問題八immutable-artifact-儲存策略)
10. [問題九：硬體升級自動加速設計](#10-問題九硬體升級自動加速設計)
11. [分層儲存架構設計（最終方案）](#11-分層儲存架構設計最終方案)
12. [行動優先順序](#12-行動優先順序)
13. [待決事項](#13-待決事項)

---

## 1. V6.2 Pipeline 現況

### 執行結果

| 指標 | 數值 |
|------|------|
| Pipeline 總耗時 | 3845s (64.1 min) |
| 特徵數 | 435,389 |
| 輸出 Groups | 708 |
| 輸出格式 | Per-group Parquet (zstd) |
| 輸出大小 | 708 files, **36.63 GB** |
| 記憶體 (RSS delta) | 600.1 MB |
| 壓縮比 | 1.06x (幾乎沒壓) |

### Layer 分佈

| Layer | 1h | 12h |
|-------|-----|------|
| L1 (raw indicators) | 1,611 | 1,611 |
| L2 (WorldQuant/Momentum) | 46,677 | 46,677 |
| L3 (rolling aggregation) | 156,920 | 156,047 |
| L4 (lag features) | 12,912 | 12,912 |
| L5 (cross-sectional) | 0 | 0 |
| L6 (meta features) | 11 | 11 |

### 時間分佈

| 階段 | 耗時 | 佔比 |
|------|------|------|
| L1+L2 (1h) | ~403s | 10.5% |
| L3+L4+L6 (1h) | ~627s | 16.3% |
| L1~L6 (12h) | ~81s | 2.1% (有 cache) |
| Multi-TF merge | ~81s | 2.1% |
| **L6.5 Preprocessing** | **2104s** | **54.7%** |
| **L7 Validate + Persist** | **540s** | **14.0%** |

### L7 Validate + Persist 時間分析

L7 佔 pipeline 14.0%（540s / 9.0 min），瓶頸是**少數巨大 group 的串行寫入**：

| 批次 | 耗時 | 原因 |
|------|------|------|
| Groups 0–100 | 74s | 含初始化 + 一些中型 group |
| Groups 100–300 | 3s | 全部是小檔（<1 MB） |
| **Groups 300–400** | **219s** | 命中 WorldQuant 1h 大 group（25,776 cols → 2.2 GB） |
| Groups 400–600 | 2s | 小檔 |
| **Groups 600–700** | **208s** | 命中 WorldQuant 12h 大 group（同結構） |
| Groups 700–708 | 34s | 含 L3_rolling 大 group 尾段 |

**發現**：4 個 >1 GB 的 group 佔了 L7 的 **79%** 時間（427s / 540s）。

### L7 優化預估

| 優化方式 | 機制 | 預估耗時 | 節省 |
|----------|------|---------|------|
| 現況 (float32) | 串行寫入 36.63 GB | 540s (9.0 min) | — |
| **float16** | 寫入量減半 → 18.3 GB | ~297s (5.0 min) | **-45%** |
| **float16 + max_group_split** | 寫入減半 + 消除大檔瓶頸 | ~216s (3.6 min) | **-60%** |
| float16 + split + ThreadPool I/O | 平行寫入多個小 group | ~120s (2.0 min) | **-78%** |

**為什麼 max_group_split 有效**：
- 25,776 cols 的單一 group → 寫入時必須一次 serialize 整個 2.2 GB Arrow table
- 拆成 6 個 ~4300 cols sub-group → 每個 ~350 MB，serialize 更快且 memory-friendly
- 拆分後還可以用 ThreadPool 平行寫入（I/O bound，不受 GIL 限制）

### 檔案大小分佈

| Bucket | 數量 | 總大小 |
|--------|------|--------|
| < 1 MB | 556 | 0.11 GB |
| 1–10 MB | 72 | 0.18 GB |
| 10–100 MB | 3 | 0.11 GB |
| 100 MB–1 GB | 73 | 29.37 GB |
| > 1 GB | 4 | 6.86 GB |

**最大檔案**: `1h_L2_WorldQuant.parquet` — 2,236 MB, 25,776 columns

### 壓縮效果差的原因

L6.5 preprocessing 後的值（rank/zscore/gaussian）是 [0, 1] 或 [-3, 3] 範圍內的**近乎均勻分佈浮點數**，bit pattern 接近隨機 → zstd 對 float32 隨機值幾乎無法壓縮。

---

## 2. 問題一：下游服務全部不相容

### 現況

V6.2 輸出 **Per-group Parquet** 到 `data_cache/features/{symbol}/{config_hash}/`，但所有下游服務都用 **h5py 讀 HDF5**：

| 下游服務 | 讀取方式 | V6.2 相容？ |
|----------|----------|-------------|
| `feature_factory_service.py` → `_load_task_features()` | `h5py.File(path)` | ❌ Crash |
| `feature_browser_service.py` → `_load_features_df()` | `h5py.File()` / `pd.read_csv()` | ❌ 不支援 Parquet dir |
| `ic_analysis_service.py` → IC Gatekeeper | `h5py` via `_load_features_hdf5()` | ❌ Crash |
| `shap_analysis_service.py` → SHAP | `h5py` 讀特徵 | ❌ Crash |
| `xgboost_task_service.py` → XGBoost | `FeatureLibrary.load()` | ❌ 只支援 HDF5 |
| `cross_symbol_training_service.py` | `FeatureLibrary.load_multi()` | ❌ 只支援 HDF5 |

### 根本問題

1. **格式不匹配**: 上游 Parquet vs 下游 HDF5
2. **manifest.json 缺失**: V6.2 output directory 沒有 manifest.json（只存在於 temp registry work_dir）
3. **全量載入**: 所有下游都是 full-materialization（一次讀全部 columns），435K columns 在 8GB 機器 = OOM

### 結論

**全面重新設計**（不做 HDF5 Bridge，直接改為最終格式）：
- 移除所有 `h5py` 讀取程式碼，統一為 Parquet reader + column projection
- manifest.json 為必要檔案，寫入 output directory
- 所有下游改為按需讀取（lazy loading, column projection），不做 full-materialization

---

## 3. 問題二：Float 精度與儲存空間

### 實測結果

| 精度 | Rank [0,1] unique | Zscore [-3,3] unique | IC delta vs f32 | Parquet 支援 |
|------|-------------------|---------------------|------------------|-------------|
| **float32** | 17,928 (全部) | 17,928 | baseline | ✅ |
| **float16** | 5,217 | 8,110 | **0.000003** | ✅ PyArrow 21 |
| **float8 E4M3** | 98 | 176 | 0.000462 | ❌ 不支援 |
| **float8 E5M2** | ~8 | ~60 | 更差 | ❌ 不支援 |

### Spearman IC 精度測試

```
float32 IC: 0.012577
float16 IC: 0.012574 (delta: 0.000003) ← 可忽略
float8  IC: 0.012115 (delta: 0.000462) ← 破壞性損失
```

### 結論

| | float16 | float8 |
|---|---|---|
| **結論** | ✅ **唯一採用格式** | ❌ **排除** |
| 精度損失 | IC delta < 0.000003，可忽略 | IC delta 0.000462，37x worse |
| 空間效果 | 36.6 GB → ~18.3 GB (省 50%) | 理論 75%，但精度不可接受 |
| 生態支援 | PyArrow 21 原生支援 | 無 Parquet 支援 |
| Unique 值 | 1024 in [0,1]，足夠區分 | 98 in [0,1]，rank 幾乎無意義 |

> **注意**: float16 壓縮後能否比 float32+zstd 更小仍需實測。由於 L6.5 後值接近隨機，理論上 float16 raw bytes 就已經比 float32+zstd 小。

---

## 4. 問題三：L3 vs L6.5 Rolling Rank 不可省略

### 語義差異

| | L3 Rolling Rank | L6.5 Rank Transform |
|---|---|---|
| **目的** | Feature Engineering — 建立新信號 | Preprocessing — 正規化分佈給 ML 用 |
| **位於** | `rolling_aggregator.py` | `_numba_transforms.py` |
| **Window** | 短期：W=3, 5, 8, 13, 21, 34, 55, 89 | 長期：W=252 |
| **輸入** | L1/L2 原始特徵 | 所有 L1~L6 特徵（含 L3 rank 輸出） |
| **語義** | 「EMA_5 在過去 5 根 K 棒中排第幾？」→ 動量信號 | 「這個特徵值在過去 252 根中排第幾？」→ 分佈正規化 |
| **輸出範例** | `close_trend_EMA_5_Rank_W5` | 對 input column 做 in-place rank transform |
| **值域** | [0, 1] 百分位 | [0, 1] 百分位 |

### 實證驗證

```
correlation(rank_long(rank_short(x)), rank_long(x)) = 0.956
```

- **0.956 ≠ 1.0** → 攜帶不同資訊
- L3 rank 是「短期相對位置」的 **信號**（像是一個技術指標）
- L6.5 rank 是「長期分佈正規化」的 **預處理**（讓 tree model 更穩定）

### 結論

**兩者都保留，不可省略。** L3 rank 建立了新的特徵維度，L6.5 rank 確保所有特徵（包含 L3 rank）在 ML 訓練時有穩定的分佈。

### 目前 L3 Rank 命名觀察

從實際 V6.2 parquet 檔案看：
- L3 files 的 columns 命名如 `close_trend_EMA_5_Slope_W3`, `close_trend_EMA_5_Range_W8` 等
- L3 **Rank** 在 V6.2 的 rolling_aggregator 中是作為 aggregation 之一（和 Mean, Std, Slope, Skew, Kurt, Range, Max, Min 並列）
- L2 WorldQuant 也有 `TsRank_W5` 等 columns（L2 層的 rolling rank operators）

---

## 5. 問題四：Multi-symbol 擴展到百/千級

### 數字限制

```
1 symbol (float32) = 435K features × 17,928 rows × 4 bytes ≈ 30 GB
1 symbol (float16) = 435K features × 17,928 rows × 2 bytes ≈ 15 GB
```

| 規模 | Float16 全量 | 本機 228 GB 可容納？ |
|------|-------------|---------------------|
| 5 symbols | 75 GB | ✅ 但接近極限 |
| 10 symbols | 150 GB | ⚠️ 需清理 |
| 50 symbols | 750 GB | ❌ 需外接 |
| 100 symbols | 1.5 TB | ❌ 需 NAS/SSD |
| 1000 symbols | 15 TB | ❌ 需雲端 |

### 關鍵洞察

**跨 symbol 訓練不需要全部 435K 特徵**。真實流程：

```
[Per-symbol] 生成 (435K) → IC 篩選 (top 500~2000) → [Cross-symbol] 訓練 (selected only)
```

訓練矩陣大小：
```
2,000 features × 17,928 rows × 100 symbols × 2 bytes (float16) = 7.2 GB
→ 8 GB M1 可以 handle
```

### 結論

- **全量儲存**：Per-symbol, per-config_hash 保留（Layer 1, immutable），float16
- **訓練讀取**：Column projection — 只讀 IC 篩選後的 features
- **硬碟策略**：本機放 active symbols，其餘放外接/遠端（config 可設定 feature store 路徑）
- **記憶體**：永遠不做 full-materialization of 435K columns

---

## 6. 問題五：IC 篩選必須同時跨 Symbol × 跨 Group

### 業界標準做法

在量化業界，IC（Information Coefficient）篩選的正確做法是 **cross-sectional IC**：

```
對於每個時間點 t：
  1. 收集 feature_X 在所有 N 個 symbols 的值 → vector(N)
  2. 收集 forward_return 在所有 N 個 symbols 的值 → vector(N)
  3. IC_t = rank_correlation(feature_X_values, forward_return_values)
然後：
  IC_mean = mean(IC_t for all t)
  ICIR = IC_mean / std(IC_t)
```

**核心要求**：每個 feature 都要跨所有 symbols 計算，才能得到穩定的 IC 估計。單 symbol IC 容易過擬合。

### 現況問題

```python
# 目前 ic_analysis_service.py cross_sectional mode:
multi_features = self._feature_library.load_multi(request.symbols, request.timeframe)
# → load_multi 會把每個 symbol 的 ALL 435K features 全載入 → OOM
```

**load_multi() 目前是 loop-per-symbol 全量載入**：
- 2 symbols × 435K features × 17,928 rows × 4 bytes = **60 GB** → 必定 OOM
- 100 symbols → **3 TB** → 完全不可能

### 最終方案：Per-Feature Streaming IC

IC 分析不需要同時載入所有 features。正確的做法是 **per-feature iteration**：

```python
def compute_cross_sectional_ic(
    symbols: list[str], 
    config_hash: str,
    label_loader: Callable,  # 載入每個 symbol 的 forward return
) -> dict[str, ICResult]:
    """跨 symbol × 跨 group 的 IC 篩選"""
    
    manifest = load_manifest(symbols[0], config_hash)
    results = {}
    
    # 逐 group 處理（每次只載入一個 group 的 columns）
    for group_name, group_info in manifest["groups"].items():
        feature_names = group_info["columns"]
        
        # 從所有 symbols 載入同一個 group（column projection）
        # 記憶體: N_symbols × group_cols × rows × 2 bytes
        # 最大 group = WorldQuant 25K cols × 100 symbols × 17928 × 2 = 90 GB → 仍太大
        # 所以需要再拆：per-feature 或 per-chunk
        
        for feature_batch in chunk(feature_names, batch_size=100):
            # 100 features × 100 symbols × 17928 rows × 2 bytes = 358 MB ← OK
            cross_data = {}
            for symbol in symbols:
                table = pq.read_table(
                    get_group_path(symbol, config_hash, group_name),
                    columns=feature_batch
                )
                cross_data[symbol] = table.to_pandas()
            
            # 組成 MultiIndex (timestamp, symbol) DataFrame
            frames = []
            for symbol, df in cross_data.items():
                df["_symbol"] = symbol
                frames.append(df)
            stacked = pd.concat(frames).set_index("_symbol", append=True)
            
            # Per-timestamp rank correlation
            for feature in feature_batch:
                ic_series = []
                for timestamp in stacked.index.get_level_values(0).unique():
                    slice_df = stacked.loc[timestamp]
                    if len(slice_df) < 3:  # 至少 3 symbols
                        continue
                    ic, _ = spearmanr(slice_df[feature], slice_df["label"])
                    ic_series.append(ic)
                
                results[feature] = ICResult(
                    ic_mean=np.nanmean(ic_series),
                    ic_std=np.nanstd(ic_series),
                    icir=np.nanmean(ic_series) / (np.nanstd(ic_series) + 1e-8),
                    ic_series=ic_series,
                )
    
    return results
```

### 記憶體預算

| 批次策略 | 100 symbols | 1000 symbols |
|---------|-------------|-------------|
| 100 features × N symbols × 17928 rows × 2B | 358 MB | 3.6 GB |
| 500 features × N symbols × 17928 rows × 2B | 1.8 GB | 18 GB (需分批) |
| 全量 435K → 不可能 | OOM | OOM |

**結論**：IC 篩選採用 per-group + per-batch streaming，batch_size 根據可用記憶體動態調整。

---

## 7. 問題六：SHAP 需要多 Symbol 分析維度

### 現況問題

目前 `shap_analysis_service.py` 只分析**單一 symbol 的模型結果**：

```python
# 現況：只從單一任務結果提取 SHAP
X_sample, feature_names, case_ids_sample = self._prepare_data(task_result, sample_size)
# task_result 來自單一 symbol 的 XGBoost 訓練
```

### 缺少的分析維度

| 分析維度 | 單 Symbol SHAP | 多 Symbol SHAP |
|---------|---------------|---------------|
| 特徵重要性排序 | ✅ 有 | 需要：跨 symbol 穩定性 |
| 特徵交互效應 | ✅ 有 | 需要：是否在不同 symbol 有不同交互 |
| 單案例解釋 | ✅ 有 | 需要：同一時間點不同 symbol 的解釋差異 |
| **跨 Symbol 穩定性** | ❌ 缺 | 「feature_A 在 80% symbols 都重要」→ 真信號 |
| **Symbol-Specific 偏差** | ❌ 缺 | 「feature_B 只在 BTC 重要」→ 可能過擬合 |
| **Regime 差異** | ❌ 缺 | 「牛市 vs 熊市的 feature importance 差異」 |

### 最終方案：Cross-Symbol SHAP Aggregation

```python
def analyze_cross_symbol_shap(
    model,  # 跨 symbol 訓練的 model
    symbols: list[str],
    config_hash: str,
    selected_features: list[str],
    sample_per_symbol: int = 500,
) -> CrossSymbolSHAPResult:
    """多 symbol SHAP 分析"""
    
    per_symbol_shap = {}
    
    for symbol in symbols:
        # 載入該 symbol 的 selected features（column projection）
        X = load_selected_features(symbol, config_hash, selected_features)
        X_sample = X.sample(min(sample_per_symbol, len(X)), random_state=42)
        
        # 計算 SHAP values
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        per_symbol_shap[symbol] = {
            "mean_abs": np.abs(shap_values).mean(axis=0),  # per-feature importance
            "raw": shap_values,
        }
    
    # 聚合分析
    all_importances = np.stack([v["mean_abs"] for v in per_symbol_shap.values()])
    
    return CrossSymbolSHAPResult(
        # 跨 symbol 平均重要性
        global_importance=all_importances.mean(axis=0),
        # 跨 symbol 穩定性（std 越低越穩定 = 越可信）
        stability=all_importances.std(axis=0),
        # 每個 symbol 的個別 importance（抓 symbol-specific bias）
        per_symbol=per_symbol_shap,
        # 「在 80%+ symbols 都排 top-50」的 features
        consensus_features=find_consensus_features(all_importances, threshold=0.8),
    )
```

### 與 IC 篩選的互補

```
IC 篩選 → 「哪些 feature 有預測力？」（統計層面）
SHAP    → 「模型實際用了哪些 feature？怎麼用？」（模型層面）

理想流程：
  1. Cross-symbol IC 篩選 → selected_features (2000)
  2. 跨 symbol 訓練 model → trained_model
  3. Cross-symbol SHAP → 驗證 model 的 feature usage 是否合理
  4. 剔除 symbol-specific bias features → refined_features
  5. 重新訓練 → final_model
```

---

## 8. 問題七：Feature Browser 完整整合

### 現況問題

Feature Browser (`feature_browser_service.py`) 提供 **12 個分析功能**，全部透過 `_load_features_df()` 載入，而該函式只支援 HDF5/CSV：

| 功能 | 方法 | 載入方式 | V7 影響 |
|------|------|---------|---------|
| 特徵概覽 | `get_overview()` | 全量載入 → 逐欄統計 | ❌ OOM on 435K cols |
| IC Dashboard | `get_ic_dashboard()` | 全量載入 → per-feature IC | ❌ OOM |
| Rolling IC | `get_rolling_ic()` | 全量載入 → 單 feature rolling | ❌ 只需 1 column |
| 品質記分卡 | `get_quality_scorecard()` | 全量載入 → ADF + coverage | ❌ OOM |
| 相關矩陣 | `get_correlation_matrix()` | 全量載入 → corr(max 200) | ❌ 只需 200 cols |
| VIF | `get_vif()` | 全量載入 → VIF(max 200) | ❌ 只需 200 cols |
| Drift Monitor | `get_drift_monitor()` | 全量載入 → PSI + KS | ❌ OOM |
| SHAP Summary | `get_shap_summary()` | 全量載入 → proxy importance | ❌ OOM |
| 重要性比較 | `get_importance_comparison()` | 全量載入 → variance/abs rank | ❌ OOM |
| 特徵目錄 | `get_catalog()` | 全量載入 → ADF + stats | ❌ OOM |
| 覆蓋率矩陣 | `get_coverage_matrix()` | `CoverageAnalyzer` HDF5 | ❌ HDF5 不相容 |
| 多 Symbol 覆蓋 | coverage cross-symbol | 逐 symbol HDF5 | ❌ HDF5 不相容 |

**核心問題**：435K columns 全量載入在 8GB 機器上不可能。但大多數功能只需要**部分 columns**或**統計值**。

### 最終方案：分層載入策略

根據功能需求，分為三種載入模式：

#### Mode 1: Metadata-Only（零值載入）

```python
# 特徵目錄、概覽 — 只需 column names + 基礎 stats
def get_overview_v7(symbol: str, config_hash: str) -> Dict:
    manifest = load_manifest(symbol, config_hash)
    
    items = []
    for group_name, group_info in manifest["groups"].items():
        # 從 parquet metadata 讀統計值（不載入資料）
        meta = pq.read_metadata(group_info["file"])
        for i in range(meta.num_columns):
            col_meta = meta.row_group(0).column(i)
            items.append({
                "feature_name": meta.schema.field(i).name,
                "group": group_name,
                "layer": extract_layer(group_name),
                "dtype": str(meta.schema.field(i).type),
                "size_bytes": col_meta.total_compressed_size,
                # parquet statistics (min/max/null_count) 已內建
                "has_statistics": col_meta.statistics is not None,
            })
    
    return {
        "total_features": manifest["total_features"],
        "total_groups": manifest["total_groups"],
        "rows": manifest["rows"],
        "items": items,
    }
```

#### Mode 2: Column-Projected（選擇性載入）

```python
# IC Dashboard, Rolling IC, 相關矩陣, VIF — 需要 column 值但可限制數量
def get_ic_dashboard_v7(symbol: str, config_hash: str, 
                        feature_subset: list[str] = None,
                        top_k: int = 50) -> Dict:
    manifest = load_manifest(symbol, config_hash)
    
    if feature_subset:
        # 用戶指定 features → column projection
        df = load_selected_features(symbol, config_hash, feature_subset)
    else:
        # 全量 IC → per-group streaming（不一次載入全部）
        results = []
        for group_name, group_info in manifest["groups"].items():
            group_df = pq.read_table(group_info["file"]).to_pandas()
            # 逐 group 計算 IC（單 group 最大 25K cols ≈ 900 MB → 勉強可以）
            group_ic = compute_ic_for_group(group_df, target)
            results.extend(group_ic)
            del group_df  # 立即釋放
        
        # 排序取 top_k
        results.sort(key=lambda x: abs(x["ic_mean"]), reverse=True)
        return {"entries": results[:top_k]}
```

#### Mode 3: Cross-Symbol Aggregation（跨 symbol 聚合）

```python
# 覆蓋率矩陣 — 跨 symbols 的 NaN 比率
def get_coverage_matrix_v7(symbols: list[str], config_hash: str,
                           feature_names: list[str]) -> Dict:
    matrix = {}
    for symbol in symbols:
        manifest = load_manifest(symbol, config_hash)
        for feature in feature_names:
            group_file = find_group_for_feature(manifest, feature)
            # 只讀 1 column → 計算 NaN%
            table = pq.read_table(group_file, columns=[feature])
            nan_pct = table.column(0).null_count / len(table)
            matrix.setdefault(feature, {})[symbol] = nan_pct
    return matrix
```

### Feature Browser V7 功能映射

| 功能 | 載入模式 | 記憶體需求 | 備註 |
|------|---------|-----------|------|
| `get_overview()` | Metadata-Only | ~10 MB | 從 parquet metadata + manifest |
| `get_catalog()` | Metadata-Only | ~10 MB | 同上 + ADF 改為 sampling |
| `get_ic_dashboard()` | Per-Group Streaming | ~900 MB peak | 逐 group 計算後釋放 |
| `get_rolling_ic()` | Column-Projected | ~0.1 MB | 只讀 1 column |
| `get_quality_scorecard()` | Per-Group Streaming | ~900 MB peak | ADF + coverage per-group |
| `get_correlation_matrix()` | Column-Projected | ~100 MB | max 200 cols |
| `get_vif()` | Column-Projected | ~100 MB | max 200 cols |
| `get_drift_monitor()` | Per-Group Streaming | ~900 MB peak | PSI + KS per-group |
| `get_shap_summary()` | Column-Projected | 依 model features | 只讀 model 使用的 features |
| `get_importance_comparison()` | Column-Projected | 依 top_k | 只讀指定 features |
| `get_coverage_matrix()` | Cross-Symbol | ~50 MB | per-feature × per-symbol |

---

## 9. 問題八：Immutable Artifact 儲存策略

### 設計原則

1. **Config Hash = 唯一識別**: 同 `scan_config.yaml` + 同 symbol → 同 hash → 不重算
2. **Append-only**: Pipeline 只新增目錄，不覆蓋舊的
3. **手動刪除才消失**: 沒有自動 cleanup（空間不夠時由使用者決定刪哪些）
4. **完整 Lineage**: manifest.json 記錄完整生成資訊

### 目錄結構

```
data_cache/features/
├── ETHUSDT/
│   ├── 18228376bf79e867590ecee84f1f3a16/   ← config_hash A
│   │   ├── manifest.json                    ← 生成資訊 + feature→group 映射
│   │   ├── 1h_L1_trend_EMA.parquet
│   │   ├── 1h_L2_WorldQuant.parquet
│   │   └── ...708 files (float16, immutable)
│   └── {another_config_hash}/              ← 改了 config → 新目錄
│       └── ...
├── BTCUSDT/
│   └── 18228376bf79e867590ecee84f1f3a16/   ← 同 config → 同 hash
│       └── ...
└── _index/                                  ← 全域索引（未來）
    └── feature_catalog.parquet
```

### manifest.json 結構（草案）

```json
{
  "version": "7.0",
  "symbol": "ETHUSDT",
  "config_hash": "18228376bf79e867590ecee84f1f3a16",
  "created_at": "2026-04-19T06:19:49",
  "pipeline_version": "V6.2-CGSA",
  "dtype": "float16",
  "timeframes": ["1h", "12h"],
  "total_features": 435389,
  "total_groups": 708,
  "rows": 17928,
  "time_range": {
    "start": "2024-01-01T00:00:00",
    "end": "2026-04-18T23:00:00"
  },
  "layer_counts": {
    "L1": 1611, "L2": 46677, "L3": 156920,
    "L4": 12912, "L5": 0, "L6": 11,
    "L1_12h": 1611, "L2_12h": 46677, "L3_12h": 156047,
    "L4_12h": 12912, "L5_12h": 0, "L6_12h": 11
  },
  "groups": {
    "1h_L1_trend_EMA": {
      "file": "1h_L1_trend_EMA.parquet",
      "columns": ["close_trend_EMA_5", "close_trend_EMA_8", "..."],
      "num_columns": 45,
      "size_bytes": 3145728
    }
  },
  "preprocessing": {
    "transforms": ["winsorize", "rank", "zscore"],
    "rank_window": 252,
    "winsorize_limits": [0.01, 0.99]
  },
  "config_snapshot": {
    "scan_config_path": "config/scan_config.yaml",
    "indicators_path": "config/indicators.yaml"
  }
}
```

### Training Pipeline Metadata（草案）

```json
{
  "pipeline_id": "train_20260419_001",
  "created_at": "2026-04-19T12:00:00",
  "symbols": ["ETHUSDT", "BTCUSDT", "SOLUSDT"],
  "config_hash": "18228376bf79e867590ecee84f1f3a16",
  "selected_features": ["feat_1", "feat_2", "..."],
  "selection_method": "ic_filter",
  "ic_threshold": 0.03,
  "label": "fwd_return_12h",
  "dtype": "float16",
  "note": "V6.2 baseline"
}
```

---

## 10. 問題九：硬體升級自動加速設計

### 設計原則

架構中所有可平行化的環節都應該**自動感知硬體資源**，不需要改程式碼就能利用更好的硬體：

### 需要參數化的瓶頸

| 瓶頸 | 目前限制 | 參數化方式 |
|------|---------|-----------|
| **L6.5 Preprocessing** (54.7% 時間) | Numba `parallel=True` 受 CPU 核心數限制 | `numba.config.NUMBA_NUM_THREADS` = `os.cpu_count()` |
| **Per-group Parquet I/O** | 逐 group 串行讀寫 | Thread pool size = `min(cpu_count, group_count)` |
| **IC Streaming batch_size** | 固定值 | `batch_size = available_ram // (n_symbols × rows × 2)` |
| **Feature Factory L3 rolling** | Numba chunk 大小固定 | Chunk size = `available_ram // (2 × dtype_size)` |
| **Training Matrix 合併** | Per-symbol 逐一讀取 | Parallel read with `ThreadPoolExecutor(max_workers=cpu_count)` |

### 資源感知配置

```python
# momentum/core/resource_config.py（新增）
import os
import psutil

class ResourceConfig:
    """自動感知硬體資源，提供最佳化參數"""
    
    @staticmethod
    def cpu_count() -> int:
        return os.cpu_count() or 4
    
    @staticmethod
    def available_ram_bytes() -> int:
        return psutil.virtual_memory().available
    
    @staticmethod
    def available_ram_gb() -> float:
        return psutil.virtual_memory().available / (1024**3)
    
    @classmethod
    def ic_batch_size(cls, n_symbols: int, n_rows: int, dtype_bytes: int = 2) -> int:
        """動態計算 IC streaming 的 batch size"""
        ram = cls.available_ram_bytes()
        # 使用 60% 可用記憶體
        budget = int(ram * 0.6)
        per_feature = n_symbols * n_rows * dtype_bytes
        return max(10, budget // per_feature)
    
    @classmethod
    def io_workers(cls) -> int:
        """I/O 平行度"""
        return min(cls.cpu_count(), 16)
    
    @classmethod
    def numba_threads(cls) -> int:
        """Numba 平行線程數"""
        return cls.cpu_count()
```

### 硬體升級效果預估

| 升級 | 影響環節 | 預估加速 |
|------|---------|---------|
| 8 核 → 16 核 | L6.5 numba, Parquet I/O, IC streaming | ~1.5-1.8x |
| 8 GB → 32 GB RAM | IC batch_size ↑, 可 handle 更多 symbols 同時 | batch_size 4x → throughput ~3x |
| SSD → NVMe | Parquet 讀寫 | ~2-3x I/O |
| 外接 GPU (CUDA) | L6.5 rank/zscore（未來 CuPy path） | ~5-10x（需新增 code path） |

### GPU 加速路徑（預留）

L6.5 preprocessing 是目前最大瓶頸（54.7%）。Numba CUDA 或 CuPy 可以加速 rolling rank/zscore：

```python
# 未來 GPU path（預留介面，不立即實作）
def preprocess_group(data: np.ndarray, window: int) -> np.ndarray:
    if gpu_available() and data.shape[1] > 1000:
        return _preprocess_gpu(data, window)  # CuPy/Numba CUDA
    else:
        return _preprocess_cpu(data, window)   # 現有 Numba CPU
```

**結論**：所有平行化參數從 `ResourceConfig` 讀取，硬體升級自動生效。GPU 預留介面但不立即實作。

---

## 11. 分層儲存架構設計（最終方案）

### 三層架構

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Training-Ready Matrix                          │
│  data_cache/ml_pipelines/{pipeline_id}/                  │
│  ├── train.parquet (selected features × all symbols)     │
│  ├── metadata.json (symbol list, features, config)       │
│  └── shap_summary.json (cross-symbol SHAP results)       │
│  大小: ~7 GB (2000 cols × 17928 rows × 100 symbols)     │
│  用途: LightGBM/XGBoost/Optuna/SHAP 直接讀取             │
├─────────────────────────────────────────────────────────┤
│  Layer 2: IC-Filtered Feature Index                      │
│  data_cache/features/_index/{config_hash}/               │
│  ├── ic_results.parquet (全 features × 全 symbols IC)    │
│  ├── selected_features.json (篩選後 500~2000 特徵)       │
│  └── feature_catalog.parquet (全域特徵名 + stats)        │
│  大小: < 100 MB                                          │
│  用途: Feature Browser, 跨 symbol 特徵選擇               │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Raw Feature Store (immutable, per-symbol)      │
│  data_cache/features/{symbol}/{config_hash}/             │
│  ├── manifest.json (必要)                                │
│  ├── columns.json.gz (全部 feature names, 壓縮)          │
│  └── {tf}_{layer}_{group}.parquet (float16)              │
│  大小: ~15 GB/symbol (float16)                           │
│  用途: IC 分析、特徵探索、reproducibility                  │
└─────────────────────────────────────────────────────────┘
```

### 下游完整需求矩陣

| 下游 | 跨指標？ | 跨 Symbol？ | 讀取 Layer | 載入模式 |
|------|---------|------------|-----------|---------|
| **Feature Browser — Overview** | ✅ 全部 | 單 symbol | L1 manifest | Metadata-Only |
| **Feature Browser — Catalog** | ✅ 全部 | 單 symbol | L1 manifest | Metadata-Only |
| **Feature Browser — IC Dashboard** | ✅ 全部 | 單 symbol | L1 per-group | Per-Group Streaming |
| **Feature Browser — Rolling IC** | 單 feature | 單 symbol | L1 column | Column-Projected |
| **Feature Browser — Quality** | ✅ 全部 | 單 symbol | L1 per-group | Per-Group Streaming |
| **Feature Browser — Correlation** | top 200 | 單 symbol | L1 column | Column-Projected |
| **Feature Browser — VIF** | top 200 | 單 symbol | L1 column | Column-Projected |
| **Feature Browser — Drift** | ✅ 全部 | 單 symbol | L1 per-group | Per-Group Streaming |
| **Feature Browser — Coverage** | 指定 features | ✅ 多 symbols | L1 column | Cross-Symbol |
| **IC Analysis (single)** | ✅ 全部 | 單 symbol | L1 per-group | Per-Group Streaming |
| **IC Analysis (cross-sectional)** | ✅ 全部 | ✅ 全部 symbols | L1 per-group | Per-Feature Streaming |
| **LightGBM/XGBoost** | selected | 單 or 多 | L3 | Direct Read |
| **Cross-symbol Training** | selected | ✅ 多 symbols | L3 | Direct Read |
| **Optuna** | per-trial subset | 單 or 多 | L3 | Column-Projected |
| **SHAP (single)** | model features | 單 symbol | L3 or L1 | Column-Projected |
| **SHAP (cross-symbol)** | model features | ✅ 多 symbols | L3 | Per-Symbol Iteration |

### 讀取模式定義

```
Metadata-Only:
  manifest.json + parquet metadata → 零資料 I/O

Column-Projected:
  manifest.json → 找到 group file → pq.read_table(columns=[...])
  記憶體: selected_cols × rows × 2 bytes

Per-Group Streaming:
  manifest.json → 逐 group 載入 → 計算 → 釋放 → 下一個 group
  記憶體: max_group_cols × rows × 2 bytes (peak ~900 MB for WorldQuant)

Per-Feature Streaming:
  manifest.json → 逐 group → 逐 feature batch → 跨 symbols 載入
  記憶體: batch_size × n_symbols × rows × 2 bytes (動態調整)

Cross-Symbol:
  Per-symbol column projection → stack/aggregate
  記憶體: n_symbols × selected_cols × rows × 2 bytes

Direct Read:
  Layer 3 train.parquet → 已合併好的訓練矩陣
  記憶體: selected_features × rows × n_symbols × 2 bytes
```

### 統一讀取介面

```python
# momentum/FeatureEngineering/feature_reader.py（新增）

class FeatureReader:
    """V7 統一特徵讀取介面 — 只支援 Parquet，不支援 HDF5"""
    
    def __init__(self, feature_base_path: str = "data_cache/features"):
        self._base = Path(feature_base_path)
    
    def load_manifest(self, symbol: str, config_hash: str) -> dict:
        """載入 manifest.json"""
        path = self._base / symbol / config_hash / "manifest.json"
        return json.loads(path.read_text())
    
    def list_features(self, symbol: str, config_hash: str) -> list[str]:
        """列出所有 feature names（不載入資料）"""
        manifest = self.load_manifest(symbol, config_hash)
        return manifest.get("all_columns", [])
    
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
    
    def stream_groups(self, symbol: str, config_hash: str
                      ) -> Iterator[tuple[str, pd.DataFrame]]:
        """逐 group 串流（計算完釋放記憶體）"""
        manifest = self.load_manifest(symbol, config_hash)
        for group_name, group_info in manifest["groups"].items():
            path = self._base / symbol / config_hash / group_info["file"]
            df = pq.read_table(str(path)).to_pandas()
            yield group_name, df
            del df
    
    def load_cross_symbol(self, symbols: list[str], config_hash: str,
                          columns: list[str]) -> pd.DataFrame:
        """跨 symbol 載入同一組 columns → MultiIndex"""
        frames = []
        for symbol in symbols:
            df = self.load_columns(symbol, config_hash, columns)
            df["_symbol"] = symbol
            frames.append(df)
        result = pd.concat(frames)
        return result.set_index("_symbol", append=True)
```

### 完整資料流

```
                    ┌──────────────┐
                    │  Pipeline    │
                    │  (V6.2+)     │
                    └──────┬───────┘
                           │ float16 parquet + manifest.json
                           ▼
              ┌────────────────────────────┐
              │  Layer 1: Feature Store     │
              │  (immutable, per-symbol)    │
              └────────────┬───────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
   ┌─────────────┐ ┌────────────┐ ┌─────────────┐
   │ Feature     │ │ IC Analysis│ │ Coverage     │
   │ Browser     │ │ (cross-    │ │ Analyzer     │
   │ (12 funcs)  │ │ symbol)    │ │ (cross-sym)  │
   └─────────────┘ └─────┬──────┘ └─────────────┘
                         │
                         │ IC results
                         ▼
              ┌────────────────────────────┐
              │  Layer 2: IC Index          │
              │  (selected_features.json)   │
              └────────────┬───────────────┘
                           │
                           │ column projection (selected only)
                           ▼
              ┌────────────────────────────┐
              │  Layer 3: Training Matrix   │
              │  (cross-symbol, selected)   │
              └────────────┬───────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
   ┌─────────────┐ ┌────────────┐ ┌─────────────┐
   │ LightGBM/   │ │ Optuna     │ │ SHAP        │
   │ XGBoost     │ │ (per-trial │ │ (cross-     │
   │ Training    │ │  subset)   │ │  symbol)    │
   └─────────────┘ └────────────┘ └─────────────┘
```

---

## 12. 行動優先順序

### P0 — 必要（下游才能用）

| # | 項目 | 內容 | 影響 |
|---|------|------|------|
| 1 | **manifest.json 寫入** | `feature_storage.py` persist 結束後寫入 output_dir（含 groups → columns 映射 + `columns.json.gz`） | 所有讀取依賴 |
| 2 | **float16 儲存** | `persist_registry_to_parquet` 寫入時 cast to float16 | 空間省 50%，36.6→18.3 GB |
| 3 | **FeatureReader 統一介面** | 新增 `momentum/FeatureEngineering/feature_reader.py`（只支援 Parquet，移除 HDF5） | 所有下游統一入口 |
| 4 | **FeatureLibrary 改造** | `load()` / `load_multi()` 改用 FeatureReader，移除 h5py | 下游直接可用 |

### P1 — 核心分析功能

| # | 項目 | 內容 | 影響 |
|---|------|------|------|
| 5 | **Cross-symbol IC streaming** | per-group + per-batch 跨 symbol IC 計算 | 正確的 IC 篩選 |
| 6 | **Feature Browser 改造** | 12 個函式改用 FeatureReader（Metadata/Streaming/Projection 三模式） | Browser 可用 |
| 7 | **ResourceConfig** | 自動感知 CPU/RAM，動態調整 batch_size/workers | 硬體升級自動生效 |

### P2 — 訓練流程

| # | 項目 | 內容 | 影響 |
|---|------|------|------|
| 8 | **Layer 2 IC Index** | IC 篩選結果 → `_index/{config_hash}/ic_results.parquet` + `selected_features.json` | 訓練流程入口 |
| 9 | **Layer 3 Training Matrix** | selected features × all symbols → `ml_pipelines/{id}/train.parquet` | ML 直接讀取 |
| 10 | **Cross-symbol SHAP** | 多 symbol SHAP aggregation + stability analysis | 特徵驗證 |

### P3 — 擴展

| # | 項目 | 內容 | 影響 |
|---|------|------|------|
| 11 | **外接儲存路徑** | `feature_base_path` 可設定為外接 SSD/NAS | 100+ symbols |
| 12 | **Batch Pipeline** | 多 symbol 批次 feature generation | 大規模研究 |
| 13 | **Group 合併** | 556 個 <1MB 小檔合併成少數大檔 | I/O 效率 |
| 14 | **GPU 預留介面** | L6.5 preprocessing GPU code path | 未來加速 |

---

## 13. 決議紀錄

### 已決定

1. **manifest.json 的 columns 清單大小** → **方案 A**
   - manifest.json 只存 `group → {file, column_count}` 映射
   - 另有 `columns.json.gz` 存完整 435K+ feature names（壓縮後 < 1 MB）
   - 理由：manifest.json 保持 < 100 KB，JSON parse 快速；完整清單用 gzip 壓縮獨立存放

2. **Layer 3 Training Matrix 何時建立** → **方案 A（用戶觸發）**
   - IC 篩選後由用戶設定 threshold → 觸發 Training Matrix 生成
   - 理由：IC threshold 是研究決策，不應自動化。不同研究需求可能設不同 threshold

3. **現有 36.6 GB float32 資料處理** → **刪除重跑**
   - 現有特徵因子檔案都是測試產生，直接刪除
   - 下次 pipeline 直接寫 float16 → 驗證 float16 完整流程正確性
   - 效能基準已記錄於 V6.2（64.1 min），可作為 float16 pipeline 的比較基準

4. **CoverageAnalyzer 的 HDF5 reader** → **直接改用 FeatureReader**
   - First Principle：系統只維護一套讀取介面（FeatureReader, Parquet-only）
   - CoverageAnalyzer 被 Feature Browser `get_coverage_matrix()` 呼叫 → 一併在 §8 Feature Browser 改造中完成
   - 移除 `_resolve_feature_file_path()` 的 `.h5` 硬編碼，改為 FeatureReader manifest-based 路徑

5. **Per-Group Streaming 最大 group 問題** → **persist 時限制 `max_group_columns = 5000`**
   - First Principle：streaming peak memory = 最大 group 大小。若佔可用 RAM 20%+，就不是好的 streaming 設計
   - WorldQuant 25,776 cols → 單 group 900 MB → 8 GB Mac 可用 ~4 GB → 22%（邊界危險）
   - 多個分析任務同時 stream → 2× peak → OOM 風險
   - 結論：persist 時自動拆分超過 5000 cols 的 group → 5000 × 17928 × 2B = 172 MB/sub-group
   - 拆分是**一次性成本**（pipeline 跑一次），讀取時**永遠受益**
   - 拆分後命名：`{tf}_{layer}_{group}_part1.parquet`, `{tf}_{layer}_{group}_part2.parquet`

### 開放問題結論

1. **L6.5 GPU 加速 ROI** → **不優先，Phase 4 Polars 是正確路徑**
   - L6.5 的 rolling rank/zscore 是 per-column sequential window operation
   - GPU 擅長 large matrix parallel ops，不擅長 sequential sliding window
   - Phase 4 Polars（Rust native parallelism）是更好的加速路徑
   - GPU 只在 ML training（matrix multiplication）才有顯著 ROI
   - 結論：§10 `ResourceConfig` 預留 GPU 介面，但不排入 P0-P2

2. **708 groups 粒度** → **不需重新設計策略，但需矯正大小差異**
   - 問題不在 group 數量（708 可以），而在大小差異太大（<1 MB ~ 2.2 GB）
   - 解法已在 P3 行動項中：
     - 合併 556 個 <1 MB 小檔（減少 I/O overhead）
     - 拆分 WorldQuant >5000 cols（上方決議 #5）

3. **Cross-sectional IC @ 1000 symbols** → **可接受，~7 min**
   - Per-feature streaming: 100 features × 1000 symbols × 17928 × 2B = 3.4 GB
   - 8 GB Mac 需降為 batch_size=50（`ResourceConfig` 自動計算）
   - I/O 估算：column projection ~1 ms/read → 435K features ÷ 50 = 8700 batches × 1000 reads = 8.7M reads
   - 但 column projection 只讀 1 group file per batch → 實際 ~8700 × 1 read = ~9 seconds I/O + 計算
   - 總估算 ~7 min（含 rank correlation 計算）→ 可接受

4. **Feature Browser ADF test @ 435K features** → **Lazy 執行，不做 batch 全量**
   - 0.05 s/feature × 435K = 21,750 s ≈ **6 hours** → 不可接受
   - 結論：ADF test 只在 Feature Browser drill-down（用戶點擊單一 feature）時 lazy 執行
   - Overview / Dashboard 層級用 cheaper proxies：variance ratio, autocorrelation lag-1
   - 若用戶需要 batch stationarity 報告 → 抽樣（每 group 10% features）

---

## 附錄：相關檔案

### 需要修改的檔案

| 檔案 | 改動 |
|------|------|
| `momentum/FeatureEngineering/feature_storage.py` | float16 persist + manifest.json 寫入 |
| `momentum/FeatureEngineering/feature_library.py` | 改用 FeatureReader，移除 h5py |
| `api/services/feature_browser_service.py` | 12 個函式改用 FeatureReader（三種載入模式） |
| `api/services/ic_analysis_service.py` | cross-sectional IC 改為 per-feature streaming |
| `api/services/shap_analysis_service.py` | 新增 cross-symbol SHAP aggregation |
| `api/services/cross_symbol_training_service.py` | 改用 FeatureReader + Layer 3 |
| `api/services/xgboost_task_service.py` | 改用 FeatureReader |
| `momentum/Analysis/coverage_analyzer.py` | 移除 HDF5 reader，改用 FeatureReader |

### 需要新增的檔案

| 檔案 | 用途 |
|------|------|
| `momentum/FeatureEngineering/feature_reader.py` | V7 統一讀取介面（Parquet-only） |
| `momentum/core/resource_config.py` | 硬體資源自動感知 |

### 參考檔案（不需修改）

| 檔案 | 用途 |
|------|------|
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | L3 rolling rank 實現 |
| `momentum/FeatureEngineering/preprocessing/_numba_transforms.py` | L6.5 rank transform 實現 |
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | L6.5 orchestrator |
| `momentum/Analysis/ic_engine.py` | IC 計算核心 |
| `momentum/Analysis/shap_analyzer.py` | SHAP 分析核心 |
| `scripts/profile_gate3_to_4_full.py` | V6.2 Pipeline 執行腳本 |
| `config/scan_config.yaml` | Feature Factory 設定 |
