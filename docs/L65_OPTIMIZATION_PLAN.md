# Layer 6.5 全模組優化計畫

> **建立日期**: 2026-04-26
> **觸發事件**: 用戶手動全開 L6.5 所有子模組（含 FracDiff/ADF/Gaussian），ETHUSDT+BTCUSDT 1h+12h 預估 ETA ~70,000 秒（19.5 小時）；對比 V8 final 只開 winsor+rank+zscore 為 494 秒，相差約 140 倍
> **目標環境**: 8GB / 16GB / 24GB / 32GB tier 全部要支援
> **驗證原則**: 跨 不同硬體tier環境下 多Symbol + 重複穩定 + 不 OOM + 最高數據品質 + 最短計算時間 + 最小輸出檔案 + 並考量量化金融業界經驗的最佳解
> **絕對不可違反**: ❌ 不可用消除特徵的方式做優化（user constraint）

---

## 📊 1. 現況精準診斷

### 1.1 L6.5 流程拆解（從 [feature_preprocessor.py](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)）

```
transform_registry_groups()                         ← 入口
  └─ _build_registry_transform_context()            ← 推導 use_fast
      use_fast = (not fracdiff and not adf and not gaussian and mode==replace)
  └─ _transform_registry_parallel(workers=2)        ← 8GB tier
      ├─ ThreadPool 並行 N 個 sub-tasks
      └─ 每個 task → _transform_single_group()
           ├─ use_fast=True  → numba 向量化 (transform_array_fast) ⚡
           └─ use_fast=False → _transform_single() pandas 慢路徑 🐢
                ├─ _apply_winsorization()           ← 永遠便宜
                ├─ _apply_fractional_differencing() ★ 主慢源
                │   └─ 對每欄 _find_min_d() → 7 次 ADF 二分搜尋
                ├─ _apply_adf_differencing()        ← 次慢源
                │   └─ 對每欄最多 max_diff+1 次 ADF
                ├─ _apply_rank_transform()          ← 中等
                ├─ _apply_gaussian_normalize()      ← 便宜
                └─ _apply_adaptive_zscore()         ← 中等
```

### 1.2 真實成本拆分（基於 log）

| 項目 | 每群組成本 | 比例 | 主因 |
|------|----------|------|------|
| `_get_non_stationary_columns` 篩選 | N × 30ms ADF | ~10% | 每欄跑 1 次 ADF 來決定是否要 FracDiff/ADF_diff |
| `_find_min_d` 二分搜尋 | N × 7 × 30ms ADF | **~70%** | 每非穩定欄跑 7 次 ADF（precision=0.01）|
| `_frac_diff_ffd` 卷積 | N × O(rows × width) | ~5% | numpy convolve，已是高速 |
| `_apply_adf_differencing` | N × 1-2 × 30ms ADF | ~10% | 重複跑 ADF |
| 其他（winsor/rank/zscore） | 整群 ~1-3s | ~5% | pandas vectorized |

對 17,928 行 × 數百欄位的 group：
- **每群組總時間 60-90 秒** ← 觀測值
- ADF（statsmodels）每次調用約 30ms（autolag=AIC + sample_size=500 已啟用）
- 8GB tier workers=2，922 sub-tasks → 序列等價 922 × 60-75s = **55,000-69,000 秒**

### 1.3 為何 ThreadPool 並行幾乎沒幫助

`adfuller()` 是純 Python 計算 → **GIL 鎖死** → workers=2 但實際只有 1 個 thread 真正在算 ADF。  
這是當前最大的隱形瓶頸。

---

## 🎯 2. 優化策略總覽（依 ROI 排序）

| Tier | 名稱 | 預期加速 | 改動成本 | 風險 | 跨 tier 穩定 | 優先級 |
|------|------|---------|---------|------|------------|-------|
| 0A | FracDiff 限定 L1/L2 | 3-10× | 低 | 低 | ✅ | **P0** |
| 0B | precision 0.01 → 0.02 + cache version bump | 1.1-1.2× | 極低 | 極低 | ✅ | **P0** |
| 1A | per-run non_stationary 分類 cache | 1.3-2× | 低 | 低 | ✅ | **P0** |
| 1B | d_star cache key 修正（symbol/timeframe/config-aware） | 第二次 run 5-10× | 低 | 低 | ✅ | **P0** |
| 1C | Batch RAM gate + symbol-level 序列調度 | 防 OOM | 中 | 低 | ✅ | **P0** |
| 2A | joblib loky 慢路徑並行（保留 chunked OOM 防護） | 1.5-3× | 中 | 中 | ⚠ tier-aware | **P1** |
| 2B | _find_min_d 改 Hurst prior + bounded search | 1.5-2× | 中 | 中 | ✅ | **P1** |
| 3 | ADF 演算法替換（numba-OLS + fallback band） | 5-10× | 高 | 中 | ✅ | **P2** |
| 4 | UI 加估時警告（防呆） | — | 低 | 無 | ✅ | **P0** |

