# Handoff

**Agent**: Claude(Opus 5) | **Branch**: main | 實作＝主委自任（`implementer=claude`）；
討論／review／adversarial＝**codex+composer+grok 三家全員**

> 🔴 本檔超過 CLAUDE.md 之 ≤30 行規約，**結構上不可能達成**：下方「未修的活缺口」節是
> **機器輸入**（`governance-ticket-closure` 之導出來源），長度由未收案票數決定。
> 刪它會使 `test_e3_ticket_union_matches_key_rows` 轉紅（實測過）。修訂案待使用者裁定。

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 🔴 **票（61 張）之狀態與問題描述** | **`docs/GOV_TICKET_SOT.md`——唯一一份，其餘全部作廢** |
| 施工順序／批次狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 之 generated block |
| ~~票的內容~~（**已作廢**） | ~~`handoffs/20260801-GOV-AMEND-BACKLOG.md`~~ 只剩長文可查，**狀態欄一律不採信** |
| 給使用者的現況 | `白話說明/接下來要做什麼.md` |
| 委員名冊 | `scripts/governance_roles.json`＋`governance_families.json` |
| `B-49` as-built 落差與殘留 | `docs/GOV_B49_ASBUILT_DELTA.md` |

🔴 改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；
本檔**不得手寫**票／批次的狀態字面值（偵測器 fail-closed；已實際擋過多次，**每個 session 都會再擋**）。

# 🔴🔴🔴 待辦清單（唯一來源，機器投影——**本節不得手寫**）

> 改法：編輯 `scripts/fact_keys.json` 之 `governance-worklist` → 跑
> `bash scripts/gen_fact_key_blocks.sh --write`。**完成就把該列狀態改成 `收案`。**
> 欄名見表頭（亦為機械產物）。手寫狀態字面值會被 fail-closed 擋下。

<!-- BEGIN GENERATED: governance-worklist -->
| 序 | 項目 | 狀態 | 內容 |
|---|---|---|---|
| 010 | WL-01 | 收案 | P0 前置：fact_keys schema 由平面列擴為具名欄＋表格投影（columns／render）。三家 review＋閉合複驗＋戳記核可；票 B-25 殘留⑥之 schema 阻塞已解除 |
| 020 | WL-02 | 收案 | P1-a 判準資料化：判準入註冊表＋三道機械檢查（狀態列舉封閉／同適用範圍同條件不得相異期望／判準宿主區塊外不得陳述期望結束狀態）。字面設計經實測為零訊號已由三家 consult 改寫；三輪委員（consult→review→closure）、三家戳記核可。🔴 語意互斥不被攔截，見 docs/GOV_CRITERIA_REGISTRY.md 殘留 1 |
| 030 | WL-03 | 收案 | P1-b 機制證據登記：平台機制入專用登記表（receipt:／assumed: 封閉格式，receipt 須指向被驗樹內之真檔且非 symlink）＋顯式 opt-in 宿主之 `- 改法` 子樹掃描。三輪委員（consult→review→stamp×2）、兩份收斂檔各三枚戳記。🔴 誠實邊界：現樹訊號近零（opt-in 五宿主子樹 195 行、平台機制命中 0），價值在面向未來；子樹旁路四度被委員實構（發現曲線未收斂，改 parser 須重跑候選組）；偶發紅之 fail-open 已封但原始觸發未獨立重現。具名殘留 1-11 見 docs/GOV_MECHANISM_REGISTRY.md |
| 040 | WL-04 | 未開工 | P1-c 戳記整行由 harness 自動生成，消滅 64 位 hex 手抄。票 B-54。🔴 BLOCKED：使用者定「票 SoT 統一與產出端覆蓋之確保都完成才能進本項」⇒ 前置＝governance-sot-plan 之 S0.1～S5.3 全部收案。設計已由三家 consult 定案（收斂檔 20260813-govwl04-x-consult-r1），票之修法方向須改寫：禁實作『自動生成整行』，改三條 harness 後處理 |
| 050 | WL-05 | 未開工 | P2 指令 tokenize 化：逐命令位置解 argv[0] 比對封閉 executor_clis。票 B-59（併 B-61 同型）。屬大重寫，須另立 epic |
| 060 | WL-06 | 未開工 | P3 測試空心／假綠之機械判準。併入票 B-25，不新開票（既有：PATH劫持1條已修、test_verify_gate系列3條、未列入排除清單2條） |
| 070 | WL-07 | 未開工 | 管線豁免提案交三家（免SPEC/TODO之三條件；延伸檔，範圍由 govb1_scope.manifest 導出以免凍結變永久） |
| 080 | WL-08 | 收案 | CLAUDE.md 去除會漂的值：code review 家數改指向 ORCH §1；pytest 秒數/測試數改為不漂的定性判準 |
| 090 | WL-09 | 未開工 | 六張無批次歸屬之票排入執行序：B-48／B-50／B-51／B-52／B-53（排序凍結已解除，見 GOVERNANCE_EXECUTION_ORDER 之 RULED-BY；backlog:3129 之舊句已作廢） |
| 100 | WL-10 | 未開工 | 站級施工順序不在本表重述，見 docs/GOVERNANCE_EXECUTION_ORDER.md 之 governance-execution-order 區塊 |
<!-- END GENERATED: governance-worklist -->

