# B2 修正指派（Composer 2.5 讀此檔執行）

Codex adversarial review 抓到 5 個 BLOCKING 繞過,詳見 `handoffs/20260701-VERIFYGATE-B2-REVIEW-CODEX.md`(逐點附行號+反例)。改 `scripts/verification_claim_check.py` 與 `tests/governance/test_verify_gate.py`。

## BLOCKING 1 — 事故詞彙未進 FAIL 詞表（同義詞繞過）
`探針紅`、`正確紅`、`搞定` 目前只 WARN。前兩者是本事故原文詞彙(METAFIX「也正確紅」),`搞定` 是 operational 完成宣稱。
- 修:把 `正確紅`、`探針紅`、`搞定` 加入**強極性 FAIL 詞表**(operational 語境無 VERIFY → 擋)。
- 保留「未知近似詞→WARN」當長尾 catch-all(reconcile 定案),但已知事故詞彙必須 FAIL,不可只 WARN。
- 順掃 review 反例區有無其他該收的(如 `全綠` 已擋、`驗證通過` 已擋,確認一致)。

## BLOCKING 2 — inline discussion 註解壓掉 operational
`- <!-- claim-context: discussion --> align mutation 已驗真紅` 目前 exit 0。
- 修:`claim-context: discussion` **只**在 fenced code block 或 blockquote(`>`)區塊生效;**不得**讓 inline 於 operational bullet/狀態段的註解免責。operational block 內含此註解仍須檢查該 claim。

## BLOCKING 3 — 討論檔名 = 全檔免責
`FORENSICS/DELIB/RECONCILE/ADV-` 檔名目前讓 `## 已完成` operational 也放行。**違反 reconcile 裁定**(檔名至多弱訊號,不可單獨免責)。
- 修:檔名**不可**單獨當 discussion 免責;判定以**局部結構+極性/citation**為主。這些檔內的 operational 新 claim(無 VERIFY)仍須擋。
- **關鍵張力(必解,否則弄破 V7)**:forensic/DELIB 檔滿是「引號內/歸屬他人」的『已驗/真紅』原文——這些是 **citation 非作者新宣稱**,移除檔名免責後仍須放行。判定 citation(放行)的規則,滿足任一即是:
  (a) 在 fenced code block 或 `>` blockquote 內;
  (b) 極性詞被**引號**包住(『』「」""'' 等);
  (c) 句子**歸屬他人或否定/檢討**該 claim(含 `把…寫成`/`宣稱`/`不實`/`假`/`SUPERSEDED`/`事故`/`捏造`/`誤讀` 等標記)。
  否則視為 operational 新 claim。
- **對照 V17 vs V7**:V17 事故 fixture 『對齊 mutation 已驗 ✅ 真紅(babu8o07p)』的 `真紅` **不在**引號內、無歸屬否定 → 擋;forensic 檔『babu8o07p 把「已跑」寫成「已驗真紅」』的 `已驗真紅` **在引號內+有「把…寫成」歸屬** → citation 放行。此區分即 (b)(c) 的目的。

## BLOCKING 4 — scope 交集太寬(共用檔路徑撐錯 node)
receipt `selected_node_ids=[tests/x.py::test_mutation_align]` 竟能撐 `center mutation 真紅 VERIFY:r-align tests/x.py::test_mutation_center`(exit 0)。根因:`_extract_scope` 併入 `tests/x.py`,`_scope_intersects` 接受 substring 重疊。
- 修:當 claim 引用到 **node-id**(含 `::`)時,scope 交集須**比對 node-id 全等/後綴**,不可只靠共用檔路徑放行。檔路徑層級的交集不足以支撐指定 node 的 claim。

## BLOCKING 5 — pending ledger 接受偽 close
close 事件目前不驗 fingerprint/scope/runtime/receipt provenance,任意 append 假 close 就關閉 pending。
- 修:close 關閉 pending 須同時滿足:exact `pending_id` + `claim_fingerprint` 相符 + `required_runtime_class`/node scope 相符 + `receipt_id` 對應**真實存在且有審計事件**的 receipt。不符則 pending 仍 open(擋該 task DONE)。

## 測試(每項補回歸,可證偽)
- `探針紅/正確紅/搞定` operational 無 VERIFY → exit1。
- inline `claim-context: discussion` 於 operational bullet → exit1。
- discussion 檔名(FORENSICS 等)內 `## 已完成` operational 無 VERIFY → exit1。
- 重用 VERIFY 但 node-id 不符(僅共用檔路徑)→ 該 claim exit1。
- 偽 pending close(錯 fingerprint/無真 receipt)→ 該 task DONE 仍被擋(修正既有 test_verify_gate.py:560-573 那個把偽 close 當允許的測試)。
- **不得回歸**:V7 誤報=0 仍須成立——修完再跑 `verification_claim_check.py --files docs/VERIFY_GATE_SPEC.md handoffs/*FORENSICS*.md handoffs/*DELIB*.md docs/VERIFY_GATE_SPEC_PLAIN*.md` → exit 0(discussion/引號原文不因 BLOCKING 3 修正而被誤擋;真原文在 fenced/quote/引用結構內)。

## 驗證(收尾附原文)
1. `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` 全綠。
2. 上述 V7 專項 exit 0 原文。
3. 跑測試前後真實路徑(run_receipts/verify_audit.log/pending jsonl)零污染。
## 規則
僅標準庫;venv/bin/python;不 import momentum/api。結構化收尾(TESTS_RUN 貼 pytest+V7 exit 原文/FAILURES_SEEN/SCOPE_CHANGES);報告勿用「已驗/真紅」字樣。
