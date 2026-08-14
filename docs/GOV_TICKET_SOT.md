# 治理票狀態（唯一來源）

FACT-KEY: governance-ticket-sot
RULED-BY: 使用者裁定「治理票的新增／刪減／修改／註解／狀態變更只能有一套」

---

## 這份表是什麼

**61 張治理票的狀態，只在這裡改。** 改法＝編輯 `scripts/fact_keys.json` 之
`governance-ticket-sot`，再跑 `bash scripts/gen_fact_key_blocks.sh --write`。

其他文件（`HANDOFF.md`／`GOVERNANCE_EXECUTION_ORDER.md`／白話說明）是**投影**，
手寫狀態字面值會被既有偵測器 fail-closed 擋下。

## 🔴 這份表刻意只有四個欄位

前兩版設計曾疊上 typed reference、跨表外鍵、九種操作路徑、證據宇宙、bootstrap
寬限期、MERGE／SPLIT 語意——兩輪三家 consult 共 39 條 findings，
**絕大多數打的是那些周邊機制，不是「票的狀態」本身**。

使用者一句「只是把票整理起來，是有什麼做不到的？」點破：那些都不是「整理票」需要的。
⇒ 本表只做**票號 × 狀態 × 問題描述 × 狀態依據**（`序` 為排序鍵非資料），
其餘全部具名為殘留另排（見下）。
（原文寫「只有三欄」係 `S0.5` 當時之設計，`問題描述` 於同批加入後未同步；`S6.2` 更正。）

## 狀態值

| 值 | 意義 |
|---|---|
| `未開工` | 沒有實作落地 |
| `部分完成` | 有交付但未閉合 |
| `收案` | 閉合**且**已登記產出端覆蓋（見 `docs/GOV_ENFORCEMENT_REGISTRY.md`） |
| `狀態未確認` | 🔴 **沒有證據可判定。不得用猜的填其他值** |

🔴 **現況（`S0.4` 逐張查證後）：`未開工` 44 張、`部分完成` 17 張、其餘為 0。**
數字會漂，權威一律看下方生成區塊，本節只記「`狀態未確認` 已清零」這個里程碑。

初始值之導出規則屬**一次性**歷史動作（`S0.4`），寫在 `handoffs/` 之收斂檔：
當時以已刪除的 `closure` 表為主、backlog 之 `PARTIAL`／`PROVISIONAL`／`DONE` 映 `部分完成`、
其餘一律 `狀態未確認`，再由三家逐張補證據把未確認清成 0。
🔴 **該規則已完成使命，不再適用於新票**——新票直接依證據填值。

🔴 **`B-32` 於 backlog 標 `DONE`，本表仍為 `部分完成`**——依產出端覆蓋鐵律，
未登記覆蓋者不得稱收案。這是規則的正確後果，三家 r1 一致確認非誤傷。
`S6.2` 進一步釐清其真正原因：該票檢查之觸發源為**派工指令**而非檔案編輯，
產出端覆蓋因而登記為豁免（`E-015`），故不具備標完成的條件。

## 🔴 `狀態依據` 欄的体例（`S6.2` 定，機械強制）

每一列的 `狀態依據` 必須含下列封閉標記之一，且標記後的內容不得為空：

| 標記 | 用於 |
|---|---|
| `還缺：` | 尚有可施工項——寫出**還缺什麼才能完成**，不是寫「誰說的」 |
| `無殘留` | 使用者裁定不做，或客觀不可執行（需 repo 外資源）|

**病根**：61 張裡原本只有 13 張寫了缺口，其餘只寫「r3 三家一致」——那是**來源**不是**內容**，
於是狀態單一化了、待辦內容卻還要回去翻已作廢的 backlog 長文。

**強制點**：`gen_fact_key_blocks.sh` 之檢查 ⑩（標記齊備＋payload 非空）與
檢查 ⑪（票全集對帳，防「刪掉整列就沒有還缺什麼可填」）。
標記集合與生成器寫死之值**集合相等**才算數——清空 schema 欄位無法停用它。

## 🔴 具名殘留（**刻意不做，不是漏做**）

1. **`B3R` 不在本表**——它是批次代號不是票，backlog 無 `## B3R` 標題。
   但 `closure`／`execution-order`／pytest union 現行把它當票字串在用。
   ⇒ **既有引用未遷移**，屬已知缺口。
2. ~~backlog 的 `TICKET-STATUS` 尚未移除 ⇒ 第二套狀態源仍存在~~ **（`S0.6` 已處置）**
   🔴 現況：backlog 檔頭已標「本檔已作廢（歷史紀錄，不再維護）」且明載
   「本檔內的 `TICKET-STATUS:` 欄位全部作廢——不論寫什麼，一律不採信」；
   `governance-ticket-closure` 已整個刪除（現存 fact-key 清單可查）。
   ⇒ **本表已是唯一狀態源。** 內容一字未改係使用者裁定「標成舊文件就好」，
   不必付移除的不可逆代價。
3. ~~43 張 `狀態未確認`~~ **（`S0.4` 已清零）**
   🔴 現況：`狀態未確認` **0 張**——三家逐張補證據後全部落到 `未開工` 或 `部分完成`。
   本條保留為體例提醒：消費端呈現仍須把「未確認」與「未開工」區分，
   將來若再出現未確認，不得算成進度。
4. **MERGE／SPLIT／已作廢恢復等操作沿革無欄位承載**。backlog 索引區實有 `🔗 MERGE`
   與拆票裁決，本表無法表達。
5. **`已完成` 的三條件（artifact ∧ 無阻塞殘留 ∧ 覆蓋）本表只能承載結果、不能承載證據**。
   要可證偽地寫出 `已完成`，需另補欄位或跨表引用——兩輪設計都卡在這裡。
6. **狀態值未納入 ticket 專屬 scope**：現行 `_schema.status_enum` 由多個 status key 共用。

## 狀態表

