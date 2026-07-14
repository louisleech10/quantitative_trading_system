# IC1CFR-STOPGAP r4 Codex review
task-id: IC1CFR-STOPGAP
正在做: r4 SPEC 閉合審查；因必要 TODO 缺失而停止正式技術簽核。
待辦: 補齊 `docs/IC1CFR_STOPGAP_TODO.md` 後重派 r4 review，逐條核 CX-1～CX-4 並掃新洞。
阻塞: `docs/IC1CFR_STOPGAP_TODO.md` 不存在；SPEC:3 明載該對應 TODO，AGENTS.md 執行合約要求開工前必讀 SPEC 與其 TODO，任一讀不到即 BLOCKED。
本次決策: 未 append RECONCILE-STAMP；缺必要審查輸入時不以 SPEC 自述或 RECONCILE 摘要代替 TODO。
踩坑提醒: 本輪已讀 HANDOFF.md、CLAUDE.md、SPEC r4、RECONCILE 與 orchestrator:1570-1725/3310-3390；這些只證明控制流可供後續複核，不解除 TODO 前置缺失。
ASSUMPTIONS_VERIFIED: `rg --files docs handoffs | rg 'IC1CFR|STOPGAP|ic1cfr|stopgap'` 僅列 SPEC/RECONCILE/reviews，無 TODO；`sed -n '1,420p' docs/IC1CFR_STOPGAP_TODO.md` 回報 No such file or directory。
TESTS_RUN: 唯讀文件/原碼檢查；未跑測試（SPEC review，且前置 BLOCKED）。
FAILURES_SEEN: 必要 TODO 缺失。
SCOPE_CHANGES: none；僅新增本交接檔，未改 RECONCILE。
NUMERIC_OR_SCHEMA_IMPACT: none。
SPEC-REVIEW-R4: REJECT(1 BLOCKING)