## 🔴🔴 `WL-04` 之前置：票 SoT 統一與產出端覆蓋（**本節亦為機器投影，不得手寫**）

> 使用者 2026-08-13 定：治理票的**新增／刪減／修改／註解／狀態變更只能有一套**，
> 且**這些確保都完成才能進 `WL-04`**。
> 改法同上：編輯 `scripts/fact_keys.json` 之 `governance-sot-plan` → 跑 `--write`。
> **由上而下第一個未完成者即當前工作**；`S0.x` 全部是後續各階段的前置。

<!-- BEGIN GENERATED: governance-sot-plan -->
| 序 | 步驟 | 狀態 | 內容 | 驗收條件 |
|---|---|---|---|---|
| 0010 | S0.1 | 收案 | 定義票之全集如何機械列舉。🔴 原描述之前提已被實測推翻並更正：backlog 之 ## 標題共 61 張全為標準 B-<數字>，格式並無例外；真正的問題是**票表混入 backlog 不存在的識別碼**（B3R 無 ## B3R 標題，僅在他票內文被提及）＋ ## 標題另有群組標題等非票項。⇒ 列舉須同時封閉「哪些 ## 是票」與「票表不得含非票識別碼」。我起草→三家審 | bash scripts/ticket_universe.sh --check rc=0；重跑兩次輸出逐位元組相同；SoT 票集合恰等於列舉結果 |
| 0020 | S0.2 | 收案 | 定義**唯一一套**狀態語意。🔴 原描述之前提已被實測推翻並更正：backlog 之 TICKET-STATUS 共 25 張（非 14），且有四態 OPEN／PARTIAL／DONE／PROVISIONAL——**並非只有兩態、亦非表達不出「做了一半」**。真正的問題是兩套值**語意不對應且無映射**（closure 用 未開工／部分完成／收案），加上兩邊涵蓋的票不同。我起草→三家審 | 四個狀態值全在 status_enum；逐值反例——在受管檔寫「票號＋該值」皆須 rc≠0（含 已完成／狀態未確認） |
| 0030 | S0.3 | 收案 | 定義票之其餘欄位（標題／內容／註解／證據指標），使新增·刪減·修改·註解·狀態變更全部只能經同一套。我起草→三家審 | 欄位齊備且 --check rc=0；改狀態只改 fact_keys 一處即全投影同步（反例：改投影檔須 rc≠0） |
| 0040 | S0.4 | 收案 | 逐張盤點 61 張票之真實狀態＋證據。🔴 我自產一版 ＋ 三家平行，逐張對照；分歧以證據裁定不數人頭（三家上輪各得 11／13／不同集合，因三來源本就對不齊）。每張須有可查證據（commit／測試名／收斂檔路徑），無證據者標「狀態未確認」不得猜 | SoT 中狀態未確認為 0；或未確認者逐張有具名理由且理由非「尚未查」 |
| 0050 | S0.5 | 收案 | 落成機器可讀之 SoT（新 fact-key）。驗收：61 張全在、欄位齊備、--check 綠 | 61 張全在、--check rc=0、已納入 status_keys |
| 0060 | S0.6 | 收案 | 🔴 消滅第二套：backlog 之 TICKET-STATUS 與 governance-ticket-closure 降為投影或作廢，不再是可獨立編輯之狀態源。**不可逆體例變更，動手前改法先給使用者確認** | 舊來源皆標作廢；反例——在舊來源改狀態不影響 SoT，且新寫入被擋 |
| 0070 | S0.7 | 收案 | 機械閘：SoT 之外手寫票狀態即 fail-closed（沿用既有手寫狀態偵測器）。驗收＝反例可構造。我→三家審。🔴 落法非新建閘，而是把兩個缺漏值補進 status_enum 使既有偵測器涵蓋完整。🔴 兩值的入列理由**不同**，勿混為一談（CODEX-R1-P1-01 實測更正主委原敘述）：狀態未確認＝ticket-sot rows 實際在用（43 列），原缺即偵測有洞；已完成＝rows **並未使用**（rows 實際值僅 未開工／部分完成／狀態未確認），入列理由為 S0.2 驗收條件括號明列，且加入後即在 GOVERNANCE_EXECUTION_ORDER 之非生成區塊抓到一處真實手寫漂移（該處寫 B1 已完成，而批次表權威值為 已落地） | 反例可構造：於 SoT 之外手寫任一狀態值即 rc≠0（逐值驗） |
| 0110 | S1.1 | 收案 | 封死幽靈票：enforcement 之 對應票 欄必須在票全集內。🔴 S0.4／S0.6 後**原實例已失效並換形態**（S0.7 後稽核更正）：B-38 現已在票 SoT（部分完成），原「在登記表、不在票表」不再成立；現存實例改為 enforcement 之對應票欄含**非票號值** G-7 與 測試套件——前者是判準代號、後者是泛稱，皆不在票全集內。⇒ 落法須先定義「合法對應票值」之封閉集合（票號 ∪ 顯式允許之非票標的），否則直接套用會把這兩列判死。依賴 S0.5（已收案） | enforcement 之對應票填不存在之票號 ⇒ rc≠0 |
| 0120 | S1.2 | 收案 | rc=2 略過 改為可判別之 fail-closed。🔴 落法＝以**承載目錄是否存在**拆成兩路（封閉可判定）：目錄在而設定檔不在 ⇒ 環境異常 ⇒ rc=3 ⇒ fail-closed；目錄本身不在 ⇒ 真非主控端（fixture／沙箱）⇒ 仍略過。如此既堵住「刪檔即跳過全部掛載點對證」，又不使最小 fixture 整批誤紅。兩個對照測試成對釘住，證明修法精準非一律判紅。🔴 此洞為主委為修測試而引入（codex：『大聲印出不是阻擋』） | settings.json 缺席時 rc≠0（非略過印訊息） |
| 0210 | S2.1 | 收案 | 收案綁定不只認「收案」字面，改綁 SoT 之所有完成語意。🔴 S0.6 後**繞過路徑清單已縮減**（S0.7 後稽核更正）：原列三條中，「backlog DONE」與「closure」兩條**已隨作廢與刪除消失**；現存繞法為①票 SoT 標「部分完成」而未登記覆蓋 ②governance-worklist 標「收案」③governance-batch-status／governance-sot-plan 標「收案」「已落地」——後兩者非票但同屬完成語意。問題本質不變（綁定只認單一字面），惟須以現存 status_keys 為準重新列舉（grok 實構） | 以任一「完成」語意標記票而未登記覆蓋 ⇒ rc≠0（不限收案字面） |
| 0220 | S2.2 | 收案 | 票在標完成**之前**即預警其產出端覆蓋缺口，非最後一刻才擋 | 票標完成前即產生警告，且有測試釘住 |
| 0310 | S3.1 | 收案 | 登記表支援多種 hook 事件（PreToolUse／PostToolUse／UserPromptSubmit／Stop）。🔴 現行只認 PostToolUse，會誤判 runtime 檢查為「應前移卻未前移」 | 登記表可填 PreToolUse／UserPromptSubmit／Stop 並通過對證；填不存在之掛載 ⇒ rc≠0 |
| 0320 | S3.2 | 收案 | 訂分類判準：內容型（單次編輯可判定）vs 一致性型（多步後才成立）。🔴 一致性型本質上做不到寫入前擋（實證：改註冊表在 PreToolUse 下會死鎖），該類是真豁免非藉口 | 內容型與一致性型各有實例入表，且分類判準有測試 |
| 0410 | S4.1 | 收案 | 依 SoT 機械導出所有已交付之票，不再靠判定式。🔴 本步由 S0.4 之完成而**實質達成**（S0.7 後稽核認定）：狀態填入 SoT 後，導出即為單一 jq 過濾，無需另建判定式。可重跑指令見 .claude/tmp/s04_export_delivered.sh（以 jq 對 governance-ticket-sot 之 rows 過濾狀態為 部分完成 或 收案 者取票號欄）⇒ 現得 17 張。🔴 此處刻意不內嵌 jq 指令：render=table 之儲存格禁管線符號，寫入會切碎表格（產出端守衛實際擋下過）。誠實邊界：機械化的是**導出動作**，不是狀態**判定**本身——判定仍由 S0.4 之人工＋三家完成，且其歸屬判準未機械化（CODEX-R4-P1-01） | 已交付票集合由 SoT 機械導出（指令可重跑），非人工判定 |
| 0420 | S4.2 | 收案 | 逐張確認：檢查實際位置（檔:行）、掛載階段、屬內容型或一致性型。我＋三家 | 每張已交付票有檢查位置紀錄（檔:行） |
| 0430 | S4.3 | 收案 | 能掛的掛上；不能的寫具名豁免。體例＝須同時寫「無等價判定之理由」與「部分閘是否已掛」 | 每張已交付票於 enforcement 有列，或有具名豁免理由 |
| 0440 | S4.4 | 收案 | 🔴 三家逐條複驗每一則豁免理由。驗收判準：登記不是免死金牌——票有可執行 artifact 卻無對應機械檢查時，「無檢查可掛」之登記不得當成完成；對外宣稱完成而無可證偽之閘與豁免列者，該宣稱視為空殼 | 三家逐條複驗完成並戳記；reconcile_stamps_check rc=0 |
| 0510 | S5.1 | 收案 | 三家 review 全鏈路 | 三家 review 完成，收斂檔 findings 全數處置 |
| 0520 | S5.2 | 未開工 | 全套 gov_check 綠 ＋ 說明檔同步 | gov_check --no-probe rc=0 且 plain_docs_sync_check rc=0 |
| 0530 | S5.3 | 未開工 | 解除 WL-04 之 BLOCKED（使用者定：這些確保都完成才能進 WL-04） | WL-04 之 BLOCKED 標記移除，且前置全部為收案 |
<!-- END GENERATED: governance-sot-plan -->

