# B4 實作指派（Composer 2.5 讀此檔執行）

實作驗收防偽閘 **Batch B4** = `docs/VERIFY_GATE_TODO.md` 的 Task 4.1/4.2/4.3/4.4（完整規格在該 TODO,逐條讀）。依賴 B1(run_with_receipt.py+審計事件)、B2(verification_claim_check.py)。

## Task 4.1 — mutation_probe_check.sh 接 receipt（行為不變）
`scripts/mutation_probe_check.sh` 規則3 的 `pytest -k test_mutation_` 改經 `run_with_receipt.py --claim-id mutation-<檔stem> --` 跑;結尾 append receipt 路徑到 `.claude/gate/audit.log`。**PASS/FAIL 判定與對外訊息、exit code 一律不變**——僅新增 receipt 副作用。

## Task 4.2 — W3:adversarial 綁 provenance
`scripts/gate.sh` 高風險 `--adversarial <path>`:除檔案存在外,path 須匹配 `handoffs/.*-ADV-(CODEX|COMPOSER)\.md` 命名 + 對應 task-id 在審計 log 有派工事件(或 `waived:理由`)。

## Task 4.3 — W2:reconcile stamp 綁 provenance
`scripts/reconcile_stamps_check.sh`:戳記 `task:<id>` 須在審計 log 有對應委員派工事件 + 輸出檔 hash 匹配(機械對照);**不破壞既有 sha256 body-hash 檢查**(現行 reconcile 檔須仍 PASS)。

## Task 4.4 — scripts/verify_audit_chain.py（W7 輔助,人工抽查,不 fail-closed）
讀 verify_audit.log,對每事件驗 receipt/log 檔存在+hash 相符,印對照表(正常 OK、竄改 TAMPER)。純報告。

## 測試（新檔 tests/governance/test_verify_gate_b4.py,勿動 test_verify_gate.py）
- Task4.1 行為不變:對固定綠/紅 fixture,mutation_probe_check.sh 改前後 PASS/FAIL 訊息+exit 一致(可用 subprocess 比對關鍵行);且產出 receipt。
- Task4.2:自寫 handoffs/fake-ADV.md 無 task 審計 → gate --adversarial 拒;有審計 → 過。
- Task4.3:手寫戳記無對應 task 審計 → reconcile_stamps_check 拒;真委員 task 事件+hash → 過;**既有 handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md 須仍 PASS 或明確說明為何(避免破壞既有流程)**。
- Task4.4:test_audit_chain_detects_tamper(改 receipt.json 使 sha256≠審計事件值→竄改列 TAMPER;正常列 OK)。
- **測試隔離**:用 VERIFY_GATE_AUDIT_LOG 等 env + tmp,不污染真實 .claude/gate/verify_audit.log、handoffs/run_receipts。

## 驗證(收尾附原文)
1. `venv/bin/python -m pytest tests/governance/test_verify_gate_b4.py -q` 全綠。
2. mutation_probe_check.sh 行為不變:貼改前後對同 fixture 的關鍵輸出 diff(應一致)。
3. **重要:確認既有 `bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` 仍 PASS**(W2 修改不得破壞現行已戳記的 reconcile;若因新 provenance 檢查失敗,須設計相容:例如僅在有審計事件時強制、既有戳記 grandfather 或明列)。
## 規則
僅標準庫/bash3.2;venv/bin/python;不 import momentum/api。結構化收尾(TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES);報告勿用「已驗/真紅」字樣。**不動** PreToolUse/git hook/CI(那是 B3)、不動 template_check.sh/verification_claim_check.py(那是 B5)。
