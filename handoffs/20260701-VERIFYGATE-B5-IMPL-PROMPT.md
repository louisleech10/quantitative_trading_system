# B5 實作指派（Composer 2.5 讀此檔執行）

實作驗收防偽閘 **Batch B5** = `docs/VERIFY_GATE_TODO.md` 的 Task 5.1/5.2/5.3（完整規格在該 TODO,逐條讀）。依賴 B2(verification_claim_check.py)。

## Task 5.1 — RESULT 硬欄位（枚舉）
- 新增 `templates/RESULT_TEMPLATE.md`,欄位:`STATIC_CHECK|RUNTIME_CHECK|MUTATION_CHECK = NOT_RUN|PASS|FAIL|N/A:reason`、`RECEIPTS=[...]`、`OPEN_PENDING=[...]`。
- `scripts/template_check.sh` 加 result kind(或錨點檢查):枚舉外的值(如 `RUNTIME_CHECK=ok`)→ FAIL。
- `scripts/verification_claim_check.py` 讀這些結構欄判定:`RUNTIME_CHECK=PASS` 但 `RECEIPTS=[]` → FAIL(PASS 需 receipt);`MUTATION_CHECK=NOT_RUN` 且該 task 寫「已驗」→ FAIL。

## Task 5.2 — #6 衝突檢查（v1 僅此,不做完整 render）
`scripts/verification_claim_check.py` 加:掃同 `claim_fingerprint`,若曾出現 FAIL/紅燈紀錄,而舊 VERIFY 綠 claim 未標 `SUPERSEDED:` → FAIL。**不自動重寫 HANDOFF、不做全域 render**。

## Task 5.3 — W1:SPEC §A FACT-RECEIPT
`scripts/template_check.sh spec` 加檢:§A 含「已確認」且涉型別/形狀/命令輸出的行,須同行/鄰行有 `FACT-RECEIPT:<transcript或receipt_id>`;純設計假設不得寫「已確認」(用「待確認」)。**只驗有出處指標存在,不檢查事實內容為真。**

## 測試（新檔 tests/governance/test_verify_gate_b5.py,勿動 test_verify_gate.py）
- 5.1:RESULT `RUNTIME_CHECK=PASS` 無 RECEIPTS → checker FAIL;枚舉外值 → template_check FAIL;合法 RESULT → 過。
- 5.2:構造同 fingerprint 先綠(VERIFY)後紅、舊綠未標 SUPERSEDED → FAIL;加 SUPERSEDED:<id> → 過。
- 5.3:SPEC §A「已確認:raw_data.index 是 DatetimeIndex」無 FACT-RECEIPT → template_check FAIL;附 FACT-RECEIPT 或改「待確認」→ 過。
- **不得回歸**:改 template_check.sh 後,既有 `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` 與 `todo docs/VERIFY_GATE_TODO.md` 仍須 PASS(現行 SPEC/TODO 不得因新 §A 檢查被誤擋——若 SPEC §A 現況缺 FACT-RECEIPT,設計為:僅對「已確認+資料結構詞」行要求,或既有檔 grandfather;明列處理方式)。
- **測試隔離**:tmp fixture,不污染真實 repo 檔/路徑。

## 驗證(收尾附原文)
1. `venv/bin/python -m pytest tests/governance/test_verify_gate_b5.py -q` 全綠。
2. **重要:`bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` 與 `todo docs/VERIFY_GATE_TODO.md` 改後仍 PASS**(貼原文;不得破壞既有 gate)。
3. `verification_claim_check.py` 對既有檔仍 V7 誤報=0(貼 exit 0)。
## 規則
僅標準庫/bash3.2;venv/bin/python;不 import momentum/api。結構化收尾(TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES);報告勿用「已驗/真紅」字樣。**不動** PreToolUse/git hook/CI(B3)、不動 gate.sh/reconcile_stamps_check.sh/mutation_probe_check.sh(B4)。verification_claim_check.py 只加 5.1 讀欄+5.2 衝突,勿改 B2 既有 claim-object 邏輯。
