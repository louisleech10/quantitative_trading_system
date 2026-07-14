# IC1C SPEC r2 閉合重驗任務書(task-id: IC1C-SPECREV)

你是 r1 的原審查委員。任務=驗證你在 `handoffs/20260714-IC1C-SPECREV-<你>.md` 提出的每個 finding 在 **SPEC r2**(`docs/IC1C_NETIC_SPEC.md` v0.2)是否真關閉(章程 §B8:原提出方重跑同一反例,不憑「已修」信任)。

**輸入**:SPEC r2 全文、`handoffs/20260714-IC1C-SPECREV-RECONCILE.md`(17 筆裁決表)、你的 r1 檔。

**必做**:
1. 逐一你的 finding:引 r2 對應段落,判 CLOSED / STILL-OPEN(附殘留反例)/ PARTIALLY(說明缺口)。r1 的可證偽反例在 r2 條文下是否仍構造得出來?
2. 檢查 RECONCILE 裁決有無曲解你的 finding(尤其 codex 的 F1 fail-closed 拆票 1c-FR、F3 去 ×2、F11 持有期矩陣不入 1c)。
3. 掃 r2 新引入的洞(新 schema/新 phase 依賴/§T 語意)——新 finding 用 `<你>-R2-n` 編號。
4. 產出寫 `handoffs/20260714-IC1C-SPECREV-R2-<你 codex|composer|grok>.md`(grok 印 stdout 由編排端落檔)。
5. 末尾兩行:`SPEC-REVIEW-R2: APPROVE|REJECT(n BLOCKING)`;若 APPROVE 另附一行 `RECONCILE-STAMP APPROVED — <你> 2026-07-14 sha256:<handoffs/20260714-IC1C-SPECREV-RECONCILE.md 的 sha256,用 shasum -a 256 算>`。

**約束**:唯讀(除產出檔);兩輪解不了記 finding 勿硬猜。
