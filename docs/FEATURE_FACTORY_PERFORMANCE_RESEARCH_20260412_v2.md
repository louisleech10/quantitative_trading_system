# Feature Factory 效能研究報告 v2（2026-04-12）

## 1. 研究範圍與目標

- 測試條件：
  - 單一 Symbol（ETHUSDT）
  - Layer 1/2/3/4/5/6/6.5 全開
  - Data source: Close + Volume + Taker-ratio（+ 自動補齊 OHLCV + 4 synthetic）
  - 主框架 1h（12,888 rows），訓練框架 1h + 12h（1,082 rows）
- 目標：
  - 不減特徵、不降品質（維持完整研究搜索空間）
  - 顯著縮短計算時間
  - 避免 OOM / swap thrashing
- 分析檔案：
  - logs/case_search_api_20260412.log（251 行）
  - logs/errors_20260412.log
- **生產環境目標**：未來演進至數百 Symbols × 3~4 timeframes，時間是很多年的1hr 資料，本報告所有優化方案須以此為終極目標

---

## 2. 本次任務時間軸（最新 task）

- task_id: ffca1f1f-7131-493e-b54e-0681d581ce50
- 開始：2026-04-12 10:04:03
- 結束：2026-04-12 12:54:48（手動中止，F 區段無任何後續 log）
- 觀測總時長：10,245 秒（170m45s）

### 主區段耗時

| 區段 | 語義 | 起訖 | 秒數 | 時長 | 占總時長 |
|---|---|---|---:|---:|---:|
| A | 1h L0→L1→L2→L3→L4→L5→L6 | 10:04:03 → 10:16:24 | 741 | 12m21s | 7.2% |
| B | 1h concat + TF align + 12h 啟動前置 | 10:16:24 → 10:30:20 | 836 | 13m56s | 8.2% |
| C | 12h L0→L1→L2→L3（rows=1082, 快速） | 10:30:20 → 10:30:57 | 37 | 0m37s | 0.4% |
| D | 12h concat + 12h→1h TF align | 10:30:57 → 10:33:35 | 158 | 2m38s | 1.5% |
| E | multi_tf_merged concat（1h+12h 合併） | 10:33:35 → 10:35:23 | 108 | 1m48s | 1.1% |
| F | final memmap 建立後無進度（23.4 GB 黑箱） | 10:35:23 → 12:54:48 | 8,365 | 139m25s | 81.6% |

---

## 3. 扣掉 F 後，ABCDE 的瓶頸排序

### 3.1 定義

- `T_total = A+B+C+D+E+F = 10,245s`
- `T_ABCDE = T_total - F = 1,880s`

### 3.2 ABCDE 重新占比（扣掉 F）

| 區段 | 秒數 | 占 ABCDE 比例 | 主要工作 |
|---|---:|---:|---|
| A | 741 | 39.4% | 1h 全層計算（L0~L6） |
| B | 836 | 44.5% | 1h concat 11.7GB + TF align 11.7GB |
| C | 37 | 2.0% | 12h 全層計算（rows=1082, 極快） |
| D | 158 | 8.4% | 12h concat 0.98GB + 12h→1h align 11.7GB |
| E | 108 | 5.7% | 1h+12h 最終合併 → 23.4GB memmap |

### 3.3 結論

- 扣掉 F 之後，**A + B = 83.9%**，確實是主瓶頸。
- B 的 44.5% 幾乎全部是記憶體搬運成本（concat + align），**不是計算**。
- A 中有近一半是 L1/L2 前置計算，另一半是 L3 rolling。
- C+D 合計 10.4%，12h 資料量小但 align 時需回寫成 12,888 rows × 226k cols = 11.7GB。
- E 的 5.7% 是將兩份 ~227k 欄合併為 453k 欄的 memmap 建立。

### 3.4 推算 F 之後（如果完成）的 L6.5 時間

根據先前單 timeframe（960 cols × 52,519 rows）的 L6.5 剖析數據：
- winsorization 約占 51%、rank 約 39%、zscore 約 10%
- 若線性外推到 453,953 cols × 12,888 rows：
  - 資料量比值 ≈ (453953×12888)/(960×52519) ≈ 116x
  - 即使考慮 column-chunking，單純線性估計 L6.5 可能需要 **數小時**
- **結論：就算 F 完成，L6.5 也可能又是另一個黑箱等待**

---

## 4. 區段 A 細分研究（1h 全層計算 = 741s）

A 區段：10:04:03 → 10:16:24（741s）

### 4.1 Log 逐行精確計時

| 時間戳 | 事件 | 累計秒 |
|---|---|---:|
| 10:04:03.000 | Task 開始，fetch ETHUSDT/1h（0.01s） | 0 |
| 10:04:03.xxx | TA-Lib 載入 132 指標 + STOCH/STOCHF/STOCHRSI 參數補全 warning ×26 | ~0 |
| 10:04:04 | microstructure_indicators 完成（trades missing → NaN） | 1 |
| 10:04:52 | **第二輪 STOCH warning ×26 出現** → L1 第二輪計算開始 | 49 |
| 10:09:59 | L3 memmap 建立：shape=(12888, 168300)，est=8.68 GB | 356 |
| 10:10:52 | L3 streaming step 10/100 | 409 |
| 10:11:35 | L3 streaming step 20/100 | 452 |
| ... | 每 10 steps ~36s 平均 | ... |
| 10:16:24 | L3 streaming step 100/100 complete | 741 |

### 4.2 可觀測子段（基於 log 重建）

| A 子段 | 起訖 | 秒數 | 占 A% | 占 ABCDE% | 何物 |
|---|---|---:|---:|---:|---|
| A1. L0+L1 第一輪 | 10:04:03 → 10:04:04 | 1 | 0.1% | 0.1% | 1h OHLCV fetch + TA-Lib 7 類別 + micro/entropy/tail |
| A2. L1 第二輪（12h 指標？） | 10:04:04 → 10:04:52 | 48 | 6.5% | 2.6% | 第二輪 STOCH warning → 可能是 derived calc |
| A3. L2+L4+L5+L6 + L3 前置 | 10:04:52 → 10:09:59 | 307 | 41.4% | 16.3% | DerivedOperatorEngine + LagProcessor + memmap 建立 |
| A4. L3 streaming 計算 | 10:09:59 → 10:16:24 | 385 | 52.0% | 20.5% | 100 steps rolling (10 agg × 10 windows) |

### 4.3 A 子段深入解讀

**A3 是 A 中最大的隱藏成本（307s = 41.4%）**：
- 從 10:04:52 到 10:09:59 有 **307 秒沒有任何 log**
- 這段包含：L2 DerivedOperatorEngine（48,591 cols 的 operators 計算）、L4 LagProcessor（13,488 cols）、L5 cross-sectional（11 cols, BTCUSDT 找不到→快速失敗）、L6 meta features、以及 L3 memmap 建立
- **L2 產出 48,591 cols 是最大嫌疑**：對 1,683 個 L1 指標做各種 derived operators → 48,591 / 1,683 ≈ 29 倍特徵爆炸
- 需要增加 L2 前後的計時 log 來確認

**A4（L3 streaming = 385s）**：
- 100 steps = 10 windows × 10 aggregators
- 每 10 steps ~36-38s → 每個 step ~3.6s
- 每 step 處理 1,683 base cols → 生成 1,683 新 cols，variance filter 後保留 1,637~1,660 cols
- L3 輸出：163,686 cols（168,300 - 4,614 dead）
- **核心成本**：`rolling.skew()`、`rolling.kurt()`、`rolling.rank()` 是 Python callback 密集操作

### 4.4 A 的特徵爆炸分析

| Layer | 欄位數 | 與 L1 倍率 | 佔 1h 總欄比 |
|---|---:|---:|---:|
| L1（atomic） | 1,683 | 1.0x | 0.7% |
| L2（derived） | 48,591 | 28.9x | 21.4% |
| L3（rolling） | 163,686 | 97.3x | 71.9% |
| L4（lag） | 13,488 | 8.0x | 5.9% |
| L5（cross-sec） | 11 | 0.0x | 0.0% |
| L6（meta） | 0（未觀測到） | - | ~0% |
| **1h 小計** | **227,459** | **135.2x** | **100%** |

**關鍵洞察**：L3 佔 71.9% 的欄位，是特徵爆炸的主要來源。L2 的 28.9x 倍率也極高。

### 4.5 A 的優化方向（不減特徵，一次到位）

1. **L2 derived operators（48,591 cols, A3 主因）**：
   - 目前對每個 L1 指標做 ~29 種衍生運算（pct_change, log_return, diff, binary_signal 等）
   - **優化**：改用 numpy vectorized batch 計算，避免逐欄 DataFrame 操作
   - **進階**：在 L1 完成後直接以 numpy ndarray 做 inplace 計算，不經 DataFrame 中間態

2. **L3 rolling aggregation（163,686 cols, A4 = 52%）**：
    - `skew/kurt` 是 rolling.apply() 內部用 Cython，但每次 rolling 仍需建立上下文
    - `rank` 使用 `rolling(w).rank(pct=True)`，在 12,888 rows × 1,683 cols 下仍然昂貴
    - **優化**：採用 fused window kernel，一次掃描同時計算 mean/std/min/max/range/zscore（目前已部分做到 cache reuse，但 skew/kurt 仍獨立 rolling）
    - **Numba JIT rank**：把 `rolling.rank` 改為 Numba O(window) 的 incremental rank
    - **分治實作，不做近似**：小窗與大窗可用不同 kernel / buffer 策略，但必須維持與現行 rolling 數值等價；在「不降品質」前提下不採用 approximate rolling

3. **L1 atomic（1s，已夠快，不需優化）**：TA-Lib C 層已高度優化

4. **STOCH 參數補全 warning 風暴**：同一組 combo 重複 warning（見第二輪 10:04:52）
   - 改為 deduplicate，只記 summary（不影響效能但改善 log 可讀性）

---

## 5. 區段 B 細分研究（1h concat + TF align = 836s）

B 區段：10:16:24 → 10:30:20（836s）

### 5.1 Log 逐行精確計時

| 時間戳 | 事件 | Δ秒 |
|---|---|---:|
| 10:16:24 | L3 streaming complete | 0 |
| 10:16:27 | Fetch BTCUSDT/1h → 找不到 → cross-sectional 失敗 | 3 |
| 10:16:28 | **memmap concat 開始**: 5 DFs → 227,459 cols × 12,888 rows ≈ 11.73 GB | 4 |
| 10:16:28 | memmap created: (12888, 227459) | 4 |
| 10:16:30 | DF 1/5 copy 開始（1,683 cols） | 6 |
| 10:16:31 | DF 1/5 copy 完成 | 7 |
| 10:19:11 | **DF 2/5 copy 開始**（48,591 cols）→ **前段空白 160s** | 167 |
| 10:19:31 | DF 2/5 copy 完成（copy 本身 20s） | 187 |
| 10:20:42 | **DF 3/5 copy 開始**（163,686 cols）→ **前段空白 71s** | 258 |
| 10:22:17 | DF 3/5 copy 完成（copy 本身 95s） | 353 |
| 10:22:34 | DF 4/5 copy 開始（13,488 cols）→ 空白 17s | 370 |
| 10:22:44 | DF 4/5 copy 完成 | 380 |
| 10:22:44 | DF 5/5 copy 開始（11 cols） | 380 |
| 10:22:47 | DF 5/5 copy 完成 | 383 |
| 10:22:48 | **MultiTF align 開始**: 227,459 cols → 46 chunks of ≤5000 | 384 |
| 10:22:48 | align memmap created: (12888, 227459) = 11.73 GB | 384 |
| 10:23:24 | chunk 5/46 | 420 |
| 10:27:46 | chunk 46/46 完成 | 682 |
| 10:30:20 | **12h TF 開始** (Processing timeframe 12h) | 836 |