# 接手第一件事：做上表**由上而下第一個尚未完成的項目**

**做完後只改 `scripts/fact_keys.json` 該列的狀態欄，再跑
`bash scripts/gen_fact_key_blocks.sh --write`**，兩份文件同時更新。
本節刻意**不重述任何一列的內容**——重述就是副本，副本就會過期。
🔴 **不要在本檔任何地方手寫項目編號＋狀態值**——偵測器會擋（歷次前置皆實際擋下過）。

使用者 2026-08-12 夜間指示（逐字）：治理 epic **不寫 SPEC/TODO**，由 Opus 依本表直接實作，
三家委員 review＋adversarial＋討論，分歧由主委與委員共識決、不上呈；中途只 commit 不 push。

🔴 **不要再提「等使用者回答兩個問題」**——已作廢。問題 (b)（凍結檔授權）建立在
**錯誤量測**上：可執行 ASSERT 僅 2 行、兩份凍結檔 0 行，授權問題不存在。
量法錯在何處見 `docs/GOV_ASSERT_PATHA_NOTE.md` §2。

## 推送狀態：**本檔不寫，直接查**

`git log --oneline origin/main..HEAD | wc -l`（待推筆數）與
`bash scripts/gov_check.sh --no-probe`（丟背景）。
🔴 **筆數與 hash 刻意不寫進本檔**——歷史上一個 session 內就漂過一次。
髒檔應為 4 個且**全為規則禁止提交項**：`.claude/gate/*.log`×2、
`governance_families.json`（`R-15`）、`docs/GOVB0_FRICTION_AMENDMENTS.md`。

