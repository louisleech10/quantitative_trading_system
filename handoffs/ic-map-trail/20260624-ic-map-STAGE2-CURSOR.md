=== codex 在跑? ===
       8
# 階段一 — Cursor 獨立版

**組織法**：訊號研究生命週期 5 階段  
**本輪範圍**：階段二「品質、動態與細節」（撐多久？線性？挑對環境？穩定？）  
**查證範圍**：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`event_filter.py`、`monotonicity_tester.py`、`api/services/ic_analysis_service.py`、`frontend/src/app/ic-analysis/`、`frontend/src/components/ic-analysis/`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/hooks/useICAnalysis.ts`  
**查證日期**：2026-06-24

---

## 階段二總覽（你的處境對照）

| 你的已知痛點 | 本階段四分析中的落點 |
|---|---|
| 無 pooled IC | 分位/單調、decay、grouped 全是 **單標的時序全樣本 IC**；cross-sectional 只做 IC/ICIR，**不算** decay/quantile/grouped |
| 主路徑無 train/test | 四分析皆在 **同一全樣本** 上算；`rolling_oos` 在 deep analysis，非主路徑 |
| grouped/decay 會崩潰 | **已確認**：`GroupedConfig` pydantic 傳入 `config.get()` → AttributeError；decay 45k×7 horizons 熱迴圈 + 萬級 warning log |
| 幽靈 feature_filter | 直接放大 #1 #2 #3 的計算量（假篩 30、真跑 45k） |

---

## 分析 1：分位 / 單調性分析

| # | 欄位 | 內容 |
|---|---|---|
| 1 | 🔍 **核心問題** | 因子值從低到高排，未來收益是否 **單調遞增**？是線性預測力還是只有極端分位有用？Long-short 價差是否顯著？ |
| 2 | 📐 **業界標準做法** | 每期（或 pooled panel）對因子 `qcut` 成 Q1–Q5（或 Q10）；算各分位平均 forward return、累積曲線、Q5−Q1 spread + t-test；單調性 = 相鄰分位收益遞增比例或 Spearman(分位序, 分位收益)；常與 turnover 一起看。事件研究：在 **事件 bar** 上對 pre-pattern 特徵做分位，label = 事件後 N bar 報酬。 |
| 3 | 🗂 **資料形狀與輸入** | **標準**：`(date × symbol)` panel 或事件清單 `(event_id, feature, label)`。**本平台主路徑**：單標的 `DataFrame(index=bar, columns=features)` + 單一 `label Series`（對齊 index）；**非** cross-sectional rank IC；**非**顯式正/反案例清單 API。 |
| 4 | 📊 **平台現況 + 實作** | **後端**：`MonotonicityTester`（`monotonicity_tester.py`）— `pd.qcut` 分位、`compute_monotonicity_score`（相鄰 diff>0 比例）、long-short spread + t-test；`ic_filter_orchestrator._stage5` 對 **全部 columns** `compute_all`（逐 feature Python 迴圈，:141–165）。**逐 symbol**：一次 analyze = 一個 symbol 的 HDF5 物化矩陣（stage0 `_load_features_hdf5`），非百 symbol pool。**事件**：stage3 `EventFilter` 用 `df.eval(query)` 在 kline 或 features 上切 **列子集**；`event_timestamps` API **未接線**（service :964–965 只 warning）。**train/test**：無；全樣本算分位。**開關**：`monotonicity_test` 在 `LOCKED_TOGGLES`（`icAnalysisStore.ts:138`）— **永遠執行**，無法關；`report.include_quantile_curves` 在 schema 存在但 orchestrator **未消費**（死配置）。 |
| 5 | 🧩 **全棧實作狀態** | **後端**：✅ 有（stage5 必跑）。**前端**：✅ `QuantileReturnChart`、`FactorEquityCurveChart`（deep tab）、`ICSummaryTable` 的 `monotonicity_score`；`ICConfigPanel` 可調 `monotonicity_score_min`。**連結**：⚠️ **schema 錯位** — report 寫入 `quantile_returns[feature] = { quantile_returns: {...}, monotonicity_score, long_short }`（orchestrator :1270），前端 `QuantileReturnChart` 期望頂層 `quantile_mean_returns` / `long_short_spread`（`QuantileReturnChart.tsx:13–17`）→ 圖表常顯示「暫無數據」，但 summary table 的 score **有值**。**判定**：🔌 **後端有、前端圖表接錯形狀（靜默空圖）**；summary 路徑 ✅。REST `/quantile/{feature}`（`ic_analysis.py:234`）同形狀問題。 |
| 6 | 🛡️ **PIT 與洩漏防禦** | 分位應在 **每期只用當期橫截面** 劃分；現況對整段時序一次 `qcut` = **全樣本分位**，含未來分布 → 分位邊界洩漏。事件模式若 query 用到未來欄位（如事後標記）會 look-ahead。無 IS/OOS：用全樣本挑「單調性好」的因子 → 選因子洩漏。 |
| 7 | ⚡ **430K×20K×百 symbol** | 複雜度 **O(n_features × n_bars × n_quantiles)**，45k features × 1.7k bars 已實測可跑數十分鐘級；百 symbol 若逐 symbol 重複 = 線性放大。**對策**：Stage A 候選集 gate（非幽靈 max_features）、分位只對 top-K、串流/分塊 qcut、事件子樣本先切再算。 |
| 8 | 🔧 **做對沒 / 漏洞** | **做對**：qcut 降 bin（樣本不足改 3 分位）、min_group_size=30、long-short t-test、threshold 可篩 `monotonicity_score_min`。**漏洞**：(1) 全樣本 qcut 洩漏；(2) 輸出 schema 與前端不一致；(3) 與幽靈 feature_filter 疊加全量 20k–45k 迴圈；(4) 事件 case-control 語義未建模（無正/反案例 label 分離）。 |
| 9 | 🏷️ **優先級** | **P0**（階段二入門圖 + 篩選門檻；先修 schema 對齊 + feature_filter 落地，否則大 run 不可用） |

---

## 分析 2：IC 衰減 / 半衰期

| # | 欄位 | 內容 |
|---|---|---|
| 1 | 🔍 **核心問題** | 預測力能 **撐幾根 bar**？peak horizon 在哪？半衰期多短？若 peak 在 horizon=1 且快速衰減 → 高換手、難實盤。 |
| 2 | 📐 **業界標準做法** | 對 horizon h=1,2,3,5,… 各算 IC(feature, forward_return_h)；畫 IC decay curve；指數擬合 `IC(h)≈A·e^{-λh}` 得 half_life=ln2/λ；或算 IC 自相關 / signal persistence。事件研究：事件後第 k bar 的 IC 序列。 |
| 3 | 🗂 **資料形狀與輸入** | 單標的 `(bars × features)` + `close`（從 kline reader）→ 各 horizon 重算 label `close.shift(-h)/close-1` 再算 IC。需 **價格序列與 feature index 對齊**。 |
| 4 | 📊 **平台現況 + 實作** | **後端**：`ICEngine.compute_ic_decay`（`ic_engine.py:331–363`）— 對 `ic_decay_horizons` 預設 `[1,2,3,5,8,13,21]` 逐 horizon 全量 `compute_ic`，再 `_fit_exponential_decay` 得 half_life/decay_rate/R²。觸發：`config.report.include_decay_analysis` + `kline_reader` 有 close（orchestrator :1122–1131）。**逐 symbol**；**無** train/test。**cross-sectional**：`analyze_cross_sectional` 硬編碼 `"ic_decay": {}`（:321）。**開關**：`featureToggles.ic_decay` → `report.include_decay_analysis`（`STAGE_OVERRIDE_PATHS` :61–62）；foundation preset **關閉**，intermediate **開啟**。 |
| 5 | 🧩 **全棧實作狀態** | **後端**：✅ 邏輯完整，但 ⚠️ **大 run 會崩/極慢**（見 #8）。**前端**：✅ `ICDecayChart`（half_life、fit_r2、bar→小時換算）、summary 欄 `ic_half_life`；`FeatureTierPanel` 可 toggle。**連結**：✅ `report.ic_decay[feature]` 形狀與 `ICDecayData` 一致；REST `/decay/{feature}` 通。**判定**：⚠️ **有但大尺度壞掉**（效能 + grouped 連帶崩潰中斷整 job）；小 fixture 路徑 ✅。 |
| 6 | 🛡️ **PIT 與洩漏防禦** | 各 horizon 的 forward return 必須 **嚴格 shift(-h)**（程式有，`close.shift(-horizon)` :991）；但若在同一全樣本上挑「半衰期長」的因子再回測 → 選因子洩漏。decay 擬合用 **全樣本 IC 曲線** 做參數選擇亦偏樂觀。 |
| 7 | ⚡ **430K×20K×百 symbol** | **O(n_features × n_horizons × n_bars)**；45k features 實測 **14,090 條** per-feature warning log（`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`）。**對策**：候選 feature 先砍到 K≪20k、horizon 向量化 batch IC、熱迴圈零 log（聚合摘要）、decay 可選「只對 summary top-N」。 |
| 8 | 🔧 **做對沒 / 漏洞** | **做對**：多 horizon、指數擬合 fail-closed（R²<0.5 標 non_exponential）、`fit_warning` 進 report warnings（orchestrator :1515–1544）。**漏洞**：(1) 逐 feature Python 雙迴圈；(2) `_fit_exponential_decay` 熱迴圈 `logger.warning`；(3) 與 grouped 同 stage4 串行，grouped 崩潰則 decay 白算；(4) 無 OOS decay 驗證；(5) 幽靈 feature_filter → 對 45k 全算。 |
| 9 | 🏷️ **優先級** | **P0**（修 crash + log 聚合 + feature guard）；**P1**（向量化 + golden，命中數值正確性） |

---

## 分析 3：分組 / 狀態（Regime）條件 IC

| # | 欄位 | 內容 |
|---|---|---|
| 1 | 🔍 **核心問題** | 因子在 **牛市/熊市/高波動/低波動** 還有效嗎？是否只在特定環境有用（挑對環境）？跨年度是否穩定？ |
| 2 | 📐 **業界標準做法** | 按 regime 變數切子樣本，各子樣本算 IC / 分位收益；rule-based（MA、vol percentile）或 unsupervised（HMM/K-Means on vol/trend/momentum）；報告 regime IC 雷達圖 + 「全 regime 同號」穩健性。Panel 研究：每 (date, symbol) 先標 regime 再 pool。 |
| 3 | 🗂 **資料形狀與輸入** | 需 `features + label + raw OHLCV`（close/volume）對齊 index。輸出 `grouped_ic`: `{ by_year, by_quarter, by_regime, by_category, by_data_source, by_layer }` → 每組 `{group_key: {feature: ic}}`。 |
| 4 | 📊 **平台現況 + 實作** | **後端**：`ICEngine.compute_grouped_ic`（:365–419）— year/quarter 用 `_iter_time_groups`；`by_regime` → rule（bull/bear/high_vol/low_vol，EMA55 + vol percentile :1052–1089）或 `RegimeDetector` K-Means（:1091–1129）；metadata 分組用 feature meta。**條件**：`include_regime_analysis=True` + `raw_data` from kline（orchestrator :1133–1139）。**逐 symbol**；**無** pooled regime IC。**事件**：事件切列後，regime 仍在 **剩餘全段** kline 上算 mask（非「僅事件當下 regime」）。**train/test**：無。 |
| 5 | 🧩 **全棧實作狀態** | **後端**：⚠️ **有但會崩** — `orchestrator:1139` 傳 `GroupedConfig` pydantic → `ic_engine:377` `config.get("method")` → **`'GroupedConfig' object has no attribute 'get'`**（實測 handoff）。**前端**：✅ `GroupedICBarChart`、`RegimeRadarChart`；toggle `grouped_ic`。**連結**：形狀 ✅（`by_regime` → `{regime: {feature: ic}}`）；但 **intermediate 預設開啟** → 大 run 必觸發崩潰。**判定**：⚠️ **有但壞掉**（P0 crash）；修後為 🔌（cross-sectional 永遠空 `grouped_ic`）。**額外**：schema `by_volatility: true` 但 `compute_grouped_ic` **無此分支**（契約漂移）。 |
| 6 | 🛡️ **PIT 與洩漏防禦** | Rule regime 用 EMA/vol rolling — 若窗口含未來 bar 會洩漏（目前 rolling 向後看，尚可）；K-Means `expanding=True`（:1116）意圖 PIT，但 **全樣本 fit 標籤語義** 需審計。`_get_time_index` 數值 timestamp **硬編碼 unit=ms`**（:1024–1025）— kline 若為 **秒** 則 year/quarter 分組錯軸（老問題重演）。用全樣本 regime IC 選因子 → 環境過擬合。 |
| 7 | ⚡ **430K×20K×百 symbol** | 每個分組對 **全部 features** 呼叫 `compute_ic`（內層仍逐 feature）；regime 4 種 × metadata 多維 × 45k ≈ **數百萬次**相關。百 symbol 無 cross-regime pool。**對策**：只對 top-K 算 grouped、regime 先算 mask 再投影、並行按組、修 `model_dump()` 先能跑通。 |
| 8 | 🔧 **做對沒 / 漏洞** | **做對**：多維分組、rule + kmeans 兩路、`RegimeDetector` 獨立模組。**漏洞**：(1) **P0 型別契約崩潰**；(2) `by_volatility` 幽靈配置；(3) timestamp 秒/毫秒；(4) `regime_robust` 在 summary **永遠 None**（orchestrator :1404，未實作）；(5) 無跨 symbol regime 一致性。 |
| 9 | 🏷️ **優先級** | **P0**（A1：`grouped_analysis.model_dump()` + 真 config 回歸測試）；**P1**（timestamp 實測 + regime_robust 落地） |

