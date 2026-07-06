# INSTREV-PHASEB-FIX2 — Composer REVIEW-1 close

## 正在做
- REVIEW-1 已關：`--staged` 非 UTF-8 staged md 改 graceful exit 2

## 本次改動
- `scripts/verification_claim_check.py`：新增 `_run_git_bytes`、`_decode_utf8_blob`；`_git_staged_blob` / `_git_staged_added_line_numbers` 改 binary-safe strict decode；`main --staged` 路徑 catch `FileReadError` → exit 2
- `tests/governance/test_precommit_autofix.py`：新增 `test_staged_non_utf8_md_checker_exit_2_graceful`

## 驗收
```bash
pytest tests/governance/ -q
# 140 passed, 9 failed（皆 pre-existing，非本次引入）
pytest tests/governance/test_precommit_autofix.py -q
# 7 passed
```

## 決策
- staged blob 與 diff 輸出皆走 bytes→strict UTF-8；失敗訊息 `not valid UTF-8 (staged blob)` 與 working tree `FileReadError` 契約對齊

## 踩坑
- 根因是 `_run_git(..., text=True)` 在 subprocess 層 decode，非 Python `read_text` 層

ASSUMPTIONS_VERIFIED: `_git_staged_blob` 用 `text=True` 會在 0xff 等 byte 上 subprocess UnicodeDecodeError traceback（handoffs/20260705-INSTREV-PHASEB-REVIEWCLOSE-codex.md 佐證）
TESTS_RUN: `pytest tests/governance/ -q` → 140 passed, 9 failed (pre-existing); `pytest tests/governance/test_precommit_autofix.py -q` → 7 passed
FAILURES_SEEN: 9 pre-existing in test_verify_gate_b4/b5/redteam (RISK-HIT / adversarial Verdict)，非本次
SCOPE_CHANGES: none（僅允許兩檔）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
