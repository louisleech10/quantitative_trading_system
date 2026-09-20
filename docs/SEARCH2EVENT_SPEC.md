# SEARCH2EVENT — 搜尋結果直送事件匯入端（純轉接器） — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260919-icpath-x-consult-r1/synth.md`　|　日期：2026-09-20　|　對應 TODO：`docs/SEARCH2EVENT_TODO.md`（本 SPEC 凍結後產）

---

## §SUPERSEDED 本 SPEC 已停用（2026-09-20 使用者方向裁定）

🔴 **本檔不凍結、不產 TODO、不進實作。** 使用者於 2026-09-20 裁定：SEARCH2EVENT 之框架錯誤——
七輪 SPEC（v1→v7）全在解「把搜尋結果**搬**到事件匯入端」，而使用者要的是
「**條件觸發（如 EMA5>EMA10>EMA30）買入、持有 N 期之報酬，與隨機買入持有同期之報酬比較**」。
實查 `momentum/DataExtraction/case_search_engine.py` 之條件可用欄位僅
`price_change`／`closing_strength`／`price_position`／`volume_multiplier`／`taker_buy_ratio` ＋ OHLCV ＋ future return，
**無任何均線／EMA／RSI／MACD** ⇒ 搬運做完也答不了使用者的問題。整票方向重定為 **EVENTSCAN**。

**本檔之保留價值＝以下已查證事實**（r7 兩家對抗審查之六條 finding，逐條處置見
`handoffs/reconcile/20260920-search2event-x-review-r7/synth.md`；全數採納並轉為 EVENTSCAN 之輸入）：

1. **觸發批不能單獨匯入**：單一正例搜尋每列 `positive_case=True`，非空單類別批被 `missing_control_group` 拒收（`api/services/.../generator.py:152`）。
2. **隨機對照批不能由搜尋頁三欄 FormData 直送**：檔案端點無 `random_control_spec` 入參，缺 batch-level receipt 即 `random_control_spec_missing`；隨機批須走既有端點 `/case/import-events/random-control`。
3. **`two_stage` 搜尋情境不可匯入**：其 producer 刻意省略 `label` 並標 `label_origin=search_unlabeled`（契約 `not_importable`），且此時 `skipped=[]` ⇒「skipped 為空」不等於「可匯入」。
4. **「重算比對」型驗收須另配契約形狀之獨立斷言**，否則產生器與 oracle 同時漂移即恆綠。
5. **改 SPEC 任一條文後須 grep 全檔同義敘述並同步**（本票兩次犯：v3 之「正規化」殘句、v7 之 Task 1.1 ③）。
6. **傳輸層結論仍可用**（若 EVENTSCAN 需要檔案端點）：`POST /api/v1/case/import-events?verify_source_digest=true`、FormData 恰三欄 `{file, source_file, lookahead_declaration}`、`file` 為裸陣列且須為帶 `.json` 檔名之 `File` part。

**以下全文自 §RISK 起為停用內容**，保留供追溯，**不得作為實作依據**。

---

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：**大**。
  🔴 **v2 更正（`CODEX-R56-P1-01`）**：v1 寫「中」是**主委違反自身憲法**。`CLAUDE.md:29` 之判準逐字為
  「命中任一 a-d（模組會變、原則不變；**不看檔案數**）」⇒ 已標 `RISK-HIT: b` 即為大，
  **不得再以「語意不動、缺口很小」自評降級**。v1 之降級推理（payload 產生器不動）是嚴重度自評，
  不是判準。本列保留此紀錄：同型（拿自評取代機械判準）會再犯。
RISK-HIT: b

- **命中高風險原則**：**(b) 跨模組／共用路徑**——新增自 `搜尋頁 → 事件匯入端` 之生產路徑，
  跨 `frontend/src/app/search`、`frontend/src/lib/api.ts`、`api/routes/case.py`、
  `api/services/case_import_service.py` 四處（`CODEX-R56-P1-04` 之範圍認定）。
  **未命中 (a)／(d)**：payload 產生器與其守衛逐字不動（見 §C-1）；本票不新增任何統計量、不動任何數值。
  🔴 **誠實邊界**：`CODEX-R56-P1-04` 主張來源證明與宣告屬資料正確性風險。主委判定該風險由
  §C-1 四條鎖死（尤其 C-1-4 宣告表單欄必送），非本票新造；若審查認為該鎖不足，
  應改標 `RISK-HIT: a,b` 並補 §G。
  **未命中 (c)**：兩 Phase、可獨立回退（§R）。
