# 階段一 — Composer（Cursor）獨立版

> **查證範圍**（2026-06-24）：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`event_filter.py`、`ic_config_schema.py`；`api/services/ic_analysis_service.py`、`api/models/ic_models.py`；`frontend/src/app/ic-analysis/page.tsx`、`ICConfigPanel.tsx`、`useICAnalysis.ts`、`icAnalysisStore.ts`；以及 `cross_symbol_validator.py`、`cross_symbol_training_service.py`、`signal_density_analyzer.py`（事件 case-control 對照）。
>
> **家族**：Composer 2.5（Cursor）。本輪獨立產出，未參閱他族 Round 1 全文。

---

## 總覽判斷（階段一橫切）

| # | 分析類型 | 全棧狀態（摘要） |
|---|---------|----------------|
| 1 | 單標的時序 IC | ✅ 主路徑連通，但 **全量物化 + 無 train/test + 幽靈 feature_filter** 使大 run 不可信/不可用 |
| 2 | Rolling IC / IC 時間序列 | ✅ 後端+圖表連通；⚠️ 依賴 #1 全量跑完，且 grouped/decay 崩潰會連帶白算 |
| 3 | Pooled / Panel 時序 IC | ❌ **完全缺**（無 engine、無 API mode、無 UI） |
| 4 | Symbol 一致性 / 普適性 | 🔌 僅 cross-sectional 路徑內建 IC 矩陣版；XGB LOSO 在別服務、**未接入 IC 主流程** |
| 5 | 橫截面 IC | 🔌 後端+UI 有；⚠️ `pd.concat` 多 symbol 全 panel + 無 server 端 50 因子硬限 |
| 6 | 事件 / case-control | ⛓️‍💥 **最危險斷裂**：UI「Event 模式」≠ 使用者主戰場 case-control；`event_timestamps` / Case Search 均未接通 |

---

## 1. 單標的時序 IC

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 對**單一 symbol**，在 bar `t` 的特徵值，能否預測 `t+h` 的 forward return？（「這個訊號在這個幣上到底有沒有預測力？」） |
| **📐 業界標準做法** | 對齊 `(feature_t, return_{t→t+h})`，算 Spearman/Pearson IC；報告 IC mean、t-stat、p-value、樣本數；選因子前應有 **in-sample / OOS 或 purged split**，避免在同一視窗上既選又驗。 |
| **🗂 資料形狀與輸入** | **單標的時序**：`features_df` shape `(T, C)` + `label_series` shape `(T,)`；index 對齊（DatetimeIndex 或 epoch）。輸入來源：Feature Library run（symbol + timeframe + config_hash）或 legacy HDF5 path。 |
| **📊 平台現況+實際怎麼實作** | **逐 symbol、非 pool**：`ic_analysis_service._run_analysis` longitudinal 分支一次只處理一個 symbol（`:161-216`）。`FeatureLibrary.load()` 全量載入 → `_materialize_features_for_ic` 寫整張 `(T,C)` 到 HDF5（`:1123-1136`）→ `ICFilterOrchestrator.analyze()` stage0 再全量讀回（`:986-1014`）。IC 本體：`ICEngine.compute_ic()` 對**所有欄位**算 pairwise corr（`ic_engine.py:74-102`）。**無 train/test 切分**：stage4 在**全樣本**上算 IC 並進 stage5 閾值篩選。`split_id` 僅存在 `compute_ic_from_l7_raw`（IC-First 選特徵路徑，`ic_engine.py:117-118`），**主 UI analyze 路徑未使用**。Label：無 `labels_path` 時用 kline `close` 現場生成 forward return（orchestrator `:1037-1055`）。 |
| **🧩 全棧實作狀態** | **後端**：✅ `ICEngine` + orchestrator stage4 + `ICAnalysisService` API 完整。**前端**：✅ `ICConfigPanel` Run 選擇器 + `ICSummaryTable` + `FilterFunnelChart`。**連結**：✅ `/analyze` → task → `/result` 通。**判定：✅ 全棧連通（功能層）**，但 **⛓️‍💥 feature_filter 幽靈**（見下）+ **主 analyze 同步阻塞 event loop**（`:209-216` 無 `asyncio.to_thread`，deep analysis 才有 `:544`）→ 大 run 體感卡死。 |
| **🛡️ PIT與洩漏防禦** | **Label 洩漏**：forward return 生成依賴 `create_label_generator`，需確認 horizon 不偷看未來（引擎假設正確，但 **無獨立 split 驗證**）。**特徵洩漏**：依賴 FF L6.5 PIT；IC 層不再審計。**選因子洩漏（高風險）**：同一全樣本上算 IC → 閾值篩選 → 報告 top features，**無 purged CV / holdout**；`rolling_oos` 在 deep analysis 模組、非 stage4 必經。 |
| **⚡ 430K×20K×百symbol 尺度對策** | **現況不可行**：`load` + materialize 需 `T×C` float32 常駐（430K×20K ≈ 34GB 僅矩陣）。L7 串流 IC（`compute_ic_from_l7_raw`）存在但 **UI 主路徑未走**。應：**feature-chunk 串流 IC**、禁止全量 concat、stage0 只載 metadata + 分塊讀 parquet；8GB tier 需 chunk size 機制（optimization handoff 共識）。 |
| **🔧 做對沒/漏洞** | **做對**：vectorized Spearman（無 missing 時）、八階段 pipeline 結構清晰、config_hash fail-closed（近期 run-selector）。**漏洞**：(1) 幽靈 `feature_filter`——前端預設 `max_features:30`（`icAnalysisStore.ts:187`），API 塞入 override（`ic_analysis_service.py:967-970`），但 `ICConfig` schema **無此欄**（`ic_config_schema.py:319-353`），orchestrator **零處理** → 使用者以為篩 30 實跑 45k；(2) 全量物化；(3) 無 OOS gate；(4) analyze 阻塞 WS。 |
| **🏷️ 優先級** | **P0**（地基；但須先修 feature_filter + 串流 + split 才能承載你的尺度） |