---

## 分析 4：穩定性 / 一致性（Win Rate、ICIR）

| # | 欄位 | 內容 |
|---|---|---|
| 1 | 🔍 **核心問題** | IC 是正的多常見（**win rate / hit rate**）？相對波動是否夠小（**ICIR = mean/std**）？滾動 IC 是否漂移？跨標的、跨時段是否一致？ |
| 2 | 📐 **業界標準做法** | Rolling IC 序列 → IC_mean、IC_std、**ICIR**、**IC>0 比例**；IC 自相關；walk-forward / rolling OOS IC；cross-sectional 每日 rank IC 再聚合；「全樣本 IC 顯著」≠ 穩定，業界看 **ICIR>0.5** 且 **hit rate>55%** 且 OOS 不塌。 |
| 3 | 🗂 **資料形狀與輸入** | **Longitudinal**：`rolling_ic[feature][window_W]` 時序 → 聚合 ICIR/hit rate。**Cross-sectional**：每 timestamp 橫截面 rank corr → `ic_series[feature]` 列表（orchestrator :228–241）。**事件**：事件子集後 rolling 樣本變短，hit rate 不穩。 |
| 4 | 📊 **平台現況 + 實作** | **後端**：`compute_rolling_ic` + `compute_icir`（`ic_engine.py:304–329`）— `ic_hit_rate = mean(IC>0)`；`StatisticalValidator.compute_ic_statistics` 得 p_value（rolling IC t-test）；`compute_ic_autocorrelation`（:421）**有算但未進 report**（stage4 放入 `ic_results` :1147，stage7 `analysis_results` **未輸出**）。**Thresholds**：`icir_min` 0.5、`ic_hit_rate_min` 0.55（`ic_config_schema.py:101–104`），`_apply_thresholds` 會剔特徵。**Cross-symbol**：僅 `analyze_cross_sectional` 的 `_build_cross_symbol_validation`（consistency_score）；longitudinal **無**。**train/test**：主路徑無；`rolling_oos` 在 deep analysis module（`RollingOOSValidator`）。**開關**：`ic_autocorrelation` toggle 存在但 **無 STAGE_OVERRIDE 路徑** → 算了也沒用。 |
| 5 | 🧩 **全棧實作狀態** | **後端**：✅ ICIR/hit rate/p_value 在 summary；⚠️ ic_autocorr 幽靈計算；⚠️ `regime_robust` 未實作。**前端**：✅ `ICSummaryTable`（ICIR、Positive Rate、排序）；✅ `RollingICChart`；✅ `ICConfigPanel` 調 `icir_min`；`CrossSymbolValidationPanel` 在 **deep tab**（`page.tsx:759`），且 `crossSymbolValidationData` 優先 deep report — longitudinal 主報告 **通常無** cross_symbol。**連結**：summary + rolling ✅；cross-symbol ⛓️‍💥 **算在 cross-sectional 主報告卻 UI 放在 deep tab**；ic_autocorr ⛓️‍💥 **後端算、不輸出、前端 toggle 假開關**。**判定**：核心 ICIR/hit rate = ✅；擴展穩定性 = 🔌/⛓️‍💥。 |
| 6 | 🛡️ **PIT 與洩漏防禦** | Rolling IC 窗口若含當期 label 需確認 stride/window 對齊（目前同 index 上 rolling corr）。**最大洩漏**：用 **全樣本 rolling IC** 算 ICIR 並在同一數據上 threshold 篩選 → 樂觀偏差。應 rolling walk-forward：train 窗估 ICIR，test 窗驗證。事件樣本少時 hit rate 統計功效不足（event_filter 有 tier 調 p_value，:1166–1171）。 |
| 7 | ⚡ **430K×20K×百 symbol** | Rolling IC 已部分向量化（`rank` + `_rolling_corr_matrix`）；瓶頸在 **45k columns** 全量 rolling + 全量 ICIR。Cross-sectional 對 **每 timestamp × 每 feature** 迴圈（:228–241），百 symbol × 千日可接受，但 **不含** 本階段 decay/grouped。**對策**：streaming/block IC、只對候選集算 rolling、ICIR 用單一 reference window（已固定 63）。 |
| 8 | 🔧 **做對沒 / 漏洞** | **做對**：多 window rolling、ICIR 標準定義、threshold 可 refilter、cross-sectional 有 consistency_score + sign conflict 偵測。**漏洞**：(1) 無 OOS ICIR gate；(2) ic_autocorr 未輸出；(3) regime_robust 占位 None；(4) cross-symbol UI 門閂錯位；(5) longitudinal 無跨標的一致性（你的百 symbol case-control 主戰場缺口）；(6) cross-sectional summary 的 `p_value: None`（:271）。 |
| 9 | 🏷️ **優先級** | **P0**（ICIR/hit rate 已是篩選核心，確保大 run 能算完 + 輸出可信）；**P1**（walk-forward / rolling_oos 提升到主路徑或基礎 tab）；**P2**（ic_autocorr 輸出 + UI） |