### 5.2 B1（1h concat = 383s）精確拆解

| concat 子步驟 | 開始 | 結束 | 秒數 | 說明 |
|---|---|---|---:|---|
| memmap 建立 | 10:16:28 | 10:16:28 | <1 | create_temp_memmap 本身快 |
| DF 1/5 copy（1,683 cols） | 10:16:30 | 10:16:31 | 1 | 快速小量 |
| **DF 1→2 間隔**（source prepare） | 10:16:31 | 10:19:11 | **160** | ⚠️ 主瓶頸：`np.asarray(df.values, dtype=np.float32, order='C')` 將 48,591 cols 的 L2 DataFrame 轉為 contiguous C-order array |
| DF 2/5 copy（48,591 cols） | 10:19:11 | 10:19:31 | 20 | copy 本身合理 |
| **DF 2→3 間隔**（source prepare） | 10:19:31 | 10:20:42 | **71** | 將 L3 的 163,686 cols memmap-backed DF 轉為 C-order =  讀取 8.68 GB memmap 頁 |
| DF 3/5 copy（163,686 cols） | 10:20:42 | 10:22:17 | 95 | 大量 copy |
| DF 3→4 間隔 + DF4+5 | 10:22:17 | 10:22:47 | 30 | 小量 |
| **合計 concat** | | | **383** | |
| 其中不可見間隔 | | | **~254** | 66.3% 是 source prepare + page fault |
| 其中可見 copy | | | **~129** | 33.7% 是實際 memcpy |

**關鍵發現**：concat 中 **66% 的時間不是 copy，而是 `np.asarray(df.values, dtype=np.float32, order='C')`**。
這個操作要把 pandas DataFrame 的 BlockManager 內部碎片記憶體整理成一個連續 C-order ndarray，
當 DataFrame 有 48,591 或 163,686 列時，這涉及：
1. 遍歷 BlockManager 中所有 blocks
2. 分配一個連續的 (12888, N) float32 array
3. 逐 block copy（觸發大量 page fault）

### 5.3 B2（1h MultiTF align = 298s）精確拆解

| align 子步驟 | 說明 | 秒數 |
|---|---|---:|
| 46 chunks merge_asof | 每 chunk ~5000 cols，每個 ~6.5s | 298 |
| 每 chunk 內部 | ① sort primary_df, ② sort chunk_work, ③ merge_asof, ④ sort by _order, ⑤ write to memmap | ~6.5 |

**merge_asof 的隱藏成本**：
- 每個 chunk 都要重新 sort primary_df（12,888 rows），雖然結果相同
- source_work 每次 `.iloc[sort_order].copy()` 建立 5000 cols 的 DataFrame 副本
- 46 次重複 sort 同一個 primary_df

### 5.4 B3（align 完成到 12h 開始 = 154s）

| 子步驟 | 秒數 | 說明 |
|---|---:|---|
| 10:27:46 → 10:30:20 | 154 | **無 log 的空白** |

**推測**：
- align 完成後，MultiTFGenerator 呼叫 `_combine_layers([L1,L2,L3,L4,L5,L6], context="multi_tf_merged")`
- 這觸發 concat_with_memmap 將 6 層合併為 aligned_outputs[0]（1h 已 aligned）
- 但這步驟**理論上不需要再次 concat**，因為 align 已經產出完整的 227k 欄 DF
- **可能在 `_apply_timeframe_tag` 做 column rename 後觸發重組**
- 或者在 align 結束後進行 `aligned.attrs = {}` 前的 GC 壓力

### 5.5 B 的優化方向（不減特徵，一次到位）

1. **消除 `np.asarray` 瓶頸（B1 最大因素）**：
   - 根因：L2 的 DerivedOperatorEngine 產出的 DataFrame 內部是碎片化的 BlockManager
   - **方案 A**：L2 計算直接寫入預分配的 numpy array（跳過 DataFrame 中介）
   - **方案 B**：concat_with_memmap 改用 `df.to_numpy(dtype=np.float32, na_value=np.nan, copy=False)` 搭配 column-block copy
   - **方案 C（最佳）**：**取消全域 concat**，改用 column-group registry + lazy reference

2. **消除 merge_asof 重複 sort（B2）**：
   - primary_sorted 和 sort_order 只需計算一次，傳給所有 chunks
   - 已在 `_merge_asof_align_chunked` 中對 sort_order 做了預計算，但 primary_sorted 仍每次 `.copy()`
   - **方案**：改為 `searchsorted` 索引映射 → O(N log N) 一次排序 + O(N) 每 chunk gather

3. **消除 B3 空白（154s）**：
   - 增加 log 精確定位是哪個操作
   - 若確認是 concat，改為 zero-copy 传递（指標 align 後直接 emit，不合併）

---

## 6. 區段 C+D 細分（12h 計算 + 對齊 = 195s）

### 6.1 C（12h 全層計算 = 37s）

| 時間 | 事件 | Δ秒 |
|---|---|---:|
| 10:30:20 | Fetch ETHUSDT/12h → 1,082 rows | 0 |
| 10:30:20~24 | L1 TA-Lib + STOCH warning ×26 | 4 |
| 10:30:24 | L1 第二輪（12h） | 4 |
| 10:30:41 | L3 memmap created: (1082, 168300 = 0.73 GB) | 21 |
| 10:30:43~57 | L3 streaming 100 steps（12h 只 1,082 rows，極快） | 14 |
| 10:30:57 | L3 complete: 162,721 survivors | 37 |

**12h 為何快 20 倍**：rows=1,082 vs 12,888（11.9x 少），加上 memmap 只 0.73 GB 完全在 RAM page cache → 無 swap 壓力。

### 6.2 D（12h concat + 12h→1h align = 158s）

| 時間 | 事件 | Δ秒 |
|---|---|---:|
| 10:30:59 | 12h memmap concat: 5 DFs → 226,494 cols × 1,082 rows = 0.98 GB | 0 |
| 10:30:59~10:31:04 | DF 1~5 copy（全部 <1s，因為 1,082 rows 極小） | 5 |
| 10:31:04 | 12h→1h align 開始：226,494 cols → 46 chunks of ≤5000 | 5 |
| 10:31:04 | **align memmap created: (12888, 226494) = 11.68 GB ⚠️** | 5 |
| 10:31:20~10:33:35 | 46 chunks merge_asof（每 chunk ~3.3s） | 156 |

**關鍵發現**：12h concat 只需 5s（因為 rows 少），但 **align 回到 1h 維度後是 (12888, 226494) = 11.68 GB**，與 1h 自身 align 同等規模。

### 6.3 E（最終合併 = 108s）

| 時間 | 事件 | Δ秒 |
|---|---|---:|
| 10:33:35 | 12h align chunk 46/46 完成 | 0 |
| 10:35:23 | **final memmap concat: 2 DFs → 453,953 cols × 12,888 rows ≈ 23.40 GB** | 108 |

**108s 做了什麼**：
- `_combine_layers(aligned_outputs)` 將 1h (227,459 cols) + 12h (226,494 cols) 合併
- 觸發 `concat_with_memmap` → 建立 23.40 GB memmap
- 然後 **開始 DF 1/2 的 `np.asarray` source prepare**…但沒有任何後續 log
- **E 的 108s 可能包含 memmap 建立 + DF1 source prepare 的前半**

## 7. 區段 F 定位（主停滯 = 8,365s = 2h19m）

### 7.1 Log 證據

```
10:35:23 - [memmap concat] 2 DFs → 453953 cols × 12888 rows ≈ 23.40 GB → disk-backed
10:35:23 - [memmap] created: shape=(12888, 453953), dtype=float32, est=23.40 GB
--- 此後無任何 log 直到 ---
12:54:48 - 正在關閉 Case Search API...（手動中止）
```

### 7.2 停滯根因分析

F 段是 `concat_with_memmap` 對兩個 ~227k 欄的 aligned DataFrame 做合併程式碼：

```python
src = np.asarray(df.values, dtype=np.float32, order="C")  # ← 卡在這裡
```

**為什麼 23.4 GB memmap 會卡**：
1. DF 1（1h aligned, 227,459 cols）的 `.values` 需要從 memmap-backed DataFrame 讀取 11.73 GB 頁面
2. `np.asarray(..., order='C')` 需要將所有頁面重組為 contiguous C-order array
3. 但 11.73 GB 遠超 8 GB RAM → macOS 必須同時 page-in memmap 頁 + page-out 既有頁
4. 結果是 **極度的 page fault thrashing**：每讀一頁新資料就要把方才讀的頁寫回 disk
5. 平均每頁 I/O ≈ 4KB page → 11.73 GB / 4KB = 3M 次 page fault
6. SSD random read ~30μs/頁 → 3M × 30μs ≈ 90s 理論下限，但 swap thrashing 使 latency 暴增 10~100x

### 7.3 為什麼 B1 concat 可以完成但 F 不行

| 比較 | B1 concat | F concat |
|---|---|---|
| 來源 DF 數量 | 5 個（L1~L6） | 2 個（1h aligned + 12h aligned） |
| 最大單一 DF | L3: 163,686 cols (memmap-backed) | 1h: 227,459 cols (memmap-backed) |
| 目標 memmap | 11.73 GB | 23.40 GB |
| 同時存活 memmap | 2（L3 source + concat target） | 4+（L3 origin + 1h concat + 1h align + 12h align + final） |
| 預估 page fault | ~3M | ~6M+ |
| OS 可用於 page cache | ~4 GB | ~0 GB（前面 memmap 吃滿） |

**結論：F 是 memmap 層疊的最終崩潰點**。前面每個階段都建立新 memmap 但舊的仍被 DataFrame 引用著（生命週期未釋放），導致 OS 的 page cache 被完全耗盡。

---

## 8. 目前架構、計算方式、格式（現況詳述）

### 8.1 計算引擎