---

## 2. Rolling IC / IC 時間序列

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 這個訊號的預測力是**穩定**還是**時好時壞**？IC 會不會只在某段行情有效？ |
| **📐 業界標準做法** | 滾動視窗（如 21/63/126 bars）算 IC 序列 → ICIR = mean(IC)/std(IC)；觀察 IC 符號翻轉、衰減、與波動 regime 的關係。視窗單位應與 timeframe 對齊。 |
| **🗂 資料形狀與輸入** | 同 #1 的 `(T,C)` + label；輸出每 feature 每 window 一條長度 ≈ `T/window` 的 IC 序列（stride 可配置，預設 1）。 |
| **📊 平台現況+實際怎麼實作** | `ICEngine.compute_rolling_ic()`（`ic_engine.py:268-302`）：rank 後 `_rolling_corr_matrix` 向量化；windows 由 config `rolling_windows: [21,63,126]`（`ic_config_schema.py:66-67`）。orchestrator stage4 必算 rolling + `compute_icir` + `compute_ic_autocorrelation`（`:1105-1110`）。報告欄位 `rolling_ic_series`（`:1276`）。**與 decay/grouped 共用同一 `features_df` 全量輸入**。 |
| **🧩 全棧實作狀態** | **後端**：✅ 完整實作。**前端**：✅ `RollingICChart` 綁 `report.rolling_ic_series[feature]`（`page.tsx:734-737`）。**連結**：✅ 報告 JSON 直出。**判定：✅ 全棧連通**。**但**：若 `include_regime_analysis=True` 觸發 grouped_ic 崩潰（見 #1 漏洞），整 task failed → rolling 結果也拿不到。decay 熱迴圈 14k warning log 拖慢（`ic-grouped-crash-perf-ANALYSIS.md` 已驗證）。 |
| **🛡️ PIT與洩漏防禦** | 滾動 IC 視窗只用 **當下視窗內** 的 (feature, label) 對，不偷未來 label（假設 label 已是 forward return）。**但**：rolling 序列仍在**全樣本 in-sample** 上算，後續閾值篩選會「看過」整段 IC 分佈 → **選因子洩漏**未解。 |
| **⚡ 430K×20K 尺度對策** | 複雜度 O(C×T×W)；瓶頸在 **C 維全量**（與 #1 相同）。應先 **候選特徵 gate**（metadata 篩選 / stage A 串流 IC）再算 rolling；或只對 top-K **survivor** 算 rolling（需審計語義：survivor 如何選）。 |
| **🔧 做對沒/漏洞** | **做對**：向量化 rolling spearman、ICIR/IC hit rate 一併產出、前端圖表齊。**漏洞**：(1) 大 C 無防護；(2) 與崩潰的 grouped/decay 同 stage4 批次執行；(3) 無 OOS rolling IC。 |
| **🏷️ 優先級** | **P1**（穩定性診斷必備；依賴 #1 尺度修復後才有意義） |

