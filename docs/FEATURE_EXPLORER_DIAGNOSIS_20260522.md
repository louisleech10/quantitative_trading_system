# Feature Explorer 載入瓶頸 + 問題特徵全量分類報告

> 任務：ETHUSDT 1h, config_hash = `c4403c2493edaf57e33d058336ace686`
> 特徵數：442,079 (L1 3,354 / L2 93,638 / L3 318,077 / L4 26,976 / L6 22 / L6.5 12)
> 時間範圍：2024-01-01 ~ 2026-04-27 (20,352 rows)
> 原始檔案：1,061 個 parquet (7.74 GB), `data_cache/features/ETHUSDT/1h/c4403c2493edaf57e33d058336ace686/raw/`
> 報告生成：2026-05-22

---

## 一、Q2 — 問題特徵全量分類報告

### 1.1 報告檔案位置

所有檔案在  
`data_cache/features/ETHUSDT/1h/c4403c2493edaf57e33d058336ace686/problem_analysis_20260522_070240/`

| 檔名 | 大小 | 內容 |
|---|---:|---|
| `summary.md` | 7.7 KB | 人類可讀的彙總（互斥分類 + 各類細分）|
| `summary.json` | 15 KB | 結構化 JSON，供 AI / 後續腳本使用 |
| `all_features.parquet` | 3.7 MB | **442,079** 列，每個特徵完整統計（nan_count / first_valid / last_valid / mid_hole_count / trailing_nan / class / source / layer / tf / family / base_indicator）|
| `problem_features.csv` | 68 MB | **441,919** 列，只包含非 CLEAN 特徵，依 class + nan_ratio 排序 |

掃描方式：以 `pc.or_kleene(pc.is_null, pc.is_nan)` 對 raw 1,061 個 parquet 全量逐欄計算，**100% 真實數據、無推估、無取樣**。耗時 302.8s。

### 1.2 互斥分類規則（強度遞減，最強者勝）

1. **HIGH_NAN** — `nan_ratio > 0.05`
2. **MID_HOLE** — 在 `[first_valid, last_valid]` 區間內存在 NaN
3. **TRAILING** — `last_valid < T-1`
4. **WARMUP_ONLY** — 僅起始有 NaN（rolling lookback 暖機）
5. **CLEAN** — 全時段有效

### 1.3 整體分布

| Class | Count | % of all |
|---|---:|---:|
| HIGH_NAN | 117,052 | 26.48% |
| MID_HOLE | 2,358 | 0.53% |
| TRAILING | 0 | 0.00% |
| WARMUP_ONLY | 322,509 | 72.95% |
| CLEAN | 160 | 0.04% |
| **合計（非 CLEAN）** | **441,919** | **99.96%** |

> 與後端 `data_quality.json` 的彙總 `{high_nan: 117052, mid_holes: 5240, trailing_nans: 724}` 比對：
> - HIGH_NAN 完全一致（117,052）
> - 後端的 `mid_holes / trailing_nans` 計數**未互斥**（同一特徵可同時計入），本報告採互斥分類，故 MID_HOLE 2,358 < 5,240、TRAILING 0 < 724（被 HIGH_NAN 或 MID_HOLE 吸收）

### 1.4 HIGH_NAN（117,052）細分

**nan_ratio 區間分布**

| 區間 | Count |
|---|---:|
| 5–10% | 54,581 |
| 10–25% | 55,272 |
| 25–50% | 5,602 |
| 50–75% | 904 |
| 75–95% | 476 |
| 95–99.9% | 3 |
| **100% (完全空)** | **214** |

**來源 prefix（前 6 名）**

| Source | Count | 說明 |
|---|---:|---|
| close | 32,394 | 收盤價衍生 |
| volume | 31,634 | 成交量衍生 |
| taker-ratio | 30,727 | Taker 買賣比率衍生 |
| hlc | 9,735 | High/Low/Close 組合 |
| hl | 4,643 | High/Low 範圍 |
| ent | 2,029 | 熵特徵 |

**Layer 分布（檔名解析）**

| Layer | Count |
|---|---:|
| L3 (rolling) | 89,911 |
| L2 (derived) | 22,249 |
| L4 (lag) | 4,216 |
| L1 (atomic) | 676 |

**Timeframe 分布**

| TF | Count |
|---|---:|
| 12h | 115,141 |
| 1h | 1,911 |

