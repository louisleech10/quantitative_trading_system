# HANDOFF — 當前任務狀態

## 現況

<!-- BEGIN GENERATED: handoff-current -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 03-005 | R-5 | 進行中 | docs/SPLITUNIFY_SPEC.md Phase 10 | 使用者 2026-09-18 放行 v7；撰寫第 10 批施工清單（Task 10.1～10.7），待三家審查凍結後施工 |
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
<!-- END GENERATED: handoff-current -->

## 待辦

<!-- BEGIN GENERATED: handoff-todo -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 02-013 | SU-B10A | 未開工 | docs/SPLITUNIFY_TODO.md §C-10 | Task 10.1 讀取者改指＋Task 10.2 IC 事件特徵列鍵更正 |
| 02-014 | SU-B10B | 未開工 | docs/SPLITUNIFY_TODO.md §C-10 | Task 10.3 投影判側錨點改為特徵列鍵＋v10 golden |
| 02-015 | SU-B10C | 未開工 | docs/SPLITUNIFY_TODO.md §C-10 | Task 10.4 邊界與標籤參數解析下沉＋逐事件處置帳 |
| 02-016 | SU-B10D | 未開工 | docs/SPLITUNIFY_TODO.md §C-10 | Task 10.5 事件掃描端接線與請求／回應契約 |
| 02-017 | SU-B10E | 未開工 | docs/SPLITUNIFY_TODO.md §C-10 | Task 10.6 前端＋Task 10.7 真實資料兩端對證與 UAT 登記 |
| 03-003 | R-3 | 未開工 | docs/SPLITUNIFY_TODO.md §E | UAT 排在最後一次做（使用者裁定） |
| 03-004 | R-4 | 未開工 | docs/SPLITUNIFY_TODO.md §E | 另開接線票；本票只保證 assignments 語意不變 |
| 03-005 | R-5 | 進行中 | docs/SPLITUNIFY_SPEC.md Phase 10 | 使用者 2026-09-18 放行 v7；撰寫第 10 批施工清單（Task 10.1～10.7），待三家審查凍結後施工 |
| 03-007 | SU-RESID-V8-ATTEST | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：專案導入 commit 簽章或受保護分支 |
| 03-008 | SU-RESID-PAUSED-NO-RESULT | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：audit 出現同輪同家 failed 且無產出之結果列 |
| 03-009 | SU-RESID-COMMITTEE-MODEL-EVIDENCE | 未開工 | docs/SPLITUNIFY_TODO.md §E | 實測兩 CLI 非互動輸出之型號與 effort 欄位 |
| 03-010 | SU-RESID-9A-UI | 未開工 | docs/SPLITUNIFY_SPEC.md R5-C5 | 隨 R-5 實作批交付（規格 R5-C5） |
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
| 03-013 | SU-RESID-4 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 IC 切分契約 |
| 03-014 | SU-RESID-5 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 SplitPlan 欄位契約 |
| 03-015 | SU-RESID-C5-TARGETS | 未開工 | docs/SPLITUNIFY_TODO.md Task 9.3 | 待觸發：Task 9.3 驗收段兩條觸發條件 |
| 04-001 | HP-PLAINDOCS | 未開工 | 白話說明/README.md | 使用者決定 白話說明/ 各份是否整理、怎麼併（GAP-3 佔 8 份） |
<!-- END GENERATED: handoff-todo -->

## 坑