🔴 **`git add` 一律逐檔列出，禁目錄形式，亦禁 `$(...)` 子命令展開**：
歷次事故＝`git add docs/` 掃進 `GOVB0_FRICTION_AMENDMENTS.md`、
`git add scripts/` 掃進 `governance_families.json`（兩者皆明令不得提交），
其中一次還連帶要重寫三個本地 commit——因為 G-7 的豁免是
「該路徑在範圍內**只**被 out-of-epic commit 觸及」，補後續 commit 解不掉。
另：中文路徑經 `git status | awk` 取值會因 quotePath 轉義而**靜默取不到**，實際踩過。

## 前一批之交付與收斂檔（**狀態值一律看最上方生成區塊，此處只給指標**）

**做法**（使用者 08-12 夜間定）：不寫 SPEC/TODO，依待辦清單直接實作＋三家 review。
每項鏈路：實作 → 三家 review → 採納修補 → **原提出方複驗**（章程 §B8）→ 三家戳記 → 清債。

| 交付 | 委員輪次 | 收斂檔（含量測與逐條處置） |
|---|---|---|
| `fact_keys` schema 擴為具名欄＋表格投影 | review → closure | `handoffs/reconcile/20260813-govwl01-x-review-r1/synth.md` |
| 判準入註冊表＋三道機械檢查 | consult → review → closure | `handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md` |
| 機制證據登記（平台機制＋改法子樹掃描） | consult → review → stamp×2 | `handoffs/reconcile/20260813-govwl03-x-review-r1/synth.md`＋`…-stamp-r2/`、`…-stamp-r3/` |
| 戳記手抄消滅之設計諮詢（**未實作**） | consult | `handoffs/reconcile/20260813-govwl04-x-consult-r1/synth.md` |
| **產出端覆蓋鐵律**（票要標收案須先擋在產出端） | review | `handoffs/reconcile/20260813-govenf-x-review-r1/synth.md` |
| **全量票之產出端覆蓋盤點** | consult | `handoffs/reconcile/20260813-govenf-x-consult-r2/synth.md` |

### 🔴 接手前必讀的五條（細節與量測看上表收斂檔，本檔不重述）

1. **清單上的字面設計不等於既成事實。** 判準與機制那兩項的字面寫法都在開工前量測時被推翻
   （一項零訊號、一項誤擋率八九成）。**先量一次再動手，不要照抄開工。**
2. **「檢查只掛在其中一條路徑上」這個形態反覆出現**（已累積六個位置）。
   審查時主動問「同一種輸入有沒有第二條處理路徑」。
3. **「兩家說沒問題、一家附可重現構造」時採後者**——本 epic 已四次，四次都是那一家對。
4. 🔴 **`jq`／command substitution 的 rc 被吞掉是本 epic 最常見的空心來源**（已三個同型）。
   `$(...)`、`< <(...)`、`2>/dev/null` 都會吞。一律先落變數驗 rc。
5. 🔴 **反例只斷言 `rc≠0` 不夠，必須斷言目標錯誤訊息**——否則 DRIFT 之類的下游紅
   會讓你誤以為目標檢查生效。實際差點把一個空心的核心卡點當成通過。

### 🔴 票 SoT 已上線（本輪最大變更，接手必讀）

**61 張票收成一份**：`docs/GOV_TICKET_SOT.md`（序／票／狀態／問題描述／狀態依據）。

- 票的**任何**變動（新增／狀態／描述）→ **只改 `scripts/fact_keys.json` 之
  `governance-ticket-sot`**，再跑 `--write`。別處寫「票號＋狀態」會被 fail-closed 擋下。
- `handoffs/…-BACKLOG.md` 與 `白話說明/治理待辦總覽.md` **已標作廢**，內容一字未改
  （使用者裁定「標成舊文件就好」，不必付移除的不可逆代價）。
