# GOVB1 fixture — fact-verified with head-based count claim

brief-kind: consult

REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: count: `head -5 some.log | wc -l` → 5
assumed: head 截斷後宣稱計數，Task 1.4 應擋。

## 任務

反例：fact-verified 指令含 head 且宣稱 count。
