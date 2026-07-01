# B1 修正指派（Composer 2.5 讀此檔執行）

你的 B1 實作被 Codex review 抓到問題，詳見 `handoffs/20260701-VERIFYGATE-B1-REVIEW-CODEX.md`（逐點附行號證據）。修下列，改 `scripts/run_with_receipt.py` 與 `tests/governance/test_verify_gate.py`。

## BLOCKING 1 — node-id 分類 + selected_node_ids
`runtime_class` 推導目前只看 `-k test_mutation_`，漏了 node-id 式（引號內）"::test_mutation_"；且 selected_node_ids 永遠是空 list。
- 修 ①：偵測 argv 或 pytest 輸出中的 node-id（含 "::test_mutation_"）→ 歸類 mutation_runtime。
- 修 ②：實際填 selected_node_ids —— 從 pytest 輸出的 PASSED/FAILED 行解析 node id，或從 argv 的 node-id 參數解析。

## BLOCKING 2 — 不存在的命令要仍產 receipt
不存在的命令目前使 FileNotFoundError 逃逸、沒產 receipt。
- 修：用 try/except 包住 subprocess 啟動；命令找不到 → 仍寫 receipt（exit_code 設 127）+ log 記 "command not found"，wrapper 以非 0 exit 收場。（對應 TODO Task 1.1 邊界①）

## BLOCKING 3 — audit 契約測試不足
audit-chain 測試只查 event/receipt_id/log_sha256/emitter，沒鎖住 B2 checker 要信任的欄位。
- 修 tests：斷言審計事件含且等於 command_sha256、receipt_sha256、exit_code、runtime_class；並**從 receipt 檔重算 sha256，斷言等於審計事件的 receipt_sha256**（防事後改 receipt 擴權）。

## NON-BLOCKING 4 — requested_class 不覆蓋
加一個測試：用 requested-class 參數傳 mutation_runtime、實際跑 python 印字串（非測試）→ receipt 的 runtime_class 仍須是 static_only（證 requested 不覆蓋推導）。

## NON-BLOCKING 5 — mutation 探針強化
把 test_mutation_receipt_missing_field_fails 改為：mutate 後呼叫**production** 的 validate_receipt_schema()（非只 test helper），確認 raise。

## 完成後
1. 跑 venv/bin/python -m pytest tests/governance/test_verify_gate.py -q （全部）。
2. 手動驗證兩條路徑：
   - 用 run_with_receipt.py 跑一個真的 mutation node-id 測試 → 確認 receipt 的 runtime_class 是 mutation_runtime 且 selected_node_ids 非空。
   - 用 run_with_receipt.py 跑一個不存在的命令 → 確認仍產出 receipt（exit_code 127）。
3. 規則：僅標準庫；venv/bin/python；不 import momentum 或 api。
4. 結構化收尾：TESTS_RUN（貼 pytest summary 原文）、FAILURES_SEEN、SCOPE_CHANGES。報告中請勿使用「已驗 / 真紅」等字樣（避免污染交接文件），只陳述跑了什麼命令與 pytest 原始輸出。
