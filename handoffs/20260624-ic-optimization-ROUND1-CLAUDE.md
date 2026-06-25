# IC-Analysis 架構級優化 — Round 1：Claude 獨立版本

> 2026-06-24 ｜ 尺度目標：單 symbol **430K 欄 × 20K 列**；跨 symbol **數十～上百**。
> 準則（CLAUDE.md Optimization Priority，依序）：① tier 可重複(8/16/24/32GB) ② 多 symbol 穩定/OOM 安全/resume ③ 數據品質(無假/無跨symbol污染/無stale/NaN·inf gate) ④ 最低算時 ⑤ 最小輸出 ⑥ 量化最佳實務(無 look-ahead/洩漏)。
> 三方各產一版 → 互審詰問 → 三輪收斂。本檔為 Claude 版,待 codex/cursor 詰問。

## 0. 核心診斷（致命瓶頸）
**現況 `_stage0_ingestion` 全量載入 features_df（pandas，430K×20K）→ float32≈34GB、float64≈68GB，單步炸穿所有 tier。** stage4/5/6 全在全矩陣上操作。這是「為什麼會 OOM / 慢」的根因,5 epic 只是表症。**真正的優化是：IC-analysis 不得在任何 tier 物化全特徵矩陣。**

關鍵物理事實：IC(feature_i, label) 對每個 feature **獨立**（單欄 vs label 的 rank/pearson 相關）→ embarrassingly parallel、可分塊；FeatureReader 已有 `load_columns_v2`（欄投影）。redundancy(VIF/correlation) 才需要跨特徵,但那只該對「已篩過的 survivors」做。

## 1. 架構重設計（principle ①②④⑤ 核心）

### 1.1 串流式分塊 IC（取代全量物化）
- **CHUNK_COLS = f(tier)**：依 available RAM 動態決定每批欄數（如 8GB→2K欄/批、32GB→16K欄/批）。沿用 Feature Factory 既有 tier 偵測。
- pipeline 改為：for col_batch in reader.iter_column_batches(run, CHUNK_COLS): 計 IC/ICIR/rolling/decay → **只保留 per-feature 標量摘要 + 進 top-N 堆**，批結束即釋放該批矩陣。**峰值記憶體 = label(20K) + 一批欄(CHUNK×20K) + 摘要表(430K×~10 標量)**，與總欄數解耦 → 任何 tier 可跑。
- 摘要表 430K×10 float32 ≈ 17MB，可常駐。

### 1.2 分階段篩選（staged screening；解「幽靈 feature_filter」+ principle ④）
- **Stage A 廉價粗篩（全特徵，串流）**：coverage/variance/dead-constant drop + |IC| 或 |ICIR| 門檻 → 產出 survivors（通常數百～數千）。輸出僅摘要。
- **Stage B 昂貴深析（僅 survivors）**：rolling 全窗、decay、grouped、redundancy(VIF)、10 個 deep 模組 **只對 survivors**。430K→survivors 把昂貴計算量降 2-3 個數量級。
- **feature_filter 真落地**：前端送的 max_features/category/source 篩選進 ICConfig schema + 在 Stage A 套用,**metadata 記原始數/篩後數/規則（可審計,不靜默截斷）**。

### 1.3 多 symbol（principle ②）
- 逐 symbol 串流（不同時載多 symbol 全矩陣）；cross-sectional 只在「對齊時間軸的 survivors 子集」上做。
- resume/retry：per-(symbol, stage) checkpoint；OOM 偵測→降 CHUNK_COLS 重試（沿用 FF 降載模式）。
- **跨 symbol 隔離**：每 symbol 獨立 run_dir/registry entry;cross-sectional merge 須 PIT 對齊、值守恆驗證（principle ③⑥）。

## 2. 逐 stage / 模組優化

