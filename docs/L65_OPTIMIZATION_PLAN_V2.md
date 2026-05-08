# Layer 6.5 全模組優化計畫 V2（V1 補充版）

> **版本**: V2
> **建立日期**: 2026-05-06
> **性質**: 純補充 V1 PLAN/SPEC/TODO；V1 已凍結的項目**不在此重複**，僅以 → 參照
> **V1 文件**: [L65_OPTIMIZATION_PLAN.md](L65_OPTIMIZATION_PLAN.md) / [L65_OPTIMIZATION_SPEC.md](L65_OPTIMIZATION_SPEC.md) / [L65_OPTIMIZATION_TODO.md](L65_OPTIMIZATION_TODO.md)
> **觸發**: P1-full baseline 29.74 GB（預期 ~1.5 GB）＋ 全模組 6 個 transform 從未系統分析**時間 × 檔案大小**兩維
> **最終目標**: 多 symbol 工廠產線 — 10+ symbol × 多 timeframe，穩定重複，最短時間，最小輸出，最高品質
> **不可違反約束**:
>   ① 不刪除任何已配置特徵因子（L1-L6 生成層不變）
>   ② 不縮減 L3 rolling windows
>   ③ 不弱化 NaN/inf/float16 roundtrip gate；integer encoding 路徑可補充，但不取代 gate
>   ④ 跨 8GB/16GB/24GB/32GB tier 重複穩定，不 OOM
>   ⑤ 量化金融業界最佳實踐（López de Prado / AQR / Two Sigma 標準）

---

## V2 範圍邊界

> V1 PLAN/SPEC/TODO 已凍結：FracDiff Layer Filter / precision / d_star cache fix / per-run non_stationary cache / Multi-Symbol Batch Hardening + Resume / joblib slow-path / Hurst Prior / Numba Fast ADF。**以下項目 V2 不重複。**

| 主題 | 時間優化 | 檔案大小優化 | 文件位置 |
|------|---------|------------|--------|
| FracDiff Layer Filter (L1/L2) | → V1 Phase 0 Task 0.1 | V2 §3.5 | |
| FracDiff precision / d_star cache fix | → V1 Phase 0 Task 0.2–0.4 | — | |
| Multi-Symbol Batch Hardening + Resume | → V1 Phase 0 Task 0.6 | — | |
| joblib Slow-Path Parallel | → V1 Phase 1 Task 1.1 | — | |
| Hurst Prior Bounded Search | → V1 Phase 1 Task 1.2 | — | |
| Numba Fast ADF | → V1 Phase 2 Task 2.1 | — | |
| **Winsorize：多 transform 複製消除 + numpy 直接化** | **V2 §3.1** | **V2 §3.1** | **V2** |
| **Rank：constant_mask rolling 消除 + IC-First 減量** | **V2 §3.2** | **V2 §3.2** | **V2** |
| **ZScore：windows 批次合併** | **V2 §3.3** | **V2 §3.3** | **V2** |
| **Gaussian：DataFrame 批次化 + erfinv 向量化** | **V2 §3.4** | **V2 §3.4** | **V2** |
| **FracDiff 輸出 file size**（時間 → V1）| → V1 | **V2 §3.5** | **V2** |
| **ADF 輸出 file size**（時間 → V1）| → V1 | **V2 §3.6** | **V2** |
| **IC-First Pipeline**（rank/zscore/gaussian 架構改造）| **V2 §4** | **V2 §4** | **V2** |
| **L7 整數編碼 + byte_stream_split**（Codec 改善）| — | **V2 §5** | **V2** |

---

## 目錄