> **重點**：HIGH_NAN 有 **98.4%** 集中在 12h timeframe — 因為 1h 有 20,352 列、12h 只有 1,696 列；當特徵 lookback (e.g. W144, W233) 大於 12h rolling 容量時，會產生大量 NaN。

**Top 10 base_indicator**

`trend_T3` (3,432), `trend_EMA` (3,200), `trend_SMA` (3,200), `trend_TEMA` (2,621), `momentum_TRIX` (2,583), `momentum_RSI` (2,504), `trend_MIDPOINT` (2,442), `trend_DEMA` (2,354), `statistics_LINEARREG` (2,219), `statistics_STDDEV` (2,189)

### 1.5 MID_HOLE（2,358）細分

> 真正「中間斷層」的特徵，這類最值得注意，可能來自交易所數據缺失或 indicator 演算過程的特殊處理。

**Top 5 來源**：hl (613) / close (582) / hlc (268) / volume (256) / tr (227)
**Layer**：L3 (1,517) > L2 (826) > L4 (13) > L1 (2)
**Timeframe**：1h (1,839) > 12h (519)
**Top base_indicator**：`momentum_AROONOSC` (233), `trend_MIDPOINT` (176), `momentum_AROON-aroonup` (148), `momentum_WILLR` (146), `momentum_AROON-aroondown` (136), `ud_vol_ratio` (133)

> AROON / WILLR / MIDPOINT 系列出現 mid-hole，極可能與**有效資料區間的窗口 max-min 同步取值**有關（演算法在某些 lookback 下會產生中間 NaN）。需個別檢視 indicator 實作。

### 1.6 WARMUP_ONLY（322,509）細分

> **這 73% 並非「壞特徵」**，而是 rolling indicator 的正常暖機期。`data_quality.json` 已給出建議起算點：

```json
"recommended_start_index": 3277,
"warmup_loss_ratio": 0.16101611635220126,
"p95_warmup": 3277,
"max_warmup": 20352
```

亦即：若統一從 index 3277 開始切資料，可救回 95% 的特徵；只有 5% 的特徵 warmup > 3,277（含上述 HIGH_NAN 與少量 W233 rolling）。

### 1.7 結論

- **真正應該下架/檢討的特徵**：
  - HIGH_NAN nan_ratio ≥ 50%（1,597 個）— 幾乎不可用
  - 100% NaN（214 個）— 必須移除
  - MID_HOLE（2,358 個）— 需個別檢視 indicator 邏輯
- **正常 warmup**（322,509 個）只需在訓練時統一從 `recommended_start_index = 3277` 切資料即可
- 完整詳細名單在 `problem_features.csv`（可用 pandas/DuckDB/Excel 查詢）

---

## 二、Q1 — Feature Explorer 全 Tab 載入瓶頸與整體優化

> 範圍：Overview / Feature Table / Time Series / Correlation / Distribution / Data Quality / NaN Pattern / VIF — **全部 tab 一起加速**。

### 2.0 各 Tab 對應 endpoint 與底層資料路徑

| Tab | Backend endpoint | 底層方法 | 關鍵成本 |
|---|---|---|---|
| Overview | `browse_summary` | `_load_cgsa_summary_fast`（讀 parquet metadata，已最佳化）+ `_start_stats_cache_warmup` 背景 | metadata 讀取 + warmup I/O 占用 |
| Feature Table | `browse_features` | `_enrich_cgsa_catalog_page_stats` → `_load_cgsa_selected_df`（每頁 30 欄）| **stats cache miss 時** 每頁 read parquet columns（多檔 ThreadPool=4）|
| Time Series | `browse_feature_data` | `_load_selected_feature_rows` / `_load_cgsa_selected_df` | 每次 read K 個 parquet 檔 = K 次 open |
| Correlation | `browse_correlation` | `_load_cgsa_selected_df`（≤50 欄）+ `df.corr()` | 選 50 個分散於 50 檔 → 50 次 cold open |
| Distribution | `browse_distribution` | `_load_cgsa_selected_df`（1 欄）+ histogram + ADF | 為 1 欄整檔讀（單檔可能含 400+ 欄一起讀進來，浪費 I/O）|
| Data Quality | `browse_data_quality` | `_build_data_quality_cgsa`（全掃 1,061 檔）| **單次 5.7 分鐘**，併發 7 次變 **11.5 分鐘** |
| NaN Pattern | `browse_nan_pattern` | `_load_cgsa_summary_fast` 取 NaN ratio → 讀 top-N 欄 | metadata 已快、選欄後 read 同 Correlation |
| VIF | `browse_vif` | `_load_cgsa_selected_df` + `np.linalg.pinv` | 同 Correlation |