- **大票附帶義務**：白話簡述於本 SPEC 凍結後另產（置於 `白話說明/`），不混寫入本檔（文件分層）。

## §A 假設與待使用者確認（事故：拿推論代替問人）

FACT-RECEIPT: `grep -rn "import-events" frontend/src/lib/api.ts` → 命中檔案端點、CSV、宣告、random-control 四處，**無** `/case/import-events/json` 之 client 函式（主委實跑 2026-09-20）
FACT-RECEIPT: `sed -n '707,712p' frontend/src/app/search/page.tsx` → 匯出整段包在 `withExportDeclarationGuard(declState, { proceed: async () => { … } })` 內（主委實跑 2026-09-20）
FACT-RECEIPT: `api/routes/case.py::import_events_json` 對 `verify_source_digest=true` **顯式 400**（`verify_unsupported_on_json_endpoint`），理由＝JSON 端點之位元組為 request body、與契約所指「使用者原始來源檔」必然不符（主委讀碼 2026-09-20）
FACT-RECEIPT: `import_events_json` 傳 `carried_declaration_acknowledged=True`（該路由自動視為已勾選；殘留 `R35-L2-ACK`）（主委讀碼 2026-09-20）

**決策點已裁定（v2；兩家一致選 `B`，主委採納）**：採 **`B`＝走檔案端點**。

| 選項 | 裁定 | 理由（逐條可驗） |
|---|---|---|
| `A` 走 JSON 端點＋具名揭露 | **否決** | 不只是失去 digest 對證：該路由傳 `carried_declaration_acknowledged=True`（`api/routes/case.py:283`），會**把列內宣告自動視為已勾選**，繞過 UI 對「調低／不可驗證答案窗」之明示確認（`CODEX-R56-P1-04`） |
| `B` 走檔案端點 | **採納** | 保住 `verify_source_digest` 對證，且宣告走表單欄、不觸發自動勾選 |
| `C` 兩段式預檢 | 否決 | 使用者仍須手動上傳，缺口只解一半，且與 `B` 相比無額外保證 |

🔴 **`B` 之 wire 於本 SPEC 寫死**（`COMPOSER-R56-P1-01` 實跑證實：少送宣告表單欄會使「調低答案窗」之批被
`lookahead_declaration_unacknowledged_lowering` 拒收）：
- 端點：`POST /api/v1/case/import-events?verify_source_digest=true`
- `FormData` **恰三欄之封閉集合**：`file`（＝`buildEventContractRecords` 輸出之 records **裸陣列** JSON）、
  `source_file`（＝同次輸出之 `source_file_text`）、`lookahead_declaration`（＝搜尋頁現行宣告狀態之
  payload，含 `acknowledged_unverifiable`）。三欄缺一即為缺陷（C-1-4）。
- 🔴 **v4（`CODEX-R58-P1-02`）**：`file` 與 `source_file` **必須是帶檔名之 `File` part**
  （`new File([...], 'events.json'|'events.source.json', { type: 'application/json' })`），
  **不得以字串 `append`**——後端該兩參數型別為 `Optional[UploadFile]`，送字串時三欄名之測試照樣綠，
  但後端收不到檔案。`lookahead_declaration` 為表單字串欄，不在此限。