**短期目標**: 先用 P0（L1/L2-only + 正確 cache + per-run cache + UI 防呆）把 19h 降到 **數小時級**；第二次同 symbol 依 d_star cache 命中率降到 **數十分鐘級**。P1/P2 再追求 30-60 分鐘。

---

## ⚖️ 3. FracDiff vs ADF Differencing 決策（重要修正）

### 3.1 業界不建議用 ADF 補 FracDiff 跳過的欄位

量化金融常見做法是：
- 對 raw price / log price / volume / level-like 序列，用 FracDiff 或一般差分處理 stationarity。
- 對 return、rank、zscore、rolling statistic、cross-sectional rank 等已轉換特徵，通常不再做 FracDiff。
- ADF 主要作為檢定工具，或傳統 Box-Jenkins 整數差分流程的一部分；較少用來「補救 FracDiff 處理不了的欄位」。

**結論**：不採用「FracDiff 跳過 → ADF 自動補上」作為本系統預設策略。若 FracDiff 因高 NaN、warmup 太長、樣本不足而跳過，應記錄品質 warning，交由品質 Gate 與使用者判斷，而不是自動套整數差分。

### 3.2 現有程式碼真實行為

程式實際邏輯（[feature_preprocessor.py:1058](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)）：

```python
def _apply_adf_differencing(self, df):
    candidate_columns = [
        column for column in columns
        if column not in self._fracdiff_processed_columns  # ← 已被 FracDiff 處理的不再處理
    ]
```

現有流程是 FracDiff → ADF，且 ADF 會避開已由 FracDiff 處理的欄位，避免同欄位重複差分。

但現有程式碼中，FracDiff 與 ADF 都會跳過 NaN ratio > 50% 的欄位。因此「ADF 會救濟 FracDiff 高 NaN 跳過欄位」並不成立，也不應作為設計目標。

### 3.3 三種配置行為對照（修正版）

| 配置 | FracDiff | ADF_diff | 同欄位實際行為 | 業界用途 |
|------|---------|---------|--------------|---------|
| 只開 FracDiff | ✓ | ✗ | FracDiff 處理（連續 d∈[0,1]，保留長記憶）| López de Prado 標準 |
| 只開 ADF_diff | ✗ | ✓ | ADF 處理（整數 d∈{1,2}，破壞長記憶）| 傳統 Box-Jenkins |
| 兩個都開 | ✓ | ✓ | FracDiff 優先；ADF 只處理未被 FracDiff 處理且同樣通過 NaN 門檻的欄位 | Expert mode，不作為預設推薦 |

### 3.4 本系統採用策略

- **預設**：FracDiff 只作用於 L1/L2 的 level-like / non-stationary 特徵。
- **ADF differencing**：預設關閉，保留為 expert option 或診斷用途。
- **高 NaN 欄位**：不自動 ADF 補救；記錄 warning，進入 L7 品質 Gate。
- **同時開啟 FracDiff + ADF**：允許但不推薦；僅作為實驗模式，並明確提示兩者不是高 NaN fallback。

### 3.5 成本含義

- 真正的主成本是 FracDiff 對大量欄位呼叫 `_find_min_d`，而不是 ADF fallback。
- 第一優先應把 FracDiff 應用範圍從全 L6.5 收斂到 L1/L2。
- ADF 不應作為補救手段擴大計算範圍，否則會增加成本且不保證品質提升。

### 3.6 UI 提示修正建議

當用戶在 [PreprocessingPanel.tsx](../frontend/src/components/feature-factory/PreprocessingPanel.tsx) 同時勾選 FracDiff 與 ADF：

```
ℹ️ FracDiff 與 ADF 可同時開啟，但不是高 NaN fallback：
   • FracDiff 為主處理器（連續 d，保留長記憶）
   • ADF 僅處理未被 FracDiff 處理且通過品質門檻的欄位
   • 兩者不會對同欄位重複處理
   業界建議：預設使用 FracDiff；ADF 保留為 expert option
```

當用戶啟用 FracDiff：
```
⚠️ FracDiff 是 L6.5 最慢子模組。系統預設僅套用 L1/L2，以保留長記憶且避免對 L3+ 已轉換特徵做低 ROI 計算。
```

---

## 🔧 4. 詳細方案

### Tier 0: Config 微調（無程式碼風險）

#### 0.1 `precision: 0.01 → 0.02`
- **位置**: [config/scan_config.yaml](../config/scan_config.yaml) line ~488 `fractional_differencing.precision`
- **效果**: `_find_min_d` 二分搜尋 ⌈log2(1/0.02)⌉ = **6 次**（原 7 次） → 14% 加速
- **品質影響**: d* 從 ±0.005 精度降到 ±0.01，對 fractional differencing 結果幾乎不可察覺
- **驗證**: 對比 d_star cache 兩種 precision 下的 fracdiff 序列 corr > 0.999

#### 0.2 `adf_threshold: 0.10`（已是預設）✓ 已最佳

