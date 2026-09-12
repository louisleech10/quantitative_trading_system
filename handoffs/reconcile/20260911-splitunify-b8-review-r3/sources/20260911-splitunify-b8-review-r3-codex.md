# SPLITUNIFY b8 R3 codex review
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R3

## CODEX-R3-P3-00

**斷言**: 本輪逐項核對後無 finding。

**碼證**: adapter NaT probe → `AlignmentViolationError`，訊息含 `NaT`；clean probe → `rows 12 has_row_pos True input_unchanged True`；同一 frame 的 `split_per_symbol` → `ValueError`，兩者皆 `ValueError` fail-closed。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b8-review-r2/synth.md#f9270e93c6c0; momentum/Analysis/ic_split_adapter.py#b05b0f73e417; momentum/core/contracts.py#1471cef968a3; tests/momentum/core/test_splitunify_producer_attest.py#fbe4779e8477

[P3] 信心度=High；R2 自家 finding `CODEX-R2-P2-01` 已閉合，adapter 現在回傳正確 typed exception，非 `NameError`。
主動攻擊面：同輸入比較 adapter 與 `split_per_symbol` 的錯誤處理；掃描 `split_cpcv`／`split_wf`／cross-sectional adapter／holdout／`split_per_symbol` 的 guard 覆蓋；對五個 b8 生產模組執行 `ruff check --select F821`，無未匯入名稱。
R2 閉合依據：3 條 targeted tests、adapter test file 5 tests、producer contract test file 24 tests 全部通過；`freeze_splitunify_golden.py` → `GOLDEN OK`。
數值輸出：R2 fix 的 production diff 僅新增一個既有 contracts exception import；`git diff --check 655d52d4^ 655d52d4` rc=0，未見 plan／schema／golden 位移。
ASSUMPTIONS_VERIFIED: typed exception inheritance、兩條 NaT producer 行為、所有 producer guard callsite、b8 生產檔 undefined-name scan、golden unchanged 均已由上述命令核對。
TESTS_RUN: `venv/bin/python -m pytest -q ...` → 3 passed；adapter suite → 5 passed；producer suite → 24 passed；`venv/bin/python scripts/freeze_splitunify_golden.py` → GOLDEN OK；ruff F821 → All checks passed。
FAILURES_SEEN: 初次反例 probe 因 `python -c` quoting 產生 SyntaxError；修正同一 probe 後 rc=0，輸出為 `AlignmentViolationError` 且 `is_alignment_violation True`、`has_nat True`。
SCOPE_CHANGES: none；遵守 brief「禁改碼」，僅新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: none；未修改生產碼、測試斷言、plan schema 或輸出大小。
HANDOFF_PATH: handoffs/20260911-splitunify-b8-review-r3-codex.md
NEXT: 無；本家 R2 finding 可收案。
BLOCKED: none
DECISIONS: `CODEX-R2-P2-01` 判定 CLOSED；本輪以 sentinel 表示 0 個新 finding。
PITFALLS: 反例 probe 必須保留實際多行 Python 語法，避免把 `\\n` 傳成字面反斜線。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R2-P2-01
STATUS: DONE
