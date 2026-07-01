# B4+B5 六 BLOCKING 修補指派（Composer 2.5 讀此檔執行）

Codex adversarial review 抓 6 BLOCKING，全附行號+已實跑反例：**逐字讀 `handoffs/20260702-VERIFYGATE-B4B5-REVIEW-CODEX.md`**（含 Suggested fix），據以修補。規格底稿 `docs/VERIFY_GATE_TODO.md` Task 4.1-4.4/5.1-5.3。

## 修補範圍（僅此 6 項 + 對應測試補牙）
1. **B4-1**（`scripts/gate.sh`）：high-risk 非 waived `--adversarial` 改 fail-closed——路徑須是 reconcile（過 `reconcile_stamps_check.sh`）或 ADV 檔（過 `verify_task_provenance.py`），其他一律拒發 token。補測試:非 ADV 任意路徑 → gate 拒。
2. **B4-2**（`scripts/verify_task_provenance.py`）：廢除日期式 grandfather，改**顯式 allowlist**（已知 legacy reconcile 的 (file,family,task_id,body_hash) 元組;現役= `handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` 等既有已戳記檔）。補測試:新檔回填舊日期戳記 → 拒。
3. **B5-1**（`scripts/verification_claim_check.py`）：RESULT 枚舉/必填欄/RECEIPTS 格式驗證移入 `check_result_structured_fields()`（checker 主路徑直接擋,不依賴另跑 template_check）。補測試:`RUNTIME_CHECK=ok` → checker rc≠0。
4. **B5-2**（`scripts/verification_claim_check.py` fingerprint）：fingerprint 改用 canonical 主題項（normalized scope+runtime_expectation+task_id），剝除 VERIFY:/SUPERSEDED:/receipt id/極性詞/計數。**補整合測試:真實 markdown 檔（非手構 ClaimObject）先綠後紅 → 未標 SUPERSEDED 擋、標了放行**。
5. **B5-3**（`scripts/template_check.sh` W1）：FACT-RECEIPT 判定詞彙擴到指令輸出類（pytest/bash/python/exit/rc=/stdout/輸出/印出/passed/failed/sha256…）。補回歸測試:指令輸出型「已確認」無 FACT-RECEIPT → FAIL。
6. **B4-3**（信任工件清理）：刪 `handoffs/run_receipts/*mutation-test_b4*`（8 檔）並從 `.claude/gate/verify_audit.log` 移除對應 4 筆合成事件（該 log 目前僅此 4 筆=清空回 committed 狀態）。fixture 證據一律留在測試隔離路徑。

## 不可做
- 不弱化任何既有檢查;不動 B1/B2 已 commit 行為(除上述修點);不碰 momentum//api/;不做 B3。
- 修後**全部既有回歸須仍 PASS**:`pytest tests/governance/ -q` 全綠;`reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` PASS;`template_check.sh spec|todo docs/VERIFY_GATE_*.md` PASS;gate.sh 正常 dispatch 路徑(reconcile adversarial)不受影響。

## 收尾
寫 `handoffs/20260702-VERIFYGATE-B4B5-FIX-composer.md`（TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES;逐 finding 列修了什麼+新測試名）。報告勿用「已驗/真紅」字樣。最後輸出一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
