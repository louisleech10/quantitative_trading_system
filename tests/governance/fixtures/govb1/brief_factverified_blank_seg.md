# GOVB1 fixture — blank command segment inside backticks (COMPOSER-R3-P3-00)

brief-kind: consult

REF:handoffs/reconcile/20260808-govb1-b3-review-r3/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: count: 1 — `   `
assumed: 純空白指令段；trim 後為空須視同零抽取明確拒絕。

## 任務

反例：count: 列反引號內僅空白。舊路徑 A 抽出非空字串（含空白）會假綠。
Task 1.4 須 trim 後空 ⇒ 明確拒絕。
