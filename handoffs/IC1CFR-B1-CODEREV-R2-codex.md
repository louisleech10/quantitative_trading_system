# IC1CFR-B1 Code Review R2 — Codex
task-id: IC1CFR-B1 | reviewer: Codex | date: 2026-07-15 | scope: 6B rework delta；唯讀，僅本檔產出

## 逐項複驗
1. **CLOSED（指定 cache-hit）**：legacy `completed_count=2` 命中無 force cache 後，FR=`unavailable`、summary=`unavailable`、completed=1（僅 trend）；具名測實際命中 `Deep analysis cache hit`。
2. **CLOSED**：重跑 `save_report` 注入 `0.42`，落檔 `SAVE_REPORT_REPLAY False`；全樹 FR 僅 §U union，summary unavailable、completed=0。
3. **CLOSED**：`module_statuses[{module_name:"factor_returns",status:"completed"}]` 轉 unavailable，`deep_analysis_summary.completed` 2→1；phase26 矛盾斷言已改 completed==1 並驗 FR status unavailable。
4. **CLOSED**：before/after-default 原始 compare=0 diff；將既有非 FR 葉 `report.results.factor_centrality.features.close_sma_ratio_20.centrality` 0.141674…→1.141674…，gate 回精確 `~ path` diff。
5. **CLOSED**：alias `FactorReturnAnalyzer as FRA; FRA({})` 得 AST hit `(2,2)`；同 allowlisted `factories.py:454` 第二 ctor 得 `#occ2` extra，兩者皆紅。
6. **STILL-OPEN（部分閉合）**：清空 `_SUMMARY_NULL_KEYS` 會留下三個有限值並紅；通用 oracle 對 `factor_returns.size=1` 會 raise，AI mutation 亦紅；但 Markdown 測試把遞迴 oracle 跑在重新 sanitize 的輸入，不是實際輸出。monkeypatch reporter 恢復 `{"factor_returns":{"size":1}}` 後，現有 Markdown 兩個斷言仍全過，實際輸出含 `- factor_returns: {'size': 1}`。

## 新 BLOCKING
- **B-R2-1 cache force-merge 漏 sanitizer**（`ic_filter_orchestrator.py:1640-1642,1726-1727`）：cache 已存在且 `force_modules=["trend_analysis"]` 時走 merge 非早退；注入 legacy FR 後實跑回 `CACHE_FORCE_MERGE_LEAK {'long_short_mean_return':0.42} completed 2`。這仍是 cache 來源的 public `run_deep_analysis` 有限 FR 洩漏；需在 merge/最終 return 前統一 sanitize，並加 force-cache 反例。
- **B-R2-2 Markdown mutation oracle 假綠**（`tests/api/test_ic_deep_analysis.py:868-889`）：需對實際 Markdown 產物建立可判有限 FR metadata 的 oracle，且 monkeypatch `_build_module_summaries` 恢復 `size:1` 時該具名測必紅；目前獨立 M2c 只證 helper，未證 Markdown wiring。

ASSUMPTIONS_VERIFIED: SPEC/TODO 三家 APPROVED；重算 hash=66db1109…8777/7bf42307…e8bd；未動 analyzer/monotonicity/net_ic/long_short/data_cache。
TESTS_RUN: 6B 精準 nodeids `pytest ...`→8 passed；`pytest tests/api/test_ic_deep_analysis.py -k sanitizer -q`→11 passed；受審檔 `git diff --check`→PASS；另跑 save/cache/inject/§G/AST/兩 mutation probes，stdout 如上。
FAILURES_SEEN: 三檔整組 pytest 超過 60 秒無輸出後終止，不用作 verdict 證據；force-cache 與 Markdown mutation 反例均穩定重現。
SCOPE_CHANGES: none；只新增本 review 檔。
NUMERIC_OR_SCHEMA_IMPACT: 已閉合路徑 finite FR→unavailable/null；未閉合 force-cache 仍洩漏有限 0.42 且 completed_count 錯計。
CODE-REVIEW-R2: REJECT(2 BLOCKING)