| 層級 | 引擎 | 資料格式 | 輸出 |
|---|---|---|---|
| L0 | AdapterRegistry → HDF5 | pd.DataFrame (12888×10) | raw OHLCV |
| L1 | TA-Lib C + 3 Python engines | pd.DataFrame (12888×1683) | atomic indicators |
| L2 | DerivedOperatorEngine | pd.DataFrame (12888×48591) | derived features |
| L3 | RollingAggregator (streaming) | numpy memmap 8.68 GB → pd.DataFrame view | rolling features |
| L4 | LagProcessor | pd.DataFrame (12888×13488) | lag features |
| L5 | RelativeStrengthProcessor | pd.DataFrame (12888×11) | cross-sectional |
| L6 | Meta feature engines | pd.DataFrame | meta features |
| concat | concat_with_memmap | memmap 11.73 GB → pd.DataFrame view | 合併輸出 |
| align | TimeframeAligner._merge_asof_align_chunked | memmap 11.73 GB → pd.DataFrame view | 對齊到 primary TF |
| final | concat_with_memmap | memmap 23.40 GB → pd.DataFrame view | 最終 1h+12h |
| L6.5 | FeaturePreprocessor._transform_chunked | memmap → pd.DataFrame | 前處理 |

### 8.2 記憶體模型

- **memmap chain**：L3(8.68GB) → 1h_concat(11.73GB) → 1h_align(11.73GB) → 12h_align(11.68GB) → final(23.40GB)
- **同時存活 memmap 估計**：在 F 段時，至少有 1h_align + 12h_align + final = 46.81 GB 的 disk-backed memmap
- **OS page cache**：macOS 8GB RAM，扣除 kernel + process ≈ 4-5 GB 可用
- **問題**：memmap 總量 46+ GB 遠超 5 GB page cache → 極度 thrashing

### 8.3 concat_with_memmap 的工作流程（現行）

```
for each source DF:
    src = np.asarray(df.values, dtype=np.float32, order='C')  ← 整個 DF → contiguous array（最慢）
    for each row_block (1024 rows):
        out_arr[row_start:row_end, col_offset:col_offset+n] = src[row_start:row_end, :]  ← memcpy
```

**瓶頸在第一行**：`np.asarray(df.values, order='C')` 需要一次讀取整個 source DF 到 RAM 並重組。

### 8.4 TimeframeAligner 的工作流程（現行）

```
pre-compute sort_order (one-time)
for each column chunk (5000 cols):
    chunk_work = source_values[chunk_cols].iloc[sort_order].copy()  ← 建立 copy
    chunk_work["_source_ts"] = source_ts_arr[sort_order]
    merged = pd.merge_asof(primary_sorted.copy(), chunk_work, ...)  ← merge
    out_arr[:, col_offset:col_offset+n] = merged[chunk_cols].values.astype(np.float32)  ← write
```

**改進空間**：`primary_sorted.copy()` 每 chunk 重新 copy 一次（46 次）。

---

## 9. 從舊模式到目前模式（演進歷史）

### 9.1 舊模式（Phase 1-3 時期）

- L3 一次 `rolling().agg()` 生成全部結果 → OOM
- 全量 `pd.concat(axis=1)` → 超過 8GB 直接崩潰
- merge_asof 一次 full-width merge → 超記憶體
- L6.5 在 full-frame 下全量操作 → OOM

### 9.2 第一輪優化（memmap 引入）

- `create_temp_memmap` 改用 disk-backed memmap 取代 `np.empty`
- `concat_with_memmap` 改用 row-block copy + heartbeat log
- L3 改為 streaming mode（per-step variance filter + memmap output）
- 效果：**不再 OOM，但極慢**（本次 170 分鐘仍未完成）

### 9.3 第二輪優化（目前狀態）

- memmap 改用 C-order（避免 F-order transpose 10-100x 慢）
- L3 增加 rolling cache reuse（mean/std/min/max 共用）
- L3 slope 改為 vectorized cumsum formula（800x 加速）
- tf_aligner 改為 column-batch merge + memmap write
- L6.5 改為 column-chunking
- 效果：**計算本身加速了，但 memmap 搬運成本成為新瓶頸**

### 9.4 現在仍卡的核心根因

**不是計算慢，是搬運慢**：
- 每個 Layer 輸出 DataFrame → concat_with_memmap 建立新 memmap → np.asarray 讀回所有頁面 → copy 到新 memmap
- 這個「讀回→重組→寫出」的循環在每個 concat/align 階段都重複
- 到 F 階段時，memmap 累計量已遠超 OS page cache，觸發 swap thrashing

---

## 10. First Principle：問題本質分析

### 10.1 根本問題：「Wide Table Anti-Pattern」

當前架構的 fundamental flaw 是假設了一個 **single-pass wide table**：

```
[12,888 rows × 453,953 columns] = 23.4 GB 的 SINGLE 矩陣
```

這個假設導致：
1. 每個 Layer 計算完畢後必須 concat 成更寬的 DataFrame
2. TF align 後必須再次 concat
3. 最終 concat 必須建立一個包含所有特徵的巨型矩陣
4. L6.5 必須讀取這個矩陣做 column-wise transform

**但下游消費者（IC Analysis / ML / SHAP）真的需要 453,953 列同時在 RAM 嗎？**

答案是 **NO**：
- IC Analysis 是 per-feature 計算（一次只需 1 列 vs label）
- XGBoost/LightGBM 的 DMatrix 建構是 column-by-column
- SHAP 是 feature-by-feature

### 10.2 真正需要的是 **Column Store**，不是 Wide Table

| 需求 | Wide Table | Column Store |
|---|---|---|
| L6.5 winsorize | 讀 453k 列 → 逐列 clip | 逐列 clip（相同） |
| IC Analysis | 讀 453k 列 → 取 1 列 vs label | 直接取 1 列 vs label |
| ML Training | 全部載入 → DMatrix | Column 迭代載入 |
| Storage | 23 GB monolithic file | 453k 個 ~51 KB 列或 column-group files |

### 10.3 量化問題：記憶體搬運次數

以 1h 的 227,459 列資料為例，追蹤一個 L3 特徵的生命週期：

| 階段 | IO 操作 | 觸碰次數 |
|---|---|---|
| L3 計算 | rolling → 寫入 L3 memmap | 寫 1 次 |
| concat | np.asarray(L3 memmap) → copy 到 concat memmap | 讀 1 + 寫 1 |
| align | 讀 concat memmap chunk → merge_asof → 寫入 align memmap | 讀 1 + 寫 1 |
| final concat | np.asarray(align memmap) → copy 到 final memmap | 讀 1 + 寫 1 |
| L6.5 | 讀 final memmap chunk → transform → 寫入 L6.5 memmap | 讀 1 + 寫 1 |
| persist | 讀 L6.5 memmap → 寫入 HDF5 | 讀 1 + 寫 1 |
| **合計** | | **讀 5 + 寫 6 = 11 次觸碰** |

**每個 float32 值被搬運了 11 次**。理想情況下應該是 **2 次**（計算 1 次 + 持久化 1 次）。

---

## 11. First Principle 解法：Column-Group Streaming Architecture（CGSA）

### 11.1 五個必須同時滿足的不變量

1. **固定工作集上限（Bounded Working Set）**：任一時刻 RAM 中的資料量 ≤ 2 GB
2. **最多觸碰兩次（Dual-Touch Maximum）**：每個 float32 值最多 compute + persist
3. **算子流式拼接（Operator Fusion）**：L2→L3→align→L6.5→persist 在同一列上連續執行
4. **可觀測性內建（Heartbeat Everywhere）**：每個 stage 每 5 秒必須有 progress log
5. **數值等價（Quality Invariance）**：新架構輸出與現有完全一致（column name + values）

### 11.2 架構設計

```
                      ┌─────────────────────────────────────┐
                      │     Column Group Registry            │
                      │  { group_id → metadata + disk_path } │
                      └──────────┬──────────────────────────┘
                                 │
    ┌──── per timeframe ─────────┤
    │                            │
    ▼                            ▼
┌─────────┐  ┌──────────┐  ┌──────────────────────────────────┐
│ L0 fetch │→│ L1 atomic │→│ L2 derived (per-source-column)    │
│ (DF 10c) │  │ (DF 1683c)│  │  → emit column_group to disk     │
└─────────┘  └──────────┘  └─────────┬────────────────────────┘
                                      │ for each column_group:
                                      ▼
                             ┌──────────────────┐
                             │ L3 rolling        │
                             │ (per group, per W) │
                             │  → emit to disk    │
                             └────────┬───────────┘
                                      │
                             ┌────────▼───────────┐
                             │ TF Align (if 12h)   │
                             │ searchsorted gather  │
                             │  → write aligned col │
                             └────────┬───────────┘
                                      │
                             ┌────────▼───────────┐
                             │ L6.5 preprocess     │
                             │ (per column group)   │
                             │ winsor → rank → zsc  │
                             └────────┬───────────┘
                                      │
                             ┌────────▼───────────┐
                             │ Persist (HDF5 /     │
                             │  Parquet col-group)  │
                             └─────────────────────┘
```

### 11.3 關鍵差異 vs 現行

| 方面 | 現行 | CGSA |
|---|---|---|
| 寬表 concat | 5 次全域 concat（每次 11+ GB） | **0 次全域 concat** |
| memmap 同時存活 | 4-5 個 × 11 GB = 46+ GB | **最多 1 個 × 2 GB** |
| np.asarray 呼叫 | 每 concat DF size 次 | **0 次**（直接 numpy 輸出） |
| TF align | merge_asof per 5k-col chunk | **searchsorted gather per column-group** |
| L6.5 輸入 | 453k cols wide table | **per column-group 獨立處理** |
| 資料觸碰次數 | 11 次 | **2 次** |
| RAM 峰值 | >8 GB（thrashing） | **<2 GB**（bounded） |

### 11.4 Column Group 定義

一個 column_group 是同一 (source, indicator, layer) 產生的一組相關欄位：

```python
# 例如 EMA 指標的 column group:
{
    "group_id": "trend_EMA_close",
    "layer": "L1",
    "source": "close",
    "indicator": "EMA",
    "columns": ["ema_5", "ema_8", "ema_13", ..., "ema_233"],  # ~10 cols
    "data_path": "/tmp/ff_cg_trend_EMA_close.npy",
    "shape": (12888, 10),
    "dtype": "float32"
}
```

L2 會為每個 L1 group 衍生出新 groups：
```python
# EMA 的 derived group:
{
    "group_id": "derived_EMA_close",
    "parent": "trend_EMA_close",
    "columns": ["ema_5_pct", "ema_5_log_ret", ...],  # ~30 cols per parent
}
```

L3 會為每個 (L1 group, window, agg) 產生新 group：
```python
# EMA rolling mean W5:
{
    "group_id": "rolling_EMA_close_mean_W5",
    "columns": ["ema_5_mean_W5", ..., "ema_233_mean_W5"],
}
```

### 11.5 對 A/B/F 的效果

