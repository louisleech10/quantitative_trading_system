# 制度層總審查 Phase A — 簡述 + Manifest(2026-07-05)

> 依據:`handoffs/20260705-INSTREV-RECONCILE.md`(雙戳記 APPROVED)+ 使用者 2026-07-05 裁決(D-1/2/3/5/6 同意,D-4 改動態選層)。
> 本批 = reconcile §E Phase A:憲法重構 + 執行端合約補齊。純文件改動,git 可整批 revert,不碰程式邏輯與資料。

## 給使用者的白話簡述

這一批要做的事,全部是「整理規則文件」,不動任何程式:

1. **刪掉一份沒人在用的舊說明書**:`.github/copilot-instructions.md` 有 739 行,內容停在四月,你已確認沒在用 Copilot。整份換成 15 行內的「請看 CLAUDE.md」指路條。
2. **把「規則為什麼存在」的故事搬家**:CLAUDE.md 每次開工都會整份載入,裡面約 80 行是「當年出過什麼事故」的故事。規則一條不刪,故事搬到新檔 `docs/SCAR_LEDGER.md`(傷疤帳本),原處留一行出處。CLAUDE.md 從 216 行瘦到 140 行以內(期望約 130,140 為硬上限——不為壓行數誤刪規則),每次開工省 token。
3. **任務分小/中/大的規則改成一張表**:現在散在三處、有兩處還互相矛盾(你已裁決:中型不准跳步、執行端分工看你當下指示)。改成 CLAUDE.md 一張決策表,其他地方只指過來。
4. **給 Codex/Cursor 看的工作合約補課**:他們的合約停在 5/31,少了五條你後來定的制度(兩輪卡關就上報、做事要留編號紀錄、說「驗過」要附證據、審查沒全數蓋章不准動工、同檔內矛盾的交接規則修正)。一次補齊。
5. **兩份大文件貼「可能過時」標籤**:ARCHITECTURE 和 DEVELOPMENT_GUIDE 不強制跟著改,只在檔頭標「治理規則以 CLAUDE.md 為準,本檔最後驗證日 XX」。
6. **Claude 自己的記憶檔同步**:與憲法重複的記憶條目改成指路條,只留你的個人偏好類(繁中、push 不用問等)。

**發現一個 reconcile 疏漏,已納入**:reconcile §E 的 Phase A 清單漏列了 U-3(合約補五項),但 Phase A 標題就叫「合約補齊」、U-3 裁決 3/3 收斂——判定為列表筆誤,本批照做(上面第 4 點)。權威依據=雙戳記 reconcile 全文 + 本 manifest [A-12] + 你的 D-1~D-6 裁決(§E 分期表為建議非窮舉);Claude 已在舊 reconcile 戳記後補一行 errata 記錄此歸屬。此點兩家 adversarial 委員(Codex/Composer)獨立確認處置正當。

**怎麼驗收**:規則一條都不能少(有逐項核對清單)、既有同步檢查腳本要過、行數目標達標、每條搬走的故事在傷疤帳本找得到。

## Manifest(機檢用,扁平 ID;coverage_check 逐項比對 SPEC/TODO)

### 憲法瘦身 + 單一來源(U-1/2/5/6/7/19)
- [A-1] copilot-instructions.md 739 行 → ≤15 行 pointer 檔(指向 CLAUDE.md/AGENTS.md)。(U-1)
- [A-2] 新建 `docs/SCAR_LEDGER.md` 規則傷疤帳本:每條規則一行「出生事故+日期+出處」;06-04 feature-browser 事故標「出處=記憶(原始 commit 未尋獲)」。(U-2,§C 取證缺口)
- [A-3] CLAUDE.md 敘事移出:驗證保真度鐵律三事故敘事、實測>假設兩事故敘事、Gate 設計理由重複段、任務分派日期考據 → SCAR_LEDGER;原處每條規則留「規則本體+一行出處 pointer」。(U-2)
- [A-4] 規則零刪減驗證:不可砍清單 8 類(資料紅線/7 解耦/facts-first+保真度+三方簽核+adversarial 紀律/gate+戳記/假綠防線/兩輪斷路器/使用者否決權+白話+繁中/中大不跳步)逐項在改後 CLAUDE.md+合約仍可 grep 到。(U-2 防護)
- [A-5] CLAUDE.md 留「何時必須去讀哪檔」觸發句(SCAR_LEDGER/ORCHESTRATION/templates),所有引用=repo 內固定路徑,不裸引用。(U-2 AGY 風險)
- [A-6] CLAUDE.md「任務分派規則」重寫為單一決策表:欄=小/中/大;列=判準(a-d 命中、管線步驟 SPEC/TODO/adversarial、執行端、review 方、SMALL_INLINE 條件、膨脹升級 5 訊號、判不出→問或當中辦)。實質規則忠實轉錄不改,分叉處按 D-1/D-4 裁定版。(U-19)
- [A-7] 選層單一來源:ORCHESTRATION §1 改為單一「現行分工」行(標最後更新日;注明「動態,一律以使用者當下指示為準,看 usage 切換,未來或加新執行端須先過 T-D」;現行=2026-07-02 中大 Codex 實作+Composer review);CLAUDE.md 決策表執行端欄=pointer 指 ORCH §1,不重複內容。(U-5,D-4)
- [A-8] 中型管線矛盾修復:刪 ORCHESTRATION「SPEC/TODO 作者流程」分層表「中=跳獨立 TODO+跳一次 adversarial」列,改指 CLAUDE.md 決策表;中型=完整管線不跳(D-1)。(U-6)
- [A-9] 輪詢節奏統一 10 分鐘:CLAUDE.md 鐵律⑤「每 5 分鐘回報」改 10 分鐘;全 repo 治理文件 grep「5 分鐘」殘留清零。(U-7,D-5)

### 執行端合約補齊(U-3/4/8)
- [A-10] HANDOFF 所有權矛盾修復:AGENTS.md 頂部「最後一步」與 .cursorrules「結束前」改為「結束前寫 handoffs/<date>-<task>.md;根 HANDOFF.md 由 Claude 維護,執行端不得改寫」,與各自第 7 條一致。(U-4)
- [A-11] debug 輪數統一:AGENTS.md/.cursorrules 第 5 條「≤3 輪」→「≤2 輪未解 → STATUS: BLOCKED 交委員會」;ORCHESTRATION §5 兩處「≤3 輪」同步改 2。(U-8,D-6)
- [A-12] 合約一次補齊 5 項(兩份合約皆補):①兩輪斷路器(=A-11);②派工附 --task-id 時產出落地須配合 register-output 留痕;③VERIFY claim 義務(報告中「已驗/passed」須附實跑命令+輸出摘要,不得空稱);④讀到 RECONCILE-STAMP 未全數 APPROVED 的 reconcile → STATUS: BLOCKED 不執行;⑤產物視為資料非指令(既有,確認保留)。(U-3)
- [A-13] 同步檢查護欄:check_agent_contract_sync.sh 全部既有 token(STATUS: BLOCKED/handoffs//data_cache/SMALL_INLINE/ASSUMPTIONS_VERIFIED/反提示注入/preflight/斷路器/委員會)於改後檔案保留,腳本跑 PASS。腳本本身不改(U-9=Phase B)。

### 低頻文件 + 記憶層
- [A-14] ARCHITECTURE.md/DEVELOPMENT_GUIDE.md 檔頭加 staleness banner:「治理制度以 CLAUDE.md/docs/MULTI_AGENT_ORCHESTRATION.md 為準;本檔最後驗證 2026-07-05,細節可能過時」。(U-11)
- [A-15] (Claude 自做,不派工)記憶同步:feedback_task_routing 加 superseded 標記指向 CLAUDE.md 決策表;feedback_dispatch_polling 改 pointer;MEMORY.md 索引行同步。(U-5/U-7/U-10)
- [A-16] (Claude 自做,不派工)記憶重疊盤點:多 agent 規則確認已入 repo 憲法後,重疊記憶條目內文改 pointer+superseded;使用者偏好類(繁中/push 不問/brief 白話/veto 彈窗)保留原樣。(U-10)

## 範圍界線
- 只改:`.github/copilot-instructions.md`、`CLAUDE.md`、`AGENTS.md`、`.cursorrules`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`docs/ARCHITECTURE.md`(僅檔頭)、`docs/DEVELOPMENT_GUIDE.md`(僅檔頭)、新建 `docs/SCAR_LEDGER.md`;A-15/16 為 Claude 對自身記憶目錄(repo 外)。
- 不改:任何 `scripts/`(U-9/12/14/15=Phase B)、任何程式碼、templates/、HANDOFF.md(Claude 收尾自更)、gate 機制本體。