---

## 3. Pooled / Panel 時序 IC（多 symbol 普適性）

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 把**所有 symbol、所有時間**的觀測堆在一起，這個 pattern **總體**上有預測力嗎？（回答「普適性」，不是「某幣碰巧有效」） |
| **📐 業界標準做法** | **Pooled IC**：concat 多幣 `(feature, label)` 對，算一個總 IC（或 weighted by symbol）。**Panel**：固定效應 / 隨機效應模型，或 Fama-MacBeth（逐期截面再時序平均）。**關鍵**：跨 symbol 前須 **rank/z-score 標準化**（價格尺度、波動不同）。 |
| **🗂 資料形狀與輸入** | **Panel/Pooled**：`(T×N_sym, C)` 長表，或 MultiIndex `(timestamp, symbol)` × features + label；可選 symbol 權重、流動性過濾。 |
| **📊 平台現況+實際怎麼實作** | **grep 全 repo：無 `pooled_ic` / `panel_ic` engine 或 API mode**。`load_multi` 僅服務 **cross_sectional** 模式（`ic_analysis_service.py:130-154`），語義是 **每個 timestamp 橫向 rank corr**（#5），**不是** pooled longitudinal IC。`CrossSymbolTrainingService` 做 XGB LOSO，是 **ML 泛化** 而非 IC pooled（`cross_symbol_training_service.py:24-79`）。 |
| **🧩 全棧實作狀態** | **後端**：❌ 無專用模組。**前端**：❌ 無模式/圖表。**連結**：N/A。**判定：❌ 完全缺**。 |
| **🛡️ PIT與洩漏防禦** | 設計時須：(1) 跨 symbol 標準化只用 **當期截面** 統計量；(2) label 對齊同一 horizon；(3) symbol 間 **cache/run 隔離**（config_hash per symbol）；(4) pooled 篩因子後仍需 **symbol-holdout** 驗證。 |
| **⚡ 430K×20K×百symbol 尺度對策** | **禁止** `pd.concat` 全 panel（cross-sectional 已踩）。應：**symbol-block 串流** → 線上累積 pooled 統計量（Welford / 分位數 sketch）；或 **two-pass**：pass1 per-symbol IC sign → pass2 只對 universal survivor 做 pooled。百 symbol 需 resume + fingerprint。 |
| **🔧 做對沒/漏洞** | **缺口本身**即最大漏洞：使用者要的「普適性」在 SCOPE 標 **[完全缺][高]**，與 #4（一致性）和 #5（橫截面）**語義不同**，不能互相替代。 |
| **🏷️ 優先級** | **P0（高）** — 你的多幣場景核心護城河；應獨立 epic，不可假裝 cross-sectional 已覆蓋。 |

---

