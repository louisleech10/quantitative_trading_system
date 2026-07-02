# O3 — 治理 forensic 誤報修補（Composer 收尾）

## 修法

`scripts/verification_claim_check.py`：

1. **`_GOVERNANCE_FORENSIC_GLOBS`**：以 `fnmatch` 比對治理過程檔路徑（REDTEAM / ADV / REVIEW / CLOSURE / RECONCILE / `-composer` / FIX-PROMPT / IMPL-PROMPT / `docs/VERIFY_GATE_*.md`）。
2. **`_detect_source_context`**：上述檔案非 operational 段 → `forensic_discussion`；`## 已完成` 等 operational 段仍 `operational_result`（不 blanket 免責）。
3. **`_is_forensic_example_or_discussion` + `_forensic_verify_requires_backing`**：`classify_mode` 開頭判定——攻擊範例/歸屬引用/假 VERIFY/錯誤訊息敘述 → `discussion` 放行；僅當 VERIFY/REF 指向**可解析真 backing** 且非範例敘述時，fall-through 照常驗 citation backing。
4. **零豁免不動**：`HANDOFF.md`、commit-msg、`*RESULT*` 路徑不在 glob；R6 假歸屬在 HANDOFF 仍 operational 擋。

## 新測試（`tests/governance/test_verify_gate_o3.py`）

| 測試名 | 意圖 |
|--------|------|
| `test_o3_redteam_attack_examples_allowed` | REDTEAM 檔攻擊範例字串 exit 0 |
| `test_o3_handoff_same_operational_still_blocked` | HANDOFF 同款仍 exit 1 |
| `test_o3_commit_msg_same_still_blocked` | commit-msg 同款仍 exit 1 |
| `test_o3_v7_regression_spec_files_unblocked` | V7 SPEC/DELIB 不回歸 |
| `test_o3_r6_fake_attribution_handoff_still_blocked` | R6 HANDOFF 假歸屬仍擋 |
| `test_o3_fix_prompt_operational_claim_still_blocked` | FIX-PROMPT operational 新宣稱仍擋 |
| `test_o3_repo_redteam_files_exit_zero` | 本 repo REDTEAM 治理檔全放行 |

ASSUMPTIONS_VERIFIED: `python scripts/verification_claim_check.py --files handoffs/20260702-VERIFYGATE-REDTEAM-*.md` → exit 0（僅 WARN 近似詞）；METAFIX-PROMPT `## 已完成` 裸宣稱仍 exit 1。
TESTS_RUN: `pytest tests/governance/ -q` → 102 passed
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 `scripts/verification_claim_check.py` + 新測試檔）
NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_NOT_UPDATED: 執行合約 append-only 至本檔，不重寫根 HANDOFF.md

STATUS: DONE