| 區段 | 現行秒數 | CGSA 預估 | 改善原因 |
|---|---:|---|---|
| A (L0~L6) | 741 | ~200s | L2/L3/L4 直接寫 column-group 到 disk，不經 DataFrame→concat |
| B (concat+align) | 836 | ~50s | **無全域 concat**；align 用 searchsorted 一次性 index map |
| C (12h 計算) | 37 | ~30s | rows 少，差異小 |
| D (12h concat+align) | 158 | ~30s | 同 B，無全域 concat |
| E (final merge) | 108 | **0s** | **消除**：不需要 final wide table |
| F (黑箱) | 8,365 | **0s** | **消除**：不存在 23.4 GB 全域 concat |
| L6.5 (未到達) | ??? | ~120s | per-group 處理，RAM 峰值 <2 GB |
| **預估總計** | >10,245 | **~430s (~7min)** | |

### 11.6 對生產環境（數百 Symbols × 3-4 TF）的延展性

| 場景 | 現行 | CGSA |
|---|---|---|
| 1 symbol × 2 TF | 170+ min（未完成） | ~7 min |
| 1 symbol × 4 TF | OOM（不可能） | ~14 min（線性增長） |
| 100 symbols × 2 TF | OOM | ~700 min（可平行化） |
| 100 symbols × 2 TF × 4 workers | N/A | ~175 min |
| 100 symbols × 4 TF × 8 workers | N/A | ~175 min |

**CGSA 的平行化天然友好**：每個 symbol 完全獨立，column-group 不共享 memmap → 可以多進程平行。

### 11.7 CGSA 下的 Multi-Timeframe 流程重設計

#### 11.7.1 現行 Multi-TF 流程的致命問題

現行 `MultiTFGenerator.generate_multi_tf()` 的完整流程：

```
for each training_tf in [1h, 12h]:        ← 順序處理，不平行
    raw = L0_fetch(symbol, tf)
    L1 = atomic(raw)                       ← 各 TF 獨立
    L2 = derived(L1, raw)                  ← 各 TF 獨立
    L3 = rolling(L1)                       ← 各 TF 獨立
    L4 = lag(L1, L2, L3, raw)              ← 各 TF 獨立
    L5 = cross_sectional(L1, L2)           ← 各 TF 獨立
    L6 = meta(L1, L2, raw)                 ← 各 TF 獨立
    
    combined = _combine_layers([L1..L6])   ← ⚠️ 第一次全域 concat（per-TF）
    aligned = align_to_primary(combined)   ← ⚠️ 第二次全量搬運（merge_asof）
    aligned = _apply_timeframe_tag(aligned)← ⚠️ rename → DataFrame copy
    aligned_outputs.append(aligned)        ← ⚠️ 所有 aligned DF 同時存活

merged = _combine_layers(aligned_outputs)  ← ⚠️ 第三次全域 concat（cross-TF）
L6.5 = preprocess(merged)                  ← ⚠️ 在 453k 列 wide table 上操作
persist(merged)                            ← ⚠️ 寫出 23.4 GB
```

**5 個隱藏問題**：

| # | 問題 | 時間成本 | 記憶體成本 |
|---|---|---|---|
| 1 | **各 TF 順序處理**：1h 和 12h 的 L0~L6 完全獨立，但以 `for` 迴圈順序執行 | 1h(741s) + 12h(37s) = 778s，平行化可降到 ~741s | 無改善 |
| 2 | **per-TF 內部 concat**：`_combine_layers([L1..L6])` 對每個 TF 做一次全域 concat | 1h: B1=383s, 12h: ~5s = 388s | 1h: 11.73 GB memmap |
| 3 | **自我對齊浪費**：primary TF=1h，training 包含 1h → `align_to_primary(1h→1h)` 執行了 merge_asof 但結果是 identity | B2=298s（完全浪費） | 11.73 GB align memmap（與 concat memmap 相同資料！） |
| 4 | **column rename copy**：`_apply_timeframe_tag()` 對 227k 欄 DataFrame 呼叫 `.rename()` → 觸發全量 column index 重建 | ~15-30s（隱含在 B3=154s 中） | column index 物件的 memory |
| 5 | **aligned_outputs 全部同時存活**：2 個 aligned DF（各 11.7 GB memmap-backed）在 `merged = _combine_layers(aligned_outputs)` 前都活著 | 等待最終 concat | 2 × 11.7 = 23.4 GB 同時存活 |

**問題 3 是最嚴重的**：37.3% 的 ABCDE 時間（B2=298s）是在做「1h 對齊到 1h」——一個 identity 操作。

#### 11.7.2 現行 Multi-TF 的資料搬運清單

以 1h TF（primary）的一個 L3 特徵為例，追蹤 multi-TF 流程中每一次觸碰：

| 步驟 | 操作 | 觸碰 |
|---|---|---|
| L3 compute | rolling → 寫入 L3 memmap | W1 |
| per-TF concat | np.asarray(L3 memmap) → copy 到 1h_concat memmap | R1 + W2 |
| 1h→1h align | 讀 concat memmap → merge_asof → 寫入 align memmap | R2 + W3 |
| TF tag rename | .rename() → column index copy | (metadata only) |
| cross-TF concat | np.asarray(align memmap) → copy 到 final memmap | R3 + W4 |
| L6.5 | 讀 final memmap → transform → 寫入 L6.5 memmap | R4 + W5 |
| persist | 讀 L6.5 memmap → 寫 HDF5 | R5 + W6 |
| **合計** | | **R5 + W6 = 11 次** |

**其中 R2+W3（1h→1h align）是完全浪費的 2 次觸碰**。

對於 12h TF（non-primary），align 是必要的，但觸碰次數相同：11 次。

#### 11.7.3 CGSA 下的 Multi-TF 重設計

```
┌───────────────────────────────────────────────────────────────────┐
│                    Multi-TF Orchestrator                          │
│                                                                   │
│  Step 1: 建立 primary TF 的 searchsorted index map                │
│          idx_map[tf] = searchsorted(source_ts[tf], primary_ts)   │
│          ※ primary TF 的 idx_map = identity (arange)             │
│                                                                   │
│  Step 2: 平行處理各 TF（ThreadPoolExecutor / ProcessPool）        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  TF=1h       │  │  TF=12h      │  │  TF=4h (未來)│            │
│  │  L0→L1→...   │  │  L0→L1→...   │  │  L0→L1→...   │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                  │                    │
│  Step 3: per column-group 流式處理                                 │
│  for each column_group from any TF:                               │
│      data = compute L2→L3→L4 (numpy/Polars/Numba)                │
│      if tf != primary:                                            │
│          data = data[idx_map[tf], :]    ← searchsorted gather    │
│      else:                                                        │
│          pass                           ← 跳過！identity！       │
│      tag_columns(data, tf)              ← 只改 metadata，不 copy  │
│      L6.5_transform(data)               ← in-place winsor/rank   │
│      persist(data, group_id, tf)        ← 寫 Parquet              │
│                                                                   │
│  ※ 任一時刻只有 1 個 column-group 在 RAM（~10 cols × 12888 rows） │
│  ※ 沒有任何全域 concat                                            │
│  ※ 沒有 aligned_outputs 列表（不累積 DF）                         │
└───────────────────────────────────────────────────────────────────┘
```

**CGSA Multi-TF 的關鍵設計決策**：

| 設計 | 現行 | CGSA Multi-TF |
|---|---|---|
| TF 處理順序 | 順序 for 迴圈 | **平行**（各 TF 的 L0~L3 獨立） |
| Primary TF align | merge_asof（浪費 298s） | **跳過**（identity → 零成本） |
| Per-TF concat | `_combine_layers([L1..L6])` = 11.7 GB | **消除**：column-group 直接 emit |
| Cross-TF concat | `_combine_layers(aligned_outputs)` = 23.4 GB | **消除**：column-group Registry 管理 |
| Column tagging | `.rename()` → DF copy | **metadata only**（group_id 包含 TF prefix） |
| aligned DF 生命週期 | 全部同時存活（23.4 GB） | **即時 persist → 釋放**（~0.5 MB peak） |
| L6.5 輸入 | 453k 列 wide table | **per-group**（~10 列 × 12888 rows） |

#### 11.7.4 CGSA Multi-TF 的觸碰次數

| 特徵來源 | 步驟 | 觸碰 |
|---|---|---|
| Primary TF (1h) 的特徵 | L3 compute → L6.5 inplace → persist | **W1 + W2 = 2 次** |
| Non-primary TF (12h) 的特徵 | L3 compute → searchsorted gather → L6.5 inplace → persist | **W1 + R1(gather) + W2 + W3 = 4 次** |

**對比現行的 11 次，Primary TF 降到 2 次（-82%），Non-primary TF 降到 4 次（-64%）**。

#### 11.7.5 修正後的效能預估（含 Multi-TF 優化）

| 區段 | 現行秒數 | 原始 CGSA 預估 | CGSA + Multi-TF 優化 | 改善說明 |
|---|---:|---:|---:|---|
| A (1h L0~L6) | 741 | ~200s | ~200s | 同原預估 |
| B1 (1h concat) | 383 | ~0s | **0s** | CGSA 消除 |
| B2 (1h→1h align) | 298 | ~50s | **0s** | ⭐ 跳過 self-alignment |
| B3 (post-align gap) | 154 | ~0s | **0s** | 無 combine_layers / rename |
| C (12h L0~L3) | 37 | ~30s | ~30s | ※ 可與 A 平行 → 實際 0s |
| D1 (12h concat) | ~5 | ~0s | **0s** | CGSA 消除 |
| D2 (12h align) | ~153 | ~30s | ~5s | searchsorted（rows=1082 → 12888 gather） |
| E (final merge) | 108 | **0s** | **0s** | CGSA 消除 |
| F (page thrashing) | 8,365 | **0s** | **0s** | CGSA 消除 |
| L6.5 | 未到達 | ~120s | ~120s | per-group 處理 |
| **總計** | >10,245 | **~430s** | **~355s (~5.9min)** | |
| ※ 若 TF 平行化 | | | **~325s (~5.4min)** | A 與 C 平行 → C 免費 |

#### 11.7.6 Multi-TF 擴展場景（3-4 TF）

若 training_tfs = [1h, 4h, 12h, 1d]（4 個 TF）：

| 指標 | 現行 | CGSA + Multi-TF |
|---|---|---|
| 全域 concat 次數 | 4 (per-TF) + 1 (cross-TF) = **5 次** | **0 次** |
| Align 次數 | 4 次（含 1 次 self-align 浪費） | **3 次**（跳過 primary self-align） |
| 同時存活 memmap | 4 × aligned + final = **~58 GB** | **< 2 GB** |
| 資料觸碰（primary 特徵） | 11 次 | **2 次** |
| 資料觸碰（non-primary 特徵） | 11 次 | **4 次** |
| TF 計算方式 | 順序（sum of all TF times） | **平行**（max of TF times） |
| 預估時間 | OOM（不可能完成） | **~350s（含 3 個 TF 對齊）** |

---

## 12. Ultra Think：現有方案的盲點與遺漏分析

> 在提出更多方案前，先自我審查 Section 11 的 CGSA + Polars 方案有什麼隱藏假設和遺漏。

### 12.1 CGSA 方案的隱藏假設

CGSA 假設「每個 column-group 完全獨立處理」——但這在以下 Layer 不成立：

