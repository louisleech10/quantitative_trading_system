# 起草任務:P2 債票 1 SPEC 初稿(governance 9 紅 fixture 遷移)
Task-id: p2debt-t1 | Date: 2026-07-11 | 起草人: Composer(四調行:實作型 SPEC/TODO 初稿=Composer)

## 背景(自己驗證,不可只信本檔)
`venv/bin/python -m pytest tests/governance -q` → 9 failed, 140 passed:
- test_verify_gate_b4.py ×3(gate_adversarial rejects/passes 系列)
- test_verify_gate_b5.py ×5(spec fact_receipt 系列)
- test_verify_gate_redteam.py ×1(test_r7_gate_task_id_appends_committee_dispatch)
根因(已裁定,出處 HANDOFF 票 1):2026-07-05 制度強化(template_check.sh 3edfa6c 等)後,fixture 斷言舊行為過期。**修法方向已定:遷移 fixture 至現行檢查器語意;禁放鬆檢查器換綠。**

## 你要做的
1. 偵察:逐一跑 9 紅、讀 fail 輸出,對照 `scripts/template_check.sh`/`scripts/gate.sh` 現行語意與 `git log --oneline -5 -- scripts/template_check.sh scripts/gate.sh`,判定每顆紅=fixture 缺什麼錨點/欄位(例:§RISK 缺 RISK-HIT、adversarial 檔缺 Verdict 行)。
2. 起草 SPEC 初稿寫入 `handoffs/P2DEBT-T1-SPEC-DRAFT-R1.md`,結構依 `templates/SPEC_TEMPLATE.md`,必含:
   - §A fact-scope:每顆紅的實跑 receipt(命令+關鍵輸出行)——驗證保真度鐵律,型別/形狀/語意主張須附實跑。
   - 修法清單:每個 fixture 檔的具體遷移內容(補哪些錨點/行),明列「禁改 scripts/ 檢查器」為硬邊界(唯一例外=發現檢查器真 bug,須另立 finding 交委員會,不得順手改)。
   - 測試章程節(docs/TEST_DESIGN_CHARTER.md):遷移後 fixture 仍須可證偽——斷言「檢查器擋壞輸入」的測試要真給壞輸入。
   - 驗收命令:`venv/bin/python -m pytest tests/governance -q` → 0 failed;且不得動 tests/governance 以外與 scripts/ 檔。
3. RISK-HIT: none(測試 fixture 遷移,不命中 a-d)——若偵察發現實際命中(例:須改共用 conftest),明寫升級訊號。

## 禁止事項
- 禁改任何 repo 檔(除 handoffs/P2DEBT-T1-SPEC-DRAFT-R1.md)。
- 禁 git checkout/restore;禁跑寫 data_cache 的命令。
- SPEC 初稿只是草案:兩家非作者(Grok+Codex)審後才正式化,你不得自審自過。
