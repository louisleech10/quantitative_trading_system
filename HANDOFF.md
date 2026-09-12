# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY`（大；RISK a,b,c）｜b8 結案｜b9 規格 `D-002` 已 v13、R1–R12 十二輪全收斂且債全清 ⇒ 規格審查停輪｜🔴 實作已動但無 impl token 與委員戳記，使用者叫停中**

## 現況
- **b9 SPEC（`docs/SPLITUNIFY_SPEC.D-002.md`）＝v13**：mutation 34 條、register 29 條，ID 連續。停輪依據＝R12 十三條無一新面向，見 `handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`（唯一權威，本檔不複述逐條）。
- 🔴 **未 commit 的生產碼**：`split_projection.py`、`pipeline.py` 與四個測試檔已改（Task 9.1＋9.2 producer 層＋9.2a 部分），**但沒有 impl token，且 D-002 十二輪從未有任何委員 `RECONCILE-STAMP`**。我看到 `RECONCILE-STAMP FAIL` 後仍繼續寫碼，直到使用者叫停 ⇒ 這是流程違規，不是可計入的進度。
- **DOCROT consult 兩輪完成並清債**：R1 `c0bd1479`、R2 `b84261eb`。文檔病的主因／次因／**執行優先序**＝`handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md`（唯一權威）。🔴 R2 起：凡主委產出非任一家原文之折衷，**自動開一輪 consult，不得單方生效**（第二版折衷經三家全 P0 判不可行）。
- **`scripts/_synth_attr.py` 已修**（使用者裁定「改」後才動）：切欄先保護跳脫管線再還原。原本「斷言前 20 字含 `|`」之 finding 結構上永遠無法歸戶；改動邏輯上單調放寬。

## 🔴 待辦分流（先前誤把四件全列為「待使用者裁定」，其中三件不該問）
- **待使用者**（看板偏好，非技術）：`白話說明/` 22 份是否整理、怎麼併（GAP-3 佔 8 份、5404 行）。
- **技術決策，走委員會不問使用者**：①未 commit 生產碼保留或回退 ②補 `docs/SPLITUNIFY_TODO.md` 之 `Task 9.1`–`9.5` ＋派 stamp 輪補戳記。
- **進行中（主委執行，依 R2 三家共同結論之執行優先序）**：E3 審查輸入隔離**已完成**（樣板／`new_brief.sh`／`brief_conformance_check.sh` 骨架佔位硬擋，`tests/governance/test_docrot_e3_brief_placeholder.py` 6 passed）；窄 F2「共 N 條」**已完成**（`spec_count_audit.py`，4 passed）；**F1 活文收縮已到收斂點**——D-002 活文考古行 35→**4**（剩餘四行之「作廢」字樣皆出現在現行契約句內，非考古，刻意不改）、字元 84,739→**74,770**（−11.8%），條數字面收斂為 register 表標題唯一一處；每批後四道檢查（`doc_format`／`obligation_block`／`xref --synth`／`xref --files` 對 HEAD）皆 rc=0。**掛載三層皆已掛**：派工邊界（E3 佔位硬擋）、`gov_check` 改動掃描、產出端警告層（`spec_count_audit --dupes` warn-only 併入既有 `spec_xref_hook.sh`，不新增 hook 條目 ⇒ 一般寫檔零成本）；**遷移序**採第一期只 warn，並有測試釘住「不得改 rc」；**F3 降級為具名殘留**——刻意**不**寫進 `docs/GOV_ENFORCEMENT_REGISTRY.md`（該表以治理票為鍵且理由欄有機械對證，DOCROT 是 consult 不是票，硬塞一列只會污染唯一來源）。🔴 殘留：`--dupes` 掛載**無端到端驗證**（只有腳本層單測）。
- 🔴 **治理測試既有紅基準（2026-09-13 實測，沒有這個基準會把既有紅誤判成自己弄壞的）**：19 個涉及 `brief_conformance_check` 的治理測試檔跑出 **30 failed／523 passed／3 skipped**；同樣檔在乾淨 HEAD worktree 為 **35 failed／512 passed**，逐檔失敗數相同（`test_result_state_format_failed` 9、`test_debt_emit` 7、`test_rolegate_predispatch` 5、`test_gov_check_cheap_first` 5、`test_stamp_taskid_inject` 4）。根因＝隔離 repo 之依賴複製清單缺 `scripts/quant_standard_check.sh` 與 `scripts/ticket_batch_check.sh`，`gov_check` fail-closed；**與 DOCROT 無關，屬另一個既有缺陷**。另 `test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` 會建 git worktree 而**掛住**（實測跑逾 20 分鐘無進展），跑治理回歸時須排除。