| Layer | 獨立性 | 反例 |
|---|---|---|
| L1 (atomic) | ✅ 完全獨立 | 各指標互不依賴 |
| L2 (derived) | ⚠️ **部分依賴** | Cross = EMA_5 - EMA_21（跨 column-group）；Ratio = RSI / EMA（跨 indicator） |
| L3 (rolling) | ✅ 每列獨立 | rolling 只看自己的歷史 |
| L4 (lag) | ✅ 每列獨立 | shift 只看自己 |
| L5 (cross-sec) | ❌ **全域依賴** | 需要 BTCUSDT 同名 feature 做 relative strength |
| L6 (meta) | ⚠️ **部分依賴** | consensus = 多指標投票；interaction = 兩列相乘 |
| L6.5 (preprocess) | ⚠️ **rank 需全域** | `rank(pct=True)` 需看同一列所有 rows 的分佈 |

**關鍵問題**：L2 的 Cross/Ratio 操作需要同時存取兩個不同 column-group 的數據。CGSA 如果嚴格按「一次只載一個 group」，Cross 就無法計算。

**解法**：L2 的跨 group 操作（Cross, Ratio）在 L1 完成後**立即計算**（L1 全量 1,683 cols = 87 MB，完全放得進 RAM），然後再進入 per-group 的 streaming L3。

### 12.2 Polars 方案的隱藏限制

1. **TA-Lib 綁定問題**：TA-Lib 的 Python binding 只接受 numpy array，不接受 Polars Series。L1 必須走 numpy → 結果得轉回 Polars。但 Polars `from_numpy` 是 zero-copy（若 array 是 contiguous），所以這不是大問題。

2. **Polars rolling 的 NaN 處理語義**：pandas `rolling.mean()` 預設 `min_periods=1`（NaN 部分跳過），Polars `rolling_mean` 預設 `min_periods=window`（window 開頭全 NaN）。必須顯式對齊。

3. **Polars rolling rank 不存在**：Polars **沒有** `rolling.rank(pct=True)` 的直接等價。需要用 `map_batches` + custom function 或 Numba，否則效能可能比 pandas 更差。

4. **Memory 並沒有更少**：Polars LazyFrame streaming 的記憶體節省來自「不物化中間 DF」。但如果最終仍需 453k 列的物化結果（寫 Parquet/HDF5），記憶體峰值不會降低——除非同時搭配 CGSA。

**結論**：Polars 單獨使用不足以根治，必須與 CGSA 搭配才有意義。

### 12.3 Multi-TF 流程的隱藏成本（原文件完全遺漏）

**原文件中 multi-TF 的分析只停留在「E 段 108s 做 cross-TF concat」和「searchsorted 取代 merge_asof」的層面，完全沒有分析以下問題**：

#### 問題 1：Primary TF 自我對齊浪費（B2 = 298s，占 ABCDE 的 15.8%）

```python
# multi_tf_generator.py 第 122 行
aligned = TimeframeAligner.align_to_primary(
    combined,        # 1h features
    timeframe,       # "1h"
    primary_timestamps,
    self._primary_tf,  # "1h"
    ...
)
```

當 `timeframe == self._primary_tf` 時，這個 align 是 **identity 操作**——但現行程式碼仍然執行了完整的 merge_asof（46 chunks × ~6.5s/chunk = 298s），並建立了 11.73 GB 的 align memmap。

**即使不做 CGSA，單純加一行 `if timeframe == primary_tf: skip align` 就能省 298s（15.8%）**。

#### 問題 2：per-TF 內部的 `_combine_layers` 是多餘的中間 concat

```python
# multi_tf_generator.py 第 120 行
combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
```

這對每個 TF 做了一次全域 concat（1h: 5 DFs → 11.73 GB memmap，12h: 5 DFs → 0.98 GB）。但這個 concat 的唯一目的是傳給 `align_to_primary()`。如果 align 改用 searchsorted，完全可以 **per-layer 獨立 align**，省掉 per-TF concat。

#### 問題 3：`_apply_timeframe_tag()` 的隱藏 copy

```python
# multi_tf_generator.py 第 124 行
aligned = self._apply_timeframe_tag(aligned, timeframe)
```

`DataFrame.rename(columns=rename_map)` 對 227k 列的 DataFrame 會：
1. 建立新的 column Index 物件
2. 觸發 BlockManager 的 column reference 更新
3. 在某些 pandas 版本中會觸發 copy

**在 CGSA 中完全不需要**——column-group 的 `group_id` 天生包含 TF prefix（如 `"1h_trend_EMA_close"`），不需要事後 rename。

#### 問題 4：所有 aligned_outputs 同時存活

```python
aligned_outputs.append(aligned)  # 每個 TF append 一個 ~11.7 GB DF
```

到 cross-TF concat 前，2 個 aligned DF 同時在 memory（backed by memmap = 23.4 GB 的 disk-backed pages）。對於 4 TF 場景：4 × 11.7 GB = 46.8 GB 同時存活 → page cache 被完全壓垮。

#### 問題 5：各 TF 順序執行但計算完全獨立

1h 和 12h 的 L0~L6 計算**零依賴**——它們讀不同的 HDF5 資料、用不同的 rows、生成不同的 features。現行用 `for` 迴圈順序處理，浪費了 M1 的多核能力。

**以上 5 個問題在 Section 11.7 的 CGSA Multi-TF 重設計中全部解決**。

### 12.4 搬運次數分析的遺漏

Section 10.3 計算「11 次觸碰」，但忽略了一個更根本的問題：

**L3 的 100 個 rolling step 中，每個 step 都觸發一次 `step_result.to_numpy(dtype=np.float32)` 寫入 memmap**。

以 1h 的 163,686 個 L3 欄位為例：
- 100 steps × 每 step 平均 1,637 cols × 12,888 rows × 4 bytes = **8.45 GB 寫入**
- 這些寫入到 L3 memmap 的資料，隨後又被 `np.asarray(df.values)` 全部讀出
- → L3 內部就已經是 **write-once + read-once = 2 次觸碰**
- 加上後續 concat/align/final/L6.5/persist 的 9 次 = **總共 11 次**

**但如果 L3 的輸出直接 pipe 給 L6.5 再 persist？**
- L3 compute → L6.5 transform → persist = **3 次觸碰**（compute + transform + write）
- 若 L6.5 是 in-place（winsor+rank+zscore 都是 element-wise）：**2 次觸碰**

這就是 CGSA 的 Operator Fusion 核心價值。

---

## 13. 超越現有方案的根治思路

> Ultra Think: 從演算法、語言、計算模型、資料結構、硬體特性五個維度，檢驗是否有比 CGSA+Polars 更好的根治方案。

### 13.1 方案 H：DuckDB 全管線引擎（SQL-native pipeline）

**核心思想**：不用 Python DataFrame 做計算，全部委託給 DuckDB 的向量化 SQL 引擎。

```sql
-- L1: TA-Lib 結果先寫入 DuckDB temp table (一次 bulk insert)
CREATE TABLE l1_features AS SELECT * FROM read_parquet('l1_output.parquet');

-- L2: derived operators 全部用 SQL 表達
CREATE TABLE l2_features AS
SELECT *,
  (ema_5 - ema_21) AS cross_ema_5_21,
  (close - ema_5) / NULLIF(ema_5, 0) AS dist_ema_5,
  (rsi_14 / NULLIF(ema_21, 0)) AS ratio_rsi_14_ema_21,
  lag(ema_5, 1) OVER (ORDER BY open_time) AS ema_5_lag1,
  ...
FROM l1_features;

-- L3: rolling aggregation 用 window functions
CREATE TABLE l3_features AS
SELECT *,
  AVG(ema_5) OVER (ORDER BY open_time ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS ema_5_mean_W5,
  STDDEV(ema_5) OVER (ORDER BY open_time ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS ema_5_std_W5,
  ...
FROM l2_features;

-- L6.5: preprocessing
CREATE TABLE l65_features AS
SELECT *,
  PERCENT_RANK() OVER (ORDER BY ema_5_mean_W5) AS ema_5_mean_W5_rank,
  ...
FROM l3_features;

-- Persist: 直接 export
COPY l65_features TO 'features.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
```

**DuckDB 的優勢**：
| 維度 | Python pipeline | DuckDB |
|---|---|---|
| 執行模型 | 逐行/逐 chunk Python | 向量化 C++ morsel-driven parallelism |
| 記憶體管理 | pandas BlockManager / memmap | DuckDB buffer manager（自適應 spill-to-disk）|
| 平行化 | GIL 限制（需 multiprocessing）| **自動多核，無 GIL** |
| Wide table concat | 需要全域 concat | **不需要**（SQL query planner 自動最佳化）|
| Rolling window | pandas Cython（單核） | DuckDB window functions（多核） |
| Disk spill | memmap（手動管理）| **自動 spill + 自適應 buffer**（不需手動） |
| Join asof | pd.merge_asof | DuckDB `ASOF JOIN`（原生、多核）|

**DuckDB 的限制**：
1. **TA-Lib 無法在 SQL 中呼叫**：L1 仍需 Python → TA-Lib → 寫 Parquet → DuckDB 讀入
2. **453,953 列的 SQL 生成**：需要 code generator 動態產生 SQL（每個 indicator × window × agg 一個 expression）
3. **window function 的 453k 列**：DuckDB 的 query planner 可能不預期單 SELECT 有 453k 列
4. **skew/kurt 不是 built-in**：DuckDB 沒有 `ROLLING_SKEW`，需要 UDF 或 SQL 公式表達
5. **滾動 rank**：DuckDB 有 `PERCENT_RANK()` 但是是全域 rank，不是 rolling window rank

**適用性判斷**：DuckDB 作為全管線替代的可行性 **中等偏低**——L3 rolling 的 skew/kurt/rank 是核心障礙。但作為 **L2 + align + L6.5 + persist** 的引擎非常有價值。

### 13.2 方案 I：Rust native pipeline（Python→Rust FFI）

**核心思想**：用 Rust 寫一個 native feature pipeline library，通過 PyO3 暴露給 Python。

**為什麼考慮 Rust**：
- Polars 本身就是 Rust 寫的；用 Polars 等於「隔了一層 Python wrapper 呼叫 Rust」
- 直接用 Rust 可以精確控制記憶體佈局、SIMD 指令、多核排程
- 消除 Python→Polars→Rust→結果→Python 的序列化開銷

**Rust 能做到的**：
```rust
// 概念：streaming rolling aggregator，zero-allocation
fn streaming_rolling_pipeline(
    input: &[f32],      // L1 column, mmap'd
    windows: &[usize],   // [5, 8, 13, ..., 233]
    output: &mut MmapMut, // 直接寫入 mmap file
) {
    // 使用 SIMD (NEON on M1) 計算 rolling stats
    // 一次 scan: 同時更新所有 windows 的 mean/std/min/max
    // 產出直接寫入 output mmap，不經中間分配
}
```

