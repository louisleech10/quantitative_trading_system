# GOVB1 fixture — even-nested backticks (NEW-CLASS; review-r3)

brief-kind: consult

REF:handoffs/reconcile/20260808-govb1-b3-review-r3/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: count: 2 — `echo outer `date` more`
assumed: 偶數巢狀反引號；配對抽出兩段皆非截斷會假綠，段間 date 須明確拒絕。

## 任務

反例：4 個反引號，序列配對得 `echo outer ` 與 ` more`，皆非截斷 ⇒ 舊判準放行。
Task 1.4 須以段間分隔符有界集合擋下（NEW-CLASS）。