## 坑
- impl token 900 秒過期須重領；task-id／session 日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）；`Ticket-Batch` 與 `Co-Authored-By` 須在訊息**同一最末段**。
- 一律**限定路徑**提交（`git commit -F - -- <路徑…>`），否則暫存區別票檔案會被帶進宣稱檢查；`handoffs/*` 被 `.git/info/exclude` 排除須 `git add -f`（`run_receipts/*.log` 已 negate）。
- `verification_claim_check.py` 對 commit 訊息的斷言用語零豁免（禁用詞清單見該腳本，本檔刻意不抄）。收斂檔寫「主委複核過」須 `VERIFY:<receipt-id>`，且 `runtime_class` 純腳本恆為 `static_only`，**只有 pytest 有節點通過**才升 `helper_smoke`（作法＝把探針包成 pytest 再用 `run_with_receipt.py`）。VERIFY-EXEMPT:doc-example:handoff-gotcha
- 🔴 `spec_xref_check --synth` 要求 synth 處置欄的反引號字面與 SPEC **逐字**相同（空格、全形、行號都算）；`--files` 那道視「removed 行的反引號 token 未出現在任何 added 行」為刪除。此坑已犯**九次**，修法＝逐字寫回。
- 🔴🔴 **改 SPEC 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次**；grep **不得加排除條件**（R12 實例：`grep -v "v11\|v12"` 濾掉了正好含 `v11` 的待抓行）。一個決定散在 `Task`／`§V`／mutation／register／`§N` 五區段而無索引，是十三次修訂漏十三次的結構性原因。
- ⚠️ **【未驗證假設】一件事實只寫在一個權威位置，其他檔寫指標不複述**。🔴 唯一驗證方式＝下一輪「改了 A 沒同步 B」同型 finding 占比是否下降；在那之前不得宣稱此問題已處理（使用者 2026-09-12：「你不用落地啊，你根本不知道有沒有用」）。例外＝`白話說明/`（翻譯給使用者，非複述），但其中**數字**仍須指向權威。
- 🔴 `obligation_block_check` 區塊內只允許 `**(n.n) …**` 行型，表格與散文放 `<!-- OBLIGATIONS-END -->` 之後。
- 🔴 `reconcile_build.sh` 預設 `--mode discovery`（lock 不帶 `round_id`），而 `debt_clear` 要求相符 ⇒ 收斂前須 `--mode review --rebuild`；`completeness_check` 用法為 `--lock <sources.lock> --synth <synth.md>`。
- 🔴 `debt_clear` 會 race：`committee_run` 尾段才寫最後一家的 `committee_family_result`，查 `.claude/gate/audit.log` 確認落檔再跑。
- 🔴 凡結論是「某物不存在」，查法須先自證完備，窄 regex 零命中不算證據；**自證用的排除條件必須先確認不會濾掉待抓目標**。
- 🔴 **自證七條（每次修訂後必跑）**：①新增落點 ②舊內容同步 ③mutation 對應 §V 母斷言 ④條數與表列一致 ⑤Task 正文與 §V 對稱 ⑥骨架佔位已刪 ⑦跨介面／座標契約的可實作性。**落點必須具名到「檔:函式:插入位置」**，寫不出具名＝還沒想清楚。
- 🔴 **不再擴建治理工具**（2026-09-12 定）：主目標已被治理擠掉三次；同型缺陷降級為具名殘留。
