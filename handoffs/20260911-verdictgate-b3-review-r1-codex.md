# VERDICTGATE B3 code review R1 — codex

task-id: 20260911-VERDICTGATE-B3-REVIEW-R1; family: codex; target: B3 implementation at HEAD d6c52c27.

**必答 1（ASSERT 對應）**: 3.1（5）：A1 `test_31_impl_self_b2_prev_blocked_rejected`；A2/A5 `test_31_impl_self_b2_prev_all_proceed_passes`；A3 `test_31_impl_self_family_not_claude_rejected`；A4 `test_31_impl_self_b1_no_prev_issues_token_and_event`。3.2（6）：`test_32_prod_without_trailer_rejected`、`test_32_small_one_file_ok_and_post_commit_event`、`test_32_small_five_files_rejected`、`test_32_batch_trailer_token_absent_rejected`、`test_32_batch_trailer_token_fresh_ok_event_true`、`test_32_docs_only_no_trailer_ok`。3.3（22）：A1 `test_33_three_small_union_five_rejected`；A2 `test_33_two_small_union_three_ok`；A3 `test_33_two_push_window_not_reset`；A4 `test_33_consumed_token_resets_window`；A5 `test_33_docs_only_batch_commit_does_not_consume`；A6/A7/A8/A10/A14/A15/A16/A18/A19/A21 缺 direct test；A9 `test_33_ghost_sha_filtered`；A11 `test_33_no_verify_then_token_not_ratified`；A12 `test_33_unconsumed_token_not_anchor`；A13 `test_33_consumed_token_resets_window`；A17 `test_33_pre_push_stdin_delete_line_skipped_and_ranges_exported`（僅 stub/env）；A20 `test_32_batch_trailer_token_fresh_ok_event_true`。補充驗證 182–184 分別由 `test_33_prod_commit_without_trailer_in_range_rejected`、`test_33_two_small_union_three_ok`、`test_33_pre_push_skip_env_leaves_audit` 涵蓋。

**必答 1（缺者）**: 缺少的 3.3 direct coverage：impl-self helper argv descoping、legacy review+consult、single-anchor token→small×3→batch→small×3、missing-root audit_append、first-push two initial prod commits、fork remote、no-range/no-upstream fail-closed、mixed delete+feature、main/feature checkout reachability、post-commit expired token false。另 3.1 的 A2/A5 共用單一測試，非一 ASSERT 一測試。

**必答 2**: `bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` rc=0；`bash scripts/gov_check.sh --fast` rc=0；`git log -3 --format=%B | git interpret-trailers --parse` rc=0。E-7 範圍與 SPEC/TODO 相同：只保護 `momentum|api|frontend/src`，B3 治理檔同步由既有 Governance-Scope trailer 表示；另見 P1-01 的 production deletion 漏洞。

**必答 3**: macOS 未重導向時 `stat -c` 會印 `illegal option -- c`，但 `_mtime()` 對該 stderr 做了 `2>/dev/null`，再以 `stat -f %m` 成功 fallback；實跑命令 rc=0。

**必答 4**: 實際 `git push origin main` 的 pre-push stdin 是恰好一行：`refs/heads/main <new-sha> refs/heads/main 0000000000000000000000000000000000000000`。`@{u}..HEAD` 僅應是明確零行時的 current-upstream fallback；現行實作把 all-delete 也當零行，見 P1-02。

**必答 5**: `gov_check.sh` 的 no-remote 例外不構成正常 git push integrity bypass：正常 push 會提供 stdin ranges，且無 configured remote 時 `git push origin` 本身不可執行；standalone no-range/no-upstream 仍與 SPEC 的 fail-closed 文字不一致，已列為缺測而非另增 finding。

**必答 6**: `--impl-self` 只新增 parser/精確 `*-impl-b<N>-claude` 驗證；既有 shared quorum/verdict blocks 同時匹配 claude 與 codex，未見 impl-self 專用 bypass。無 `--spec` 時 brief 本來就非必要；有 spec 時仍要求 brief，未發現本輪新增的 gate weakening。

**必答 7**: 不能接受 B3；P1-01、P1-02 尚未關閉，且 P2 contract/test gaps 仍在。

## CODEX-R1-P1-01
**斷言**: production deletion 被 `--diff-filter=ACMR` 排除，commit-msg 與 push-range 都會把 deletion-only production commit 當成無 production change，因而不要求 Ticket-Batch trailer/token。
**碼證**: `scripts/ticket_batch_check.sh:46,89-98`；temp probe 顯示 staged `D momentum/to-delete.py`、ACMR name count=0、`DELETION_MSG_CHECK_RC=0`、`DELETION_PUSH_RANGE_RC=0`。
**來源摘要**: `scripts/ticket_batch_check.sh#cde2cc01a70e`；`scripts/git_hooks/commit-msg#53dc5dcf7c3c`；`scripts/gov_check.sh#971faf4fbdb2`；`docs/VERDICTGATE_SPEC.md#d723f42d7194`。
[MAJOR] 信心度=High；影響：刪除 production code 的後續 commit 可無 trailer 進 remote，B4 亦看不到 production change，audit 無法重建此授權鏈。修復方向：production change detection 必須納入 D（及規範允許的 deletion 狀態），並對 deletion-only commit 執行既有 fail-closed gate。