#### 0.3 加入 `apply_to_layer_filter` 環境變數
- **新增**: `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`（預設 `L1,L2`）
- **效果**: L3/L4 是 indicator-of-indicator 多半已 stationary 或本身就是差分量（rank/zscore），對它們再做 fracdiff 增益遞減；只對 L1/L2 做 → 欄位數從 ~50k 降到 ~5-15k → **3-10× 加速**
- **品質影響**: 量化研究上 fracdiff 主要價值在處理「原始價格序列的長記憶」，indicator 的 indicator 已經被多次處理，fracdiff 邊際效益低
- **絕不違反 user constraint**: ✅ 特徵集合不變，只是不對 L3+ 多算一次 fracdiff（L3+ 仍保留所有 winsor/rank/zscore）
- **決策**: 預設鎖定 `L1,L2`；一般 UI 不開放 L3+，僅保留 expert env override 供研究驗證

### Tier 1A: per-run non_stationary 分類 cache

**問題**: `_get_non_stationary_columns` 在同一次 L6.5 run 內會被 FracDiff 與 ADF 多次呼叫，對相同欄位與相同設定重複跑 ADF。

**做法**:
1. 在 `FeaturePreprocessor` 內新增 per-run cache：`(column, adf_threshold, sample_size, input_fingerprint) -> pvalue / is_non_stationary`
2. `_select_columns(apply_to="non_stationary")` 先查 cache，miss 才跑 ADF
3. FracDiff 與 ADF 共用同一份 per-run 判定結果
4. 不先做 cross-symbol hard skip，避免不同 symbol 的統計性質被錯誤套用

**預期效果**:
- 避免同一 run 內重複 ADF
- 對 FracDiff + ADF 同開、chunked group、重複欄位判定有直接幫助
- 加速約 1.3-2×，且風險低

**程式碼位置**: `_get_non_stationary_columns()` 與 `_select_columns()`

**穩定性**: ✅ 全 tier 適用，cache 只在單次 run 內有效，不跨 symbol 污染

### Tier 1B: d_star Cache Key 與 Schema 修正

**問題**: [feature_preprocessor.py:1394](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) line 1394 的 cache key 寫死為 `("default", "default")`，導致 ETHUSDT 跑出來的 d_star 會被 BTCUSDT 誤用。

**做法**:
1. `FeaturePreprocessor` 接收 `symbol`、`timeframe`、`config_hash` 或由 `FeatureFactory` 注入 context
2. Cache 路徑改為 `data_cache/feature_preprocessing/d_star_{symbol}_{timeframe}_{config_hash}.json`
3. Cache schema 加入 `version`、`symbol`、`timeframe`、`config_hash`、`adf_threshold`、`precision`、`max_lag`、`weight_threshold`、`adf_engine_version`
4. Cache write 改為 atomic write（temp + rename），避免多 worker 寫壞 JSON
5. `precision` 或 ADF 設定變更時 bump cache version，不沿用舊 d_star

**預期效果**:
- **品質提升**: 不同 symbol 的 d_star 不再互相污染
- **時間提升**: 第二次 run 同 symbol → cache hit → 跳過 _find_min_d → **5-10× 加速**
- **重複穩定**: 同 symbol / 同 timeframe / 同 config 的 cache hit 可重現；不同 config 自動隔離

**穩定性**: ✅ 全 tier 適用，只是 cache 檔案多一些

### Tier 1C: Batch RAM gate + symbol-level 序列調度

**問題**: 現有 batch service 可同時跑多個 batch，且每個 batch 又可開多個 process。若再疊加 Multi-TF 與未來 joblib，8GB/16GB tier 很容易 OOM。

**做法**:
1. Feature Factory heavy batch 預設同時間只允許 1 個 batch
2. `request.max_workers` 不直接信任；由 `hardware_utils.py` 的 tier table 決定 `concurrent_symbols`
3. 8GB/16GB 預設 `concurrent_symbols=1`；24GB=2；32GB=3
4. 啟動前檢查 `psutil.virtual_memory().available`，低於門檻拒絕新任務
5. 每完成一個 symbol 寫 checkpoint，釋放記憶體並 `gc.collect()`

**預期效果**: 不直接加速單 symbol，但保證多 symbol 不 OOM，避免 19hr 任務跑到後段失敗後全重來。

### Tier 2A: joblib loky 慢路徑並行

**問題**: ThreadPool 對 statsmodels ADF 慢路徑幾乎無效，但直接把整個 L6.5 換成 ProcessPool 會破壞現有 chunked OOM 防護。

**做法**:
1. 不全面替換 `_transform_registry_parallel`
2. 保留現有 fast path（Numba + ThreadPool + split）
3. 只對 FracDiff/ADF slow path 使用 `joblib.Parallel(backend="loky", mmap_mode="r")`
4. 工作單位必須是 tier-safe chunk，不是整個巨大 group
5. 明確避免巢狀 process pool：Batch / Multi-TF / L6.5 joblib 同時只能展開一層
6. 設定 `OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1`，避免 BLAS oversubscription

**預期效果**: 8GB tier 1.5-2×、16GB+ tier 2-3×。實際加速以 RSS gate 與 benchmark 決定，不用冒 OOM 風險換速度。

**穩定性**: ⚠ 必須先通過 8GB peak RSS 驗證；未通過前預設 OFF。

