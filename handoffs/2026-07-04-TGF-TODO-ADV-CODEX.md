# TEMPLATE_GATE_FIX TODO adversarial review — Codex

SPEC_FILE=docs/TEMPLATE_GATE_FIX_SPEC.md
TODO_FILE=docs/TEMPLATE_GATE_FIX_TODO.md
PLAN_FILE=handoffs/2026-07-04-template-review-RECONCILE.md
REVIEW_FOCUS=完整審查，重點=SPEC↔TODO 交叉一致性+TODO 可執行性
起始 ID：ADV-CODEX-5

## Verdict：需修補後派工

TODO 整體覆蓋 12 Task 與 29 manifest ID，但有 1 個 closure 契約走樣會讓 MAJOR/ID finding 不必 reconcile，另有數個驗收命令不可機械執行或與 SPEC 不一致。這些不應進 Frozen。

## Low-cost VERIFY receipts

VERIFY: `printf 'TODO Task count: '; grep -c '^### Task' docs/TEMPLATE_GATE_FIX_TODO.md; printf 'Appendix ID rows: '; sed -n '/^## 附錄 M/,$p' docs/TEMPLATE_GATE_FIX_TODO.md | grep -c '^| \\[[A-F]-[0-9]\\]'; printf 'Manifest ID rows: '; grep -c '^- \\[[A-F]-[0-9]\\]' docs/TEMPLATE_GATE_FIX_MANIFEST.md`
Output: `TODO Task count: 12` / `Appendix ID rows: 29` / `Manifest ID rows: 29`

VERIFY: `sed -n '/^## 附錄 M/,$p' docs/TEMPLATE_GATE_FIX_TODO.md | grep -o '\\[[A-F]-[0-9]\\]' | sort | uniq -c`
Output: each `[A-1]`..`[F-4]` appears exactly `1`; duplicate check output was empty.

VERIFY: `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo $?` and `bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md; echo $?`
Output: both print `TEMPLATE PASS ...`; both exit `0`.

VERIFY: `nl -ba templates/TODO_GENERATION_PROMPT.md | sed -n '20,24p'; nl -ba docs/TEMPLATE_GATE_FIX_TODO.md | sed -n '1,4p'`
Output: current prompt line 23 says unconditional read of `.github/copilot-instructions.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_GUIDE.md`; TODO line 3 states ARCHITECTURE/DEVELOPMENT_GUIDE were not fully read.

## Findings

[MAJOR] High — ID: ADV-CODEX-5 — Task 6.1 narrows SPEC's reconcile trigger from `BLOCKING OR ID` to `BLOCKING AND ID`.
Evidence: SPEC Task 6.1 says `--adversarial 檔含 [BLOCKING] 或 ID: 格式 finding 時，--reconcile 必填`; TODO Task 6.1 says `含 ID: 格式 finding 且含 [BLOCKING] → --reconcile 必填`.
How it fails: an adversarial file with `ID: ADV-CODEX-9` and only MAJOR findings would satisfy the TODO implementation without a reconcile mapping, despite SPEC requiring ID-based closure. This directly weakens the finding closure mechanism from RECONCILE U9.
VERIFY: `grep -n '含 .*BLOCKING.*ID\\|含 .*ID.*BLOCKING\\|--reconcile' docs/TEMPLATE_GATE_FIX_SPEC.md docs/TEMPLATE_GATE_FIX_TODO.md` shows SPEC line 116 uses `或`, TODO line 143 uses `且`.
Fix: change TODO Task 6.1 implementation and verification to match SPEC: any new-format file containing `ID:` requires `--reconcile`; if `[BLOCKING]` is present, absence of reconcile is fail-closed. Define exact expected behavior for ID-only MAJOR/MINOR files.
RECHECK: `grep -n '含 .*ID:.*或\\|含 .*BLOCKING.*或' docs/TEMPLATE_GATE_FIX_TODO.md` and run a gate fixture with `ID:` + `[MAJOR]` + no `--reconcile`; expected exit `1`.

[MAJOR] High — ID: ADV-CODEX-6 — Task 6.1 gate-fixture verification is underspecified and can test the wrong path.
Evidence: SPEC Task 6.1 requires constructing 4 gate fixtures and running `gate.sh dispatch --spec ... --adversarial <fixture> [--reconcile <fixture>]`; TODO Task 6.1 lists only `scripts/gate.sh` as modified file and its final explicit smoke command is low-risk without `--spec`, `--adversarial`, or `--reconcile`.
How it fails: executor can pass the low-risk smoke token flow while never exercising the new adversarial/reconcile parser. Current `gate.sh` already passes that low-risk command without any of the new code paths.
VERIFY: `GATE_DIR_OVERRIDE=/tmp/tgf-gate-review bash scripts/gate.sh dispatch --intent test --risk low --facts-asked none-needed:test --review-role single-executor:n/a --template "n/a:test"; echo $?` prints `GATE PASS` and exit `0`; grep of `scripts/gate.sh` shows current parser has `--adversarial`, `--spec`, `--todo`, `--manifest` but no `--reconcile`.
Fix: Task 6.1 must name fixture paths, e.g. `tests/gate_fixtures/gate_no_verdict.md`, `gate_blocking_no_reconcile.md`, `gate_reconcile_missing_id.md`, `gate_reconcile_complete.md`, plus exact high-risk commands with `GATE_DIR_OVERRIDE=/tmp/...`, `--spec docs/TEMPLATE_GATE_FIX_SPEC.md`, `--todo docs/TEMPLATE_GATE_FIX_TODO.md`, `--manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md`, `--adversarial`, and `--reconcile`.
RECHECK: run the four exact high-risk gate commands and verify exit `1/1/1/0`; separately run the low-risk smoke only as token-flow regression, not as the main acceptance.