---

## 跨分析「靜默斷裂」清單（Cursor 查證）

| 類型 | 現象 | 證據 |
|---|---|---|
| ⛓️‍💥 幽靈 feature_filter | UI 預設 `max_features:30`，後端 merge，**ICConfig 無欄位、orchestrator 零處理** | `icAnalysisStore.ts:187` → `useICAnalysis.ts:176` → `ic_analysis_service.py:967` → `ic_config_schema.py:319–353` 無 `feature_filter` |
| ⛓️‍💥 quantile 圖表 schema | 後端巢狀 `quantile_returns.quantile_mean_returns`，前端讀頂層 | orchestrator :1270 vs `QuantileReturnChart.tsx:13–17` |
| ⛓️‍💥 event_timestamps | API 欄位存在，orchestrator 不傳 | `ic_analysis_service.py:964–965`；`event_filter.py` 支援 timestamps 但 stage3 只傳 query |
| ⛓️‍💥 ic_autocorrelation toggle | 前端可切，後端算了不進 report | `ic_filter_orchestrator.py:1110,1147` vs stage7 :1266–1278 |
| ⚠️ grouped_ic 崩潰 | intermediate 預設開，大 run 必炸 | `ic_filter_orchestrator.py:1139` + handoff 實測 |
| ⛓️‍💥 cross_symbol UI | 資料在 cross-sectional 主 report，面板在 deep tab | `page.tsx:759` vs orchestrator :333 |