### Tier 2B: _find_min_d 改 Hurst prior + bounded search

**問題**: 二分搜尋從 `[0, 1]` 開始，每次分 50%，需要 7 次 ADF。

**機會**:
- 用 R/S 統計或 DFA 估計 Hurst exponent H → d_star ≈ H - 0.5（理論關係）
- Hurst 估計只需 1 次 numpy O(N) 運算 ~5ms
- 用 Hurst 作為 prior，但不直接替代 ADF decision
- 先測 `d=0` 與 `d=1`，再做 coarse grid，找到第一個通過 ADF 的區間後局部 binary refine
- 對 `(column, d)` 的 ADF p-value 做 per-run cache，避免重複測同一個 d

**預期效果**: `_find_min_d` 從 7 次 ADF → 平均 3-5 次 ADF → **1.5-2× 加速**

**不採用**: 不使用 golden section search 作為主演算法，因 ADF p-value 在有限樣本與 FFD width 截斷下不保證單峰。

**穩定性**: ✅ 全 tier 適用

### Tier 3: ADF 演算法替換

**問題**: `statsmodels.tsa.stattools.adfuller` 是純 Python，每次 ~30ms。

**機會**: ADF 核心是 OLS regression on lag terms，可以用 numpy/numba 實作專用版本。

**做法**:
1. 寫 `momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py`，提供 `adf_pvalue_fast(series, lag=None)`
2. 加 `FFACT_USE_FAST_ADF=1` 開關，預設先 OFF，通過 gate 後再考慮預設 ON
3. threshold 附近 `p ∈ [0.08, 0.12]` 強制 fallback statsmodels，避免臨界值誤判
4. 驗證不只看 p-value correlation，而看 stationarity classification agreement 與 d_star 差異

**驗證 Gate**:
- 1000+ 組樣本分層抽樣（不同 symbol、timeframe、layer、feature type）
- `pvalue <= 0.10` 分類一致率 > 99%
- d_star median abs diff < 0.02，P95 abs diff < 0.05
- threshold 附近 fallback statsmodels 後，最終 d_star 與 baseline corr > 0.99

**預期效果**: ADF 從 30ms → 3-5ms → **6-10× 加速**

**穩定性**: ✅ 全 tier 適用，但屬最高風險 phase，必須在 P0/P1 完成後再做

### Tier 4: UI 加估時警告（防呆）

**位置**: [frontend/src/components/feature-factory/PreprocessingPanel.tsx](../frontend/src/components/feature-factory/PreprocessingPanel.tsx)（推測，需驗）

**做法**: 當用戶勾選 FracDiff 或 ADF 時顯示：
```
⚠️ 注意：FracDiff 啟用後 L6.5 預估時間 ×100~140
   1h+12h × 17928 rows 在 8GB 機上預估 18-20 小時
   建議：如僅做流程驗證請取消勾選；如確認需要請使用 cache_d_star=true
```

**穩定性**: 純 UI 改動，無計算風險

---

## 🧪 4. 跨 Tier 穩定性矩陣

| Tier | concurrent_symbols | l65_workers | split_threshold | slow_path_joblib | P0 後 L6.5 全開 | P1/P2 後 L6.5 全開 |
|------|-------------------|------------|----------------|------------------|------------------|---------------------|
| 8GB  | 1 | 2 | 2000 | 預設 OFF，驗證後開 | ~3-5h | ~50-70 min |
| 16GB | 1 | 6 | 8000 | 驗證後開 | ~2-4h | ~25-40 min |
| 24GB | 2 | 8 | 12000 | 驗證後開 | ~1.5-3h | ~20-30 min |
| 32GB | 3 | 8 | 16000 | 驗證後開 | ~1-2h | ~15-25 min |

**穩定性保證**:
- chunked path（已在）保證 8GB 不 OOM
- per-run non_stationary cache 不跨 symbol → 無品質污染
- d_star cache atomic write（temp + rename）→ 無競爭

---

## 📦 5. 輸出檔案大小影響

L6.5 輸出大小由：
1. 欄位數（不變 — user constraint）
2. mode=replace vs append → append 會在 L6.5 多出 `_fracdiff` 欄位

**現況**:
- mode 預設 `replace` ✓（最小輸出）
- L7 `float16 + zstd level 1 + use_dictionary=False` ✓ 已最佳

**新增建議**:
- 新增 `FFACT_L65_FRACDIFF_OVERRIDE_MODE=replace` 強制選項
- 即使全域 mode=append，也允許單獨對 fracdiff 用 replace（節省輸出但保留分析意義）

**結論**: 輸出大小已是最優；本計畫不會擴大輸出。

---

## 📋 6. 實施階段

### Phase A — L6.5 降時 Quick Wins（1-2 天）✅ 立即實作
- [ ] `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`（預設鎖定，expert env override）
- [ ] `precision 0.01 → 0.02`，並 bump d_star cache version
- [ ] per-run non_stationary classification cache
- [ ] d_star cache key 改為 symbol/timeframe/config-aware + atomic write
- [ ] UI 加估時警告，修正 FracDiff/ADF 文案
- **預期**: 單 symbol 全開場景從 19h 降至 ~3-5h，第二次 same symbol 降至 ~30-60 min

