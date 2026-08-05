# GOVB0-R4-STAMP — codex
TASK_ID: GOVB0-R4-STAMP; family: codex
STAMP: RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP
DIFF: +RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP
CONCURRENT_SYNC: 驗證期間 composer/grok 戳記亦出現在同一 ## 戳記 區；非本 codex patch，未改其內容。
FINDING_CLUSTER_CHECK: G-1=CODEX-R4-P0-01+COMPOSER-R4-P1-03；G-2=CODEX-R4-P0-02+COMPOSER-R4-P2-02；G-3=CODEX-R4-P2-01；G-4=COMPOSER-R4-P1-01；G-5=COMPOSER-R4-P1-02；G-6=COMPOSER-R4-P2-01；8/8、語意與處置一致。
MODIFICATION_1: EXEMPT_RE 僅接受 typo/doc-example/migration-note/template-drift/tooling-blocked/spec-ambiguity；doc-summary 無效，移除後無合法豁免掩飾。
MODIFICATION_2: G-3/G-4 receipt 可機驗；G-1/G-2/G-5/G-6 明列 R5 逐條複核，責任落在既定 R5 確認輪，不是自證或豁免。
MODIFICATION_3: 現行群集定位用 Task；`:237`/`:398` 等只在歷史說明或 byte-faithful 附錄，無其他 active 行號/檔案大小/未鎖定計數。
E_SCOPE: 截斷 oracle、B-34 語意閉合、B-24 機械強制面、B-15 FP-2 維持 OUT-OF-SCOPE；B-36 ID 錯位保留為具名殘留。
R5_DECISION: (a) 有必要；R4 仍有 2 個新 P0 機制缺口，且四項待驗狀態需在 R5 確認，不重開已裁決事項。
ASSUMPTIONS_VERIFIED: body hash=ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa；SPEC FACT-RECEIPT=10；Task=11；TODO 尚不存在且 SPEC 標為待生成。
TESTS_RUN: bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md
STDOUT: RECONCILE-STAMP PASS: handoffs/reconcile/20260805-govb0-spec-r4/synth.md 已獲 codex,composer,grok 全數 APPROVED 且本體雜湊相符(sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa)。
STDOUT: 使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。
RC: 0
TESTS_RUN: bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock
STDOUT: COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-codex.md — 3/3 個 ID 全在綜合檔。
STDOUT: COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-composer.md — 5/5 個 ID 全在綜合檔。
STDOUT: COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
RC: 0
TESTS_RUN: python3 scripts/verification_claim_check.py --files handoffs/reconcile/20260805-govb0-spec-r4/synth.md
STDOUT: <empty>
RC: 0
TMP_CLEANUP: /tmp/workdir 不存在，無需刪除；/tmp/claude-501 存在並保留。
FAILURES_SEEN: 初次 stamps_check 缺三家戳記 rc=1；後續協作同步後重跑 rc=0；completeness/claims 均 rc=0。
SCOPE_CHANGES: none；未 commit、未 push、未改 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT: handoffs/20260805-govb0-r4-stamp-codex.md
STATUS: DONE
