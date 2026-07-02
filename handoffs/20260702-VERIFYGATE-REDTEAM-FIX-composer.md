# VERIFYGATE 紅隊修補 — Composer 收尾

依 `handoffs/20260702-VERIFYGATE-REDTEAM-FIX-PROMPT.md` + reconcile v2 實作 R1–R7。

## 逐項修補

| R# | 檔案 | 變更摘要 |
|----|------|----------|
| R1 | `scripts/gate_check.sh` | Bash 路徑比對前 while 剝除 `VAR=value ` env 前綴，再 match executor |
| R2 | `scripts/verification_claim_check.py`, `scripts/verify_pretooluse.sh` | `docs/*` 在 `## 已完成`/STATUS/RESULT 段視為 operational_result；PreToolUse 亦掃 `docs/` operational |
| R3 | `scripts/verification_claim_check.py` | `check_backing`：success claim 無 scope/runtime 線索 → `模糊 scope` FAIL |
| R4 | `scripts/verify_pretooluse.sh` | `realpath` 正規化 repo root 與 file_path；無法對齊目標檔 fail-closed exit 2 |
| R5 | `docs/VERIFY_GATE_EMERGENCY.md` | 新增：unset core.hooksPath、暫移 PreToolUse hook、修復後回歸步驟 |
| R6 | `scripts/verification_claim_check.py` | 假歸屬（寫道/檔案說 + 引號內判詞）不享 citation 豁免；`classify_mode` 改 operational |
| R7 | `scripts/gate.sh` | 新增 `--task-id`；高風險派工在 provenance 機檢**前** append `committee_dispatch` JSON 至 audit.log |

## 新測試（`tests/governance/test_verify_gate_redteam.py`）

- `test_r1_gate_check_env_prefix_matches_bare_verdict`
- `test_r1_gate_check_blocks_without_token_isolated`
- `test_r1_gate_check_blocks_multiple_env_prefixes_isolated`
- `test_r2_docs_operational_without_backing_blocked`
- `test_r2_docs_discussion_prose_allowed`
- `test_r3_vague_scope_receipt_wash_blocked`
- `test_r3_specific_scope_receipt_allowed`
- `test_r4_pretooluse_tmp_private_tmp_same_verdict`
- `test_r4_pretooluse_fail_closed_on_unresolvable_handoff_path`
- `test_r6_fake_attribution_quoted_polarity_blocked_staged`
- `test_r6_true_attribution_with_verify_allowed`
- `test_r6_v7_regression_spec_files_unblocked`
- `test_r7_gate_task_id_appends_committee_dispatch`

```
ASSUMPTIONS_VERIFIED: gate_check 硬編碼 .claude/gate 不變；R1 隔離測試用 tmp 複本 gate_check；R7 emitter 在 adversarial 機檢前寫 audit 且 export VERIFY_GATE_COMMITTEE_AUDIT_LOG；真實 .claude/gate/* 未改
TESTS_RUN: pytest tests/governance/ -q → 88 passed；template_check spec docs/VERIFY_GATE_SPEC.md → PASS；reconcile_stamps_check DELIB+P0FF3 reconcile → PASS
FAILURES_SEEN: R1 初版 assert exit 2 因 repo 有 fresh dispatch.token 得 0 → 改隔離 GATE_DIR 複本測試後通過
SCOPE_CHANGES: none（僅 prompt 允許檔 + 新測試 + VERIFY_GATE_EMERGENCY.md）
NUMERIC_OR_SCHEMA_IMPACT: committee_dispatch JSON 欄位對齊 verify_task_provenance；checker 新增模糊 scope / docs operational / 假歸屬判定；無 receipt schema 變更
```

STATUS: DONE
