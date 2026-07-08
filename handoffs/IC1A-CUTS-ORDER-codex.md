# IC1A-CUTS-ORDER codex consult
TASK_ID: IC1A-CUTS-ORDER
HEAD: 1f8749a
MODE: read-only consult; production code/tests unchanged.

## A. 現況偵察
- Receipt commands: `sed -n`/`nl -ba` on target files; `rg -n "1-align|FDR|Net IC|factor_attribution|HAC|bootstrap|空圖|grouped_ic|adjust_multiple_comparisons|validate_alignment|compute_grouped_ic"` across docs, momentum, api, frontend.
- 1-align: still needed. `momentum/core/contracts.py:745-766` has `AlignmentSpec`, but `validate_alignment(...)` raises `NotImplementedError("1-align 落地")`; grep shows tests only assert signature/NotImplemented (`tests/momentum/core/test_alignment_contract.py:24-34`). No main path import/call in `ic_filter_orchestrator.py:31-38`.
- 1b FDR: still needed, but kernel exists. `statistical_validator.py:58-70` implements `adjust_multiple_comparisons`; `_stage5_statistical_validation` builds raw `ic_stats` then `_apply_thresholds` (`ic_filter_orchestrator.py:1951-1979`), and `_apply_thresholds` compares `row["p_value"]` directly (`:2287-2290`). Frontend exposes `fdr_correction` (`FeatureTierPanel.tsx:38`, store advanced preset `icAnalysisStore.ts:130`) but `getEffectiveConfig` never sends it (`icAnalysisStore.ts:300-311`), and backend maps no such key (`ic_filter_orchestrator.py:47-58,69-75,2586-2628`).
- 1c Net IC: still needed. `net_ic_analyzer.py:25-42` computes `net_ic = gross_ic - (cost_bps/10000)*turnover*2`, i.e. subtracts return-cost units from correlation; `_run_net_ic` feeds only `ic_mean` + turnover (`ic_filter_orchestrator.py:1524-1538`). Frontend chart consumes this as Net IC (`NetICChart.tsx:15-27,51-63`).
- 1d factor_attribution: still needed. Real OLS exists in `factor_exposure_analyzer.py:104-148`, but orchestrator `_run_factor_exposure` does not call it; it returns exposure proxy as `factor_betas` and NaN alpha/r_squared/unexplained (`ic_filter_orchestrator.py:1448-1501`). Frontend type/chart accepts/display proxy fallback (`types.ts:2370-2382`, `FactorExposureRadar.tsx:12-18`).
- 1e HAC/block bootstrap: still needed. Current stats use one-sample t-test and ordinary CI (`statistical_validator.py:95-138`); no HAC/Newey-West call in main IC validator. Existing `bootstrap_estimator.py` is generic bootstrap, not wired into IC p-value path. IC autocorr is computed (`ic_filter_orchestrator.py:1879-1881`) but not used to correct significance.
- 1f 靜默空圖/schema flatten: partially still needed. Reporter emits legacy flat fields only (`ic_reporter.py:36-54`); frontend has empty states for grouped/net/factor charts (`GroupedICBarChart.tsx:85-88`, `NetICChart.tsx:51-52`, `FactorExposureRadar.tsx:37-39`) but no module status for base grouped/FDR empty output in `ICReport` except deep module fields (`types.ts:2091-2126`). Not a stats kernel, but schema/status/UX wiring remains.
- grouped_ic 止血: not complete. Phase 0 fixed pydantic caller by passing `.model_dump()` (`ic_filter_orchestrator.py:1911-1918`) and fail-closed by_volatility (`ic_engine.py:394-397`, schema default false `ic_config_schema.py:76-98`). Still only runs when raw kline exists and regime report enabled (`ic_filter_orchestrator.py:1887-1918`), cross_sectional report always sets `{}` (`:930-934`), frontend coerces unsupported nested/missing values to 0 (`GroupedICBarChart.tsx:45-55`, `RegimeRadarChart.tsx:15-24`). Keep as stop-bleed/schema task, not remove.

## B. 施工順序提案
1. 1-align — 大: Feature_t vs Target_t+lag 是所有 IC/p-value/FDR/OOS 的基礎；先做硬閘與 consumer-map/red-on-break，否則後面統計可能全建在錯位資料上。
2. 合併 1e HAC/block bootstrap + 1b FDR — 大: FDR 消費 p-value，HAC/bootstrap 生產可信 p-value；分開做會先接一輪不可信 raw t-test 後返工。先落 corrected p-value/SelectionScope/report 欄位，再讓 selection 主流程消費。
3. 1c Net IC — 大: 目前公式量綱錯；依賴已可信的 IC/turnover/autocorr 統計，需明確 Grinold/成本折價輸出 schema 與前端語意。
4. 1d factor_attribution — 大: 有 OLS helper 但主流程仍是 proxy+NaN；應接真實 attribution 或 UI 正名 proxy，並鎖 NaN policy。
5. grouped_ic 止血 — 中/大: Phase 0 crash 已修但仍有空 `{}`、cross_sectional 不支援、前端 0 填補與缺 module-status；建議和 1f 同一 schema/UX 刀處理。
6. 1f 靜默空圖 — 中: 不改核心數值，主要是 report schema flatten/module status/前後端 empty-state 接線；應收尾做，避免前面欄位再變造成返工。

## 清單調整
- 可移除: 無。cut1/cut2/Phase0 只修了 split/cross_sectional 標籤/部分 grouped crash，未完成以上刀。
- 建議合併: `1e+1b`；`grouped_ic 止血+1f`。
- 核心排序邏輯: 先修資料時間對齊，再修 p-value 生產與多重比較消費，再修解讀層數值公式，最後做歸因與報表/前端狀態；依賴順序可降低統計重做與 schema 返工。

ASSUMPTIONS_VERIFIED: HEAD=1f8749a; all above judgments backed by rg/nl reads listed in receipts.
TESTS_RUN: none; read-only consultation, no code/test changes requested.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; only this output file added.
NUMERIC_OR_SCHEMA_IMPACT: none from this consult; proposed future work may affect report schema/metrics.
STATUS: DONE
