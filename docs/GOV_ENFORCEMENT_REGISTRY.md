# 產出端覆蓋登記表（唯一來源）

FACT-KEY: governance-enforcement
LAST-RULED: 2026-08-13
RULED-BY: 使用者直接裁定（憲法級）
CHECKED-AT: 產出端（`scripts/factkey_write_guard.sh`，PostToolUse Edit/Write）

---

## 本檔要強制的規則（使用者 2026-08-13 逐字）

> 「我覺得要加入一個規則，就是治理的所有票，包含已經做過和正在做和未來的實作，
> **都要在產出端擋下，這才能當已完成**，除非像 G-7 和 pytest 等可以說明為何不該放在產出端，
> 這任務完成檢查在**所有治理 epic 中都適用**，你要想辦法卡住，**不能漏**。」

前一天（2026-08-13 稍早）使用者已指出病根：

> 「到 git push 才做等於全部都可以廢掉不需要，所有的上百項治理問題，
> **全部都是在產出就發生問題**，這連留到下一節點派工都已經是摩擦，
> **所有在產出完成前沒辦法擋的都等於沒意義**」

**本檔不是文件宣告，是機械強制點。** 「不能漏」的落法＝把「票能不能標收案」
跟「它的檢查在不在產出端」綁死，見下方檢查 ④。

## 機械檢查（皆在 `gen_fact_key_blocks.sh`，並由產出端守衛在寫檔當下觸發）

> 🔴 本節**不寫道數**——歷史上寫「四道」而實際已長到八道，成為又一份過期副本。
> 權威是 `scripts/gen_fact_key_blocks.sh` 之 `_fk_validate_enforcement`。

1. **強制側封閉列舉**：`強制側` 欄只收 `_schema.enforcement_side_enum` 所列值。
2. 🔴 **掛載點機械對證，禁自我宣稱**：`強制側` 為產出端者，其 `掛載點` 必須在
   `.claude/settings.json` 的 hooks 內**實際存在**——event 對得上、matcher 對得上、
   command 以 `bash <片段>` 起頭。**光在表裡寫「我掛在產出端」不算數。**
3. **豁免須具名理由**：`強制側` 為豁免者，`豁免理由` 不得為空、不得為佔位符。
4. 🔴 **完成綁定**：票 SoT 中狀態屬**完成語意集合**（`S2.1`：收案／已落地／已完成）的
   **每一張票**，必須在本表至少有一列。**這是「卡住」的那一道**——任何票要標完成，
   得先在這裡登記它的檢查掛在哪；掛不到產出端就得寫出為什麼。
   （原文寫 `governance-ticket-closure`，該來源已於 `S0.6` 刪除，此處同步更正。）
5. **幽靈票**（`S1.1`）：`對應票` 欄之值須在「票全集 ∪ `enforcement_ticket_allowlist`」內。
6. **提前預警**（`S2.2`）：票尚未標完成但已推進中而無覆蓋登記者，先警告、不判紅。
7. **判定型分類**（`S3.2`）：產出端列須為 `內容型`／`一致性型`，豁免列須為 `n/a`。
8. 🔴 **理由体例與引用對證**（`S6.1`，見下節）。

## 掛載點格式

`<event>:<matcher>:<command 片段>`，三段以半形冒號分隔。

matcher 段之多個工具名以**半形逗號**分隔（`Edit,Write`），**不用 `|`**——
`render: table` 的儲存格禁 `|`，會切碎表格。
🔴 這個限制是產出端守衛在本檔上線當天、寫檔的**當下**實際擋下的，
不是事後 review 發現的——正好是本規則要的效果。

豁免列之 `掛載點` 欄**不受對證**（該判定本來就不在 hook 上），填實際最早的攔截點即可。

## 🔴 理由欄体例（`S6.1` 定，檢查 ⑧ 機械強制）

| 強制側 | `豁免理由` 欄必須寫 |
|---|---|
| 產出端 | `實作位置：<檔>:<行>`（＋路由說明） |
| 豁免 | `PreToolUse不可：…` ＋ `PostToolUse不可：…` ＋ `部分閘：…` **三段齊備** |

