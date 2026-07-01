# B2 code review 指派（Codex 讀此檔執行）

Composer 已實作 Batch B2:`scripts/verification_claim_check.py`(claim-object 偵測)、`handoffs/pending_verifications.jsonl`(ledger)、`tests/governance/test_verify_gate.py`(追加 V2-V11/V17/mutation)。對照 `docs/VERIFY_GATE_SPEC.md` P2 與 `docs/VERIFY_GATE_TODO.md` Task 2.1/2.2。

這是全閘偵測核心,請做 **adversarial code review**——目標是**攻破 checker**,不是認同。逐項查:

1. **繞過手法(reconcile §3 列過的)**:同義詞/改詞(「正確紅」「探針紅」「驗證通過」「全綠」「搞定」)、拆段(claim 與 VERIFY 拆不同 block)、unicode/零寬/全形、HTML comment 包整段 operational、VERIFY-EXEMPT 濫用(HANDOFF operational/commit/RESULT 應零豁免——真的擋了嗎?)。逐一實跑構造反例。
2. **backing 偽造**:手寫 receipt 無審計事件→是否真擋?事後改 receipt JSON 擴 scope(改 selected_node_ids)但不動審計事件→check 是否重算 sha256 比對抓到?worktree-only(未 staged/tracked)receipt 撐已 commit claim→擋?
3. **快測冒充慢測(V4)**:static_only/helper_smoke receipt 撐「mutation/runtime/慢測/真跑」claim → 真擋?
4. **同段多 claim**:一 receipt 只覆蓋其中一個 scope,其餘 claim 是否仍 FAIL?
5. **claim_fingerprint** 公式是否一致(供 #6/ledger),可否被規避。
6. **pending ledger**:close 是否須對 exact pending_id?任意 append 偽 close 可否繞?race/陳舊?
7. **�feature誤報=0**:實跑 `verification_claim_check.py --files docs/VERIFY_GATE_SPEC.md handoffs/*FORENSICS*.md handoffs/*DELIB*.md docs/VERIFY_GATE_SPEC_PLAIN*.md` → 應 exit 0(討論/引號不誤擋)。若誤擋任一 = BLOCKING。
8. **測試品質**:斷言可證偽非 assert True?mutation 探針真有牙齒(移守衛→對應測試轉綠)?測試隔離(不碰真實 run_receipts/verify_audit.log/pending jsonl)?
9. 僅標準庫、不 import momentum/api、空殼/邊界漏洞。

跑 `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q`。逐點 CONFIRM/BLOCKING/MAJOR/MINOR + 具體反例證據(行號/實跑輸出)。VERDICT: APPROVED 或 CHANGES-REQUESTED。寫 `handoffs/20260701-VERIFYGATE-B2-REVIEW-CODEX.md`。
