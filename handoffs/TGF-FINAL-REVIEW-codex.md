# TEMPLATE_GATE_FIX Final Cross-Family Code Review — Codex

task-id: tgf-final-review-codex
reviewer: Codex GPT-5.5
range: `git diff 2447c88..HEAD`
verdict: 需修補

## Findings

ID:(ADV-CODEX-R1) [BLOCKING] RESULT discussion 分流可吞掉後續 operational DONE
- 證據：`scripts/template_check.sh:193` `while IFS= read -r res_line`; `scripts/template_check.sh:194` `claim-context:[[:space:]]*discussion`; `scripts/template_check.sh:198` `if [ "${in_discussion}" -eq 1 ]; then continue`. `tests/gate_fixtures/result_notrun_done_in_discussion.md:13` 只覆蓋 discussion 區內 DONE，未覆蓋 discussion 後再出現 operational DONE。
- 失敗方式：`in_discussion` 一旦變 1 永不退出，`MUTATION_CHECK=NOT_RUN` 的 RESULT 可先放一行 `claim-context: discussion`，再在後面寫 `STATUS: DONE` 或「全綠」，機檢仍 PASS。
- VERIFY: `tmp=$(mktemp); cp tests/gate_fixtures/result_notrun_done_in_discussion.md "$tmp"; printf '\nclaim-context: operational\nSTATUS: DONE\n' >> "$tmp"; bash scripts/template_check.sh result "$tmp"; echo RC:$?; rm -f "$tmp"` → `TEMPLATE PASS ... RC:0`.
- 修法：把 discussion 豁免做成明確區塊邊界（例如遇下一個 `claim-context:`、下一個 heading、或 EOF 才結束），且 `claim-context: operational` 後恢復掃描；新增 fixture 覆蓋 discussion 後的 DONE 必須 FAIL。
- RECHECK: 上述 VERIFY 應改為 `RC:1`，並 `bash scripts/test_template_check.sh` 仍 `MATRIX PASS`。

ID:(ADV-CODEX-R2) [MAJOR] `.claude/gate/audit.log` 進入 diff，違反本 TODO 的不得修改紅線
- 證據：`docs/TEMPLATE_GATE_FIX_TODO.md:9` `任何 Task 不得修改`; `docs/TEMPLATE_GATE_FIX_TODO.md:158` `不得修改 .claude/gate/audit.log`; `git diff --name-status 2447c88..HEAD` 顯示 `M .claude/gate/audit.log`; `git diff 2447c88..HEAD -- .claude/gate/audit.log` 顯示新增 dispatch/provenance/audit 內容。
- 失敗方式：把本地審計流水帳納入 epic diff，會把 runtime trust artifact 當成實作產物；後續 review/commit 可能把環境特定 token/provenance 雜訊一起帶入。
- VERIFY: `git diff --name-status 2447c88..HEAD | grep '.claude/gate/audit.log'` → `M .claude/gate/audit.log`.
- 修法：從本 epic 變更中移除 `.claude/gate/audit.log`，保留為本地 append-only runtime artifact；若確實需要保存 receipt，轉寫到 `handoffs/` 或 `run_receipts/` 的明確報告檔。
- RECHECK: `git diff --name-only 2447c88..HEAD | grep -x '.claude/gate/audit.log'; echo $?` 應為 `1`。

ID:(ADV-CODEX-R3) [MAJOR] 根 `HANDOFF.md` 被納入實作 diff，超出 SPEC/TODO 修改清單
- 證據：`docs/TEMPLATE_GATE_FIX_TODO.md:157` Task 6.2 修改檔案清單只列 `scripts/gate.sh`、`CLAUDE.md`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`scripts/coverage_check.sh`、`templates/RESULT_TEMPLATE.md`、`docs/TEMPLATE_GATE_FIX_GRANDFATHER.md`；`git diff --name-status 2447c88..HEAD` 顯示 `M HANDOFF.md`。
- 失敗方式：根 handoff 是協作索引，不是 TGF 實作產物；把它混入 epic diff 會讓 reviewer/lander 無法區分制度改動與當前任務狀態更新，也違反執行端交接寫 `handoffs/<task>.md` 的契約。
- VERIFY: `git diff 2447c88..HEAD -- HANDOFF.md | sed -n '1,20p'` → 顯示整段 IC/模板審查狀態改寫。
- 修法：從實作分支/PR 中排除根 `HANDOFF.md`，本次 review 結果只保留在 `handoffs/TGF-FINAL-REVIEW-codex.md`。
- RECHECK: `git diff --name-only 2447c88..HEAD | grep -x 'HANDOFF.md'; echo $?` 應為 `1`。