- 🔴 **本檔文法**（定義於 `scripts/live_doc_registry.json` 之 handoff 段；寫入前由 `scripts/live_doc_write_guard.sh` 擋，commit 前再以 `--staged` 擋）：「現況」「待辦」只放生成區塊——狀態與下一步改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；「坑」手寫；「進行中紀錄」只准條目標記與指標行 `- <日期>：<識別碼或 v<N>> → <反引號路徑或 commit>`，條目所含識別碼一轉完成，整則移至 `docs/HANDOFF_ARCHIVE.md`。
- 🔴 **新增行不得同行寫「識別碼＋狀態字面」**（全部狀態 key 之識別碼，含 `docrot2_status_keys`），也不得寫刪除線、考古字面、canonical finding ID；需要引用過時樣本時放 fenced code block。出處與輪次留在 `handoffs/reconcile/` 收斂檔。
- 使用者 2026-09-15 對 DOCROT2 之逐字裁定見 `docs/DOCROT2_SPEC.md` §C；委員組成之唯一權威＝`scripts/governance_families.json` 之 `active_stampers`（本檔不寫家數）。
- 🔴 **SPEC 戳記要能過 provenance，需 `gate.sh register-output <task> <SPEC路徑> --kind stamp --family <fam>` 逐家各跑一次**（`--kind stamp` 才會跳過 verdict parser；檔名無 `-<family>.md` 尾碼時 family 必須顯式給）。且該 SPEC 路徑須先列入 `scripts/stampable_artifacts.txt`；`docs/GAP3_EVENT_UX_SPEC.D-001.md` 與 GAP3 UX TODO 各延伸檔未列入，其戳記未對證現行 body hash。
- 🔴 **委員裁決塊不合契約時，出路是 `debt_clear.sh:394` 的設計路徑：主委修檔後 `register-output`**，不是重派；裁決行 `CLOSED:` 只准填 finding ID，填日期會被 `verdict_parse` 拒收。
- **同輪重派＝兩個指令，不經使用者終端機**（該家最新結果非 success 時）：①`bash scripts/gate.sh redispatch --round-id <id> --family <fam> --reason <文字>` 取得綁定許可並印出唯一可放行之指令；②以 Bash 原樣執行該指令（不得加重導向或串接）。前次產出會自動保存於 `handoffs/redispatch_archive/`，銷帳前收斂檔須引用保存檔路徑並逐條處置其 finding。重派達上限時改棄置：`bash scripts/debt_clear.sh --abandon --round-id <id> --kind collection-failed --reason <文字> --approver <文字>`，再以新 session 重審。**永遠不要 kill 執行中的 `committee_run`**。
- **session 名不得重複**（fail-closed），格式 `<YYYYMMDD>-<epic>-b<N>-<kind>-r<N>`（`scripts/session_name_check.sh`）；派前先 `bash scripts/debt_ledger.sh --list | grep <session>`。
- **SPEC 戳記輪的 brief-kind 要用 `closure` 不是 `stamp`**：`brief_conformance_check.sh:425` 要求 `stamp-target` 須 `handoffs/` 前綴，而 SPEC 在 `docs/`。既有作法見 `handoffs/20260912-SPLITUNIFY-D001-STAMP-BRIEF.md`。
- **synth 處置欄的反引號 token 必須逐字出現在標的檔**（`spec_xref_check --synth`），否則寫檔 hook 擋；`延後→Task N.N` 之說明**不得有巢狀全形括號**，且目標 Task 須已存在於 `--todo`。
- `committee_run` 的 harness exit code 不可信，**讀 `committee_rc=` 那行**。
- 🔴 `pytest` 一律逐檔明列路徑；`-k` 只過濾執行、**不減少收集**，無路徑即從 rootdir 收全套。
- 🔴 `reconcile_build.sh` 一律帶 `--mode review`；`debt_clear` 用 `--round-id <id> --session <name> --lock <sources.lock>`（不吃位置參數）。
- 🔴 `handoffs/` 整包在 `.git/info/exclude`：brief、委員產出、收斂檔只在本機，commit 時 `git add` 會被拒；commit 訊息之 REF 仍須指向含 VERIFY／SIGNOFF／RECONCILE-STAMP／CLOSED／APPROVED 字樣之檔。
- 新增 `scripts/` 檔或改掛載後跑 `bash scripts/list_active_mechanisms.sh --write`，否則寫檔 hook 擋；在 fixture 目錄建檔名含 `TODO`／`SPEC` 之樁檔須先 `bash scripts/gate.sh artifact`。
- 🔴 **既有紅（2026-09-14 實測，非 DOCROT2 改壞）**：`tests/governance/test_debt_emit.py` 之 7 條 `test_b3_*`（隔離 repo 缺 `scripts/prev_review_resolve.sh`）；`tests/governance/test_gate_deny_fields.py::test_01_corpus_a_covers_decision_branches`（錨點 `INPUT="$(cat)"` 已漂移）；`scripts/obligation_block_check.sh` 對 `docs/SPLITUNIFY_SPEC.D-002.md` 結構性 rc=1（舊段更正註記逐字引用裁決編號，義務區塊內零違規）。
- 🔴 治理測試既有紅基準（2026-09-13 實測）：19 個涉及 `brief_conformance_check` 的檔為 30 failed／523 passed／3 skipped；根因＝隔離 repo 依賴複製清單缺 `scripts/quant_standard_check.sh`／`ticket_batch_check.sh`。`test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` 會**掛住**，跑治理回歸須排除。
- 🔴 **治理全套基準（2026-09-17 實測，改動前後兩棵樹並行各約 1:52，單跑約 1:40）**：`venv/bin/python -m pytest -q tests/governance --deselect tests/governance/test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` → HEAD `c7edce12` 為 **69 failed／2377 passed／3 skipped**，與改動前 `61aa55b0`（69 failed／2329 passed）之 FAILED 名稱集合**完全相同**。既有紅名單須以「在改動前之 commit 建暫時 worktree 重跑同一批檔、逐名比對」證明（比對法：`git worktree add -f <tmp> <舊commit>` → 於該目錄跑同檔 → `comm` 比對 FAILED 名稱集合）。判回歸看**名稱集合差集**，不要比總數。
- 🔴 **後加的守衛會遮蔽先前的守衛**：兩道守衛對同一情境給出相同 rc 時，先前那道被改壞後測試仍綠＝該道從此無人守（同一票內犯三次）。修法＝每個拒絕出口輸出可區分的原因碼（例 `RD_GUARD_REASON=<code>`），**測試斷言原因碼而非只斷言被拒**；加新守衛時必須同時檢查它是否吃掉既有 mutation 的鑑別力。
- 🔴 **確認點越多、縫越多**：把檢查拆成前後兩道，兩道之間就是可用窗口（同長度覆寫落於其間兩道都過）。正解是**合併成單一確認點並置於最後**，且最後一次觀測要比**內容本身**、不得以長度或 `mtime` 當代理（`mtime` 偵測力取決於檔案系統解析度）。殘餘＝最後一次觀測取得資料之後，具名於 `docs/REDISPATCH_SPEC.md` §C 誠實邊界⑧。
- 🔴 **`gov_check.sh` 段 2（白話說明過期）是 fail-stop 前段，一紅就吃掉段 5／6 的全套測試**；且段 2 目前**結構性紅**：`白話說明/` 有五份無 WATCHED 定義（fail-closed）、兩份他票文件過期於 `c3a58988`、`SPLITUNIFY施工進度.md` 之 WATCHED 涵蓋整個 `scripts/`（動任何治理腳本即過期）。⇒ 收票前要拿真實測試證據就**直接跑 pytest**，不要只看 `gov_check` 的 rc。
- 🔴 **放水語閘會擋下派工單裡的否定用法**（為說明「為何停在這裡」而引用被禁字面亦擋）。正解＝改寫成可證偽條件，**不得替自己加白名單**。
- 🔴 改 SPEC／TODO 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次；grep **不得加排除條件**。
- 🔴 **治理工具擴建**：2026-09-12「不再擴建治理工具」；2026-09-15 使用者放寬，逐字「允許擴建治理工具，就是要修正DOCROT沒做好之處」（範圍＝DOCROT2）。DOCROT2 已於 2026-09-17 收票，該放寬隨之用盡，9/12 之「不再擴建」恢復為現行（我的判斷；新治理需求先問使用者）。
- 🔴 **DOCROT2 成效報表之量測對象不含續作舊票**：`scripts/docrot2_metrics.sh` 之 cohort＝「首個 review 輪序號大於 `closure_sequence`（4831）之票鍵（task-id 前兩段）」，`20260911-SPLITUNIFY` 首個 review 輪序號為 3610 ⇒ SPLITUNIFY 之後續輪次**永遠不會**被報表選中，報表會量其後第一張新開之票。要以 SPLITUNIFY 輪次檢驗成效，須直接讀 audit 中該輪之 `docrot2_round_metric` 事件逐條套契約四條及格線。
- 🔴 **finding 類別（DOCROT2 Task 3.1，門檻 audit 序號 4778）**：門檻後開債之輪，委員交件每條 finding（含 `P3-00` sentinel）須一行 `**類別**: <值>`（值集與語意見 `scripts/governance_verdicts.json`），`cx_run` 交件當下擋；主委收斂檔群集表須加第 5 欄「主委類別」，兩欄不一致之 ID 須列於 `### 類別不一致` 段一行並附處置 token，否則 synth 寫入 hook 與 `debt_clear` 擋。類別行文法唯一實作＝`scripts/_finding_category.py`（HTML 註解內、fence 內不算）。
- 🔴 **`debt_clear` 銷帳前會寫 `docrot2_round_metric`**（門檻後之輪；缺類別、缺主委欄或寫入失敗即拒銷）；成效報表 `bash scripts/docrot2_metrics.sh`：`scripts/docrot2_metric_contract.json` 之 `closure_sequence`＝4831（2026-09-17 收票寫入）；量測對象＝其後首張開 review 輪之票的前兩輪，該票開輪前報表為 rc=1（`cohort-unknown`），前兩輪銷帳後才出四條及格線結果。
- 🔴 **`committee_round_open` 之 `brief_kind` 為必填**：測試輔助碼開輪須帶（值取 brief 行首 `brief-kind:`）；要模擬上線前無 `brief_kind` 之舊輪，用 `tests/governance/_debt_probe_helper.py` 之 `legacy_round_open_registry`（只改沙箱副本登記檔）。隔離沙箱之複製清單須含 `DOCROT2_HELPER_SCRIPTS`，否則 `--single`／`debt_clear` fail-closed。
- 🔴 **`tests/governance/conftest.py` 對每條測試設 `DEBT_AUDIT_OVERRIDE`**：測試「會寫 audit 之腳本」時必須顯式把 env 指向沙箱 audit，否則事件寫到 conftest 之暫存 audit，斷言沙箱 audit 會落空。
- 🔴 **登記表 `<檔>:<行>` 只驗「非註解非空行」，語意漂移不會紅**：改任何被引用之腳本後，以 `git show HEAD:<檔> | sed -n <行>p` 取舊行內容、`grep -nF` 找新行號逐列更正；2026-09-16 對讀時另抓到四列原本即指錯行（`}`、他函式之 `return 0` 等）。
- 🔴 **`gate.sh dispatch --impl-self` 與 `git commit` 必須以 `&&` 串接**：以 `;` 串接時 gate 拒發 token 而 commit 仍成立，post-commit 記 `token_fresh=false`，pre-push 段 1c 擋推送且事後領 token 不追認；未推送時之出路＝`git reset --soft HEAD~1`、先處理 gate 拒發原因（例：先銷帳）、重領 token 後重新 commit。
- 🔴 **委員名冊變動會使舊收斂檔戳記不足**：`active_stampers` 增加家族後，`--impl-self --adversarial <收斂檔>` 要求現行全員戳記；出路＝只派缺席家族之 stamp 輪補簽（brief-kind stamp、stamp-target 指該收斂檔）。
- 🔴 **全專案遷移判定有兩個模式**：`bash scripts/live_doc_registry_check.sh --migration` 讀工作樹（含未追蹤檔）；`--migration --index` 判暫存快照（清冊、內容、登記、`fact_keys`、殘留清單與生成器皆取 index），pre-commit 用後者。命中消失時 `scripts/docrot2_migration_residuals.json` 該列須同 commit 刪；新增狀態識別碼可讓未被編輯之既有行命中，改 `fact_keys.json` 後先跑一次。暫存檢查一律取快照，讀工作樹之判定會被「只暫存一半」或 `git rm --cached` 繞過。
- 🔴 **委員並行跑會就地改寫檔案之 mutation 執行器會互相污染**（2026-09-17 閉合輪實例：一家兩次執行重疊，另一家看到未還原之改壞並自行 `git checkout` 還原）。收件後先 `git diff HEAD -- scripts tests docs` 對證零差異再收斂。
- 🔴 **生成器無參數模式有 2 秒預算測試**（`test_govb1_factkey_gen.py::test_generator_runs_under_two_seconds`）：2026-09-17 新增一個狀態 key 前實測已 1.92 秒；`_fk_validate_shape` 七次 jq 合一後 1.65 秒。再加 key 前先量；worktree 基準量時須補齊 `handoffs/` 物件，否則生成器提早失敗、耗時失真。
- 🔴 **verdictgate 對 `<root>-B<N>-*` 派工要求前批每條 blocked finding 有同家後續 `CLOSED:`**：規格層輪次用 `x` 命名不經此閘；前批欠帳時以「只核對本家 ID」之閉合輪補（brief-kind closure、session kind stamp，附逐條 ID 清單附件），銷帳後重跑 `bash scripts/verdictgate_check.sh <root> <N> <前批 review 前綴>,<前批 stamp 前綴>` rc=0 才開下一批（2026-09-17 SPLITUNIFY b9 實例：108 條一輪閉合）。
- 🔴 **`spec_xref_hook.sh` 之 synth 對證取的是字母序最早、不是最新之「修訂標的」收斂檔**（`grep -l … | head -1`）：寫 `docs/SPLITUNIFY_SPEC.md` 永遠對 `20260911-splitunify-x-consult-r2/synth.md` 對證而報 `split_projection.py:569` 缺失；D-001 同型報 b8 收斂檔。屬誤報，本輪收斂檔以 `bash scripts/spec_xref_check.sh --synth <本輪 synth> <標的>` 另跑為準（已報使用者，未改工具）。
- 🔴 **委員裁決行多個 ID 須以半形逗號分隔**：`BLOCKED-BY: A; B` 會被 `verdict_parse` 拒收（`result_state=verdict_rejected`）而使 `debt_clear` 拒銷；出路＝主委把分號改逗號後 `bash scripts/gate.sh register-output <task> <委員檔>`（2026-09-17 x-review-r15 實例）。brief 格式硬約束段已加註此條。
- 🔴 **FF 特徵表列時間戳＝K 線開盤時刻**（列之主週期欄含該根收盤；跨週期欄 `OPEN_MINUS` 只含收盤 ≤ 列開盤之高週期 K 線）。凡以時間戳取「決策時點可用之特徵列」，鍵須為「收盤 ≤ 決策時點之最後一根」之**開盤**（對齊收據 `last_bar_open_ms`），**不是** `feature_cutoff_ms`（收盤時刻）。2026-09-17 真實資料三家實跑：IC 事件路徑 `_run_event_label_stages` 自 `fe5f715e`（8/28）起以 `feature_cutoff_ms` 為鍵，165／165 事件讀到晚一根（BOP 之 IC 0.074 被灌成 0.286）；修正排入 `docs/SPLITUNIFY_SPEC.md` v7 之 `R5-C9`（使用者裁定不得列殘留）。對證探針：`handoffs/20260911-splitunify-x-consult-r4-probes/`。
- 🔴 **事件掃描端與 IC 端之分析用標籤參數不同源**：IC 路徑以 `event_label_spec`（預設導出在 `api/routes/ic_analysis.py` 之 `_resolve_event_batch`）建分析副本再對齊，事件掃描端 `_prepare` 用匯入原值；預設參數下兩端 `label_window_rows` 即不同（144／156），邊界差 12 小時。統一解析排入 v7 之 `R5-C10`。
- **session 名之 kind 封閉集＝`impl|review|stamp|consult|fix`**：閉合輪之 session 用 `stamp`、brief 行首 `brief-kind: closure`（例 `20260911-splitunify-b9-stamp-r13`）。
- **Bash 命令列含委員家族名字面（以豎線串接之三家名）會被 `gate_check.sh` 判為派工而擋**：要列家族時從 `scripts/governance_families.json` 以 `jq` 取，不在命令列寫字面。
- 🔴 **規格寫入之權宜作法（2026-09-17）**：`docs/SPLITUNIFY_SPEC.md` 以 scratchpad 組稿後 `cp` 入檔；寫入前以同內容之 Write payload 餵 `bash scripts/live_doc_write_guard.sh`（rc=0 才 `cp`），寫入後跑 `doc_format_precheck.sh`、`spec_xref_check.sh --files <HEAD 版> <新版>`、`obligation_block_check.sh`。日後小幅修改一律用 Edit。

## 進行中紀錄

<!-- HISTORY-BEGIN -->
<!-- ENTRY: R-5 -->
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-consult-r3/synth.md`
- 2026-09-17：R-5 → `docs/SPLITUNIFY_SPEC.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-review-r14/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-review-r15/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-stamp-r7/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-stamp-r8/synth.md`
- 2026-09-17：R-5 → `白話說明/SPLITUNIFY規格白話.md`
- 2026-09-17：R-5 → `handoffs/20260911-SPLITUNIFY-B9-STAMP-R13-BRIEF.md`
- 2026-09-17：R-5 → `handoffs/20260911-SPLITUNIFY-X-CONSULT-R4-BRIEF.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-b9-stamp-r13/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-consult-r4/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-review-r16/synth.md`
- 2026-09-17：R-5 → `handoffs/reconcile/20260911-splitunify-x-stamp-r9/synth.md`
- 2026-09-18：R-5 → `handoffs/reconcile/20260911-splitunify-x-stamp-r10/synth.md`
- 2026-09-18：R-5 → `handoffs/reconcile/20260911-splitunify-x-review-r17/synth.md`
<!-- HISTORY-END -->