## CODEX-R1-P1-02
**斷言**: pre-push 未記錄「曾讀到 stdin」與「all-delete」兩種狀態；all-delete 時 `_pp_ranges` 維持空字串，tracked upstream 存在便錯誤 fallback 到 `@{u}..HEAD`，阻擋合法 branch deletion。
**碼證**: `scripts/git_hooks/pre-push:29-39`、`scripts/gov_check.sh:292-300`；實際 `git push -q origin --delete feature` 得 `DELETE_PUSH_RC=1`，stub 收到 `RANGES=@{u}..HEAD LOCALS=<local-sha>`，remote branch 未被刪除。
**來源摘要**: `scripts/git_hooks/pre-push#bd4611c4f30f`；`scripts/gov_check.sh#971faf4fbdb2`；`docs/VERDICTGATE_SPEC.md#d723f42d7194`。
[MAJOR] 信心度=High；影響：B4 cleanup/branch-delete push 在 tracked worktree 且 HEAD 有未推送 commit 時不能完成，且可能被 unrelated current-branch range 阻擋。修復方向：分辨真正零行、all-delete、mixed push；all-delete 直接通過，只有真正零行才使用 upstream fallback。

## CODEX-R1-P2-03
**斷言**: trailer pattern `*/b[0-9]*` 並未要求 `<N>` 全為數字；`ROOT/b2oops` 會被接受，違反 `<root>/b<N>` 精確格式。
**碼證**: `scripts/ticket_batch_check.sh:60-64`；malformed temp probe 建立 `impl.ROOT-b2oops.token`，`Ticket-Batch: ROOT/b2oops` 得 `MALFORMED_TRAILER_RC=0`。
**來源摘要**: `scripts/ticket_batch_check.sh#cde2cc01a70e`；`docs/VERDICTGATE_TODO.md#012a38a2888f`。
[MINOR] 信心度=High；影響：fail-closed trailer contract 有語法漏洞；標準 gate-issued token 不會產生此檔名，未見直接權限提升。修復方向：以 anchored numeric validation 驗證 root 與 batch number，而非 shell glob。

## CODEX-R1-P2-04
**斷言**: Task 3.3 規定的 22 個 fixed ASSERT 並未各自有 direct test；現有 deletion test 只驗 stub 的 env export，未驗實際 gov_check deletion 行為，故測試追蹤性不足。
**碼證**: `docs/VERDICTGATE_SPEC.md:164-180`；`tests/governance/test_verdictgate_p3.py:180-296` 僅有 13 個 3.3 測試；全檔實跑為 29 passed，但缺口包含 A6/A7/A8/A10/A14/A15/A16/A18/A19/A21。
**來源摘要**: `docs/VERDICTGATE_SPEC.md#d723f42d7194`；`tests/governance/test_verdictgate_p3.py#0c4d81cc95ea`。
[MINOR] 信心度=High；影響：多項 B3 safety contract 可能在腳本回歸時保持假綠。修復方向：為列出的每個 ASSERT 增加 direct executable test，並讓 delete/mixed/no-upstream cases 呼叫真實 hook/gov path。

ASSUMPTIONS_VERIFIED: HEAD 與 brief 指定 B3 目標一致；production prefix、ASSERT 編號、hook stdin/fallback、token glob 與 source digests 均以實際檔案/命令核對。
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → collected 29, 29 passed, rc=0；三項必跑治理命令均 rc=0；另完成 actual push/delete/deletion/malformed probes（P1-02/P1-01/P2-03 證據如上）。
FAILURES_SEEN: 必跑測試與治理命令無失敗；targeted probes 重現 P1-01、P1-02、P2-03。
SCOPE_CHANGES: 無；只新增本交接檔，未改 tracked source、tests、HANDOFF.md 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無 production numeric/schema/output change。
OUTPUT_ARTIFACT: `handoffs/20260911-verdictgate-b3-review-r1-codex.md`
TMP_CLEANUP: 已刪除 `/tmp/verdictgate-b3-codex-r1`，並確認 `/tmp/claude-501` 保留。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01, CODEX-R1-P1-02
CLOSED:
STATUS: DONE

<!-- 主委正規化（2026-09-11）：原行「VERDICT: blocked by CODEX-R1-P1-01, CODEX-R1-P1-02; P2 findings remain.」不合 governance_verdicts.json 值集，被 register-output 拒收（audit verdict_rejected）；語意不變，改為三行機械塊後重註冊。 -->
