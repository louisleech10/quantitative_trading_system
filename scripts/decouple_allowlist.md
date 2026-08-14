# Decoupling Import Allowlist

本表是 R2/R3 AST scanner 的唯一機讀豁免來源；每列皆為完整 module 與顯式 symbol。

| module | allowed_symbols | module_import | owner | contract |
|---|---|---|---|---|
| momentum.FeatureEngineering.atomic.warmup_lookup | get_warmup_bars,get_warmup_factor | deny | committee/DECOUPLE-TRIAGE | 行為凍結的 warmup 與資料品質政策 |
| momentum.FeatureEngineering.consumer_gate | TrainingReadError,assert_consumer_run_status,effective_run_status,intersect_columns_without_masking,is_source_run_status_reusable | deny | committee/DECOUPLE-TRIAGE | browse=open、strict=closed、cache-reuse=closed 三語意契約 |
| momentum.FeatureEngineering.feature_reader | FeatureReader | deny | committee/DECOUPLE-TRIAGE | L7 解碼屬資料正確性介面 |
| momentum.FeatureEngineering.run_locks | RunBusyError,is_run_active | deny | committee/DECOUPLE-TRIAGE | 單寫者契約且 probe 具有檔案系統副作用 |
| momentum.FeatureEngineering.run_paths | cgsa_work_dir,features_run_dir | deny | committee/DECOUPLE-TRIAGE | Feature Factory 儲存 layout 凍結 |
| momentum.FeatureEngineering.utils.hardware_utils | TIER_THRESHOLDS,get_current_tier_gb,get_memory_tier,get_tier_concurrent_symbols,get_tier_config | deny | committee/DECOUPLE-TRIAGE | Feature Factory hardware tier 運維政策；package 錯位列 P3 |

## 新揭露暫豁免（pending triage）

| module | allowed_symbols | module_import | owner | contract |
|---|---|---|---|---|
| momentum.Strategy.performance_metrics | PerformanceMetrics | deny | pending/DECOUPLE-TRIAGE-2 | 舊 scanner 盲區既存依賴，暫豁免維持現狀；真偽 triage 另立票 |
| momentum.Analysis.strategy_registry | strategy_registry | deny | pending/DECOUPLE-TRIAGE-2 | 舊 scanner 盲區既存依賴，暫豁免維持現狀；真偽 triage 另立票 |
| momentum.Analysis.pareto_analyzer | ParetoAnalyzer | deny | pending/DECOUPLE-TRIAGE-2 | 舊 scanner 盲區既存依賴，暫豁免維持現狀；真偽 triage 另立票 |
| momentum.FeatureEngineering.feature_config | SUPPORTED_TIMEFRAMES | deny | committee/DECOUPLE-SCAN2 | 行為凍結 timeframe 驗證常數；relocate-to-core-constants P3（codex 少數意見）；重複副本債另記 |

## 戳記

<!-- v2 格式：RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<task-id> — <理由> -->
RECONCILE-STAMP: codex APPROVED 2026-07-14 sha256:65a7c0a97bf13cf4514c71070bff8b64fba31d1829a53dc49bd53b0455efff8e task:DECOUPLE-SCAN2 — 既有 9 條與前版逐行一致；新增 SUPPORTED_TIMEFRAMES 精準 symbol 豁免符合 DECOUPLE-SCAN2 多數終判，contract 忠實保留 relocate-to-core-constants P3 的 codex 少數意見與重複副本債。
RECONCILE-STAMP: composer APPROVED 2026-07-14 sha256:65a7c0a97bf13cf4514c71070bff8b64fba31d1829a53dc49bd53b0455efff8e task:DECOUPLE-SCAN2 — 既有 9 條與 aad9495^ 逐列等值未動；第 10 條 feature_config/SUPPORTED_TIMEFRAMES 白名單與 §C 終判一致（symbol 級、module_import=deny、owner=committee/DECOUPLE-SCAN2），contract 忠實含 relocate-to-core-constants P3（codex 少數意見）及重複副本債另記。
RECONCILE-STAMP: grok APPROVED 2026-08-14 sha256:65a7c0a97bf13cf4514c71070bff8b64fba31d1829a53dc49bd53b0455efff8e task:20260814-GOVMOUNT-X-REVIEW-R1 — 獨立重算 body hash 與 codex/composer 一致；10 條豁免逐列核：module 皆可 import、allowed_symbols 皆存在、module_import=deny 全表一致；6 條 committee 契約可對應現用介面；3 條 pending/DECOUPLE-TRIAGE-2 標暫豁免誠實；SUPPORTED_TIMEFRAMES 精準 symbol 豁免與 contract 之 relocate-to-core-constants P3 少數意見保留。
