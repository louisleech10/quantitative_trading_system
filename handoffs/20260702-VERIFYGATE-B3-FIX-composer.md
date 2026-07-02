# VERIFYGATE B3 — 四 BLOCKING 修補（Composer）

**Date**: 2026-07-02  
**Scope**: Codex review `20260702-VERIFYGATE-B3-REVIEW-CODEX.md` 四 BLOCKING + NB-1

## Finding → 修法

### B3-1 partial-stage 繞過
- **改動**: `scripts/verification_claim_check.py`
  - `--staged` 改讀 index blob（`git diff --cached --name-only --diff-filter=ACMR -z` + `git show :<path>`），不再 `path.read_text()` working tree。
  - 新增 `_git_staged_scannable_paths` / `_git_staged_blob` / `content_map` 供 `check_files()` 使用。
- **新測**: `test_git_hook_rejects_partial_stage_fake_claim`

### B3-2 code-only commit 假紅
- **改動**: `scripts/verification_claim_check.py`
  - 僅 `--staged` 且無 scannable staged path 時 exit 0（一般 CLI 無 input 仍 exit 2）。
- **新測**: `test_git_hook_allows_code_only_commit`

### B3-3 health / preflight 交付狀態
- **改動**: `scripts/verify_hooks_health.sh`
  - hooks 未安裝 → `HEALTH WARN` + setup 指引 + exit 0（明示殘餘風險）。
  - hooks 已安裝但缺件/被掏空 → `HEALTH FAIL` exit 1。
  - `py_compile` 改 `ast.parse`（不寫 pyc）。
- **測試**: 原 `test_health_fails_without_hooks_path` 改為 `test_health_warns_without_hooks_installed`；新增 `test_preflight_usable_without_hooks_installed`；`test_mutation_removed_precommit_checker_fails_health` 仍驗已安裝但壞 → FAIL。

### B3-4 CI binary / non-UTF crash
- **改動**:
  - `.github/workflows/verify_claim.yml`：`CHANGED` 只取 scannable markdown pathspec；空 CHANGED 不傳 `--files`。
  - `scripts/verification_claim_check.py`：`--files` 過 `_is_scannable_path()`；non-UTF 回 exit 2 可診斷訊息（`FileReadError`）；`_is_scannable_path` / `_scannable_rel_path` 支援絕對路徑（測試 temp 檔不誤濾）。
- **新測**: `test_verify_claim_workflow_scannable_pathspec_only`、`test_explicit_files_binary_non_utf8_no_crash`、`test_explicit_files_non_scannable_skipped_no_crash`

### NB-1 verify_task_provenance
- **新測**: `test_stamp_task_id_hyphen_not_truncated`、`test_non_allowlist_p0ff3_r2_requires_committee_audit`（邏輯已在 `verify_task_provenance.py`，未改 production code）

## ASSUMPTIONS_VERIFIED
- partial-stage 反例：staged 假 claim + working tree 乾淨 → commit 被拒（temp repo pytest）。
- code-only staged `foo.py` → commit exit 0（temp repo pytest）。
- 真實 repo `core.hooksPath` unset → `agent_preflight.sh` exit 0 且印 `install_verify_hooks.sh`。
- `--files` 帶 non-UTF `docs/*.md` → exit 2、`Traceback` 不在 stderr。
- `task:p0ff3-r2` parse 完整、非 allowlist reconcile 須 committee_dispatch。

## TESTS_RUN
```
pytest tests/governance/ -q
# 75 passed in 13.79s

bash scripts/agent_preflight.sh /tmp/b3-fix-preflight-snap.txt
# exit=0, HEALTH WARN + install 指引

bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
bash scripts/template_check.sh todo docs/VERIFY_GATE_TODO.md
bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md
# ALL PASS
```

## FAILURES_SEEN
- 首輪：`--files` 對絕對路徑誤用 `_is_scannable_path` 導致 B2/B5 回歸 24 fail；修正 `_is_scannable_path`/`_scannable_rel_path` 後全綠。

## SCOPE_CHANGES
- none（僅 FIX-PROMPT 列出的 scripts/workflow/tests）

## NUMERIC_OR_SCHEMA_IMPACT
- none

STATUS: DONE
