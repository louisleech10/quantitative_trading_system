# B1 VERIFY_GATE handoff — Composer bqbxovif9

## 實作範圍
- `scripts/run_with_receipt.py`（receipt JSON+log、審計事件、runtime_class 推導、exit 透傳）
- `.gitignore` 白名單例外（`!handoffs/run_receipts/*.log`、`!.claude/gate/verify_audit.log`）
- `handoffs/run_receipts/.gitkeep`
- `tests/governance/test_verify_gate.py`（V1 + gitignore + mutation 探針）

## ASSUMPTIONS_VERIFIED
- `git check-ignore` 對已 un-ignore 路徑：無 `-v` 時 exit 1；`-v` 仍印 negation 規則且 exit 0 → 測試用無 `-v` 判斷 receipt 可追蹤
- receipt 必填欄位 25 個（SPEC P1-1 列舉；TODO 寫 22 為概數）

## TESTS_RUN
`venv/bin/python -m pytest tests/governance/test_verify_gate.py -k "receipt or gitignore" -q` → 4 passed in 0.33s

## FAILURES_SEEN
- `test_gitignore_receipt_trackable` 初版用 `git check-ignore -v` 對 receipt log 得 exit 0（negation 規則仍輸出）→ 改為無 `-v` 後通過

## SCOPE_CHANGES
none

## NUMERIC_OR_SCHEMA_IMPACT
新增 receipt JSON schema v1.0（25 欄）與 verify_audit.log 審計事件格式；不影響 momentum/api 數值路徑

---

## B1 FIX（Codex review 回修）— 2026-07-01

### 修正內容
1. **BLOCKING 1**：`derive_runtime_class` 偵測 argv/output 中 `::test_mutation_` node-id；`selected_node_ids` 從 argv + pytest PASSED/FAILED 行解析。
2. **BLOCKING 2**：`FileNotFoundError` 捕獲 → exit_code=127、stderr 記 "command not found"、仍寫 receipt/audit。
3. **BLOCKING 3**：`test_receipt_schema` 斷言 audit 的 command_sha256/receipt_sha256/exit_code/runtime_class；receipt 檔重算 sha256 比對。
4. **NON-BLOCKING 4**：新增 `test_requested_class_does_not_override_runtime_class`。
5. **NON-BLOCKING 5**：`test_mutation_receipt_missing_field_fails` 改呼叫 production `validate_receipt_schema()`。
6. 新增 `test_command_not_found_still_produces_receipt`、`test_mutation_node_id_runtime_class_and_selected_nodes`。

### ASSUMPTIONS_VERIFIED
- pytest PASSED 行格式 `path::test_name PASSED` 可被 `_NODE_ID_RESULT_RE` 解析
- `python -c pass` 不產 pytest 摘要 → runtime_class=static_only（即使 requested_class=mutation_runtime）
- 不存在命令觸發 `FileNotFoundError`（非 OSError 其他子類）

### TESTS_RUN
```
venv/bin/python -m pytest tests/governance/test_verify_gate.py -q
============================== 7 passed in 2.98s ===============================
```

手動路徑 1：
```
venv/bin/python scripts/run_with_receipt.py --claim-id manual-mutation-node-id -- venv/bin/python -m pytest tests/governance/test_verify_gate.py::test_mutation_receipt_missing_field_fails -q
→ runtime_class=mutation_runtime, selected_node_ids=['tests/governance/test_verify_gate.py::test_mutation_receipt_missing_field_fails'], exit_code=0
```

手動路徑 2：
```
venv/bin/python scripts/run_with_receipt.py --claim-id manual-missing-cmd -- definitely-not-a-real-command-verifygate
→ wrapper_exit=127, receipt exit_code=127, receipt_id=20260701T061748Z-manual-missing-cmd
```

### FAILURES_SEEN
none

### SCOPE_CHANGES
none（僅 `scripts/run_with_receipt.py`、`tests/governance/test_verify_gate.py`）

### NUMERIC_OR_SCHEMA_IMPACT
none（行為修正；schema 欄位不變）

STATUS: DONE
