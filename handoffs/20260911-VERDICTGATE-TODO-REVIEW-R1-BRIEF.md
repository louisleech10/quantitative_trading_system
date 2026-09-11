# VERDICTGATE TODO adversarial review（R1）＋ codex R8 閉合確認

brief-kind: review
task-id: 20260911-VERDICTGATE-X-TODOREVIEW-R1
findings-round: R1

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`（本 brief 之 R 計數自 TODO 審查起算）。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （codex：R8 之 CODEX-R8-P1-01／P1-02／P2-03／P2-04 在 SPEC v9 是否閉合——重跑你的構造，列已閉合者）
```

## 審查對象
`docs/VERDICTGATE_TODO.md`（DRAFT）對照 `docs/VERDICTGATE_SPEC.md` **v9**。生成依 `templates/TODO_GENERATION_PROMPT.md` V13；§T 追溯表宣稱 8 Task／9 約束／72 ASSERT／4 殘留全覆蓋。

## 🔴 必答
1. **追溯**：§T 宣稱 72 條 ASSERT 全有落點。實跑 `grep -o 'ASSERT bash\|ASSERT git\|ASSERT GOVERNANCE' docs/VERDICTGATE_SPEC.md | wc -l` 並逐 Task 對照 TODO「驗證」欄——有無 SPEC ASSERT 在 TODO 找不到對應 Task（真遺漏），或 TODO 宣稱數與 SPEC 不符？
2. **深度紅線**：任一 Task 拿給「沒讀過 SPEC 的 agent」能否直接開寫？指出偽碼不足／修改檔案未到函式名／邊界 <2 之 Task。
3. **跨 Task 同檔衝突**：`gate.sh` 在 1.2／2.2／3.1、`debt_clear.sh` 在 2.2／4.1、`cx_run.sh` 在 1.2——§B 序列化是否足夠？B4 依賴只寫 B1，但 4.1 改 `debt_clear.sh` 而 2.2 也改它——B4 能否在 B2 之前做？給立場。
4. **§B 批次間 Gate「本票吃自己的閘」**：B3 上線後 B4 之 commit 須 `--impl-self` 領 token＋`Ticket-Batch: VERDICTGATE/b4`。這對本票 B3 自身的 commit（Phase 3 上線那一刻）怎麼處理——B3 的 commit 是在閘上線**前**還是**後**？TODO §0 寫「過渡以 small 或 Governance-Scope」——small 限 ≤3 檔，B3 改 4 檔以上；請指出這個矛盾並給可行做法。
5. **Task 4.1 與已上線的兩支 hook**（`spec_xref_hook.sh`／`synth_attribution_hook.sh`）：TODO 說共用模組 `_synth_attr.py`；hook 只驗「ID 在表＋修訂標的」、debt_clear 才驗 20 字＋處置 token。「填寫中不擋」的切法會不會讓 20 字引用又變成輪級才發現（使用者 2026-09-11 質問「輪級才擋等於沒用」）？給立場：是否該在 hook 也驗 20 字（填 synth 時 finding 已在附錄，可對）？
6. **§E 殘留**：E-5（append 序第二層）與 E-6（語意等價）為 TODO 層新增，理由類別是否合法（needs-research 須說明「研究什麼」）？
7. **可否 FROZEN**？

## 停輪條件
①必答 1–7 皆有立場；②必答 1 附實跑計數；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤codex 之 `CLOSED:` 只列重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh todo docs/VERDICTGATE_TODO.md` rc=0（主委 2026-09-11）。
fact-verified: SPEC ASSERT 實數 72（主委 grep；各 Task 0/12/3/19/5/6/22/5）。
fact-verified: `scripts/spec_xref_hook.sh`／`synth_attribution_hook.sh` 已掛 PostToolUse 並實測阻塞（commit `d886dc67`）。
assumed: B3 之 commit 可在 Phase 3 hook 檔案進 repo 但**尚未被 git 掛載**（`core.hooksPath` 指向 `scripts/git_hooks`，新增 `post-commit` 檔即生效——此假設**可能錯**）⇒ 否證觀測：`git config core.hooksPath` 已是 `scripts/git_hooks`，新增檔即刻生效 ⇒ B3 自己的 commit 會被自己的 commit-msg 閘擋。／我跑了：`git config core.hooksPath` → `scripts/git_hooks`（**假設看起來錯**，請必答 4 正面打）。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