**待使用者確認：無**（技術選擇交委員會；使用者之審閱點為本 SPEC 凍結後之白話結論）。
**已確認（使用者裁定）**：2026-09-20 —— 本票排序第 1；**手動驗收併入 UAT（`R-3`）**，本票不另開 UAT 條目。
🔴 **v6 補可追蹤之 UAT 條目（`CODEX-R60-P2-02`：僅寫「併入 R-3」而無 owner／畫面／成功證據，等於沒有驗收）**。
併入 `docs/SPLITUNIFY_TODO.md` §E `R-3` 之條目逐字如下：
- **步驟 1**：於 `/search` 跑一次搜尋、完成答案窗宣告，按「直接匯入」。
- **步驟 2**：於 `/data-preparation` 之已匯入事件批清單中，找到步驟 1 畫面所顯示之 `import_id`。
- **成功證據**：①該批之筆數等於**產生器實際輸出之 records 筆數**（🔴 v7 更正：v6 寫「與搜尋結果筆數相同」，
  而產生器會跳過部分列 ⇒ 有跳過時該條會**假紅**，`COMPOSER-R61-P2-01`）；②若有跳過，畫面須已顯示跳過筆數與原因；
  ③以該批跑一次事件型 IC 分析不被拒收。
- **確認者**：使用者（本專案 UAT 一律由使用者確認）。**owner**：SEARCH2EVENT 票主委負責備妥可重跑之步驟。

## §C 約束（不重抄，引用 + 只列本任務相關）

### C-1 🔴 單一 payload 產生器與單一守衛（範圍鎖死之機械判準）

委員會 2026-09-19 共識之放行條件＝**純轉接器**。本 SPEC 將其寫成三條可機械驗之約束：

1. **payload 唯一產生點**＝`buildEventContractRecords`。一鍵路徑**不得**自行組裝 records、不得就地改寫其輸出。
   判準：`frontend/src/app/search/page.tsx` 內 `records` 之來源運算式，兩條路徑逐字相同。
2. **守衛唯一入口**＝`withExportDeclarationGuard`。一鍵路徑**必須**在同一個 `proceed` 內，
   **不得**另寫一份條件判斷。理由：該守衛擋的是 look-ahead 宣告未過；繞過它等於開一個無宣告之事件批入口。
3. **不得挾帶下游欄位**。理由＝`ICPATH`／`GLOBALH` 尚未定型逐列模式與答案窗欄之身分
   （`CODEX-R55-P2-04`）；本票先接線即固定格式將造成返工。
   🔴 **v2 改寫判準（`CODEX-R56-P1-02`／`COMPOSER-R56-P2-01`：v1 之「body 鍵集 ⊆ 契約欄位」不可執行
   ——envelope／FormData 之鍵本來就不是逐列契約欄名，照字面寫測試會恆紅）**。改為兩層：
   - **傳輸層**：`FormData` 鍵集**恰等於**封閉集合 `{file, source_file, lookahead_declaration}`（多一欄即紅）。
   - **內容層**：🔴 **v6 改為深度相等（`CODEX-R60-P1-01`）**——v2–v5 之「頂層鍵集 ⊆ 契約欄位」
     **只管頂層**，在巢狀欄位（例 `label_definition` 內）塞一個契約未列之鍵仍會被後端接受並保留。
     改判準為：`file` 內之 records **與獨立重算之 `buildEventContractRecords` 輸出 `toEqual` 深度相等**。
     🔴 **v7 補（`COMPOSER-R61-P1-01`）**：比對對象**必須是以同輸入重新呼叫產生器所得之新物件**，
     不得比對 adapter 手上的同一個物件參考——後者在 adapter **就地改寫**該物件時**恆綠**（拿自己比自己）。
     此判準同時涵蓋原本的「鍵集受限」與「不得多於產生器輸出」，且封住任意深度之挾帶——
     因為「純轉接器」的定義本就是**原樣轉送**，任何差異（含巢狀多一鍵）皆為違反。
   - 🔴 **v3 新增三條（`CODEX-R57-P1-01` ≡ `COMPOSER-R57-P1-01`，兩家獨立命中同一洞）**：
     前兩層**鎖不住 `file` part 本身的形狀**，實測可繞之三條路徑各自封死——
     (i) **檔名必須以 `.json` 結尾**：檔名非 `.json` 時後端 `parse_upload` 走 CSV 分支並**回空列表**。
         🔴 **v6 事實更正（`CODEX-R60-P2-01`）**：v3–v5 於此寫「得到一個**成功但空**的批」係**主委轉述時放大後果**
         ——實查後續 `import_records` 會以 `contract_violation` 拒收，**不會成功落檔**。
         本條之缺陷仍成立（使用者得到的是一個語意不明的拒收，而非「檔名錯了」），mutation 保留；
         但描述改為事實。**轉述他人碼證時不得加碼**。
     (ii) **envelope 形狀明定為裸陣列**（`[record, …]`）：檔案端點對裸陣列／`{records:[…]}`／整包下載檔三者皆收，
         而物件 envelope 可另帶 `label_rule` 經 `_envelope_label_rule` 送進 `import_records`
         ⇒ 正是本條要禁的「挾帶下游欄位」。本票一律送裸陣列。
     (iii) **envelope 不得有任何額外鍵**：送裸陣列即自然滿足；測試仍須顯式斷言頂層為 `Array.isArray` 且非物件。

