# B1 測試隔離修正 — 執行收尾（Composer）

## 變更摘要

### `scripts/run_with_receipt.py`
- 新增 `VERIFY_GATE_RECEIPTS_DIR` / `VERIFY_GATE_AUDIT_LOG` 環境變數覆蓋（預設維持 `handoffs/run_receipts`、`.claude/gate/verify_audit.log`）。
- `_receipts_dir()` / `_audit_log_path()` 於 runtime 讀取 env；`main()` 使用上述 helper。

### `tests/governance/test_verify_gate.py`
- `autouse` fixture `isolated_verify_gate_paths`：`tmp_path` + `monkeypatch.setenv` 注入隔離路徑。
- `_receipts_dir()` / `_audit_log()` 從環境變數讀路徑；`_latest_receipt_for_claim` / `_read_last_audit_event` 改呼叫 helper。
- `_run_wrapper` 子進程繼承 monkeypatch 後的 env，不再寫入真實受追蹤路徑。

## ASSUMPTIONS_VERIFIED
- `run_with_receipt.py` 子進程會讀取 `VERIFY_GATE_*` env（subprocess 繼承 monkeypatch）。
- 未設 env 時手動執行仍寫入預設 `handoffs/run_receipts/`（已手動跑並刪除 `*-x.*` receipt）。

## TESTS_RUN

### pytest
```
venv/bin/python -m pytest tests/governance/test_verify_gate.py -q
7 passed in 5.26s
```

### git status — 測試前
```
?? .claude/gate/verify_audit.log
?? handoffs/run_receipts/
```

### git status — 測試後
```
?? .claude/gate/verify_audit.log
?? handoffs/run_receipts/
```

### 檔案清單前後 diff
`find handoffs/run_receipts .claude/gate/verify_audit.log -type f | sort` → **FILE_LIST_UNCHANGED**（測試未新增/改動真實路徑內檔案）。

### 預設行為手動驗證
```
venv/bin/python scripts/run_with_receipt.py --claim-id x -- python -c "print(1)"
→ 產出 handoffs/run_receipts/20260701T062850Z-x.{json,log}；已刪除。
```

## FAILURES_SEEN
none

## SCOPE_CHANGES
none

## NUMERIC_OR_SCHEMA_IMPACT
none（僅路徑可配置；receipt schema 不變）

HANDOFF_NOT_UPDATED: 執行端合約 — 根 HANDOFF.md 由 Claude 維護
