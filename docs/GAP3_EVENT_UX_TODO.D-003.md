# GAP3_EVENT_UX_TODO — D 延伸 003（B4／B5 實作期之修訂）

> ## 🔴 本檔已因 R 重開而失效（SUPERSEDED-BY-R，2026-09-02）
>
> **失效依據**：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1（R ⇒ 所有延伸檔失效；安全閥①全量作廢）。
> 觸發：`docs/GAP3_EVENT_UX_SPEC.md` R35-R（§D **D-8**）。
> **處置**：A-016／A-017／A-019 **併回本體**（Task 1.6／1.3）；**A-018 自然關閉（Task 2.2 退役）**。
> 本檔不得再作為任何派工之授權來源。

BASE: docs/GAP3_EVENT_UX_TODO.md @ afa70967
PREDECESSOR: docs/GAP3_EVENT_UX_TODO.D-002.md

改什麼: 三條——A-016 定案 Task 1.6 之 `mapping_provenance` 欄位集合與批內單一 digest invariant；
A-017 更正 Task 1.3「修改檔案」行之 `api/routes/case.py` 字面（B2 R1 已判 doc drift）；
A-018 更正 Task 2.2「修改檔案」行之後端序列化函式字面（實際落點在前端 `eventExport.ts`）。
為什麼: A-016 為 B4 實作**新增**之約束，FROZEN TODO 未宣告，不寫下就會有人以為那是 SPEC 要求
（B4 R1 `CODEX-R1-P2-03`）；A-017／A-018 為凍結文件與 repo 實況不符之 doc drift，
凍結後不就地改、一律走延伸檔。
檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約）。

## 觸及面宣告

新增: Task 1.6 之 `mapping_provenance` 欄位集合（七欄）與其 fail-closed 條件
覆寫: Task 1.3「修改檔案」行之 `api/routes/case.py` 字面；Task 2.2「修改檔案」行之
`api/services/case_import_service.py::EventImportService` 之 `label_definition` 序列化函式字面
依賴: docs/GAP3_EVENT_UX_TODO.D-001.md、docs/GAP3_EVENT_UX_TODO.D-002.md

## 內容

### A-016 — Task 1.6 之 `mapping_provenance` 欄位定案（七欄）與批內單一 digest invariant

- **TODO／SPEC 原文**（Task 1.6）：輸入為四項——`column_mapping`、來源檔名、`source_file_digest`、確認時間；
  「不可做：不得省略 `source_file_digest`（否則無法對證來源）」。
- **實作落地為七欄**（`momentum/Analysis/contracts/event_import_contract.json`
  之 `receipt_schema.mapping_provenance`）：
  `column_mapping` / `source_file_name` / `source_file_digest` /
  **`source_digest_verified`** / **`event_id_source`** / `confirmed_at` / **`confirmed_at_source`**。
- **三個新增欄各自的理由（皆為「不揭露就會讀成別的意思」）**：
  1. `source_digest_verified`：未附 companion 來源檔時，`source_file_digest` 只證明使用者**填了**
     同一串 64-hex，**不證明**它對應任何檔案。少了本欄，receipt 讀起來像已對證（B4 R1
     `CODEX-R1-P1-02` 判 BLOCKING）。
  2. `event_id_source`：`event_id` 可能是使用者 CSV 欄，也可能由後端依契約模板產生
     （見下 A-016b）。兩者之可追程度不同，必須分得出來。
  3. `confirmed_at_source`：客戶端未宣告確認時間時記伺服器落檔時間；不揭露就是**伺服器時間
     冒充使用者確認時間**。
- **`confirmed_at` 之地位**：格式須為 UTC ISO-8601（`…Z`），不合即拒；但本欄是**使用者聲明之時刻**、
  **非可信時鐘**（客戶端可偽造）。時間權威一律以 receipt 之 `imported_at` 為準。
- **批內單一 digest invariant（本延伸檔之新增約束）**：對映路徑落檔時，本批各列宣告之
  `source_file_digest` 須解析出**單一值**；批內不一致或缺 ⇒ 視為缺值，由
  `validate_receipt_namespace` 以契約之「缺必填欄」reason fail-closed，**落檔數 0**。
  理由：provenance 要回答的是「這批是依**哪個檔**宣告的」，兩個不同 digest 等於沒有答案。
  **代價已知**：合法之「多來源檔合併批」在對映路徑上會被擋，解法是拆批或走 JSON 直傳。
- **JSON 直傳路徑不寫本 namespace**：該路徑沒有欄名對映可追，寫了也只有空殼。

#### A-016b — Task 1.5 之 `derive_event_id`（opt-in）與殘留 `R-B2-1` 之解除判準