**為什麼要拆成兩段寫。** `S4.3` 一口氣填 16 則，理由清一色是
「輸入為完整文件，非單次編輯內容」。那句話**只證明不能 `PreToolUse`**，
對 `PostToolUse` 一個字都沒說——而反例就在同一棵樹上：
`factkey_write_guard.sh` 也要讀整棵樹，照樣掛在 `PostToolUse`。
`S6.1` 逐列重問後，**五列被實跑反例推翻**（`E-009`／`E-010`／`E-011`／`E-012`／`E-019`），
其中三列的檢查**早就在產出端跑著**，只是登記寫錯。

**三個必須分開的概念**（混用即為藉口）：

1. **不能 `PreToolUse`** —— 寫入前該物件還不存在。
2. **不能 `PostToolUse`** —— 觸發源根本不是主控端 `Edit`／`Write`（如派工指令、
   執行端 CLI 直接寫檔），或代價不可接受（全套 pytest）。
3. **沒有東西可掛** —— 改法未完成／純紀律條文。這是「無檢查」，**不是**「檢查掛不了」。

**引用對證**：`部分閘：`／`實作位置：` 之後的 `<檔>:<行>` 會被機械對證——
檔案須存在，且該行**不得是註解或空行**。
🔴 此條是拿代價換的：`S4.4` 打回的五則不實登記中，`E-011` 填的行號落在註解區塊首行；
`S6.1` 重掃**又抓到四處同型**（`E-014`／`E-015`／`E-019`／`E-020`）。
同一種錯誤犯到第六次就不該再靠人眼。

## 🔴 具名殘留

1. ~~本表現在只涵蓋「已收案」的票~~ **（S4.3 後已失效，改寫如下）**
   🔴 本表現涵蓋**全部 17 張已交付票**（狀態＝部分完成；收案 0 張），逐張有列。
   檢查 ④ 綁的是**完成語意集合**（S2.1：收案／已落地／已完成），非單一收案字面。
   尚未涵蓋者＝44 張「未開工」票——它們無交付物，故無檢查可掛，
   標完成前必然撞到檢查 ④，且 S2.2 會在那之前先預警。
2. ~~`E-007`（`票 B-49`）的豁免理由尚未經委員裁定~~ **（S4.4 已裁定）**
   🔴 S4.4 三家逐條複驗 20 則登記，一致判「需修補」並具名 12 條 findings；
   主委實跑查證後確認**五則有事實錯誤**（`B-10`／`B-19`／`B-16`／`B-32`／`B-31`），
   已逐則更正並在該列標「R5 更正」。⇒ **登記表的自述曾與現樹漂移，這是實例**。
   B-49 本身之豁免理由未被推翻，但其收案宣稱早已退回（見票 SoT 狀態＝部分完成）。
3. 🔴 **檢查 ② 擋得掉「換成別的指令」，擋不掉「腳本被掏空」。**
   r1 三家全員實構出偽造路徑，已據此強化為：片段須為 `.sh`、對應檔須存在、
   且 command 必須**以 `bash <片段>` 起頭**（原本只用 `contains`，`sh`／`a` 這種短子串
   對真實 settings.json 即命中）。但把腳本內容換成永遠 rc=0 的 noop 仍會通過——
   該層靠 review 與各票自己的 mutation 測試。
4. **豁免理由的「充分性」仍不機械判定。** 檢查 ⑧ 驗的是**体例齊備**與**引用指向可執行碼**，
   驗不到「這個理由是真的嗎」。`S6.1` 本身就是實例：五列的体例當時看起來完整
   （寫了「無等價判定」也寫了「部分閘」），內容卻是錯的——三列的檢查早在產出端跑著。
   🔴 **能機械擋的是形態，不是真偽；真偽只能靠實跑反例。**
   本輪凡改判為產出端者皆附反例實跑，未附者一律不改判。
5. 🔴 **自我保護有本質極限（`CODEX-R1-P0-03`，無解）。**
   生成器、守衛自身與 `settings.json` 已納入受管，但**把生成器加回受管不足以保護它**——
   守衛執行的正是那支已被竄改的生成器。真正的獨立錨是 pytest 與 pre-push。
   ⇒ 本機制**只擋意外改壞，不擋蓄意**。