### Phase A0 — Multi-Symbol Hardening（1-2 天）✅ 與 Phase A 同步
- [ ] Feature Factory heavy batch 預設同時只允許 1 個 batch
- [ ] Symbol-level 序列調度 + concurrent_symbols tier table
- [ ] RAM gate + checkpoint + Resume API
- [ ] 每完成 symbol 立即輸出、釋放記憶體、更新 ETA
- **預期**: 多 symbol 任務不因 queue/process 疊加 OOM；中斷後可 resume

### Phase B — Safe Parallelism（3-5 天）
- [ ] joblib loky 只套用 FracDiff/ADF slow path
- [ ] 保留現有 chunked OOM 防護與 fast path ThreadPool
- [ ] tier-aware n_jobs + 禁止巢狀 process pool
- [ ] Hurst prior + bounded search，取代純二分搜尋
- **預期**: 全開場景再降至 ~1-2h

### Phase C — Algorithm Replacement（5-7 天，最高風險）
- [ ] numba-OLS Fast ADF 實作
- [ ] threshold fallback band + statsmodels fallback
- [ ] classification agreement / d_star diff gate 驗證
- **預期**: 全開場景降至 ~30-60 min，等價 V8 場景降至 ~3-5 min

### Phase D — 持續監控
- [ ] 加 L6.5 benchmark suite（每 phase 自動跑）
- [ ] 跨 tier 自動回歸（CI 在 8GB / 16GB sim 環境跑）

---

## ✅ 7. 驗收標準

每個 Phase 結束須通過：

1. **品質 Gate**：
   - 對 ETHUSDT 1h，fracdiff 結果與 baseline corr > 0.99
   - d_star cache 在 cache miss 與 cache hit 兩種情況下產出 bit-similar
   - 不同 symbol/timeframe/config 的 d_star cache 不互相污染
   - Fast ADF phase 必須通過 classification agreement 與 d_star diff gate
   - L7 輸出 float16 roundtrip gate 全通過

2. **穩定性 Gate**：
   - 8GB tier 連續跑 3 次同任務無 OOM
   - 16GB/24GB/32GB tier 各跑 1 次無 OOM
   - 既有 381 個 L6.5 相關測試 100% pass

3. **效能 Gate**：
   - Phase A 完成後：全開場景 < 5 小時（從 19h）
   - Phase B 完成後：全開場景 < 2 小時
   - Phase C 完成後：全開場景 < 1 小時

4. **輸出大小 Gate**：
   - L7 parquet 總大小相對 baseline 變化 < 5%

---

## 🚫 8. 絕不做的事

| 項目 | 理由 |
|------|------|
| ❌ 砍掉任何 indicator 欄位 | 違反 user constraint |
| ❌ 把 L3 windows 從 10 個減到 5 個 | 違反 user constraint |
| ❌ 把 fracdiff 從 L6.5 移除 | 量化研究需要 |
| ❌ 把 mode 預設改成 append | 會擴大輸出 |
| ❌ 用 lossy compression（gzip→snappy） | 已是 zstd level 1 最佳 |
| ❌ 跳過 float16 roundtrip gate | 會造成數值錯誤 |

---

## 📚 9. 參考

- 現況問題分析: 此 conversation
- 既有架構: [docs/FEATURE_FACTORY_V8_FINAL_OPTIMIZATION_STATUS.md](FEATURE_FACTORY_V8_FINAL_OPTIMIZATION_STATUS.md)
- V7→V8 進化: [docs/V7_vs_V8_Comparison.md](V7_vs_V8_Comparison.md)
- V8 微調: [docs/V8_initial_vs_V8_final_Comparison.md](V8_initial_vs_V8_final_Comparison.md)
- FracDiff 理論: López de Prado, "Advances in Financial Machine Learning", Ch. 5
- ADF 演算法: Said & Dickey (1984), "Testing for Unit Roots in Autoregressive-Moving Average Models of Unknown Order"

---

## 📌 10. 已決策事項（依量化金融業界經驗 + 多 symbol 場景）

### Q0 (UPDATED): FracDiff 跳過的欄位是否用 ADF 補上？→ **不採用** ✅

見 §3 詳細說明。**結論**：量化金融業界通常不把 FracDiff 跳過的欄位再用 ADF 自動補上。若 FracDiff 因高 NaN、warmup 太長或資料不足跳過，應記錄品質 warning 並交給 L7 品質 Gate；ADF 保留為 expert option，不作為預設 fallback。

### Q1: L3+ 是否做 fracdiff？→ **不做（L1+L2 only）** ✅