- **殘留原文**（B2 R2 reconcile）：「前端對映 UI 應在單位偵測後**預填正規化 ID**」。
- **B4 R1 裁定**：只把期望值**顯示**出來不算預填（`CODEX-R1-P1-01` 判 BLOCKING、
  `GROK-R1-P2-02` 判部分解除）。
- **定案**：CSV 對映端點新增 `derive_event_id` 表單旗標，**預設 `false`**（不推斷＝A-4′）；
  為 `true` 時由後端在 **t0 單位正規化之後**、以契約 `event_id_template` 之唯一實作
  `canonical_event_id()` 逐列產生 `event_id`，並於 provenance 記 `event_id_source`。
  **不改上傳位元組**——改寫上傳檔會讓 `upload_sha256` 與 Task 1.6 之來源 provenance
  指向前端重寫過的檔。
- **解除判準**：秒級 t0 之 CSV 在 `derive_event_id=true` 時**後端接受且落檔 ID 為毫秒版**
  （斷言送出結果，不是斷言畫面文字）。

#### A-016c — CSV 對映路徑之欄數不齊一律 fail-closed

- **背景**：`pd.read_csv` 在「**每一列**都比標頭多一格」時會把首欄當 index、**整列左移且零 warning**
  ——`label` 讀到的是隔壁欄的值。B4 R1 三家各自實跑重現（`GROK-R1-P1-01`／
  `COMPOSER-R1-P1-01`／`CODEX-R1-P2-05`）。
- **定案（R2 修訂後）**：**主要守衛＝以 `csv` 標準庫獨立驗列寬**
  （`EventImportService._assert_uniform_row_widths()`）：規則只有一條——
  **每一資料列之欄數 == 標頭欄數**，長列短列同一條，與 pandas 版本無關；不符即 `parse_error` 拒收。
  前端 `csvPreview.parseCsvText()` 之 `raggedRows` 用**同一條規則**，兩端因此不會出現
  「畫面擋了後端收」或反過來的落差。
- **為何不能只靠 pandas**（R2 `CODEX-R2-P1-02` 實測）：pandas 對同源異常有**三種**行為——
  每列多一格非空 ⇒ 靜默左移（加 `index_col=False` 後改為 `ParserWarning`）；
  每列多一格**空的** ⇒ 完全靜默吞掉；只有某一列多 ⇒ `ParserError`。
  三種行為且依版本而異 ⇒ 不能當規則來源。
- **後備層保留**：reader 仍帶 `index_col=False` ＋ `ParserWarning` 升例外，
  以防 `csv` 標準庫與 pandas 對某引號形態 tokenize 不同時退回靜默左移。
  🔴 `on_bad_lines="error"` **無效**（實測仍左移），不得改用它。
- **空行之定義（R3 三家共提之修訂）**：一行**只有空白字元或完全沒有字元**時跳過
  （`csv.reader` 對前者回 `[' ']`、對後者回 `[]`，**兩種都要跳**；實測 pandas 兩種都跳）。
  🔴 但 `,,`（欄數正確、值全空）**不是**空行——`csv.reader` 回 `['', '']`、pandas 保留為一列空值
  ⇒ 不得跳過，否則會把真實資料列吃掉。兩側邊界各有 mutation（`1.2-M7`／`1.2-M8`）。
- 🔴 **誠實邊界（R3 `CODEX-R3-P2-02` 之降級）**：後備層**沒有專屬 mutation**——主要守衛會先攔下
  同一批輸入，任何只拆後備層的變異都錄不到紅（空紅集合）。`1.2-M5`／`1.2-M6` 之紅集合差
  **只證明「主要守衛被拆掉時後備層仍攔得住長列」**，**不證明**後備層在 production 可達
  （那需要一個「`csv` 標準庫與 pandas tokenize 不同」之實例，本專案目前**沒有**已知案例）。
  receipt 之結論以此為準，不得讀成「後備層已被證明有用」。

### A-017 — Task 1.3「修改檔案」行之 `api/routes/case.py` 字面

- **TODO 原文**（Task 1.3 修改檔案行）：`api/routes/case.py`。
- **實況**：Task 1.3 之承載點採 SPEC 之「既有匯出流程服務端入口」＝`api/routes/case_search.py`
  （`get_task_result` ＋ `_attach_canonical_source()`），因 `api/routes/case.py` 之 `@router`
  無一持有 `cases`。B2 R1 已判為 doc drift 並具名回報。
- **裁定**：以 repo 實況為準；TODO 該字面作廢。

### A-018 — Task 2.2「修改檔案」行之後端序列化函式字面

