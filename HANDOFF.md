# HANDOFF — 當前任務狀態

**更新：2026-09-12｜`VERDICTGATE`（治理票 B-62）**結案**（收票審 R11／R12 三家 proceed、CLOSED 全部；SoT 票列狀態見 `docs/GOV_TICKET_SOT.md`；強制清單 E-022～E-025）｜下一步＝回量化主線：`SPLITUNIFY` 復工（`verdictgate_check 20260911-SPLITUNIFY 8` ✓；**R-1 per-symbol 投影仍待使用者裁**）｜開工前照 CLAUDE.md 稽核本檔 vs repo**
- 本票四閘（皆已實戰）：①`cx_run` 交件即 `register-output`／`verdict_parse`（拒收委員裁決行 4 次）②`gate.sh`／`committee_run` 開輪與 `--impl-self` 前 `verdictgate_check`（**C-4 只擋進入新批**：本批已有未 abandon 之 review 輪 ⇒ 不重驗前批；closure／consult 首進不算——收票審三家同題 P1 修）③commit-msg `Ticket-Batch:`＋post-commit `ticket_commit`＋pre-push 1c（ACDMR、全零 range fail-closed、全 delete 不回退）④synth hook＋`debt_clear _run_attribution`（`_synth_attr.py`：ID 必列、逐字引用斷言前 20 字、整詞處置 token、延後目標封閉文法）。
- 🔴 寫 synth 群集表：每列逐字引用該 finding 斷言**前 20 字**（NFC、去空白）＋第 4 欄整詞 token（採納｜部分採納｜駁回｜延後→E-n／Task N.N，說明只准括號）；處置欄不得夾字面延後箭號（實戰擋過主委）。x-review 層另須 `**修訂標的**` 且處置欄反引號概念見於標的。
- 🔴 task-id／session 之**日期前綴屬 root**：同票跨日沿用首日前綴（R11 用 `20260912-` ⇒ CLOSED 被拒；`register-output` 語料已改去日期比對，但 helper／checker／token 名仍含日期）。
- 🔴 閘實戰揭露並已修之洞：debt_clear 不認「拒收後重註冊」；語料不含 B1 上線前舊輪（`expected_outputs` 補）；語料不認跨日 root。教訓同 B1：動 audit 消費端必對真 audit 複本跑全部 caller。
- 殘留（`docs/VERDICTGATE_TODO.md` §E）：E-1／E-2／E-4／E-7 user-ruling；E-3／E-6 needs-research；E-5 研究完成（`handoffs/20260911-verdictgate-e5-probe.sh`：序判無增量、mtime 保留）；**E-8（新，登記於 R11 synth）**登記表行號語意對位 needs-research；**SPEC C-4 字面修訂延後至下張治理票**（三家接受，與 E-7 同批）。TODO v3 FROZEN 未改——E-8 與 C-4 註記只在 synth／本檔。
- 殘留動作：`handoffs/reconcile/zz-live-x-review-r1/`（實測檔，使用者拒刪兩次，untracked 無害）；`test_govb1_factkey_hook.py` 3 skip（pre-existing）；歷史 24 份 synth 對新閘全紅（print-only，SPEC 規定不回改）。
- 使用者裁定（逐字）：「為了文檔品質，先把治理票做完，再開始量化主線項目」；「若…無法收斂或無限窮舉…該適時停止」；「你進度表這樣寫，我看不懂到底有哪些項目，然後做到哪和也不知剩下哪些要做」⇒ 白話進度表固定三段（交付項目表／現在在哪／還剩什麼）。
- 白話：`白話說明/Archived/VERDICTGATE施工進度.md`（結案版）；README 首段已註結案。

## SPLITUNIFY 復工時之狀態（全部已 push，`fa9f51c1` 為其最後實作 commit）
- B1–B4 完成；audit 之 `b5`–`b7` 輪皆為 B4 後續輪借號（命名規約），**真實下一批在 audit 語意為 b8**；`20260911-SPLITUNIFY-B7-REVIEW-R2` 補裁決輪三家 proceed 已清債。🔴 **未收票**：R-1（待使用者）、R-5、SU-RESID-2、SU-RESID-3；D1 範圍裁定曾以已廢止之「95% 就收」接受、未重審（復工首輪須重審）。
- 復工前：`bash scripts/gate.sh dispatch --impl-self --task-id 20260911-SPLITUNIFY-impl-b8-claude …` 自證；生產路徑 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`（commit-msg 會擋）。

## 踩坑（本票）
- `committee_run.sh` 的 `--` 後須帶 gate 全部必填；同一 Bash 指令內先 `gate.sh dispatch` 再 `committee_run` 會被 PreToolUse 擋 ⇒ 分兩次呼叫。委員名字出現在 Bash 指令列／暫存路徑會被 `gate_check` 誤判派工（委員隔離環境同）。
- `fact_keys.json` 行號會位移（本票四次）；受管檔手寫「識別碼＋狀態詞」同一行會被 guard 擋；`handoffs/` gitignored 須 `git add -f`；heredoc python 在 Bash 會被分類器拒。
