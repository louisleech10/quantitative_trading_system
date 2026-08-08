# GOVB1 fixture — discussion-context must NOT enter fact-verified selector

brief-kind: consult

REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

請依 templates/COMMITTEE_FINDING_TEMPLATE.md 全文照做。

fact-verified: smoke baseline → ok
assumed: 討論語境列不得被選入規則①解析器。

## 任務

反例（修前誤擋、修後須 rc=0）：討論列同時提及宣告關鍵字與計數標記，
且二者皆在反引號內——**非**行首 fact-verified 宣告。

討論語境：規則以 `fact-verified:` 與 `count:` 標記掃描整行。

另：fence 內宣告樣式亦不得進解析器：

```
fact-verified: count: 1 — `head -5 some.log` → 5
```
