# VERDICTGATE SPEC v8 閉合確認（R8——最後一輪找碴）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R8
findings-round: R8

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

🔴 **使用者 2026-09-11 裁定（逐字）**：「若是有地方是你跟委員判定無法收斂或無限窮舉或實作或落地後對整個流程的運作成本和時間成本太高，這就不要鑽下去，該適時停止」。據此：①`small` 視窗規則凍結於 v7 語意，再進一步繞法已登記 §N「蓄意等價」——**本輪請不要再對 small 視窗提新構造**，只審 §N 那條的理由是否成立；②本輪為最後一輪找碴：若只剩文字同步類，主委修完直接進白話審閱閘，不派 R9。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R8-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R7 提過、v8 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v8**。R7 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r7/synth.md`（U1–U4 全採納）。主委本輪已先做全文自掃（12 個被改概念逐一 grep，殘留皆為歷史敘述或否定句）。

## 🔴 必答
1. 你 R7 的每一條在 v8 是否閉合？重跑你的探針（helper grammar 對 `P16 6`／`P16 4`／`SPLITUNIFY 2`；pre-push stdin range 對 fork Case B／C；stamp kind 分流）。
2. **§N 新增之 small 視窗殘留**：理由「重置成本＝合規成本 ⇒ 繞過等價於合規 ⇒ 蓄意、非意外」是否成立？若你認為存在**非蓄意**（正常流程會意外踩到）的拆分構造，列出；否則寫「同意凍結」。
3. **U3 pre-push stdin range**：pre-push 一次 push 多個 ref（`git push origin main feature`）⇒ stdin 多行 ⇒ 1c 是否對每行各驗？SPEC 寫「每行」——請確認無歧義；`git push --delete`（local sha 全零）⇒ 該行跳過，SPEC 未寫——給立場。
4. **U4 stamp 分流**：`register-output --kind stamp` 之 `committee_output.verdict=null`——Task 2.1 `--report` 會把它算成 `unknown` 還是另列？C-4 對前批 review round 的判定會不會誤讀到同 task 的 stamp 事件？給碼證或宣告無。
5. 🔴 **全文互斥掃描**：列出每一處，或宣告「全文無互斥」並附掃描方法。
6. **可否據此生成 TODO**？

## 停輪條件
①必答 1–6 皆有立場；②必答 2 須明確「同意凍結」或附非蓄意構造；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v8，主委 2026-09-11）。
fact-verified: R7 三家產出已 `register-output`；round `0e5dcd11` 已 `debt_clear`。
fact-verified: `git remote | wc -l`＝1、`git branch -r | wc -l`＝12（本 repo；composer R7 之 fork 構造可在此成立）。
assumed: pre-push stdin 在 `git push origin main` 時恰一行、`<remote sha>` 為 origin/main 當前 sha ⇒ 否證觀測：若 hook 收到零行（某些 GUI 客戶端）⇒ range 空 ⇒ 1c 無輸入——SPEC 寫「手動呼叫無 `--range` ⇒ 回退 `@{u}..HEAD`」，pre-push 收到零行時應走同一回退，SPEC **未寫**。／我跑了：**沒跑**。請必答 3 一併答。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
