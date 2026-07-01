# B2 實作指派（Composer 2.5 讀此檔執行）

實作驗收防偽閘 **Batch B2** = `docs/VERIFY_GATE_TODO.md` 的 **Task 2.1 + Task 2.2**（完整規格與偽碼在該 TODO,務必逐條讀）。依賴 B1 已完成的 `scripts/run_with_receipt.py`(產 receipt + `.claude/gate/verify_audit.log` 審計事件,含 command_sha256/receipt_sha256/log_sha256/runtime_class/selected_node_ids)。

## Task 2.1 — `scripts/verification_claim_check.py`（claim-object 偵測；核心）
依 TODO Task 2.1 全部 9 個實作要點:normalize(NFKC+strip ZWSP+統一 hyphen/空白)→段切分→claim-object 抽取(polarity/scope/runtime_expectation/source_context/backing)→模式判定(citation/supersede/discussion/operational)→`check_backing`(receipt 存在+已tracked/staged+審計事件+重算 sha256 比對+極性符+runtime_class 不可用 static/helper 撐 runtime/mutation+scope 交集)→`claim_fingerprint`→VERIFY-EXEMPT 窄類別(HANDOFF operational/commit/RESULT 零豁免)→未知近似詞 WARN。
CLI:`[--staged | --files f... | --range A...B | --commit-msg FILE]`;掃 HANDOFF.md/handoffs/*.md/docs/*.md/commit-msg。

## Task 2.2 — pending ledger `handoffs/pending_verifications.jsonl`
依 TODO Task 2.2:reducer 求未結;open/close 事件格式;`list-open` 子指令;同 task 有未結 pending → 擋該 task「已驗/DONE/ready」claim。

## 測試（tests/governance/test_verify_gate.py 追加）
實作 TODO 列的 V2-V11 + V17,每項一測,務必**可證偽**(非 assert True)。特別:
- **V7 誤報=0(進 B3 的硬性關卡)**:本 repo 既有檔中的合法「已驗/真紅」原文——`docs/VERIFY_GATE_SPEC.md`、`handoffs/*FORENSICS*`、`handoffs/*DELIB*`、`docs/VERIFY_GATE_SPEC_PLAIN*.md` 內 fenced/引號/討論語境——**必須全部不被誤擋**;`\`42 passed\``、`passed through`、`通過層 6.5` 不誤擋。
- **V17 事故 byte fixture**:`已驗 ✅ … 真紅(babu8o07p)`、`已驗(babu8o07p):對齊 mutation 真紅`、METAFIX `也正確紅` 這類 operational 無 VERIFY → **必擋**。
- mutation 探針:移掉 check_backing 的審計事件驗證 → V6(手寫 receipt 無審計事件應擋)須轉綠=證有牙齒。
- **測試隔離(承 B1 教訓)**:用 `VERIFY_GATE_RECEIPTS_DIR`/`VERIFY_GATE_AUDIT_LOG` env + tmp_path,測試**不得污染**真實 `handoffs/run_receipts/`、`.claude/gate/verify_audit.log`、`handoffs/pending_verifications.jsonl`;checker 掃描目標也用 tmp fixture 檔,不掃真實 repo 檔。

## 驗證（收尾附原文）
1. `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` 全綠。
2. **V7 專項**:實跑 `verification_claim_check.py --files docs/VERIFY_GATE_SPEC.md handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md docs/VERIFY_GATE_SPEC_PLAIN.md` → **exit 0(誤報=0)**;貼原文輸出。
3. 跑測試前後 `git status --porcelain handoffs/run_receipts/ .claude/gate/verify_audit.log handoffs/pending_verifications.jsonl` → 無改動。

## 規則
- 僅標準庫;venv/bin/python;不 import momentum/api。誠實邊界寫進 docstring(router 非 judge)。
- 結構化收尾:TESTS_RUN(貼 pytest summary + V7 專項 exit code 原文)、FAILURES_SEEN、SCOPE_CHANGES。報告勿用「已驗/真紅」字樣。
- **不要**在本批動 PreToolUse/git hook/CI(那是 B3);本批只交付 checker + ledger + 測試。
