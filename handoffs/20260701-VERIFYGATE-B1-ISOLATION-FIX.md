# B1 測試隔離修正（Composer 2.5 讀此檔執行）

**問題（Claude 驗收抓到，Codex review 未涵蓋）**:`tests/governance/test_verify_gate.py` 直接寫入**真實**目錄 `handoffs/run_receipts/` 與真實檔 `.claude/gate/verify_audit.log`（見測試碼 `RECEIPTS_DIR`/`AUDIT_LOG` 常數）。每次跑測試都污染這兩個**受 git 追蹤**的路徑,並讓噪音混入 B2 checker 要讀的 audit log。

## 修正
1. **`scripts/run_with_receipt.py` 加環境變數覆蓋**（預設維持現行路徑,不破壞正式行為）:
   - `VERIFY_GATE_RECEIPTS_DIR`(預設 `handoffs/run_receipts`)
   - `VERIFY_GATE_AUDIT_LOG`(預設 `.claude/gate/verify_audit.log`)
   - 兩者存在時,receipt 與審計事件寫到覆蓋路徑。
2. **`tests/governance/test_verify_gate.py` 全面用隔離路徑**:
   - 用 pytest `tmp_path`/`monkeypatch.setenv` 把上述兩個環境變數指到臨時目錄,讓**所有**測試(含 `_run_wrapper` helper)不再碰真實 `handoffs/run_receipts/` 與真實 `verify_audit.log`。
   - `RECEIPTS_DIR`/`AUDIT_LOG` 常數改為從環境變數讀(或測試內以 fixture 注入),確保 `_latest_receipt_for_claim`/audit 斷言都指向臨時路徑。

## 驗證
1. 跑 `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` → 全綠。
2. 跑測試**前後** `git status --porcelain handoffs/run_receipts/ .claude/gate/verify_audit.log` → **無新增/改動**(證測試不再污染真實路徑)。這是本次的核心驗收點。
3. 手動 `run_with_receipt.py --claim-id x -- python -c "print(1)"`(不設環境變數)→ 仍寫到預設 `handoffs/run_receipts/`(證正式行為不變);之後手動刪除該筆。

## 規則
- 僅標準庫;venv/bin/python;不 import momentum/api。
- 結構化收尾:TESTS_RUN(貼 pytest summary + 前後 git status 原文)、FAILURES_SEEN、SCOPE_CHANGES。報告勿用「已驗/真紅」字樣。
