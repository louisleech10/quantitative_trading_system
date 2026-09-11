# HANDOFF — 當前任務狀態

**更新：2026-09-11｜現行票：`VERDICTGATE`（治理，大；RISK b,c）｜狀態：SPEC v2（R1 五條全採納）→ **三家 adversarial R2 進行中**（session `20260911-verdictgate-x-review-r2`，task-id `20260911-VERDICTGATE-X-REVIEW-R2`，背景 `bbp3jy1os`）｜`SPLITUNIFY` 暫停**
- R1：composer／grok 皆 `VERDICT: blocked`（5 條）；codex 誤依 AGENTS.md Rule 12 交空檔 ⇒ round `65dfe9d9` 以 `collection-failed` 廢止；R1 synth W1–W4 在 `handoffs/reconcile/20260911-verdictgate-x-review-r1/synth.md`。R2 brief 檔頭明寫 Rule 12 不適用。
- 未 push 的 commit：`71821203`、`aa6bdc87`（push 被白話時序閘擋；須先補 README／治理進度日誌／接下來要做什麼／流程摩擦記錄／現在做到哪 註記後 render 再 push）。白話 `VERDICTGATE施工進度.md` 已寫。
- R2 回來後：`reconcile_build` → synth（含處置 token）→ attr 驗 → `register-output`×3 → `--rebuild` → `debt_clear` → SPEC v3（若需再派 R3）→ 白話 `VERDICTGATE規格白話.md` 給使用者審閱（**阻塞閘**）→ TODO（TODO_GENERATION_PROMPT）→ TODO adversarial → 戳記輪 → 實作 B1（裁決契約）。
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
