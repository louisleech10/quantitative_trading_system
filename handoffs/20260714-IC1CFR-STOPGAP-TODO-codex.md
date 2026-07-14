# IC1CFR-STOPGAP TODO adversarial review — Codex
task-id: `IC1CFR-STOPGAP-TODO:adversarial` | date: 2026-07-14 | basis: SPEC v1.0 Frozen

結論: REJECT。名目 Task 0.1/1.1-1.3/2.1-2.2=6/6，但語意覆蓋與可執行 gate 有 5 個 BLOCKING。

1. **B1 §G before hash 自相矛盾**（TODO:26-28；SPEC:34,37）。TODO 要 dump 全 deep report 且重跑 hash 一致；現碼 `DeepAnalysisReport.total_execution_time_s`（`deep_analysis_types.py:29`）每跑必漂，錯誤另有 timestamp（:17）。SPEC 又明定這些欄只在 path compare 排除。修訂須寫清：before artifact 保留原值但防竄改 hash 只驗同一 bytes，或 hash 前 canonicalize 排除欄；不可要求兩次真跑 raw JSON 同 hash。
2. **B2 Task 1.2 grep 找不全必掛邊界，且 sanitizer 放置檔未定**（TODO:41）。列出的 grep 只掃 service/reporter，卻漏現碼 cache hit `ic_filter_orchestrator.py:1629-1636`；也不命中 raw JSON 出口 `ic_analysis_service.py:437-438`。`export_all` 同樣 raw dump（`ic_reporter.py:334-335`）。修訂須指定單一 sanitizer 的 momentum-side 檔案（避免 momentum import api）及逐掛點清單；cache hit、service serializer、raw JSON、reporter serializer/export_all 各有具名測試。
3. **B3 M3/M4 綁錯**（TODO:67,72；SPEC:75-76）。SPEC M3 是 FactorReturn legacy finite 不得 render；TODO 卻把 `test_mutation_m3_render_legacy` 掛在 FactorEquityCurve，實際是 M4，且追溯表漏 M4。Task 2.1 必有 M3 probe；Task 2.2 應命名 M4 probe；兩者各自基線綠→mutation 紅。
4. **B4 B2 backend gate 無可判定 pass/fail**（TODO:20）。命令跑大集合，文字卻允許「既有紅非本票」，沒有 frozen failure allowlist/baseline diff；exit 非 0 時執行端無法機械判斷是舊紅或回歸。修訂須用 baseline nodeid 集差分且禁止新增失敗，或改成已知可全綠的精準集合；不得靠人工括號豁免。
5. **B5 factory 白名單不可留給執行端自由校準**（TODO:48-50）。實跑 `rg -n "create_factor_return_analyzer" momentum api scripts tests` 現況只有 factory 定義與 `tests/phase26/test_deep_analysis_factories.py` 呼叫；TODO 預期的 analyzer tests/orchestrator runner 皆非 factory caller（後者在 `ic_filter_orchestrator.py:1780-1785` 直接建 class）。允許實作者「據實際 repo 校準」可把新繞路一起白名單。須在 B0 凍結精確 invocation allowlist（definition 不算 caller），並另掃 `FactorReturnAnalyzer` 直接 production consumer；只允許既定 orchestrator、phase24 analyzer tests，tmp script 必 quarantine。

通過項: Task 1.1 已精確指定專屬 except 必在通用 except 前、union/summary/error 行為；現碼計數只計 `completed`/`skipped`（:1698-1703），故 `unavailable` 自然排除，無需發明第三計數。四組測試覆蓋 default、純 tier、force+override、deep-off，且 M1b 可證 tier 排除；建議再 assert default/pure-tier 時 deep 全域確為開，屬加固非 blocking。
通過項: gate 工具/入口離線可解析：`python`/`pytest` 指向 venv，frontend 有 `test=vitest run`、`build=next build`，`bash -n scripts/mutation_probe_check.sh scripts/check_decoupling.sh` exit 0；計畫中 freeze script/stopgap test 尚未建立符合 Task 0.1/1.1 的產物順序。
非阻塞漂移: TODO:72 稱 `long_short_analysis` 已列 §0 不動清單，但 §0 未逐字列出；§G「所有非 factor_returns results exact」仍可守住，建議補名以忠實追溯。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、Frozen SPEC、TODO；reconcile 三家 stamp 實跑通過；上述行號均以現碼 rg/nl 核對。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh ... codex,composer,grok`→PASS sha256 66db1109…；`bash -n ...`→0；`python/pytest/npm/node --version`→可用；未跑會寫 cache/build/receipt 的 suite（唯讀約束）。
FAILURES_SEEN: none
SCOPE_CHANGES: 僅新增本檔；未改 HANDOFF.md、docs、runtime、tests、data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none（文件唯讀審查）。
TODO-REVIEW: REJECT(5 BLOCKING)
