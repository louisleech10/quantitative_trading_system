# 階段三—統計嚴謹度與防偽獨立版

查證基準：讀了 `HANDOFF.md`、`CLAUDE.md`，並查 `momentum/Analysis/*`、`api/services/ic_analysis_service.py`、`api/services/model_enhancement_service.py`、`frontend/src/app/ic-analysis/page.tsx`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/hooks/useICAnalysis.ts`。本輪 read-only，未改檔。

## 1. IC 顯著性（t-stat / p-value / bootstrap CI）

1. 🔍核心問題：IC 是真的穩定大於 0，還是 rolling windows 裡剛好抽到好運？
2. 📐業界標準做法：對 IC 時序做均值 t-test、p-value、CI；金融時序應補 Newey-West/HAC 或 block bootstrap，避免自相關高估顯著性。
3. 🗂資料形狀與輸入：每 feature 一串 rolling IC values；平台從 `rolling_ic` dict 收集成 array。
4. 📊平台現況+實作：`StatisticalValidator.compute_ic_statistics()` 有 t-stat、p-value、t CI；主流程 Stage 5 呼叫它並用 raw p-value gate。證據：`statistical_validator.py:24-32,95-138`、`ic_filter_orchestrator.py:1165-1191`。但 `_build_summary_table()` 只輸出 `p_value`，沒有輸出 `t_stat/ci_lower/ci_upper`，前端 t-stat 欄多數拿不到。
5. 🧩全棧狀態：⚠️有但壞掉。後端算了 t/CI/p，但 report 只帶 p；前端 `ICSummaryTable` 有 t-stat/P-Value 欄，p-value 可顯示，t-stat 對 longitudinal 幾乎斷線。
6. 🛡️PIT與洩漏防禦：label generation 用 future return 是 IC 目的本身；但顯著性沒有校正 overlapping rolling windows、自相關、事件 cluster。
7. ⚡尺度對策：20K features × rolling IC array 可算，但若 430K rows、stride=1、三個 windows，全量 rolling IC 記憶體與輸出很重；目前沒有 streaming significance，只先算 rolling_ic 再統計。
8. 🔧做對沒/漏洞：raw p-value gate 有用；t-stat/CI 報表漏出；無 Newey-West；bootstrap estimator 不是 IC 用的 block bootstrap。
9. 🏷️優先級：P0。這是「是不是運氣」的主門檻，現在容易過度自信。

## 2. FDR / 多重比較校正

1. 🔍核心問題：一次測 20K features，p<0.05 會自然冒出一堆假陽性。
2. 📐業界標準做法：Bonferroni 保守控 family-wise error；Benjamini-Hochberg 控 FDR；報表需同時保留 raw p 與 adjusted p。
3. 🗂資料形狀與輸入：`{feature: p_value}`，理想上是所有候選 features 的 p-values，不只 top_n。
4. 📊平台現況+實作：`StatisticalValidator.adjust_multiple_comparisons()`、`_bonferroni()`、`_fdr_bh()` 已存在。證據：`statistical_validator.py:58-73,141-160`。但 `ic_filter_orchestrator._stage5_statistical_validation()` 沒呼叫，只拿 `p_value_max` 直接篩。
5. 🧩全棧狀態：⛓️‍💥兩端有但沒連結靜默失效。後端演算法存在；前端 advanced preset 有 `fdr_correction: true`，但 `getEffectiveConfig()` 沒把它送進後端；後端 schema 也無 FDR flag/method。
6. 🛡️PIT與洩漏防禦：FDR 本身不防 look-ahead，只防 multiple testing 假陽性；目前未啟用，所以防偽缺口大。
7. ⚡尺度對策：20K p-values 排序 O(n log n) 很便宜；真正問題是要保存全量 p-values，不可只對 top 30 做校正。
8. 🔧做對沒/漏洞：BH 實作方向正確；主流程完全沒套用；前端顯示「FDR 多重比較校正」會誤導使用者以為已防偽。
9. 🏷️優先級：P0。主戰場 20K features，這是必修。

## 3. Block Bootstrap / Clustered SE

1. 🔍核心問題：樣本不是 iid；相鄰 K 線、同事件、同 symbol 會相關，普通 SE/CI 會太樂觀。
2. 📐業界標準做法：time block bootstrap、stationary bootstrap、clustered SE by event/symbol/date，或 Newey-West HAC。
3. 🗂資料形狀與輸入：IC series + timestamp/event_id/symbol cluster；case-control 需要 event cluster。
4. 📊平台現況+實作：`BootstrapEstimator` 存在，但做的是 ML metric 的 iid row bootstrap：AUC/PR-AUC/Brier/precision_at_10，`rng.integers(0,n,n)` 抽樣。證據：`bootstrap_estimator.py`。未見 IC block bootstrap、clustered SE、Newey-West。
5. 🧩全棧狀態：❌完全缺針對本題的版本。後端有普通 bootstrap 類，但不是 IC/block/clustered；前端無呈現。
6. 🛡️PIT與洩漏防禦：目前無 cluster/purge 概念；事件 case-control 中同一行情片段可能被當成多個獨立樣本。
7. ⚡尺度對策：全量 block bootstrap 對 430K×20K 不能 naive 重算；應對 rolling IC 或 per-feature sufficient stats 做 chunked/parallel bootstrap，並限制 B 次數。
8. 🔧做對沒/漏洞：現有 bootstrap 若拿來宣稱 IC CI 會錯；缺 block length 選擇、cluster id、symbol-level aggregation。
9. 🏷️優先級：P1。FDR/raw p 先補，block/cluster 接著補，尤其事件 case-control 必要。

## 4. Train/Test Split（主路徑）

1. 🔍核心問題：篩 feature 是否只在同一批資料內看起來好，到了未來樣本就失效？
2. 📐業界標準做法：時間序列 train/validation/test 或 OOT split；feature selection 只能在 train/validation 完成，test 最後一次使用。
3. 🗂資料形狀與輸入：features_df rows=time/events，cols=features；label_series；timestamp index。
4. 📊平台現況+實作：IC 主 `analyze()` 是 ingestion → preprocessing → label → event filter → IC → stat validation → redundancy → report，沒有 split。`TimeSplitter`/OOT/PurgedTimeSeriesSplit 存在於 ML/XGBoost 路徑，不是 IC 主路徑。
5. 🧩全棧狀態：❌IC 主路徑缺。後端其他 ML 模組有 split 工具，IC 分析頁沒有 train/test gate。
6. 🛡️PIT與洩漏防禦：主路徑沒有 holdout，無法阻止使用者在全樣本上挑 feature；event filter 也不是 train/test isolation。
7. ⚡尺度對策：430K rows 可按 timestamp 切，不貴；真正要避免的是為每 split 重載 20K features，可用 column chunks + cached labels。
8. 🔧做對沒/漏洞：主 analyze 產出的 p-value/ICIR 是全樣本內評估，不是 OOS 能力；泛用平台使用者容易誤當可上線。
9. 🏷️優先級：P0。這是防過擬合主路徑。

## 5. Walk-Forward / Rolling OOS

1. 🔍核心問題：feature 在多段未來樣本是否都有效，還是只在某段有效？
2. 📐業界標準做法：rolling/expanding train window + forward test window；看 IS/OOS gap、OOS hit rate、退化期。
3. 🗂資料形狀與輸入：IC deep module 用 feature series + label series；ML walk-forward 用 model_factory + X/y。
4. 📊平台現況+實作：IC 有 `RollingOOSValidator`，計算 per-feature IS IC / OOS IC、degradation、assessment。由 `run_deep_analysis()` 的 `_run_rolling_oos()` 呼叫，不在主 Stage 5 gate。另有 `model_validation/walk_forward_validator.py` 走 ML AUC，不接 IC task。
5. 🧩全棧狀態：✅全棧連通但只是 deep tab；🔌主流程未接。IC 頁可按「深度分析」跑 Rolling OOS 並顯示 `OOSDistributionChart`；不會阻止主結果通過。
6. 🛡️PIT與洩漏防禦：Rolling OOS split 是 train 後接 test，方向正確；但 IC 版沒有 purge/embargo，重疊 horizon 或事件群仍可能洩漏。
7. ⚡尺度對策：前端 deep 預設 top 30，API top_n 上限 200，避開 20K 全跑；這可用但代表不是全量防偽。
8. 🔧做對沒/漏洞：作為診斷 OK；作為 gate 不夠。ML WalkForward 與 case-control / IC feature selection 沒接。
9. 🏷️優先級：P0/P1。先把 Rolling OOS 變成可選硬 gate；ML WalkForward 可放 P1。

## 6. Purged / Combinatorial Purged CV

1. 🔍核心問題：label horizon 重疊、事件前後相鄰資料會讓 train 看到 test 附近資訊。
2. 📐業界標準做法：Purged K-Fold、embargo、CPCV；尤其金融 ML 需要按事件 span purge。
3. 🗂資料形狀與輸入：X/y、timestamp/order、label span 或 horizon、groups；CPCV 還需要 n_groups/n_test_groups。
4. 📊平台現況+實作：`CombinatorialPurgedCV` 有 `purge_gap`、`embargo_pct`、group combinations、AUC paths。證據：`combinatorial_purged_cv.py:20-82,84-150`。API 在 `/api/v1/model-enhancement/cpcv`，從 `model_task_id` payload 取 X/y/model_factory。
5. 🧩全棧狀態：🔌後端有，IC/事件主流程缺。不是 IC Gatekeeper 主流程；不是 case-control 搜尋/分析主流程；前端 IC 頁沒有 CPCV。
6. 🛡️PIT與洩漏防禦：CPCV 版有 purge/embargo，但按 sample index，不是事件 span；若 case-control 有 event duration，現在沒看到接入。
7. ⚡尺度對策：`max_paths` 預設 50，避免組合爆炸；但 430K×20K 每 path 訓練模型很重，需 feature subset/streaming/抽樣策略。
8. 🔧做對沒/漏洞：模型驗證工具存在；沒有成為 IC selection 的防偽流程；purge_gap 是固定 row count，不保證匹配 horizon/timeframe/event span。
9. 🏷️優先級：P1。事件 case-control 要升級為 span-aware purged split。

## 7. 極端值影響診斷

1. 🔍核心問題：某個 feature 的好 IC 是否被少數極端行情/錯值撐起來？
2. 📐業界標準做法：winsorize 前後 IC 對比、leave-one-event-out、Cook’s distance/influence、top-k contribution、tail-only stress。
3. 🗂資料形狀與輸入：feature values、labels、timestamps/event_id/symbol；需要能標出影響最大的 rows/events。
4. 📊平台現況+實作：有 preprocessing winsorization；`FeatureQualityDiagnostics` 有 ADF 前 winsorize、Ljung-Box、coverage、drift、redundancy。證據：`feature_quality_diagnostics.py`。但沒有「極端值影響」專門診斷。
5. 🧩全棧狀態：❌完全缺核心診斷；🎨/🔌只有相鄰功能。前端有 Quality Dashboard，但顯示的是 stationarity/autocorrelation/coverage/drift，不是 outlier influence。
6. 🛡️PIT與洩漏防禦：winsorization 可降低極值，但若用全樣本分位數做預處理，仍需確認是否 train-only；這輪未追到完整 preprocessing 分位數 fit 邊界。
7. ⚡尺度對策：不能對 20K features 做完整 leave-one-row-out；可先用 top influence approximation：按 `abs(z_feature * z_label)` 或 per-event contribution 篩 top rows，再對 top features 做精算。
8. 🔧做對沒/漏洞：Quality Diagnostics 名稱容易讓人以為已防極端值；實際未回答「少數點移除後 IC 是否崩掉」。
9. 🏷️優先級：P1。對事件 case-control 很重要，因為事件樣本少且尾部行情容易主導結論。

## 總判斷

目前階段三不是完全空白，但「存在」和「接主流程」差距很大：

- 主 IC gate 真正有用的是 raw p-value。
- FDR 是最明顯的 ⛓️‍💥：後端方法有、前端開關有、主流程沒接。
- Rolling OOS 是 deep tab 診斷，不是主流程防偽 gate。
- WalkForward/CPCV 是 ML model-enhancement 孤島，未接 IC/case-control。
- Block bootstrap/clustered SE、極端值影響診斷基本缺。
- Train/test split 在 IC 主 analyze 確認缺失。

ASSUMPTIONS_VERIFIED: 已讀碼確認 StatisticalValidator/FDR 存在但 Stage 5 未呼叫 adjusted p；IC 主 analyze 無 train/test split；Rolling OOS 接 IC deep-analysis；WalkForward/CPCV 在 model-enhancement；FeatureQualityDiagnostics 非 outlier influence。
TESTS_RUN: read-only code inspection only；未跑 pytest。
FAILURES_SEEN: none。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: read-only 任務且使用者要求直接輸出，不改檔。
STATUS: DONE