## 4. Symbol 一致性 / 普適性分析

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 這個因子在 **BTC 有效、ETH 翻車** 還是 **方向一致、普遍有效**？哪些因子是 symbol-specific？ |
| **📐 業界標準做法** | (1) **Per-symbol IC 矩陣** + sign agreement / dispersion；(2) **LOSO**（leave-one-symbol-out）訓練/測試；(3) ICIR 跨 symbol 分佈、universal vs specific 分類；(4) 可視化 heatmap (symbol × feature)。 |
| **🗂 資料形狀與輸入** | MultiIndex panel 或 dict `{symbol: (T,C)}`；輸出 `symbols × features` IC 矩陣 + 聚合分數。 |
| **📊 平台現況+實際怎麼實作** | **路徑 A（IC 內建，僅 cross-sectional）**：`analyze_cross_sectional` → `_build_cross_sectional_symbol_matrix`（orchestrator `:353-377`：每 symbol 算時序 IC）→ `_build_cross_symbol_validation`（`:379-469`：consistency_score、sign_conflict、universal_features）。**路徑 B（ML LOSO）**：`CrossSymbolValidator.run_leave_one_symbol_out`（`cross_symbol_validator.py:113-144`），經 `CrossSymbolTrainingService`，**僅測試/fixture 調用**，**無 IC UI 入口、無 `/analyze` 整合**。**單 symbol global/event 模式**：不算跨 symbol 一致性。 |
| **🧩 全棧實作狀態** | **後端**：🔌 兩套實作（IC 矩陣版 vs XGB 版），後者孤立。**前端**：🔌 `CrossSymbolValidationPanel` 在 **深度分析 Tab**（`page.tsx:759-761`），資料來自 `report.cross_symbol_validation` 或 deep payload；**僅 cross-sectional 主分析會自動產生**。**判定：🔌 後端有、前端部分有；⛓️‍💥 XGB LOSO 與 IC 主流程未連結；單幣模式完全無一致性視圖**。 |
| **🛡️ PIT與洩漏防禦** | Per-symbol IC 應各自 PIT-safe run（config_hash 隔離）。LOSO 若在同一時間軸上打亂 symbol **不**算 OOS——須 **時間切分** 或 **symbol holdout**。現況 XGB 路徑無時間 purging。 |
| **⚡ 430K×20K×百symbol 尺度對策** | 矩陣版只需 **per-symbol 摘要 IC**（C 維可串流），不必物化全 panel。百 symbol × 20k features：先 per-symbol top-K 或 IC>|threshold| 再建矩陣。 |
| **🔧 做對沒/漏洞** | **做對**：`_build_cross_symbol_validation` 有 sign_conflict / universal 啟發式分類（`:423-439`）。**漏洞**：(1) 與 pooled IC（#3）未整合；(2) ML validator 未接入；(3) 單幣使用者看不到一致性；(4) cross-sectional 的 per-symbol IC 是 **各幣全樣本 IC**，非 pooled。 |
| **🏷️ 優先級** | **P0**（多幣研究必備；應與 #3 同一 epic） |

---

## 5. 橫截面 IC（Cross-Sectional IC）

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 在**同一時刻**，橫向比較多 symbol，特徵值高的幣是否明天漲更多？（「截面排序」預測力，非單幣時序） |
| **📐 業界標準做法** | 每個 timestamp `t`：對 `{symbol_i}` 算 `rank_corr(feature_{i,t}, return_{i,t+1})`；再對時間平均得 mean IC、ICIR；常配合行業中性、市值中性。 |
| **🗂 資料形狀與輸入** | MultiIndex `(timestamp, symbol)` × `(C+1)` numeric；label 為各 symbol forward return。至少 2 symbols × 每 slice ≥2 有效樣本。 |
| **📊 平台現況+實際怎麼實作** | API `mode=cross_sectional`（`ic_models.py:59-61`）；service `load_multi` 各 symbol → **`pd.concat(frames)` 全 panel**（`ic_analysis_service.py:135-144`）→ `analyze_cross_sectional`（orchestrator `:162-338`）。核心：按 timestamp `groupby`，每 slice 對每 feature 算 rank corr（`:228-241`）。附帶產出 `cross_sectional_symbol_ic` 矩陣（#4 路徑 A）。Label：無 `labels_path` 時 `_append_cross_sectional_labels` 從 kline 生成。 |
| **🧩 全棧實作狀態** | **後端**：✅ `analyze_cross_sectional` 完整。**前端**：✅ 模式選擇器 + 批次 Run 選擇（`ICConfigPanel.tsx:225-244`）+ `CrossSectionalICHeatmap`（`page.tsx:715-718`）+ `ICSummaryTable` cross 欄位。**連結**：✅ payload 送 `cross_sectional_runs`（`useICAnalysis.ts:168`）。**判定：✅ 全棧連通（小規模）**；**⚠️ 大規模會 OOM/極慢**；UI 顯示「最多 50 因子」（`ICConfigPanel.tsx:278-279`）但僅 **前端預估**（`page.tsx:119-161` 用 `featureFilter` 本地篩），**後端無硬限** → 可送 20k 欄。 |
| **🛡️ PIT與洩漏防禦** | 截面 IC 本身只用 `t` 時刻特徵 vs `t→t+h` return（若 label 生成正確）。**洩漏點**：全時間平均 IC 後在同一資料上篩因子；多 symbol 若共用錯誤 config_hash 會 **跨 run 污染**（run-selector 已部分修復）。 |
| **⚡ 430K×20K×百symbol 尺度對策** | 現況 `concat` = **(T×N)×C** 記憶體炸彈。必改：**timestamp-block 串流**（每 t 只載 N×C_chunk），或 feature-chunk × symbol-block（optimization CONVERGED 共識）。百 symbol 需取消全 panel 物化。 |
| **🔧 做對沒/漏洞** | **做對**：語義正確的 per-timestamp rank corr；symbol 矩陣 + validation 附贈。**漏洞**：(1) concat OOM；(2) 50 因子限僅 UI 文案；(3) 與 #3 pooled longitudinal 混淆風險；(4) 無 train/test。 |
| **🏷️ 優先級** | **P1**（有實作但需重設計才可上百 symbol） |