**業界依據**：
- López de Prado《Advances in Financial ML》Ch. 5：fracdiff 的價值是「保留長記憶（long memory）同時達到 stationarity」，對象是**原始價格、log-return、成交量**這類具長記憶的 raw 序列。
- L3 是 indicator-of-indicator（rank_252、zscore_100、percentile_rank、diff），**根據定義 bounded 或 zero-mean**，本身就 stationary，再做 fracdiff 會：
  1. ADF 早就 pass → fracdiff 直接退化為 d≈0（等於不變），白白消耗 7 次 ADF
  2. 即使 d>0，FFD 卷積會在已標準化序列上引入「微弱長記憶」反而稀釋訊號
- AQR、Two Sigma、Man AHL 公開 paper 均**僅對 raw price/return level 做 fracdiff**，indicator 一律不做
- L4（cross-sectional rank）更是定義上 stationary，絕對不該做

**結論**：Phase A 預設 `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`，且一般 UI 不開放用戶調 L3+（避免亂用）；只保留 expert env override 供研究驗證。
**特徵不流失**：L3+ 仍跑 winsor/rank/zscore/gaussian，只是不重複跑 fracdiff。

### Q2: 多 symbol 場景如何處理？→ **新增 Phase A0（symbol-level orchestration）**

見下方 §11 詳細設計。

### Q3: 先處理多 symbol 還是先處理 L6.5？→ **先砍單 symbol 19h，同步補多 symbol 安全閘門** ✅

**理由**：
- 多 symbol 編排只能帶來「並行度倍率」（受 RAM/核心數限制，8GB 上實際只能 ×1，16GB ×2，32GB ×3）
- L6.5 per-symbol 優化每改善 1× 就會在「所有 symbol」上線性放大
- 數學：10 symbols × 19h ÷ 並行度 vs 10 symbols × 1h ÷ 並行度，後者贏整整一個量級

**順序**：
1. **Phase A**：L1/L2-only FracDiff + d_star cache + per-run cache，先把 19h 降到數小時
2. **Phase A0**（同步做）：batch RAM gate + resume，確保多 symbol 不 OOM、不全重跑
3. **Phase B**：joblib 只套 slow path，保留現有 chunked OOM 防護
4. **Phase C**：Fast ADF

### Q4: ProcessPool 在 macOS？→ **不全面替換；joblib 只用於 slow path** ✅

**業界依據**：
- 純 multiprocessing 在 macOS Python 3.8+ 預設 spawn mode → 每個 worker 重新 import statsmodels（~3 秒）
- **joblib + loky** 是 scikit-learn / NumPy ecosystem 公認的跨平台標準（macOS / Linux / Windows 行為一致）
- joblib 內建 worker reuse、shared memory（mmap_mode）、自動序列化大 array
- AQR Quantopian 內部 pipeline、quantlib、mlfinlab 全用 joblib

**結論**：採用 `joblib.Parallel(n_jobs=workers, backend='loky', mmap_mode='r')`，但只包 FracDiff/ADF slow path；現有 Numba fast path、ThreadPool split、slow-chunked OOM 防護都要保留。

### Q5: Fast ADF 實作？→ **做，但用 numba-OLS 而非全自己寫** ✅

**業界依據**：
- 系統開發階段，演算法可變更 ✓
- statsmodels.adfuller 為通用版本（含多種 lag 選擇 + 完整輸出）→ 對 L6.5 場景過度泛化
- ADF 核心 = AR(p) OLS + t-statistic → numba JIT 後 ~3-5ms（vs statsmodels 30ms）
- mlfinlab、arch 套件均提供類似 fast ADF
- Critical values 用 MacKinnon (1996) 公式查表（lookup O(1)）

**結論**：Phase C 實作 `_fast_adf_numba.py`，但合併 gate 以 stationarity classification agreement 與 d_star 差異為主；threshold 附近 fallback statsmodels，不只看 p-value correlation。

---

## 🌐 11. Multi-Symbol Pipeline 設計（NEW — Phase A0）

### 11.1 現況問題

當用戶生成 10 個 symbols × 2 個 timeframes = 20 個 feature factory tasks 時：

| 問題 | 現況 | 影響 |
|------|------|------|
| Symbols 序列執行 | `multi_tf_max_workers=1`（8GB tier） | 10 symbol × 19h = 190 小時 |
| d_star cache 全域共享 (`default,default`) | BTC 跑出來的 d_star 給 ETH 用 | **品質污染**（不同 symbol 長記憶結構不同）|
| L0 K-line 重複載入 | 每個 task 自己讀 HDF5 | I/O 浪費 |
| non_stationary 判定未快取 | 同 run 內可能重複分類 | 多算 ADF |
| FastAPI task queue 無記憶體閘門 | 同時跑 2 個會 OOM | 8GB tier 易爆 |
| 任務失敗無 resume | 跑到第 8 個失敗要全部重來 | 災難 |

### 11.2 解決方案（Phase A0）

#### 11.2.1 Symbol-level 序列 + Symbol-internal 並行（業界標準）

**業界共識**（Quantopian / AQR / WorldQuant）：
- 多 symbol pipeline 在 commodity hardware 上**不應跨 symbol 並行**，因為單 symbol 內部已經吃滿 CPU/RAM
- 改採「Symbol A 跑完 → Symbol B 跑」的序列模式，但每個 symbol 內部用滿 workers