### 2.1 現況實測（從 `logs/case_search_api_20260521.log` 提取）

任務完成於 23:23:23（feature_count=442,079）。Frontend 在 23:23:43 開始打開 Feature Explorer。日誌顯示 `browse_data_quality` 共被觸發 **7 次**，每次都重新掃描 1,061 個 parquet：

| 開始時間 | 完成時間 | 耗時 |
|---|---|---:|
| 23:23:43 | 23:29:25 | **342.1 s** |
| 23:24:55 | 23:33:53 | **538.0 s** |
| 23:25:17 | 23:35:16 | **599.4 s** |
| 23:27:22 (×2) | 23:38:42 / 53 | **680.1 / 678.4 s** |
| 23:27:34 (×2) | 23:38:53 / 54 | **691.0 / 679.5 s** |

> **這是用戶感受到「Feature Explorer 慢」的真正原因**：
> 1. `_build_data_quality_cgsa` 單次掃描 442,079 欄 × 1,061 檔 = 約 **5.7 分鐘**（單一執行緒、無快取時）
> 2. Frontend 對同一任務發出 **7 次平行請求**（無 request coalescing），互相搶 I/O & CPU 後變成 **11.5 分鐘**
> 3. 同期 `feature_stats_cache_parts/` 也在背景 warmup（23:23:58 ~ 23:41:28，**17.5 分鐘**），與 data_quality 搶資源

另外 disk cache (`data_quality.json`) 雖已存在，但 **每次重啟 task / 重新 generate 時就會失效**，下一次 cold-open 又會重跑全量掃描。

> **本節範圍**：以下所有優化只討論 **fresh run / 全 cold cache** 情境（不假設 `data_quality.json`、`feature_stats_cache_parts/`、`_stats_cache`、`_adf_cache`、LRU 任何一個存在）。換句話說：**從「task 剛完成」到「user 第一次看到每個 tab」的真實 cold 時間**才算數。

### 2.2 共同瓶頸（fresh / cold 情況下全 tab 一起慢的真正主因）

1. **背景 warmup 連續霸佔 I/O 17.5 分鐘**
   `CGSA stats warmup started 23:23:58 → completed 23:41:28 → 441,766 features cached`。期間 `feature_stats_cache_parts/` 不斷寫入 1,063 個小檔，與所有 user 觸發的 read 互搶 macOS APFS I/O queue → 連 Overview / Correlation / Distribution 都慢。

2. **`browse_data_quality` 同時併發 7 次**
   日誌 progress 行 100+ 條交錯，4 個併發 scan 同時推進 file 830 / 840 / 850 / 860；CPU + I/O 雙重抖動。**這 11.5 分鐘內所有其他 tab 也卡死**。

3. **`_load_cgsa_selected_df` 沒有 file handle / 計算結果快取**
   每次呼叫都重開 parquet → 解壓 → 轉 pandas。
   - Correlation 選 50 欄分散在 50 檔 = **50 次 cold open + 50 次 decompress**
   - 同一 tab 重新整理或切換 tab 後切回來都整套重做（無 LRU）
   - Distribution / VIF / Time Series 共用同一個方法，問題一致

4. **Stats / ADF cache cold-start 全失效**
   `_stats_cache` / `_adf_cache` 都是 in-memory dict（無 disk persist），API restart 後立刻全空，第一次點 Feature Table → 又得啟 17.5 分鐘 warmup；Distribution tab 的 ADF 顯示也要重算。

5. **Frontend 在 Explorer mount 時 fan-out 多個 heavy endpoint**
   單一頁面開啟同時觸發 summary / data-quality / quality-scorecard / drift / importance-comparison …，加上 React StrictMode 雙觸發、user reload、tab 切換重新訂閱 → 7 次併發是這樣來的。

### 2.3 整體優化建議（fresh / no-cache 情境，按 ROI 排序）

#### 🥇 P0-A — Request coalescing（單一 task_id 同 endpoint 共享 future）

