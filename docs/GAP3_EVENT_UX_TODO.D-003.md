# GAP3_EVENT_UX_TODO — D 延伸 003（B4／B5 實作期之修訂）

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
- **定案**：reader 一律帶 `index_col=False` 並把 `ParserWarning` 升為例外 ⇒ 長列拒收（`parse_error`）。
  🔴 `on_bad_lines="error"` **無效**（實測仍左移），不得改用它。
- **誠實邊界**：欄數**比標頭少**之列，pandas 靜默補空字串且無任何 signal，reader 擋不住；
  那些空值由契約層逐欄拒（落檔仍為 0），前端則於預覽階段直接擋送出。

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

## 修訂索引

| 編號 | 標的 | 一句話 | 日期 |
|---|---|---|---|
| **A-016** | Task 1.6 provenance | 欄位定案為七欄；三個新增欄皆為「不揭露就會讀成別的意思」；批內單一 digest ⇒ fail-closed | 2026-08-25 |
| **A-016b** | Task 1.5 `derive_event_id` | 只顯示期望值不算解除 `R-B2-1`；改為後端 opt-in 產生 ID，判準＝送出後後端接受 | 2026-08-25 |
| **A-016c** | Task 1.2 reader | 欄數不齊之 CSV 一律拒收；`index_col=False` ＋ ParserWarning 升例外（`on_bad_lines` 無效） | 2026-08-25 |
| **A-017** | Task 1.3 修改檔案行 | `api/routes/case.py` 字面作廢，實際在 `case_search.py` | 2026-08-25 |
| **A-018** | Task 2.2 修改檔案行 | 後端序列化函式字面作廢，實際在 `frontend/src/lib/eventExport.ts` | 2026-08-25 |

## 戳記

（委員於此 append；格式：
`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`）
