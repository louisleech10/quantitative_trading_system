# 第二輪交叉詰問 BRIEF — Template 審查（2026-07-04）

四方獨立審查已收齊。本輪**解除獨立性限制**：請讀全部四份 review 後作答。
- Claude 版：`handoffs/2026-07-04-template-review-claude.md`
- Codex 版：`handoffs/2026-07-04-template-review-codex.md`
- Composer 版：`handoffs/2026-07-04-template-review-composer.md`
- Gemini 版：附於本檔末（read-only 委員，stdout 收錄）

## 已定案（Composer 反例探針實證 + Claude 覆核，不必重辯，除非你有反證）
- **U1 [BLOCKING]** FACT-RECEIPT 範本↔機檢漂移＋「已驗證事實」完全繞過（探針 `/tmp/spec_verified_bypass.md` PASS 不應）
- **U2 [BLOCKING]** §RISK↔§G 脫鉤，高風險可 §N 標 N/A 逃 Golden（探針 PASS 不應）
- **U3 [MAJOR]** TODO per-Task 三欄僅全域 grep（探針 PASS 不應）
- **U11 [MAJOR]** 治理文件殘留 §1.0/§1.4 舊錨點（Claude 已 grep 證實 gate.sh:254、CLAUDE.md:41 等 6 處）
- **U13 [MINOR]** 「待使用者確認：本任務無」regex 誤擋（Claude 已實跑 NO MATCH 證實）

## 待詰問題（逐題作答，AGREE/DISAGREE + 理由；DISAGREE 須附反證或反例）

**Q1（Claude 獨有 CL-2）**：adversarial review prompt 是否應加強制條款「§A 宣稱事實凡可低成本核實（grep/讀真實檔/一行 python）者，reviewer 必須實際執行並附輸出；無法執行則標『未經覆核』且相關 finding 不得低於 MAJOR」？Composer 本輪用行動證明了實跑反例的價值（三個探針），但沒人把它寫成對 prompt 的要求。若 AGREE，給出你認為的最小可行條款文字。

**Q2（閉合機制群：CL-3 + Composer C-13 + Gemini PREMISE-1）**：三方都指向「findings 落地無強制」但修法不同——(a) 每 finding 附穩定 ID + RECHECK 可重跑命令，原提出方修後重跑；(b) gate 輕量 grep Verdict + 無未處理 BLOCKING；(c) reconcile 須附 `[Finding ID] → [已修 SPEC 章節]` 對映表供機檢。三者可組合。請給你認為**最小充分**的組合與機檢實作成本評估。

**Q3（Claude 獨有 CL-4）**：SPEC §V 是否應加一行強制引用 `docs/TEST_DESIGN_CHARTER.md`（聲稱驗正確性的測試須附 mutation/可證偽設計），把 RESULT 的 MUTATION_CHECK 欄位接上上游？還是這屬過度工程？

**Q4（憲法瘦身，三案並立）**：TODO 階段 0「無條件讀 copilot-instructions(739行)+ARCHITECTURE(1989行)+DEVELOPMENT_GUIDE(2407行)」如何改？(a) Codex 案：另立短 canonical 憲法摘要檔；(b) Composer 案：改讀 `AGENTS.md`+按需節選（並指出 copilot 檔與執行端合約分叉問題）；(c) Gemini 案：輕量 CODING_STANDARDS + ARCHITECTURE 僅跨模組變更才讀。選一並說明如何不重開「沒讀憲法」事故面。

**Q5（反駁機會）**：四份 review 中你認為**錯誤或過度**的 finding？逐條點名+理由。特別請檢視：severity 校準（哪些真值 BLOCKING）、Codex C8（SPEC ID→TODO 追溯模式）是否與現行 manifest 慣例重複、Composer C-6（RESULT vs ASSUMPTIONS 雙軌）的實際衝突面。

**Q6（優先序）**：給你的 top-5 修補順序（用 U 編號或原 finding ID）。

## 輸出格式
逐題 `Q1: AGREE/DISAGREE/PARTIAL — 理由(≤5行)`；Q5 逐條；Q6 一行列表。文末 `STATUS: DONE`。

---
## 附：Gemini 獨立審查全文（節錄要點）
- DRIFT-1[BLOCKING]=U1；DRIFT-2[MAJOR]=U3；DRIFT-3[MINOR]=U13
- PREMISE-1[MAJOR]：reconcile 落地無強制（狐狸審雞窩）→ 修法：`[Finding ID]→[已修章節]` 對映表或第三方確認
- PREMISE-2[MAJOR]：coverage 可被「跳過清單」游走（ID 出現即 PASS）→ 修法：ID 限標題行
- PREMISE-3[SUGGESTION]：「驗證：確認有 1 個檔案」含數字即過反空殼 → adversarial §2 加假證偽例示
- TOKEN-1[MAJOR]=U5：ARCHITECTURE 全讀改按需
- 不可砍：階段1 覆蓋追溯、雙家族 adversarial、gate 錨點機檢