- 新增票**不必**寫 backlog：`scripts/ticket_universe.sh --check` 是**單向**檢查
  （backlog 有而 SoT 缺 ⇒ 擋；SoT 多出的新票 ⇒ 放行；票號格式錯 ⇒ 擋）。
  🔴 原設計要求「集合相等」，與「backlog 已作廢」自相矛盾——**使用者指出後才修正**。

### 🔴 步驟狀態只有三個值（本輪定死，不得再造詞）

**未開工**＝產物一個都不存在；**進行中**＝產物部分存在但驗收未全達成；
**收案**＝驗收條件全部達成且有可重跑的驗證指令。
🔴 主委曾臨時造「基本完成」「可標收案」兩個詞——**沒全達成就是進行中**，
「驗收過了但還沒改表」不是狀態，是該立刻去改表。
`governance-sot-plan` 已加「驗收條件」欄，20 步全填且皆為可重跑指令或可構造反例。

### 🔴 「產出端」的定義（本輪釐清，勿再誤讀）

使用者原話是「產出**完成前**」「連留到**下一節點派工**都已經是摩擦」⇒
**產出端＝我還在做這件事的那個工作階段內就知道**；**消費端＝要等後面某個關卡才發現**。
`PostToolUse` **屬產出端**（寫完當下回灌），不是「寫入前」。
🔴 主委曾把它誤讀成「寫入前」並據此排錯優先序；`PreToolUse` 對**一致性型**檢查
會直接死鎖（改註冊表必然先不一致 ⇒ 永遠通不過）。分類見 `governance-sot-plan` 之 `S3.2`。

## 已完成並 push（`origin/main`）

- `票 B-49`：凍結出口補上、幽靈路徑 11→0、關票條件機械可驗（**狀態值見生成區塊**）
- **ASSERT 自鎖 T0 止血**（`53966e90`）：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`
- 檢查鏈段序改「便宜先」＋早退＋失敗摘要（`2c34027a`）

## 📜 前一 session（2026-08-12）之批次——**歷史紀錄，非現況**

**PUSH 11 分鐘 ＋ ASSERT 自鎖，兩題皆已改碼**（前版交接記為「一行程式碼都沒改」）：

| 改動 | 檔 |
|---|---|
| 段序改便宜先＋便宜段早退＋失敗摘要末尾化＋backlog 移至最末 | `scripts/gov_check.sh` |
| 路 A：呼叫端不執行文件內 ASSERT（**三處**） | `gate.sh`×2、`spec_fourway_check.sh`×1 |
| NO_EXEC 下印出「ASSERT 未驗證」（不得靜默） | `scripts/template_check.sh` |
| 新增守衛測試 13 格（含 5 條 mutation 反面） | `tests/governance/test_gov_check_cheap_first.py` |
| 處置與具名殘留 | `docs/GOV_ASSERT_PATHA_NOTE.md` |

**三家 review**（`handoffs/20260812-govcheap-x-review-r1/`）：Composer／Grok 判可派工；
**Codex 判需修補**（2 條 P1，附行號碼證）。依「不數人頭以碼證定」採 Codex，兩條均已修：
① G-7 缺檔原寫成「略過」＝fail-open ⇒ 改以 `scripts/govb1_scope.manifest` 判適用性、
　 缺腳本判紅，並補 `test_mutation_removing_g7_script_turns_red`
② NO_EXEC 靜默放行「文法對但結果會錯」之 ASSERT ⇒ 改為大聲印出，
　 並把可執行 ASSERT 之**檔案集合凍成具名清單**（新增即轉紅）
另 Grok＋Codex 抓到主委自造回歸：以 `awk` 批次改註解時**掉了 `gov_check.sh` 的可執行位**，已還原。

### 續作（同日第二輪，session `20260812-govassert-x-review-r1`）

`CODEX-R1-P2-04` 指出「掃呼叫端」判準**不封閉**（`scripts/test_template_check.sh:64`
以 `bash "${TEMPLATE_CHECK}"` 呼叫，正則看不見）⇒ **反轉預設**：
`template_check.sh` 改為預設不執行、須明示 `TEMPLATE_CHECK_EXEC=1`；
四處呼叫端的死旗標移除；列舉式掃描測試刪除，改為形態面＋行為面兩條判準。

三家再審 6 條**全數採納並修**。其中 `GROK-R1-P1-01` 為 BLOCKING：
反轉後 `test_t15_a1_path_hijack_blocked`（唯一不走 `_run_fn` 的承重測）變成空心格，
已修並經反面實證（拆掉 PATH 固定 ⇒ marker 出現）。

🔴 **本輪品質觀察（重要）**：必答「是否出現空心格」一題，**Codex 與 Composer 皆答錯**
（兩家都聲稱 PATH 劫持測經由 `_run_fn`，實為自建 probe），只有 grok 實跑隔離。
⇒ 該兩家之「可 commit」verdict 建立在錯誤事實上。
**review 品質的分水嶺是「有沒有真的跑」，不是家數**——派工時應要求附實跑隔離結果。

### 第三批（`eddd78e3`；使用者指示「寫在一定會看到、不會漏也不會讀錯的地方」）

- **待辦清單改為機械投影**：新 fact-key `governance-worklist`，宿主＝本檔＋
  `白話說明/接下來要做什麼.md`。**狀態只改 `scripts/fact_keys.json` 一處**，手寫即 fail-closed。
- **`CLAUDE.md` 去除會漂的值**：① code review 家數改為指向 `ORCH §1`
  （原寫「2 個」而 ORCH 為三家，當日害主委做錯一次）② pytest 秒數／測試數改為
  「十分鐘級、前景必 timeout」之不變判準（該數字已過期四次）。
- 延伸檔 `docs/GOV_B25_SCOPE_AMENDMENT.md` 補列 `FACTKEY-ADDED: governance-worklist`，
  並把該檔寫死的「兩個狀態 key」改為指標。
- 🔴 **本批未經三家 review**（改動為資料註冊與文件去漂，無行為邏輯）。
  若下個 session 認為需要，補派一輪即可；**不得宣稱已審**。

## 實測數字：本檔不重述，看唯一來源

| 量到什麼 | 唯一來源 |
|---|---|
| `--fast`／全套 push 路徑之前後對照、backlog 75 秒之根因 | `白話說明/接下來要做什麼.md` 之「8/12 深夜」節 |
| 可稽核收據（含 exit_code／sha256／git_head） | `handoffs/run_receipts/20260812T121019Z-govcheap-fast-1s.*`<br>`handoffs/run_receipts/20260812T122358Z-govcheap-fullgate-703s.*` |
| ASSERT 執行面之正確量法與數字 | `docs/GOV_ASSERT_PATHA_NOTE.md` §2 |

🔴 **舊記「89 行／9 檔／凍結檔 45 行」係量法錯誤（未錨定行首），已作廢——勿再引用。**

## 平台事實（勿重測，直接用）

- `ulimit -H -u` 本機**不能降**（`Invalid argument`）；只降 soft 必被子程序抬回
- **無 `setsid` 指令**；`set -m` 可使背景 job 自成 pgid，`kill -TERM -<pgid>` 實測連孫程序一併終止
- per-user process 上限 `ulimit -u`＝**1333**

## 🔴 未修的活缺口

> 🔴 **本節是機器輸入**：`governance-ticket-closure` 之導出集合＝本節 ∪
> backlog「2026-08-10 scope 缺口」節所提及之票號。增刪票號提及須同步 `scripts/fact_keys.json`。

- 🔴 `票 B-25`：判準資料化**三段皆已交付**（待辦清單前三列）。
  🔴 **能力邊界（三家一致，永遠不會由本機制關閉）**：語意互斥——兩段話用**不同條件字串**
  描述同一物理事件時鍵不相等，機械上偵測不到；出生事故那型即屬此類。
  另：既有散文判準不溯及既往；機制證據那段在現樹訊號近零，且其子樹旁路
  **四度被委員實構**（發現曲線未收斂，改 parser 須重跑候選組）。
  完整殘留見 `docs/GOV_CRITERIA_REGISTRY.md` 與 `docs/GOV_MECHANISM_REGISTRY.md`（11 條）。
  該票於票狀態表之列為 ord `005`（**狀態值見生成區塊，本檔不重述**）；
  票本身另有具名殘留，見 backlog `B-25` 節。
- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；OOE 通道救不了
- `R-13` Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`
- 🔴 `票 B-49`：**狀態已下修**（值見生成區塊）——產出端覆蓋鐵律之第一個溯及既往實例。
  主委所寫之豁免理由經三家一致否決——閉合證據的靜態可判定部分無需 commit 亦可於產出端驗。
  重新收案之前置＝把靜態子集前移至產出端，見 `docs/GOV_ENFORCEMENT_REGISTRY.md` 之 `E-007`。
  另四條具名殘留見 `docs/GOV_B49_ASBUILT_DELTA.md` §3
- 🔴 **產出端覆蓋機制本身之缺口**（9 條，見 `docs/GOV_ENFORCEMENT_REGISTRY.md` 殘留節）：
  掛載點對證擋不掉「腳本被掏空」；自我保護有本質極限（守衛執行的正是可能已被竄改的生成器）
  ⇒ **只擋意外不擋蓄意**；票表刪列可繞過；批次不受覆蓋要求；`settings.json` 缺席時略過對證
  （主委為修測試而引入之 fail-open）。**當下票表已無收案票 ⇒ 該閘無實際攔截對象**
- `票 B-54`：戳記 64 位 hex 仍由委員手抄，曾掉字一次。**已部分緩解但未機械化**——
  現行做法是在 stamp brief 內要求委員**自行以 `reconcile_body_hash.sh` 重算核對、不得抄**，
  並聲明「算出不同就以你算的為準並開 finding」。屬紀律非強制；根治＝待辦清單之 `WL-04`
- `B3R` 已進主樹但三家 review 未戳記 ⇒ 只能說「已交付、待戳記」
- `票 B-56`／`票 B-57`（優先序低）／`票 B-58`（前導空行是否為缺陷未判定）
- `票 B-59`（優先序高）：dispatch gate 判定式為黑名單列舉，**不得宣稱閘已完備**
- `票 B-60`：`review_quorum_check.sh:35` 家族清單硬編未讀 SoT
- `票 B-61`：`_role_gate.sh` 之 `known_only` 對未知家族靜默放行
- `票 B-15` 誤擋仍在（含 `for f in codex composer grok` 這類唯讀迴圈被家族名偵測誤擋）
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 只能說「產出端已有檢查點」（`票 B-53` 落地前）
- 站 5 未修殘留：`CODEX-R3-P0-03`／`CODEX-R3-P1-04`／`gate_check.sh` audit 分類器未同步
- 另有兩條空心探針不在 `LEGACY_PROBE_DEBT` 內（`test_mutation_g5_g6_empty_extract_fails`／
  `test_mutation_removing_selfcheck_case_turns_red`）⇒ `gov_check` 全跑必紅（pre-push 用
  `--no-probe` 跳過故不擋推送）。**既有債**，pre-B49 基準實測同樣紅。刻意不加進具名排除清單。
- `R-15`：`scripts/governance_families.json` 不可 commit
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**`（`run_receipts/` 除外）不得 commit
- 卡頓偵測器錯誤歸因：`settings.json` 之 `ts_stamp.sh OUT`（`:184`）早於
  `doc_format_precheck`（`:197`）⇒ hook 執行時間被記成「Claude 生成慢」。屬使用者設定檔，需其同意

## ⚠ 操作紀律（踩過的坑，一律照做）

- ✅ **「推送前必跑 8 秒快閘」已不再是紀律**——白話同步／fact-key／G-7 已是 `gov_check.sh`
  的第 2–4 段，且**便宜段一紅即早退**（實測 10 秒內給答案，不再跑滿 12 分鐘）。
  自檢直接跑 `bash scripts/gov_check.sh --no-probe`（丟背景）即可。
- 🔴 **失敗先看最末的 `GOV-CHECK-FAILED:` 摘要**（已具名段號與修法），**禁直接重跑套件**。
  曾兩次只 `tail -3` 就重跑，白花 22 分鐘——摘要末尾化就是為此而做。
- 🔴 **G-7／F5 用 endpoint 淨差**：commit **前**是綠的（檔還沒進範圍），一 commit 才現形
  ⇒ **commit 之後必須重驗**。歷次 session 皆踩過。
- 🔴 **G-7 的 out-of-epic 豁免是「該路徑在範圍內*只*被帶 trailer 的 commit 觸及」**
  ⇒ 同一檔若被任一無 trailer 的 commit 碰過，**補後續 commit 解不掉**，只能重寫歷史。
  凡動到 scope 外的檔（如新建 `docs/GOV*`），**該檔涉及的每一筆 commit 都要帶 trailer**。
- 🔴 **反向驗證才算數**（移除判定 ⇒ 對應斷言須轉紅）；**前必先 commit**——
  `git clone --local` 只取已提交內容（曾因此白驗一輪）。
- 🔴 **實測 > 假設**（本專案最貴的一條，已連續多輪咬人）：
  ・寫進文件的機制**必須先實跑**（`setsid`／`ulimit` 那次燒掉三輪審查）
  ・**量測時 pattern 須一致**，且**引用命中數必須同時給比對式**——
  　同一件事三家量出三個不同數字，只是寬嚴不同，不附 pattern 的數字等於沒有數字
  ・**斷言「這條規則抓得到那個已知案例」時，要拿那個案例去跑**——
  　曾斷言新規則會攔到 `setsid`，實測發現 `setsid` 不在 PATH ⇒ 規則反而漏掉它本身
- 🔴 **待辦清單上的字面設計不等於既成事實**：連續兩項（判準偵測、機制證據）
  的字面寫法都在開工前量測時被推翻（一項零訊號、一項誤擋率八九成）。
  **每項開工前先量一次「這條規則在現有語料抓得到東西嗎」**，這已兩次擋下無效施工。
- 🔴 **注意「檢查只掛在其中一條路徑上」這個形態**：一天內出現四個位置
  （表頭 vs 儲存格／schema 單欄刪除／狀態靠列舉位置／驗證只掛 `--check`）。
  審查時主動問「同一種輸入有沒有第二條處理路徑」。
- 🔴 **不以家數表決，以碼證定**（本 epic 三次「兩家一種說法、一家附碼證」，皆採後者）。
- 🔴 **同一支腳本不得並行跑多份**——曾三份 `template_check` 併發導致 fork 耗盡（上限 1333）。
- 🔴 fact-key 註記**不得含日期**；改 `fact_keys.json` 後 `factkey_clean`／`factkey_drifted`
  兩 fixture 皆須用 `GOVB1_FACTKEY_ROOT=<目錄>` 重生成，drifted 須維持「恰一列不同」。
- 🔴 **新增一個 fact-key 有四項固定連帶工作，缺一即紅**（上輪四項全中，14 分鐘 gate 抓了三輪）：
  ① 延伸檔補 `FACTKEY-ADDED:`（集合相等契約）② 兩份 fixture 各補宿主檔
  ③ 內容不得含 `年-月-日` ④ 動到 `status_scope_grandfathered` 須同步
  `test_govb1_factkey_gen.py` 之集合相等表。
  **改完先跑窄測試**（`pytest tests/governance/test_govb1_factkey_{gen,hook}.py -q`，約 2 分鐘），
  **不要讓 14 分鐘的全套去發現 2 分鐘能發現的事**。
- 🔴 **說明檔同步是工作項目的最後一個 commit**：同一 commit 既動 `scripts/` 又動
  `白話說明/` 必判過期（判準＝說明檔不早於其 WATCHED）。一輪內踩三次，一律拆兩個 commit。
- 🔴 **commit 訊息檔寫在專案內**（如 `.claude/tmp/`），勿放 scratchpad——
  `/private/tmp` 在專案外，每次 `git commit -F` 都命中權限分類器（實測 12–17 秒／次）。

### 下個 session 開頭優先處理：把測試選擇機械化（未開工）

**問題**：`gov_check` 含全套 pytest（1674 條、約 14 分鐘），而典型改動只牽動一小撮測試
（本輪改 fact-key 只需 `test_govb1_factkey_*` 共 212 條、112 秒）。問題留到 push 才現形，
一輪紅就是 14 分鐘，本輪連紅三輪。**這正是「檢查放在後面關卡＝純摩擦」的實例。**

**提案**：`factkey_write_guard.sh`（已掛 `PostToolUse`）順帶跑相關測試子集。
🔴 **必須 fail-closed**——改到的檔不在對應表內就跑全套；漏登記的代價是慢，不是放行。

**另一條路（傾向否決）**：`pytest-xdist` 平行化。治理測試有一批會就地 mutate 檔案再還原，
專案明令不得並行；標漏一個即隨機假綠。**風險高於收益。**

⇒ 屬技術取捨，**交委員會裁定**，不佔用使用者判斷。
- 🔴 `handoffs/run_receipts/` 進 commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且 **trailer 必須在最後一段**（git 只解析最末段）。
- 🔴 閘會把含家族名的**讀取指令與 commit 訊息**當成派工 ⇒ 訊息一律用 Write 工具寫檔再 `-F`。
- 🔴 禁 `cd <專案路徑>` 前綴、禁 `sed -i`、禁 `rm`（用 `mv` 到 `.claude/tmp/`）、
  禁 `python3 - <<'PY'` heredoc；改檔一律用 Edit／Write。
  **`printf ... >> 檔` 也算違反**——內容裡的 `%` 會被當格式指令，
  曾一次把三份說明檔截斷在句子中間。Edit 找不到目標會失敗，shell 拼字串會**靜默產出半截**。
- 🔴 **`git add` 一律逐檔列出，禁目錄形式**——`git add docs/`／`git add scripts/`
  曾各掃進一個明令不得提交的檔（`GOVB0_FRICTION_AMENDMENTS.md`、`governance_families.json`），
  其中一次還連帶要重寫三個本地 commit。
- 🔴 **說明檔同步是「每個工作項目的最後一個 commit」**，不是每次存檔都補——
  時序判準比的是「說明檔最後改動不早於程式最後改動」，只要又動程式全部說明檔就再度過期。
  曾照「每次存檔都補」做而連撞三次。
- 🔴 **委員戳記的 body hash 一律要求委員自算**（brief 內明寫「不得抄、算出不同以你的為準」）——
  `票 B-54` 是委員手抄掉字造成的。
- 🔴 **生成區塊的內容不得含 `年-月-日`**——既有測試 `test_output_has_no_bom_no_crlf_no_timestamp`
  會攔。要標時間點就寫「使用者定」「本輪」，日期留給 git。**本輪犯兩次。**
- 🔴 **派工前先開 gate token**：`committee_run.sh` 本身就會被 `gate_check.sh` 擋
  （它是 dispatch 動作），要先跑 `gate.sh dispatch`。另：session 名須符命名規約，
  `kind ∈ {impl,review,stamp,consult,fix}`——**沒有 `closure`**，閉合輪走 `stamp-r<N>`；
  task-id 須為 session 的**大寫**形式。三者本輪各擋一次。
- 🔴 **委員 brief 要求「每條 finding 附修法」**（使用者本輪指示）：具體到檔＋行＋可貼片段，
  無需修者寫 `不需修：<理由>`。實證可省掉整整一輪往返。
- 🔴 **唯讀指令裡不要出現家族名**（如 `for f in codex composer grok`）——
  會被 dispatch 閘誤判為派工（`票 B-15`，本輪又擋一次）。改用萬用字元或不列舉。
- 🔴 **`scripts/fact_keys.json` 一律用 Edit 改，`jq` 只准拿來讀**——
  `jq` 會把整檔重新格式化，實測 diff 從 2 個字變成 **1322 行整檔重排**，review 完全看不出真正改了什麼。
  **本輪犯兩次**（第二次是在剛寫下這條規則之後）。改資料列用 `awk` 逐行重寫亦可。
- 🔴 **反例只看 rc 會被騙**：本輪兩次「rc 如期轉紅」，一查訊息才發現紅的是別的原因
  （一次是 JSON 語法錯、一次是 DRIFT），**目標檢查根本沒被執行到**。
  一律 `grep` 目標錯誤訊息，不要只斷言 rc。
- 🔴 **作廢一份文件後，要把後果推到底**：本輪把 backlog 標作廢，卻仍寫了「SoT 必須等於
  backlog」的檢查 ⇒ 新增票會被逼去寫作廢檔。**舊模型的假設會殘留在新設計裡**，
  作廢／取代之後要回頭檢查所有依賴它的規則。
