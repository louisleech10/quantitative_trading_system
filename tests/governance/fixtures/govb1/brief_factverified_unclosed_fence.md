# GOVB1 fixture — 未閉合 code fence 須 fail-closed（禁吞至 EOF）

brief-kind: consult

REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: smoke before fence → ok
assumed: 未閉合 fence 之後的 active 宣告不得被吞掉而不受檢。

## 未閉合 fence

```
code sample without closing fence
fact-verified: count: 1 — `head -5 some.log` → 5
