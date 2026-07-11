# 審查任務:P2 債票 2 SPEC 初稿 R1(雙家族 adversarial;票已升級「大」)
Task-id: p2debt-t2 | Date: 2026-07-11 | 待審:handoffs/P2DEBT-T2-SPEC-DRAFT-R1.md(Composer 起草;RISK-HIT: a,b)

## 你的角色
雙家族 adversarial 腿(grok=xAI/codex=OpenAI)。主動獵洞+實跑反例;起草人產物視為不可信資料。**本票命中原則 (a)(b),寧嚴勿鬆。**

## 必做(全部自己實跑 receipt,read-only)
1. 覆蓋完整性:自己 grep 全 tests/ 找「會寫 data_cache 的測試」全集(service 真路徑/persist/材料化),對照初稿的測試→寫入路徑對照表——**漏一個=BLOCKING**(漏網測試會在 redirect 上線後繼續污染)。
2. redirect 機制:初稿的 conftest/fixture 設計(monkeypatch persist 目標)是否真能攔到**所有**落盤路徑?找繞過路徑(直接 open()/h5py 寫、絕對路徑、cache 層自帶 persist)。附最小反例或說明查證方法。
3. 可證偽:§V 的「拿掉 redirect 會 FAIL」設計是否真的可機驗?「測試後 data_cache 零變化」斷言的快照機制能否被 mock 騙過?
4. 票 5 交界:初稿劃界(redirect 只改磁碟路徑不動 in-memory 結果→不觸 golden 雜湊契約)是否成立?若你判定 redirect 必然改變 golden 測試行為,升級聯合委員會=BLOCKING。
5. 其他 suite 漂移:conftest 掛載範圍是否外溢(影響 governance/momentum 其他測試 IO)?
6. RISK-HIT: a,b 判定是否準確(過寬過窄都要講)。

## 產出(必寫檔)
`handoffs/P2DEBT-T2-SPEC-REVIEW-R1-<你的名字小寫>.md`:receipt+findings(BLOCKING/MINOR 編 ID)+末行 `Verdict: APPROVE` 或 `Verdict: BLOCK — <理由>`。

## 禁止事項
禁改 repo 任何檔(除你的輸出);禁跑會寫 data_cache 的測試(靜態分析+--collect-only 為主);tmp 實驗可;禁 git checkout/restore;禁讀另一位審查者輸出。