ID:(ADV-CODEX-R4) [MINOR] `git diff --check` 失敗，新增文件含尾隨空白
- 證據：`docs/TEMPLATE_GATE_FIX_GRANDFATHER.md:3`、`:4`；多個 `handoffs/2026-07-04-*` 檔也有 trailing whitespace。
- 失敗方式：不影響 gate 邏輯，但會污染 diff hygiene；若後續 pre-commit 啟用 whitespace check 會擋 commit。
- VERIFY: `git diff --check 2447c88..HEAD` → exit `2`，首項輸出 `docs/TEMPLATE_GATE_FIX_GRANDFATHER.md:3: trailing whitespace.`
- 修法：移除新增/修改檔案的尾隨空白，至少清掉 `docs/`、`scripts/`、`templates/` 與本 epic handoff 中的 trailing whitespace。
- RECHECK: `git diff --check 2447c88..HEAD` 應 exit `0`。

## Verified Passing Checks

- VERIFY: `bash scripts/test_template_check.sh; echo RC:$?` → `MATRIX PASS: 全 13 fixture 與 EXPECTED 一致`, `RC:0`.
- VERIFY: `for id in A-1 A-3 A-4 A-5; do bash scripts/test_template_check.sh --mutate $id; done` → four `MUTATE PASS`, all `RC:0`; follow-up `git diff --exit-code scripts/template_check.sh scripts/test_template_check.sh` → `RC:0`.
- VERIFY: gate fixture commands with `GATE_DIR_OVERRIDE=/tmp/tgf-final-gate*` produced expected exits `1/1/1/1/0`; low-risk smoke produced `RC:0`.
- VERIFY: `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md`, `bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md`, and both `coverage_check.sh` calls all exit `0`.
- VERIFY: docs scan confirms grandfather behavior: old SPECs fail under new rules, TGF SPEC/TODO pass, and `docs/TEMPLATE_GATE_FIX_GRANDFATHER.md` contains `IC_PHASE0_SPEC` plus `僅新文件適用`.
- VERIFY: `grep -n "§1\\.0\\|§1\\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md; echo RC:$?` → `RC:1`; `grep -rn "COVERAGE PASS" scripts/ --include="*.sh"; echo RC:$?` → `RC:1`.

## SPEC/TODO Drift Notes

- No blocking drift found for the main B1/B2/B3/B4 acceptance matrix: fixture count, mutation contract, gate 5-case expectation, template grep assertions, old-anchor removal, and GRANDFATHER policy are implemented and verified.
- The RESULT discussion bypass in ADV-CODEX-R1 is a drift against Task 2.4's intent: `MUTATION_CHECK=NOT_RUN` should forbid operational polarity outside discussion, but current parser has no discussion exit.

ASSUMPTIONS_VERIFIED: diff range inspected; SPEC/TODO/MANIFEST/reconcile read; template_check/gate/test runner executed with positive, negative, mutation, and custom bypass probes.
TESTS_RUN: see Verified Passing Checks plus ADV-CODEX-R1/R2/R3/R4 VERIFY commands; key failing probe is RESULT discussion-after-DONE returning `RC:0`.
FAILURES_SEEN: custom RESULT bypass succeeded unexpectedly; `git diff --check` failed with trailing whitespace; an initial malformed gate loop was rerun with correct arguments.
SCOPE_CHANGES: none by reviewer; observed out-of-scope modified files `.claude/gate/audit.log` and `HANDOFF.md`.
NUMERIC_OR_SCHEMA_IMPACT: none; review covered governance shell/templates/docs only.
STATUS: DONE