6. 🔴 **從票表刪掉整列可繞過檢查 ④**（`COMPOSER-R1-P1-01`）：票不在表裡就不算收案。
   該層由 `test_e3_ticket_union_matches_key_rows`（要求票集合與 `HANDOFF` 活缺口節一致）承接，
   但那是 pytest ＝消費端。具名缺口。
7. 🔴 **批次不受覆蓋要求。** 啟用判定掃**所有**狀態表（含 `governance-batch-status`，
   故有收案批次時規則無法被停用），但檢查 ④ 只要求**票**有覆蓋列。
   這是刻意的不對稱——使用者的規則說的是「治理的所有票」。批次若要納入須另行裁定。
8. 🔴 **檢查 ④ 目前沒有實際攔截對象**（票表無完成語意之票，`B-49` 於 r1 後退回）。
   其鑑別力由自造測試票的 pytest 承擔；下一張票要標完成時它才會第一次真的咬人。
   （本條原句寫「本表只涵蓋已收案的票」，與殘留 1 矛盾——`S4.3` 後已改為涵蓋全部已交付票，
   `S6.1` 同步更正此處。**同一份文件內兩條互相矛盾的自述，正是本表要治的病。**）
9. 🔴 **「改判為產出端」不等於「該票已完成」。** `S6.1` 把五列改判為產出端，
   意思只是「該票**已交付的那個檢查**跑在產出端」，不是它沒有殘留。
   五票在票 SoT 之狀態一律仍為部分完成，各自的殘留見該票之狀態依據欄。

## 登記表

> `強制側` 為產出端者，`掛載點` 會被拿去跟 `.claude/settings.json` 對證。
> `豁免理由` 欄之体例見上方「理由欄体例」節（檢查 ⑧ 機械強制）。