4. 🔴 **宣告與對證三者必送、不得省**（v2 新增；`CODEX-R56-P1-03`／`COMPOSER-R56-P1-01`）：
   `verify_source_digest=true`、`source_file` 欄、`lookahead_declaration` 欄**三者缺一即為缺陷**。
   理由：C-1 前三條只鎖 producer／guard／records 形狀，刪掉宣告表單欄仍可全綠而匯入端回 4xx
   （或更糟：實作者為了讓它過而把檔案路由也改成自動勾選，那會違反 §C-2 並把 `R35-L2-ACK`
   自「僅 JSON 直傳」洩漏到有宣告 UI 之檔案路徑）。
   判準：以**調低答案窗且未勾選**之 records 實跑一次，須得到 `lookahead_declaration_unacknowledged_lowering`；
   勾選後須 `ok`。
   🔴 **v3 補（`CODEX-R57-P2-02` ≡ `COMPOSER-R57-P2-01`，兩家撞題）**：只驗「欄存在」＋「後端會拒」**不夠**
   ——送一份**內容不同**的宣告仍可通過該兩條。須再加一條：`lookahead_declaration` 欄之 JSON
   **逐鍵等於**同一個 `proceed` 內由 `buildDeclarationPayload(declState.declared, declState.acknowledged, declState.preview)`
   產出者（同源，非另組一份），且該產出**不得為 `null`**（v5 更正簽名；理由見 Task 1.1 ⑥）。

5. 🔴 **v7 新增：產生器之 `skipped` 必須揭露並由使用者確認（`CODEX-R61-P1-01` ≡ `COMPOSER-R61-P2-01`，兩家撞題）**。
   `buildEventContractRecords` 會跳過部分列並記入 `skipped: {index, reason}[]`，
   reason 之實際字面為 `unparseable_timestamp` 與 **`missing_positive_case_flag`**
   （`frontend/src/lib/eventExport.ts:482-501`；🔴 委員轉述為 `missing_positive_case`，**以碼內字面為準**）
   ⇒ **搜尋結果列數 ≠ 送出 records 筆數**。
   本票之處置：**不 fail-closed**（下載路徑現況即允許跳過，改為拒送會違反 C-3 之「行為不變」精神），
   但**一鍵路徑送出前必須顯示跳過筆數與逐項原因，並取得使用者確認**；使用者取消即不送。
   判準：`skipped.length > 0` 時未顯示或未確認即送出 ⇒ 缺陷。

### C-2 後端不改

`api/routes/case.py`、`api/services/case_import_service.py`、`momentum/Analysis/contracts/event_import_contract.json`
**本票一律不改**。任何「後端要配合改一下」之需求即代表 C-1 被違反，應退回重新設計。

### C-3 兩條路徑並存，下載路徑行為逐字不變

既有「下載 `events_*.json` ＋ `events_*.source.json`」之流程**不得移除、不得改變輸出位元組**。
理由：它是目前唯一能做來源檔對證之路徑（§A 決策點 `B`／`C` 未採時尤然）。

### C-4 失敗與揭露