---

## 6. 🎯 事件 / Case-Control 研究（使用者主戰場）

| 欄 | 內容 |
|----|------|
| **🔍 核心問題** | 我有 **正例事件**（如大漲前形態）和 **負例/對照**，事件前 `pre-pattern` 視窗內特徵分佈是否系統性不同？這個 pattern 能否區分正反例？ |
| **📐 業界標準做法** | **顯式事件清單** `(timestamp, symbol, label∈{+,-})` + 可選 matched controls；提取事件前 `W` bars 特徵；比較 mean/Mann-Whitney/Cohen's d 或 **條件 IC**；多重比較 FDR；case-control 須防 **標籤洩漏**（特徵視窗嚴格在事件前）。平台內 `SignalDensityAnalyzer` 已實作此範式（`signal_density_analyzer.py:1-18`：TO 前 N 根密度、positive vs negative t-test）。 |
| **🗂 資料形狀與輸入** | **事件清單 + 標籤**：`List[{case_id, symbol, event_ts, case_type}]`；**pre-pattern 視窗** `TrainingWindowConfig`；特徵矩陣可事後對齊到事件窗。 **不是** 全序列 `(T,C)` 上的布林 query 而已。 |
| **📊 平台現況+實際怎麼實作** | **IC「Event 模式」**（前端 `config.mode==='event'`）：僅多送 `event_query` 字串（`useICAnalysis.ts:177`）→ API 轉 `event_filter.enabled + query`（`ic_analysis_service.py:956-961`）→ `EventFilter.apply_filter` 對 **kline DataFrame** 做 `df.eval(query)` 布林遮罩（`event_filter.py:73-83`；orchestrator stage3 用 kline 作 filter_base `:1072-1083`）→ 剩餘 rows 上跑 **標準時序 IC**（非 case-control 統計）。**`event_timestamps` 顯式清單**：API 收到只 `logger.warning("not supported")`（`:964-965`）；orchestrator stage3 **硬編碼 `timestamps=None`**（`:1070`）。**Case Search → IC**：無程式路徑；Case Search 在 `/search`，Signal Density 在 optimization/chart_signals，**與 `/ic-analysis` 無 import/路由串接**。**真正 case-control 引擎**在 `SignalDensityAnalyzer`，**不在 IC Gatekeeper 管線內**。 |
| **🧩 全棧實作狀態** | **後端**：🔌 `EventFilter` 有（query 版）；❌ 無 case 清單輸入；❌ IC 管線未調用 `SignalDensityAnalyzer`。**前端**：🎨 `Event-Driven 模式` + query textarea（`ICConfigPanel.tsx:259-270`）；❌ 無匯入 Case Search 結果、無正負例標籤 UI、無 pre-window 設定。**連結**：⛓️‍💥 **兩端有「事件」字眼但語義錯位**——UI 稱 Event，實作是 **全序列子集 IC**；使用者要的 case-control 在 **另一套系統**。**判定：⛓️‍💥 兩端有但沒連結（靜默語義錯誤）**；若開 decay+regime 還會 **⚠️ 崩潰**（與 #1 相同）。 |
| **🛡️ PIT與洩漏防禦** | **Query 模式風險**：若 query 含當期/未來欄位（如 `close > future_high`），`eval` 無 PIT 審計 → **未來函數**。**Case-control 風險**：pre-pattern 視窗必須 **嚴格 < event_ts**；正負例須 **匹配市場環境** 否則虛假分離。**現況**：無顯式 case 時間錨點 → 無法保證 pre-pattern 對齊。樣本數：`check_sample_size` 有 tier（`event_filter.py:128-144`），不足時 **fallback 全樣本**（orchestrator `:1085-1087`）→ **靜默放寬**。 |
| **⚡ 430K×20K 尺度對策** | Case-control 應 **事件驅動稀疏採樣**：只算 `N_cases × W × C_event`（通常 N≪T）。現況 query 子集仍對 **子集上全 C** 跑 IC → 未利用稀疏性。應：**事件清單 → 只投影相關 bars/特徵 chunk**；與 FF L7 串流結合。 |
| **🔧 做對沒/漏洞** | **做對**：query 有 blocklist 安全驗證（`event_filter.py:39-50`）；樣本數 tier 會調 p-value 閾值（stage5 `:1166-1171`）；`FilterFunnelChart` 可顯示 stage3 event 資訊。**漏洞（致命）**：(1) **無顯式事件清單**；(2) Event 模式 ≠ case-control；(3) `event_timestamps` 未實作；(4) Case Search 斷裂；(5) insufficient events **fallback 全量**；(6) 與 SignalDensity 重複建設、使用者不知走哪條路。 |
| **🏷️ 優先級** | **P0（最高）** — 你的主戰場；應定義 **單一 canonical 事件分析契約**（清單輸入 + pre-window + 正反例標籤），並決定是擴展 IC 管線還是將 SignalDensity 升格為一級 UI。 |

