# VERDICTGATE SPEC v3 閉合確認＋adversarial review（R3）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R3
findings-round: R3

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R3-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R2 提過、v3 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v3**。R2 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r2/synth.md`（群集 X1–X6；11 條全採納、`CODEX-R2-P1-02` 之 (c) 駁回並附理由）。

## 🔴 必答
1. **你 R2 的每一條**在 v3 是否閉合？逐條「已閉合／未閉合＋理由」，並在 `CLOSED:` 列出已閉合者。閉合判準＝你自己的反例／構造在 v3 文字下**會被擋**（重跑或重推演，不憑「已修」）。
2. **X1 持續視窗**（Task 3.2 邊界④／Task 3.3）：起算點＝「最近一筆 `impl_token_issued`，或最近一個 `Ticket-Batch: <root>/b<N>` commit」。給一個 v3 仍擋不住的 small 序列，或宣告擋得住並說明兩個起算點衝突時取哪個（SPEC 未寫——請指出並建議）。
3. **X5／C-9 `no_output` fail-closed**：`committee_family_result` 存在而無同家 `committee_output` ⇒ blocked，除非 round 已 `--abandon`。這會不會把「委員 DONE 但 `cx_run` 自動註冊被拒收（`verdict_rejected`）」的合法情況變成死鎖？主委該怎麼解——SPEC 有沒有寫？
4. **X6 駁回 (c)**：主委駁回「改提新 P2 並 CLOSED 舊 ID」為語意問題（§N 第二條同族）。**codex**：接受或反駁，附機械判準（若你能給出一條可證偽規則，主委採納）。
5. **C-8 事件 schema**：`small_commit` 在 commit-msg hook 階段寫 audit——commit 若隨後被 `--amend`／`reset` 丟棄，audit 裡的 `small_commit` 仍在 ⇒ 聯集會**多算**。這是 fail-closed 可接受的誤擋，還是需要以 `git cat-file -e <sha>` 過濾？給立場。
6. §N 第三條新增之「SPLITUNIFY B5 前派**補裁決輪**（closure kind，只寫機械塊）」：主委實跑 `grep -ln '^VERDICT:' handoffs/2026091*-splitunify-*.md` 只命中一份 stamp 檔 ⇒ B4 閉合輪三份皆無 `VERDICT:`。補裁決輪是否會與 Task 2.2 邊界①「閉合輪不受閘擋」形成「先用閉合輪解鎖、再補裁決」的漏洞？給立場與構造。
7. **可否據此生成 TODO**？

## 停輪條件
①必答 1–7 皆有立場；②必答 2、5 附構造或碼證；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v3，主委 2026-09-11）。
fact-verified: `grep -n 'baseline' docs/VERDICTGATE_SPEC.md` → 5 處，全為 `verdictgate_baseline.sh` 檔名或「無基準檔」否定句（主委 2026-09-11）。
fact-verified: R2 三家產出已 `register-output`（audit `committee_output` ×3）；round `d2ccf23a` 已 `debt_clear`。
assumed: `impl_token_issued` 與 `Ticket-Batch: <root>/b<N>` commit 之 `small_commit` 兩種起算點在正常流程下**同序**（先領 token 再 commit）⇒ 否證觀測：主委領 token 後未 commit 該批、改做 small ⇒ 起算點為 token、視窗含該 small，合理；反向（先有 batch commit 再領 token）在 Task 3.2 下不可能（無 token 拒 commit）。／我跑了：**沒跑**，僅推演。請正面打（必答 2）。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
