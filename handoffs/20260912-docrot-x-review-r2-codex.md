# CODEX R2 review
task-id: 20260912-DOCROT-X-REVIEW-R2；scope: brief 指定 current block＋cd3044ff..HEAD diff。
## CODEX-R2-P1-01
**斷言**：Task 1.6 的 HISTORY anchor 判定應只把目標檔真正的歷史段拒收；目前會把 scanner 自身註解的 marker literal 當成 HISTORY，拒收合法 code anchor。
**碼證**：`_validate_anchors` 逐行以 `/HISTORY-BEGIN/`、`/HISTORY-END/` 改變狀態；現行檔註解本身含該字面。
CODE-ANCHOR: scripts/completeness_check.sh:393
MUTATION: 將有效 CODE-ANCHOR 改指 scanner 註解後的現行程式行，再跑 --single；目前由 rc=0 變 rc=1。
**來源摘要**: scripts/completeness_check.sh#76203bf280a43d8e9d1757b3
[BLOCKING] `bash scripts/completeness_check.sh --single scratchpad/docrot-r2-probe/comment_anchor_finding.md --family codex` 實跑 rc=1，報 `scripts/completeness_check.sh:413` 落歷史；同檔第 413 行只是 scanner code，不是 HISTORY。
## CODEX-R2-P1-02
**斷言**：Task 1.6 的 `path:line` 解析不得把 `path:1-3` 靜默截成 `path:1`；否則跨越 HISTORY 的 range 可偽裝成現行 anchor。
**碼證**：`emit_anchors` 的 `[0-9]+` 正則及 `sub(/^.*:/, "", ln)` 只保留 range 起始行。
CODE-ANCHOR: scripts/completeness_check.sh:393
MUTATION: 將有效 anchor 改成跨 HISTORY 的 `hist_sandwich.md:1-3`；目前 `--single` 仍 rc=0，預期應 rc=1。
**來源摘要**: scripts/completeness_check.sh#76203bf280a43d8e9d1757b3
[BLOCKING] `bash scripts/completeness_check.sh --single scratchpad/docrot-r2-probe/range_anchor_finding.md --family codex` 實跑 rc=0；該 probe 的第 1 行在活文、第 3 行在 HISTORY。
TASK_VERDICT: 1.1 interval/no-break PASS；1.2 僅 `_RE_TOTAL_ITEMS` PASS；1.3 gov 1b fail-closed、CLI warn-only PASS；1.4 history interval PASS；1.5 roster/audit commit gate PASS；1.6 token＋forward-only PASS 但有上述兩項 parser 缺口；1.7 沿用 R3 synth 唯一 SSOT 成效句 PASS；1.8 exact-line、fence、blockquote、unclosed fence 測試 PASS。
OUT_OF_SCOPE: 接受 `finding_real_p300.md` 補 token（不改斷言）；接受 held-out mutation 移除 `_validate_anchors` 呼叫（隔離非空判定）；未見其他越界。
MUTATIONS: MUT-OK-1 base `spec_count_audit.py`（break 變異）stderr 空、HEAD 報活文 `1,5`，兩者 rc=0；MUT-OK-2 `test_mut_drop_substantive_check_regresses` rc=0，1 passed，內部確認 base≠0／mutant=0。
ASSUMPTIONS_VERIFIED: 反引號 numeric anchor 可抽取；`:L12` 不抽取而 fail-closed；`:12-15` 會截斷且上述 P1 成立；五種 new_brief kind 的現行 placeholder 集合未見缺行；規定 task-id 形狀可匹配。
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed in 4.39s，rc=0。
FAILURES_SEEN: `scripts/verify_mutation.sh` rc=1，sandbox 禁止 `git worktree add` 寫 `.git/worktrees`；主 repo 未被該 probe 修改。兩個直接 probe 均已另行完成。
SCOPE_CHANGES: none；未修改程式碼、測試、templates 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_PATH: handoffs/20260912-docrot-x-review-r2-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01, CODEX-R2-P1-02
CLOSED:
