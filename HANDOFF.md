# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY`（大；RISK a,b,c）｜b8 已結案｜現在：b9 規格 `D-002` 第十三次修訂完成、R12 債已清、🔴 停輪判準已觸發 ⇒ 規格審查結束，下一步直接進 `Task 9.1` 實作**

## 現況
- **b8 已結案**：三輪三家審碼收斂、回歸為零（對照實驗證實浮現的 10 筆紅為既有紅）。
- **b9（`docs/SPLITUNIFY_SPEC.D-002.md`）**：偵察 1 輪＋找碴 **R1–R12** 共十二輪全部收斂，**R4–R12 債已清**（R12 `round_id=6877c963-8947-43eb-a32a-0ddb66c4353f`）。SPEC 現為 **v13**；mutation **34** 條、register **29** 條，ID 皆連續無重複。
- 🔴 **v13 落地（依 R12 十三條／七群，全部採納）**：O1 §V 兩條 metadata ASSERT 移出當輪（`EventPipelineResult` 無 `metadata` 欄，與「併入 `SU-RESID-9A-UI` 殘留」同段矛盾）；O2 `Task 9.5` 增外部錨寫入步驟（逐字 `V8_BASELINE_SHA256=`）＋§V 錨點存在性斷言＋`M-SU-D2-34`；O3 §V 與 `M-SU-D2-30` 同步改為「進入 derive **之前**由具名層已呼叫 validator」；O4 具名事件路徑呼叫點（`EventSamplePipeline.run` 在 `derive_event_split_from_plans` 之前，`feature_index` 作 `ts`、`train_plan.symbol` 廣播作 `symbols`）；O5 §C 條數改為指向 register、不再重複寫數字；O6 `C5-13` 明列三處甲類；O7 `Task 9.1` 之「三處」實為四處且整段隨 O1 移入殘留。
- 🔴 **停輪判準已觸發（規格審查結束）**：R12 十三條**無一新面向**，全在打 v12 剛寫的段落；三家一致確認 register 涵蓋性、「API 計數模型」駁回、(G-4e) 殘餘標註、metadata 併殘留**四項已閉**；剩餘七群全為字面同步與具名落點，無一需重新設計。⇒ **不再派規格審查輪**，殘餘缺陷交由實作期 pytest 暴露。
- **v12 落地（依 R11 十二條／六群；五群採納、一群部分採納）**：①N1 §V 值相等斷言補**可執行入口**＝`EventSamplePipeline.run`，`metadata.split_unify` 層明確併入 `SU-RESID-9A-UI` 殘留；②N2 register 25 → **29**（補 `pipeline.py:760-762` summary counts、`split_projection.py:559-569`／`:716-719` 門檻路徑、`EventTablesPanel.tsx:361` 計數顯示、`tables.py:372` 之 `assignments` 消費面），**駁回**「API 計數模型」一列；③N3 座標契約改為「validator 由 producer／adapter 層呼叫、投影端只讀 `row_index_local`、座標系禁混用」＋四案真值表進 §V；④N4 (G-4d)① 增 `O_EXCL` write-once／外部錨／主檔 11 鍵 fail-closed ＋三條 §V 母斷言 ＋ `M-SU-D2-33`；⑤N5／N6 兩條 mutation 舊字面同步。mutation 32 → **33**（ID 01–33 連續無重複）。
- **閘況（皆已跑）**：`obligation_block_check` rc=0、`doc_format_precheck` rc=0（SPEC／TODO）、`spec_xref_check --synth` 對 **r1–r11 十一份** rc=0。
- **本輪性質變化**：R11 的 12 條**首度全是「我上一版修法本身的缺陷」**（四群打穿 v11 新寫的 M2／M5／M6／M7，兩群是 mutation 舊字面未同步），不是新開面向。十一輪 findings 數 15／11／15／8／11／16／15／14／21／13／12。

