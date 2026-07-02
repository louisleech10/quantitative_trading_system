# VERIFYGATE 過嚴回歸修補 (O1+O2) — Composer

## O1 — pre-commit 只掃 staged 新增行

**根因**：`--staged` 用 `git show :path` 掃整檔 index blob，未改動的歷史 operational 行每次 commit 都被重掃。

**修法**（`scripts/verification_claim_check.py`）：
- 新增 `_git_staged_added_line_numbers()`：以 `git diff --cached -U0` 解析 `+` 行 1-based 行號。
- `_git_staged_markdown_files()` 回傳 `(paths, content_map, added_lines_map)`。
- `check_files()` / `_scan_file_content()` 支援 `added_lines_map`；`--staged` 僅對 `_unit_touches_added_lines()` 為真的 unit 跑 `check_unit`；內容仍讀 index blob（B3-1 partial-stage 不回歸）。
- 刪除/context 行不掃。

**新測試**（`tests/governance/test_verify_gate_overstrict.py`）：
- `test_o1_staged_unchanged_history_line_not_rescanned`
- `test_o1_staged_new_unbacked_operational_blocked`
- `test_o1_staged_partial_stage_fake_claim_still_blocked`

**反例關閉**：temp repo 先 commit 含 `- align 已驗真紅` 的 HANDOFF（無 hook），裝 hook 後只 staged 新增 innocuous 行 → `git commit` rc=0；本次新增假 claim / partial-stage 仍 rc≠0。

## O2 — REF 收檔案路徑

**根因**：`VERIFY_RE` 無 `/`，`REF:handoffs/x.md` 只截到 `handoffs` → 誤判 receipt 不存在。

**修法**：
- `VERIFY_RE` 改為 `([A-Za-z0-9_.\-:]+(?:/[\w./\-]+)?)`，可捕獲 `handoffs/…md` / `docs/…md`。
- 新增 `_file_content_has_backing()`、`_is_ref_file_path()`；`check_backing()` 對路徑型 REF 檢查檔案存在 + 內容含 VERIFY/SIGNOFF/RECONCILE-STAMP 或 `CLOSED`/`APPROVED`（與 R6 歸屬機制對齊）；receipt id 路徑不變。
- `_attributed_file_has_backing()` 改用 `_file_content_has_backing()`。

**新測試**：
- `test_o2_ref_existing_closure_file_allowed`
- `test_o2_ref_missing_file_blocked`
- `test_o2_ref_empty_file_no_backing_blocked`
- `test_o2_r6_fake_attribution_without_ref_still_blocked`

**反例關閉**：`REF:handoffs/20260702-VERIFYGATE-REDTEAM-CLOSURE-CODEX.md`（含 CLOSED）→ rc=0；不存在/空檔 → rc=1；R6 無 REF 假歸屬仍 rc=1。

ASSUMPTIONS_VERIFIED: `git diff --cached -U0` 在 temp repo 與真實 repo 皆能正確給新增行號；closure 檔 `VERDICT: R1-R7 CLOSED` 觸發 `_file_content_has_backing`；argparse 多檔須單一 `--files a b` 非重複 flag。
TESTS_RUN: `pytest tests/governance/test_verify_gate_overstrict.py -q` → 7 passed; `pytest tests/governance/ -q` → 95 passed
FAILURES_SEEN: `test_o2_ref_empty_file_no_backing_blocked` 初版用重複 `--files` 只掃到第二檔（argparse 行為）→ 改單一 `--files HANDOFF.md handoffs/…` 後通過
SCOPE_CHANGES: none（僅 `scripts/verification_claim_check.py` + `tests/governance/test_verify_gate_overstrict.py`）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
