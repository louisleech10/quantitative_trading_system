# R2 閉合複驗派工:1-align SPEC/TODO v2(task-id: ic1a-align-specadv-r2)

你是 R1 adversarial 的**原提出方**。SPEC/TODO 已依你們雙家族 R1 findings 全面改版(v2):

- SPEC=docs/IC_PHASE1_1A_ALIGN_SPEC.md(§ADV-RESOLUTION 有逐項裁決對照表)
- TODO=docs/IC_PHASE1_1A_ALIGN_TODO.md
- 你的 R1:handoffs/IC1A-ALIGN-SPECADV-codex.md(Codex)/ handoffs/IC1A-ALIGN-SPECADV-composer.md(Composer)

## 任務(閉合複驗鐵律:原提出方重跑同一反例,不憑「已修」信任)
1. 逐條檢查**你自己**在 R1 提的每個 BLOCKING/MAJOR:v2 的修法是否真閉合?判斷依據=重跑你 R1 的同一反例/receipt(如 kline gap 腳本、roundtrip index 型別實跑、event_filter TypeError snippet),對照 v2 條文是否涵蓋該反例。
2. v2 的新增裁決(D-1 int64 相容/D-2 bar-ordinal/D-3 兩段 freq/Task 1.2 horizon resolver/Task 2.4 event_filter 適配/M5 雙腿)有沒有**引入新洞**?
3. 每條結論:`R1-ID / CLOSED|STILL-OPEN|NEW-ISSUE / 依據(重跑 receipt 或條文對照)`。
4. 結尾:`VERDICT: APPROVE|REJECT`(任一 STILL-OPEN/NEW-ISSUE BLOCKING 即 REJECT);若 APPROVE 且你同意凍結,**另起一行輸出**:`RECONCILE-STAMP APPROVED <你的名字> 2026-07-08`。

## 產出
`handoffs/IC1A-ALIGN-SPECADV-R2-<codex|composer>.md`。只讀+寫自己輸出檔;不改生產 code/測試;不 git checkout tracked 檔。
