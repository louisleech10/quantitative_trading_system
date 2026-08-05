# GOVB0-R7-STAMP
family: codex
task-id: GOVB0-R7-STAMP
verdict: APPROVED；H-1/H-2 群集與處置忠實反映四條 R7 findings，可進 TODO 生成。
SCOPE: 僅於 `handoffs/reconcile/20260805-govb0-spec-r7/synth.md` 的 `## 戳記` 區段追加 codex stamp；未改 SPEC、附錄或根 HANDOFF。
DIFF: `@@ synth.md:83`；`## 戳記` 後新增 `RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP`。
ID_MAPPING: `rg -n '^\\| H-[12]|^## (CODEX|COMPOSER)-R7' handoffs/reconcile/20260805-govb0-spec-r7/synth.md` 對照附錄：H-1=`CODEX-R7-P1-01`+`COMPOSER-R7-P2-01`，H-2=`CODEX-R7-P1-02`+`COMPOSER-R7-P2-02`，逐字正確。
ALLOWLIST_ATTACK: `bash -c` heredoc probes；`~ { } [ ] ! * ?` 各 stdout=`VALUE`、`AFTER`，各 rc=0；未加引號 `#` stdout syntax error、rc=2；quoted `#` 與 `EOF#1` 各 stdout=`VALUE`、`AFTER`，rc=0。
ALLOWLIST_RESULT: ⑥(c) 八字元在 delimiter word 不做 tilde/brace/glob/history 展開，加入不引入 fail-open；`#` 保留未加引號 BLOCK 是保守正確，quoted/內嵌合法形仍由其他路徑或 residual 處理。
RESIDUAL_RESULT: H-1 未列 grammar 字元只進⑦ BLOCK，方向為過擋；H-2 crash 留 reclaim lock 後下一次 mkdir EEXIST 拒絕，只有單一 `<out>` 可用性鎖死，不會雙 CLI，兩者皆 named-residual、非 deliverable-invalidating。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` stdout=`RECONCILE-STAMP PASS: handoffs/reconcile/20260805-govb0-spec-r7/synth.md 已獲 codex,composer,grok 全數 APPROVED 且本體雜湊相符(sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd)。`；下一行 stdout=`  使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。`；rc=0。
TESTS_RUN: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r7/sources.lock` stdout 三行=`COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r7/sources/20260805-govb0-spec-r7-codex.md — 2/2 個 ID 全在綜合檔。`、`COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r7/sources/20260805-govb0-spec-r7-composer.md — 2/2 個 ID 全在綜合檔。`、`COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。`；rc=0。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` stdout=`TEMPLATE PASS (spec): docs/GOVB0_FRICTION_SPEC.md 含全部必填錨點，且無明顯空殼。`；rc=0。
FAILURES_SEEN: `#` 未加引號 rc=2 是預期 shell syntax error；最後複合唯讀確認被既有 PreToolUse OPEN-debt gate 攔截，非三支驗收器失敗。
SCOPE_CHANGES: none；tracked worktree 既有修改未觸碰；R7 synth 為 `.git/info/exclude` 忽略產物，故 git diff 不顯示。
NUMERIC_OR_SCHEMA_IMPACT: none；synth 本體 hash 維持 b502bac...fa4bd，僅 stamp 區段變更。
TMP_CLEANUP: `/tmp`（即 `/private/tmp`）inventory 無任何 entry，故無可刪 workdir；`claude-501` 保留條件未受影響。
HANDOFF_OUTPUT: handoffs/20260805-govb0-r7-stamp-codex.md
