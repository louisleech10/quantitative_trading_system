# VERDICTGATE SPEC v4 閉合確認（R4）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R4
findings-round: R4

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R4-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R3 提過、v4 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v4**。R3 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r3/synth.md`（群集 Y1–Y6；8 條全採納，Y5 採**較嚴**版）。

## 🔴 必答
1. **codex／grok**：你 R3 的每一條在 v4 是否閉合？逐條「已閉合／未閉合＋理由」，重跑你自己的構造，並在 `CLOSED:` 列出已閉合者。**composer**：R3 你 `proceed`；請對 v4 之 Y5（C-4 反轉為 fail-closed）與 Y2（post-commit 寫入＋`merge-base --is-ancestor` 過濾）獨立找碴。
2. **Y5 較嚴版**（C-4：前批有 `committee_round_open` 但 `quorum_eligible` 任一家無 `verdict` ⇒ blocked）：這與使用者 2026-08-05「面向未來不溯及既往」是否衝突？主委立場：不衝突——閘不讀舊 markdown、不推導，只要求「活票復工前補一輪機械裁決」；已收票不會再開批故不受影響。給立場；若認為衝突，指出哪一句裁定被違反。
3. **Y5 邊界**：descoped 票（前批編號不連續、`_rq_prev` 回溯到更早批）在 C-4 下會不會誤擋？`_rq_prev` 回溯到的那批若是上線前的 round ⇒ 擋並要求補裁決——這是預期。給一個你認為**不該擋卻被擋**的構造，或宣告無。
4. **Y2 `post-commit`**：`post-commit` hook 寫 audit 失敗不擋 commit；Task 3.3 邊界④以「`origin/main..HEAD` 有 small trailer 卻無 `small_commit` 事件 ⇒ 拒 push」補洞。`git commit --amend` 會再觸發 `post-commit` 嗎（給碼證或實跑）？若會，舊 sha 事件靠 `is-ancestor` 過濾、新 sha 重寫——確認無漏。
5. **Y1 單錨**：`impl_token_issued` 為唯一重置錨。主委在**不同票**間切換（ROOT-A 領 token → small → ROOT-B 領 token → small）：視窗以最近 token 重置屬預期（領權限即重置）。是否存在「領一個假 token 只為重置視窗」的繞法？`--impl-self` 須過 quorum／verdictgate 才發 token——足夠嗎？
6. **Y3／Y4**：C-9 roster 讀 `committee_round_open.quorum_eligible`；`--abandon` 只准用於「該家無任何 `family_result`」。構造一個合法流程被卡死的情況（例如委員 DONE 但 `cx_run` 自動註冊被拒收後，主委修檔再 `register-output` 是否一定能解），或宣告無。
7. **可否據此生成 TODO**？

## 停輪條件
①必答 1–7 皆有立場；②必答 3、5、6 附構造或明確「無」；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v4，主委 2026-09-11）。
fact-verified: `sed -n '16p' scripts/audit_append.sh` → `REGISTRY=…/audit_events.json`；`scripts/governance_verdicts.json` 不存在（主委 2026-09-11）。
fact-verified: `sed -n '219,233p' scripts/committee_run.sh` → `committee_round_open` 已寫 `participants`／`quorum_eligible`／`expected_outputs`（主委 2026-09-11）。
fact-verified: R3 三家產出已 `register-output`；round `7fdcc5ff` 已 `debt_clear`。
assumed: `git commit --amend` 會重新觸發 `post-commit` hook ⇒ 否證觀測：若不觸發，amend 後新 sha 無 `small_commit` 事件 ⇒ Task 3.3 邊界④會在 push 時擋（fail-closed 而非漏）——所以即使假設錯，結果是誤擋非繞過。／我跑了：**沒跑**。請必答 4 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