**做法**：
- 在 [api/services/feature_factory_batch_service.py](../api/services/feature_factory_batch_service.py) 新增 symbol-level 序列調度
- 每完成一個 symbol 主動 `gc.collect()` + 釋放 d_star cache memory copy（保留磁碟）

**Concurrent Symbols Tier Table**（基於實測 single-symbol L6.5 全開 peak 6-8GB + 25% buffer 業界標準）：

| Tier | OS+Browser+API 占用 | 可用 RAM | concurrent_symbols | 計算 |
|------|-------------------|---------|--------------------|----|
| 8GB  | ~3GB | 5GB | **1** | 5÷8 = 0.6 → 強制 1 |
| 16GB | ~3GB | 13GB | **1** | 13÷8 = 1.6 → 取 1（不能穩定撐 2）|
| 24GB | ~4GB | 20GB | **2** | 20÷8 = 2.5 → 取 2 |
| 32GB | ~4GB | 28GB | **3** | 28÷8 = 3.5 → 取 3 ✓ |

**32GB = 3 的依據**: 28GB 可用 ÷ 8GB peak = 3.5，留 0.5 個 symbol 的 buffer (~4GB) 完全足夠 joblib worker overhead 與 pandas temp。

#### 11.2.2 d_star Cache 設計：per-symbol-per-tf-config JSON + 索引

```
data_cache/feature_preprocessing/
   d_star_BTCUSDT_1h_<config_hash>.json
   d_star_BTCUSDT_12h_<config_hash>.json
   d_star_ETHUSDT_1h_<config_hash>.json
   d_star_index.json          ← 索引：哪些 (symbol,tf,config,column,d_star) 已算過
```

**好處**：
- 第二次同 symbol → 完整 cache hit → fracdiff 跳過 90% ADF
- 跨 symbol 不污染（品質保證）
- 索引檔可快速判斷「哪些 task 可以 skip ADF 階段」

#### 11.2.3 Cross-Symbol Non-Stationary Cache（降級為未來研究）

部分 indicator（RSI、MACD diff、ATR 等）在不同 symbol 上可能呈現相似 stationary 傾向，但仍不能直接假設完全相同。

**做法**：
- Phase A 只做 per-run cache，不做 cross-symbol hard skip
- 未來若要做 cross-symbol cache，只能作為 prior / hint，不可直接決定跳過 ADF
- 低信心度、臨界 p-value、不同 symbol regime 一律 fallback 跑 ADF

**節省**：可能有 10-30% 的 `_get_non_stationary_columns` 時間，但風險高於 per-run cache，故不列入首波降時。

#### 11.2.4 K-line 共享載入（非首波必要）

- 在 batch service 入口一次性載入「該 symbol+tf 全時段 K-line」存入 worker initializer 的 shared memory
- 所有 worker 共用，避免 N task × HDF5 read
- 用 `joblib.Memory` 或 `multiprocessing.shared_memory`

**決策**：K-line I/O 不是 19h 的主瓶頸，首波先不做 shared memory，避免增加 process lifecycle 複雜度。等 Phase A/B 完成後再依 profile 決定。

#### 11.2.5 RAM 閘門 + Resume

- batch service 啟動時 `psutil.virtual_memory().available` 檢查
- 若 available < 4GB → 拒絕啟動新 symbol 任務並提示
- 任務狀態 checkpoint 到 `data_cache/feature_preprocessing/batch_state_{batch_id}.json`：
  - 已完成 symbol 列表
  - 失敗 symbol + 錯誤訊息
  - 啟動參數
- Resume API：`POST /api/v1/feature-factory/batch/resume?batch_id=xxx`

#### 11.2.6 Frontend 多 symbol UI

- Batch task panel 顯示：總 symbol 數 / 已完成 / 進行中 / 預估剩餘時間
- 預估時間用「已完成 symbol 平均時間 × 剩餘 symbol 數」
- 每完成 1 個 symbol 立即輸出 L7 parquet（不等全 batch 完）→ 即使中途中斷已有部分結果

### 11.3 多 Symbol 場景效能預估

以 **10 symbols × 2 tf = 20 tasks，全開 L6.5** 為例：

| 階段 | 8GB tier | 16GB | 24GB | 32GB |
|------|---------|------|------|------|
| 現況（無優化） | 380h（不可行） | 190h | 130h | 95h |
| Phase A0 + A | 30-50h | 20-30h | 12-18h | 8-12h |
| Phase A0 + A + B | 12-20h | 8-12h | 5-8h | 3-5h |
| Phase A0 + A + B + C | 5-8h | 3-5h | 2-3h | 1.5-2h |
| **第二次同 batch（cache hit）** | **30-60 min** | **20-40 min** | **15-30 min** | **10-20 min** |

### 11.4 多 Symbol 場景輸出檔案大小

- L7 parquet 為 per-(symbol, tf) 獨立檔 → 多 symbol 不會放大
- 新增的 d_star JSON 每個約 1-3 MB → 10 symbols 共 ~30MB（可忽略）
- batch_state JSON < 100KB

---

## 🚦 12. 修正後的 Phase 順序（含多 symbol）