---

## 跨類型基礎設施問題（影響多欄）

| 問題 | 影響分析 | 證據 |
|------|---------|------|
| 幽靈 `feature_filter` | #1 #2 #5 #6 全量 C | API override → schema 無 → orchestrator 無 |
| 主 analyze 阻塞 event loop | 全部 UI 任務 | `_run_analysis` 同步 `analyzer.analyze()` |
| `GroupedConfig` vs `dict` 崩潰 | #1 #2 報告附帶 decay/grouped | orchestrator `:1139` → `ic_engine.py:377 config.get` |
| 無 train/test / purged CV | #1–#6 選因子洩漏 | 主路徑全樣本；`rolling_oos` 僅 deep 可選 |
| 全量 `FeatureLibrary.load` + HDF5 materialize | #1 #5 #6 | `ic_analysis_service.py:1123-1136` |

---

## 建議 Epic 排序（僅階段一範圍）

1. **P0 — 事件契約**：顯式 `event_timestamps` / Case Search 匯入 + pre-pattern 視窗 + 與 `SignalDensityAnalyzer` 或 IC 管線統一。
2. **P0 — 止血**：`feature_filter` 落地或改名 `preview_limit` + metadata 審計；`GroupedConfig.model_dump()`；analyze `to_thread`。
3. **P0 — Pooled IC + Symbol 一致性**：新 engine + 與 #4 矩陣共用輸出層。
4. **P1 — 串流化**：L7/feature-chunk IC 接入主 UI；cross-sectional 移除 `pd.concat`。
5. **P1 — Purged split**：stage4 前強制 `split_id` / selection_window（對齊 `ic_engine` IC-First 已有欄位）。

---

## 誠實邊界聲明

- 第 4、5 欄均來自 **2026-06-24 實際讀碼**；未跑 live 430K run（無法在本文證明 OOM 閾值，但 materialize 路徑與 handoff 實測 45k×1696 一致）。
- `CrossSymbolTrainingService` 是否曾從 production UI 觸發：**未找到路由/前端引用**，僅測試與 ARCHITECTURE 文件。
- grouped/decay 崩潰：**引用 handoff 實測 + 讀碼確認契約不一致**；本文未重現 runtime。

---

HANDOFF_NOT_UPDATED: READ-ONLY 任務，使用者要求直接輸出存檔。