- **TODO 原文**（Task 2.2 修改檔案行）：🔴 **定案**＝`api/services/case_import_service.py::EventImportService`
  之 `label_definition` 序列化函式。
- **實況**：`label_definition` 是在**前端**組的——`frontend/src/lib/eventExport.ts`
  之 `buildEventContractRecords()`（`label_definition: {...}`）。後端只驗證與落檔，不組該物件。
- **裁定**：Task 2.2 之落點為 `frontend/src/lib/eventExport.ts`；TODO 該字面作廢。
  **不變的部分**：序列化規則一律引用 §G S-1..S-9（本 Task 不自訂），
  且**不得**把篩選條件納入 `event_id` 之輸入（D-2）。

### A-019 — 🔴 SPEC Task 1.3 對 `source_file_digest` 之單位敘述**自相矛盾**，以可實作之讀法為準

- **SPEC 原文**（L1427）：「`source_file_digest` ＝上傳 CSV 位元組之 `hashlib.sha256(raw).hexdigest()`。」
- **同一 Task 下段（L1428–1440）卻寫**：digest 綁 `/search` 之**完整 `CaseData` 列**之遞迴 canonical JSON
  （依 §G S-9 序列化）——那是**來源檔**（`/search` 匯出時一併下載之 `*.source.json`），
  不是使用者上傳的那個事件檔。
- **兩者互斥，且第一種讀法在數學上不可實作**：事件檔**自身含 `source_file_digest` 欄**，
  對自己取 sha256 恆不自洽。B2 之路由層已為此立了專屬 reason
  `source_file_must_differ_from_event_file`（`api/routes/case.py`）——**那條守衛的存在本身**
  就是「上傳檔 digest」讀法不可行的證據。
- **裁定**：以**可實作且已上線**之讀法為準——`source_file_digest` 綁**來源檔**位元組；
  上傳事件檔本身之 sha256 另存為 receipt 之 `upload_sha256`（既有欄，未改）。
  L1427 之字面判為 **doc drift**，比照 D-002 `A-005`（SPEC 對 producer 之敘述與實況不符者以實況為準）。
- **B4 未改變任何語意**：本批只是把該值**記進** `mapping_provenance`，並新增
  `source_digest_verified` 揭露它有沒有被位元組對證過。指出此矛盾者＝R2 `CODEX-R2-P1-01`。
- **殘留**：SPEC 本身之字面未改（凍結文件不就地改）；日後若有人只讀 L1427 仍會誤解，
  故本條為**必讀之並讀項**。三值理由 `user-ruling`（凍結後修訂一律走延伸檔）。

## 修訂索引

| 編號 | 標的 | 一句話 | 日期 |
|---|---|---|---|
| **A-016** | Task 1.6 provenance | 欄位定案為七欄；三個新增欄皆為「不揭露就會讀成別的意思」；批內單一 digest ⇒ fail-closed | 2026-08-25 |
| **A-016b** | Task 1.5 `derive_event_id` | 只顯示期望值不算解除 `R-B2-1`；改為後端 opt-in 產生 ID，判準＝送出後後端接受 | 2026-08-25 |
| **A-016c** | Task 1.2 reader | 欄數不齊之 CSV 一律拒收；主要守衛＝`csv` 標準庫獨立驗列寬（長短同一條、與 pandas 版本無關），reader 參數降為後備 | 2026-08-25 |
| **A-019** | Task 1.3 digest 語意 | 🔴 SPEC L1427「上傳 CSV 位元組」與同 Task 下段「綁 /search 完整 CaseData」互斥且前者不可實作（事件檔含自身 digest）；以來源檔讀法為準，L1427 判 doc drift | 2026-08-26 |
| **A-017** | Task 1.3 修改檔案行 | `api/routes/case.py` 字面作廢，實際在 `case_search.py` | 2026-08-25 |
| **A-018** | Task 2.2 修改檔案行 | 後端序列化函式字面作廢，實際在 `frontend/src/lib/eventExport.ts` | 2026-08-25 |

## 戳記

（委員於此 append；格式：
`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`）

RECONCILE-STAMP: grok APPROVED 2026-08-28 sha256:18abd9ad505ddec674d73998d9b8f3b23a0c3bc4a8ad3aaa0a1e3ad1e3ac5775 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-003

RECONCILE-STAMP: composer APPROVED 2026-08-28 sha256:18abd9ad505ddec674d73998d9b8f3b23a0c3bc4a8ad3aaa0a1e3ad1e3ac5775 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-003
RECONCILE-STAMP: codex APPROVED 2026-08-28 sha256:18abd9ad505ddec674d73998d9b8f3b23a0c3bc4a8ad3aaa0a1e3ad1e3ac5775 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-003