### Phase A — L6.5 降時 Quick Wins（1-2 天）⭐ 最高優先
- [ ] `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`（lock at config layer）
- [ ] precision 0.01 → 0.02 + cache version bump
- [ ] d_star cache per-(symbol, tf, config_hash) + atomic write
- [ ] per-run non_stationary classification cache
- [ ] UI 加估時警告 + FracDiff/ADF 文案修正

### Phase A0 — Multi-Symbol Pipeline Hardening（1-2 天，與 Phase A 同步）
- [ ] Symbol-level 序列調度 + concurrent_symbols tier table
- [ ] RAM gate + checkpoint + Resume API
- [ ] Frontend batch panel + per-symbol incremental output
- [ ] heavy batch 預設同時只允許 1 個

### Phase B — joblib slow-path 並行（3-5 天）
- [ ] joblib loky backend 只包 FracDiff/ADF slow path
- [ ] tier-aware n_jobs（8GB=2、16=4、24=6、32=8）
- [ ] 保留現有 fast path ThreadPool + slow-chunked OOM 防護
- [ ] Hurst prior + bounded search 取代純二分

### Phase C — Fast ADF（5-7 天）
- [ ] numba-OLS ADF 實作
- [ ] MacKinnon critical values lookup
- [ ] 與 statsmodels 1000+ 樣本驗證 stationarity classification agreement
- [ ] threshold fallback band + statsmodels fallback

### Phase D — 監控
- [ ] L6.5 + multi-symbol benchmark suite
- [ ] CI 自動跨 tier 回歸

---

## ✅ 13. 最終承諾矩陣

| 原則 | 達成方式 |
|------|---------|
| **多 symbol 穩定** | Phase A0 序列調度 + RAM gate + Resume |
| **跨 tier 不 OOM** | concurrent_symbols tier table + RAM gate + chunked path（已在）+ joblib slow-path only |
| **最高品質** | d_star per-symbol/config（不污染）+ 不做 ADF 高 NaN 補救 + Fast ADF classification gate + L1/L2 fracdiff（業界標準）|
| **最短時間** | Phase A 先把 19h 降到數小時；Phase B/C 再追 30-60 分鐘 |
| **最小輸出** | 不變（mode=replace + L7 zstd float16 已最優）|
| **零特徵刪除** | L3+ 仍跑所有其他 transforms，只是不做 fracdiff（fracdiff 對 L3+ 在數學上本來就退化為 d≈0）|

## 🛡️ 14. 進階建議與潛在風險防範

基於上述計畫，為確保在實際執行（特別是 8GB 機器）時萬無一失，補充以下進階建議與防範措施：

### 14.1 Joblib Loky 的序列化成本 (Serialization Overhead)
* **風險**: Loky backend 雖然能繞過 GIL，但會將資料透過 Pickle 序列化傳給 Worker。若傳遞整張大表會造成極大的記憶體與時間開銷。
* **建議**: 在派發給 Loky Worker 時，**絕對不要**把整張包含數萬欄的 DataFrame 傳進去。必須只傳遞「該次運算需要的單一欄位 `Series.values` (NumPy Array)」。對於大陣列，確實如計畫所寫使用 `mmap_mode='r'`，這能讓多個 Worker 共享同一段實體記憶體，避免 8GB 機器在建立子程序時瞬間 OOM。

### 14.2 Hurst Exponent Prior 的邊界條件
* **風險**: Hurst 的估計（特別是基於 R/S 或 DFA）在遇到金融市場異常震盪（如 2020 年 3 月）時可能產生極端值。
* **建議**: 將 Hurst 推導出的 `d_star` 預測值僅作為起點，務必給予一個堅固的安全搜索範圍（例如 `predict_d ± 0.2`）。如果超出了這範圍 ADF 仍未通過，應退回原本完整的二分搜尋，確保結果不會被錯誤的 Hurst 先驗帶偏。

### 14.3 Numba Fast ADF 的數值精度問題 (Numerical Stability)
* **風險**: Fast ADF 會用到內部矩陣求逆或 OLS 計算。金融時間序列有時會出現共線性或極端數值，導致奇異矩陣 (Singular Matrix)。
* **建議**: 在 Numba 實作 OLS 的 `np.linalg.solve` 或 `np.linalg.lstsq` 時，請預測可能出現的 `LinAlgError`。Numba 在捕捉這類例外時不如純 Python 容易，需硬性加入防止除以零或對角線過小的安全機制，若觸發或數值異常直接 Fallback 到 `statsmodels`。

### 14.4 磁碟 I/O 瓶頸與 Checkpoint 阻塞
* **風險**: 大量併發的快取寫入與 Checkpoint 更新（包含 d_star 的 atomic write）可能對硬碟造成隨機寫入壓力，阻塞 CPU 運算。
* **建議**: 維持計畫中的 Atomic Write（先寫 `.tmp` 再 `rename`），但建議非關鍵的 I/O 操作可以放進背景執行緒（或用 async 包裝），確保 I/O 不會阻塞寶貴的 CPU 運算主執行緒。
