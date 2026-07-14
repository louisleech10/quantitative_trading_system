# IC1C-B2 Code Review R4 — Codex (2026-07-14)

task-id: IC1C-B2 | reviewer: B2/codex | scope: R3 唯一 BLOCKING 閉合重驗

## Verdict

**CLOSED。** `check_gross_ic_pair` 現依 Frozen TODO:127/r7b 在 `max(|gi|)≥0.05` 時強制同號；0 無號，因此 `(0.0,0.2)` FAIL。近零雙側 `max<0.05` 仍允許異號，且 `|diff|≤0.2`、finite、[-1,1] gate 未弱化。R3 剩餘 BLOCKING 已閉合，無新 BLOCKING。

## Evidence

- `bash scripts/reconcile_stamps_check.sh ...SPECREV... codex,composer,grok` 與 TODOREV 同命令 → 兩者 PASS（sha256 `ab910286...` / `936daabc...`）。
- 直接呼叫 predicate：near-zero opposite PASS；threshold opposite FAIL；zero-vs-material FAIL；diff>0.2 FAIL；non-finite FAIL；out-of-range FAIL；5 語意組/6 probes 全符合 oracle。
- `PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/ic1c_freeze_baseline.py --self-test` → PASS，含 r7b predicates。
- `/tmp/ic1c-b2-r4.M8z6hL` 唯讀鏡像跑 `.../venv/bin/python scripts/ic1c_freeze_baseline.py --baseline new2` → exit 0，`compared_features=4`；sha `4babd5...`。與工作區 sha `57cdbc...` 的 JSON 移除 lineage `git_head` 後逐鍵相等；差異僅鏡像無 `.git` 而記 `unknown`。
- `git diff --check -- scripts/ic1c_freeze_baseline.py handoffs/IC1C-B2-RESULT.md` → PASS。

ASSUMPTIONS_VERIFIED: Frozen TODO 是 RESULT 上位 oracle；composer 附錄與單檔修補一致；zero-vs-material 現為 FAIL；new2 真 API 路徑通過。
TESTS_RUN: predicate 6 probes PASS；`--self-test` PASS；隔離鏡像 `--baseline new2` exit 0；兩份 reconcile checker PASS；diff-check PASS。
FAILURES_SEEN: none；鏡像 sha 差異已證實只來自 `git_head` lineage，非語意/數值差異。
SCOPE_CHANGES: none；僅新增本 review 產出檔，未改程式、baseline 或 `data_cache/`。
NUMERIC_OR_SCHEMA_IMPACT: reviewer 無；修補僅收緊 r7b 同號 predicate，schema/輸出大小未變。
OUTPUT: handoffs/IC1C-B2-CODEREV-R4-codex.md
CODE-REVIEW-R4: APPROVE(0 BLOCKING)
