# 階段一 — Codex 家族獨立版

讀碼範圍已覆蓋：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`event_filter.py`、`api/services/ic_analysis_service.py`、`api/routes/ic_analysis.py`、`frontend/src/app/ic-analysis/page.tsx`、`frontend/src/components/ic-analysis/`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`。以下第 4、5 欄是 repo 現況，不是推測。

## 1. 單標的時序 IC

1. 🔍 核心問題  
   對某一個 symbol，單一 feature 今天的值，和未來收益是否穩定同向或反向相關？

2. 📐 業界標準做法  
   對齊 `feature_t` 與 `return_{t+h}`，常用 Spearman rank IC；看 IC mean、ICIR、t-stat/p-value、hit rate、分位數收益單調性。至少切 train/validation/test 或 walk-forward，IC 選因子只允許用訓練窗，測試窗只做一次驗證。

3. 🗂 資料形狀與輸入  
   單標的時序：index=time，columns=features；label 是同一 symbol 的 future return series。可從 labels HDF5 讀，也可由 kline close 生成 future return。

4. 📊 平台現況 + 實際怎麼實作  
   主路徑是 `ICFilterOrchestrator.analyze()` 八階段 pipeline：ingestion → preprocessing → label_generation → event_filter → IC → stat_validation → redundancy → report（`ic_filter_orchestrator.py:96-160`）。API 非 cross-sectional 時會 materialize feature library run 到 HDF5，再呼叫 `analyzer.analyze()`（`api/services/ic_analysis_service.py:160-210`）。IC 本體用 `compute_ic(features_df, label_series, method)`，rolling IC/ICIR 同時算（`ic_filter_orchestrator.py:1092-1152`）。沒有看到主路徑 train/test split；label 若沒給，直接用全段 kline 生成 future return（`ic_filter_orchestrator.py:1021-1055`）。

5. 🧩 全棧實作狀態  
   ✅ 全棧連通。前端 `global` 模式送成後端 `longitudinal`（`useICAnalysis.ts:123-162`），後端跑單標的 pipeline，UI 顯示 summary table、quantile、rolling、decay、grouped 等。  
   但有一個靜默失效：前端 Feature 預過濾只更新 selectedFeatures，也會把 `feature_filter` 送後端（`FeatureFilterPanel.tsx:46-62`, `useICAnalysis.ts:138-162`），後端把它 merge 到 override（`ic_analysis_service.py:967-970`），但 `ICConfig` schema 沒有 `feature_filter` 欄位（`ic_config_schema.py:319-351`），主 pipeline 沒有消費，所以實際 IC 仍跑全部 feature。

6. 🛡️ PIT 與洩漏防禦  
   最大地雷是用全樣本同時選因子與評估，ICIR/p-value 會樂觀。label 生成必須確認 `return_{t+h}` 不把未來價格泄入 feature preprocessing；事件 query 若用到 future 欄位也會泄漏。現況未見主路徑 split guard。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   單標的 430K×20K 要避免一次性 full correlation + full rolling dense output；應分 feature block 計算、只保留 top/borderline rolling traces、summary streaming 寫出。現況主 analyze materialize HDF5 後整個 DataFrame 進 pipeline，不適合百 symbol 全量同時跑。

8. 🔧 做對沒 / 漏洞  
   做對：核心 IC/rolling/ICIR/report 有端到端。漏洞：無 train/test、feature_filter 幽靈、DataFrame 全量路徑對 20K feature 壓力大、event/filter 先後順序可能讓 query 基於 raw_data 但 IC 基於 feature index 子集，需嚴格 index 對齊測試。

9. 🏷️ 優先級  
   P0：補 train/validation/test 或 walk-forward selection window；修 feature_filter 真正裁 feature；建立 scale-safe block IC。

## 2. Rolling IC / IC 時間序列

1. 🔍 核心問題  
   這個 feature 的預測力是否只在某段時間有效，還是跨時間穩定？

2. 📐 業界標準做法  
   用 rolling window 計算每個 feature 的 IC series，觀察均值、波動、ICIR、hit rate、autocorrelation、regime shift；rolling 結果不得用未來窗更新過去判斷。

3. 🗂 資料形狀與輸入  
   單標的時序矩陣 + label series；輸出是 feature → window → IC time series。

4. 📊 平台現況 + 實際怎麼實作  
   `ICEngine.compute_rolling_ic()` 對全樣本先 concat/dropna，Spearman 時先對全段 rank，再 rolling corr（`ic_engine.py:260+`；stage 呼叫在 `ic_filter_orchestrator.py:1105-1110`）。結果進 `rolling_ic_series` report（`ic_filter_orchestrator.py:1266-1278`）。這是單標的 rolling，不是 panel rolling。

5. 🧩 全棧實作狀態  
   ✅ 全棧連通。後端輸出 `rolling_ic_series`，前端 `RollingICChart` 在基本分析 tab 顯示（`page.tsx:735-738`）。

6. 🛡️ PIT 與洩漏防禦  
   注意 rank 計算若先對全段 rank，會把未來分布資訊帶入過去 rolling window。嚴格 PIT 應在每個 rolling window 內 rank/corr，或確認全段 rank 不作為可交易信號，只作描述統計。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   rolling series 是巨大輸出面。應用 stride、只輸出入選/topN features、壓縮時間軸、分塊算 rolling covariance，不要為 20K features 全部回傳完整 series 給前端。

8. 🔧 做對沒 / 漏洞  
   做對：已有 rolling windows、stride、ICIR、autocorr。漏洞：全段 rank 的 PIT 爭議、全量 rolling output 尺度危險、圖表可能無 timestamp axis 語義，只是 list。

9. 🏷️ 優先級  
   P1：P0 split 完成後，修 rolling PIT/rank 方式與輸出裁剪。

## 3. Pooled / Panel 時序 IC（多 symbol 普適性）

1. 🔍 核心問題  
   把多個 symbol 的時間序列放在一起後，feature 是否仍有普遍預測力，而不是只在單一 symbol 偶然有效？

2. 📐 業界標準做法  
   Panel long format `(timestamp, symbol, feature, label)`；可做 pooled Spearman/Pearson、symbol fixed effects、cluster-robust SE、per-symbol zscore/rank 後 pooled IC。必須避免大市值/長歷史 symbol 壓倒其他 symbol。

3. 🗂 資料形狀與輸入  
   MultiIndex `(timestamp, symbol)` 或 long table；features 同名同義；label 是每個 symbol 自己的 future return。

4. 📊 平台現況 + 實際怎麼實作  
   沒看到 pooled/panel time-series IC 主路徑。多 symbol API 目前只走 `mode == "cross_sectional"`，把多 symbol concat 後 set `_symbol` index（`ic_analysis_service.py:114-159`），再做每個 timestamp 的截面 rank IC（`ic_filter_orchestrator.py:162-335`）。這不是 pooled longitudinal IC。

5. 🧩 全棧實作狀態  
   ❌ 完全缺。前端有 cross-sectional 批次選擇，但沒有 pooled/panel 時序 IC 模式；後端沒有 pooled longitudinal analyzer。

6. 🛡️ PIT 與洩漏防禦  
   Panel pooled 最容易混入跨 symbol normalization 泄漏，例如用全市場全期間 mean/std 標準化；也容易把同 timestamp 多 symbol 當獨立樣本而低估 SE。應按 symbol 和 train window 做 preprocessing，SE 按 symbol/time cluster。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   必須 column/block streaming：每次處理 feature block × symbol chunk，先 per-symbol 對齊 label，再累積秩相關或近似 rank sketches。不要構造 430K×20K×100 dense panel。

8. 🔧 做對沒 / 漏洞  
   目前用 cross-sectional 功能容易被誤認為 panel 普適性。缺 pooled IC、缺 fixed-effect/cluster SE、缺 per-symbol contribution diagnostics。

9. 🏷️ 優先級  
   P0.5：使用者要百 symbol 泛用平台，這是核心缺口，但應排在主路徑 split/leakage 之後。

## 4. Symbol 一致性 / 普適性分析

1. 🔍 核心問題  
   同一個 feature 在不同 symbol 上方向是否一致？是否只是某一兩個 symbol 拉高平均？

2. 📐 業界標準做法  
   先算 per-symbol IC/ICIR，再看 sign agreement、dispersion、worst/best symbol、coverage、leave-one-symbol-out、symbol-weighted average；區分 universal、symbol-specific、sign-conflict features。

3. 🗂 資料形狀與輸入  
   多 symbol panel 或 per-symbol IC table：feature × symbol → IC/ICIR/hit rate/sample count。

4. 📊 平台現況 + 實際怎麼實作  
   後端在 cross-sectional mode 會建立 `cross_sectional_symbol_ic`：對每個 symbol，把該 symbol 時序內 feature 與 label 做 rank corr（`ic_filter_orchestrator.py:298-304`, `379+`），再用 sign agreement/dispersion 產 `cross_symbol_validation`。這是從 cross-sectional flow 衍生的 per-symbol 檢查，不是一般 longitudinal run 集合的一致性分析。

5. 🧩 全棧實作狀態  
   ⛓️‍💥 兩端有但連結不完整。後端 report 有 `cross_symbol_validation`，前端有 `CrossSymbolValidationPanel`，但 panel 放在 deep tab；cross-sectional 基本結果只明確顯示 heatmap，deep tab 可見性依 `deep_analysis_enabled`/deep report 條件，cross-sectional report 本身未必讓使用者看到一致性 panel。  
   判定：功能局部存在，但 UX/wiring 容易讓結果藏起來。

6. 🛡️ PIT 與洩漏防禦  
   普適性應用 train symbols 選因子、holdout symbols 驗證；不能看完所有 symbol 再宣稱 universal。若 symbol universe 是事後挑選，也會 survivor bias。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   per-symbol summary 可 streaming：每個 symbol/feature block 算 IC summary，落地 feature × symbol sparse/top table；前端只看 topN、conflict samples、drilldown，不傳完整 20K×100 大矩陣。

8. 🔧 做對沒 / 漏洞  
   做對：已有 sign conflict、universal/symbol-specific 粗分類。漏洞：綁在 cross-sectional flow、缺 holdout symbol、前端 panel 可見性不可靠、統計口徑不是明確 per-symbol longitudinal ICIR。

9. 🏷️ 優先級  
   P1：對泛用平台很重要；先把它獨立成明確「symbol consistency」報表，並修 UI 可見性。

## 5. 橫截面 IC

1. 🔍 核心問題  
   在同一個時間點，feature 能否把多個 symbol 的未來收益排序對？

2. 📐 業界標準做法  
   每個 timestamp 對所有 symbol 做 rank corr：`corr(rank(feature_{i,t}), rank(return_{i,t+h}))`；再沿時間取均值、ICIR、hit rate。需要足夠 symbol 數、同 timestamp 對齊、處理 missing、避免用未來 universe 成分。

3. 🗂 資料形狀與輸入  
   MultiIndex `(timestamp, symbol)`，同名 feature columns；label column 如 `return_1` 或外部 labels。

4. 📊 平台現況 + 實際怎麼實作  
   API cross-sectional mode 接 `cross_sectional_runs` 或 `symbols`，`load_multi()` 讀多 run，concat 成 MultiIndex（`ic_analysis_service.py:118-145`）。若沒 labels_path，固定從 kline 生成 `return_1` log label（`ic_analysis_service.py:146-152`, `1248-1285`）。Analyzer 按 timestamp group，對每個 feature 做 Spearman rank corr，輸出 `summary_table`、`rolling_ic_series.window_cross_sectional`、`cross_sectional_symbol_ic`（`ic_filter_orchestrator.py:162-335`）。

5. 🧩 全棧實作狀態  
   ✅ 全棧連通。前端有 `cross_sectional` mode、批次 selector、至少 2 symbols gate、50 因子提示、`CrossSectionalICHeatmap`（`ICConfigPanel.tsx:248-280`, `page.tsx:723+`）。  
   但 feature_filter 仍是靜默失效：前端用 filter 估算 feature count，後端實際沒有裁 feature，所以 UI 的 50 因子限制不保證後端真的只跑 50 個。

6. 🛡️ PIT 與洩漏防禦  
   必須固定當時可交易 universe；不能用事後存在的 symbol 清單。label horizon 需可配置且對齊 feature timestamp。現況無 labels_path 時固定 `return_1` log，和 UI horizon 多選不是同一件事，容易造成使用者誤解。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   截面 IC 每個 timestamp × feature 都要跨 symbol rank；100 symbols 還可，但 20K features × 430K timestamps 必須 feature chunk、timestamp chunk、topN output、後端 hard cap。前端 cap 不能替代後端 cap。

8. 🔧 做對沒 / 漏洞  
   做對：有真正 cross-sectional branch、MultiIndex 檢查、批次 run 選擇。漏洞：feature_filter/cap 不落地、label horizon 固定、p_value 為 None、沒有 train/test 或 time split。

9. 🏷️ 優先級  
   P1：已有基礎，可在 P0 leakage 修完後補後端 feature cap/filter、horizon wiring、p-value/SE。

## 6. 事件 / case-control 研究（使用者主戰場）

1. 🔍 核心問題  
   在某類事件發生前，哪些 pre-pattern 預示正例未來會漲/表現好，而負例不會？這不是只問「事件子集上的 IC」，而是問正反樣本的可區分前兆。

2. 📐 業界標準做法  
   明確事件清單：`event_id, symbol, timestamp, label/case_type, horizon, outcome`；用 event-time alignment 建立 pre-window features。case-control 要有正負樣本配對或分層抽樣、時間隔離、symbol/regime balance、train/test split、OOT validation。統計可用 conditional difference、logit/AUC、matched-pair tests、per-event pre-pattern attribution。

3. 🗂 資料形狀與輸入  
   事件清單 + 標籤是主資料：每列一個事件；features 是事件前 N bars 的摘要或 pattern 向量；labels 是正/負或多 horizon outcome。可回連 panel kline/features 取 pre-window。

4. 📊 平台現況 + 實際怎麼實作  
   現況只有 event filter，不是 case-control。前端 `event` mode 只提供 query textarea（`ICConfigPanel.tsx:258-270`）。Hook 只在 event mode 送 `event_query`（`useICAnalysis.ts:123-162`）。後端把 `event_query` merge 成 `event_filter.enabled/query`（`ic_analysis_service.py:956-962`）。Orchestrator stage3 用 query 對 raw_data 或 features 做 boolean mask，然後在事件子集上跑同一套 IC（`ic_filter_orchestrator.py:1057-1090`）。`EventFilter` 支援 query/timestamps mask（`event_filter.py:55-82`），但 orchestrator 把 `timestamps = None` 寫死（`ic_filter_orchestrator.py:1069-1082`）。API 收到 `event_timestamps` 只 warning，不支援（`ic_analysis_service.py:964-965`）。

5. 🧩 全棧實作狀態  
   ⚠️ 有但壞掉 / 語義不足。  
   對「event query subset IC」：前後端可跑。  
   對「事件 case-control 研究」：❌ 核心缺失。沒有顯式事件清單 ingestion、沒有 label/case_type、沒有正負配對、沒有 pre-window extraction、沒有 train/test/OOT、`event_timestamps` 是死線。這是使用者主戰場，不能把現有 event filter 當成已完成。

6. 🛡️ PIT 與洩漏防禦  
   最大雷：事件定義若包含未來 outcome，就不能拿同一 outcome 再驗證 feature；負例抽樣若從全期間事後挑，會有 look-ahead；pre-pattern 必須只使用 event timestamp 前的資料；同一 symbol 鄰近事件要 purge/embargo。

7. ⚡ 430K×20K×百 symbol 尺度對策  
   不應對全 panel 全 feature 暴力掃 case-control。先用事件清單定位 event windows，再只抽 pre-window feature block；事件級 table 可遠小於全量 panel。需要 event index store、symbol/time partition、precomputed feature block reader、正負抽樣 cache。

8. 🔧 做對沒 / 漏洞  
   做對：query 安全驗證有 blocklist 與 identifier check，事件子集樣本數 tier 有基本 guard。漏洞：沒有顯式事件清單、timestamps 未接通、query 只能產子集 IC、fallback insufficient 時直接回全樣本可能讓使用者以為事件分析已跑、沒有 case/control schema 與 split。

9. 🏷️ 優先級  
   P0 最高。這是使用者主戰場，應先設計事件資料模型與 case-control pipeline，再談 UI polishing。

## 橫向結論

P0 修正順序我會排：

1. 主 IC / event / cross-sectional 都補明確 train/validation/test 或 walk-forward selection discipline。
2. 把 `feature_filter` 從幽靈 wiring 變成後端實際裁 feature，並加後端 hard cap。
3. 建事件 case-control：事件清單、label、pre-window、negative sampling、purge/embargo、OOT。
4. 補 pooled/panel longitudinal IC 與獨立 symbol consistency report。
5. 再處理 rolling/cross-sectional 的 scale-safe output 與統計細節。

ASSUMPTIONS_VERIFIED: 已讀指定 repo 檔案並核對主路徑、cross-sectional branch、event query/timestamps、feature_filter wiring、前端 mode/payload/UI。
TESTS_RUN: read-only 任務；未跑 pytest/npm；使用 `sed`/`rg`/`nl` 做靜態查證。
FAILURES_SEEN: none。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none，未改程式。
HANDOFF_NOT_UPDATED: read-only 任務且使用者要求直接輸出內容，不寫交接檔、不更新 HANDOFF.md。
STATUS: DONE