# GAP-2 B1 stamp — codex
task-id: 20260818-GAP2-B1-STAMP-R13
判定: BLOCKED
stamp-target: handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md
body_sha256: 78efca544667239988a3baf35b4023d6d71a37092539f625fa2bfef8c1c57619

判準 1: PASS — completeness_check --lock rc=0；11/11 canonical IDs。
判準 2: PASS — git show ede80b42；deepcopy 反例 fresh version=1。
判準 3: PASS — view_status_keys 契約符合；top-level exact test PASS。
判準 4: PASS — constant survivor、budget+removed、constant label 反例均符合 A1-7。
判準 5: BLOCKED — gap2_mutation_probe --batch B1 rc=1；V-6 未轉紅，其餘 9 case RED→GREEN。
判準 6: PASS — point-estimate bootstrap mutant test 確實 RED。
判準 7: PASS（targeted）— reason AST subset test PASS；完整套件後同測試出現順序相關失敗。
判準 8: PASS — TODO top-level allowlist／test_load_top_level_keys_exact PASS；K7 駁回依 A1-7。
判準 9: BLOCKED — exact pytest = 1 failed, 45 passed（reason literal no_survivors）；mutation_probe_check PASS。
判準 10: BLOCKED — git diff 022650ff ede80b42 含 .claude/gate/audit.log、docs/site 及白話檔等允許清單外檔。

ASSUMPTIONS_VERIFIED: body hash、SPEC R7、AMENDMENTS A1-7、TODO FROZEN、上游 RECONCILE-STAMP 均已核對。
TESTS_RUN: reconcile_body_hash rc=0；completeness rc=0；targeted K2/K3/K7 PASS；point mutant RED；probe receipt 20260818T154734Z；two-file pytest rc=1；mutation_probe_check rc=0。
FAILURES_SEEN: 首次 probe 因既有鎖 rc=3；重試後 V-6 未轉紅；post-restore/full two-file pytest 45 passed/1 failed。
SCOPE_CHANGES: 僅 append 目標一行 BLOCKED 與新增本交件檔；未改 code/test/spec/todo/data_cache，未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none。
TMP_CLEANUP: /tmp/workdir 與 /private/tmp/workdir 均不存在；/tmp/claude-501 保留。
HANDOFF_OUTPUT: handoffs/20260818-gap2-b1-stamp-codex.md
STATUS: BLOCKED — V-6 mutation oracle 未轉紅，且判準 9/10 未通過。