**Rust 的優勢**：
- **零分配 rolling**：用 ring buffer / deque 維護窗口，O(1) amortized per step
- **SIMD (ARM NEON on M1)**：8×float32 並行，rolling mean/std 可用 SIMD
- **多核無 GIL**：rayon 自動分配工作到所有核心
- **記憶體精確控制**：可以保證任一時刻只有固定量 RAM

**Rust 的劣勢**：
- **開發成本極高**：需要 Rust expertise + PyO3 FFI 經驗
- **維護成本高**：每次新增指標或修改 pipeline 都需要改 Rust 程式碼
- **TA-Lib 整合**：TA-Lib 是 C 函式庫，Rust 可以用 FFI 呼叫，但 binding 品質參差

**適用性判斷**：**不推薦**。Polars 已經是 Rust 的上層包裝，獲得了 90% 的 Rust 效能收益但開發成本只有 10%。除非 Polars 證明不足，否則不值得。

### 13.3 方案 J：Array Database（ClickHouse / TimescaleDB）

**核心思想**：把特徵計算交給專門的 time-series database。

**ClickHouse 優勢**：
- 向量化列式存儲引擎，window functions 極快
- 支援 `windowFunnel`、`retention` 等 analytics functions
- 可以處理寬表（但 453k 列超過建議上限）

**實際限制**：
- ClickHouse/TimescaleDB 的 column 數限制通常在 ~10k
- 453k 列超出所有 RDBMS/OLAP 系統的設計範圍
- 需要把資料轉成 **long format**（row per feature per timestamp），查詢模式完全不同

**適用性判斷**：**不適用**。453k 列超出所有 array/time-series DB 的設計假設。

### 13.4 方案 K：Dask / Ray DataFrame（分散式計算）

**核心思想**：用 Dask DataFrame 或 Ray Dataset 做平行計算和 out-of-core 處理。

**Dask 優勢**：
- 原生支援 out-of-core（chunked） DataFrame
- `dask.dataframe.rolling()` 自動分 partition
- 可以透明地利用多核
- API 和 pandas 幾乎一致

**Dask 的根本問題**：
1. **同樣是 Wide Table**：Dask 把 DataFrame 切成 row-partitions，不是 column-partitions → 453k 列的問題完全不解
2. **Overhead per task**：Dask 每個 task 有 ~1ms overhead → 100 rolling steps × 46 chunks = 4,600 tasks → 4.6s overhead
3. **Rolling across partitions**：rolling window 需要 partition 之間的 overlap → 額外 IO
4. **不解決 concat**：Dask 的 concat 最終也會 materialize

**Ray 的相同問題**：Ray Dataset 也是 row-based partitioning。

**適用性判斷**：**不推薦**。Dask/Ray 解決的是「data too many rows, one machine can't fit」。我們的問題是「data too many columns, one DataFrame can't handle」。方向錯誤。

### 13.5 方案 L：numpy + Numba 全管線（Python-native 極致優化）

**核心思想**：不引入任何新 DataFrame 函式庫。全程只用 numpy ndarray + Numba JIT，徹底避開 pandas/Polars 的 overhead。

**架構**：
```
L0: HDF5 → numpy array (12888 × 10) = 0.5 MB
L1: TA-Lib(numpy) → numpy array (12888 × 1683) = 87 MB
L2: Numba(numpy) → per-group .npy files on disk
L3: Numba rolling(numpy) → per-group .npy files on disk
L4: numpy shift → per-group .npy files on disk
align: searchsorted + fancy indexing（純 numpy）
L6.5: Numba winsor/rank/zscore → per-group .npy files on disk
persist: per-group .npy → final Parquet (via pyarrow)
```

**為什麼這可能比 Polars 更好**：
1. **零 DataFrame overhead**：完全繞過 pandas BlockManager 和 Polars Arrow buffer
2. **精確控制 memory layout**：C-order、column-major、可選 mmap — 由我們決定
3. **Numba 在 M1 上的表現**：Numba 利用 LLVM 編譯到 ARM64 native code，效能接近 C
4. **不需要 Polars 的 copy semantics**：Polars 的 immutable data model 意味着某些 inplace 操作必須 copy，numpy 不必

**L2 全部 Numba 化的範例**：
```python
@numba.njit(parallel=True)
def compute_derived_batch(
    l1_data: np.ndarray,   # shape = (N, 1683) float32
    output: np.ndarray,     # shape = (N, 48591) float32, pre-allocated
):
    """一次掃描所有 L1 列，生成所有 L2 derived features。"""
    N, n_cols = l1_data.shape
    out_idx = 0
    for col in numba.prange(n_cols):
        series = l1_data[:, col]
        # pct_change
        for i in range(1, N):
            prev = series[i-1]
            if prev == 0.0 or np.isnan(prev):
                output[i, out_idx] = np.nan
            else:
                output[i, out_idx] = (series[i] - prev) / prev
        output[0, out_idx] = np.nan
        out_idx += 1
        # log_return
        for i in range(1, N):
            prev = series[i-1]
            curr = series[i]
            if prev <= 0.0 or curr <= 0.0 or np.isnan(prev) or np.isnan(curr):
                output[i, out_idx] = np.nan
            else:
                output[i, out_idx] = np.log(curr / prev)
        output[0, out_idx] = np.nan
        out_idx += 1
        # ... more operators
```

**L3 全部 Numba 化（多 window 融合）**：
```python
@numba.njit
def fused_rolling_all_windows(
    col: np.ndarray,          # (N,) float32 — 單一列
    windows: np.ndarray,       # [5, 8, 13, 21, 34, 55, 89, 144, 177, 233]
    output: np.ndarray,        # (N, n_windows * n_aggs) — pre-allocated
):
    """一次掃描，同時計算所有 window 的 mean/std/min/max/rank/skew/kurt/slope。
    使用 incremental online algorithms：
    - mean/std: Welford's online algorithm（O(1) per step per window）
    - min/max: monotonic deque（amortized O(1)）
    - rank: sorted insert + bisect（O(log W)）
    - skew/kurt: online 3rd/4th moment（O(1) per step）
    - slope: online linear regression（O(1) per step，基於 running sums）
    """
    # 單次 O(N) 掃描，並行更新所有 window 的 running statistics
    # 記憶體：每個 window 只需 O(W) 的 deque/buffer
```

**優勢**：
- **理論最優 FLOP count**：每個 float 只觸碰必要次數
- **記憶體恰好 = 輸出大小 + 工作 buffer**：沒有中間 DataFrame
- **Numba JIT compilation cache**：首次慢（~5s compile），後續 instant

**劣勢**：
- **開發複雜度高**：需手寫每個 operator 的 Numba 版本
- **除錯困難**：Numba nopython mode 的限制（不能用 pandas, 不能 print etc.）
- **skew/kurt online algorithm 數值穩定性**：需要仔細實作避免 catastrophic cancellation

### 13.6 方案 M：Hybrid 最佳化（CGSA + Polars L2/L6.5 + Numba L3）

**核心思想**：不追求單一引擎統一，而是每層選用最適合的引擎。

| Layer | 引擎選擇 | 理由 |
|---|---|---|
| L0 | pandas → numpy | HDF5 讀取只有 10 列，什麼都快 |
| L1 | TA-Lib (C) → numpy array | TA-Lib API 要求 numpy，效能已最優 |
| L2 | **Polars expressions** | Polars 的 `with_columns()` 可一次生成所有 derived，lazy eval 自動批次化 |
| L3 | **Numba fused rolling** | Polars 的 rolling rank 不存在；Numba 可做 multi-window fusion |
| L4 | numpy `np.roll` / Polars `shift` | 簡單操作，哪個都行 |
| L5 | Polars `join` + 比值計算 | cross-sectional 需要兩個 symbol 的 join |
| L6 | Polars expressions | consensus/interaction = column-wise 運算 |
| Align | **numpy searchsorted** | O(N log N) 一次排序 + O(N) gather，比任何 join 都快 |
| L6.5 | **Polars expressions** | winsorization(clip) + rank + zscore 是 Polars 強項 |
| Persist | **Parquet (PyArrow)** | Arrow 生態一致性 |

**這個 Hybrid 比「全 Polars」或「全 Numba」好在哪**：
- L3 的 rolling rank/skew/kurt 在 Polars 中**沒有高效原生實作**，強用 Polars 反而慢
- L2/L6.5 的 element-wise 操作在 Polars 中**極高效**（向量化 Rust，自動多核）
- 不需要統一到單一技術棧，降低遷移風險

---

## 14. 深度比較：所有方案完整評估

### 14.1 延伸方案矩陣（含新方案 H~M）

| 方案 | 改動量 | 風險 | 效果 | RAM 峰值 | 多核利用 | 維護成本 | 適用性 |
|---|---|---|---|---|---|---|---|
| A. numpy block-copy 修補 | 小 | 低 | B1 加速 2-3x | 不變 | ❌ | 低 | 止血 |
| B. searchsorted 取代 merge_asof | 中 | 低 | B2 加速 20x | 不變 | ❌ | 低 | ✅ 立即可做 |
| C. Polars 替代 pandas (L2~L6.5) | 大 | 中 | 全域 3-10x | 降低 | ✅ | 中 | ⚠️ L3 有缺口 |
| D. CGSA column-group streaming | 大 | 中 | 消除 concat/F | <2GB | ❌ | 中 | ✅ 根治 |
| E. Parquet 持久化 | 中 | 低 | 下游加速 | 不變 | ❌ | 低 | ✅ 配合 D |
| F. Numba JIT L3 算子 | 中 | 低 | L3 加速 3-5x | 不變 | ✅ | 中 | ✅ 配合 D |
| G. DuckDB 下游分析 | 小 | 低 | IC/ML 加速 | 自適應 | ✅ | 低 | ✅ 配合 E |
| **H. DuckDB 全管線** | 大 | 高 | 3-10x | 自適應 | ✅ | 高 | ⚠️ L3 rank/skew 不支援 |
| **I. Rust native pipeline** | 極大 | 高 | 理論最優 | 最優 | ✅ | 極高 | ❌ 開發成本不合理 |
| **J. ClickHouse/TimescaleDB** | 大 | 高 | 不適用 | N/A | ✅ | 高 | ❌ 453k 列超限 |
| **K. Dask/Ray** | 中 | 中 | <2x | 不變 | ✅ | 中 | ❌ 方向錯誤 |
| **L. numpy+Numba 全管線** | 極大 | 中 | 理論最優 | 最優 | ✅ | 高 | ⚠️ 除錯困難 |
| **M. Hybrid (CGSA+Polars+Numba)** | 大 | 中 | **接近理論最優** | <2GB | ✅ | **中** | ✅ **最佳平衡** |

### 14.2 淘汰分析

| 方案 | 淘汰原因 |
|---|---|
| I. Rust native | 開發成本極高，Polars 已提供 90% 收益 |
| J. Array DB | 453k 列超出任何 OLAP DB 設計極限 |
| K. Dask/Ray | 解決的是 row-scale 問題，我們是 column-scale 問題 |
| H. DuckDB 全管線 | L3 的 rolling rank/skew/kurt 無原生 SQL 實作，必須 UDF → 效能倒退 |
| L. 全 Numba | 接近理論最優但維護成本太高，每新增一個 operator 都要寫 Numba |
| A. block-copy | 只止血不根治，不進入最終方案 |

