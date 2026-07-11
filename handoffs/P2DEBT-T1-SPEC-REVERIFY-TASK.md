# 複驗任務:P2 債票 1 SPEC R2(原提出方閉合複驗,章程§B8)
Task-id: p2debt-t1 | Date: 2026-07-11 | 待驗:handoffs/P2DEBT-T1-SPEC-DRAFT-R2.md

## 你的角色
你是 R1 BLOCK findings 的原提出方(grok=G-B1~B3+G-M*;codex=B-CODEX-1/2+M-CODEX-1/2)。複驗規則:**重跑你自己 R1 的同一反例**,確認按 R2 修法清單施工後反例真的關閉且可證偽,不憑「已修」字樣信任。

## 必做
1. 讀 R2 全稿+末行 R2-CLOSURE,對照你的 R1 review(可讀自己的,仍禁讀對方的複驗輸出)。
2. 逐個你的 finding:在 tmp 按 R2 的遷移內容手工做出 fixture/檔案,重跑你 R1 用的同一反例命令:
   - 你若提過 B5 假綠反例:canonical `- **已確認**:` 無 receipt 必 FAIL、有 receipt 必 PASS,親跑 template_check 證實。
   - 你若提過可證偽缺口:確認 R2 新增負例測試(uppercase VERDICT/缺 RISK-HIT/移除 FACT-RECEIPT)的函式與斷言設計真的「改壞會 FAIL」。
   - B 案:確認 R2 對 docs/VERIFY_GATE_SPEC.md 的錨點設計(RISK-HIT: b+真實 FACT-RECEIPT)在 tmp 副本可 TEMPLATE PASS 且非 stub。
3. 檢查 R2 是否引入新問題(改稿常見:修 A 壞 B)。
4. 若全部關閉:在你的輸出檔末尾 append `RECONCILE-STAMP APPROVED (p2debt-t1 R2, <你名>, 2026-07-11)`。

## 產出(必寫檔)
`handoffs/P2DEBT-T1-SPEC-REVERIFY-<你的名字小寫>.md`:逐 finding 複驗 receipt(命令+rc+關鍵行)→ CLOSED/STILL-OPEN;新 findings(若有);末行 `Verdict: APPROVE`(+STAMP)或 `Verdict: BLOCK — <理由>`。

## 禁止事項
禁改 repo 任何檔(除你的複驗輸出檔);試跑一律 tmp;禁 git checkout/restore;禁寫 data_cache;禁讀對方複驗輸出。
