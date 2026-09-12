# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY`（大；RISK a,b,c）｜b8 已結案｜現在：b9 規格 `D-002` 第十二次修訂完成、R11 債已清，R12 待派**

## 現況
- **b8 已結案**：三輪三家審碼收斂、回歸為零（對照實驗證實浮現的 10 筆紅為既有紅）。
- **b9（`docs/SPLITUNIFY_SPEC.D-002.md`）**：偵察 1 輪＋找碴 **R1–R11** 共十一輪全部收斂，**R4–R11 債已清**（R11 `round_id=67a7dba5-cebc-47d6-aaa9-27a3c2ff507e`）。SPEC 現為 **v12**。
- **v12 落地（依 R11 十二條／六群；五群採納、一群部分採納）**：①N1 §V 值相等斷言補**可執行入口**＝`EventSamplePipeline.run`，`metadata.split_unify` 層明確併入 `SU-RESID-9A-UI` 殘留；②N2 register 25 → **29**（補 `pipeline.py:760-762` summary counts、`split_projection.py:559-569`／`:716-719` 門檻路徑、`EventTablesPanel.tsx:361` 計數顯示、`tables.py:372` 之 `assignments` 消費面），**駁回**「API 計數模型」一列；③N3 座標契約改為「validator 由 producer／adapter 層呼叫、投影端只讀 `row_index_local`、座標系禁混用」＋四案真值表進 §V；④N4 (G-4d)① 增 `O_EXCL` write-once／外部錨／主檔 11 鍵 fail-closed ＋三條 §V 母斷言 ＋ `M-SU-D2-33`；⑤N5／N6 兩條 mutation 舊字面同步。mutation 32 → **33**（ID 01–33 連續無重複）。
- **閘況（皆已跑）**：`obligation_block_check` rc=0、`doc_format_precheck` rc=0（SPEC／TODO）、`spec_xref_check --synth` 對 **r1–r11 十一份** rc=0。
- **本輪性質變化**：R11 的 12 條**首度全是「我上一版修法本身的缺陷」**（四群打穿 v11 新寫的 M2／M5／M6／M7，兩群是 mutation 舊字面未同步），不是新開面向。十一輪 findings 數 15／11／15／8／11／16／15／14／21／13／12。

## 坑
- impl token 900 秒過期須重領；commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b9`；task-id／session 之日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 一律**限定路徑**提交（`git commit -F - -- <路徑…>`）：不限定會把暫存區裡別票的 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 帶進宣稱檢查。`handoffs/*` 被 `.git/info/exclude` 排除，須 `git add -f`（例外：`handoffs/run_receipts/*.log` 已 negate，`.json` 仍要 `-f`）。
- commit 訊息含「全綠／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，**零豁免**。🔴 **G-7 是 warn-only**，提示不必補 trailer。
- 🔴 **收斂檔寫「主委已複驗」會被宣稱閘擋**：須 `VERIFY:<receipt-id>` 背書，且 receipt 之 `runtime_class` 要夠——純腳本恆為 `static_only`，**只有 pytest 且有節點通過**才升 `helper_smoke`。做法＝把探針包成 pytest（用 importlib 載入探針本體，不重寫），再 `venv/bin/python scripts/run_with_receipt.py --claim-id <id> -- venv/bin/python -m pytest <檔> -q`。
- 🔴 **`spec_xref_check --synth` 要求 synth 處置欄的反引號字面與 SPEC **逐字**相同**（空格、全形、行號都算）；`--files` 那道則是「removed 行的反引號 token 未出現在任何 added 行即視為被拿掉」⇒ 改寫時必須把原有字面寫回。此坑已犯**九次**。
- 🔴 **`obligation_block_check` 區塊內只允許 `**(n.n) …**` 行型**，表格與散文一律放到 `<!-- OBLIGATIONS-END -->` 之後。
- 🔴 **`reconcile_build.sh` 預設 `--mode discovery`**，lock 不帶 `round_id`，而 `debt_clear` 要求 `lock.round_id == --round-id` ⇒ 收斂前須 `bash scripts/reconcile_build.sh <session> --mode review --rebuild`（只改 lock，不動 synth，已實測）。`completeness_check` 用法是 `--lock <sources.lock> --synth <synth.md>`。
- 🔴 **`debt_clear` 會 race**：`committee_run` 尾段才寫最後一家的 `committee_family_result`，太早清債會報「家族 X 無 committee_family_result」；查 `.claude/gate/audit.log` 確認再跑。
- 🔴 **凡結論是「某物不存在」，查法必須先自證完備**；窄 regex 的零命中不算證據。
- 🔴 **自證七條（每次修訂後必跑）**：①新增內容落點 ②被取代的舊內容是否同步改掉 ③每條 mutation 是否有 §V 母斷言 ④條數與表列一致 ⑤Task 正文與 §V 對稱 ⑥骨架佔位已刪 ⑦🔴 **跨既有介面／座標契約的「可實作性」**（R11 新增；不是文字位置對不對，而是寫下的落點在既有契約下能不能實作——v11 的 M5 兩案皆牴觸 `D-001-C2` (4.10) 即為證據）。本輪自證抓到三處漏改（兩處條數、一處分類未同步）。

## 下一步
1. commit＋push（限定路徑；R11 交件／synth／探針／receipt 須 `git add -f`）。
2. 更新 `白話說明/SPLITUNIFY施工進度.md` 與 `白話說明/流程摩擦記錄.md`。
3. R12：寫 brief → `gate.sh dispatch`（五個必填旗標）→ `committee_run.sh --session <name> <brief> <out前綴> codex,composer,grok -- <gate flags>` → `reconcile_build --mode review` → 群集表 → 歸戶／completeness → `register-output` ×3 → `debt_clear`。
4. 三家戳記通過後才進 `Task 9.1` 實作；其後 `D1` 走 R 重開重戳；最後一批 `R-5`。
