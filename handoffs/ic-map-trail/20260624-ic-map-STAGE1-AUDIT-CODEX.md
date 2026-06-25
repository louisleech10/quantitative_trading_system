VERDICT: CHANGES

**Required Changes**

1. Type 4 `consistency_score` wording is too strong.
Evidence: [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:420) computes `sign_agreement`, but [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:427) also mixes in dispersion, and [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:429) defines score as `0.7 * sign_agreement + 0.3 * dispersion_score`.
Change synthesis lines 13/39/62 from “consistency_score 做 sign 一致性” to “consistency_score 是 sign agreement + dispersion 的加權分數；`sign_conflict_features` 才是明確方向衝突偵測”.

2. Type 6 “核心套件全缺” is inaccurate.
Evidence: [signal_density_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/signal_density_analyzer.py:12) defines positive vs negative signal-density separation, and the IC flow does not call it. Existing event flow is query subset IC: [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1081).
Change line 52/15 to: “IC case-control 契約 / 管線 / UI 全缺；相關 `SignalDensityAnalyzer` 和 case search 存在於另一套系統但未接入 IC Gatekeeper.”

3. Type 6 should explicitly mention `event_timestamps` dead wiring and insufficient-event fallback.
Evidence: API model accepts timestamps at [ic_models.py](/Users/louis/Desktop/quantitative_trading_system/api/models/ic_models.py:67), service only warns at [ic_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/ic_analysis_service.py:964), orchestrator hardcodes `timestamps = None` at [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1069), and insufficient events fall back to full sample at [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1085).
Change Type 6漏洞欄加：`event_timestamps` API 假入口、事件不足時 fallback 全樣本，屬靜默語義風險.

4. Type 2 leakage defense is incomplete.
Evidence: rolling Spearman ranks the full aligned sample before rolling windows at [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:288).
Change line 29 from only “窗 left-closed/right-current” to include: “現況 Spearman rolling 先全段 rank，再 rolling corr；若用作 PIT 評估/選因子，需改為 window-local rank 或標為描述統計.”

5. Type 5 timestamp bug is attached to the wrong surface.
Evidence: cross-sectional grouping uses MultiIndex levels at [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:219), while `_get_time_index` numeric `unit="ms"` is in grouped/regime helper at [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:1018).
Change line 47 to say timestamp ms/sec bug affects grouped/regime time grouping, not proven to affect `analyze_cross_sectional` timestamp grouping directly.

6. Type 5 misses label horizon mismatch.
Evidence: frontend sends `labels.horizons` at [useICAnalysis.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/hooks/useICAnalysis.ts:48), but cross-sectional fallback label generation hardcodes horizon `1` and log return at [ic_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/ic_analysis_service.py:1273).
Change Type 5漏洞欄 add: “fallback labels 固定 `return_1` log，與 UI horizons 可能不一致.”

**Confirmed Accurate**

Type 1 ✅ functional-layer status plus ghost `feature_filter` is accurate: frontend sends `feature_filter` at [useICAnalysis.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/hooks/useICAnalysis.ts:176), service merges it at [ic_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/ic_analysis_service.py:967), but `ICConfig` has no such field at [ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:319).

Type 4 `🔌/⛓️‍💥` status is directionally accurate: cross-sectional mode builds symbol IC matrix and validation at [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:298), panel is only rendered inside deep tab at [page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:750), and single-symbol longitudinal/event mode does not produce a meaningful consistency view.

Type 6 event-query semantic mismatch is accurate: UI is only query textarea at [ICConfigPanel.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/ICConfigPanel.tsx:264), service maps it to `event_filter.query` at [ic_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/ic_analysis_service.py:956), and `EventFilter` applies boolean row filtering at [event_filter.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/event_filter.py:73).

No additional Stage 1 “signal validity exploration” type was found that all four missed. Regime/conditional IC and neutralization are important diagnostics, but they fit under existing rolling/grouped robustness rather than a missing top-level Stage 1 type.

ASSUMPTIONS_VERIFIED: Read synthesis, four source handoffs, and checked IC backend/frontend code paths for types 1/4/5/6 plus rolling leakage.
TESTS_RUN: read-only static review with `sed`, `nl`, `rg`; no pytest/npm run.
FAILURES_SEEN: none.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none.
HANDOFF_NOT_UPDATED: read-only sandbox and user requested review output only.
STATUS: DONE