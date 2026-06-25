# IC-Analysis 優化 — Round 2：Claude 互審詰問（對三份 Round-1）

> 2026-06-24 ｜ 審 Claude/codex/cursor 三份 Round-1，全範圍。待與 codex/cursor 的 Round-2 reconcile。

## 1. 收斂點（三方已同意，視為定案基礎）
1. **IC-analysis 不得在任何 tier 物化全特徵矩陣**；改串流分塊（column-projection via load_columns_v2）。
2. **分階段（staged）**：廉價粗篩全特徵（coverage/variance/exact IC/ICIR）→ 昂貴計算（rolling 全序列/decay/grouped/redundancy/10 deep 模組）**只對 survivors/candidates**。
3. **重用既有 `compute_ic_from_l7_raw`（ic_engine:104-266）的串流藍本**；orchestrator `analyze()` 全面 adopt，棄 `_load_features_hdf5` 全量物化。
4. **per-tier chunk 預算**；redundancy/centrality/orthogonalize 的 O(k²/k³) 必須硬上限（candidate cap）。
5. **cross-sectional 禁 `pd.concat(frames)`**；per-symbol streaming + per-symbol IC 粗篩 + symbol fingerprint 隔離。
6. **Hotfix 共識**：GroupedConfig `.model_dump()`、timestamp seconds/ms 實測判斷、decay warning 聚合（熱迴圈零 log）、主 analyze `asyncio.to_thread`、feature_filter 真落地（不靜默假篩）。
7. **正確性紅線共識**：staged screening / max_features 前置截斷**不得當唯一正式 gate**（會漏「單弱組合強」因子）；truncation 必須 report 揭露；改數值路徑需 golden。

## 2. 分歧點 + 我的裁決
| # | 分歧 | 三方立場 | 我的裁決 + 理由 |
|---|---|---|---|
| D1 | chunk 大小 | Claude 8GB=2K欄(激進);codex 8GB=512欄;cursor 2D(cols×rows) | **採 codex/cursor 保守模型**:我的 2K 低估 pandas 2-3x + rank/rolling copy。8GB=512-1024 欄、單 worker 峰值≤35% RAM。cross-sectional 必須**同時切 cols 與 rows**(cursor 對) |
| D2 | winsor/標準化 | Claude/codex 兩遍掃描;cursor 優先重用 FF L6.5 processed artifact | **採 cursor**:若 FF 已 winsorize→byte-faithful 驗證後直接消費 processed artifact,免重算 + 防雙重處理(命中準則③)。FF 未做才兩遍 |
| D3 | materialize 路徑 | — | **cursor 揪到關鍵**:`_materialize_features_for_ic` 可能仍產 34GB 中間檔。串流 IC **必須跳過 materialize 直讀 L7 parquet**,否則磁碟/時間瓶頸仍在。必修 |
| D4 | 並行模型 | Claude/codex worker pool;cursor 警告 macOS spawn h5py 開銷可能反增 | **採 cursor 謹慎**:先 microbench(sciprts/b7_l65 模式)再定 process vs thread;預設單 worker 穩定優先,並行為 opt-in |
| D5 | rolling ICIR 串流 | codex/cursor Welford 統計;需證與現 `_rolling_corr_matrix` 逐點一致 | **需 golden 鎖**:Welford mean/std 對 ICIR 數學等價,但 stride>1/窗邊界須 golden 比對改前後一致才採 |
| D6 | epic 切分 | 三方各一版(A-H / E0-E6 / 我8項) | **以 codex A-H 為骨架**(最細),併入 cursor E0 hotfix 先合併、我的 IC-CORRECT(時間軸+PIT golden)獨立。見 §5 |

