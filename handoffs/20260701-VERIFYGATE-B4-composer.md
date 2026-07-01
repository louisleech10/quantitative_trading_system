# B4 實作收尾 — Composer (VERIFYGATE-B4)

## 完成項目
- **Task 4.1** `scripts/mutation_probe_check.sh`：規則3 經 `run_with_receipt.py --claim-id mutation-<stem>` 包裝 pytest；結尾 best-effort append `mutation_receipt=<path>` 至 gate audit（`VERIFY_GATE_COMMITTEE_AUDIT_LOG` 可覆蓋）。PASS/FAIL 判定與 exit code 不變。
- **Task 4.2** `scripts/gate.sh`：高風險 `--adversarial` 對 `handoffs/*-ADV-(CODEX|COMPOSER).md` 呼叫 `verify_task_provenance.py check-adversarial`（命名 + `committee_dispatch` 事件 + 輸出 hash）。reconcile 路徑仍走 `reconcile_stamps_check.sh`。
- **Task 4.3** `scripts/reconcile_stamps_check.sh`：body sha256 檢查後對每戳記呼叫 `verify_task_provenance.py check-stamp`。**Grandfather**：`VERIFY_GATE_TASK_PROVENANCE_GRANDFATHER_DATE` 預設 `2026-07-01`，該日（含）前且無審計事件之戳記跳過 provenance（`DELIB-RECONCILE` 仍 PASS）。
- **Task 4.4** 新增 `scripts/verify_audit_chain.py`：讀 `verify_audit.log` 印 receipt/log 對照（OK / TAMPER），純報告 exit 0。
- **共用** 新增 `scripts/verify_task_provenance.py`：`committee_dispatch` JSON 行格式 `{event, task_id, family, output_path, output_sha256, ts}`。

## ASSUMPTIONS_VERIFIED
- `run_with_receipt.py` 包裝 pytest 須將 `${VENV_PY}` 作為子命令首項（否則 `-W` 被當 executable → rc=127）。
- 既有 `handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` 戳記日期 2026-07-01、無 `committee_dispatch` 事件 → grandfather 後 `reconcile_stamps_check.sh` exit 0。
- gate adversarial case 模式 `handoffs/*-ADV-*.md` 不 match 子目錄；測試 fixture 放 `handoffs/` 根下。

## TESTS_RUN
```
$ venv/bin/python -m pytest tests/governance/test_verify_gate_b4.py -q
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/louis/Desktop/quantitative_trading_system
configfile: pytest.ini
plugins: asyncio-1.2.0, anyio-4.10.0, cov-7.0.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 9 items

tests/governance/test_verify_gate_b4.py::test_mutation_probe_green_produces_receipt_and_same_verdict PASSED [ 11%]
tests/governance/test_verify_gate_b4.py::test_mutation_probe_red_same_fail_verdict_and_receipt PASSED [ 22%]
tests/governance/test_verify_gate_b4.py::test_mutation_probe_key_lines_stable_green_vs_red PASSED [ 33%]
tests/governance/test_verify_gate_b4.py::test_gate_adversarial_rejects_without_dispatch PASSED [ 44%]
tests/governance/test_verify_gate_b4.py::test_gate_adversarial_passes_with_dispatch PASSED [ 55%]
tests/governance/test_verify_gate_b4.py::test_reconcile_rejects_stamp_without_dispatch PASSED [ 66%]
tests/governance/test_verify_gate_b4.py::test_reconcile_passes_with_dispatch_and_hash PASSED [ 77%]
tests/governance/test_verify_gate_b4.py::test_delib_reconcile_still_passes_grandfather PASSED [ 88%]
tests/governance/test_verify_gate_b4.py::test_audit_chain_detects_tamper PASSED [100%]

============================== 9 passed in 1.87s ===============================
```

```
$ bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md
RECONCILE-STAMP PASS: handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md 已獲 codex,composer 全數 APPROVED 且本體雜湊相符(sha256:86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044)。
  使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。
```

mutation_probe 行為抽樣（綠 exit=0 / 紅 exit=1；關鍵 PASS/FAIL 行不變，新增 receipt 副作用）：
```
→ 跑 mutation 探針: pytest -k test_mutation_ .../test_b4_green.py
1 passed, 1 deselected in 0.00s
MUTATION-PROBE PASS: ... 且 1 個探針真跑過。
→ 跑 mutation 探針: pytest -k test_mutation_ .../test_b4_red.py
1 failed, 1 deselected in 0.02s
MUTATION-PROBE FAIL:
```

## FAILURES_SEEN
- 初版 mutation 包裝漏 `${VENV_PY}` 子命令首項 → pytest rc=127；已修。
- 初版綠 fixture 未過 `mutation_probe_static`（偽 raises）→ 改 monkeypatch 探針。
- 初版 test 模組 import 用錯 loader → 已修。

## SCOPE_CHANGES
- none（範圍內新增 `verify_task_provenance.py`、`verify_audit_chain.py`、`test_verify_gate_b4.py`；未動 B3/B5 檔案）。

## NUMERIC_OR_SCHEMA_IMPACT
- 新增 `committee_dispatch` 審計 JSON 行 schema（append 至 `.claude/gate/audit.log` 或 `VERIFY_GATE_COMMITTEE_AUDIT_LOG`）。
- mutation 規則3 新增 receipt + `mutation_receipt=` audit 副作用；對外 PASS/FAIL 判定不變。
