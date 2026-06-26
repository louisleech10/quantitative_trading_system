# IC Phase 1 1-contract — TODO Adversarial Review 派工指令

> 雙家族各獨立做一次（GPT-5.5 / Composer 2.5），不互看、不自審作者框架。
> 依 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md（V13）。本輪審 TODO（對照已雙審修訂的 SPEC v2）。

## 你要審的檔（全讀，讀不到要說，不得假裝讀過）
- **TODO（本輪主審）**：`docs/IC_PHASE1_CONTRACT_TODO.md`
- SPEC v2（TODO 的來源，已過雙家 adversarial 修訂）：`docs/IC_PHASE1_CONTRACT_SPEC.md`
- 上一輪 SPEC reconcile（看哪些 finding 已納入）：`handoffs/20260626-ic-PHASE1-CONTRACT-ADVERSARIAL-RECONCILE.md`
- Manifest：`handoffs/20260625-ic-PHASE1-CONTRACT-MANIFEST.md`
- 範本：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`

## 變數
- `{{SPEC_FILE}}` = docs/IC_PHASE1_CONTRACT_SPEC.md
- `{{TODO_FILE}}` = docs/IC_PHASE1_CONTRACT_TODO.md
- `{{PLAN_FILE}}` = handoffs/20260624-ic-roadmap-phasing-CONVERGED.md
- `{{REVIEW_FOCUS}}` = TODO 冷啟動可執行性 + 下列重點
- `{{STRICTNESS}}` = MAXIMUM

## 本輪必查（TODO 層 + 確認上輪 finding 真的落地）
1. **冷啟動可執行性（§1.10）**：一個沒讀過 SPEC 的 agent 拿每個 Task 能否直接開寫？實作要點是否 ≥3 含偽碼/簽名、修改檔到函式、邊界 ≥2、驗證有可證偽通過條件？指出任何「貌似有內容但邏輯空」的 Task。
2. **上輪 BLOCKING 是否真落地**（防「修了 SPEC 但 TODO 又漏」）：① WF 無 split() → Task 1.4 是否正確包 `_generate_rolling_splits` 不改 wf？② 單 symbol gap 洩漏 → Task 1.3 是否有 gap 反例 fail-closed 測試？③ CPCV embargo 降級 → Task 1.4 strict 偵測是否可執行（effective vs requested 怎麼算，TODO 寫清楚沒）？④ flag-off byte 不變 → Task 2.2/3.2 是否真不污染 v1 JSON 路徑？
3. **覆蓋追溯**：[C-1..C-12] + R1-R9 是否每項都有對應 Task（抓掉項）。
4. **批次依賴拓撲**（§B）：B1-B5 依賴對嗎？有無 forward dependency（Task 依賴尚未完成的後續批次）？
5. **語義/既有 caller**：Task 2.2 給 ICResult 加欄 → 既有 `_to_json_compatible`/to_dict caller 是否真不受影響（TODO 有標檢查點沒）？Task 3.2 改 get_result → decay/quantile/correlation/grouped/export caller flag-off 是否真不變？
6. **量化正確性殘留**：purge_semantic="rows" 預設留到 1a 改 timedelta——TODO 是否清楚標記這是已知債、且 Phase 1 的 gap 偵測能擋住 rows-purge 的洩漏？
7. **使用者橫向考量**：數據品質/計算時間/計算穩定性/跨 tier(8-32GB)/檔案大小/業界標準——TODO 的 tier 表、artifact 寫入延遲、atomic write 是否足夠可執行。

## 輸出
- 依範本 §輸出格式：Verdict + Findings([BLOCKING|MAJOR|MINOR]+信心度+證據+怎麼失敗+修法) + 被當成事實的未驗證假設。
- **GPT-5.5 寫到**：`handoffs/20260626-ic-PHASE1-CONTRACT-TODO-ADVERSARIAL-CODEX.md`
- **Composer 2.5 寫到**：`handoffs/20260626-ic-PHASE1-CONTRACT-TODO-ADVERSARIAL-CURSOR.md`
- 完成 `STATUS: DONE`，BLOCKED 則 `STATUS: BLOCKED — <原因>`。