---

## 階段二優先級總排序（Cursor 觀點）

1. **P0 — 止血**：`feature_filter` 真落地或改名 `preview_limit` + metadata；`GroupedConfig.model_dump()`；decay 熱迴圈 log 聚合；analyze `asyncio.to_thread`（否則 WS 假死）。
2. **P0 — 正確性地基**：train/validation 切分或 walk-forward selection window（否則四分析答案用於「選因子」皆帶洩漏）。
3. **P1 — 接線修復**：quantile_returns 輸出 flatten；`regime_robust` 實作；timestamp 秒/毫秒實測。
4. **P1 — 你的主戰場**：顯式 **case-control 事件清單 + label**（正/反 pre-pattern），非僅 `df.eval` 列篩選。
5. **P2 — 尺度**：decay/grouped 向量化 + golden；cross-sectional 補 decay/grouped 或明確文檔「不支援」。

---

**誠實邊界**：第 4、5 欄皆為 2026-06-24 讀碼結論；未在本機重跑 45k analyze（依 handoff 實測 log）。`rolling_oos`、walk-forward 等 **深度模組** 未展開讀碼，穩定性欄位僅標註其在 deep path 的存在。

**HANDOFF_NOT_UPDATED**：使用者指定 READ-ONLY 產出，不修改根 `HANDOFF.md`。