<!-- BEGIN GENERATED: governance-enforcement -->
| 檢查ID | 對應票 | 掛載點 | 強制側 | 豁免理由 | 判定型 |
|---|---|---|---|---|---|
| E-001 | B-25 | PostToolUse:Edit,Write:scripts/factkey_write_guard.sh | 產出端 | 實作位置：scripts/factkey_write_guard.sh:116（寫檔當下對受管檔重跑 gen_fact_key_blocks --check） | 一致性型 |
| E-002 | B-25 | pre-push:gov_check.sh 第 3 段 | 豁免 | PreToolUse不可：本列記錄的是 pre-push 之第二層掛載，該階段依定義在 commit 之後。PostToolUse不可：**不適用**——同一判定已由 E-001 掛在 PostToolUse；本列僅記錄 defense-in-depth 之第二個掛載點，非缺口。部分閘：有——scripts/factkey_write_guard.sh:116（同一判定之產出端掛載） | n/a |
| E-003 | B-38 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:150（findings 分支呼叫 cx_run --selfcheck；零 findings 之 sentinel 形態與必填欄於該路徑檢查，反例已實跑） | 內容型 |
| E-004 | B-31 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:150（與委員交件跑同一支檢查、同一組參數）。誠實邊界：票 SoT 之對外用語限「產出端已有檢查點」，不得稱強制 | 內容型 |
| E-005 | G-7 | commit-msg:g7_trailer_precheck.sh ＋ pre-push:govb1_final_gate.sh --only g7 | 豁免 | PreToolUse不可：判定式為 base..HEAD 之 endpoint 淨差，寫入前無 commit 可算。PostToolUse不可：判定對象是 commit 的屬性（訊息末段之 Governance-Scope trailer），寫檔當下該物件尚不存在；而寫檔當下算得出的「路徑在 scope 外」若單獨告警，對本 repo 多數新增路徑恆真 ⇒ 高頻無訊號。部分閘：有——scripts/g7_trailer_precheck.sh:83（commit-msg 階段：staged 含 scope 外路徑而訊息末段無 trailer 即擋；四向反例已驗，含 trailer 放中間段仍擋、只動 scope 內檔則放行）。🔴 R6 更正：原登記「本票不存在可前移的靜態子集」為事實錯誤——同日兩次 G-7 紅正是此子集，且因豁免須「該路徑只被帶 trailer 的 commit 觸及」，補後續 commit 解不掉，只能重寫歷史 | n/a |
| E-006 | 測試套件 | pre-push:gov_check.sh 第 5 段 | 豁免 | PreToolUse不可：全套 pytest 為十分鐘級，寫入前執行會使每次編輯停擺。PostToolUse不可：同上——此為**成本型**而非判定型限制，技術上跑得動、代價不可接受，兩者須誠實區分。部分閘：有——各票之承重判準已分散於本表其他列之產出端掛載，代表兩處為 scripts/factkey_write_guard.sh:116 與 scripts/doc_format_precheck.sh:150；測試子集化之提案見 HANDOFF 之「把測試選擇機械化」節（未開工） | n/a |
| E-007 | B-49 | pre-push:gov_check.sh 第 5 段 | 豁免 | PreToolUse不可：閉合證據須隔離重放＋git 狀態比對，寫入前無可重放之標的。PostToolUse不可：**理由為「現行無可掛之判定」，不是「掛不上」**（CODEX-R2-P1-04 要求釐清）——三家 r1 一致認定閉合證據的靜態可判定部分無需 commit 亦可於產出端驗，故技術上掛得上；本列仍為豁免純因該靜態子集**尚未抽成可掛的檢查**（改法未完成）。部分閘：無——具名缺口，亦為該票重新收案之前置 | n/a |
| E-008 | B-7 | — | 豁免 | PreToolUse不可：判定對象為委員產出的戳記行，派工前尚不存在。PostToolUse不可：戳記由執行端 CLI 直接寫檔，不經主控端 Edit/Write ⇒ 該 hook 不會被觸發。部分閘：有——scripts/cx_run.sh:776（派工 prompt 逐字注入 task-id 並明令 brief 內範例值不得採用，從源頭消滅手抄）＋ scripts/cx_run.sh:413（task_id 缺漏即拒派）。🔴 R6 更正：原登記「改法未完成、現樹無對應檢查可掛、部分閘無」為事實錯誤 | n/a |
| E-009 | B-10 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/template_check.sh:324（dext 分支之必填錨點檢查；由 scripts/doc_format_precheck.sh:80 判型後呼叫）。🔴 R6 更正：原登記為豁免，理由寫「輸入為完整文件，非單次編輯內容」——那只證明不能 PreToolUse；實跑反例（寫入缺錨點之 D 延伸檔）當下即紅，證明 PostToolUse 本就掛得上、且早已掛上 | 內容型 |
| E-010 | B-15 | PreToolUse:Task,Bash,Write:scripts/gate_check.sh | 產出端 | 實作位置：scripts/gate_check.sh:218（_gate_cmd_is_dispatch 之派工判定，掛 PreToolUse ⇒ 指令送出前即判）。🔴 R6 更正：原登記為豁免，理由「須完整指令上下文方能判」——完整指令字串正是 PreToolUse 的輸入，該理由不成立。誠實邊界：本票之殘留是**誤擋率**而非缺掛載，對外不得宣稱誤擋已修復 | 內容型 |
| E-011 | B-16 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/template_check.sh:711（_check_scope_claim 與 _run_assert_lines 之接線，僅 docs 之 SPEC／TODO 檔套用）。誠實邊界：寫檔階段**不執行** ASSERT 行（T0 自鎖止血），只驗文法與錨點，執行留給 gate.sh。🔴 R6 更正：原登記為豁免，惟其 R5 更正已自承「該檢查亦經 doc_format_precheck 路徑觸發」，與豁免宣稱自相矛盾 | 內容型 |
| E-012 | B-19 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:195（handoffs 下含 brief-kind 標記之檔即路由至 brief_conformance_check）。🔴 R6 更正：原登記「部分閘是否已掛：無」為事實錯誤——實跑反例（寫入不引用範本之 brief）當下即紅。殘留 R-12（full path 不驗 EXPECTED-DELTA）仍在，屬檢查深度不足，非未掛載 | 內容型 |
| E-013 | B-24 | — | 豁免 | PreToolUse不可：現樹無對應判定式可執行（本票改法為紀律條文）。PostToolUse不可：同上——不是掛不上，是**沒有東西可掛**；「無檢查」與「檢查掛不了」不得混為一談。部分閘：無 | n/a |
| E-014 | B-29 | — | 豁免 | PreToolUse不可：判定輸入為派工參數與 brief 檔內容之比對，寫檔當下無派工事件。PostToolUse不可：觸發源為派工指令而非 Edit/Write ⇒ 該 hook 不觸發；改掛 PostToolUse:Bash 亦判不了，因判定需 gate 內部狀態（已開 session、brief 已解析），非指令字串可導出。部分閘：有——scripts/committee_run.sh:420（gate_args 追加 --brief，否則 gate 之 --brief 掛點空轉）。🔴 R6 更正：原填 :410 落在註解行。🔴 R7 更正（GROK-R2-P1-01）：R6 改填之 :411 為**非註解但指錯行**（該行是工作區漂移之 echo）——檢查 ⑧ 只拒註解／空行／缺檔，擋不掉語意錯位，此為其具名能力邊界 | n/a |
| E-015 | B-32 | — | 豁免 | PreToolUse不可：判定輸入為 brief-kind 與派工結果（CLI rc、輸出檔），寫入前皆不存在。PostToolUse不可：觸發源為派工指令而非 Edit/Write ⇒ 該 hook 不觸發。部分閘：有——scripts/cx_run.sh:495（_maybe_register_stamp_output，僅 stamp kind 且三條件成立才註冊）。🔴 R6 更正：原填 :493 落在註解行；R5 之「部分閘已落地」結論不變 | n/a |
| E-016 | B-34 | — | 豁免 | PreToolUse不可：現樹無對應判定式（角色閘與戳記檢查之一致性改法未完成）。PostToolUse不可：同上——無物可掛，非掛不上。部分閘：無 | n/a |
| E-017 | B-36 | — | 豁免 | PreToolUse不可：群集歸屬須整份收斂檔方能判，寫入前內容不完整。PostToolUse不可：**理由為「現行無可掛之阻擋判定」，不是「掛不上」**（CODEX-R2-P1-05 要求釐清）——synth 檔之寫入已由 scripts/doc_format_precheck.sh:96 路由，技術上掛得上；但 scripts/reconcile_cluster_attribution_check.sh 全檔僅為純報告、無失敗條件（三家 r2 實跑：對未被引用之 ID 仍 rc=0），且其唯一訊號在收斂檔撰寫過程中恆為真 ⇒ 掛上不產生任何拒絕語意且高誤擋（與 WL-02 開工前量測推翻字面設計同型）。⇒ 屬該票改法未完成。部分閘：有——scripts/reconcile_build.sh:378（收集節點呼叫，提示不阻擋） | n/a |
| E-018 | B-37 | — | 豁免 | PreToolUse不可：本票產物為唯讀彙整報表，無「不通過」語意，無可阻擋之判定。PostToolUse不可：**理由為「無拒絕條件可掛」，不是「掛不上」**（CODEX-R2-P1-05 要求釐清）——掛得上，但本票產物本質為唯讀彙整，掛上不產生任何拒絕語意。部分閘：有——scripts/friction_tally.sh:154（彙整輸出行；唯讀無阻擋語意） | n/a |
| E-019 | B-39 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/completeness_check.sh:157（heading 路由與必填欄判定；由 scripts/doc_format_precheck.sh:150 之 findings 分支經 cx_run --selfcheck 呼叫）。🔴 R6 更正：原登記為豁免且原填 :135 落在註解行；實跑反例（P0 來源摘要寫行號而非雜湊）當下即紅。誠實邊界：跨檔完整性（來源 ID 是否全在綜合）仍須 lock 與全部來源，屬合理的消費端檢查 | 內容型 |
| E-020 | B-50 | — | 豁免 | PreToolUse不可：判定需「派工前」與「派工後」兩個工作區快照之差，寫入前只有單點。PostToolUse不可：觸發源為派工指令；Edit/Write 之 PostToolUse 取不到派工前那個快照。技術上可改掛 PostToolUse:Bash，但那會對**每一個** Bash 呼叫做 git status 全掃 ⇒ 成本與噪音不成比例，未採並具名記錄。部分閘：有——scripts/committee_run.sh:320（_ws_snapshot，派工前後比對）。🔴 R6 更正：原填 :267 落在註解行。🔴 R7 更正：R6 改填之 :311 於同輪內因本檔新增 mkdir 守衛而位移成註解行，三家 r2 一致以 --check rc=1 攔下——**行號引用會隨上游編輯漂移，這是本機制的內建代價，換來的是不會靜默腐爛** | n/a |
<!-- END GENERATED: governance-enforcement -->