1. [根因精確診斷](#1-根因精確診斷)
2. [全模組診斷矩陣](#2-全模組診斷矩陣6-transform--時間--檔案大小)
3. [Per-Transform 優化設計](#3-per-transform-優化設計)
4. [IC-First Pipeline（架構改造）](#4-ic-first-pipeline架構改造)
5. [L7 Codec 改善](#5-l7-codec-改善)
6. [多 Symbol 工廠產線](#6-多-symbol-工廠產線)
7. [效益試算](#7-效益試算)
8. [驗收標準（V2 新增）](#8-驗收標準v2-新增)
9. [絕不做的事](#9-絕不做的事)
10. [決策紀錄](#10-決策紀錄)

---

## 1. 根因精確診斷

### 1.1 P1-full Baseline 實測數據

**環境**：ETHUSDT 1h+12h，L6.5=winsor+rank+zscore（FracDiff OFF），workers=2，8GB tier

| 指標 | 值 |
|------|---|
| 特徵數 | 434,982 |
| Parquet groups | 858 |
| float16 files | 329 files, **0.02 GB**（通過 roundtrip gate）|
| float32 files | 529 files, **29.74 GB**（roundtrip gate 失敗 → fallback）|
| 對比：同資料 V8 final（無 rank/zscore）| **1.255 GiB** |
| L6.5 時間拆分 | winsorize **51%** / rank **39%** / zscore **10%** |

### 1.2 29 GB 雙重失效機制

```
rank/zscore 輸出特性
    ├── 高熵（iid-like 分布）
    │       ├── rank → 均勻分布 U[1/N, 1]（N=252）
    │       └── zscore → 近似 N(0, 1)
    │
    ├── 壓縮失效
    │       ├── zstd 壓縮率: 10-12× → 1.05-1.1×
    │       └── float32 × rows × features ≈ 31 GB raw → 29.74 GB 落盤
    │
    └── float16 roundtrip gate 失效
            ├── rank 最小值 ≈ 1/252 ≈ 0.004
            ├── float16 在 0.004 附近的絕對精度 ≈ 3.8e-6
            ├── → 相對誤差 ≈ 9.5e-4 < 1e-3（剛好在邊界）
            ├── 但 zscore 近 0 的值（|z| < 0.01）相對誤差 > 1% >> 1e-3
            └── → 529/858 groups 失敗 → float32 fallback
```

### 1.3 架構錯位根因

```python
# ic_engine.py line 87（實際程式碼）
ranked_features = aligned[features_df.columns].rank(axis=0, method="average")
```

IC engine 在計算 Spearman IC 時目前會先做 `rank(axis=0, method="average")`，但此處必須先確認 pandas `axis=0` 在實際 `aligned` shape 下的語義（通常是沿 index 排名，未必是跨欄位 cross-sectional rank）。
L6.5 的 rank transform 是 **time-series rolling rank**（每欄在時間窗 [t-W+1, t] 內排名），它不是對整條 feature series 的全域單調轉換，因此不能宣稱 `cs_rank(ts_rank(F)) = cs_rank(F)` 在所有 IC 計算上完全相同。

修正後結論：IC-First 是高 ROI 架構假設，但不是可無條件成立的數學等式。V2 允許先把 rank/zscore/gaussian 移到 IC 後，前提是必須通過 IC stability gates（IC score diff、selected set overlap、top-K stability、下游 proxy validation）。若任一 gate 失敗，必須回退 legacy 或採 dual-path IC（rank-before-IC 與 raw-before-IC 同時計算後比較）。

### 1.4 L6.5 各 Transform 時間拆分（4,003s 實測）

| 子步驟 | 佔比 | 時間（估）| 現有實作狀態 |
|--------|------|---------|---------|
| Winsorize | **51%** | ~2,042s | `selected.mean()/std()/clip()` ← 已 DataFrame 向量化；開銷主因是各 transform 各自 `df.copy()` |
| Rank | **39%** | ~1,561s | `pd.DataFrame.rolling(W).rank(pct=True)` ← 已向量化；但有 2 次多餘 `rolling.max()/min()` passes |
| ZScore | **10%** | ~400s | `selected.rolling(W).mean()/std()` ← 已 DataFrame 批次化 |
| Gaussian | <1% | ~40s | `for col: series.rank(pct=True)` → erfinv ← **per-column loop**，可批次化 |
| FracDiff（關閉）| — | — | — |

---

## 2. 全模組診斷矩陣（6 Transform × 時間 × 檔案大小）

| Transform | 現狀時間開銷 | 現狀檔案大小特性 | 時間優化方向（V2 新增）| 檔案大小優化方向（V2 新增）|
|-----------|---------|---------|---------|--------|
| **Winsorize** | 51%；DataFrame 向量化但 `df.copy()` 開銷大 | bounded 輸出（[q1,q2] 範圍）；entropy 中等；float16 gate 多通過 → ~1.3 GB | ① 消除多 transform 重複 copy；② sigma→numpy direct；③ quantile→單次 `np.nanquantile(2D)` | 現況已可接受；IC-First 後 L7_raw 仍以 winsorized 全量存檔 |
| **Rank** | 39%；已向量化但有 2 次多餘 rolling passes | U[0,1] → near-iid → 壓縮 1.1×；float16 gate 邊界 → 529/858 float32 → 29.74 GB | ① 消除 `constant_mask` 2 次多餘 rolling；② IC-First 後只對 ~2k 特徵做 rank | ① **IC-First**（最大）：29 GB → 0；② uint8/uint16 整數編碼（window≤252 fits uint8）|
| **ZScore** | 10%；`selected.rolling().mean()/std()` 已批次 | N(0,1) → 最高熵 → 壓縮 1.05×；float16 失敗率高 | ① 多 window（100,252）可在同一次 rolling pass 計算；② 消除 `df.copy()` | ① IC-First：只對 ~2k 特徵做；② scaled int16（×1000）存儲 |
| **Gaussian** | <1%；但 per-column loop 可批次化 | N(0,1) 近似；與 zscore 同等 entropy 問題 | ① `df[cols].rank(pct=True)` 替代 per-column loop；② `scipy.special.ndtri(arr_2d)` 向量 ppf | ① IC-First；② scaled int16；③ 預設關閉：目前無實際 file size 問題 |
| **FracDiff** | → V1 Phase 0-2 | L1/L2 filter 後 ~1-3 GB（估）；d 近 1 時 return-like → 壓縮適中；d 近 0 時大值 → float16 可能 overflow | → V1 | ① byte_stream_split（V2 §5）；② V1 L1/L2 filter 已大幅減量 |
| **ADF** | → V1 Phase 0-2 | 整數差分後 stationary → return-like → 壓縮適中；float16 gate 多通過 | → V1 | 無特殊處理需求；byte_stream_split 對殘餘 float32 groups 有輕微幫助 |

---

## 3. Per-Transform 優化設計

### 3.1 Winsorize

#### 時間：消除多 transform 重複複製

**根本開銷來源**：`_apply_winsorization`、`_apply_rank_transform`、`_apply_adaptive_zscore` 各自在開頭呼叫 `result = df.copy()`，導致同一 group DataFrame 被深複製 **3+ 次**。每次複製 N_rows × N_cols × 8 bytes（float64）→ 對大型 group 可達數百 MB。

**優化方案 — 單次複製 + numpy 直接操作**：

```python
# 現有：每個 transform 獨立 copy（3 次 df.copy()）
def _transform_single_group(self, group_df):
    transformed = self._apply_winsorization(group_df)  # 內部 df.copy()
    transformed = self._apply_rank_transform(transformed)   # 內部 df.copy()
    transformed = self._apply_adaptive_zscore(transformed)  # 內部 df.copy()
    return transformed

# 目標：一次複製 + 在 numpy array 上原地操作
def _transform_single_group_optimized(self, group_df):
    columns = self._select_columns(group_df, apply_to="all")
    arr = group_df[columns].to_numpy(copy=True)  # 唯一一次 copy；不得提早降精度，除非數值等效 gate + accepted risk 通過
    if self.do_winsorize:
        arr = _winsorize_2d_inplace(arr, self.lower_q, self.upper_q)
    if self.do_rank:
        arr = _rolling_rank_2d(arr, self.rank_window)
    if self.do_zscore:
        arr = _rolling_zscore_2d(arr, self.zscore_windows)
    if self.do_gaussian:
        arr = _gaussian_2d(arr)
    result = group_df.copy()
    result[columns] = arr
    return result
```

**預期效益**：消除 ~2-3 次 DataFrame copy 開銷 → 估 15-25% 整體 L6.5 時間降低。

#### 時間：numpy direct + 單次 quantile（quantile method 適用）

```python
# 現有（pandas）：2 次 DataFrame.quantile() = 2 次排序
lowers = selected.quantile(lower_q)  # sort 1
uppers = selected.quantile(upper_q)  # sort 2

# 改進（numpy）：1 次 nanquantile = 1 次排序
bounds = np.nanquantile(arr, [lower_q, upper_q], axis=0)  # sort 1（兩分位同時算）
lowers, uppers = bounds[0], bounds[1]
arr = np.clip(arr, lowers, uppers)
```

**預期效益**：quantile method 下 winsorize 排序次數從 2 → 1，~30-40% winsorize 時間降低。

#### 檔案大小：現況已可接受

- Winsorized 輸出 bounded（[q1, q2] percentile 範圍）→ entropy 中等 → zstd 壓縮率 3-6×
- float16 gate pass rate 預期 90%+（沒有系統性 near-zero 問題）
- V8 final（winsor only）= 1.255 GiB → 已合格
- IC-First 後 L7_raw 仍以 winsorized 全量存檔（~1.3 GB/symbol），這是可接受的基準
- **不需要特殊 file size 處理**

---

### 3.2 Rank

#### 時間：消除 constant_mask 兩次多餘 rolling

**現有程式碼**（`_apply_rank_transform` 實際實作）：
```python
rolling = selected.rolling(window, min_periods=1)
ranked_df = rolling.rank(method="average", pct=True)   # rolling pass 1
rolling_max = rolling.max()                             # rolling pass 2（多餘）
rolling_min = rolling.min()                             # rolling pass 3（多餘）
constant_mask = rolling_max == rolling_min
ranked_df = ranked_df.mask(constant_mask, 0.5)
```

`constant_mask` 的目的是把「全部值相同的時間窗」的排名設為 0.5（legacy behavior）。但這需要 2 次額外 rolling pass（.max() + .min()），對大型 DataFrame 是顯著開銷。

**優化方案**：驗證 pandas `rolling.rank(method="average", pct=True)` 對 constant window 是否已自動回傳 0.5：

```python
# 驗收前提：先做 unit test
import pandas as pd
import numpy as np

arr = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
result = arr.rolling(3, min_periods=1).rank(method="average", pct=True)
# 若 result.iloc[2:] 全為 0.5 → 可直接移除 rolling.max()/rolling.min() 兩行
```

- 若確認：可直接刪除 rolling.max() 和 rolling.min() 兩行 → ~15% rank 時間降低
- 若未確認：改用 `rolling.std()` 單次 pass 判斷 constant（std=0 → assign 0.5）

**預期效益**：rank 時間 39% → 估 33%（節省 ~200-300s）。

#### 時間：IC-First 後 scope 減少 99.5%

IC-First Pipeline（§4）實施後，rank 只對 ~2k selected features 做 → rank 時間 ~4s（vs 1,561s）。**這是 rank 最大的時間優化，遠超 constant_mask 優化。**

#### 檔案大小：uint8/uint16 整數編碼（V2 新增）

**問題**：rolling rank with `pct=True` 輸出 U(0,1] 分布 → near-iid → zstd 壓縮率 1.1× → float32 × 29.74 GB。

**方案 1（主）：IC-First** → 不儲存非選中特徵的 rank 輸出 → 0 GB for non-selected。

**方案 2（補充，僅用於 L7_processed 的 ~2k selected features）：uint16 整數編碼**

- rolling rank window W=252 → pct rank values 在 {1/252, 2/252, ..., 252/252}
- 乘以 W×2 → 整數 index k ∈ {2, 4, ..., 504} → **fits uint16**（0-65535）
- 對 ties（method='average'）：k 可為 0.5 倍整數 → 乘以 2 → k×2 ∈ {2,3,...,504}
- NaN sentinel：uint16=0（rank 從 1 起，0 不是有效值）
- 讀回：`float32 = uint16 / (2.0 * W)`
- 空間：float32（4B）→ uint16（2B）= 2× 縮小；加上 zstd 對有限值域（2-504）壓縮率 8-12× → 整體 15-25× 縮小

```python
# feature_storage.py 新增 rank 整數編碼路徑
def encode_rank_as_uint16(rank_arr: np.ndarray, window: int) -> np.ndarray:
    '''rank pct -> uint16 index; NaN -> 0'''
    scaled = (rank_arr * window * 2).round().astype(np.float32)
    out = np.where(np.isnan(rank_arr), 0, scaled).astype(np.uint16)
    return out

def decode_rank_from_uint16(uint_arr: np.ndarray, window: int) -> np.ndarray:
    '''uint16 index -> float32 rank pct; 0 -> NaN'''
    result = uint_arr.astype(np.float32) / (window * 2.0)
    result[uint_arr == 0] = np.nan
    return result
```

**驗收**：decode(encode(rank_arr)) 與原始 rank_arr 相差 ≤ 1/(2W) = 0.002（W=252）；NaN 位置完全一致。

---

### 3.3 ZScore

#### 時間：多 window 合併 + 消除 copy

**現有**（append mode，多 window）：對每個 window 各自計算 `selected.rolling(W).mean()/std()`，各有 copy 開銷。

**優化**：在同一次 rolling 物件上計算 mean 和 std：

```python
# 目標：減少 rolling 物件建立次數
for window in windows:
    r = selected.rolling(window, min_periods=1)
    mean = r.mean()   # 與 std 共用同一個 rolling 物件
    std = r.std()
    zscore = (selected - mean) / (std + epsilon)
```

**注意**：現有 replace mode 已是 `selected.rolling().mean()/std()` 兩次，無法進一步合併（需要兩個統計量）。主要優化來自消除 `df.copy()` 重複（見 §3.1 多 transform 單次複製）。

**預期效益**：ZScore 本身 10% 佔比，節省 copy 後估降至 6-7%。

#### 檔案大小：scaled int16 整數編碼（V2 新增）

**問題**：ZScore 輸出 N(0,1)，near-iid → zstd 壓縮率 1.05× → float32 高比例失敗 float16 gate。

**方案 1（主）：IC-First** → 不儲存非選中特徵的 zscore 輸出。

**方案 2（補充，僅用於 L7_processed 的 ~2k selected features）：scaled int16**

- ZScore 實際範圍通常 ±6σ（極端值已被 winsorize 截斷）
- 乘以 1000 → int16 range ±32767 覆蓋 ±32.767（遠大於 ±6）
- NaN sentinel：`INT16_MIN = -32768`（超出 ±6σ 實際不出現）
- 讀回：`float32 = int16 / 1000.0`（0 以 `INT16_MIN` 判斷 NaN）
- 精度：0.001 絕對誤差 → 優於 float16 在小 z 值的表現（float16 在 |z|<0.1 時誤差更大）
- 空間：float32（4B）→ int16（2B）= 2× 縮小；int16 near-zero clusters → zstd 壓縮率 3-5× → 整體 6-10× 縮小

```python
def encode_zscore_as_int16(zscore_arr: np.ndarray) -> np.ndarray:
    '''zscore -> int16; NaN -> INT16_MIN；超界欄位 fallback float32，不 clip'''
    finite_abs_max = np.nanmax(np.abs(zscore_arr))
    if finite_abs_max > 32.767:
        raise EncodeFallbackRequired("zscore out of int16 range; fallback float32")
    scaled = zscore_arr * 1000.0
    out = np.where(np.isnan(zscore_arr), np.int16(-32768), scaled.round().astype(np.int16))
    return out

def decode_zscore_from_int16(int_arr: np.ndarray) -> np.ndarray:
    '''int16 -> float32 zscore; INT16_MIN -> NaN'''
    result = int_arr.astype(np.float32) / 1000.0
    result[int_arr == -32768] = np.nan
    return result
```

**驗收**：decode(encode(z)) 與原始 z 差 ≤ 0.001；NaN 位置完全一致；|z| ≤ 32 範圍內無 overflow。

---

### 3.4 Gaussian

#### 時間：DataFrame 批次化 + 向量化 erfinv

**現有**（per-column loop）：
```python
# feature_preprocessor.py _apply_gaussian_normalize()
for column in columns:
    series = result[column].astype(float)
    ranked = series.rank(pct=True)       # 每欄各自 rank（全歷史，非 rolling）
    clipped = ranked.clip(lower, upper)
    gaussian = np.sqrt(2.0) * erfinv(2.0 * clipped - 1.0)  # scipy erfinv
    result[column] = gaussian_series.astype(np.float32)
```

**優化**：批次化整個 DataFrame：
```python
# 批次替換
selected = result[columns].astype(float)
ranked_df = selected.rank(pct=True)                    # 一次 DataFrame.rank()
clipped = ranked_df.clip(lower=lower, upper=upper)     # 一次 clip
vals = clipped.to_numpy(dtype=np.float64)
gaussian_arr = np.sqrt(2.0) * scipy.special.ndtri(2.0 * vals - 1.0)  # ndtri 是 vectorized C
gaussian_arr = gaussian_arr.astype(np.float32)
result[columns] = gaussian_arr
```

**關鍵**：`scipy.special.ndtri(arr)` 是 C 向量化實作，比逐列呼叫 `erfinv` 更快；`DataFrame.rank(pct=True)` 也是批次操作。

**預期效益**：gaussian 本身 <1%，但這是 per-column loop 的正確性修正，消除 C 次 Python 函式呼叫。

#### 檔案大小：與 ZScore 相同處理

- Gaussian 輸出近似 N(0,1)（ppf(U(0,1)) = N(0,1)，clip 後約 ±3σ）
- 同 ZScore 的 scaled int16 方案（×1000 → int16）
- IC-First 後只對 ~2k selected features 做 → 磁碟幾乎為零
- 預設配置 Gaussian 是關閉的 → 目前無實際 file size 問題；此方案為未來啟用時準備

---

### 3.5 FracDiff（檔案大小，時間 → V1）

> 時間優化已完整定義於 V1 PLAN/SPEC/TODO Phase 0 Task 0.1-0.4 + Phase 1-2。

#### 檔案大小分析

**V1 L1/L2 filter 後的 FracDiff 輸出**：
- 特徵數從 ~435k → ~5-15k（L1/L2 only）→ 輸出大幅縮小
- d 近 1（強差分）：輸出為 return-like → 值域 ±0.1 → float16 gate 通過率高 → 壓縮率 3-5×
- d 近 0（弱差分）：輸出保留大部分原始 magnitude → 高價格序列（BTC ≈ 50,000）→ float16 overflow（> 65504）
- 現有 float16 roundtrip gate 已保護此情況 → float32 fallback

**額外優化**：
- `byte_stream_split` 編碼對 FracDiff 的 float32 fallback groups 有幫助（見 §5）
- V1 L1/L2 filter 是最大的 file size 優化（95%+ 特徵數減少）

**預計大小（V1 全優化後）**：~0.2-0.5 GB（L1/L2 only FracDiff，~5-15k 特徵，float16 pass 率估 70-80%）

---

### 3.6 ADF（檔案大小，時間 → V1）

> 時間優化已完整定義於 V1 PLAN/SPEC/TODO Phase 0 Task 0.1-0.4 + Phase 1-2。

#### 檔案大小分析

- ADF 整數差分（d=1）後：輸出為一階差分序列，近似 returns
- 值域通常 ±0.1（相對變化），float16 gate 通過率高（values well within ±65504）
- 壓縮率適中（stationary but not pure noise）
- **無需特殊 file size 處理**；`byte_stream_split` 對殘餘 float32 groups 有輕微幫助

---

## 4. IC-First Pipeline（架構改造）

**此為 V2 最大 ROI 項目，同時解決 rank/zscore/gaussian 的 file size + time 問題。**

### 4.1 核心設計

```
現有流程：
L1-L6 generate
→ L6.5(winsor ALL + FracDiff L1/L2 + rank ALL + zscore ALL)
→ L7 persist ALL transformed                → 29.74 GB
→ IC Gatekeeper reads L7                    ← IC engine 內部再次 rank

IC-First 流程（FFACT_IC_FIRST_PIPELINE=1）：
L1-L6 generate
→ L6.5_pre(winsor ALL + FracDiff L1/L2)     ← 只做 IC 前必要 transform
→ L7_raw persist ALL winsorized features    ← ~1.3 GB（無 rank/zscore）
→ IC Gatekeeper reads L7_raw                ← IC engine 內部自行 rank
→ IC selection → ~2,000-3,000 features
→ L6.5_post(rank + zscore + gaussian on selected only)
→ L7_processed persist selected + transformed  ← ~0.16 GB
```

### 4.2 儲存路徑

```
data_cache/features/{SYMBOL}/{TF}/{config_hash}/
    raw/
        {group_id}.parquet      ← L7_raw（winsorized，ALL features）
    processed/
        {group_id}.parquet      ← L7_processed（rank+zscore，selected ~2k only）
    ic_selected_features_{SYMBOL}_{TF}.json   ← IC 篩選結果（feature list + IC scores + fingerprints）
    feature_manifest.json       ← 完整寫入標記、schema hash、row count、group manifest
```

### 4.3 量化業界依據

| Transform | 計算時機 | 理由 |
|-----------|---------|------|
| Winsorize | IC **前**（必須）| IC 前去極值才能得到可靠 Spearman IC |
| FracDiff（L1/L2）| IC **前**（必須）| IC 需要平穩序列；López de Prado Ch.5 |
| Rank（time-series）| IC **後**（ML 前，需通過 stability gates）| 高 ROI 假設：IC 前不存全量 rank；但 rolling rank 可能改變 IC selection，必須以 C-V2-7 驗證，不可僅依「單調變換」推論 |
| ZScore（adaptive）| IC **後**（ML 前）| ML normalization；不影響 IC 計算 |
| Gaussian | IC **後**（可選）| 僅 linear factor models 需要 |

### 4.4 實作步驟

1. **`feature_factory.py`** `_layer6_5_preprocessing()` 新增 pre/post 兩個 mode：
   ```python
   def _layer6_5_pre_ic(self, groups, config):
       '''Pre-IC: winsor + fracdiff(L1/L2 only) — 不做 rank/zscore'''

   def _layer6_5_post_ic(self, selected_features, groups, config):
       '''Post-IC: rank + zscore + gaussian on selected features only'''
   ```
   - `FFACT_IC_FIRST_PIPELINE=1` 控制（預設 OFF，驗證後 ON）

2. **`feature_storage.py`** 新增 `write_raw()` / `write_processed()` 兩條路徑；保留現有 `write()` 作為 legacy fallback。

3. **IC Gatekeeper**（`ic_analysis_service.py` + `ic_engine.py`）：
    - 讀取 canonical 路徑 `features/{SYMBOL}/{TF}/{config_hash}/raw/`，legacy fallback 僅能讀舊版 `features/{SYMBOL}/{config_hash}/` 或既有 writer 路徑
    - 篩選結果以 atomic write 寫入 `ic_selected_features_{SYMBOL}_{TF}.json`
    - `feature_manifest.json` 必須含 `complete=true`、`schema_hash`、`data_fingerprint`、每個 group 的 path/columns/dtype/row_count

4. **Post-IC Transform Service**：
   - `FeaturePreprocessor.transform_selected(selected: List[str], groups, config)`
   - 讀 L7_raw → 只對 selected features 做 rank/zscore → 寫 L7_processed

### 4.5 IC-First 與「不刪減特徵」約束的關係

- L1-L6 仍完整生成 434,982 個特徵 ✅
- L7_raw 仍儲存全部特徵（winsorized）✅
- IC 篩選是**特徵選擇**（決定進入 ML 訓練的特徵），不是特徵刪除 ✅
- Rank/zscore/gaussian 改為只對 IC 選中的 ~2k 特徵執行 ✅

### 4.6 Fallback 機制

- `FFACT_IC_FIRST_PIPELINE=0`（legacy）：現有行為，rank/zscore 對 ALL 特徵
- `FFACT_IC_FIRST_PIPELINE=1`（IC-First）：新流程
- L7 schema 版本號區分：`schema_version: "raw_v1"` vs `"processed_v1"`

### 4.7 驗收條件

- L7_raw 磁碟大小 ≤ 1.38 GiB（V8 final × 1.1）
- L7_processed 磁碟大小 ≤ 0.25 GB
- IC stability gates（IC-First mode vs legacy mode）全部通過：`max_abs_ic_diff ≤ 0.01`、selected set Jaccard ≥ 0.90、top-K（預設 K=500）overlap ≥ 0.90、top-K IC rank Spearman ≥ 0.95、下游 ML/backtest proxy 不劣於 legacy 超過 1%
- 多 symbol 測試：10 symbols × 2 tf，每個 symbol 獨立 L7_raw

---

## 5. L7 Codec 改善

### 5.1 byte_stream_split（FracDiff float32 groups 的過渡措施）

Parquet 的 `PLAIN` encoding 對 float32 按 column-major 儲存，high-entropy float 壓縮差。
`BYTE_STREAM_SPLIT` 將 float 的 bytes 分流（exponent bytes vs mantissa bytes 分開），降低各 byte stream 的熵 → 壓縮率提升。

```python
# feature_storage.py 中的 parquet writer（對 float32 fallback groups）
pq.write_table(
    table,
    output_path,
    compression="zstd",
    compression_level=3,
    use_dictionary=False,
    column_encoding={
        col: "BYTE_STREAM_SPLIT"
        for col in float32_cols   # 只對 float32 group 啟用；float16 groups 維持現有
    },
)
```

**適用場景**：
- FracDiff 輸出的 float32 groups（d 值小，magnitude 大，float16 overflow）
- ADF 差分後的 float32 groups（較少）
- rank/zscore float32 groups（在 IC-First 之前的過渡期）

**預期效益**：
- FracDiff float32 groups：壓縮率 1.5-2×（vs 現有 ~2-3×，輕微改善）
- rank/zscore float32 groups（過渡期）：29 GB → ~22 GB（治標）
- byte_stream_split 是 lossless → 不影響任何 gate

**驗收**：讀寫 roundtrip bit-exact；磁碟大小降低 ≥ 10%（否則 ROI 不足，優先推進 IC-First）。

### 5.2 整數編碼 Registry

針對 rank/zscore/gaussian 建立統一的整數編碼 metadata：

```python
# L7 parquet file metadata（PyArrow schema metadata；per-column registry）
{
    "l7_encoding_registry": json.dumps({
        "feature_a_rank_252": {
            "encoding_type": "rank_uint16",
            "scale_factor": "504",
            "nan_sentinel": "0",
            "window": "252",
            "original_dtype": "float32"
        },
        "feature_b_zscore": {
            "encoding_type": "zscore_int16",
            "scale_factor": "1000",
            "nan_sentinel": "-32768",
            "window": None,
            "original_dtype": "float32"
        }
    })
}
```

- 讀取端根據 `l7_encoding_registry` 的 per-column metadata 自動 decode
- 向後相容：無 `l7_encoding_registry` metadata 的舊 parquet 以現有 float 路徑讀取
- L7_processed（IC-First mode）預設使用整數編碼；L7_raw（winsorized only）維持 float 路徑

---

## 6. 多 Symbol 工廠產線

> Multi-Symbol Batch Hardening + Resume（RAM gate、checkpoint、concurrent_symbols tier table）已完整定義於 V1 PLAN/SPEC/TODO Phase 0 Task 0.6。此節僅補充 IC-First 架構與多 symbol 的整合設計。

### 6.1 Per-Symbol 隔離原則

每個 symbol 是完全獨立的計算單元；不允許統計數據跨 symbol 共享：

- d_star cache：`(symbol, timeframe, config_hash)` 獨立 → V1 Phase 0 Task 0.3
- per-run non-stationary cache：每個 `FeaturePreprocessor` instance 獨立 → V1 Phase 0 Task 0.4
- L7 路徑：`data_cache/features/{SYMBOL}/{TF}/{config_hash}/raw/` 和 `/processed/`
- IC selected features：`ic_selected_features_{SYMBOL}_{TF}.json`（每 symbol 獨立）

### 6.2 Sequential Symbol Execution with IC-First

> ⚠️ **OOM 關鍵邊界**：`persist_l7_raw` 完成後，`run_ic_gate` 之前**必須**顯式釋放 L6.5_pre 輸出並呼叫 `gc.collect()`。
> 否則 L6.5_pre 的 winsorized DataFrame（~7 GB in-mem，435k feat × 2k rows × float64）與 IC engine 讀回的 L7_raw 資料同時存在 heap → 8GB tier OOM。

```
for (symbol, tf) in batch:
    [V1] check RAM gate; skip if checkpoint completed
    run_l1_l6(symbol, tf)
    pre_ic_groups = run_l65_pre_ic(symbol, tf)   ← winsor + fracdiff(L1/L2)
    persist_l7_raw(symbol, tf, pre_ic_groups)     ← 寫入 ~1.3 GB（atomic write + manifest complete）
    del pre_ic_groups; gc.collect()               ← ⚠️ 必要：釋放 large refs；以 available RAM / peak RSS gate 驗證，不以固定 RSS 下降量作唯一 gate
    run_ic_gate(symbol, tf)                       ← per-group 迭代讀 L7_raw；IC 篩選；atomic write ic_selected_features_{SYMBOL}_{TF}.json
    run_l65_post_ic(symbol, tf)                   ← rank + zscore on selected ~2k；peak < 50 MB
    persist_l7_processed(symbol, tf)              ← ~0.16 GB
    [V1] gc.collect(); write_checkpoint(symbol, tf)
```

> **額外要求**：`ic_engine` 讀取 L7_raw 時必須 **per-group 迭代**（逐 parquet group 讀取、計算 IC、釋放），不可一次全載。
> 858 groups × per-group peak ~8 MB → 總 peak < 300 MB（IC 計算期間）。
> 若 IC engine 改為一次全載，8GB tier 下 peak ≈ 6.96 GB × 2（loaded + ranked）= ~14 GB → OOM。

### 6.3 Cross-Symbol Rank（可選，獨立批次）

Cross-sectional rank 需要多 symbol 同一 timestamp 的特徵值，**必須在所有 symbol L7_raw 完成後才能執行**：

```
Phase 1：per-symbol L7_raw（可並行）→ 全部完成
Phase 2：CSR Batch（獨立 API，POST /api/v1/features/cross-symbol-rank）
         align_timestamps(all symbols)
         cs_rank = rank(axis=0, method='average')
         write_l7_csr(all symbols)
```

CSR 是可選的，不阻塞 per-symbol L6.5 計算路徑。

---

## 7. 效益試算

### 7.1 單 Symbol 時間效益（ETHUSDT 1h+12h）

| 優化組合 | 現狀 4,003s | V2 新增 | V1 + V2 合計 |
|---------|-----------|--------|------------|
| 消除多 transform copy（§3.1）| 4,003s | ~3,000s（~25%↓）| — |
| + rank constant_mask 消除（§3.2）| 3,000s | ~2,750s | — |
| + **IC-First（§4）** | 2,750s | **~250s**（rank/zscore scope 99.5%↓）| — |
| + V1 P0 全部（FracDiff L1/L2, cache）| 250s | — | **~180s** |
| + V1 P1（joblib parallel）| 180s | — | **~100s** |
| 全優化（含 V1 P2 Fast ADF，FracDiff ON）| — | — | **~80-120s** |

### 7.2 磁碟大小效益

| 場景 | 現狀 | + byte_stream_split（§5.1）| + IC-First（§4）| + 整數編碼（§5.2）|
|------|------|--------------------------|----------------|------------------|
| winsor only | ~1.3 GB | ~1.1 GB | ~1.3 GB（L7_raw）| ~1.1 GB |
| winsor+rank+zscore（預設）| **29.74 GB** | ~22 GB | **~1.5 GB（L7_raw）+ 0.16 GB（L7_processed）** | **~1.5 + 0.05 GB** |
| winsor+rank+zscore+FracDiff | >30 GB | ~7 GB | ~1.5 + 0.2 GB | ~1.5 + 0.07 GB |

### 7.3 多 Symbol 擴展效益（10 symbols × 2 tf）

| 狀態 | 8GB serial 時間 | 磁碟總計 |
|------|----------------|--------|
| 現狀 | ~11.1h | 10 × 29.74 GB = **297 GB** |
| V2 IC-First + V1 P0 | ~0.5h | 10 × (1.5 + 0.16) GB = **16.6 GB** |
| 全優化（V1+V2，FracDiff ON）| ~0.3h | ~18 GB |

---

## 8. 驗收標準（V2 新增）

> V1 SPEC 的硬約束（C-OPT-1 ~ C-OPT-6）和 C1-C5 繼續有效。以下為 V2 新增。

| ID | 約束 | 驗收方式 |
|----|------|--------|
| **C-V2-1** | 消除多 transform copy 後，結果與 legacy 數值等效 | schema / NaN mask exact + numeric `assert_allclose(rtol=1e-5, atol=1e-8)`；若聲稱 bit-exact 才額外 `assert_array_equal` |
| **C-V2-2** | rank constant_mask 消除後，constant window 回傳 0.5（legacy behavior 不變）| unit test: 全常數 array → ranked_df = 0.5 |
| **C-V2-3** | Gaussian 批次化後，結果與 per-column loop bit-exact | `np.testing.assert_allclose(rtol=1e-5)` |
| **C-V2-4** | uint16 rank 整數編碼 roundtrip 誤差 ≤ 1/(2W)（W 由 per-column metadata 決定）| roundtrip test with dynamic tolerance |
| **C-V2-5** | int16 zscore/gaussian 整數編碼 roundtrip 誤差 ≤ 0.001；NaN 位置一致 | roundtrip test with tolerance |
| **C-V2-6** | IC-First 模式：L7_raw ≤ 1.5 GB；L7_processed ≤ 0.25 GB | file size check post-benchmark |
| **C-V2-7** | IC-First vs legacy 的 IC selection stability 通過 | `max_abs_ic_diff ≤ 0.01` + selected set Jaccard ≥ 0.90 + top-K overlap ≥ 0.90 + top-K IC rank Spearman ≥ 0.95 + downstream proxy degradation ≤ 1% |
| **C-V2-8** | byte_stream_split roundtrip bit-exact | pyarrow.parquet read-write roundtrip |
| **C-V2-9** | integer encoding metadata 正確寫入 parquet schema，且支援 mixed rank/zscore/gaussian columns | read schema metadata + validate per-column `l7_encoding_registry` |
| **C-V2-10** | IC-First 模式，8GB tier 下全流程不 OOM（單 symbol）| memory profiler peak RSS < 7 GB during `run_ic_gate` |
| **C-V2-11** | `persist_l7_raw` 後釋放 large refs，且 IC Gate 前 available RAM / peak RSS 滿足 tier budget | `psutil.Process().memory_info().rss` + `psutil.virtual_memory().available` + memory profiler；5GB RSS drop 只作 full-scale diagnostic，不作 universal hard fail |

---

## 9. 絕不做的事

| 項目 | 理由 |
|------|------|
| ❌ 刪除任何 L1-L6 特徵欄位 | 違反約束①；L7_raw 仍儲存所有特徵 |
| ❌ 縮減 L3 rolling windows | 違反約束② |
| ❌ 弱化 float16 roundtrip gate | 現有 gate 不變；整數編碼是補充路徑，不取代 gate |
| ❌ integer encoding 用於 winsorize / FracDiff | 這兩者的值域不規則，整數編碼會損失精度 |
| ❌ IC-First 模式下讓 IC Gatekeeper 讀 L7_processed | L7_processed 只有選中特徵；IC 要讀全量 L7_raw |
| ❌ 跨 symbol 共用統計 cache（d_star / non_stationary / IC selected）| 不同 symbol 動態不同 → 違反隔離原則 |
| ❌ 在 IC-First 之前啟用 integer encoding for rank/zscore at L7_raw | L7_raw 只存 winsorized；rank/zscore 進 L7_processed |
| ❌ 用低壓縮率 codec（如 snappy）替換 zstd | zstd level 1/3 已是較合適的壓縮/速度折衷 |
| ❌ 把 gaussian 批次化的 `DataFrame.rank(pct=True)` 換成 rolling rank | gaussian 用的是 cross-time rank（非 rolling），語義不同 |
| ❌ IC-First 中 `persist_l7_raw` 後不 `del` + `gc.collect()` 直接 `run_ic_gate` | L6.5_pre 輸出（~7 GB in-mem）未釋放 + IC 讀回 → 8GB tier OOM |
| ❌ IC engine 一次全載 L7_raw 所有 group 計算 IC | 解壓後 ~14 GB，8GB tier 必 OOM；必須 per-group 迭代 |

---

## 10. 決策紀錄

### D1: IC-First 是否等同「刪除特徵」？→ **不等同** ✅

- L1-L6 仍完整生成 434,982 個特徵
- L7_raw 仍儲存全部特徵（winsorized）
- IC 篩選是特徵選擇（ML training set），不是特徵刪除（不再計算）
- 業界標準：AQR/Two Sigma/Man AHL 均有 alpha filtering stage

### D2: Time-Series Rank（L6.5）vs IC engine rank → **高 ROI 假設，必須由 gate 證明** ⚠️

- L6.5 rank：每欄在時間窗 [t-W+1, t] 內排名（time-series）→ 去除量綱
- IC engine rank：目前程式碼使用 `rank(axis=0)`，需先驗證實際 `aligned` shape 下它是沿時間或跨欄位排名；不可只用註解推定 cross-sectional 行為
- rolling time-series rank 不是全域單調轉換，可能改變 IC score 與 selected feature set
- 結論：rank 移至 IC 後是高 ROI 設計，但必須通過 C-V2-7 stability gates；若失敗，使用 `FFACT_IC_FIRST_PIPELINE=0` 或 dual-path IC fallback

### D3: 整數編碼是否違反「不弱化 float16 roundtrip gate」？→ **不違反** ✅

- float16 gate 對「是否以 float16 儲存一個 float 值」做精度驗證 → 繼續維持
- uint8/int16 整數編碼是**另一條儲存路徑**，不透過 float16 gate
- 整數編碼的精度（rank: 0.002，zscore: 0.001）**優於 float16**（float16 在 near-zero 可達 0.1%+ 相對誤差）
- 只對 IC-First 的 L7_processed 使用；L7_raw（winsorized）維持現有 float 路徑

### D4: constant_mask rolling 消除是否安全？→ **需先驗證再執行** ⚠️

- 假設 `pd.DataFrame.rolling(W).rank(method='average', pct=True)` 對 constant window 自動回傳 0.5
- 若確認：可直接移除 rolling.max() 和 rolling.min() 兩行
- 若未確認：改用 `rolling.std()` 單次 pass 偵測 constant window（std=0 → assign 0.5）
- 驗收：unit test constant array → ranked output = 0.5 per window

### D5: byte_stream_split 在 IC-First 後是否仍有必要？→ **有限度仍有用** ✅

- IC-First 後 rank/zscore 不再存全量 → byte_stream_split 對 L7_raw 幫助有限
- 但 FracDiff float32 fallback groups（level series d≈0）仍從 byte_stream_split 受益
- ADF float32 residual groups 同上
- 建議：IC-First 後繼續保留 byte_stream_split 僅用於 FracDiff/ADF float32 groups

### D6: Gaussian 批次化是否改變語義？→ **不改變** ✅

- 現有：`series.rank(pct=True)` = cross-time rank on entire series（非 rolling）
- 改為：`df[cols].rank(pct=True)` = 同樣的 cross-time rank，只是批次化計算
- `scipy.special.ndtri` 與 `np.sqrt(2.0) * erfinv(2.0 * x - 1.0)` 數值相等
- 結果 bit-exact（或 float64 精度內），可用 `assert_allclose(rtol=1e-5)` 驗證