### 14.3 存活方案深度比較

**進入決賽的三個組合**：

| | 組合 1:「CGSA + Polars 全域」 | 組合 2:「CGSA + 全 Numba」 | 組合 3:「**CGSA + Hybrid M**」 |
|---|---|---|---|
| L2 引擎 | Polars expressions | Numba batch | **Polars expressions** |
| L3 引擎 | Polars rolling (缺 rank/skew/kurt) | Numba fused rolling | **Numba fused rolling** |
| L6.5 引擎 | Polars clip/rank/zscore | Numba per-col | **Polars clip/rank/zscore** |
| align | Polars join_asof | numpy searchsorted | **numpy searchsorted** |
| L3 rolling rank | ❌ 需 workaround | ✅ native Numba | ✅ native Numba |
| L3 rolling skew/kurt | ❌ 需 map_batches | ✅ online algorithm | ✅ online algorithm |
| L6.5 rank | ✅ Polars native | 需自己寫 | ✅ Polars native |
| 開發量估計 | 中 | 大 | **中**（L3 Numba + 其餘 Polars）|
| 除錯難度 | 低（Polars 有好的 error msg）| 高（Numba nopython 限制）| **中** |
| 數值驗證 | 需驗 Polars NaN 語義 | 需驗 online algorithm 精度 | **兩者都要驗，但範圍較小** |

**組合 3（Hybrid M）** 在效能和開發成本的 trade-off 上最優：
- 把 Numba 只用在 Polars 做不好的地方（L3 rolling rank/skew/kurt）
- 把 Polars 用在它最強的地方（L2 expressions, L6.5 rank/zscore）
- searchsorted 是演算法上的最優解，不需要任何 DataFrame 函式庫

### 14.4 Hybrid M 的預估效能（細分到每層）

| 階段 | 現行秒數 | Hybrid M 預估 | 計算依據 |
|---|---:|---:|---|
| L0 fetch | 0.01 | 0.01 | 不變 |
| L1 TA-Lib | 1 | 1 | C 函式庫，已最優 |
| L2 Polars expressions | ~48 (A2) | ~5 | SIMD + 多核（M1 8 cores），無 BlockManager |
| L3 前置（memmap 建立等） | ~307 (A3) | ~10 | CGSA 消除中間 concat；column-group 直接 .npy |
| L3 rolling (Numba fused) | 385 (A4) | ~60 | multi-window fusion: 10 windows 一次掃描 vs 100 獨立 rolling |
| L4 lag (Polars shift) | 含在 A3 | ~3 | 簡單 shift，極快 |
| L5 cross-sectional | <1 | <1 | 不變 |
| 1h concat | 383 (B1) | **0** | CGSA：無全域 concat |
| 1h align (searchsorted) | 298 (B2) | ~10 | O(N log N) sort + O(N) gather |
| 12h L1~L3 | 37 (C) | ~10 | rows=1082，什麼都快 |
| 12h concat+align | 158 (D) | ~5 | 同上，無 concat + searchsorted |
| Final merge | 108 (E) | **0** | CGSA：無 final wide table |
| F (page thrashing) | 8,365 (F) | **0** | CGSA：無 23.4 GB memmap |
| L6.5 Polars transform | 未到達 | ~60 | per-group winsor+rank+zscore，Polars 多核 |
| Persist (Parquet) | 未到達 | ~30 | per-group Parquet 寫入，zstd 壓縮 |
| **單 Symbol 總計** | **>10,245** | **~195s (~3.3min)** | |

### 14.5 較原始 CGSA+Polars 預估（~430s）更快的原因

1. **L2 加速**：原評估假設 L2 用 CGSA per-group → 仍有 Python loop overhead。改為 Polars `with_columns()` batch → SIMD 多核 → 48→5s
2. **L3 加速**：原評估假設 L3 仍是 100 individual steps。改為 Numba multi-window fused scanning → 一次掃描同時更新 10 windows → 385→60s
3. **L6.5 加速**：原評估假設 per-group 獨立處理。Polars 可以 batch 整個 column slice 做 rank → 比 per-column 更高效

---

## 15. 具體優化技術方案（全方位，含新方案）

### 15.1 Polars 替代 pandas（L2 / L6.5 計算層）

| 維度 | pandas | Polars | 改善 |
|---|---|---|---|
| 記憶體模型 | BlockManager（碎片化） | Arrow columnar（連續） | 消除 `np.asarray` 重組成本 |
| rolling 引擎 | Cython（GIL 限制） | Rust multi-thread | L3 可用所有 M1 核心 |
| concat | 建立新 BlockManager | Zero-copy column append | B1 的 254s 空白消除 |
| groupby/join | 單線程 | SIMD + 多線程 | 2-10x |
| lazy evaluation | 無 | LazyFrame → streaming | 可延遲計算，只 materialize 需要的 |
| join_asof | `pd.merge_asof`（逐 chunk） | `polars.join_asof`（native） | align 可一次完成 |
| 記憶體峰值 | 持有所有中間態 | streaming 可控 peak | 可限制在 2 GB |
| 與 numpy 互操作 | `.values` → copy | `.to_numpy(zero_copy_only=True)` | Zero-copy |

**Polars 在 Hybrid M 中的角色**：
- L1（TA-Lib）仍需 numpy → Polars `from_numpy` zero-copy 接手
- L2 用 Polars `with_columns()` 一次計算所有 derived（28.9x 爆炸但都是 element-wise）
- L6.5 用 Polars 的 `clip` + `rank` + `(col - mean) / std` — 全部原生多核
- **不用 Polars 做 L3 rolling rank/skew/kurt**（Polars 缺原生支援）

### 15.2 Numba JIT 融合 rolling（L3 核心引擎）

**單次掃描多 window 融合**——這是比原方案（Section 12.6）更根本的優化：

```python
@numba.njit
def fused_rolling_stats(
    col: np.ndarray,              # (N,) float64 — 一個 L1 特徵列
    windows: np.ndarray,           # [5, 8, 13, 21, 34, 55, 89, 144, 177, 233]
    # output pointers for each (window, agg)
    out_mean: np.ndarray,          # (N, n_windows)
    out_std: np.ndarray,
    out_min: np.ndarray,
    out_max: np.ndarray,
    out_range: np.ndarray,
    out_zscore: np.ndarray,
    out_skew: np.ndarray,
    out_kurt: np.ndarray,
    out_rank: np.ndarray,
    out_slope: np.ndarray,
):
    """
    一次 O(N) 掃描，維護所有 windows 的 running statistics：
    
    演算法：
    - mean/std: Welford's online algorithm (add/remove from window)
    - min/max: 雙端 monotonic deque 維護（amortized O(1)）
    - rank: 維護 sorted window buffer + bisect_left（O(log W) per step）
    - skew/kurt: 擴展 Welford 到 3rd/4th central moments
    - slope: running sums of (x·y), (x), (y), (x²) → O(1) update
    - zscore: (val - mean) / std → 利用已算好的 mean/std
    - range: max - min → 利用已算好的 min/max
    
    記憶體：每個 window 需要 O(W) buffer → 最大 W=233 → 10 windows ≈ 10 KB
    """
    # Per-window state: ring buffer + running statistics
    n_windows = len(windows)
    for w_idx in range(n_windows):
        W = windows[w_idx]
        # Initialize ring buffer and statistics accumulators
        # ... (Welford, monotonic deque, sorted buffer)
    
    # Single pass: iterate through N rows
    for i in range(len(col)):
        val = col[i]
        for w_idx in range(n_windows):
            W = windows[w_idx]
            # 1. Add val to window, remove oldest if full
            # 2. Update mean/var (Welford delta method)
            # 3. Update min/max (deque push/pop)
            # 4. Update rank (sorted insert)
            # 5. Update 3rd/4th moments
            # 6. Update slope running sums
            # 7. Write all 10 agg results to output arrays
```

**關鍵加速**：
- 原始方式：100 步 × 每步建立 rolling object + 掃描全列 = **100N 次掃描**
- 融合方式：1 次掃描 × 內部更新 10 windows × 10 aggs = **1N 次掃描**
- 理論加速：**100×**（實際因 inner loop 複雜度 → 約 10-30×）

**數值穩定性注意**：
- Welford 的 3rd/4th moment 在 window>>100 時有數值穩定性問題
- 解法：使用 Pebay (2008) 的 parallel algorithm，每隔 W 步從 buffer 重算一次
- 或使用 two-pass: 先 online mean/std（精確），再用 buffer 計算 skew/kurt（buffer 只 O(W)）

### 15.3 searchsorted 替代 merge_asof（TF align）

```python
# 精確等價 merge_asof(direction='backward') 的 numpy 實作
def build_asof_index_map(
    primary_ts: np.ndarray,    # int64 ns timestamps, sorted
    source_ts: np.ndarray,     # int64 ns timestamps, sorted
    offset_ns: int = -1,       # OPEN_MINUS = -1ns
) -> np.ndarray:
    """
    output[i] = j where source_ts[j] <= (primary_ts[i] + offset_ns)
    等價於 merge_asof(left_on=primary, right_on=source, direction='backward')
    
    時間複雜度：O(N log M) where N=primary rows, M=source rows
    空間複雜度：O(N) output only
    """
    anchor = primary_ts + offset_ns
    idx = np.searchsorted(source_ts, anchor, side='right') - 1
    # searchsorted(..., 'right') - 1 → 最大的 j where source[j] <= anchor
    idx = np.clip(idx, 0, len(source_ts) - 1)
    
    # Validate: source_ts[idx] must be <= anchor (handle edge case)
    valid_mask = source_ts[idx] <= anchor
    idx[~valid_mask] = -1  # mark as unmatched → NaN later
    return idx

# 使用：所有 column-group 共用同一個 idx_map
idx_map = build_asof_index_map(primary_ts, source_ts, offset_ns=-1)
for group in column_groups:
    src = np.load(group.data_path, mmap_mode='r')  # read-only mmap
    aligned = np.empty((len(primary_ts), src.shape[1]), dtype=np.float32)
    valid = idx_map >= 0
    aligned[valid] = src[idx_map[valid], :]
    aligned[~valid] = np.nan
    np.save(group.aligned_path, aligned)
```

**對比**：
- 現行：46 chunks × merge_asof(DataFrame, sort, copy) = 298s
- searchsorted：1 次 sort + N 次 fancy index = **~5-10s**

### 15.4 Apache Arrow + Parquet（傳輸 + 持久化）

- Arrow IPC 作為 column-group 的 disk 格式（比 .npy 有 metadata）
- Parquet 作為最終持久化格式（壓縮率高、下游 Polars/DuckDB 原生讀取）
- `pyarrow.RecordBatch` 可 zero-copy 轉 Polars DataFrame / numpy array

### 15.5 DuckDB 下游分析引擎

