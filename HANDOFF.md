# HANDOFF — 當前任務狀態

## 現況

<!-- BEGIN GENERATED: handoff-current -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
<!-- END GENERATED: handoff-current -->

## 待辦

<!-- BEGIN GENERATED: handoff-todo -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 01-003 | D2C | 未開工 | docs/DOCROT2_TODO.md §B | 票 B-64（同輪重派死結）落地後開工 Task 3.1–3.2 |
| 01-004 | D2D | 未開工 | docs/DOCROT2_TODO.md §B | D2C 審碼閉合後開工 Task 4.1 |
| 03-003 | R-3 | 未開工 | docs/SPLITUNIFY_TODO.md §E | UAT 排在最後一次做（使用者裁定） |
| 03-004 | R-4 | 未開工 | docs/SPLITUNIFY_TODO.md §E | 另開接線票；本票只保證 assignments 語意不變 |
| 03-005 | R-5 | 未開工 | docs/SPLITUNIFY_TODO.md §E | 規格 R 重開後實作，排在 DOCROT2 之後 |
| 03-007 | SU-RESID-V8-ATTEST | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：專案導入 commit 簽章或受保護分支 |
| 03-008 | SU-RESID-PAUSED-NO-RESULT | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：audit 出現同輪同家 failed 且無產出之結果列 |
| 03-009 | SU-RESID-COMMITTEE-MODEL-EVIDENCE | 未開工 | docs/SPLITUNIFY_TODO.md §E | 實測兩 CLI 非互動輸出之型號與 effort 欄位 |
| 03-010 | SU-RESID-9A-UI | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：api/ 出現 EventSamplePipeline.run 生產呼叫 |
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
| 03-013 | SU-RESID-4 | 未開工 | docs/SPLITUNIFY_SPEC.D-001.md 殘留節 | 待觸發：下一次動 IC 切分契約 |
| 03-014 | SU-RESID-5 | 未開工 | docs/SPLITUNIFY_SPEC.D-001.md 殘留節 | 待觸發：下一次動 SplitPlan 欄位契約 |
| 03-015 | SU-RESID-C5-TARGETS | 未開工 | docs/SPLITUNIFY_TODO.md Task 9.3 | 待觸發：Task 9.3 驗收段兩條觸發條件 |
| 04-001 | HP-PLAINDOCS | 未開工 | 白話說明/README.md | 使用者決定 白話說明/ 各份是否整理、怎麼併（GAP-3 佔 8 份） |
| 04-002 | HP-REDISPATCH | 未開工 | scripts/fact_keys.json 票 B-64 | 與兩家委員共識決定修法（同輪、同家、無產出之重派不再須使用者終端機）→ SPEC／TODO 審定後實作；排在 D2C 之前 |
<!-- END GENERATED: handoff-todo -->

## 坑

- 🔴 **本檔文法**（定義於 `scripts/live_doc_registry.json` 之 handoff 段；寫入前由 `scripts/live_doc_write_guard.sh` 擋，commit 前再以 `--staged` 擋）：「現況」「待辦」只放生成區塊——狀態與下一步改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；「坑」手寫；「進行中紀錄」只准條目標記與指標行 `- <日期>：<識別碼或 v<N>> → <反引號路徑或 commit>`，條目所含識別碼一轉完成，整則移至 `docs/HANDOFF_ARCHIVE.md`。
- 🔴 **新增行不得同行寫「識別碼＋狀態字面」**（全部狀態 key 之識別碼，含 `docrot2_status_keys`），也不得寫刪除線、考古字面、canonical finding ID；需要引用過時樣本時放 fenced code block。出處與輪次留在 `handoffs/reconcile/` 收斂檔。
- 使用者 2026-09-15 對 DOCROT2 之逐字裁定見 `docs/DOCROT2_SPEC.md` §C；委員組成之唯一權威＝`scripts/governance_families.json` 之 `active_stampers`（本檔不寫家數）。
- 🔴 **SPEC 戳記要能過 provenance，需 `gate.sh register-output <task> <SPEC路徑> --kind stamp --family <fam>` 逐家各跑一次**（`--kind stamp` 才會跳過 verdict parser；檔名無 `-<family>.md` 尾碼時 family 必須顯式給）。且該 SPEC 路徑須先列入 `scripts/stampable_artifacts.txt`；`docs/GAP3_EVENT_UX_SPEC.D-001.md` 與 GAP3 UX TODO 各延伸檔未列入，其戳記未對證現行 body hash。
- 🔴 **委員裁決塊不合契約時，出路是 `debt_clear.sh:394` 的設計路徑：主委修檔後 `register-output`**，不是重派；裁決行 `CLOSED:` 只准填 finding ID，填日期會被 `verdict_parse` 拒收。
- **同輪重派仍須使用者 terminal**（gate 見本輪 OPEN 債即拒發 token；直接跑 `cx_run.sh` 亦須 token）。委員 CLI 回「Selected model is at capacity」而無產出即屬此情形。命令形式：`ROUND_ID=<id> bash scripts/cx_run.sh <family> <brief> <out>`；主控端再 `register-output` → 移走舊收斂目錄後 `reconcile_build` 重建 → `debt_clear`。**永遠不要 kill 執行中的 `committee_run`**。
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
- 🔴 改 SPEC／TODO 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次；grep **不得加排除條件**。
- 🔴 **治理工具擴建**：2026-09-12「不再擴建治理工具」；2026-09-15 使用者放寬，逐字「允許擴建治理工具，就是要修正DOCROT沒做好之處」（範圍＝DOCROT2）。

## 進行中紀錄

<!-- HISTORY-BEGIN -->
<!-- ENTRY: B-63 -->
- 2026-09-15：B-63 → `docs/DOCROT2_SPEC.md`
- 2026-09-15：B-63 → `docs/DOCROT2_TODO.md`
- 2026-09-15：B-63 → `handoffs/reconcile/20260915-docrot2-b1-review-r2/synth.md`
- 2026-09-15：B-63 → commit `80fb3cb2`
- 2026-09-15：B-63 → `handoffs/reconcile/20260915-docrot2-b2-review-r5/synth.md`
- 2026-09-15：B-63 → `docs/HANDOFF_ARCHIVE.md`
<!-- HISTORY-END -->
