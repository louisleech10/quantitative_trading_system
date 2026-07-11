# 改稿任務:P2 債票 1 SPEC R2(Composer 回改)
Task-id: p2debt-t1 | Date: 2026-07-11 | 前置:R1 雙 BLOCK(grok+codex 收斂,無衝突)

## 你要做的
讀你的初稿 `handoffs/P2DEBT-T1-SPEC-DRAFT-R1.md` 與兩份審查:
- `handoffs/P2DEBT-T1-SPEC-REVIEW-R1-grok.md`(G-B1/G-B2/G-B3+建議修正最小集 §8)
- `handoffs/P2DEBT-T1-SPEC-REVIEW-R1-codex.md`(B-CODEX-1/2+M-CODEX-1/2)

產出 `handoffs/P2DEBT-T1-SPEC-DRAFT-R2.md`(全量新稿,非 patch),逐項閉合:

### 綁定修正(主委整併,雙家 BLOCKING 全收)
1. **B5 fact-scope 狀態機對齊**(G-B1~B3=B-CODEX-1):四個內聯 fixture 的 §A「已確認」行改為檢查器可觸發的 canonical 形狀(`- **已確認**:`);兩個負測=canonical+**無** receipt(必 FAIL 且 stdout 含 FACT-RECEIPT);兩個正測=canonical+**有** receipt(必 PASS);pending 測試僅補 RISK-HIT。刪除「補 RISK-HIT 即恢復斷言」敘事。每個遷移後 fixture 附你在 tmp 實跑的 template_check receipt(rc+關鍵行)。
2. **可證偽負例入 §V 並落到測試清單**(B-CODEX-2):至少三個顯式負例=①缺 RISK-HIT 必 FAIL ②`VERDICT:` 全大寫必 FAIL(釘住大小寫語意)③正例移除 FACT-RECEIPT 必 FAIL。寫明對應測試函式名與檔案。
3. **鎖定 B 案**(兩家一致):`docs/VERIFY_GATE_SPEC.md` 補 `RISK-HIT: b` + 2 條**真實非 stub** FACT-RECEIPT(指向真命令/摘要或 SIGNOFF 鏈);測試不變仍對真實路徑 assert。scope 例外正式列入 §C(委員會已核=本輪雙審一致)。
4. **commit 歸因訂正**(M-CODEX-1):RISK-HIT/C3 出自 `f5850c6`(以 git blame 自證),3edfa6c 只改 RESULT discussion 邊界;§A 根因節同步改。
5. **殘餘風險登記**(M-CODEX-2):§V 明載現行 gate 只驗 `Verdict` 錨點存在不解析值(`Verdict: REJECTED`+provenance 會 PASS);本票不改 scripts,列殘餘風險非 bug。
6. **禁止事項補三條**(codex):禁 tmp 注入取代真實路徑回歸;禁 fact 行留在非 canonical fact-scope 格式;scope 驗收=task 前後 diff 對比,非全域 git diff。

## 產出末行
`R2-CLOSURE: <逐 finding ID 一行對應處置>`;不加 RECONCILE-STAMP(那是審查方複驗後 append)。

## 禁止事項
禁改 repo 任何檔(除 R2 草稿檔);試跑一律 tmp;禁 git checkout/restore;禁寫 data_cache。
