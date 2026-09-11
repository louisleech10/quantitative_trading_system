# VERDICTGATE SPEC v5 閉合確認（R5）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R5
findings-round: R5

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R5-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R4 提過、v5 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v5**。R4 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r4/synth.md`（群集 Z1–Z5，codex 五條全採納；Z4 採較嚴版）。

## 🔴 必答
1. **codex**：你 R4 的每一條在 v5 是否閉合？重跑你的四組事件序模擬（token 追認、b1 未用 token、descoped、amend）。**composer／grok**：R4 你們 `proceed`；請對 v5 之 Z4「被消費的 token 才是錨」與 Z3 `ticket_commit.token_fresh` 獨立找碴。
2. **Z4 語意**：錨＝「`impl_token_issued` 且其後有同 `<root>/b<N>` 之 `ticket_commit.token_fresh=true`」。構造：主委領 b2 token → 打一個**只改一行**的 batch commit（消費 token）→ small×3 → small×3 → push。第二波 small 在窗內（自消費 token 起）⇒ 6 ⇒ 擋？請確認；並給一個 v5 仍擋不住的序列，或宣告無。
3. **Z3 `token_fresh` 由 post-commit 讀 token 檔 mtime**：`.claude/gate/impl.<root>-b<N>.token` 可被 `touch` 延長 mtime（`GATE-TOKEN-BINDING` 已知坑）。這是否讓 Z3 空轉？主委立場：`touch` 屬蓄意繞過，與 `--no-verify` 同族（§N 第一條），不另立閘；但 `impl_token_issued` 事件的 audit append 序 vs `ticket_commit` append 序**可**機械驗（token 事件必在 commit 事件之前、且兩者相距 ≤900s 之 `ts`）——是否該以此取代 mtime？給立場。
4. **Z5 `brief_kind`**：上線前 round 以 task_id 含 `-REVIEW-` 判為唯一例外。`grep -c '"event": "committee_round_open"' .claude/gate/audit.log` 中 task_id 不含 `-REVIEW-`／`-CONSULT-`／`-STAMP-`／`-CLOSURE-`／`-IMPL-` 的有幾筆？（實跑）若非零，例外規則會把它們判成什麼？
5. **Z1 family 由檔名尾碼解析**：`handoffs/<x>-<family>.md` 慣例是否**全庫一致**？實跑 `ls handoffs/*-review-*.md | grep -vE -- '-(codex|composer|grok|claude)\.md$'` 報數。
6. **可否據此生成 TODO**？

## 停輪條件
①必答 1–6 皆有立場；②必答 2、4、5 附實跑或構造；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v5，主委 2026-09-11）。
fact-verified: `sed -n '202p' scripts/gate.sh` → `register-output` 寫 `family=unknown`；`jq` → `committee_output` 在 `non_debt_legacy_events`、`round_open` 無 `brief_kind`（主委 2026-09-11）。
fact-verified: R4 三家產出已 `register-output`；round `99b677d2` 已 `debt_clear`。
assumed: 「被消費的 token」語意不會把合法流程卡死——主委領 token 後因故未 commit（例如實作中途發現要改 SPEC）⇒ 該 token 不是錨 ⇒ 之後的 small 仍累計在前一個錨的窗內 ⇒ 若累計 >3 會擋 small。否證觀測：這是誤擋（可再領 token 並真的 commit 解除），非繞過。／我跑了：**沒跑**，推演。請必答 2 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