| Stage/模組 | 現況問題 | 優化 |
|---|---|---|
| stage0 ingestion | 全量物化 | 改 lazy 欄投影 + 串流；NaN gate 逐批 |
| stage1 preprocess | 全矩陣 | 逐批；winsor/zscore 用 streaming 統計（兩遍或 t-digest）|
| stage2 label | — | label 一次載(20K)、forward-shift PIT 正確性斷言 |
| stage3 event filter | 全矩陣 mask | 逐批套 mask |
| stage4 IC | 全矩陣 + 逐特徵 decay Python 迴圈 + 14K log | 串流分塊 + decay 只對 survivors + Numba fit + **log 聚合一行** |
| stage5 統計驗證(FDR) | 全特徵 p 值 | FDR 對 survivors;p 值串流收集 |
| stage6 redundancy(VIF/corr) | O(n²) 全特徵 | **只對 survivors**;corr 用分塊 Gram 或 random projection 預篩 |
| stage7 report | 可能輸出 per-feature 大物件 | top-N 明細 + 其餘聚合;**輸出 parquet/壓縮,decay 曲線不逐特徵存** |
| grouped_ic | 崩潰(pydantic) + 全特徵分組重算 | 修契約(A1)+只對 survivors + 時間軸 ms/s 正確性(既存 bug) |
| decay | 逐特徵 fit + 無意義(R2≈0) | 只對 survivors;R2 低不 early-skip 改 metadata 標記(不丟語義) |
| 10 deep 模組 | 全特徵 | 只對 survivors;centrality/orthogonalize(O(n²/n³)) 必須先篩 |

## 3. 數據品質 / 無洩漏（principle ③⑥，紅線）
- **PIT**：label forward-shift 正確、IC 用同期對齊不混入未來;rolling/grouped 不跨 split 洩漏。
- **時間軸 bug**：`_get_time_index` numeric 當 ms（ic_engine:1021）→ 若 kline 為秒則 grouped IC 軸錯,須真實 kline 驗證修正。
- **train/val/test**：deep 模組(rolling_oos/walk-forward) 嚴格時序切,test 只用一次。
- **跨 symbol 污染**：cross-sectional 對齊前驗 symbol 隔離;不共用 winsor/zscore 統計跨 symbol。
- 不靜默截斷;不放寬 NaN/inf gate。

## 4. 輸出最小化（principle ⑤）
- 預設只存 top-N(可配置) 特徵明細 + 全體聚合統計(分位/計數);per-feature decay 曲線/grouped 全表不預存(on-demand 重算或 debug flag)。
- parquet + 壓縮;float32;摘要表而非原始 IC 序列。

## 5. UX/系統（IC-UX-ERR/IC-PERF，principle ④ 體感）
- analyze 改 `asyncio.to_thread`(解 event loop 阻塞→WS 不假死)。
- WS：failed→setError(message)+停重連;HTTP poll fallback。
- stage4 子進度(batch i/N);cancel API;大 run 警示(>門檻要求先粗篩或 explicit override)。
- log 聚合(熱迴圈零 log)。

## 6. 落地切分（取代原 5 epic,重排）
| Epic | 內容 | 優先 | 命中準則 |
|---|---|---|---|
| IC-STREAM | 串流分塊 IC + tier-adaptive CHUNK + 摘要表（核心,解 OOM） | P0 | ①②④⑤ |
| IC-SCREEN | staged screening + feature_filter 真落地 + 大 run guard | P0 | ③④ |
| IC-CRASH | GroupedConfig 修 + 真回歸 | P0 | 正確性 |
| IC-UX-ERR | to_thread + WS 真錯誤 + 停重連 | P0 | 體感 |
| IC-CORRECT | 時間軸 ms/s 修 + PIT/隔離不變量測試(golden) | P1 | ③⑥ |
| IC-PERF | decay/redundancy 只對 survivors + Numba + log 聚合 + 子進度/cancel | P1 | ④ |
| IC-OUTPUT | top-N+聚合輸出 + 壓縮 | P2 | ⑤ |
| IC-PERF-DEEP | 向量化/並行(golden) | P2 | ④ |

## 7. 待詰問的開放問題（給 codex/cursor）
1. 串流分塊是否破壞任何「需全矩陣」的計算？（redundancy/centrality/orthogonalize 跨特徵——我主張先篩再做,但 survivors 仍可能上千,O(n²) 仍重?）
2. Stage A 粗篩門檻會不會漏掉「單獨弱但組合強」的因子（互動效應）？粗篩的正確性代價?
3. tier-adaptive CHUNK 的記憶體模型是否漏算（rolling 窗 ×、grouped 分組副本、pandas 開銷 ~2-3x）?
4. streaming winsor/zscore 兩遍 vs t-digest 的精度 vs 記憶體權衡?
5. 430K 欄的 reader 欄投影 I/O：逐批讀 parquet 的 I/O 放大 vs 記憶體節省?
6. cross-sectional 數十-上百 symbol 的對齊矩陣本身多大?是否又是一個物化炸點?
