# GOVB1 fixture — multi-backtick count claim with early trunc

brief-kind: consult

REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: count: 2 — `head -5 some.log`；`echo stable`
assumed: 較早反引號含 head 截斷；舊 _extract_cmd 只取末組會假綠。

## 任務

反例：count: 列含多組反引號，首組為 head 截斷、末組無害。
Task 1.4 須逐一抽取並擋下（CODEX-R1-P1-03）。
