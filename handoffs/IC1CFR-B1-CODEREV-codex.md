# IC1CFR-B1 Code Review — Codex
task-id: IC1CFR-B1 | reviewer: Codex | date: 2026-07-15 | scope: git diff HEAD + B1 RESULT + Frozen Phase 1

## Verdict
REJECT：6 BLOCKING；三態主 runner 正確，但 cache/inject 狀態、完整輸出邊界及驗證守衛未閉合。

## BLOCKING
1. `ic_filter_orchestrator.py:1633-1638` cache-hit 只 sanitize results；`factor_return_sanitizer.py:44-67` 保留 legacy summary=`completed`，completed_count 亦留 1。輸出成 unavailable union + completed，違反 unavailable 不計數；現有 cache 測試刻意注入此狀態卻未驗 summary/count。
2. `ic_reporter.py:425-443` 的 public `save_report()` 仍 raw `json.dump(report)`；production caller=`ic_filter_orchestrator.py:3222`。實跑 direct legacy inject 落檔得到 `SAVE_REPORT_LEAK 0.42`，故「全樹無 finite FR 洩漏」不成立。
3. `ic_reporter.py:767-818` inject 先把 module_summary 轉成 `module_statuses`/completed count，末端 sanitizer 不識別 list entry；`test_ic_reporter_deep_analysis.py:39-47` 甚至在 FR 已 unavailable 後仍斷言 completed==2，留下矛盾 legacy 輸出。
4. `ic1cfr_stopgap_freeze.py:663-773` 的 after 兩模式只驗 FR 狀態並寫 artifact，未實作 SPEC §G 要求的非 FR逐 path exact compare/FAIL path diff。外部 `diff <(jq ...del(.factor_returns))` 本次碰巧無差，但 gate 刪掉非 FR 比對仍會綠。
5. consumer guard 僅 `rg FactorReturnAnalyzer\(`/factory symbol + `path:line` subset (`freeze.py:445-489`,`test_factor_return_stopgap.py:167-202`)；alias `FactorReturnAnalyzer as FRA; FRA(...)` 零命中，同一 allowlisted 行追加第二 ctor 亦集合去重，故「新繞路→紅」不成立。
6. sanitizer 驗證有兩類假綠：legacy fixture 未含三個 summary null keys，將 `_SUMMARY_NULL_KEYS` 清空後 sanitizer suite 仍 9 passed；AI/Markdown oracle 只禁特定字面，恢復 finite `size:1` metadata 後兩測仍 2 passed。M2 只證 detailed CSV local hook，未證這兩項 Frozen property。

## Confirmed / Scope ruling
自構三態 probe：default/pure intermediate/pure advanced/deep-off-force=`not_run`+無節；force/override=`unavailable` union、無 finite、未入 errors。
七個具名掛點現碼皆存在；sanitizer 冪等、results finite 轉 union、module_summary 字串不再觸發 ResponseValidationError；但 B1-1/B1-3 狀態一致性未解。
M1/M1b 真 monkeypatch production runner/tier 並自證紅；M2 有效但覆蓋不足。phase29 已 top-level SystemExit quarantine；`check_decoupling.sh` 全 PASS；momentum 無 import api。
`momentum/factories.py` re-export 裁為可接受：TODO 固定 sanitizer 在 Analysis，API service 直接 import 會違 Rule 3；wrapper 是較小合規面。
§V 7 筆改寫皆有理由且 52-test suite 全綠；RESULT 未逐筆列保留的 analyzer self-test grep hit，屬 nonblocking 治理缺口。另 `.claude/*`、API doc whitespace 等非 B1 dirty diff 不應歸責本批。

ASSUMPTIONS_VERIFIED: 雙 RECONCILE-STAMP APPROVED/hash 相符；B0 frozen allowlist 已讀；未動 analyzer/monotonicity/long_short/net_ic/trend。
TESTS_RUN: targeted 38-suite=37P/1 flaky fail，該 nodeid 單跑=1P；rewrite suite=52P；mutation script=6P；decoupling=PASS；自構三態/allowlist/save_report probes 如上。
FAILURES_SEEN: `test_legacy_request_gross_only` 全組合時背景 task 未 ready 回400，單跑通過；`git diff --check` 另票 API doc trailing whitespace。
SCOPE_CHANGES: factories re-export accepted；其餘髒樹非 B1 內容須隔離 stage；本 review 唯一 workspace 寫入為本檔。
NUMERIC_OR_SCHEMA_IMPACT: runtime intended FR finite→unavailable/null；B1-2 證明 save_report 仍可落有限值，B1-1/B1-3 證明 status/count schema 語意矛盾。
CODE-REVIEW: REJECT(6 BLOCKING)