**覆蓋**：data_quality / correlation / distribution / feature_data / nan_pattern / vif / summary
**做法**：建立 `_inflight_requests: Dict[(endpoint, task_id, fingerprint), asyncio.Future]`；同 key 的併發請求 await 同一個 future（**不持久化、不算 cache**——只是去重正在跑的同一份工作）。
**預期**：fresh cold 下 data quality 從 7×併發 11.5 分鐘 → 單次 5.7 分鐘（−50%）；其他 tab 不再被冗餘呼叫拖慢。
**位置**：所有 `browse_*` 入口 [api/services/feature_factory_service.py](api/services/feature_factory_service.py)

#### 🥇 P0-B — Frontend：lazy fetch，不要 mount 就 fan-out

**覆蓋**：全 tab（fresh cold 第一道防線）
**做法**：
- 每個 tab/panel 用 `useEffect(...,[isActive])`，**只在被開啟時才 fetch**，避免 Explorer 一 mount 就 fan-out
- SWR / React Query 設 `dedupingInterval ≥ 60s`、`revalidateOnFocus=false`（**同視窗去重，不是跨 session cache**）
- 對 heavy endpoint（data_quality, vif, correlation, distribution）強制 `keepPreviousData`
- 修掉 React StrictMode 雙觸發（用 ref guard）
**預期**：fresh cold 時 user 只開 Overview → 只有 1 個 endpoint 被打；開到哪個 tab 才付那個 tab 的 cost。**這是把「全 tab 平行付出 7×成本」降回「序列付出 1×成本」的關鍵**。
**位置**：[frontend/src/app/feature-browser/](frontend/src/app/feature-browser/), [frontend/src/store/featureBrowserStore.ts](frontend/src/store/featureBrowserStore.ts)

#### 🥇 P0-C — Warmup throttle / 降併發 workers

**覆蓋**：全 tab（解決 fresh cold 時背景 warmup 與前景 tab 互搶 I/O）
**做法**：
- `_start_stats_cache_warmup` 加「user 有未完成 browse_* 請求時暫停 0.5 s」的協作式 throttle
- 或把 warmup workers 從 2 降到 1（搭配 thread priority 降級）
- 偵測 8 GB tier 時自動延後 warmup 30 秒（讓 user 先看到 Overview）
**預期**：fresh cold 下 user 操作期間背景 warmup 讓出 I/O 70% → Overview / Correlation / Distribution 的 cold latency 降 30–50%。
**注意**：warmup 本身仍然執行（**之後 warmup 完成的 cache 不算入本節收益**）；只是不再與前景搶資源。

#### 🥈 P1-A — `_build_data_quality_cgsa` 平行掃描 raw