匯入端回 4xx（含 `EventImportRejected` 之 `kind`／`message`）時，畫面須**原樣顯示該 kind 與 message**，
不得吞成通用錯誤；成功時須顯示落檔之 `import_id` 與筆數，並提供前往該批之路徑。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）

見 §N：本票未命中 (a)／(d)，Golden N/A。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 1 — 轉接器與出口（依賴：無）

**Task 1.1 — 事件匯入 client 函式**
- 檔案：`frontend/src/lib/api.ts`（新增一支；wire 依 §A 已裁定之 `B`）。
- 驗證：`vitest run src/lib/search2eventClient.test.ts` rc=0，**七條**斷言——① 送出之 URL 逐字等於 `/api/v1/case/import-events?verify_source_digest=true` ② `Array.from(formData.keys()).sort()` 逐值等於 `['file','lookahead_declaration','source_file']` ③ **v6 同步改為深度相等**（隨 C-1-3 內容層改判；`CODEX-R60-P1-01`）：解析 `file` 後之 records 與同一次 `buildEventContractRecords` 輸出 `toEqual` **深度相等**——舊版「頂層鍵集 ⊆ 契約欄位」只管頂層，巢狀塞鍵仍會過④ `file` 內容 `Array.isArray` 為 true 且頂層非物件（C-1-3 (ii)(iii)）⑤ **v4**：`formData.get('file')` 與 `get('source_file')` 皆 `instanceof File` 且 `.name` 分別以 `.json` 結尾（`CODEX-R58-P1-02`）⑥ **v5 更正（`CODEX-R59-P1-02` ≡ `COMPOSER-R59-P1-01`，兩家撞題）**：`JSON.parse(String(formData.get('lookahead_declaration')))` 與同一 `proceed` 內 **`buildDeclarationPayload(declState.declared, declState.acknowledged, declState.preview)`**（實查簽名：`frontend/src/lib/lookaheadDeclaration.ts:173-177` 為**三參**，且 `preview` 缺或空即 `return null`）之產出 `toEqual` 逐鍵相等，**並顯式斷言該產出非 `null`**。
  🔴 v4 誤寫為單參 `buildDeclarationPayload(declState)` ⇒ 實際回 `null`，斷言變成 `null === null` **恆綠**，而 client 會把字串 `"null"` 當表單欄送出、後端 `_form_json_dict` 以非物件 400。**主委未查函式簽名即寫死呼叫式**，與 v3 寫死不存在路徑同型（同一票內第二次）。
⑦ **v5**（`CODEX-R59-P1-01`）：`await (formData.get('source_file') as File).text()` **逐字等於** 同次輸出之 `payload.source_file_text`——只驗「是 File 且檔名 `.json`」擋不住「metadata 合法但內容被換掉」，而後端之 source digest 對證會因此拒收。
- 邊界：① 匯入端回 4xx ⇒ 丟出帶 `kind` 與 `message` 之具名錯誤 ② 網路失敗 ⇒ 不得吞成成功 ③ 三欄缺任一 ⇒ 本函式即拒送（不等後端 4xx）。
- **存活至**：`ICPATH` 之後仍保留（該票不改本出口）。
- **覆蓋風險**：無後續 Phase 改本函式簽名。
- 不可做：不得在本函式內組裝或改寫 records；不得補任何預設欄位。

**Task 1.2 — 搜尋頁「直接匯入」出口**
- 檔案：`frontend/src/app/search/page.tsx`（在既有 `withExportDeclarationGuard` 之 `proceed` 內新增出口）。
- 驗證：`vitest run src/app/search/search2eventWiring.test.tsx` rc=0，且含一條斷言「直接匯入送出之 `records` 與下載路徑之 `payload.records` **逐鍵相等**」（`toEqual`，非形狀比對）。
- 邊界：① 零筆結果 ⇒ 不發請求 ② 宣告未通過 ⇒ 不發請求（沿用守衛）③ 只有一段條件 ⇒ 沿用既有阻擋。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`GLOBALH` 不改本頁。
- 不可做：不得另寫第二份條件判斷；不得把出口移出 `proceed`。

**Task 1.3 — 成功／失敗之畫面揭露（C-4）**
- 檔案：同 Task 1.2。
- 驗證（v2 補足；`CODEX-R56-P1-05`：v1 只驗 `import_id` 與 `kind`，其餘三項可被吞掉仍綠）：同檔測試四條——① 成功 ⇒ 畫面文字含後端 `import_id` 字面 ② 成功 ⇒ 含後端回傳之 **canonical `n_rows`** 字面（v3；`CODEX-R57-P2-05`：「或等價欄」會讓畫面顯示別的數字仍綠 ⇒ 欄名寫死）③ 成功 ⇒ 存在連結且其 `href` **逐字等於** `/data-preparation`，且**同一區塊之文字含該 `import_id` 字面**
  （🔴 **v4 更正（`CODEX-R58-P1-01` ≡ `COMPOSER-R58-P1-02`，兩家撞題）**：v3 寫死之 `/case/events/{import_id}`
  是**後端 API 路徑**（實際為 `/api/v1/case/events/{id}`），前端無該頁、rewrite 亦只接 `/api/v1/:path*`
  ⇒ 照做會把 C-4 之「前往該批」鎖成 404。實查前端路由：列出已匯入事件批者為
  `frontend/src/app/data-preparation/page.tsx`（`listEventImports()`、`eventImports.map` 以 `import_id` 為 key），
  且該頁**不讀 query param**（無 `useSearchParams`）⇒ **不得**寫死任何 `?import_id=` 之查詢字串，
  否則又是一個「寫死一個不存在的東西」。批次之定位改以畫面文字顯示 `import_id` 達成。
  **本條之出生事故**：v3 是為了修「只驗含 import_id 太寬」而寫死路徑，結果**錯得更具體**——
  收窄斷言時必須先查該值是否真的存在。） ④ 4xx ⇒ 畫面同時含後端 `kind` 與 `message` 兩者之字面。
- 邊界：① 後端未給 `kind` ⇒ 顯示原始 message 而非空白 ② **重複匯入**：連按兩次一鍵 ⇒ 得到**兩個不同** `import_id`（現行 `import_records` 每次新批、無內容去重，`api/services/case_import_service.py:1342`）；本票**不改**該行為，測試只釘住「兩次＝兩批」以防實作者自行發明後端去重（`COMPOSER-R56-P2-02`）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得把後端錯誤吞成通用文案。

### Phase 2 — 機械閘與回歸（依賴：Phase 1）

**Task 2.1 — C-1 四條之機械測試**
- 檔案：`frontend/src/app/search/search2eventScopeLock.test.tsx`（新）。
- 驗證：**十三條** mutation 逐條實跑並貼 rc=1——① 一鍵路徑改為自組 records ② 出口移出 `proceed` ③ `FormData` 加第四欄 ③′ **v7 拆為獨立一條（`COMPOSER-R61-P1-01`：以「或」並列時實作者可只做前者）**：record 之**巢狀**欄位（例 `label_definition` 內）加一個契約未列之鍵④ 刪除 `lookahead_declaration` 欄（C-1-4）⑤ **`file` 之檔名改為非 `.json`**（v3 (i)；現況後端會走 CSV 分支並回空列表而非拒收）⑥ **envelope 改為 `{records:[…]}` 物件**（v3 (ii)）⑦ **envelope 夾帶 `label_rule` 鍵**（v3 (ii)，現況會經 `_envelope_label_rule` 送進 `import_records`）⑧ **v4：`lookahead_declaration` 改送內容不同但形狀合法之宣告**（例：把 `acknowledged_unverifiable` 由 true 改 false、或把 `declared_window_bars` 換成 preview 預設值；現況後端以表單值為準並改寫落檔深度）⑨ **v4：`source_file` 以字串而非 `File` part 送出**（`CODEX-R58-P1-02`）⑩ **v5：`source_file` 保留合法檔名與型別但內容換掉**（`CODEX-R59-P1-01`）⑪ **v5：宣告 payload 以單參呼叫而得 `null`、且仍被送出**（`CODEX-R59-P1-02`）⑫ **v7：`skipped` 非空時未顯示、未取得確認即送出**（C-1-5）⑬ **v7：deep-equal 改為比對 adapter 手上之同一物件參考**（`COMPOSER-R61-P1-01`：就地改寫時恆綠）；**十三者**皆須轉紅（rc=1）。
- 邊界：① 契約欄位集合改變時，鍵集斷言須自 `event_import_contract.json` 讀取而非手打字面 ② 調低答案窗且未勾選之 records ⇒ 須能重現 `lookahead_declaration_unacknowledged_lowering`（C-1-4 之判準）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`ICPATH` 若新增契約欄，本測試之鍵集來源自契約 ⇒ 自動跟隨。
- 不可做：不得以 grep 原始碼形狀代替執行期斷言。

