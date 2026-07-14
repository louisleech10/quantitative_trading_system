# IC1C-FR-STOPGAP SPEC r2 adversarial review — codex (2026-07-14)
範圍：唯讀重跑 r1 6B、掃 r2 新洞、核對 RECONCILE S-F1~S-F8；裁決 REJECT。

| r1 finding | 判定 | 反例重跑結果 |
|---|---|---|
| CX-1 預設/tier 繞道 | CLOSED | §A/Task 1.1 已列 schema、YAML、API model、store 三處與 tier 排除；M1b 覆蓋 override/force/tier。 |
| CX-2 EquityCurve 獨立同病 | CLOSED | Task 2.2 獨立下架；現碼仍證實 producer `monotonicity_tester.py:43-55` 丟 timestamp、chart `:79,92-110,143-155` 按位置相減。 |
| CX-3 legacy/export 漏網 | CLOSED | Task 1.2 指定單一 boundary sanitizer，明列 API/JSON/CSV/AI/Markdown/export_all/serialization/cache hit，finite legacy payload 為 oracle。 |
| CX-4 佔位形狀未定 | CLOSED | §C 精確定案 `{status:"unavailable",value:null,reason}`，TS 同構，module_summary=`unavailable`。 |
| CX-5 golden/mutation 假綠 | CLOSED | §G 改逐 path exact compare+排除欄；M1/M1b/M2 分離 runner、繞道、finite legacy sanitizer mutant。 |
| CX-6 factory/script 旁路 | CLOSED | Task 1.3 保留 factory 但加 caller gate，已具體處置現存 `scripts/phase29_perf_validation_tmp.py:30` 直接 class consumer。 |

- **R2-CX-1｜BLOCKING｜預設關閉與 unavailable 契約互斥。** Task 1.1 要四處 default false；現 `run_deep_analysis` 在 `_is_module_enabled=False` 時於 `ic_filter_orchestrator.py:1651-1657` 根本不加入 runner，`:1694-1696` 只補 `module_summary="not_run"`，不產生 `results.factor_returns`。但 §C 要 `module_summary.factor_returns="unavailable"`、§G(2) 要 `factor_returns` 節等於佔位；Task 1.2 邊界又明定 payload 缺鍵「不注入」。反例：default request、不 force、不 override → runner 未執行、sanitizer 不注入，得到 missing+not_run，仍可同時違反 §C/§G 而 Task 1.1/1.2 測試各自通過。r3 須二選一並同步 oracle：A) disabled 也在 orchestrator 明建 unavailable 結果+summary；或 B) default-off 契約定為 missing+not_run，僅顯式 enable/force 才為佔位，並改 §C/§G/測試。
- **CX-7 NON-BLOCKING 維持。** `long_short_analyzer.py:33-36,63-76` index-align 且分側計算，無錯位位置相減；§N 出 scope 合理。
- **RECONCILE 曲解檢查：無。** S-F2 明載推翻「非消費者→出 scope」的理由，且 r2 沒把 EquityCurve 誤稱 factor-return consumer，而是依獨立 producer/chart 證據另設 Task 2.2；S-F1~S-F8 其餘落點與原 findings 相符。

ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF.md/CLAUDE.md/SPEC r2/r1 codex/RECONCILE；逐碼核對 config、runner selection/cache、reporter/export、兩張 chart、producer、caller/test 詞掃；RECONCILE 存在精確 `## 戳記` 區段。
TESTS_RUN: `nl/sed` 核對上述檔案行；`rg -n` 掃 factor_return/quantile_returns/cumulative_returns/callers/tests；`test -f tests/fixtures/ic_api_real_kline.py`→present；review-only，未跑未實作 pytest/vitest。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本審查檔，REJECT 故未追加 RECONCILE-STAMP。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改數值/schema；R2-CX-1 要求釐清 missing+not_run 與 unavailable union 的唯一對外契約。
SPEC-REVIEW-R2: REJECT(1 BLOCKING)
