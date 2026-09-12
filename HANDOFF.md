# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY`（大；RISK a,b,c）｜b8 已結案｜現在：b9 規格 `D-002` 第十一次修訂完成、三閘綠，R11 待派**

## 現況
- **b8 已結案**：三輪三家審碼收斂、回歸為零（對照實驗證實浮現的 10 筆紅為既有紅，非本批造成）。
- **b9（`docs/SPLITUNIFY_SPEC.D-002.md`）**：偵察 1 輪＋找碴 **R1–R10** 共十輪全部收斂，**R4–R10 債已清**（R10 `round_id=6b721c53-aed2-4f3e-bc11-fe3186c99018`）。SPEC 現為 **v11**。
- **v11 落地（依 R10 十三條／八群，全部採納）**：(G-4e) 第三份判準改為 fixture 字面 `expected_side` ＋明禁與投影／oracle 共用 helper；§V `metadata.split_unify` 由「帶該鍵」升級為**值相等**；`baseline` **刪**舊鍵 `n_test`、改出 `n_test_events`／`n_test_samples`；補 `Task 9.4`／(G-4d)①／座標 adapter 三條 §V 母斷言；(G-4d)① 指定不可變 `splitunify_golden.v8.json` ＋ `.sha256` ＋版本化新鍵；新增 **(5.6) 消費面 register 25 條**（取代並存的「16 處／20 處」兩套數字）；`SU-RESID-9A-UI` 觸發式改廣義 call-site 掃描。mutation 31 → **32 條**（ID 01–32 連續、無重複）。
- **閘況（皆已跑）**：`obligation_block_check` rc=0、`doc_format_precheck` rc=0（SPEC／TODO）、`spec_xref_check --synth` 對 **r1–r10 十份** 皆 rc=0。
- **核心目標之不可達形態已連中四次**（只加欄位 → 沒改 caller → 四參數閘先擋 → producer 內 merge 與輸出欄），根因同一句：**義務寫進規格 ≠ 施工單派到落點**。

## 坑
- impl token 900 秒過期須重領；commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b9`；task-id／session 之日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 一律**限定路徑**提交（`git commit -F msg -- <路徑…>`）：不限定會把暫存區裡別票的 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 帶進宣稱檢查而被擋。`handoffs/*` 被 `.git/info/exclude` 排除，新交件檔須 `git add -f`。
- commit 訊息含「全綠／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，且 commit **零豁免**。🔴 **G-7 是 warn-only**，其提示不必補 `Governance-Scope` trailer。
- 🔴 **改 SPEC 最常犯的坑（已八次）**：`spec_xref_hook.sh` 判準＝removed 行之反引號 token 未出現在任何 added 行即視為「被拿掉」⇒ 改寫時**必須把原有反引號字面逐字寫回**；synth 處置欄之字面亦須**逐字**出現於 SPEC（含全形省略號、`=` 而非 `==`、行號）。
- 🔴 **`obligation_block_check` 之義務區塊內只允許 `**(n.n) …**` 行型**，表格與散文一律放到 `<!-- OBLIGATIONS-END -->` 之後。
- 🔴 **`debt_clear` 會 race**：`committee_run` 背景程序尾段才寫最後一家的 `committee_family_result`，太早清債會報「家族 X 無 committee_family_result」；查 `.claude/gate/audit.log` 確認該事件落檔再跑即可。
- 🔴 **凡結論是「某物不存在」，查法必須先自證完備**（不截斷、不要求同一行）；窄 regex 的零命中不算證據。
- 🔴 **自證六條（每次修訂後必跑）**：①新增內容落點 ②被取代的舊內容是否同步改掉 ③每條 mutation 是否有 §V 母斷言 ④條數與表列一致 ⑤Task 正文與 §V 對稱 ⑥骨架佔位已刪。本輪據此抓到兩處「16 處」未同步、兩條 mutation 無母斷言。

## 下一步
1. commit＋push（限定路徑；R10 三份交件與 synth 須 `git add -f`）。
2. 更新 `白話說明/SPLITUNIFY施工進度.md` 與 `白話說明/流程摩擦記錄.md`。
3. R11：寫 brief → `gate.sh dispatch` 自行領 token → `committee_run.sh` 派三家 → `reconcile_build.sh` → 手填群集表 → 歸戶／completeness → `gate.sh register-output` ×3 → `debt_clear.sh`。
4. 三家戳記通過後才進 `Task 9.1` 實作；其後 `D1` 走 R 重開重戳；最後一批 `R-5`（不得與未完成之 `D1` 同批上線）。
