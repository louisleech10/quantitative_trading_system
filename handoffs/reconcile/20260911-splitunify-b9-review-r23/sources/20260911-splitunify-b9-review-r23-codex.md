## CODEX-R23-P1-01
**斷言**: 前置 reconcile 閘未通過；依 Rule 12 本輪不得重簽 SPEC 或進入下游實作。
**碼證**: `reconcile_stamps_check` 實跑 rc=1：codex 最新戳記宣稱 sha256:76006a…，實際 body 為 sha256:1b0890…；composer/grok R23 provenance 仍 pending。
CODE-ANCHOR: scripts/reconcile_stamps_check.sh:126
MUTATION: 在未修正 hash/provenance 下啟動下游實作，會把未全數核可的 reconcile 傳入執行流程。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d3a633424b03; scripts/reconcile_stamps_check.sh#df3a5bd20c1d
**必要性**: P1；未核可狀態是執行合約的硬阻塞，不可自行繞過。
ROUND_STATUS: R22 三項不能標記 CLOSED；本輪 diff、反例與新 finding 未在閘未通過時正式裁定。
STAMP: 未追加 R23 codex 戳記；SPEC 與程式碼均未修改。
ANSWER_1: 1a blocked；1b 未執行，避免在未核可 reconcile 上做 review 結論。
ANSWER_2: SU-RESID-2 blockers 未重判；不宣稱僅 9.2b／9.3 或其他數量。
ANSWER_3: Task 9.2b 三分支一致性未正式重驗。
ANSWER_4: Task 2.3 單 TF golden 條件未正式重判。
ANSWER_5: 5a／5b 不作 finding 結論；因此不寫 0-finding sentinel。
ANSWER_6: 不進 B9C；待 reconcile 全數 APPROVED 且 provenance 可驗後重開本輪。
ASSUMPTIONS_VERIFIED: body hash=1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7；SPEC/TODO doc_format_precheck 均 rc=0。
TESTS_RUN: bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md；rc=1（codex hash mismatch，composer/grok provenance pending）。
FAILURES_SEEN: reconcile precondition gate failed；未執行回歸測試或 mutation。
SCOPE_CHANGES: 僅新增本交接檔；未改 SPEC 正文、TODO、程式碼、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none。
TMP_CLEANUP: /tmp 為空，無 workdir 或 claude-501 目標可清理；未刪除任何項目。
VERDICT: blocked
BLOCKED-BY: CODEX-R23-P1-01
CLOSED:
STATUS: BLOCKED — reconcile 未全數 APPROVED（codex body hash mismatch；composer/grok provenance pending）