[MAJOR] High — ID: ADV-CODEX-7 — Task 3.2 turns SPEC's delta constraint into a wrong absolute line-count threshold.
Evidence: SPEC Task 3.2 verification says `範本總行數增幅 ≤ 12 行`; TODO Task 3.2 verification says `wc -l < templates/SPEC_TEMPLATE.md ≤ 75（現 61＋增幅 ≤ 12＋頭注 1 行）`.
How it fails: current `templates/SPEC_TEMPLATE.md` has 60 lines, so `≤75` allows +15 lines, not +12. The TODO also embeds a false current baseline (`現 61`). Executor could add too much prompt bulk and still pass TODO verification.
VERIFY: `wc -l < templates/SPEC_TEMPLATE.md` outputs `60`; `grep -n '範本總行數\\|wc -l < templates/SPEC_TEMPLATE.md' docs/TEMPLATE_GATE_FIX_SPEC.md docs/TEMPLATE_GATE_FIX_TODO.md` shows SPEC line 91 delta-only and TODO line 113 absolute `≤75`.
Fix: make TODO verification compute before/after or freeze baseline in Task 3.2: `before=$(git show HEAD:templates/SPEC_TEMPLATE.md | wc -l)` or use the known current `60`, then require `after - before <= 12`. Do not hardcode `75`.
RECHECK: `before=60; after=$(wc -l < templates/SPEC_TEMPLATE.md); test $((after-before)) -le 12`.

[MAJOR] Medium — ID: ADV-CODEX-8 — Mutation gates are not directly executable as batch gates.
Evidence: TODO §B says `B2→B3 gate＝bash scripts/test_template_check.sh; echo $? = 0 且 4 條 mutation case 各轉紅`; individual Tasks 2.1-2.4 say "改壞一字元 → 矩陣轉紅" but do not give a command, patch, or mutation runner.
How it fails: a headless executor can honestly run the matrix but skip mutation because there is no reproducible command. Manual source editing for mutation also risks dirtying `scripts/template_check.sh` or being reported as pass without receipt.
VERIFY: `grep -n 'mutation' docs/TEMPLATE_GATE_FIX_TODO.md` shows mutation requirements but no executable command beyond `bash scripts/test_template_check.sh`; no `scripts/test_template_check.sh --mutation` contract is specified.
Fix: either add a `--mutation <case>` mode to `scripts/test_template_check.sh`, or add exact reversible patch snippets/commands for A-1/A-3/A-4/A-5 and require `git diff --exit-code scripts/template_check.sh` after restoring. Record each case in `MUTATION.txt` with command + expected rc.
RECHECK: `grep -n -- '--mutation\\|MUTATION_CASE\\|git diff --exit-code scripts/template_check.sh' docs/TEMPLATE_GATE_FIX_TODO.md`.

[MAJOR] Medium — ID: ADV-CODEX-9 — TODO headnote's constitution-read deviation is disclosed but not formally acceptable under the current generator contract.
Evidence: current `templates/TODO_GENERATION_PROMPT.md` line 23 requires unconditional reading `.github/copilot-instructions.md`, `docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_GUIDE.md`; TODO line 3 explicitly says ARCHITECTURE/DEVELOPMENT_GUIDE were not fully read because this epic intends to institutionalize that behavior later.
How it fails: this bootstraps the future rule before it exists. Even if practically low risk for a governance-only epic, it weakens the current TODO generation contract and gives future authors a pattern for self-waiving "無條件讀" by rationale.
VERIFY: command in receipts above shows the contradiction directly.
Fix: add an explicit reconcile waiver line before Frozen, e.g. `WAIVER: TODO_GEN_STAGE0_DEVIATION approved because scope excludes momentum/api/frontend/data_cache; compensating checks are SPEC §C + TODO §0 + adversarial review`, or regenerate TODO after Task 5.1 lands. Without that waiver, treat as process MAJOR.
RECHECK: `grep -n 'WAIVER: TODO_GEN_STAGE0_DEVIATION\\|ARCHITECTURE/DEVELOPMENT_GUIDE 未全讀' docs/TEMPLATE_GATE_FIX_TODO.md`.

## 被當成事實的未驗證假設

- "B2→B3 gate includes 4 mutation cases" is stated as a batch gate, but no runnable mutation mechanism is specified. This is an assumed executable gate, not a verified one. See ADV-CODEX-8.
- "真 gate 實跑 exit 0" in Task 6.1 is assumed to validate the new reconcile path, but the explicit command is a low-risk smoke that bypasses `--adversarial`/`--reconcile`. See ADV-CODEX-6.
- "TODO generation deviation is acceptable because this epic will institutionalize it" is a process assumption, not yet authorized by the current TODO generation prompt. See ADV-CODEX-9.

## §1 必查 10 類

1. 矛盾/互斥：有。ADV-CODEX-5 and ADV-CODEX-7.
2. 漏項/端到端：有。ADV-CODEX-6; gate fixture paths and high-risk commands are missing.
3. 不可測驗收：有。ADV-CODEX-8 mutation gate is not executable.
4. 可疑 quant 假設：無。本 epic does not touch quant computation.
5. 過度工程：無。Batching is mostly sensible.
6. OOM/並行：無.
7. Cache 正確性：無.
8. API/型別/相容：無 API impact; gate CLI compatibility risk is covered by ADV-CODEX-6.
9. 測試品質：有。ADV-CODEX-6/8.
10. Agent 可執行性：有。ADV-CODEX-6/8/9.

## 附錄 M / 12 Task / 29 ID check

No finding on count or uniqueness: TODO has 12 `### Task`, Appendix M has 29 ID rows, manifest has 29 rows, and Appendix M has no duplicate IDs. The issue is semantic fidelity, not count coverage.

STATUS: DONE