## 3. 三方都漏 / 補強（盲點）
- **B1 持久化 task registry**(cursor#10)：現 `_tasks` 在記憶體 → server restart 後 resume 失效。長跑 430K×N 必須持久化 task/checkpoint。三方 resume 都假設可續但沒說 registry 怎麼存。
- **B2 chunk 對齊 parquet group 邊界**(cursor#12)：chunk_cols 不對齊 group 會碎片化讀放大 I/O。需讀真實 manifest 定 chunk 邊界。
- **B3 spill/輸出 retention**(cursor#11)：430K×N symbol 的 spill + artifact 磁碟用量需 retention policy（準則⑤）；三方談輸出小但沒談中間 spill 清理。
- **B4 row_index 可得性**(cursor#1)：舊 run 無 row_index → 串流時間軸從何來；需 fallback（讀 parquet 首欄 index vs fail-closed）。
- **B5 FF 上游 430K 爆炸**(cursor#5)：是否 FF indicator 笛卡爾積該加 hard cap?**這是獨立產品決策**——IC 側優化是治本(必做),但 FF 側 cap 可大幅減負;建議併入但分 epic,不阻 IC 優化。
- **B6 stage1 preprocessor 跨欄操作未審**(codex)：若 preprocess 含跨欄(如 cross-sectional neutralize)則非 streaming-safe,須逐一分類 streaming-safe vs candidate-only。動工前必查。

## 4. 正確性紅線爭議（須 Round 3 / 產品定）
- **staged screening 漏交互效應因子**：cheap IC 粗篩會漏「單獨 IC 低但組合/非線性強」的因子。三方共識「不可當唯一 gate」。**裁決**:粗篩用於 tier 降載與互動式預設;提供 explicit「full mode」(慢但全量,不截斷);report 永遠揭露 screened/total。這是 scale 與 quant 完備性的根本張力,須使用者/產品確認可接受「互動式預設粗篩 + 可選全量」。
- **candidate-only redundancy/centrality/PCA 漏共線**(codex)：未入候選的 crowding/共線看不到。可接受但須文件化 + report 標 truncated。
- **必須 golden 的清單**(三方合):串流 vs pandas 小矩陣 rtol 一致;timestamp 四路徑;resume 中斷一致;no-stale-cache fingerprint;cross-symbol 隔離;Welford ICIR vs 逐點;numba rank tie/NaN 行為。

## 5. 我的 Round-2 收斂建議（epic 骨架）
| Epic | 內容 | 準則 | 依賴 |
|---|---|---|---|
| **E0 止血** | GroupedConfig + timestamp unit + decay log 聚合 + to_thread + WS 真錯誤/停重連 | 正確性/體感 | 無,先合併 |
| **E1 feature_filter 落地** | schema 加 feature_filter + Stage A 套用 + metadata 揭露(原始/篩後/規則) | ③ | E0 |
| **E2 Stage0 catalog + chunk reader** | FeatureMatrixSource/catalog/fingerprint/chunk manifest;跳過 materialize 直讀 L7;chunk 對齊 group 邊界 | ①② | E1 |
| **E3 Stage4 串流 IC engine** | chunk exact IC + rolling summary sink(Welford) + decay/grouped chunk 化(只 survivors) | ①②④ | E2 |
| **E4 Stage5/6 串流驗證 + candidate gate** | FDR 串流;redundancy/VIF candidate 硬上限 + truncation 揭露;artifact-backed metric table | ①③⑤ | E3 |
| **E5 deep 10 模組 candidate-only** | centrality/orthogonalize/PCA 硬上限;rolling 序列只 top-N | ①④⑥ | E4 |
| **E6 cross-sectional 重設計** | 移除 concat;symbol readers + block aggregator;persistent task registry;100-symbol resume | ②③ | E3 |
| **E7 正確性 golden 套件** | 串流==pandas/timestamp/resume/stale-cache/cross-symbol/Welford golden | ③⑥ | 貫穿 |
| **E8 perf + 輸出** | Numba/prefix-sum/worker pool(microbench 後);top-N+壓縮輸出;spill retention | ④⑤ | E3 後 |
| **(E9 FF 上游 cap，獨立議)** | indicator 笛卡爾積 hard cap / preview 警示 | ④ | 與 IC 解耦 |

**順序**：E0(止血先合) → E1 → E2 → E3(最大收益) → E4/E6 → E5 → E8;E7 貫穿;E9 獨立。

## 6. 仍需 Round 3 收斂的點
1. staged screening 的「互動式預設粗篩 + full mode」是否使用者可接受（產品紅線）。
2. chunk 大小最終數字（需讀真實 430K manifest 的 group 分佈定）。
3. FF 上游是否同步加 cap（E9 要不要進這個 epic 群）。
4. preprocessor 跨欄操作分類（動工前必查的事實）。