**Task 2.2 — 下載路徑位元組不變回歸**
- 檔案：`frontend/src/app/search/exportBytesUnchanged.test.tsx`（新）。
- 驗證（v2 補可重現性；`CODEX-R56-P1-06`：v1 只說「凍結值」而未給值、來源與產生方式 ⇒ 可先改序列化再把新輸出當凍結值，rc=0 照樣過）：
  - 🔴 **v7（`CODEX-R61-P2-01`）**：fixture 之 `CaseData` 與其 `source_file_text`／`source_file_digest`
    **必須取自同一次後端 `/search` 結果**（同源 canonical），不得分別拼湊——現行 `requireBackendSource`
    只檢查文字型別與 digest 之 64 位十六進位**形狀**，拼湊而成之 fixture 仍可通過形狀檢查而語意不一致。
    產生方式（含來源之 task_id）寫入 sha 檔首註解。
  - **固定輸入**落為 fixture 檔 `frontend/src/app/search/__fixtures__/search2event_cases.json`（自真實搜尋結果擷取後去識別化之 `CaseData` 陣列；**不得**於測試內以程式產生）。
  - 🔴 **v3：凍結必須在固定時鐘下產生**（`CODEX-R57-P1-03`）——`buildEventContractRecords`
    以 `new Date().toISOString().slice(0,10)`（`eventExport.ts:481`）把**當日日期**寫入每筆 record 之
    `data_snapshot_digest`（`:545`）⇒ 跨 UTC 日重跑同一 fixture 與同一 opts 會得到不同 bytes，
    v2 之「凍結 sha」本身不穩定、下一個 UTC 日就會無故變紅。
    **修法採提出方方案**：產生命令與測試**同在固定時鐘下執行**（`vi.setSystemTime` 固定為寫死之 UTC 日期，
    該日期字面寫在 sha 檔首註解），凍結的是**真實輸出 bytes**、不做任何欄位置換。
    🔴 **不採「比對前正規化該欄」**（主委 v3 初稿之方案）：那會讓 baseline 對「該欄的產生方式被改壞」失去偵測力，
    比固定時鐘弱。另於 sha 檔首註解列出**時鐘衍生欄之封閉清單**（現為 `data_snapshot_digest` 一欄），
    新增時鐘衍生欄而未列入即為缺陷。
  - **凍結值**落為 `frontend/src/app/search/__fixtures__/search2event_export.sha256`
    （內容＝**真實輸出** `JSON.stringify(payload, null, 2)` 之 sha256；產生命令、寫死之 UTC 日期、
    時鐘衍生欄清單三者寫在該檔首行註解）。
    🔴 **v4 更正（`COMPOSER-R58-P1-01`）**：v3 在此仍留著「正規化後」與「非正規化欄」之字面，
    與同段已裁定之「不採正規化、凍結真實 bytes」**自相矛盾**——實作者可照殘留字面把
    `data_snapshot_digest` 列入正規化欄，使固定時鐘失去偵測力。**全部改為真實 bytes，無任何欄位置換。**
    這是「改了理由段卻沒改被它取代的那一行」之同型（本專案已記多次），由主委在同一輪內製造。
  - 🔴 **固定時鐘之寫法亦寫死**：`vi.setSystemTime(new Date('<YYYY-MM-DD>T00:00:00.000Z'))`，
    **必須帶 `Z`**（UTC instant）。以本地午夜設定會在非 UTC 時區跨日，等於沒固定（同上 finding）。
  - 測試比對兩者相等 rc=0；mutation＝改動 payload **任一欄**（含 `data_snapshot_digest` 之產生方式）⇒ rc=1。
  - 🔴 **重凍紀律與其誠實邊界**（`CODEX-R57-P1-04`）：凍結值之變更須**同 commit** 附理由，且須同時改到序列化相關碼；
    **只改 sha 不改碼**之 commit 視為缺陷。
    **但此半靠審碼輪人工對證，非機械不可繞**——同一 commit 可同時換掉 `search2event_cases.json`、
    重算 sha 並夾帶表面相關之改動，測試仍 rc=0。⇒ 登記為具名殘留（見 §N），理由類別 `user-ruling`
    （倉內無獨立信任根；同型已由 `SU-RESID-V8-ATTEST` 裁定為不再擴建治理工具、降級具名殘留）。
    可機械化的那半**已做**：fixture 本身之 sha256 亦寫入同一註解，換 fixture 必留痕。