**覆蓋**：data_quality（fresh cold 最大單點 5.7 分鐘）
**做法**：`for path in raw_files` 改成 `ThreadPoolExecutor(max_workers=4)`（pyarrow read_table + 統計計算都釋放 GIL）。
**預期**：實測單執行緒 302 s（用 `scripts/analyze_problem_features.py` 量到）→ **預估 80–120 s（−60%）**。配合 P0-A coalescing → fresh cold 從 11.5 分鐘 → **80–120 秒**。
**注意**：8 GB tier 限 ≤ 4 worker；要在 worker 內 `del table` 並週期 `gc.collect()` 防峰值記憶體爆。
**位置**：[api/services/feature_factory_service.py#L1891](api/services/feature_factory_service.py) `_build_data_quality_cgsa`

#### 🥈 P1-B — `_load_cgsa_selected_df` 改用 `pyarrow.dataset` 整批 scan

**覆蓋**：Correlation / VIF / Time Series / Distribution（fresh cold 所有要實際讀資料的 tab）
**做法**：目前 `_load_cgsa_selected_df` 已用 `ThreadPoolExecutor(max_workers=min(4, len(file_to_cols)))`，但仍是 50 次獨立 `pq.read_table`。fresh cold 還可降的點：
- 用 `pyarrow.dataset.dataset(paths).to_table(columns=...)` 一次 scan + column-prune，amortize 開檔 overhead
- 啟用 `pre_buffer=True` + `use_threads=True` 讓 pyarrow 在單檔內也平行 decompress
- 對「同 base_indicator 跨檔」的選擇優先打包成同一個 dataset scan call
**預期**：50 欄分散 50 檔的 Correlation cold-open 從 ~30 s → **10–15 s**（pyarrow dataset scan 比 50× independent open 快 2–3×）。
**位置**：[api/services/feature_factory_service.py#L4034](api/services/feature_factory_service.py) `_load_cgsa_selected_df`

#### 🥈 P1-C — `browse_features` 每頁 stats 改成 dataset.scan 整批算

**覆蓋**：Feature Table（fresh cold 翻頁 1–3 s/頁）
**做法**：當 stats cache miss 時（fresh cold 一定 miss），把該頁 30 欄一次性用 `pyarrow.dataset` scan 進來，再用 `pd.DataFrame.agg(['mean','std','count'])` 向量化算（而非每欄各 call 一次 `_load_cgsa_selected_df`）。
**預期**：fresh cold 翻頁 1–3 s → **0.3–0.8 s**。
**位置**：`_enrich_cgsa_catalog_page_stats` [api/services/feature_factory_service.py#L1153](api/services/feature_factory_service.py)

#### 🥈 P1-D — 把 first_valid / last_valid / mid_hole 算進 feature generation 本身

**覆蓋**：data_quality（fresh cold 完全跳過全量掃描）
**做法**：在 `feature_preprocessor` 的 raw-sink 階段（資料本來就要過一次）順手算 3 個 per-column 統計，存進 raw parquet 的 **schema metadata**（`pq.write_table(... metadata=...)`）或同檔 sidecar JSON。
**這不是 cache**：資訊**內嵌進資料本身**，跟 row count 寫進 parquet footer 同性質——任何 fresh run 都自帶。
**預期**：fresh cold 下 `_build_data_quality_cgsa` 退化為「讀 1,061 個 parquet footer」**< 5 秒**（比 P1-A 平行掃描還快 16×）。
**成本**：raw-sink 多 1–3% 時間（總長 1,333 s → +13–40 s，可接受）。
**位置**：[momentum/FeatureEngineering/preprocessing/feature_preprocessor.py](momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)，metadata 寫入 [momentum/FeatureEngineering/feature_storage.py](momentum/FeatureEngineering/feature_storage.py)

#### 🥉 P2-A — Distribution tab ADF 改成 on-demand

**覆蓋**：Distribution（fresh cold 1 欄 ADF ~1–3 s）
**做法**：
- ADF 預設關閉，user 按「Run ADF」按鈕才算（避免 fresh cold 開 tab 就 block）
- 或改用固定 lag=10 的 fast-ADF（不做自動 lag 選擇）將計算量降 5×
**預期**：fresh Distribution cold 從 2–8 s → **< 0.5 s**（ADF 改 on-demand）。
**位置**：[api/services/feature_factory_service.py#L1687](api/services/feature_factory_service.py) `browse_distribution` + 對應 frontend tab

#### 🥉 P2-B — `browse_summary` metadata read 用 thread pool

**覆蓋**：Overview（fresh cold ~5–10 s）
**做法**：`_load_cgsa_summary_fast` 對 1,061 檔讀 parquet footer 目前是串列，改 `ThreadPoolExecutor(max_workers=8)`（footer read 是純 I/O bound）。
**預期**：fresh cold ~5–10 s → **1–2 s**。
**位置**：[api/services/feature_factory_service.py#L3566](api/services/feature_factory_service.py) `_load_cgsa_summary_fast`

### 2.4 fresh / no-cache 跨 Tab 收益對照

| Tab | 現況 fresh cold | + P0-A 去重 | + P0-B 前端 lazy | + P0-C warmup throttle | + P1/P2 全部上 |
|---|---:|---:|---:|---:|---:|
| Overview | 5–30 s（被 warmup 干擾）| 5–30 s | 5–30 s | 3–10 s | **1–2 s**（P2-B）|
| Feature Table 首頁 | 17.5 min（warmup 在跑 stats）| 17.5 min | 開時才算 | 仍要等 warmup | 翻頁 **0.3–0.8 s**（P1-C）|
| Time Series（5 欄）| 3–10 s | 3–10 s | 3–10 s | 2–6 s | **1–3 s**（P1-B）|
| Correlation（30 欄）| 10–30 s（被 dq 干擾 60 s+）| 10–30 s | 10–30 s | 5–15 s | **3–8 s**（P1-B）|
| Distribution（1 欄）| 2–8 s | 2–8 s | 2–8 s | 2–6 s | **< 0.5 s**（P2-A）|
| **Data Quality** | **5.7–11.5 min** | **5.7 min** | **5.7 min** | **5 min** | **< 5 s**（P1-D）或 80–120 s（只上 P1-A）|
| NaN Pattern | 5–15 s | 5–15 s | 5–15 s | 3–10 s | **1–3 s**（與 P2-B 同路徑）|
| VIF（20 欄）| 5–15 s | 5–15 s | 5–15 s | 3–10 s | **2–5 s**（P1-B）|

**關鍵觀察**：
- 光靠 P0 三項（**完全不靠任何 cache**），fresh cold 已經從 11.5 min 降到 5 min 級
- P1 系列是真正改 fresh cold 演算法的部分（平行、column prune、把計算搬進 pipeline），收益最大
- **P1-D 是唯一一個讓 data_quality 在 fresh cold 也能 < 5 s 的方案**——它不靠 cache，而是改變資料寫入時就帶 metadata

### 2.5 建議實施順序（皆為 fresh / no-cache 收益）

| 階段 | 任務 | 預估開發 | fresh cold 影響 |
|---|---|---|---|
| **Step 1** | P0-B 前端 lazy fetch | 1 天 | 全 tab：避免被別的 tab 拖慢 |
| **Step 2** | P0-A request coalescing | 半天 | data_quality 11.5 → 5.7 min |
| **Step 3** | P0-C warmup throttle | 0.5 天 | 前景 tab cold 降 30–50% |
| **Step 4** | P2-B summary metadata thread pool | 0.5 天 | Overview 5–10 → 1–2 s |
| **Step 5** | P1-A data_quality 平行掃描 | 0.5 天 | data_quality 5.7 → 80–120 s |
| **Step 6** | P1-B `_load_cgsa_selected_df` dataset.scan | 1 天 | Correlation/VIF/TS 降 60–70% |
| **Step 7** | P1-C `browse_features` 整批 dataset.scan | 0.5 天 | Feature Table 翻頁 1–3 → 0.3–0.8 s |
| **Step 8** | P2-A Distribution ADF 改 on-demand | 0.5 天 | Distribution 2–8 → < 0.5 s |
| **Step 9** | P1-D parquet metadata 內嵌 first/last/mid_hole | 1 天 | data_quality 80–120 s → **< 5 s** |

**核心理念（fresh / no-cache 版）**：
1. **不做重複的事**（P0-A 去 in-flight 重複、P0-B 不 fan-out 沒開的 tab）
2. **不互相搶資源**（P0-C 背景任務讓位）
3. **能平行就平行**（P1-A、P2-B：I/O bound 工作上 ThreadPool）
4. **降低 I/O 次數**（P1-B、P1-C：用 dataset.scan 整批讀、column prune）
5. **能在 pipeline 裡算的，就別留到 Explorer 開時才算**（P1-D：metadata 內嵌；**這不是 cache，是把資訊放在資料本身**）

### 2.6 不建議的做法

- ❌ **取樣**：違反 §1 高保真原則，且 first_valid/last_valid 必須全掃才有正確答案
- ❌ **降低欄位數**：違反「絕不刪減配置中的特徵廣度」原則
- ❌ **改用 float16 加速統計計算**：raw 已是 mixed dtype；統計需 float64 才正確
- ❌ **在前端直接 throttle 後 ignore**：會掩蓋真正問題，user 一直按 reload 還是會擠爆
- ❌ **依賴 disk cache / LRU / 任務完成 bake 來「假裝快」**：本節已明確排除——fresh cold 才算數

---

## 三、可立即執行的下一步（按用戶選擇）

1. **若要先看詳細問題特徵**：
   `head -50 data_cache/features/ETHUSDT/1h/c4403c2493edaf57e33d058336ace686/problem_analysis_20260522_070240/problem_features.csv`
   或用 DuckDB：
   `duckdb -c "SELECT class, COUNT(*) FROM read_parquet('.../all_features.parquet') GROUP BY 1"`

2. **若要做 Q1 Step 1 + 2（最高 CP 值優化）**：等待用戶確認後修改
   - [api/services/feature_factory_service.py](api/services/feature_factory_service.py) 加 request coalescing
   - 任務完成時觸發 `data_quality` 背景 bake

3. **若要驗證 Q1 數據**：可實際 curl Feature Explorer API 觀察當前耗時，與本文 §2.1 對照
