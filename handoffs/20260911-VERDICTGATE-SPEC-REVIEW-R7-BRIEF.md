# VERDICTGATE SPEC v7 閉合確認（R7）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R7
findings-round: R7

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R7-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R6 提過、v7 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v7**。R6 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r6/synth.md`（V1–V5 全採納；composer 尾碼型 marker 併入 V2；R4 synth Z4 之錯由 V5 具名更正）。

## 🔴 必答
1. **codex**：R6 四條在 v7 是否閉合（重跑：兩參數 ASSERT 計數、helper 契約對 `P16-B5-TASK31-REV`／`P16-B3-STAMP`、首次 push 序列、`y-codex.md` 非 expected path）？**grok**：`GROK-R6-P1-01` 是否閉合（L169 已改 union=3 rc=0 並明寫 `prod_files`）？**composer**：對 V3 `git rev-list HEAD --not --remotes` 獨立找碴——多 remote、fork remote、`--remotes` 含 tag 或 stale remote-tracking ref 時會不會**漏驗**（range 變空）或**過驗**（把已 push 的 commit 又算進來）？給實跑或碼證。
2. **V2 helper 契約**：「候選＝task_id 以 `<root>-b<K>-` 為前綴」——本票自己的 review 命名為 `<root>-x-review-r<N>`（batch=`x`）。`x` 批次的 round 在 helper 下算不算前批？主委立場：`x` 為 SPEC／TODO 審查層，不是實作批，不進 `b<K>` 候選；但 TODO 戳記輪（`x-stamp`）之 `CLOSED` 是否該計入 Task 2.2 解除？給立場。
3. 🔴 **全文互斥掃描**（同 R6 必答 4，v7 又改了 14 處）：Task 之間、C 約束之間、ASSERT 之間是否還有互斥或死文。列出每一處，或宣告「全文無互斥」並附掃描方法。
4. **可否據此生成 TODO**？

## 停輪條件
①必答 1–4 皆有立場；②必答 1（composer）、3 附實跑或掃描方法；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v7，主委 2026-09-11）。
fact-verified: `grep -nE 'verdictgate_check\.sh ROOT [0-9] WHEN' docs/VERDICTGATE_SPEC.md` → 只剩一條「argv 只有兩個 ⇒ rc≠0 印 usage」之負例（主委 2026-09-11）。
fact-verified: R6 三家產出已 `register-output`；round `4674242a` 已 `debt_clear`。
assumed: 本 repo 只有一個 remote（`origin`）⇒ `--not --remotes` 等價 `origin/main..HEAD`＋首次 push 全量 ⇒ 否證觀測：`git remote | wc -l` ≠ 1 或存在 stale remote-tracking ref。／我跑了：**沒跑**。請 composer 必答 1 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