- 特徵計算完成後，IC Analysis / ML 可透過 DuckDB 直接讀 Parquet
- 不需要把 453k 列全部載入 → DuckDB 只讀需要的 column
- 範例：`SELECT feature_name, corr(...) FROM read_parquet('features/*.parquet') GROUP BY feature_name`

### 15.6 多進程平行化

```python
# Hybrid M + multiprocessing:
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=min(8, os.cpu_count())) as pool:
    futures = {
        pool.submit(hybrid_m_pipeline, symbol, timeframes): symbol
        for symbol in symbols
    }
    # 100 symbols × ~3.3 min / 8 workers ≈ 41 min
```

---

## 16. 推薦方案與實施路線

### 16.1 最終推薦：方案 M（Hybrid — CGSA + Polars + Numba + searchsorted）

經過所有方案的 First Principle 分析和淘汰，**方案 M** 是最佳平衡：

| 維度 | 評分 | 說明 |
|---|---|---|
| 效能 | ⭐⭐⭐⭐⭐ | 接近理論最優（~195s vs 理論下限 ~120s） |
| 開發成本 | ⭐⭐⭐ | 需要重構 pipeline + 寫 Numba L3 |
| 維護成本 | ⭐⭐⭐⭐ | Polars/Numba 有活躍生態，不是 custom C/Rust |
| 風險 | ⭐⭐⭐⭐ | 每個組件可獨立驗證（Polars NaN、Numba 精度、searchsorted 等） |
| 延展性 | ⭐⭐⭐⭐⭐ | CGSA 天然支援 multi-symbol parallel |
| 品質不變量 | ⭐⭐⭐⭐⭐ | column name + 數值完全一致（透過 test suite 驗證) |

**註記**：維持方案 M 作為 end-state target，但執行順序仍以 Phase 0 → 1 → 2 → 3 為主。只有在 Phase 3 後重新 profile 仍證明 L2 / L6.5 是主瓶頸時，才推進 Phase 4 Polars，避免過早重構。

### 16.2 實施路線（依賴拓撲排序）

```
Phase 0  ─── 基礎建設（不改變現有行為）───
├─ 0.1  增加 L2 前後的計時 log（精確定位 A3 的 307s）
├─ 0.2  增加 F 段的 heartbeat log（每 30s 報告 page fault count）
└─ 0.3  建立數值等價 test suite（現有 pipeline 的 golden output）

Phase 1  ─── searchsorted align + Multi-TF 快修（最低風險，最快見效）───
├─ 1.1  實作 build_asof_index_map()
├─ 1.2  替換 _merge_asof_align_chunked() 
├─ 1.3  驗證：新 align vs 舊 align 數值完全一致
├─ 1.4  ★ Multi-TF: 跳過 primary self-alignment
│       在 MultiTFGenerator 中加 `if tf == primary_tf: skip align_to_primary()`
│       預計效果：B2 298s → 0s（pure identity operation 無需執行）
├─ 1.5  ★ Multi-TF: 各 TF 平行化
│       `concurrent.futures.ProcessPoolExecutor` 平行 L0~L6 per TF
│       預計附加效果：C(37s) 與 A(741s) 重疊 → C 免費
└─ 預計效果：B2 298s → 0s, D 156s → ~5s, C 37s → 0s（平行）

Phase 2  ─── CGSA 骨架（核心重構）───
├─ 2.1  定義 ColumnGroup dataclass + Registry
├─ 2.2  改 L1 輸出為 per-indicator column-group .npy
├─ 2.3  改 _combine_layers() 為 registry-based（不做 concat，只註冊）
│       ★ Multi-TF: 消除 per-TF 內部 concat 和 cross-TF concat（共 5 次 → 0 次）
├─ 2.4  ★ Multi-TF: column tagging 改為 group_id 命名（group_id 天生包含 TF prefix）
│       消除 _apply_timeframe_tag() 的 .rename() copy
├─ 2.5  改 L6.5 為 per-group 處理（讀 .npy → transform → 寫 .npy）
├─ 2.6  改 persist 為 per-group → Parquet（**建議**：按類別或 Indicator 拆分多個 Parquet 儲存，避免單一 Parquet Schema 塞入 45 萬欄位導致下游 Metadata 讀取瓶頸；並確保中介 `.npy` 在持久化後隨即刪除以避免硬碟撐爆）
└─ 預計效果：消除 B1 concat(383s) + E(108s) + F(8365s) + per-TF concat + rename copy

Phase 3  ─── Numba L3 fused rolling ───
├─ 3.1  實作 fused_rolling_stats() 的 mean/std/min/max/range/zscore
├─ 3.2  實作 online skew/kurt（Pebay algorithm + 定期校正）（**建議**：Numba 內部的累加器務必強制使用 `float64` 進行計算，最後輸出再轉回 `float32`，這是防範 `float32` 累加出現災難性消去 catastrophic cancellation 的最輕量解法）
├─ 3.3  實作 rolling rank（sorted buffer + bisect）
├─ 3.4  實作 slope（running sums, 已有 vectorized 版本可參考）
├─ 3.5  驗證：Numba 結果 vs pandas rolling 結果（atol=1e-6）
└─ 預計效果：A4 385s → ~60s

Phase 4  ─── Polars L2 / L6.5（conditional）───
├─ 4.1  L1 輸出 → Polars DataFrame（from_numpy zero-copy）
├─ 4.2  L2 DerivedOperatorEngine → Polars with_columns() batch
├─ 4.3  L6.5 FeaturePreprocessor → Polars expressions
├─ 4.4  驗證：Polars NaN 語義與 pandas 一致
└─ 預計效果：A3 307s → ~15s, L6.5 → ~60s

Phase 5  ─── 生產化 ───
├─ 5.1  multi-symbol ProcessPoolExecutor
├─ 5.2  Arrow IPC 作為 column-group intermediate
├─ 5.3  DuckDB 讀取 Parquet (IC/ML 下游)
└─ 預計效果：100 symbols × 4 TF × 8 workers → ~41 min
```

### 16.3 預計最終效能

| 場景 | 現行 | Phase 1 | Phase 1+2 | Phase 1+2+3+4 | Phase 1~5 |
|---|---|---|---|---|---|
| 1 sym × 2 TF | 170+ min ❌ | ~140 min | ~20 min | **~3.3 min** | ~3.3 min |
| 1 sym × 4 TF | OOM ❌ | OOM ❌ | ~40 min | ~6.5 min | ~6.5 min |
| 100 sym × 2 TF | OOM ❌ | OOM ❌ | ~33 hrs | ~5.5 hrs | **~41 min** |
| 100 sym × 4 TF | OOM ❌ | OOM ❌ | ~66 hrs | ~11 hrs | **~82 min** |

**註記**：上表屬目標估算，不是 commit。每完成一個 Phase 都要用同一資料集重新 profile，並對照 golden output 確認「不減特徵、不降品質」。

---

## 17. 評論與結論

### 17.1 研究收穫：為什麼簡單「換 Polars」不夠

很多效能問題的第一反應是「換引擎」（pandas → Polars / DuckDB）。Ultra Think 的分析揭示：

1. **真正的瓶頸不是計算引擎慢，而是架構強制了 11 次重複搬運**
2. **Polars 有 rolling rank/skew/kurt 的缺口**——盲目換引擎會撞到新的牆
3. **DuckDB 沒有 rolling window rank**——SQL 計算模型不完全匹配
4. **Dask/Ray 解決的是 row-scaling，不是 column-scaling**——方向完全錯誤
5. **Rust 原生理論最優但開發成本不合理**——Polars 已取得 90% 收益

**真正的 First Principle 答案是：消除搬運（CGSA）+ 每層選最適引擎（Hybrid）**

### 17.2 關鍵數據對比

| 指標 | 現行 | Hybrid M |
|---|---|---|
| 資料觸碰次數（primary TF 每 float） | 11 次 | **2 次** |
| 資料觸碰次數（non-primary TF 每 float） | 11 次 | **4 次** |
| memmap 同時存活 | 46+ GB | **<2 GB** |
| 全域 concat 次數 | 5 次（per-TF + cross-TF） | **0 次** |
| Self-alignment 浪費 | 298s（B2 完全浪費） | **0s（跳過）** |
| TF 處理方式 | 順序（for 迴圈） | **平行（ProcessPool）** |
| L3 掃描總次數 | 100N | **1N**（融合） |
| B+F 占比 | 90%+ | **0%**（消除） |
| 單 symbol 完成時間 | >170 min (未完成) | **~3.3 min** |
| 100 symbols 可行性 | 不可能 | **~41 min (8 workers)** |

### 17.3 最終結論

1. **架構問題 > 引擎問題**：CGSA（消除 concat）的效果遠大於任何引擎替換
2. **Hybrid > 一統，但要分階段驗證**：每層選最適引擎（Polars L2/L6.5 + Numba L3 + searchsorted align）是正確終局，但落地應先做 searchsorted + CGSA + Numba，再依 re-profile 決定是否導入 Polars
3. **Dask/Ray/ClickHouse/Rust 均不適用**——經深度分析後淘汰
4. **數值等價是不可退讓的硬約束**：所有變更都必須通過 golden output test suite
5. **Phase 1（searchsorted）可以立即動手**——風險最低、效果立見（B2+D 從 454s→15s）
6. **維持現行 phased plan，但加上 decision gate**：方向不變，避免在未重新量測前提前承諾 Phase 4/5 的全面遷移

### 17.4 下一步行動項

- [ ] **Phase 0.3**：執行現有 pipeline 一次（可用 smaller config），儲存 golden output 作為基準
- [ ] **Phase 1.1**：實作 `build_asof_index_map()` 並跑 unit test
- [ ] **Phase 1.3**：驗證 searchsorted vs merge_asof 數值一致
- [ ] **Phase 1.4**：★ Multi-TF 快修 — 在 `MultiTFGenerator.generate_multi_tf()` 加 `if timeframe == self._primary_tf: aligned = combined`（跳過 align_to_primary），驗證數值不變
- [ ] **Phase 1.5**：★ Multi-TF 各 TF 平行化 — 替換 `for` 迴圈為 ProcessPoolExecutor
- [ ] **Phase 2.1**：設計 ColumnGroup dataclass + Registry interface
- [ ] **Phase 2.4**：★ Multi-TF column tagging 改為 group_id 命名方案
- [ ] **Phase 3.1**：PoC — 單一 L1 column (EMA_5) 的 Numba fused_rolling_stats
- [ ] **Phase 3.5**：Numba 結果 vs pandas rolling 的數值驗證（atol=1e-6）
- [ ] **Phase 4.4**：Polars NaN min_periods 語義驗證
- [ ] **Phase Gate**：Phase 3 完成後重新 profile；若 B/F 已消除且 L2 / L6.5 不再是主瓶頸，則延後 Phase 4，避免為換引擎而換引擎
- [ ] 增加 L2 前後的計時 log 以精確定位 A3 的 307s 分布
- [ ] 增加 F 段 heartbeat log（每 30s 報告進度 + page fault count）
