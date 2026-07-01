# VERIFYGATE B4+B5 六 BLOCKING 修補 — Composer 收尾

## 逐 finding 修補摘要

| ID | 修了什麼 | 新/更新測試 |
|----|----------|-------------|
| **B4-1** | `scripts/gate.sh`：高風險非 waived `--adversarial` 改 fail-closed——ADV 路徑走 `verify_task_provenance.py check-adversarial`，其餘須過 `reconcile_stamps_check.sh`，否則拒發 token | `test_gate_adversarial_rejects_non_adv_non_reconcile` |
| **B4-2** | `scripts/verify_task_provenance.py`：廢除日期 grandfather；改 `LEGACY_STAMP_ALLOWLIST`（DELIB reconcile 兩戳記）；`check-stamp` 新增 `--file`；`reconcile_stamps_check.sh` 傳 reconcile 路徑 | `test_reconcile_rejects_backdated_stamp_not_on_allowlist`；`test_delib_reconcile_still_passes_allowlist`（原 grandfather 測試更名） |
| **B4-3** | 刪除 `handoffs/run_receipts/*mutation-test_b4*`（8 檔）；`.claude/gate/verify_audit.log` 清空回 committed 空檔 | （衛生清理，無新測試） |
| **B5-1** | `verification_claim_check.py`：`check_result_structured_fields()` 補必填欄、枚舉、`RECEIPTS` 格式驗證（RESULT 檔主路徑直接擋） | `test_b5_result_invalid_enum_fails_checker`；`test_v11_pending_open_blocks_done_claim` fixture 補合法 RESULT 硬欄位（回歸適配） |
| **B5-2** | `claim_fingerprint()` 改 canonical 主題項 `(scope, runtime_expectation, task_id)`，剝除 raw `source_line_text` | `test_b5_fingerprint_conflict_real_markdown_green_then_red_fails`；`test_b5_fingerprint_conflict_real_markdown_superseded_passes` |
| **B5-3** | `template_check.sh` §A FACT-RECEIPT 判定詞彙擴至指令輸出類（pytest/bash/python/exit/rc=/stdout/輸出/passed/failed/sha256…） | `test_b5_spec_command_output_fact_receipt_missing_fails` |

## ASSUMPTIONS_VERIFIED

- Codex 六 BLOCKING repro 已對照修補後行為：`/tmp/not-adv.md` gate rc=1；`RUNTIME_CHECK=ok` checker rc=1；parser 綠/紅行 fingerprint 現可碰撞。
- DELIB reconcile body hash=`86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044`（`reconcile_body_hash.sh` 實跑）。
- committed `verify_audit.log` 為空檔；合成 mutation-test_b4 事件已移除。

## TESTS_RUN

```
pytest tests/governance/ -q
# 55 passed in 11.59s

bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md
# RECONCILE-STAMP PASS

bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
bash scripts/template_check.sh todo docs/VERIFY_GATE_TODO.md
# TEMPLATE PASS (both)

tmp=$(mktemp); printf '# not an ADV\n' > "$tmp"
bash scripts/gate.sh dispatch --intent test --risk high --facts-asked none-needed:test \
  --review-role single-executor:n/a --template n/a:test --adversarial "$tmp"
# rc=1（非 ADV 非 reconcile 拒發）
```

## FAILURES_SEEN

- 首跑 `pytest tests/governance/ -q`：`test_v11_pending_open_blocks_done_claim` 因 B5-1 RESULT 必填欄位檢查失敗 → 更新該測試 fixture 補五硬欄位後全綠。

## SCOPE_CHANGES

- none（僅 prompt 允許範圍內檔案 + 對應測試）。

## NUMERIC_OR_SCHEMA_IMPACT

- `claim_fingerprint` 語意變更：同 scope/task/runtime 的綠/紅 claim 現可觸發 #6 衝突（刻意硬化，非數值計算影響）。
- RESULT handoff 經 checker 掃描時須含五硬欄位與合法枚舉。

HANDOFF_NOT_UPDATED: 執行合約規定 append-only 寫本檔，不覆蓋根 HANDOFF.md。