<!-- BEGIN GENERATED: governance-ticket-sot -->
| 序 | 票 | 狀態 | 問題描述 | 狀態依據 |
|---|---|---|---|---|
| 0010 | B-1 | 未開工 | `scripts/spec_binding_check.sh`（不存在） | r3 三家一致 ｜還缺：整支 spec_binding_check.sh 尚未建立；A1 取樣須改用不受 env 影響之 git ls-tree，A0 才有獨立可測效果 |
| 0020 | B-10 | 部分完成 | `template_check.sh` 沒有 D 延伸檔的 kind。 | r3 三家一致 ｜還缺：施工面無已知殘留——兩個修法選項皆已落地（template_check.sh 之 dext 分支；gate.sh:796 依 D-NNN 命名自動選 kind）。缺的是**狀態複核**：S0.4 裁定之部分完成與現樹落差尚未複核，本輪不重啟 S0.4。🔴 R2 更正（GROK-R1-P1-01）：原寫「選項②未做、仍須人工指定 kind」為事實錯誤 |
| 0030 | B-11 | 未開工 | 治理檢查器把『依賴缺席』當成『檢查不適用』而非『檢查失敗』 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：委員改寫版未實作——靜態探針降級為可解釋 tripwire 警告、隔離 runtime mutation 當硬 gate；主委原案已被實跑否決（誤判率 100% 且漏抓真陽性） |
| 0040 | B-12 | 未開工 | 不再列為待辦 | r3 三家一致 ｜還缺：測試 harness 之腳本複製清單仍無單一來源，全文見 docs/ROADMAP.md |
| 0050 | B-13 | 未開工 | 文件搬遷沒有機械完整性檢查；「已完整併回」是散文宣稱。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：以 completeness_check.sh 之 heading 路由為單一來源尚未落地；13-d 之監看路徑改前綴 docs/GOV、受管清單改現讀資料夾導出亦未做 |
| 0060 | B-14 | 未開工 | `cursor-agent`（composer）寫完產出後不退出，整輪掛住。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：cx_run.sh 之 per-family timeout 未實作（逾時且產出檔已通過 completeness_check --single 者應視為完成） |
| 0070 | B-15 | 部分完成 | `gate_check.sh` 把唯讀查詢誤判為派工。 | r3 三家一致 ｜對外不得宣稱：不得宣稱誤擋已修復——B7 之後仍存在，GOVB0 B4 Task 2.3/2.4 未做 ｜還缺：誤擋事件無紀錄 ⇒ 誤擋率無法量測、改完無法驗證、B-29 對本票做不出差集；修法須先補紀錄。GOVB0 B4 Task 2.3／2.4 未做 |
| 0080 | B-16 | 部分完成 | 機器實際依賴的契約長在散文裡，導致「用 regex 解析 markdown」成為必經之路。 | r4 主委裁定：template_check.sh L408+ 與測試檔碼內明文票號，歸屬成立 ｜還缺：四類偵測（ID 樣式／可執行斷言／路徑與函式樣式／複合句）僅部分落地；每項修法須附誤擋率 receipt；是否納入 白話說明 掃描未決，納入前不得宣稱覆蓋使用者可見面。🔴 2026-08-14T15:05+08:00 使用者裁定併入本票（擴充 D）：擴充 A 只驗**已寫成可執行斷言形式**者，故機器可導出之事實若以純散文書寫即完全不受檢——實例＝docs/GOV_TICKET_SOT.md 散文區寫「43 張 狀態未確認」，S0.4 清零後該句過期數週而 --check 全程 rc=0（生成區塊與散文區之涵蓋落差）。⇒ 修法方向：狀態宿主檔之散文區內，凡陳述機器可導出之計數或狀態分布者，須改寫為可執行斷言形式（交由擴充 A 實跑比對）或改為指向生成區塊，否則 rc=1 |
| 0090 | B-17 | 未開工 | 四張機器依賴的表改為結構化資料 ＋ 生成視圖（本票是刪除，非新增）。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：四張機器依賴之手寫表未轉為單一資料源＋生成視圖；驗收＝抽出之 key 集合與原表逐項相等且 round-trip 一致 |
| 0100 | B-18 | 未開工 | 收斂步驟是自由書寫，漏一項不會被擋。 | r4 主委裁定：改法要逐 finding ID 預填，實跑 reconcile_build 只得單一總佔位 ｜還缺：reconcile_build.sh 已能抽出全部 finding ID，但未逐 ID 預填群集骨架（實跑只得單一總佔位） |
| 0110 | B-19 | 部分完成 | brief 是最高槓桿產物，卻檢查最少。曾因此燒掉 3 輪。 | r3 三家一致 ｜還缺：doc_format_precheck 對 brief 之三項增驗僅部分落地；具名殘留 R-12——full path 不驗 EXPECTED-DELTA |
| 0120 | B-2 | 未開工 | `scripts/manifest_parse.py` 不存在——manifest 解析與三項判定無單一實作；各檢查器自行以 awk／sed 解析 yaml 會對巢狀結構與引號得出不同結果 | r3 三家一致 ｜還缺：整支 manifest_parse.py 尚未建立；須實作 §4.2 之三項判定（supersedes 子集／extension 衝突／state 值域），且禁各檢查器自行以 awk 或 sed 解析 yaml |
| 0130 | B-20 | 未開工 | 「有沒有建閘」目前完全靠主委自覺——這一層沒有閘（遞迴少一層）。 | r4 主委裁定：GOV_ENFORCEMENT_REGISTRY 係為產出端鐵律而建，非本票驅動 ｜還缺：二擇一結案閘未建——票要結案須①指向一個可 grep 驗證確實掛在 gov_check 或 hook 的檢查，或②帶一行具名說明為何無法機械強制；二者皆無不得結案。誠實邊界：本閘只擋已知形狀的契約缺閘，全新型態仍靠三家獨立審偵測 |
| 0140 | B-21 | 未開工 | 凡被 `scripts/*` 當資料源讀取的檔，須在「artifact → 驗證檢查器」註冊表有一列；�… | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：artifact 到驗證檢查器之註冊表未建，缺列 fail-closed 亦未實作；本票管覆蓋面稽核，與 B-18 互補。🔴 2026-08-14T16:20+08:00 使用者裁定擴充範圍：原文之適用面為「被 scripts 當資料源讀取的檔」，該定義**漏掉「給人看但沒人檢查」這一類**——實例即 docs/GOV_TICKET_SOT.md 之散文區與 白話說明/接下來要做什麼.md 之檔頭現況段，兩者皆長期過期而任何檢查都不會發現（生成區塊正確使人誤以為整份正確）。⇒ 範圍須由「被腳本讀取的檔」擴為「受管檔」：每份治理文件在註冊表須有一列寫明誰在檢查它、檢查什麼，或具名寫出「本檔刻意無檢查，理由為 X」；缺列即 fail-closed |
| 0150 | B-22 | 未開工 | 派工監看，不走委員通道。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：便宜模型每 2 分鐘檢查進程樹與產出檔之守望者未建。誠實邊界：Multi-Review 那類做法給的是 recall 提升，不是保證 |
| 0160 | B-23 | 未開工 | 標記／符號／字體用法改為白名單；白名單外一律拒收，要加須經討論。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：允許標記集合之白名單未定義；現行做法是列舉禁止形式（無界空間），使用者已於 2026-08-04 指出此為病根 |
| 0170 | B-24 | 部分完成 | 同一形態單日發生三次 | r3 三家一致 ｜還缺：「驗收欄凡要求跑腳本者必須同時要求狀態斷言」尚未推廣至所有票，應併入 B-17 之修法 |
| 0180 | B-25 | 部分完成 | 「改一項漏多項」的直接解——本票為使用者追問時才發現的缺口，前 22 張票�… | r3 三家一致 ｜對外不得宣稱：判準資料化三段皆已交付：schema 阻塞（WL-01）、互斥判準偵測（WL-02）、機制證據登記（WL-03，含 receipt/assumed 封閉格式與 opt-in 宿主改法子樹掃描）。🔴 仍不得宣稱已閉合：①語意互斥（不同條件字串描述同一物理事件）機械上偵測不到，三家一致判為能力邊界，見 docs/GOV_CRITERIA_REGISTRY.md 殘留 1 ②既有 700-800 行散文判準不溯及既往 ③WL-03 在現樹訊號近零、價值在面向未來，且子樹旁路四度被實構（發現曲線未收斂），十一條具名殘留見 docs/GOV_MECHANISM_REGISTRY.md ｜還缺：①語意互斥（不同條件字串描述同一物理事件）機械上偵測不到，三家一致判為能力邊界 ②既有 700-800 行散文判準不溯及既往 ③WL-03 在現樹訊號近零，子樹旁路四度被委員實構 |
| 0190 | B-26 | 未開工 | ID 空間跨檔配置無登記、無檢查——單日撞號 8 次。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：ID 空間配置閘未建。backlog 已定三條 rc=1 檢查且皆未實作——①樣式須在 docs/GOVERNANCE_ID_NAMESPACES.md §1 登記 ②新號不得與該空間既有值重複（含粗體變體之抽取）③配置紀錄須寫在該空間之唯一擁有文件內，不得散在他處。🔴 R2 更正（COMPOSER-R1-P0-01）：原寫「修法段尚未展開為可執行步驟」為事實錯誤，係主委抽取工具視窗過窄所致 |
| 0200 | B-27 | 未開工 | 專案無任何文件分類規定。 | r3 三家一致 ｜還缺：兩段交付皆未做——①規則本體（哪類文件放哪目錄／檔名慣例／票只能開在哪一份）②對應之機械檢查 |
| 0210 | B-28 | 未開工 | 凍結程序 v2.0 §6 白名單逐支列出的檢查器、§4 依賴的 registry，三者皆不存在。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：三件工具未實作且未掛上 v2.0 §3／§4／§5 所述掛點；未完成前 §7 遷移階段 1 不算 DoD 達成 |
| 0220 | B-29 | 部分完成 | 改「判定類程式」時，只驗證「我要的那個效果有了」，不驗證「還有什麼跟著變了」。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：三段強制僅落地第一段之接線（committee_run 強制把 session brief 傳入 gate）。缺①派工當下 gate 須驗 brief 之 EXPECTED-DELTA 區塊，缺區塊或格式不合即不發 token（掛點＝B-19）②交件當下 cx_run 自動跑前後對照並與宣告比對，不符即 result_state=format-failed 同輪重派（機制已存在但未接）③pre-commit 之最後攔截。另：兩份清單須由呼叫圖現算，不得手寫 |
| 0230 | B-3 | 未開工 | `rejections.yaml` 的專用 validator（不存在） | r3 三家一致 ｜還缺：獨立 validator（或 reconcile_stamps_check 之子命令）尚未建立，用以驗 §7 rejections.yaml 之四欄完整性 |
| 0240 | B-30 | 未開工 | 委員可以把自己已經寫好的產出檔覆蓋掉，系統無任何保護，且主委只會看到「�… | r3 三家一致 ｜還缺：修法方向未定案（backlog 明載 SPEC 前須先實測）。三個候選——①cx_run 於 CLI 返回後比對產出檔之 inode／大小／sha 軌跡以偵測「曾非空後歸零」②new_brief 骨架標示產出路徑專用禁挪用並列出委員自建檔命名空間 ③產出路徑加 .part、完成才 rename。🔴 ③與 B-14 之 terminal marker 是同一個機制，勿各做一份 |
| 0250 | B-31 | 部分完成 | 委員交件格式不合規（`result_state=format-failed`）之後，唯一可行路徑是「整份重跑」；… | r3 三家一致 ｜對外不得宣稱：不得說「強制」，只能說「產出端已有檢查點」 ｜還缺：原三個事後補救方向**仍全數未實作**——①新增 brief-kind: fixup（角色規則＝只准原產出方且只准改自己那個檔）②同輪重派允許附掛 brief（round 綁定改為原 brief sha 與附掛 brief sha 的有序對，審計記兩者以不破壞 provenance）③debt_clear 降級（須雙家族 adversarial 前置）。第二次事故追加之④預防（交件前自檢進 cx_run prompt 模板）已落地並有 7 條測試。🔴 R2 更正（CODEX-R1-P1-05）：原登記只寫追加項未實作，漏載原①②③仍保留為待辦 |
| 0260 | B-32 | 部分完成 | `cx_run.sh` 對「每一次派工」都注入 RECONCILE-STAMP 指示，不分 `brief-kind`； 而… | r3 三家一致 ｜還缺：改法本身 backlog 已於 2026-08-07 更正為「殘留：無」（按 brief-kind 條件注入已落地並有 mutation 測）；本票仍非收案，係因其檢查之觸發源為派工指令、產出端覆蓋登記為豁免（E-015），依產出端覆蓋鐵律不得標完成。🔴 勿照票名施工——票名描述的是病，修法方向與其相反。🔴 R2 更正（COMPOSER-R1-P2-01／GROK-R1-P1-02）：原寫「整體修法方向仍未定案」係誤採已被取代之小節標題 |
| 0270 | B-33 | 未開工 | 治理守衛的判定依賴環境 locale；在 `LC_ALL=C` 下 `gate.sh` 與 `doc_format_precheck.sh` 雙雙 fail-open。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：修法方向未定案。三個候選——①受影響腳本顯式鎖定 locale（腳本內設定，不依賴繼承）②或改用不依賴 locale 之位元組級比對 ③加一條 meta 測試：於 LC_ALL=C 與 UTF-8 兩種環境各跑一次守衛測試且結果須一致。🔴 ③是強制機制，沒有它修完仍會再漂 |
| 0280 | B-34 | 部分完成 | 角色閘把 implementer 排除在 review 之外，戳記檢查卻要求「全部 review_families�… | r3 三家一致 ｜還缺：嚴重度與修法皆待委員裁定（已列入第 0 批 SPEC R2 審查輪之必答題），未實作 |
| 0290 | B-35 | 未開工 | 沒有任何機制能判斷委員產出是否「寫完整了」——只能判斷「格式合不合規」。 一… | r3 三家一致 ｜還缺：修法方向未定案。三個候選——①委員端於 prompt 先宣告預期 finding 數，交件時比對 ②producer 寫完產生 sidecar（byte count＋sha256），publish 前比對 ③以 STATUS: DONE 類終止標記為必要條件。🔴 ③最便宜但可被截斷後偽造，須與①②併用 |
| 0300 | B-36 | 部分完成 | 收斂工具宣稱的「零掉項」只涵蓋檔案層，不涵蓋判斷層—— 一條 finding 可以完… | r4 主委裁定：reconcile_cluster_attribution_check.sh 存在且被呼叫，主委實跑抓到掉項 ｜還缺：產出端修法（reconcile_build 生成群集表骨架時預列全部來源 ID）未實作。🔴 具名殘留：產出端修法只能擋「漏」，擋不了「錯位」，已於 2026-08-05 R3 戳記輪實證 |
| 0310 | B-37 | 部分完成 | 票的優先順序目前 | r3 三家一致 ｜還缺：修法③「強制機制」未交付——原 Phase 2 文件裸數字偵測於 r1 被兩家實測判死；修法①票與事件簽章對照表留序 140 未做 |
| 0320 | B-38 | 部分完成 | 委員合法回報「0 findings」時，… | r3 三家一致 ｜還缺：核心殘留之既定修法「0-canonical-ID ⇒ FAIL」被行為表契約否決、本批不改判；語意空洞 sentinel 仍可通過四入口；修法須先統一表達方式再談收斂端如何接受 |
| 0330 | B-39 | 部分完成 | `completeness_check.sh` 的 finding-ID 通道把「長得像 ID 的合法子標題」判為非法， 使 | r3 三家一致 ｜還缺：修法方向兩家一致但驗收項 6 之 mutation（移除修法後項目 1／2 須轉紅）未完成 |
| 0340 | B-4 | 未開工 | 遷移影響已實測 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：§4.4 之戳記區白名單未實作；遷移影響已實測，見程序正文 §4.4 |
| 0350 | B-40 | 未開工 | 治理文件中「使用者定／使用者原話／依使用者裁定」的宣稱， �… | 🔴 語意註記：使用者裁定不做，非積壓工作。三態枚舉裝不下此語意（GROK-R4-P3-01） ｜無殘留：本票不做係使用者裁定，非積壓工作 ⇒ 無「還缺什麼」可填 |
| 0360 | B-41 | 未開工 | 分工規則（誰起草、誰審查、審幾家）零機械強制，且同一事實在同一份文件有三處副本。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：兩段皆未實作——①機械強制：gate.sh dispatch 於 brief-kind=impl 且 brief 或 intent 指向產出 SPEC／TODO 時拒發 token，逃生口為顯式 --drafting-fallback 且該旗標寫入 audit ②單一來源（治本，併 B-25）：ORCH 之分工規則抽成資料檔，表格與 ORCH:61／:190 皆由該檔生成、禁手寫 |
| 0370 | B-42 | 未開工 | 把 GOVB1 的 TODO 專屬閘（複數）泛化為通用閘，但既有語料誤擋率使其不得直接上線。 | r3 三家一致 ｜還缺：泛化未做；依「95% 解法就收」原則，部分泛化亦為合格交付。已採之前向修法不溯及既往（使用者 2026-08-05 定） |
| 0380 | B-43 | 未開工 | 凍結施工清單的偽碼不可執行，且與實作分叉——後批照抄即得假綠。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：修法方向明載不在本 epic，須另立 epic |
| 0390 | B-44 | 未開工 | 治理守衛可在同一 commit 內自我授權——repo 內無解，須外部信任錨。 | 🔴 語意註記：需 repo 外資源方可執行，現況客觀不可執行，非單純未排程 ｜無殘留（無可施工項）：需 repo 外資源方可執行，本票無機械綁定，與 B-43 同屬已知且具名接受之暴露面 |
| 0400 | B-45 | 未開工 | `P0-01` 全量 data-drive ＋ 五份隔離 harness 同步 JSON——受 epic 凍結 scope 阻塞。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：r5 指定之 P0-01／P0-02 修法在 epic 凍結 scope 內不可執行；需改五份測試檔，皆 in_allow=0 in_meta=0 |
| 0410 | B-46 | 未開工 | `_lifecycle_cleanup_if_temp` 之 rc 未被 caller 檢查；`rm` 失敗時 temp 殘留且回 rc=0。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：候選修法未實作——每輪私有 temp 目錄＋清理失敗時 stderr 顯式告警＋保留派工 rc，並附 rm-failure 回歸測試。🔴 禁採之修法（三家戳記確認）：caller 檢查 cleanup rc、失敗即回非零——會使派工鏈路整條停擺且不可自救，所防損害遠小於引入之風險 |
| 0420 | B-47 | 未開工 | `assumed:` 列之計數宣稱完全不受規則① 檢查——第四條逃逸路。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：擴及 assumed 之判定超出 TODO Task 1.4 宣告範圍，須改 docs/GOVB1_ 系列文件，尚未執行 |
| 0430 | B-48 | 部分完成 | `abandon_kind` 宣告「預期零 findings」，該輪卻實收 5 個 findings（含 1 個 BLOCKING P0）。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：collection-failed 之事實查核條件不同，另議。🔴 2026-08-14T17:10+08:00 使用者核可後已交付主體：no-findings-expected 之機械綁定落在 scripts/debt_clear.sh:544（產出檔含非 sentinel 之 canonical finding 即拒絕結案），逃生口 --zero-findings-verified 落審計故其使用次數可稽核；六條反例測試見 tests/governance/test_zero_findings_guard.py，含 sentinel 對照組與 mutation 反驗。🔴 具名殘留三條：①產出檔不存在時不阻擋（檔不在無從判定；因而擋不到「刪檔再結案」，不宣稱防蓄意）②歷史 20 輪標籤不實者依「面向未來不溯及既往」不回頭處理，那些 findings 無紀錄可證被看過 ③collection-failed 仍無查核 |
| 0440 | B-49 | 部分完成 | 由 CLOSED 退回 OPEN（產出端覆蓋鐵律） | r3 三家一致 ｜對外不得宣稱：🔴 已由收案**退回**：依使用者定死之產出端覆蓋鐵律，票要標收案其檢查須擋在產出端；主委原豁免理由（單次 Edit 無等價判定）經三家 r1 一致否決——閉合證據的**靜態可判定部分**無需 commit 亦可於產出端驗（CODEX-R1-P1-05／COMPOSER-R1-P1-02／GROK-R1-P2-01）。關票證據本身仍機械可驗（票標 CLOSED 時逐格於隔離副本跑六個具名 selector），但該檢查僅掛 pre-push。不得宣稱防蓄意——只防意外與遺忘；四條具名殘留見 docs/GOV_B49_ASBUILT_DELTA.md §3。重新收案之前置＝把靜態子集前移至產出端，見 docs/GOV_ENFORCEMENT_REGISTRY.md 之 E-007 ｜還缺：四條具名殘留見 docs/GOV_B49_ASBUILT_DELTA.md §3。🔴 原列於此的前置「把閉合證據之靜態可判定子集前移至產出端」**已完成**（2026-08-14）：抽成 scripts/b49_closure_static_check.py 並掛 PostToolUse，見 E-007；該子集不含隔離重放，重放仍在 pre-push |
| 0450 | B-5 | 未開工 | 這兩處在正文以「待實作」標示 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：兩處與正文 §3.4／§7b 目標態之差距未補——gate.sh:488-528 對空值與 waived 直接跳過；reconcile_stamps_check 呼叫仍只在 spec 非空之分支內 |
| 0460 | B-50 | 部分完成 | 執行端把工作區留在壞狀態、未還原；本 epic 內發生兩次且形態不同 | r3 三家一致 ｜對外不得宣稱：不得宣稱已收案——流程面永久標記為跳步，形態①④ 未做 ｜還缺：形態①與④未做；流程面永久標記為跳步。本票換來之可援引判準：只有在固定 producer contract 與輸入字母表下機械不可達才可稱上界 |
| 0470 | B-51 | 未開工 | 凍結文件宣告範圍以外 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：機械強制點未建；候選＝gate.sh 發 token 前比對「本輪宣告的修改檔集合」與「工作區實際 diff 路徑集合」，逸出即拒發。現況純靠紀律 |
| 0480 | B-52 | 未開工 | 對 stamp 輪照跑 findings-format 閘 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：兩條路都動不了——debt_clear.sh 不在 GOVB1 manifest allow；govflow_lifecycle.json 之既有節受 single-writer 契約凍結（只准新增具名節）⇒ 須於 GOVB1 之外的 epic 處理 |
| 0490 | B-53 | 未開工 | 有產出端檢查點但沒有硬閘 | r4 主委裁定：backlog 該章節之已交付（B10）為前置票紀錄，本票四方案皆被否決 ｜還缺：四方案皆被否決，現無可行修法。在本票落地前，B-31 對外一律只能說「產出端已有檢查點」，不得說「強制」 |
| 0500 | B-54 | 未開工 | 委員以自然語言輸出 | r3 三家一致 ｜對外不得宣稱：不得宣稱戳記已機械化——64 位 hex 仍由委員手抄，已實際掉字一次 ｜還缺：修法方向未裁決——由 cx_run 或 committee_run 在委員判 APPROVED 後自動生成整行，委員只輸出 APPROVED 或 REJECTED 與理由。🔴 反面風險須先答：自動生成會不會使戳記退化為橡皮圖章（現行手抄至少強迫跑一次 hash 指令）⇒ 屬取捨題非純實作題，須走 consult。根治歸待辦清單之 WL-04 |
| 0510 | B-55 | 未開工 | `gate.sh dispatch` 之旗標對「顯式傳空值」處置不一致——只有 `--spec` 擋空值，其餘靜默視同未給 | r3 三家一致 ｜對外不得宣稱：不得宣稱旗標空值處置一致——只有 --spec 擋空值 ｜還缺：把判準寫成資料（每個旗標宣告 required／optional／mode-selecting）未做；現僅 --spec 擋空值 |
| 0520 | B-56 | 未開工 | `_gate_lex_extract_*` 仍是逐字迴圈 ⇒ 長字串為平方級（實測 15.32 秒） | r3 三家一致 ｜對外不得宣稱：低優先；不得以安全風險為由排程（慢不等於危險，見 C5 延伸勘誤） ｜還缺：須先獨立判定 j = i + RLENGTH 是否為缺陷（附反例），再談效能；效能修法沿用 Phase 3 之視窗手法（WIN_AT／CH／SLICE／NEXT_OF） |
| 0530 | B-57 | 未開工 | `parse_heredoc_delim` 開頭之 `rest = substr(s, pos)` 為全尾切 ⇒ 平方級 | r3 三家一致 ｜對外不得宣稱：低優先；heredoc 密集 500K 需 434 秒，但無已知產生者，不得稱安全風險 ｜還缺：同 B-56 之視窗手法未實作；另 substr 三字元取用亦應改走 SLICE |
| 0540 | B-58 | 未開工 | 前導換行被丟棄 | r3 三家一致 ｜對外不得宣稱：不得宣稱前導空行處理已判定——現行為丟棄，是否為缺陷未評估 ｜還缺：前導空行是否為缺陷尚未判定；若判為缺陷，修法須同步更新回歸樁並走 phase2_expected_flips 登記為預期翻轉 |
| 0550 | B-59 | 未開工 | wrapper 名稱／選項語法／分隔符／重定向／直譯器旗標／合併旗標／引號形式 | r3 三家一致 ｜對外不得宣稱：不得宣稱 dispatch gate 已完備——判定式為黑名單列舉，三輪各找到四條新形態 ｜還缺：指令 tokenize 化（逐命令位置解 argv 首元素比對封閉 executor_clis）未實作，屬大重寫須另立 epic。優先序高——這是唯一能讓漏放形態停止增生的方向 |
| 0560 | B-6 | 未開工 | gate token 未綁 worktree（`GATE-TOKEN-BINDING` 債之延伸），同一 token 可跨 worktree 使用 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：token 未綁 worktree（GATE-TOKEN-BINDING 債之延伸）；backlog 明載不在該程序範圍，須另立 epic |
| 0570 | B-60 | 未開工 | `review_quorum_check.sh` 的家族清單硬編未讀 SoT，名冊改動不會連動 | r3 三家一致 ｜對外不得宣稱：不得宣稱 quorum 讀 SoT——review_quorum_check.sh 家族清單仍硬編，_DRIFT 已釘故測試通過不代表連動 ｜還缺：改讀共用 getter（families_get review_families）未實作；並須補 mutation——以不同的合法子集（非現行三家）證明它不是只對現行名單有效 |
| 0580 | B-61 | 未開工 | `_role_gate.sh` 之 `known_only` 對未知家族靜默放行（fail-open） | r3 三家一致 ｜對外不得宣稱：不得宣稱角色閘已無 fail-open——known_only 對未知家族仍靜默放行；既有行為非本輪引入 ｜還缺：known_only 之「跳過」須改為具名白名單（哪些家族允許交給下游 dispatch 判定），而非「不認得就放行」；與 B-59 同型（黑名單 vs 封閉集合） |
| 0590 | B-7 | 部分完成 | 要求委員手抄 task-id，抄錯是必然而非偶然——曾有兩家抄了 brief 的格式範例字串，多花兩輪補正 | r3 三家一致 ｜還缺：cx_run 已從源頭注入 task-id 並於缺漏時拒派，但 brief 側表述尚未全面改為「用注入值」，委員仍可能手抄；根治與 B-54 同屬 WL-04 |
| 0600 | B-8 | 未開工 | 皆為 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` v1.0 > 首次實戰才現形的問題：該程序創造了「D 延伸檔�… | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：正式的拒絕清單確認機制未建；現行緩解僅「--rejected 覆寫限測試 harness」與「每次執行印出清單 sha256」 |
| 0610 | B-9 | 未開工 | `docs/` 內的 D 延伸檔無法取得可過機檢的戳記。 | r4 三家一致（歸屬判準：他票副產物不算本票落地） ｜還缺：修法須走程序 §5 的 R（完整三家審＋使用者裁定），尚未啟動 |
<!-- END GENERATED: governance-ticket-sot -->

---

## 🔴 這張票掛在哪／為什麼沒掛（同一份資料，不是副本）

> 使用者 2026-08-14 逐字：「**把治理 epic 的票，做過的能掛上的就掛上，不能掛的寫原因。**」
> 那件事做完了，但答案原本只存在 `docs/GOV_ENFORCEMENT_REGISTRY.md`，
> 打開本檔看不到 ⇒ **使用者問了五次都以為沒做**。
>
> ⇒ 下表與該檔**是同一個 fact-key 的同一份 rows**（`governance-enforcement` 之多宿主投影），
> **不是抄過來的副本**。改一處兩邊同時變，手改會被 fail-closed 擋下。
>
> **怎麼讀**：`強制側 = 產出端` ⇒ **已掛上**，`掛載點` 欄就是掛在哪。
> `強制側 = 豁免` ⇒ **不掛**，`豁免理由` 欄就是原因（体例＝須同時寫
> 「`PreToolUse不可：`」「`PostToolUse不可：`」「`部分閘：`」三段）。
>
> 🔴 **未開工的票不在下表**——它們沒有產物，沒有東西可掛。要它們有掛載點，
> 得先做它們的改法，那是排程決策不是掛載問題。

<!-- BEGIN GENERATED: governance-enforcement -->
| 檢查ID | 對應票 | 掛載點 | 強制側 | 豁免理由 | 判定型 |
|---|---|---|---|---|---|
| E-001 | B-25 | PostToolUse:Edit,Write:scripts/factkey_write_guard.sh | 產出端 | 實作位置：scripts/factkey_write_guard.sh:116（寫檔當下對受管檔重跑 gen_fact_key_blocks --check） | 一致性型 |
| E-002 | B-25 | pre-push:gov_check.sh 第 3 段 | 豁免 | PreToolUse不可：本列記錄的是 pre-push 之第二層掛載，該階段依定義在 commit 之後。PostToolUse不可：**不適用**——同一判定已由 E-001 掛在 PostToolUse；本列僅記錄 defense-in-depth 之第二個掛載點，非缺口。部分閘：有——scripts/factkey_write_guard.sh:116（同一判定之產出端掛載） | n/a |
| E-003 | B-38 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:150（findings 分支呼叫 cx_run --selfcheck；零 findings 之 sentinel 形態與必填欄於該路徑檢查，反例已實跑） | 內容型 |
| E-004 | B-31 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:150（與委員交件跑同一支檢查、同一組參數）。誠實邊界：票 SoT 之對外用語限「產出端已有檢查點」，不得稱強制 | 內容型 |
| E-005 | G-7 | commit-msg:g7_trailer_precheck.sh ＋ pre-push:govb1_final_gate.sh --only g7 | 豁免 | PreToolUse不可：判定式為 base..HEAD 之 endpoint 淨差，寫入前無 commit 可算。PostToolUse不可：判定對象是 commit 的屬性（訊息末段之 Governance-Scope trailer），寫檔當下該物件尚不存在；而寫檔當下算得出的「路徑在 scope 外」若單獨告警，對本 repo 多數新增路徑恆真 ⇒ 高頻無訊號。部分閘：有——scripts/g7_trailer_precheck.sh:83（commit-msg 階段：staged 含 scope 外路徑而訊息末段無 trailer 即擋；四向反例已驗，含 trailer 放中間段仍擋、只動 scope 內檔則放行）。🔴 R6 更正：原登記「本票不存在可前移的靜態子集」為事實錯誤——同日兩次 G-7 紅正是此子集，且因豁免須「該路徑只被帶 trailer 的 commit 觸及」，補後續 commit 解不掉，只能重寫歷史 | n/a |
| E-006 | 測試套件 | pre-push:gov_check.sh 第 5 段 | 豁免 | PreToolUse不可：全套 pytest 為十分鐘級，寫入前執行會使每次編輯停擺。PostToolUse不可：同上——此為**成本型**而非判定型限制，技術上跑得動、代價不可接受，兩者須誠實區分。部分閘：有——各票之承重判準已分散於本表其他列之產出端掛載，代表兩處為 scripts/factkey_write_guard.sh:116 與 scripts/doc_format_precheck.sh:150；測試子集化之提案見 HANDOFF 之「把測試選擇機械化」節（未開工） | n/a |
| E-007 | B-49 | PostToolUse:Edit,Write:scripts/narrow_check_router.sh | 產出端 | 實作位置：scripts/b49_closure_static_check.py:178（六格 selector 之實質斷言逐格判定；清單完整性於 :155 起之 check_static 前段）。🔴 R8 更正（2026-08-14）：原登記為豁免，理由「靜態子集尚未抽成可掛的檢查」——該改法**已完成**：靜態可判定的兩條（selector 清單完整性、每格是否有可達之實質斷言）已抽成獨立腳本並掛上 PostToolUse，寫檔當下即判；tests/governance/test_govb1_contract_matrix.py 改為自本檔 import 同一份定義，不再各持一份。誠實邊界：本層**不取代** pre-push 之 _assert_b49_closure_evidence（隔離重放、rc／passed／skipped 比對確實需要可重放標的，掛不上產出端），兩者為 defense-in-depth；且 assert True 仍會通過，只防意外掏空與重構失手 | 內容型 |
| E-008 | B-7 | — | 豁免 | PreToolUse不可：判定對象為委員產出的戳記行，派工前尚不存在。PostToolUse不可：🔴 R8 實測更正（2026-08-14T19:0x+08:00）——原登記「不經主控端 Edit/Write ⇒ 該 hook 不會被觸發」**只對了一半**：真的把探針掛上 PostToolUse:Bash 後，派工指令**確實觸發**它（實證：scripts/probe_dispatch_posttooluse.sh，記錄於 .claude/tmp/probe_b50.log）。真正的限制是**時點**：委員派工依合約以背景執行（前景必 timeout），hook 觸發於**啟動當下**，該時點 handoffs/ 下只有 brief、無任何委員產出檔（實測 ls 僅列出 BRIEF 一列）⇒ 戳記行尚不存在，無標的可判。部分閘：有——scripts/cx_run.sh:776（派工 prompt 逐字注入 task-id 並明令 brief 內範例值不得採用，從源頭消滅手抄）＋ scripts/cx_run.sh:413（task_id 缺漏即拒派）。🔴 R6 更正：原登記「改法未完成、現樹無對應檢查可掛、部分閘無」為事實錯誤 | n/a |
| E-009 | B-10 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/template_check.sh:324（dext 分支之必填錨點檢查；由 scripts/doc_format_precheck.sh:80 判型後呼叫）。🔴 R6 更正：原登記為豁免，理由寫「輸入為完整文件，非單次編輯內容」——那只證明不能 PreToolUse；實跑反例（寫入缺錨點之 D 延伸檔）當下即紅，證明 PostToolUse 本就掛得上、且早已掛上 | 內容型 |
| E-010 | B-15 | PreToolUse:Task,Bash,Write:scripts/gate_check.sh | 產出端 | 實作位置：scripts/gate_check.sh:218（_gate_cmd_is_dispatch 之派工判定，掛 PreToolUse ⇒ 指令送出前即判）。🔴 R6 更正：原登記為豁免，理由「須完整指令上下文方能判」——完整指令字串正是 PreToolUse 的輸入，該理由不成立。誠實邊界：本票之殘留是**誤擋率**而非缺掛載，對外不得宣稱誤擋已修復 | 內容型 |
| E-011 | B-16 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/template_check.sh:711（_check_scope_claim 與 _run_assert_lines 之接線，僅 docs 之 SPEC／TODO 檔套用）。誠實邊界：寫檔階段**不執行** ASSERT 行（T0 自鎖止血），只驗文法與錨點，執行留給 gate.sh。🔴 R6 更正：原登記為豁免，惟其 R5 更正已自承「該檢查亦經 doc_format_precheck 路徑觸發」，與豁免宣稱自相矛盾 | 內容型 |
| E-012 | B-19 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/doc_format_precheck.sh:195（handoffs 下含 brief-kind 標記之檔即路由至 brief_conformance_check）。🔴 R6 更正：原登記「部分閘是否已掛：無」為事實錯誤——實跑反例（寫入不引用範本之 brief）當下即紅。殘留 R-12（full path 不驗 EXPECTED-DELTA）仍在，屬檢查深度不足，非未掛載 | 內容型 |
| E-013 | B-24 | — | 豁免 | PreToolUse不可：現樹無對應判定式可執行（本票改法為紀律條文）。PostToolUse不可：同上——不是掛不上，是**沒有東西可掛**；「無檢查」與「檢查掛不了」不得混為一談。部分閘：無 | n/a |
| E-014 | B-29 | — | 豁免 | PreToolUse不可：判定輸入為派工參數與 brief 檔內容之比對，寫檔當下無派工事件。PostToolUse不可：觸發源為派工指令而非 Edit/Write ⇒ 該 hook 不觸發；改掛 PostToolUse:Bash 亦判不了，因判定需 gate 內部狀態（已開 session、brief 已解析），非指令字串可導出。部分閘：有——scripts/committee_run.sh:420（gate_args 追加 --brief，否則 gate 之 --brief 掛點空轉）。🔴 R6 更正：原填 :410 落在註解行。🔴 R7 更正（GROK-R2-P1-01）：R6 改填之 :411 為**非註解但指錯行**（該行是工作區漂移之 echo）——檢查 ⑧ 只拒註解／空行／缺檔，擋不掉語意錯位，此為其具名能力邊界 | n/a |
| E-015 | B-32 | — | 豁免 | PreToolUse不可：判定輸入為 brief-kind 與派工結果（CLI rc、輸出檔），寫入前皆不存在。PostToolUse不可：🔴 R8 實測更正（2026-08-14T19:0x+08:00）——原登記「觸發源為派工指令而非 Edit/Write ⇒ 該 hook 不觸發」為**事實錯誤**：掛上 PostToolUse:Bash 探針後派工指令確實觸發它。真正的限制是**時點**：派工依合約背景執行，hook 觸發於啟動當下，此時委員產出檔與 CLI rc 皆尚未產生（實測 ls 僅列出 BRIEF）⇒ brief-kind 與派工結果無從比對。部分閘：有——scripts/cx_run.sh:495（_maybe_register_stamp_output，僅 stamp kind 且三條件成立才註冊）。🔴 R6 更正：原填 :493 落在註解行；R5 之「部分閘已落地」結論不變 | n/a |
| E-016 | B-34 | — | 豁免 | PreToolUse不可：現樹無對應判定式（角色閘與戳記檢查之一致性改法未完成）。PostToolUse不可：同上——無物可掛，非掛不上。部分閘：無 | n/a |
| E-017 | B-36 | — | 豁免 | PreToolUse不可：群集歸屬須整份收斂檔方能判，寫入前內容不完整。PostToolUse不可：**理由為「現行無可掛之阻擋判定」，不是「掛不上」**（CODEX-R2-P1-05 要求釐清）——synth 檔之寫入已由 scripts/doc_format_precheck.sh:96 路由，技術上掛得上；但 scripts/reconcile_cluster_attribution_check.sh 全檔僅為純報告、無失敗條件（三家 r2 實跑：對未被引用之 ID 仍 rc=0），且其唯一訊號在收斂檔撰寫過程中恆為真 ⇒ 掛上不產生任何拒絕語意且高誤擋（與 WL-02 開工前量測推翻字面設計同型）。⇒ 屬該票改法未完成。部分閘：有——scripts/reconcile_build.sh:378（收集節點呼叫，提示不阻擋） | n/a |
| E-018 | B-37 | — | 豁免 | PreToolUse不可：本票產物為唯讀彙整報表，無「不通過」語意，無可阻擋之判定。PostToolUse不可：**理由為「無拒絕條件可掛」，不是「掛不上」**（CODEX-R2-P1-05 要求釐清）——掛得上，但本票產物本質為唯讀彙整，掛上不產生任何拒絕語意。部分閘：有——scripts/friction_tally.sh:155（彙整輸出行；唯讀無阻擋語意。🔴 該腳本檔頭已依使用者 2026-08-14T18:05+08:00 之要求寫死「這裡沒有機械保護」） | n/a |
| E-019 | B-39 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | 實作位置：scripts/completeness_check.sh:157（heading 路由與必填欄判定；由 scripts/doc_format_precheck.sh:150 之 findings 分支經 cx_run --selfcheck 呼叫）。🔴 R6 更正：原登記為豁免且原填 :135 落在註解行；實跑反例（P0 來源摘要寫行號而非雜湊）當下即紅。誠實邊界：跨檔完整性（來源 ID 是否全在綜合）仍須 lock 與全部來源，屬合理的消費端檢查 | 內容型 |
| E-020 | B-50 | — | 豁免 | PreToolUse不可：判定需「派工前」與「派工後」兩個工作區快照之差，寫入前只有單點。PostToolUse不可：🔴 R8 實測更正（2026-08-14T19:0x+08:00）——真的掛上 PostToolUse:Bash 探針實測，得到**兩個各自獨立就足以判死**的理由：①hook 只有**一個**時間點，「派工前」那個快照不在其視野內，差值算不出來 ②派工依合約背景執行 ⇒ 觸發當下「派工後」根本尚未發生（實測該時點 git status --porcelain 計數等於派工前之值）。原登記之成本理由（對每個 Bash 呼叫做 git status 全掃）仍成立，但那是次要理由，主因是上述時點問題。部分閘：有——scripts/committee_run.sh:320（_ws_snapshot，派工前後比對）。🔴 R6 更正：原填 :267 落在註解行。🔴 R7 更正：R6 改填之 :311 於同輪內因本檔新增 mkdir 守衛而位移成註解行，三家 r2 一致以 --check rc=1 攔下——**行號引用會隨上游編輯漂移，這是本機制的內建代價，換來的是不會靜默腐爛** | n/a |
| E-021 | B-48 | PreToolUse:Task,Bash,Write:scripts/gate_check.sh | 產出端 | 實作位置：scripts/gate_check.sh:250（_gate_precheck_content 之 no-findings-expected 標籤真偽判定，掛 PreToolUse ⇒ debt_clear 指令送出前即判）。工具內部第一層在 scripts/debt_clear.sh:548（_dc_zero_findings_guard，結案前擋）。誠實邊界：本層**不比工具內部更早**（PreToolUse 之後工具緊接著就跑），價值在 defense-in-depth 與「指令字串即可判」，**不得對外稱前移**。逃生口 --zero-findings-verified 落審計（scripts/debt_clear.sh:462） | 內容型 |
<!-- END GENERATED: governance-enforcement -->
