# HANDOFF — 當前任務狀態

**更新：2026-09-11｜現行票：`VERDICTGATE`（治理，大；RISK b,c）｜狀態：SPEC v9 **停輪**（R1–R8 共 48 條全採納；R8 兩家 proceed、三家同意凍結 small 視窗）→ 使用者同意白話「四段全做」→ TODO v3 **FROZEN**（R9／R10 收斂；戳記 R11 codex／R12 composer／R13 grok 皆 APPROVED，stamp-target＝R10 synth，body `7883342f…`）→ 第一、二批已閉合 → 第三批已實作（`d6c52c27`）→ **第三批已閉合（R1 收斂 K1–K5、閉合 R2／R3 codex CLOSED 全部；`verdictgate_check … 4` ✓）→ **第四批（Task 4.1）已實作，三家審碼 R1 進行中**（session `20260911-verdictgate-b4-review-r1`；`--impl-self` 自證已 GATE PASS）｜`SPLITUNIFY` 暫停**
- B4 產物：`scripts/_synth_attr.py`（唯一實作；hook 子集／gate 全量）、`reconcile_cluster_attribution_check.sh`（重寫為閘）、`synth_attribution_hook.sh`（改呼叫模組）、`debt_clear.sh::_run_attribution`（completeness 之後；`--todo` 由 session 第二段推 `docs/<EPIC>_TODO.md`）、`reconcile_build.sh` 骨架提示；p4 21 測試、mutate-b4 9/9。主委自查修一條 fail-open（`延後→Task 9.9` 被空白截成 `Task` 恆真）。歷史 24 份 synth 對新閘全紅（print-only，SPEC 規定不回改）。
- 🔴 從 B4 起寫 synth 群集表：每列必逐字引用該 finding 斷言**前 20 字**（NFC、去空白、不寬容標點）＋第 4 欄處置 token（採納｜部分採納｜駁回｜延後→<TODO 內存在之 ID 或 Task N.N>）——hook 寫入當下就擋。
- 使用者 2026-09-11：「進度表看不懂有哪些項目、做到哪、剩哪些」⇒ 白話進度表改為「交付項目表／現在在哪／還剩什麼」三段開頭（記憶 `feedback_progress_board_items_status_remaining`）。
- 🔴 R3 主委踩坑：brief 要求 codex 在 `CLOSED:` 列他家 ID（`CLAUDE-R1-P1-01`）⇒ `verdict_parse` 拒收；契約 CLOSED 只准本家。主委自查 ID 只進 synth 群集表，不進 blocked_by，不必委員閉合。K5 probe：`handoffs/20260911-verdictgate-k5-probe.sh`（委員隔離環境跑 probe 時指令列不得含家族名，否則 `gate_check` 誤判 dispatch）。
- B3 R1：composer／grok proceed；codex blocked（K1 刪生產檔不算生產變更 ACMR→ACDMR；K2 全 delete push 誤回退 @{u}..HEAD → `VG_PUSH_ALL_DELETE`；K3 trailer glob → 錨定 regex；K4 22 ASSERT 補直接測試 p3 29→47）＋主委自查 K5（`--range 0000000..<sha>` rev-list rc=128 被吞 ⇒ fail-open，已 fail-closed）。mutation 17/17。
- 🔴 閘實戰：codex 裁決行寫成一句話 ⇒ `verdict_parse` 拒收、audit `verdict_rejected`；主委正規化重 register-output 後 **debt_clear 仍鎖**（只認最新 family_result=success；registry 綁 family_result 單一 origin，gate 不得補寫）⇒ debt_clear ⑤ 改認「拒收後其後之 committee_output」（同 verdictgate_check 語意，3 測試）。閉合 brief 已請 codex 審此縫。
- B3 產物：`ticket_batch_check.sh`（--msg／--emit-event／--push-range）、hooks（commit-msg／post-commit／pre-push stdin range）、gov_check 1c、gate `--impl-self`。
- 🔴 殘留：`test_govb1_factkey_hook.py` 3 條 skip——2 條為 08-14 pre-push `--fast` 裁定後過期、1 條 fixture `factkey_clean` 隨 fact_keys 變更過期（需在 fixture repo 跑 gen --write 再生；rm -rf 被拒未做）。
- 🔴 B1 兩次踩同型坑：把 `committee_output` 移入 debt_events 後，帳本對舊列（無 sequence）與新列（無 round_id）各紅一次 ⇒ gate 全面拒發。修法＝registry `sequence_since`＋`round_scoped:false`。**教訓**：動 registry event 集合時，必須對真 audit 複本跑全部消費端（ledger／append／reconcile／provenance），不能只跑隔離測試。
- B3 注意：`audit_append` 拒空值欄 ⇒ `ticket_commit` 之 small 須 `root=small batch=0`（非空字串）。codex 交件檔常漏 `STATUS: DONE` ⇒ 自動註冊已改「有 VERDICT 行即嘗試」。
- B1 做法：`scripts/governance_verdicts.json`（新）、`scripts/audit_events.json`（三事件＋`committee_output` 移出 legacy＋`brief_kind`＋origin allowlist）、三範本末段機械塊＋`template_check` 雙格式判定、`scripts/verdict_parse.sh`（新）、`gate.sh register-output`（family 由尾碼＋roster＋expected_outputs 對證；`--kind stamp --family`）、`cx_run.sh` review／closure 自動註冊＋`verdict_rejected`、`committee_run.sh` round_open 寫 `brief_kind`；測試 `tests/governance/test_verdictgate_p1.py`；mutation `handoffs/20260911-verdictgate-mutate-b1.py`。本票 commit 只帶 `Governance-Scope`（scripts-only，TODO §0）。
- R9 揭露：本票 scripts-only ⇒ Task 3.2 trailer 閘不觸發，治理腳本 commit 不受 Phase 3 保護 ⇒ TODO §E E-7（user-ruling 停輪、下張治理票再議）。R9 synth 首版簡寫簽名被 `spec_xref_hook` 當場擋下（閘實戰首例）。
- 本日新上線三支產出端閘（使用者質問「為何不每次都做全文掃描／輪級才擋等於沒用／reconcile 也要」）：`spec_xref_hook.sh`（寫 SPEC/TODO/任何被 synth 宣告之修訂標的時：殘留掃描＋synth 處置對證）、`synth_attribution_hook.sh`（寫 synth 時：ID 全在表＋-x- 層必宣告 `**修訂標的**：`）、`spec_xref_check.sh --staged/--synth`（pre-commit／debt_clear 後備）。22 測試含 mutation。🔴 hook 阻塞理由必走 stderr。
- 殘留動作：`handoffs/reconcile/zz-live-x-review-r1/` 實測檔，rm／git clean 被使用者拒兩次，待使用者處置（untracked、無害）。
- 🔴 使用者 2026-09-11 裁定（逐字）：「若是有地方是你跟委員判定無法收斂或無限窮舉或實作或落地後對整個流程的運作成本和時間成本太高，這就不要鑽下去，該適時停止」⇒ small 視窗規則凍結於 v7、登記 §N；R8 後若只剩文字同步類 ⇒ 主委修完直接進白話審閱閘（AskUserQuestion 阻塞），不派 R9。記憶 `feedback_stop_when_nonconvergent`。
- 收斂檔：`handoffs/reconcile/20260911-verdictgate-x-review-r{2..6}/synth.md`（債皆已清）。R2 X、R3 Y、R4 Z、R5 W、R6 V。composer 自 R3 起每輪 `proceed`；codex 每輪再挖 3–6 條、碼證皆實，多為「改一處漏一處」；R6 grok 抓到 R4 synth Z4 寫錯（錨前 small 不在窗內）。
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