## 坑
- impl token 900 秒過期須重領；commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b9`；task-id／session 之日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 一律**限定路徑**提交（`git commit -F - -- <路徑…>`）：不限定會把暫存區裡別票的 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 帶進宣稱檢查。`handoffs/*` 被 `.git/info/exclude` 排除，須 `git add -f`（例外：`handoffs/run_receipts/*.log` 已 negate，`.json` 仍要 `-f`）。
- commit 訊息含「全綠／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，**零豁免**。🔴 **G-7 是 warn-only**，提示不必補 trailer。
- 🔴 **收斂檔寫「主委已複驗」會被宣稱閘擋**：須 `VERIFY:<receipt-id>` 背書，且 receipt 之 `runtime_class` 要夠——純腳本恆為 `static_only`，**只有 pytest 且有節點通過**才升 `helper_smoke`。做法＝把探針包成 pytest（用 importlib 載入探針本體，不重寫），再 `venv/bin/python scripts/run_with_receipt.py --claim-id <id> -- venv/bin/python -m pytest <檔> -q`。
- 🔴 **`spec_xref_check --synth` 要求 synth 處置欄的反引號字面與 SPEC **逐字**相同**（空格、全形、行號都算）；`--files` 那道則是「removed 行的反引號 token 未出現在任何 added 行即視為被拿掉」⇒ 改寫時必須把原有字面寫回。此坑已犯**九次**。
- 🔴🔴 **改 SPEC 的唯一正確動作：改之前先 grep 列出該決定的所有落點**（2026-09-12 使用者質問後定；**這條取代並撤銷先前的「插入不重寫」**）。
  - **為什麼撤銷「插入不重寫」**：那條只避開 xref 閘報錯，卻讓**舊說法留在原地**與新說法並存——R12 的 O1／O3／O6 正是這個形態（插入了新說法、舊說法還在、兩者矛盾）。它是問題的成因之一，不是解法。
  - **真根因不是紀律，是資訊結構**：一個決定散在 `Task`／`§V`／mutation 表／register 表／`§N` **五個區段**，而文件裡沒有任何地方列出「這個決定住在哪幾處」⇒ 我每次靠記憶回想，十三次修訂漏了十三次。
  - **做法（可查核，非空話）**：改任一決定前，先 `grep -n "<該決定的關鍵字面>" docs/SPLITUNIFY_SPEC.D-002.md`，把**全部命中**列出，逐條決定改／不改；改完**再 grep 一次**確認無遺漏。grep 輸出即證據，應貼進 commit 訊息或收斂檔。
  - **實證**：R12 六條缺陷，每一條都會被這個動作抓到——`grep "metadata.split_unify"` 會同時吐出 Task 9.1／§V／`M-SU-D2-03`；`grep "validate_split_pair_integrity"` 會吐出 Task 9.2b／§V／`M-SU-D2-30`；`grep "tables"` 會吐出 (5.1)／(5.3)／`C5-13`／`C5-29`。
  - 🔴 **grep 不得加排除條件**（見下一條坑：排除條件會濾掉待抓目標）。
  - 🔴 **上條只解單檔內；跨檔靠下一條。**
- 🔴🔴 **文檔病之三家裁定**（2026-09-12 DOCROT consult R1；債已清 c0bd1479）
  - **主因（三家獨立撞題）＝一個決定在活文複述五處以上且無索引**。碼證：`Task 9.2b` 活文 19 次、`metadata.split_unify` 11 處、`validate_split_pair_integrity` 5 處、數字字面 27 處。REF:handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md
  - **次因＝修訂考古寫進活義務**（活文 109 個版本標記、沿革段佔 25%）。🔴 **主委原把次因當主因，排序被三家推翻**。REF:handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md
  - **三道格式閘同時 rc=0 之狀態，不足以推出規格無語意互斥**（三家撞題，群集 D3）：`spec_xref_check` 檔頭自白只驗存在不驗語意等價；codex 另揭 Bash 與生成器寫檔不觸發 Edit 與 Write 之文件 hook，產出端有洞、具名殘留。
  - **「七成浪費」被限縮**（群集 D4）：grok 判其對 R8 之後成立，外推到全部 164 條會抹掉 R1 至 R6 的真架構收益（末五輪 73/164 約 45%）。REF:handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md
  - 🔴 **路線裁定（經使用者指正後改寫；原「採 grok 較窄版、不建強制機制」已作廢）**：原案之 F1 至 F3 雖可機械驗證，但**無機制強制執行**，與自證七條同型而該清單在 R12 仍中六條 ⇒ 屬紀律型，使用者逐字指正「靠紀律你絕對失敗」。另兩條駁回理由亦不成立——「語意閘不可行」係誤用（composer 提的是**結構閘**非語意判斷），「不再擴建治理工具」係主委自定且已自標未驗證假設。**新裁定＝判定採 grok（純計數、零維護、不需 YAML registry），強制採 composer（掛既有 `PostToolUse` 文件檢查鏈，不新開 epic）**：活文版本標記歸零、數字字面恰一處、單一決定活文計數 ≤3，違反即寫檔當下報。
  - 🔴 **成效判定（下一張中大票驗收）**：若仍出現「改一處漏一處」型 finding 且占比未下降 ⇒ **本裁定失敗**，屆時改採 composer 之機械方案。
- ⚠️ **【未驗證假設，不是已處理】一件事實只寫在一個權威位置，其他檔一律寫指標、不得複述**（2026-09-12）。
  - 🔴 **為什麼標「未驗證」**：本 session 我已經寫錯一條規則（「插入不重寫」，實際有害、已撤銷）、寫漏一條（「改前先 grep」，第一次執行就漏掉 `test_summary_has_all_twelve_keys`——函式名不含關鍵字，grep 抓不到）。**每次被指出問題就往 HANDOFF 加一條規則，本身就是「看起來有做」**；使用者 2026-09-12 當面點破：「你不用落地啊，你根本不知道有沒有用」。
  - **唯一的驗證方式**：下一輪審查中「改了 A 沒同步 B」的同型 finding 數是否下降。**在那之前不得宣稱此問題已處理**。
  - **這不是新規則，是我沒遵守既有的**：`CLAUDE.md` 的七條解耦規則早已標明「本表＝唯一權威(canonical single source)，ARCHITECTURE／DEV_GUIDE 只得 pointer 回本節，不得自列不同版本」，且註明是因為漂移過才加。
  - **我違反的實證（本 session）**：R12 那七群，我在 **synth 群集表／SPEC 沿革／HANDOFF／白話進度表**各寫一份完整敘述；`grep` 顯示同一批事實（v13／十二輪／164 條／29 條）散在 **12 個檔案**。改一處要同步四到十二處，記憶必漏。
  - **做法**：寫任何「現況／條數／輪次／決策結論」之前，先問「這件事已經有權威位置了嗎」；有就寫 `見 <檔>:<錨點>`，**不得**把內容再抄一份。
  - **唯一例外＝白話說明**：它是**翻譯給不同讀者**（使用者），不是複述，該存在；但它引用的**數字**仍須指向權威，不得自己記一份——本 session 的「151／164」就是自己記了一份才會漏改。
  - 🔴 **已知待整理（尚未處理，具名殘留）**：`白話說明/` 有 19 份文件，其中 **GAP-3 有六份**在講同一件事（`GAP-3施工進度`／`GAP-3施工看板`／`GAP-3還差什麼才算完整`／`GAP-3還沒做的事`／`GAP-3驗收清單`／`GAP-3規格42個Task勾選表`），另有兩份並存的「接下來」（`接下來要做什麼.md`／`接下來要做的票.md`）。**合併與否屬使用者的看板偏好，不由我自行決定**；但在合併前，新增內容一律只進其中一份、其餘寫指標。
- 🔴 **同一個數字不得寫在兩個地方**（同上）：本輪 register 條數同時活在節標題／表標題／§RISK／§R 回退句／(5.6) 內文**五處**，我改了三處漏兩處。約定＝條數只存在於 **register 表標題**，其餘一律寫「見 (5.6) register」。重複真相源一消除，「條數與表列不符」這類錯誤**結構上不會發生**，不必靠檢查。
- 🔴 **不再擴建治理工具**（2026-09-12 定）：「改了 §V 沒回寫 mutation」（累計八次）雖可用 `spec_xref_check --synth` 同型機制機械化，但主目標已被治理擠掉三次，**不加第四次**；該類降級為具名殘留，靠自證清單第②③條擋。
- 🔴 **`obligation_block_check` 區塊內只允許 `**(n.n) …**` 行型**，表格與散文一律放到 `<!-- OBLIGATIONS-END -->` 之後。
- 🔴 **`reconcile_build.sh` 預設 `--mode discovery`**，lock 不帶 `round_id`，而 `debt_clear` 要求 `lock.round_id == --round-id` ⇒ 收斂前須 `bash scripts/reconcile_build.sh <session> --mode review --rebuild`（只改 lock，不動 synth，已實測）。`completeness_check` 用法是 `--lock <sources.lock> --synth <synth.md>`。
- 🔴 **`debt_clear` 會 race**：`committee_run` 尾段才寫最後一家的 `committee_family_result`，太早清債會報「家族 X 無 committee_family_result」；查 `.claude/gate/audit.log` 確認再跑。
- 🔴 **凡結論是「某物不存在」，查法必須先自證完備**；窄 regex 的零命中不算證據。
- 🔴 **自證的查法本身會有洞**（2026-09-12 R12 實例）：我跑殘留掃描時用 `grep -v "v11\|v12\|沿革"` 排除歷史敘述，而**待抓的那一行正好含「v11」字樣**，被自己的過濾條件濾掉 ⇒ 兩家委員抓到我漏的 `25 條`。判準：**自證用的排除條件，必須先確認它不會濾掉待抓目標**；寧可不過濾、逐行看。
- 🔴 **自證七條（每次修訂後必跑）**：①新增內容落點 ②被取代的舊內容是否同步改掉 ③每條 mutation 是否有 §V 母斷言 ④條數與表列一致 ⑤Task 正文與 §V 對稱 ⑥骨架佔位已刪 ⑦🔴 **跨既有介面／座標契約的「可實作性」**（R11 新增；不是文字位置對不對，而是寫下的落點在既有契約下能不能實作——v11 的 M5 兩案皆牴觸 `D-001-C2` (4.10) 即為證據）。🔴 **R12 再收緊**：落點**必須具名到「檔:函式:插入位置」**，寫不出具名就是還沒想清楚——v12 寫「由 producer／adapter 層呼叫」而沒具名，三家實查發現事件路徑上該層根本不存在。本輪自證抓到三處漏改（兩處條數、一處分類未同步）。

## 下一步
1. **R12 收斂**（已派出，`session=20260911-splitunify-b9-review-r12`）：`reconcile_build --mode review` → 手填群集表 → 歸戶／`completeness_check --lock <sources.lock> --synth <synth.md>` → `register-output` ×3 → `debt_clear`。
2. 🔴 **停輪判準（2026-09-12 定，取代「三家全放行才進實作」）**：R12 若開出的條目**仍全是打 v12 自己寫的段落、沒有新面向**，則第十三次修訂後**直接進 `Task 9.1` 實作**，剩餘規格缺陷交給實作期的 pytest 抓。依據：十一輪 findings 數 15／11／15／8／11／16／15／14／21／13／12 無下降，但 R11 十二條**全部**在打 v11 的修法——面向已收斂，剩下的是修法品質，而修法品質靠再審規格的邊際效益遞減；實作期有測試，「寫了要做卻沒做」「指名走不到的落點」這類會自動變紅。
3. 其後 `D1` 走 R 重開重戳；最後一批 `R-5`（不得與未完成之 `D1` 同批上線）。
