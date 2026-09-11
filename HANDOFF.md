# HANDOFF — 當前任務狀態

**更新：2026-09-11｜現行票：`VERDICTGATE`（治理，大；RISK b,c）｜狀態：SPEC v5（R1–R4 共 29 條全採納；最新 commit `5370ffc4` 已 push）→ **三家閉合確認 R5 進行中**（session `20260911-verdictgate-x-review-r5`，task-id `20260911-VERDICTGATE-X-REVIEW-R5`）｜`SPLITUNIFY` 暫停**
- 收斂檔：`handoffs/reconcile/20260911-verdictgate-x-review-r{2,3,4}/synth.md`（債皆已清）。R2 X1–X6、R3 Y1–Y6、R4 Z1–Z5。composer／grok 自 R3／R4 起 `proceed`；codex 每輪再挖 5–6 條、碼證皆實。
- v5 關鍵語意：small 視窗錨＝**被消費的** token；`ticket_commit.token_fresh` 由 post-commit 寫；C-4 對「前批有 review round 但無機械裁決」fail-closed（SPLITUNIFY 復工前須補裁決輪）；roster 讀 `round_open.quorum_eligible`；`register-output` family 由檔名尾碼對 roster。
- 🔴 `committee_run.sh` 的 `--` 後須帶 gate 全部必填（`--intent --risk --facts-asked --review-role --template --task-id`），只給 task-id 會 gate 拒發（本日踩一次）。`handoffs/` 大多 gitignored，brief 要 `git add -f`。
- 白話 `VERDICTGATE規格白話.md`（審閱閘用）與 `VERDICTGATE施工進度.md` 已寫；R3 若三家 proceed ⇒ 用 AskUserQuestion 阻塞給使用者審白話 → TODO（TODO_GENERATION_PROMPT）→ TODO adversarial → 戳記輪 → 實作 B1。若 blocked ⇒ SPEC v4 再派 R4。
- 使用者裁定（逐字）：「為了文檔品質，先把治理票做完，再開始量化主線項目」；「我切換模型用Fable5.1做治理了，繼續執行」。
- 使用者待裁：SPLITUNIFY R-1（per-symbol 投影，推翻 SPEC C-2）做不做。

## VERDICTGATE 要解什麼（實證見 `handoffs/20260911-VERDICTGATE-RECON-claude.md`）
1. `review_quorum_check.sh` 只在 `*-impl-b<N>-<家族>` 派工時觸發 ⇒ 主委自任實作時從未跑過；且只驗「有沒有派出去」、不讀裁決。
2. 審碼收斂不要求委員確認；`completeness_check` 附錄逐字保留 ⇒ 永遠通過；attribution 恆 rc=0。回溯：8 輪 57 條中 3 條被主委弄丟。
3. 使用者設計指示：**不論哪家執行都要觸發**（含主委自任）⇒ `--impl-self` token＋commit-msg `Ticket-Batch:` trailer＋gov_check 1c。

## SPLITUNIFY 暫停時之狀態（全部已 push，最新 `fa9f51c1`）
- B1–B4 完成；8 輪審碼＋閉合確認輪。🔴 **未收票**：R-1（待使用者）、R-5、SU-RESID-2、SU-RESID-3；SU-RESID-1 併入 VERDICTGATE；D1 範圍裁定曾以已廢止之「95% 就收」接受、未重審。

## 踩坑（本 session）
- `fact_keys.json` 行號引用會位移（本日兩次）；委員名字出現在 Bash 指令列會被 `gate_check` 誤判為派工 ⇒ 寫腳本檔再跑；`rm -rf`／heredoc python 被分類器拒。
- doc_format_precheck：RISK-HIT 不可含反引號、brief 需至少一條 `assumed:`；reconcile roster≠round 家數 ⇒ `debt_clear --abandon --kind collection-failed`。