- 邊界：① 輸入含缺 horizon 之列 ② 兩段條件 ③ 一段條件（反例未啟用）⇒ 既有阻擋仍生效。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`B` 之 multipart 組裝不改 `buildEventContractRecords` 之輸出（C-1-1），故本凍結值不受 wire 決策影響；若日後有票改該產生器，須同 commit 重凍。
- 不可做：不得為了讓測試過而放寬凍結值；不得以程式即時產生 fixture。

## §V 驗證策略與邊界測試目錄

每個 Task 之五個必填欄已於 §P 逐 Task 列出（各含可執行命令與 rc）；本節只定策略與邊界目錄，不重抄。

- **可證偽性**：C-1 四條各配一條 mutation（逐條見 Task 2.1），皆須轉紅（rc=1）。
- **邊界目錄**：① 零筆搜尋結果 ② 宣告未通過 ③ 匯入端回 4xx ④ **重複匯入**：兩次一鍵 ⇒ 兩個不同 `import_id`（現行行為，本票不改、不得自行加去重）⑤ 只有一段條件（反例未啟用）之既有阻擋仍生效 ⑥ 調低答案窗且未勾選 ⇒ 匯入端具名拒收。
- **禁**：以原始碼形狀（grep 到函式名）證明執行期性質；一律斷言實際送出之 body 與實際渲染之畫面。

## §R 回退

移除新增之 client 函式與該出口按鈕即回到現狀；下載路徑與後端皆未改動，故回退不需資料遷移、不影響既有事件批。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）

- **具名殘留 `S2E-RESID-FIXTURE-ATTEST`**（v3 新增；`CODEX-R57-P1-04`）：Task 2.2 之「不得先改序列化再重凍」
  只有**審碼輪人工對證**這一層，非機械不可繞——同一 commit 可同時換 fixture、重算 sha 並夾帶改動而測試仍 rc=0。
  **為何現在不做**：`user-ruling:2026-09-12 使用者裁定「不再擴建治理工具；同型缺陷降級為具名殘留」`；
  倉內無獨立信任根，要擋需受保護簽章或不可變 attestation，同型已由 `SU-RESID-V8-ATTEST` 裁定。
  **已做到的那半**：fixture 自身之 sha256 寫入凍結檔首註解，換 fixture 必留痕。
  **觸發條件（可執行）**：專案導入 commit 簽章或受保護分支（`git config --get commit.gpgsign` 為 true，或 repo 有 branch protection）。
  **owner**：SEARCH2EVENT 票主委。
- **§G Golden / Baseline＝N/A**。理由：本票不新增、不改動任何數值或統計量；payload 產生器（`buildEventContractRecords`）
  與後端匯入端皆逐字不動（C-1／C-2），故無「改前後數值比對」之對象。**誠實邊界**：若委員裁定選項 `B`
  （改走檔案端點）而該路徑之 multipart 組裝會改變送出位元組，則須回頭把「送出位元組」列入 §G 並補基準。
