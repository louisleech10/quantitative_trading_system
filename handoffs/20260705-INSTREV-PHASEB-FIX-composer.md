# INSTREV Phase B — Codex CR fixes (Composer)

## 修法摘要

- **REVIEW-1** `scripts/git_hooks/pre-commit`：binary-safe transformer（`git cat-file blob` + `sys.stdin.buffer.read()` strict UTF-8 decode；`UnicodeDecodeError` → exit 2 skip、不改 index）；拆 temp blob/out 避免 pipeline 掩蓋失敗；加 `set -o pipefail`。
- **REVIEW-2** 同上：從 `git ls-files -s` 讀 mode，`update-index --cacheinfo "$mode"` 保留 100755。
- **REVIEW-3** `test_dispatch_explicit_task_id_not_overridden`：隔離 `GATE_DIR_OVERRIDE` 解析 audit JSON，強斷言 `task_id=="20990101-explicit-id"` 且無 `^\d{8}-x$` 自動 id；移除 `returncode in (0,1)` 放行。

## 新增測試

- `test_precommit_skips_non_utf8_staged_md_index_unchanged` — hex `616263ff2020200a` index byte-for-byte 不變
- `test_precommit_preserves_executable_mode_on_autofix` — 100755 保留

## Tests Run

```bash
source venv/bin/activate && pytest tests/governance/test_precommit_autofix.py tests/governance/test_dispatch_wrapper.py -v --tb=short
# 13 passed in 2.26s

source venv/bin/activate && pytest tests/governance/ -q
# 139 passed, 9 failed in 25.03s
```

**FAILURES（pre-existing，非本次引入）**：`test_verify_gate_b4`×3、`test_verify_gate_b5`×5、`test_verify_gate_redteam::test_r7_gate_task_id_appends_committee_dispatch`×1 — 皆 RISK-HIT / adversarial Verdict 類；`git diff -- tests/governance/test_verify_gate*.py` 為空。

## ASSUMPTIONS_VERIFIED

- 非 UTF-8 staged md 觸發 Python exit 2 時 shell 不 `update-index`（實測 `docs/bad.md` before==after）
- executable md auto-fix 後 `git ls-files -s` mode 仍 100755
- explicit `--task-id`（不帶 `--output` 避 bash3.2 空 `final_args[@]` bug）audit 寫入 `20990101-explicit-id` 非 `{date}-x`

## SCOPE_CHANGES

none（僅允許檔）

## NUMERIC_OR_SCHEMA_IMPACT

none

STATUS: DONE
