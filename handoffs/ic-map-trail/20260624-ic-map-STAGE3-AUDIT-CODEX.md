VERDICT: CHANGES

1. FDR ⛓️‍💥 + 高風險假綠：屬實。
證據：`adjust_multiple_comparisons/_fdr_bh/_bonferroni` 存在於 [statistical_validator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/statistical_validator.py:58)，但 Stage5 只 `compute_ic_statistics` 後用 raw `p_value` threshold，未呼叫 FDR：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1165)、[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1187)。前端 `fdr_correction` toggle 存在：[FeatureTierPanel.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/FeatureTierPanel.tsx:38)，advanced preset 會開：[icAnalysisStore.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/store/icAnalysisStore.ts:130)，但 `getEffectiveConfig()` 不送 FDR：[icAnalysisStore.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/store/icAnalysisStore.ts:290)。API request/schema 也無 FDR 欄：[ic_models.py](/Users/louis/Desktop/quantitative_trading_system/api/models/ic_models.py:49)、[ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:319)。
改法：保留 Claude 判定；補一句「event_filter 的 `adjusted_p_threshold` 不是 FDR」。

2. 型1 global summary 無 `t_stat`、CI 算了不進 report：屬實，但行號/根因需修正。
證據：`compute_ic_statistics()` 確實算 `t_stat/ci_lower/ci_upper`：[statistical_validator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/statistical_validator.py:118)。真正第一個漏點是 `_build_summary_table()` 只放 `p_value`，未放 `t_stat/ci_*`：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1387)。`ic_reporter` CSV/JSON/MD 又只輸出 `p_value`：[ic_reporter.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_reporter.py:114)、[ic_reporter.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_reporter.py:241)、[ic_reporter.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_reporter.py:275)。前端 `t_stat` 會 fallback 推算，但 longitudinal 拿不到：[ICSummaryTable.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/ICSummaryTable.tsx:75)。
改法：把 synthesis 的 `ic_reporter:155` 改成「`ic_filter_orchestrator._build_summary_table`:1387 起未帶 `t_stat/ci_*`；`ic_reporter`:114 起二次漏匯出」。

3. 型4 train/test 主路徑缺、winsorize 全樣本 fit：屬實。
證據：`analyze()` Stage0→7 對同一 `features_df/label_series` 做 preprocessing、IC、Stage5、report，無 holdout：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:93)。Stage4 全量計算 IC：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1092)。Stage5 全量算統計與 thresholds：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1154)。winsorize 在 Stage1 對整個 df quantile/mean/std fit：[data_preprocessor.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/data_preprocessor.py:38)、[data_preprocessor.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/data_preprocessor.py:151)。
改法：保留 Claude 判定。

4. 型5/6 walk-forward/purged CV 在 deep tab / ML 孤島未接 IC 主流程：屬實，但需精準化。
證據：IC Rolling OOS 只在 deep module runners：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:609)，由 `_run_rolling_oos()` 呼叫：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:809)，前端只在 deep chart 顯示：[page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:800)。IC Rolling OOS splits 無 purge gap，train_end 直接接 test：[rolling_oos_validator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/rolling_oos_validator.py:163)。ML `WalkForwardValidator` 則有 `purge_gap/embargo_pct`：[walk_forward_validator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/model_validation/walk_forward_validator.py:18)，所以「無 purge/embargo」只能指 IC Rolling OOS，不可泛指 ML WF。CPCV 有 purge/embargo：[combinatorial_purged_cv.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/model_validation/combinatorial_purged_cv.py:18)，但從 `model_enhancement_service` 執行，不接 IC：[model_enhancement_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/model_enhancement_service.py:100)。
改法：改成「IC Rolling OOS deep tab 有、無 purge；ML WalkForward/CPCV 有 purge/embargo，但在 model-enhancement 孤島，IC 主流程未接」。

5. 階段三 7 型是否該加 Deflated Sharpe / PBO：Claude synthesis 漏定案，需改。
證據：四家原始版有提出或提到 PBO/Deflated Sharpe，synthesis 只放在「待委員檢查」，未進 9 欄。repo 內未見 Deflated Sharpe/PBO 實作；只見 Sharpe/proxy/overfitting gap 類功能，非 DSR/PBO。
改法：不必新增第 8 型；建議補入型5/6「業界標準/缺口」：CPCV 可估 PBO，factor-return/backtest Sharpe 應有 Deflated Sharpe 或至少 multiple-testing haircut。型1/2只處理 IC 顯著性與多重比較，不足以覆蓋策略 Sharpe 過擬合概率。

6. 9 欄業界標準/洩漏防禦與原始版重要點：大方向正確，但有兩處需修。
改法 A：型5 欄位不要寫成 WF/CPCV 整體無 purge；精準區分 IC Rolling OOS 無 purge vs ML WF/CPCV 有 purge 但孤島。
改法 B：型1 證據行號修正為 Stage5/summary/report 多段漏出，否則會讓人誤以為只有 exporter 問題。
未驗證：未跑 live 430K run、未驗證 WebSocket serialization；本次只做 read-only code inspection。

ASSUMPTIONS_VERIFIED: 已讀 synthesis、四家原始版與相關程式碼；逐項驗證 FDR wiring、summary/report 欄位、主 IC split、winsorize fit、Rolling OOS/CPCV/WalkForward 接線。
TESTS_RUN: read-only inspection only；使用 `rg`/`nl` 對照程式碼，未跑 pytest。
FAILURES_SEEN: none。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: read-only sandbox 且本任務要求審查輸出，不寫交接檔。
STATUS: DONE