# HANDOFF — 當前任務狀態

**更新：2026-09-13｜現行 topic：SPLITUNIFY b9 復工**。DOCROT／CXSTAMP 已結票（三家戳記、無欠債），**不重開**。本 session 進度：①開工稽核抓到 HANDOFF 一處過時（原寫「四個測試檔」，實為 **2** 個）並更正；②派 `20260911-splitunify-b9-consult-r2` 三家裁定未 commit 生產碼去留——**composer／grok 皆判 `REVERT`，codex 依 `AGENTS.md:40` Rule 12 判 blocked（不裁）**；收斂 `handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md`（10 findings 全歸戶、completeness PASS、`debt_clear` rc=0）；③**REVERT 已執行**（四檔 ＋ staged 的 `handoffs/20260911-splitunify-b9-probe-multitf.py` 全還原至 HEAD，備份在 scratchpad 之 `b9_reverted_worktree.patch`），重跑 `test_splitunify_derive.py`＋`test_splitunify_wiring.py` 得 **87 passed／0 failed**；④**`docs/SPLITUNIFY_TODO.md` 已補 `§B` 之 `B9A`–`B9F` 與 `§C-9` 之 `Task 9.1`–`9.5`**（`doc_format_precheck` rc=0、`spec_xref_check --synth` rc=0／18 概念同步）；⑤**戳記輪 `20260911-splitunify-b9-stamp-r1` 完成**——三家皆 APPROVED，`reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **PASS**（十三輪來第一次）；同輪 codex 對 §C-9 提四條 P1（`VERDICT: blocked`）、grok 一條 P2，**五條全採納並已修**；收斂 `.../20260911-splitunify-b9-stamp-r1/synth.md`，`debt_clear` rc=0。⑥**review-r13 完成（＝DOCROT 成效量測第一輪）**：stamp-r1 五條 finding **全數由原提出方 CLOSED**；composer／grok 零 finding proceed；codex 新開兩條 P1＋一條 P2，**全採納並已修**——T1 `C5-20` 之 mutation 錯配（另主委同型自查補 `C5-21`）⇒ 新增 `M-SU-D2-35`／`M-SU-D2-36`、條數 34→**36**、SPEC 進 **v14**；T2 `Task 9.3` receipt 閘只比行數可被繞過 ⇒ 改 exact ID set ＋ TASK／COMMIT 綁定；T3 `B9D` 描述與表列列數不符 ⇒ 逐列具名。**`doc_friction_ratio` = 0/5 = 0.00，finding 總數 5（≤20）⇒ 第一輪達標**。🔴 **T1 使 SPEC body 變更 ⇒ v13 之三家戳記失效**，新 body sha256 `7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2` 須重簽。⑦**review-r14 完成（＝DOCROT 量測第二輪）**：r13 三條全數由 codex CLOSED；但**逐列窮舉揭出一整類存量缺陷**——register 之 mutation 欄再有**五列**錯配（`C5-24`／`25`／`27`／`29` 改指或補掛、`C5-28` 之 `—` 經複驗確為刻意並已具名 `blocked-by`），新增 `M-SU-D2-37`..`40`、條數 36→**40**、SPEC 進 **v15**；另兩類：`M-SU-D2-35`／`36` 應紅欄可被 `in df.columns` 軟包短路（兩家撞題，已加欄位存在斷言＋軟包禁令＋多 TF fixture）、`Task 9.3` receipt 閘可用「分類全填同值＋占位碼證＋任意 COMMIT」假完成（三家撞題，已加改前分類對證 SPEC 現況、碼證 path:line 須真實存在、COMMIT 須等於 audit 之 round-start HEAD）。🔴 **`C5-01`..`29` 之逐列核對已窮舉完成**（三家獨立確認 `C5-01`..`23`／`C5-26` 無誤），此類存量到此為止。**DOCROT 兩輪皆達標**：r13 = 0/5、r14 = 0/10（現行判準）；若採 codex 提議之加強字面集合則 r13 = 1/5 = 0.20、r14 = 0/10，兩種判準下皆 ≤0.30 且每輪 ≤20。🔴 **誠實邊界**：本輪十條有七條屬「指標指錯／閘不夠緊」，那是**另一種**文檔病，現行 `doc_friction_ratio` 完全量不到；「0.00」只證明 DOCROT 針對的那一種病沒再發作，**不等於**文件健康。⑧下一步＝派 `20260911-splitunify-b9-review-r15`（U1–U3 閉合再驗證 ＋ 對新 body sha256 `c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0` 重簽）。

## 現況
- **b9 SPEC（`docs/SPLITUNIFY_SPEC.D-002.md`）＝v13，body sha256 `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`，仍為零戳記**。停輪依據＝`handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`（唯一權威，本檔不複述）。
- **consult-r2 之四步裁定**（`.../20260911-splitunify-b9-consult-r2/synth.md` ＝唯一權威）：①REVERT **已做** ②補 TODO Task 9.1–9.5 **已做** ③派 stamp 輪 **進行中** ④領 impl token 後才動生產碼 **未做**。
- **Phase 9 依賴序（四方一致）**：`9.1 → 9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5`；`9.2`／`9.2a` 不得拆批；`9.5` 必須最後。
- 🔴 **主委具名不採納委員原文兩處**（理由見 synth）：grok `Task 9.4` 之**無路徑** `pytest -k`（會收全套、小時級）；composer `Task 9.2b` 之 `bash scripts/freeze_splitunify_golden.py`（檔是 `.py`，且 golden 重凍屬 `9.5`）。
- 🔴 **「雙家族」字面已更正為指標**（`CLAUDE.md:30`、ORCH `:41`／`:195`）——唯一權威＝ORCH §1 現行分工行＋`scripts/governance_roles.json`，現行＝**三家全員**。CLAUDE.md 自己已明令「本檔不得自寫家數」，這是同型漂移第二次。
- 🔴 **DOCROT 成效量測點的編號要對**：b9 之 `review-r1`..`r12` 全是**規格**審查輪（DOCROT 上線前），`doc_friction_ratio` 要量的是**上線後**的前兩輪 review ⇒ 實際落在 **`review-r13`／`review-r14`**（Task 9.1 實作後的審碼輪）。兩輪皆須 ≤0.30 且每輪 ≤20 條；不達＝DOCROT 失敗，回報使用者重議，**禁順手開新 epic**。

## 待辦分流
- **待使用者**（看板偏好，非技術）：`白話說明/` 22 份是否整理、怎麼併（GAP-3 佔 8 份、5404 行）。
- **下一步（技術，不問使用者）**：stamp-r1 三家回報 → 收斂＋`debt_clear` → 若 APPROVED 則領 impl token 進 `Task 9.1`；若 REJECTED 則依阻擋條一次修訂後重派。

- 🔴 **新發現的系統性缺口（具名殘留，`blocked-by`，**未**開新 epic）**：`docs/` 底下帶 `RECONCILE-STAMP` 的檔**沒有任何一份**能通過 `reconcile_stamps_check`——`gate.sh register-output` 原只收 `handoffs/`，而 provenance 要求審計中有指向被戳記檔**自身**的事件。本輪只把 `docs/SPLITUNIFY_SPEC.D-002.md` 加進既有封閉白名單 `scripts/stampable_artifacts.txt`（該檔正是為此型缺口而建）；`GAP3_EVENT_UX_SPEC.D-001.md`、`GAP3_EVENT_UX_TODO.D-001`..`D-006` **未一併加入**，因其戳記是否對應現行 body hash 未經查證，盲加＝把未驗證的背書寫成既成事實。另 `handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md`（D-001 定案檔）之戳記 hash 與 HEAD body hash **不符**（戳記 `9e1ef3d1` vs 實際 `e3f2847d`），亦即「D-001 三家戳記定案」目前機械上是紅的。

## 坑
- 🔴 **SPEC 戳記要能過 provenance，需 `gate.sh register-output <task> <SPEC路徑> --kind stamp --family <fam>` 逐家各跑一次**（`--kind stamp` 才會跳過 verdict parser；檔名無 `-<family>.md` 尾碼時 family 必須顯式給）。且該 SPEC 路徑須先列入 `scripts/stampable_artifacts.txt`。
- 🔴 **委員裁決塊不合契約時，出路是 `debt_clear.sh:394` 的設計路徑：主委修檔後 `register-output`**，不是重派。本輪 codex 寫 `CLOSED: 2026-09-13`（日期而非 finding ID）被 `verdict_parse` 拒收 ⇒ 主委只改那一行為空值並於檔內註明，其餘一字未動，再 register-output 即解鎖。
- **同輪重派仍須使用者 terminal**（gate 見本輪 OPEN 債即拒發 token）。命令形式：`ROUND_ID=<id> bash scripts/cx_run.sh <family> <brief> <out>`；主控端再 `register-output` → 移走舊收斂目錄後 `reconcile_build` 重建 → `debt_clear`。**永遠不要 kill 執行中的 `committee_run`**。
- **session 名不得重複**（fail-closed）：`20260911-splitunify-b9-consult-r1` 早在 2026-09-12 用過，本輪只好用 `-r2`。派前先 `bash scripts/debt_ledger.sh --list | grep <session>`。
- **SPEC 戳記輪的 brief-kind 要用 `closure` 不是 `stamp`**：`brief_conformance_check.sh:425` 要求 `stamp-target` 須 `handoffs/` 前綴，而 SPEC 在 `docs/`。既有作法見 `handoffs/20260912-SPLITUNIFY-D001-STAMP-BRIEF.md`。
- **synth 處置欄的反引號 token 必須逐字出現在標的檔**（`spec_xref_check --synth`），否則寫檔 hook 擋；`延後→Task N.N` 之說明**不得有巢狀全形括號**，且目標 Task 須已存在於 `--todo`。
- `committee_run` 的 harness exit code 不可信：本輪 `committee_rc=0` 但 harness 報 failed（尾端 `tail /tmp/*.log` 因沙箱重導而找不到檔）。**讀 `committee_rc=` 那行**。
- 🔴 `pytest` 一律逐檔明列路徑；`-k` 只過濾執行、**不減少收集**，無路徑即從 rootdir 收全套。
- 🔴 `reconcile_build.sh` 一律帶 `--mode review`；`debt_clear` 用 `--round-id <id> --session <name> --lock <sources.lock>`（不吃位置參數）。
- 🔴 治理測試既有紅基準（2026-09-13 實測）：19 個涉及 `brief_conformance_check` 的檔為 **30 failed／523 passed／3 skipped**；乾淨 HEAD worktree 為 **35 failed／512 passed**。根因＝隔離 repo 依賴複製清單缺 `scripts/quant_standard_check.sh`／`ticket_batch_check.sh`。`test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` 會**掛住**，跑治理回歸須排除。
- 🔴 改 SPEC／TODO 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次；grep **不得加排除條件**。
- 🔴 **不再擴建治理工具**（2026-09-12 定）；同型缺陷降級為具名殘留。
