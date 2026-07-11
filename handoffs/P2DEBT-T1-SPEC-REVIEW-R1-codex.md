# P2DEBT-T1 SPEC R1 Codex adversarial review
Task-id: p2debt-t1 | Date: 2026-07-11 | Reviewer: codex | sibling reviews: 未讀

## Receipts
- 基線：`venv/bin/python -m pytest tests/governance -q` 實跑兩次，皆遇環境間歇中止；再按同一 149 nodes 分檔實跑：`dispatch_wrapper+gate_deny_audit+precommit_autofix+sync_check`=25 passed；`test_verify_gate.py`=28 passed；`b4+b5+redteam`=9 failed,32 passed；其餘五檔=55 passed。合計確認 **9 failed / 140 passed**，紅點正是 B4×3+B5×5+R7×1。
- 大小寫：`printf ... | grep -qE 'Verdict[[:space:]]*[:：]'` → `VERDICT: APPROVED` rc=1、`Verdict: APPROVED` rc=0；原碼 `scripts/gate.sh:207` 相符。
- 路徑反例：tmp 非 ADV + `Verdict: REJECTED` → rc=1，進 `RECONCILE-STAMP FAIL`；tmp ADV + uppercase `VERDICT` → rc=1 D-1；tmp ADV + 有 dispatch + `Verdict: REJECTED` → rc=0 `GATE PASS`。
- B5 原始修法反例：tmp 複本只補 `RISK-HIT: none`（BAD 再補 C3）後跑四個 B5 nodes → **2 failed,2 passed**；兩個缺 receipt 負例反而 rc=0，證初稿清單不真且正例可假綠。
- B5 修正版最小反例：`bash scripts/template_check.sh spec /tmp/p2debt-b5-negative.md`（`- **已確認**:`、無 receipt）→ rc=1 且報缺 FACT-RECEIPT；同結構加 receipt → rc=0。
- B 案 tmp 實證：真實 `docs/VERIFY_GATE_SPEC.md` 副本補 `RISK-HIT: b` + 兩個相鄰非空 FACT-RECEIPT 後，`bash scripts/template_check.sh spec <tmp-copy>` → TEMPLATE PASS。

## BLOCKING findings
- **B-CODEX-1 — B5 修法造成假綠。** `check_sec_a_fact_scope` 只以 `### ...已確認` 或 `- **...已確認` 開 fact-scope；現有普通 `- 已確認:` 不觸發。正式 SPEC 必要求三個已確認 fixture 遷移到檢查器可辨識的 canonical scope（建議 `- **已確認**:`），再保留缺 receipt=FAIL／有 receipt=PASS oracle；不可只補 RISK-HIT/C3。
- **B-CODEX-2 — §V 的 mutation 宣稱沒有落到測試。** repo 中無 RISK-HIT 專屬測試；遷移完 uppercase `VERDICT` 也會消失，故刪 RISK-HIT gate 或改成 case-insensitive 時 suite 仍可能綠。正式 SPEC 須新增至少兩個顯式負例：缺 `RISK-HIT` 必 FAIL、`VERDICT:` uppercase 必 FAIL；並要求從正例移除 FACT-RECEIPT 必 FAIL。

## MINOR findings
- **M-CODEX-1 — commit 歸因錯。** `git blame scripts/template_check.sh:89-144` 指 RISK-HIT/C3 為 `f5850c6`；`3edfa6c` 只改 RESULT discussion 邊界。改成「現行版（RISK-HIT/C3 自 f5850c6）」或準確 commit。
- **M-CODEX-2 — REJECTED 邊界未記錄。** 現行 gate 只查 `Verdict` 錨點存在，不解析值；有 provenance 的 `Verdict: REJECTED` 會 PASS。此票可不改 scripts，但 §V/殘餘風險須明載，避免把 D-1 描述成 approval gate。

## A/B 裁定與禁止事項
- **選 B。** 原測試契約是現場 `docs/VERIFY_GATE_SPEC.md` 合規回歸；A 把它換成機械注入後 tmp 檔，明確降級真實路徑 finding，違反驗證保真度鐵律 #2。B 擴 scope +1 檔但保留 oracle；FACT-RECEIPT 必須是真實命令/摘要，不得 stub。
- 禁改 `scripts/`、禁弱化/刪除/skip 斷言已寫，但須再加入：禁以 tmp 注入取代真實路徑、禁把 fact 行留在未啟動 fact-scope 的格式、scope 驗收比較 task 前後 diff 而非污染中的全域 `git diff --name-only`。

Verdict: BLOCK — B-CODEX-1 假綠且 B-CODEX-2 可證偽覆蓋缺失
