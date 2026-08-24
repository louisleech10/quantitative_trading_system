# GAP-3 事件型 UAT 缺口修補 TODO（v0.1 DRAFT｜基於 `docs/GAP3_EVENT_UX_SPEC.md` **FROZEN 2026-08-24**｜生成日 2026-08-24）

> ⚠️ **DRAFT — 未過 adversarial review，不得據以派工。**
> 生成依據：`templates/TODO_GENERATION_PROMPT.md` V13；
> 階段 1 索引＝`handoffs/20260824-gap3ux-todo-stage1-index.md`
> （追溯基準：**Phase 7／Task 42／§V 驗證項 20／§G Golden 3／§A 假設 4**）。
> 歸屬票：全部 Task＝`docs/IC_QUANT_GAP_REGISTRY.md` **#3（GAP-3）**；各 Task 標題之 `票 #3-<子項>`
> 指該 Task 對應之 SPEC Phase 標頭所列子票（如 Phase 1 標頭之【#0(b) ＋ #5】）。

## 層級宣告（W1）

- **操作依據＝本檔**：執行端逐 Task 寫碼以本檔為準，不必回讀 SPEC 即可開工。
- **語意權威＝`docs/GAP3_EVENT_UX_SPEC.md`（FROZEN）**：本檔與 SPEC 衝突時**以 SPEC 為準並回報**，
  執行端不得自行取捨。
- 🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**（SPEC 行號逐 Task 標註，如 `SPEC ref：L1282`）。本檔於每 Task 之「驗證」列出
  **可執行命令與條目下限**，並指向 SPEC 行號；**不重抄斷言字面**——
  重抄即第二份副本，而本 epic 三十四輪之自傷絕大多數出自「副本與本體漂移」。
- **欄位／枚舉／reason 字面 SoT＝`momentum/Analysis/contracts/event_import_contract.json`**；
  §G S-9 序列化規則 SoT＝SPEC §G。本檔與程式**禁複列鍵表**。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 0.1 解耦（憲法 7 條；SPEC §C 引用）
1. **R1**：`momentum/` 不得 `import api.*`。新邏輯放 `momentum/Analysis/event_samples/`；
   範例：`from momentum.Analysis.event_samples.alignment import align_events` 合法，
   在 `momentum/` 內寫 `from api.models import …` ＝違規。
2. **R3**：`api/services/` 取用 core 能力一律經 `momentum/factories.py` 之 `create_*`。
3. **R4**：`api/services/` 之間**不得**互相 import。
4. **R5**：設定單一來源——運行參數入 `momentum/core/config.py` 或函式參數 dataclass；
   **門檻／枚舉／reason 字面唯一住契約檔**，禁散落模組級常數。
5. **R6**：`pytest tests/momentum/` 須可獨立跑（不啟 `run_api.py`）。
6. **R7**：DTO 不跨界——事件契約 dataclass 住 `momentum/Analysis/event_samples/types.py`，
   `api/models/` 只做 request/response 殼。

### 0.2 不可違反原則（§C0，最高位階）
- **量化正確性只能更嚴、不得放水**；「95% 就收」不適用量化路徑。
- 資料正確性類缺口**不得**降級為具名殘留放行。
- 不得弱化既有 NaN／inf 閘；不得未經核准改變輸出大小。
- 涉對齊／特徵取列／全 K 線驗證 ⇒ **必用真實 kline**（`data_cache/feature_klines/kline_cache.h5`）
  （`tests/golden/la0/inputs/` 既有 fixture 或 `data_cache/feature_klines/kline_cache.h5`）；
  統計 oracle 可用合成**因子／label／事件序列**，**禁合成價格**。

### 0.3 防假綠（本 epic 三十四輪最大宗自傷）
- **不得放寬既有測試斷言**；每批收尾須 diff 既有斷言。
- 🔴 **V-M（可證偽性）為全批適用之驗證項**（SPEC §V L3446）：每 Task 之 mutation 須**逐條**列出
  ——mutation 內容／命令／預期紅／**實際 receipt 路徑**，四者缺一不可；
  **不得只寫「逐條紅」**。還原後須全綠。本項於每 Task「驗證」欄以 mutation 條數（`>= 1`）體現。
- 「未登記／未涵蓋 ⇒ 紅」屬 **fail-closed 之預期行為**，
  **不得以放寬 validator 或加白名單消紅**。
- 契約增量一律以**對凍結 fixture 之差集**表述，**禁寫計數字面**
  （SPEC R6／R7 各有三條自傷出自計數字面與其所計之物不同步）。

### 0.35 Golden／Baseline（§G）之全批義務
- 🔴 **G-1 IC 主線未被波及**：**每個 Phase Gate 皆須**跑
  `python3 scripts/gap3_freeze_golden.py --check` 並維持通過
  ——本批不得波及既有 IC 主線；該檢查轉紅即**停批查明**，不得重凍。
- **G-2 事件路徑專屬 golden**：固定 fixture（真實 kline 切片）＋固定 horizons。
  其**任何改變**須依 **D-4** 於 commit message 說明，並以 **§G S-9 參考實作**重算、
  以 **§G S-8 之獨立 oracle** 驗證（**不得以被測函式自產**）。落點＝Task 4.2／7.1／7.5。
- **G-3 analysis-label golden**：分析層 producer 之 golden（含逐列 purge、receipt hash、
  混 TF 覆蓋面）。落點＝Task 7.0b。

### 0.4 風險命中（§RISK）
**RISK-HIT: a,b**——(a) 數值/資料品質（`label` 語意不可機械證明，見 D-1）；
(b) 跨模組（`api/routes/case.py`／`frontend/src/`／`momentum/Analysis/event_samples/` 三層）。
**非 (c)**（各 Phase 獨立 commit 可逐一 revert）、**非 (d)**（不動回測與 ML 正確性路徑）。

### 0.5 Logging 與錯誤分類
`get_logger(__name__)`；hot loop 不 log。
Retryable：rate_limit／timeout；Non-retryable：invalid_symbol／logic／data format
（本批之匯入拒收一律 Non-retryable，走契約 `import_failure_reasons`）。

---

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1 契約與深度根基** | 1.1、1.10 | 無 | 兩者皆為**唯讀增量之根**：1.1 定 reason／derived 欄／typed receipt schema，1.10 定 lookahead registry。後續每個 Phase 都讀它們；先落地才能讓其餘 Task 的 fail-closed 有依據 | 中 |
| **B2 CSV 匯入主線** | 1.2、1.3、1.4、1.8 | B1 | 同一端點之解析鏈（收檔→digest→單位→異質列），共用同一 schema 檢核函式；拆開會讓 V-3 之共用性 oracle 無法一次驗 | 中 |
| **B3 深度三層防線** | 1.11、1.12、1.9 | B1、B2 | L2（強制宣告）→L3（禁進切分）→L2 之 UI（答案窗宣告）為同一條 D-7 防線，且 1.9 明文依賴 1.10／1.11 | 大 |
| **B4 匯入前端** | 1.5、1.6、1.7 | B2 | 同一頁面之上傳／預覽／對映／provenance／可疑欄警示，共用同一 React 元件樹 | 中 |
| **B5 匯出前篩選** | Phase 2 全部 | B1 | 見 Part 2 | — |
| **B6 刪除** | Phase 3 全部 | 無 | 見 Part 2 | — |
| **B7 匯出端報酬欄** | Phase 4 全部 | B1 | 見 Part 2 | — |
| **B8 訊息與表頭** | Phase 5 全部 | Task 5.0（同批內最先做） | 見 Part 2 | — |
| **B9 IC 止血閘** | Phase 6 全部 | Task 6.0（同批內最先做） | 見 Part 2 | — |
| **B10 全棧接線** | Phase 7 全部 | B1–B9 | 見 Part 2；🔴 **批內強制順序**：`7.0 → 7.1 → 7.2`；且 **7.6 之 formatter registry 須先於 7.3**（7.3 只選取自己的欄集，registry 由 7.6 定義）；`4.2 → 7.5`（同一表格）；`4.1b → 7.3`（後者取代前者，取代前須逐項比對 4.1b ⊆ 7.3） | — |

🔴 **批次間 Gate**：下一批開工前，上一批之**全部 mutation 須實跑轉紅並還原轉綠**，
receipt 路徑入 commit message。未附 receipt ⇒ 不得開下一批。

---

## Phase 1 — 使用者自篩 CSV 匯入（依賴：無）

**目標**：使用者可上傳自己篩好的 CSV 事件檔，系統以 fail-closed 方式收檔、
綁定 provenance、並在「答案窗深度不可證」時擋住切分。
**完成後系統狀態**：`POST /api/v1/case/import-events/csv` 可用；
契約已登記本批全部新 reason 與兩個 derived／batch 欄；D-7 三層防線可運作。

### Task 1.1 — 契約先行：新增 reason 與 label_definition.filters（`票 #3-0(b)`）

- **SPEC ref**：L1282–1413　**目標**：把本批需要的 reason、`filters` 欄、
  `lookahead_bars_declared`／`analysis_alignment_receipt_hash` 一次登記進契約，並把
  `receipt_schema` 由「欄名清單」升為 **namespace-aware 之 `{欄名: 型別}`**。
- **輸入**：`momentum/Analysis/contracts/event_import_contract.json`（改前）
  **輸出**：①同檔改後 ②凍結副本
  `tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json`（immutable）
- **實作要點**：
  1. 🔴 **第一個動作**（在動任何契約欄位**之前**）：位元組拷貝出 baseline fixture，
     跑 `cmp -s` 與 `shasum -a 256`，三條輸出入 commit message。
     先改再拷、或產生 sanitized／重排版之副本 ⇒ 差集失去改前語意，屬違規。
  2. `import_failure_reasons` 增四值（字面見 SPEC L1284–1285）；
     🔴 `label_producer_unsupported_for_declared_semantics` **不進**本清單，
     改進 `capability_unavailable_reasons`（§F-2′；放錯清單會讓前端在錯的生命週期顯示它）。
  3. `receipt_schema` migration（**namespace-aware，不攤平**）：
     ```python
     receipt_schema = {
       "event_level": {<既有欄名>: <型別>, ...},   # 欄名與順序照抄，只補型別
       "per_tf":      {<既有欄名>: <型別>, ...},
       "batch": {                                   # R11 新增之第三個 namespace
         "lookahead_bars_declared": "Mapping[str,int>=0]",
         "analysis_alignment_receipt_hash": "str",
       },
     }
     ```
     兩個新欄**一律放 `batch`**（批次層屬性，非逐列／逐 TF）。
  4. 新增**單一** exported traversal：
     `def flatten_receipt_schema(schema: Mapping) -> list[str]`
     ——回傳 `["<namespace>.<欄名>", ...]`（保序）。
     🔴 **runtime validator 與驗收共用同一函式參考**，不得各寫一份。
  5. 型別判定：`lookahead_bars_declared` 之值一律 `type(v) is int`（**不用 `isinstance`**，
     因 `bool ⊂ int`，`True` 會通過卻序列化成 `true`）。
- **修改檔案**（精確到函式名）：
  - `momentum/Analysis/contracts/event_import_contract.json`（資料）
  - `momentum/Analysis/event_samples/import_contract.py`：
    `load_event_import_contract()`（搜尋路徑**不得含 `tests/`**）、
    `validate_event_import()`（接上新型別判定）、新增 `flatten_receipt_schema()`
  - 新增 fixture `tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json`
  - **既有 caller**：`api/services/case_import_service.py::EventImportService`（讀契約）、
    `api/routes/case.py::import_events_file/import_events_json`（經 service 間接）
- **不可做**：不得在 `api/` 或 `frontend/` 另寫一份 reason 清單；
  不得動既有 reason 之字面與順序；不得寫任何 reason **計數字面**。
- **邊界**：
  ① 既有 reason 順序被改動 ⇒ 驗收②須紅（不靠計數，靠 prefix 相等）。
  ② `lookahead_bars_declared` 傳 root scalar（如 `72`）⇒ 須 fail-closed，
     不得因「是個整數」而通過。
- **風險緩解**：RISK-(a)——型別登記與 runtime validator 共用同一 typed path，
  避免「登記了但沒生效」。
- **驗證**：`pytest tests/api -q -k gap3_contract_reason_registry` **≥8 條**
  （①–⑧，字面見 SPEC L1350–1401；⑧(c) 之五個反例含 `bool`）。
  **mutation 六條**（SPEC L1402–1407）逐條實跑轉紅、還原轉綠，receipt 入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——契約為唯讀增量；Phase 2 之 Task 2.2 只寫 `filters` 之值，
  Phase 6 之 Task 6.0 另建 IC 側 reason 檔而不併入本檔，Phase 7 動的是 `label_definition` 其他鍵。

### Task 1.2 — 新端點 `POST /api/v1/case/import-events/csv`（`票 #3-5`）

- **SPEC ref**：L1414–1422　**目標**：以 multipart 收 CSV，組出契約記錄後
  **呼叫與 `/import-events` 相同的 schema 檢核與落檔函式**。
- **輸入**：multipart（CSV bytes ＋ `column_mapping` ＋ `batch_defaults`）
  **輸出**：`EventImportResponse`（既有 model，簽章不變）
- **實作要點**：
  1. 新增 route handler `async def import_events_csv(...)`，緊鄰既有
     `import_events_file`／`import_events_json`。
  2. CSV → 契約記錄之組裝**只做欄位對映**；schema 檢核與落檔一律轉呼
     `EventImportService` 之**同一**方法（與 JSON 路徑同一函式物件）。
  3. 拒收一律經 `EventImportRejectedError` → `api/routes/case.py::_rejected()`。
- **修改檔案**：`api/routes/case.py`（新增 `import_events_csv`）；
  `api/services/case_import_service.py::EventImportService`（抽出共用檢核方法，若尚未共用）
  **既有 caller**：無（新端點）；前端 caller 於 Task 1.5 接上。
- **不可做**：不得為 CSV 路徑另寫一份 schema 檢核邏輯。
- **邊界**：① 只新增端點，**不改** `/import-events` 與 `/import-events/json` 之任何行為。
  ② CSV 標頭缺 `column_mapping` 指定之欄 ⇒ `column_not_found_in_file`，落檔數 `== 0`。
- **風險緩解**：RISK-(b)——共用性由 V-3 **兩重 oracle**（AST 靜態＋mutation 行為）機械對證，
  不靠 sha256 相等。
- **驗證**：`pytest tests/api -q -k gap3_csv_import` **≥8 條**全綠；
  共用性見 V-3（SPEC L3428）。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——Phase 4 疊加 horizon 欄，端點簽章不變。
### Task 1.3 — `event_id` 沿用既有 canonical（D-2）（`票 #3-5`）

- **SPEC ref**：L1424–1565　**目標**：`event_id` 與前端匯出**同一實作**；
  `source_file_digest` 綁**完整 `CaseData`** 之 canonical bytes，且**一律由後端計算**。
- **輸入**：上傳 CSV 之 raw bytes／`/search` 之 `cases` 列
  **輸出**：`event_id`（`${symbol}:${timeframe}:${t0}`）、`source_file_digest`、`source_file_text`
- **實作要點**：
  1. 抽出共用 `event_id` 定義來源，前後端各自呼叫；**不得發明新演算法**
     （R1 兩家獨立判為 BLOCKING）。前端現址 `frontend/src/lib/eventExport.ts:88`。
  2. `canonicalSourceText` 由五欄子集改為**每列完整 `CaseData` 之遞迴 canonical JSON**：
     保留所有 own keys 與值（含全部 `future_*` return／drawdown），
     只做固定 key ordering（§G S-2，UTF-8 升冪），**不改名、不篩欄、不省略**。
  3. 序列化**依 §G S-9**：`repr(float)` round-trip lexeme、NaN／±Inf → `null`、
     `-0.0` 保留、固定 separators、UTF-8 無 BOM。
     🔴 **只准 import S-9 之參考實作，禁在 TS 重寫**（S-9 第 7 條）。
  4. **不新增任何 route**：`/search` 匯出在送出前呼叫**既有匯出／檢核之同一服務端入口**取得
     digest，其回應**增兩鍵** `{source_file_digest: str, source_file_text: str}`
     （後者為 exact bytes 之 UTF-8 解碼，**無尾端 newline**）。
  5. 🔴 `rule_digest`（綁 `search_rule_summary`）與 `source_file_digest`（綁完整 `CaseData` 列）
     **為兩件事，須分離**——同一 helper 不得同時產出兩者而共用序列化路徑。
  6. **時序**：digest 於**匯出當下**由後端產生，與 `source_file_text` 一同回傳並寫進匯出檔；
     **匯入時不重算**，只比對（`verify_source_digest`）。
- **修改檔案**：
  - `frontend/src/lib/eventExport.ts`：`canonicalSourceText`（改為呼叫後端取得，不自算）
  - 既有匯出服務端入口（`api/routes/export.py` 或 case 匯出鏈之對應 handler）：回應增兩鍵
  - `momentum/Analysis/event_samples/import_contract.py`：新增 `verify_source_digest()`
  - S-9 參考實作模組（依 SPEC §G S-9 所指位置）
  - **既有 caller**：`frontend/src/app/search/page.tsx`（匯出按鈕鏈）
- **不可做**：🔴 **不得發明新的 `event_id` 演算法**；前端**不得**自行計算 `source_file_digest`；
  不得新增第二個 transport／route。
- **邊界**：
  ① 刪除／改名／改值任一 `future_*` 欄 ⇒ digest **必須改變**（三條各一測）。
  ② 含 `-0.0`／極大極小浮點之 fixture ⇒ 前端取得之 digest 與後端 S-9 參考實作**位元組相同**。
- **風險緩解**：RISK-(a)(b)——改名攻擊之證據面（Task 1.10 信任邊界）靠完整列 digest 閉合。
- **驗證**（`npx vitest run canonicalSourceCoverage` **≥3 條** ＋ 下列 ④(a)(b)(c)；🔴 本 Task 之 selector 為 `canonicalSourceCoverage`，**不得**與 Task 1.9 之 `gap3_horizon_declaration` 混用）：
  - `npx vitest run canonicalSourceCoverage` **≥3 條**（①②③，SPEC L1495–1497）
  - ④(a) **執行期**：vitest `setupFiles` 統一 stub 雜湊入口之**顯式枚舉**
    （`globalThis.crypto.subtle.digest`／`node:crypto` 之 `createHash`／`hash`／`Hash`／`webcrypto`），
    跑完整匯出流程後斷言與 `source_file_digest` 相關之呼叫數 `== 0`（`rule_digest` 另計）。
    另以 `await import('node:crypto')`（**禁 `require`**，vitest 為 jsdom＋ESM）斷言
    `Object.getOwnPropertyNames(m).sort()` **逐字等於** golden
    `tests/.../node_crypto_exports.golden.json`；golden 之 added／removed 須與
    `tests/.../node_crypto_review_manifest.json` **雙向封閉集合相等**（任一側多出即紅）。
    🔴 **不得自稱窮舉**（該清單已連三輪被補）。
  - ④(b) **靜態**：以 **AST（非 grep）**掃 `frontend/src/**`，
    斷言**無任何模組同時** import 上述雜湊入口 **且** 出現 `source_file_digest` 之寫入。
  - **mutation 三條**（SPEC L1550–1553）。
  ⚠️ **具名殘留**：純 JS 手刻 sha256（不經上述入口）本閘看不見；
  三值理由 `needs-research`，owner 主委，觸發＝FROZEN 後。**不得宣稱已解決。**
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——`event_id` 輸入僅 symbol／timeframe／t0 三者，後續 Phase 不改。
  🔴 **須同步**：Task 7.1 之 `decision_offset_bars`／`entry_price_semantic` 若被實作成**改動 t0 取值**，
  同一事件會跨批得到不同 `event_id` ⇒ 實作 7.1 時**須重跑本 Task 之集合相等斷言**，
  不得只跑 7.1 自身測試。

### Task 1.4 — t0 單位偵測（`票 #3-5`）

- **SPEC ref**：L1566–1577　**目標**：毫秒／秒級自動判定，判不出即拒。
- **輸入**：CSV 之 t0 欄原始值　**輸出**：毫秒整數
- **實作要點**：
  1. 沿用契約既有 `ms_magnitude_min` 門檻（**不得**另立第二條判定路徑）。
  2. 秒級 ×1000；無法判定 ⇒ `invalid_timestamp_unit`（既有 reason）。
  3. 偵測函式須為 **exported 單一函式**，CSV 與 JSON 兩路徑共用。
- **修改檔案**：`momentum/Analysis/event_samples/import_contract.py`
  （新增或抽出 `detect_t0_unit_ms()`）；`api/services/case_import_service.py::EventImportService` 呼叫之
  **既有 caller**：`import_events_file`／`import_events_json`（經 service）
- **不可做**：判不出單位時**不得猜預設值**。
- **邊界**：① `1704067200`（秒）⇒ `== 1704067200000`。
  ② 落在 `ms_magnitude_min` 兩側之模糊值 ⇒ `invalid_timestamp_unit`，不猜。
- **風險緩解**：RISK-(a)。
- **驗證**：三組 fixture（ms／秒／不合法）各 1 測；ms 值精確 `== 1704067200000`。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（`1704067200`（秒）⇒ `== 1704067200000`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：V-3 之 AST oracle 涵蓋面**須包含本偵測函式**，
  不得只證 schema 檢核共用——否則兩路徑會各自演化出不同單位判定。

### Task 1.5 — 前端上傳、預覽與對映 UI（含強制確認）（`票 #3-5`）

- **SPEC ref**：L1578–1587　**目標**：選檔→預覽→逐項對映→填批次預設→**強制勾選確認**→送出。
- **輸入**：使用者選擇之 CSV　**輸出**：呼叫 Task 1.2 端點之 multipart 請求
- **實作要點**：
  1. 顯示前 5 列預覽與**全部欄名**；逐項下拉對映（**不得預設任何對映**，A-4′）。
  2. 送出前顯示「你聲明的正例 X 筆／反例 Y 筆」並要求**勾選確認**；
     未勾 ⇒ `fetch` **不得**被呼叫。
  3. 文案**禁用「label 正確」字樣**（D-1：語意正確性不可機械證明，只能說「你聲明」）。
- **修改檔案**：`frontend/src/app/`（事件匯入頁；新增上傳與對映元件）；
  型別入 `frontend/src/lib/types.ts`
  **既有 caller**：無（新頁面／新區塊）
- **不可做**：不得預設任何欄位對映；文案禁用「label 正確」。
- **邊界**：① 未勾確認 ⇒ `fetch` call count `== 0`。
  ② 欄名重複之 CSV ⇒ 下拉須各自可辨（不得靜默取第一個同名欄）。
- **風險緩解**：RISK-(a)——強制確認與可疑欄警示（1.7）為 D-1 三層降險之兩層。
- **驗證**：`npx vitest run gap3_csv` **≥5 條**；`npm run build` rc=0。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（未勾確認 ⇒ `fetch` call count `== 0`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——Phase 4 於同頁加 horizon 多選，屬疊加。

### Task 1.6 — 對映 provenance 落檔（D-1）（`票 #3-5`）

- **SPEC ref**：L1588–1601　**目標**：可追「這批的正反例是依哪一欄、哪個檔宣告的」。
- **輸入**：`column_mapping`、來源檔名、`source_file_digest`、確認時間
  **輸出**：寫入該批 receipt
- **實作要點**：
  1. 於落檔時把四項寫入 receipt（**只記錄，不參與任何計算**）。
  2. `source_file_digest` **不得省略**（否則無法對證來源）。
  3. receipt 欄位型別依 Task 1.1 之 typed `receipt_schema`。
- **修改檔案**：`api/services/case_import_service.py::EventImportService`（落檔路徑）
  **既有 caller**：`import_events_csv`（Task 1.2）
- **不可做**：不得省略 `source_file_digest`。
- **邊界**：① 未帶 digest ⇒ fail-closed。② receipt 已存在時**不覆寫**既有欄。
- **風險緩解**：RISK-(a)。
- **驗證**：`pytest tests/api -q -k gap3_csv_provenance` **≥2 條**；
  `receipt['column_mapping']['label'] ==` 送出值。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（未帶 digest ⇒ fail-closed。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（receipt 為只增欄位之記錄檔）。
  🔴 **須同步**：Task 7.1 讓五維度由寫死改為可選之後，本 receipt **須一併記錄五維度之實際選值**，
  否則 Phase 7 之後「這批是用什麼語意算出來的」不可追。

### Task 1.7 — 可疑欄警示（D-1）（`票 #3-5`）

- **SPEC ref**：L1602–1613　**目標**：列出**其他也是二元**的欄名，降低誤指機率。
- **輸入**：CSV 全欄　**輸出**：警示清單（僅前端顯示，**不持久化**）
- **實作要點**：
  1. 預覽階段掃描所有欄，判定值域 ⊆ `{0,1}` 或 `{true,false}`。
  2. 列出**除使用者所選以外**的二元欄名。
  3. **只警示不阻擋**（語意不可機械判定）。
- **修改檔案**：`frontend/src/app/`（預覽元件內之 `detectBinaryColumns()`）
  **既有 caller**：Task 1.5 之預覽區塊
- **不可做**：不得因為只有一個二元欄就自動選它（A-4′）。
- **邊界**：① fixture 含 3 個二元欄 ⇒ 警示 `len == 2` 且集合相等。
  ② 全欄皆非二元 ⇒ 警示為空陣列（不得報錯）。
- **風險緩解**：RISK-(a)。
- **驗證**：`npx vitest run suspiciousBinaryColumns` **≥2 條**——①fixture 含 3 個二元欄 ⇒ 警示 `len == 2` 且集合相等；②全欄皆非二元 ⇒ 警示為 `[]` 且不報錯。
  **mutation**：改為「只有一個二元欄就自動選它」⇒ ①須紅。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（不寫入任何持久產物）。
  🔴 **須同步**：Phase 2 之篩選作用於**系統內搜尋結果**（欄位由系統產生），
  **不得**與本掃描合併為同一實作——合併後所有值域落在 `{0,1}` 之系統旗標欄都會被列為可疑，
  警示失去鑑別力（本 Task 之「`len == 2`」即會鬆脫）。

### Task 1.8 — 異質列顯式拒收（A-5′）（`票 #3-5`）

- **SPEC ref**：L1614–1626　**目標**：列間於 `direction`／`scenario`／`label_definition` 不一致
  且 `batch_defaults` 未涵蓋 ⇒ 拒收。
- **輸入**：解析後之列集合＋`batch_defaults`　**輸出**：`heterogeneous_rows_in_batch` 或通過
- **實作要點**：
  1. 逐列比對三個維度；`batch_defaults` 有指定者視為已涵蓋。
  2. 拒收訊息列出**前 3 個**衝突列號與欄名。
  3. **不自動分批**、**不靜默取第一列之值套用全批**。
- **修改檔案**：`momentum/Analysis/event_samples/import_contract.py::validate_event_import()`
  （新增異質列檢查）
  **既有 caller**：`EventImportService`（CSV 與 JSON 兩路徑）
- **不可做**：不得靜默取第一列之值套用全批。
- **邊界**：① fixture 混 long/short ⇒ 得該 reason 且**落檔數 `== 0`**。
  ② `batch_defaults` 指定 `scenario='A'` 而列間混 A／B ⇒ 落檔數 `== 0`
     （🔴 此組為 **Task 7.1 擴大 `scenario` 取值面後之必要 fixture**，須同批加）。
- **風險緩解**：RISK-(a)。
- **驗證**：`pytest tests/api -q -k gap3_heterogeneous_rows` **≥2 條**——
  ①混 long/short 之 fixture ⇒ reason `== 'heterogeneous_rows_in_batch'` 且**落檔數 `== 0`**；
  ②`batch_defaults` 指定 `scenario='A'` 而列間混 A／B ⇒ **落檔數 `== 0`**。
  訊息須列出**前 3 個**衝突列號與欄名（斷言列號數 `== 3`）。
  **mutation**：改為靜默取第一列之值套用全批 ⇒ ①②皆須紅。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：Task 7.1 將 `scenario` 由寫死 `'C'` 改為四值可選
  ⇒ 本 Task 之 fixture 須加邊界②那組，否則 Phase 7 擴大出來的取值面沒有對應測試。
### Task 1.10 — 欄位級 `lookahead_bars` 契約（D-7 之 L1）（`票 #3-0(b)`）

- **SPEC ref**：L1627–1686　**目標**：登記搜尋結果**每一個**未來欄之前視深度，
  並定死「名稱不具證據力」之信任邊界。
- **輸入**：`momentum/DataExtraction/case_search_engine.py` 之欄位盤點
  **輸出**：新檔 `momentum/Analysis/contracts/future_column_lookahead.json`
- **實作要點**：
  1. 🔴 **兩套命名、單位不同，不得寫死常數**：
     - **bar 命名**（`future_{N}bar_return`／`future_{N}bar_max_drawdown`）：
       `N` 就是根數 ⇒ 存 `lookahead_bars = N`。
     - **小時命名**（`future{H}_close_return`／`future72_max_return`／`future72_max_drawdown`，
       H ∈ {1,2,4,6,24,48,72}）：`H` 是**小時** ⇒ 存 `lookahead_hours = H`、
       **禁存固定 bar 數**；執行期以 `H ÷ 每根小時數` 換算
       （`case_search_engine.py:1385-1387` 之 `periods_{H}h`；12h 線 ⇒ `future72_*` 為 **6 根**，
       1h 線 ⇒ **72 根**）。
     - **無數字之 legacy 欄**（`future_max_return`／`future_max_drawdown` 等）：
       深度不可由欄名導出 ⇒ 顯式標 `lookahead_unknown: true`，走 L2／L3，
       **不得給任何預設深度**。
  2. ⚠️ `periods_72h` 亦被用於**過去 3 天 lookback**（`case_search_engine.py:1028-1046`），
     與未來欄同名不同義，**登記時不得混淆**。
  3. **辨識規則**須同時涵蓋契約蛇形與 CSV 標題形
     （`Future_NBar_Return_%`／`Future_NBar_Drawdown_%`，含大小寫與 `%` 後綴；
     見 `frontend/src/app/search/page.tsx:567-573`）。
  4. 🔴 **信任邊界（兩類來源，規則不同）**：
     - **系統產生欄**（`/search` 結果，有 producer／manifest provenance）：
       可由 L1 依 registry 直接解析深度；判定依據＝該批之 **provenance 記錄**，**非欄名**。
     - **外部上傳欄**（CSV 路徑）：**一律不得僅憑欄名進入可切分路徑**；
       須帶 producer/schema/digest 綁定，否則無論欄名是否命中 registry，
       皆走 Task 1.11 之 L2 並依 1.12 之 L3 決定可否切分。
  5. 換算為 **exported 函式** `resolve_lookahead_bars(column: str, timeframe: str) -> int | None`
     ——Task 1.9／1.11／2.1b 皆呼叫它，禁各自實作。
- **修改檔案**：新增 `momentum/Analysis/contracts/future_column_lookahead.json`；
  新增 `momentum/Analysis/event_samples/lookahead_registry.py`
  （`load_lookahead_registry()`／`resolve_lookahead_bars()`／`unregistered_future_columns()`）
  **既有 caller**：無（新模組）；Task 1.9／1.11／1.12／2.1b 為其消費端。
- **不可做**：不得以欄名字串樣式**推測**深度；不得漏登 `*_max_drawdown` 與 `future72_*`。
- **邊界**：
  ① 上傳 CSV 之欄名為 `future_4bar_return` 但**無 provenance** ⇒ `requires_declaration == True`
     （不得因名稱命中 registry 而放行）。
  ② 同欄名但來自 `/search` 之系統產生批（有 provenance）⇒ 深度直接解析 `== 4`。
- **風險緩解**：RISK-(a)——這是 D-7 三層防線之根；名稱可偽造，故以 provenance 為判定依據。
- **驗證**（`pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete` ＋ `pytest tests/api -q -k lookahead_rename_attack` **≥2 條**；🔴 深度導出之 `gap3_lookahead_depth` 屬 **Task 2.1b**，本 Task 不共用該 selector）：
  - ① `m['future_4bar_max_drawdown']['lookahead_bars'] == 4`；
    `m['future72_max_return']['lookahead_hours'] == 72` 且**無** `lookahead_bars` 鍵；
    換算對 `'12h'` 回 `6`、對 `'1h'` 回 `72`（精確 `==`）
  - ② `pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete`
    ——未登記集合 `== set()`
  - ③ 三形態 `Future_4Bar_Return_%`／`future_4bar_return`／`FUTURE_4BAR_RETURN` 皆解析為 4
  - ④ **registry 內容正確性**：以實跑盤出之全部 `future*` 欄逐欄對證單位與深度；
    盤點命令
    `grep -oE "future[_0-9][A-Za-z0-9_]*" momentum/DataExtraction/case_search_engine.py | sort -u`
    ——每項須在 registry 有對應且**分類正確（bar／hour／unknown 三類）**
  - ⑤ `pytest tests/api -q -k lookahead_rename_attack` **≥2 條**（見邊界①②）
  - **mutation 三條**（SPEC L1680–1683）
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**——1.11／1.12／2.1b 皆只讀不改。
  🔴 **須同步**：Phase 4 之 Task 4.1、Phase 7 之 Task 7.5 若引入任何新未來欄，
  **須先在本 registry 登記**；未登記時驗證② `== set()` 會紅，該紅為 fail-closed 之預期行為，
  **不得以放寬 validator 或加白名單消紅**。

### Task 1.11 — 未知欄強制宣告（D-7 之 L2）（`票 #3-0(b)`）

- **SPEC ref**：L1687–1703　**目標**：registry 解析不出深度時，**強制使用者宣告**，不得靜默取 max。
- **輸入**：解析後之欄集合＋registry　**輸出**：`requires_declaration: bool` ＋宣告值
- **實作要點**：
  1. 若出現無法由 Task 1.10 registry 解析深度之 `future*` 欄或自訂欄
     ⇒ `requires_declaration = True`。
  2. 🔴 **不得**以「其他欄都能解析」而取其 max 當全批深度。
  3. UI 明示「系統無法驗證此深度，錯報將導致資料洩漏」＋**勾選不可驗聲明**。
- **修改檔案**：`momentum/Analysis/event_samples/lookahead_registry.py`
  （新增 `requires_declaration(columns, timeframe) -> bool`）；
  `frontend/src/app/`（宣告輸入與勾選 UI）
  **既有 caller**：Task 1.9 之 UI、Task 1.12 之 L3 判定
- **不可做**：不得因為「其他欄都能解析」就用它們的 max。
- **邊界**：① fixture 含 `my_custom_signal` 欄且被條件引用 ⇒ `requires_declaration == True`。
  ② 未填宣告即送出 ⇒ fail-closed，**落檔數 `== 0`**。
- **風險緩解**：RISK-(a)。
- **驗證**：`pytest tests/api -q -k lookahead_declaration` **≥2 條**（見邊界①②）；
  **mutation**：改為「忽略無法解析之欄」⇒ ①須紅。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**——L2 與 Task 2.1b 之「全部可解析」路徑為**互斥分支**，非覆蓋關係。
  🔴 **須同步**：日後若任一 Phase 允許使用者自訂欄名進入篩選條件，
  該 Phase 須同批擴充本 Task 之宣告 UI，否則自訂欄會落入「無人負責宣告深度」之縫隙。

### Task 1.12 — 不可證則禁進切分（D-7 之 L3）（`票 #3-0(b)`）

- **SPEC ref**：L1704–1750　**目標**：深度不可證之批**禁止進入 train/test 切分與條件 IC**，
  但**仍可產出事件研究表**（無訓練即無洩漏）。
- **輸入**：批次之 `requires_declaration` 與宣告值　**輸出**：批次狀態
  `split_blocked_unverifiable_lookahead` ＋ event-study-only 執行路徑
- **實作要點**：
  1. 未填 L2 宣告、或宣告與 registry 衝突 ⇒ `split_events` 與 `ic_feed` **皆拒**。
  2. 🔴 **新增 executor `run_event_study_only()`**——**不呼叫** `split_events`／`ic_feed`、
     不進訓練。理由：現碼 `pipeline.py:178` 之 `run()` **無條件**呼叫 `split_events`，
     照現有呼叫鏈只能在「違反 L3」與「產不出表」之間二選一。
  3. `event_forward_return_table` 之 `event_split_plan` 改 **`Optional`**；
     為 `None` 時所有列之 `time_cluster_id` 取 `-1`
     （現碼 `tables.py:140` 對不在 `cl.index` 者已是此值）。
  4. 🔴 `event_split_plan is None` 時 **`ci` 一律標 `unavailable`，不得計算**
     ——`_cluster_bootstrap_ci` 依 cluster 重抽樣，全塞同一個 `-1` 會產生
     **看似有效但錯誤**的信賴區間。與 `tables.py:61-69` 之既有 fail-closed 一致
     （`formal_pooled_inference_allowed=False`、`reason=no_event_split_plan`）。
  5. 🔴 **不得**以空的假 `split_plan` 冒充「未執行切分」（具名之假綠形態）。
- **修改檔案**：
  - `momentum/Analysis/event_samples/pipeline.py`：新增 `run_event_study_only()`
  - `momentum/Analysis/event_samples/tables.py::event_forward_return_table()`
    （`event_split_plan` 改 Optional；`ci` 之 unavailable 分支）
  - `momentum/Analysis/event_samples/event_split.py::split_events()`（拒絕分支）
  - `momentum/Analysis/event_samples/ic_feed.py`（拒絕分支）
  **既有 caller**：`pipeline.py::run()`；`api/routes/case.py::analyze_event_import`
- **不可做**：不得以「警告後放行」替代（fail-open）；不得把 reason 硬寫進程式。
- **邊界**：
  ① 該批呼叫 analyze ⇒ **`split_events` 未被呼叫**（斷言未呼叫，非只回警告字串）。
  ② 傳入 `clusters` 為空 DataFrame 之假 split plan ⇒ **raise**（不得靜默當 None 走過去）。
- **風險緩解**：RISK-(a)——這是三層防線之最後一層。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k split_blocked` **≥6 條**
  （①②③③b③c④，字面見 SPEC L1730–1741）；
  ④ 另含 `grep -rc 'split_blocked_unverifiable_lookahead' api/ frontend/src/ momentum/
  --include=*.py --include=*.ts` 之**硬編碼字面數 `== 0`**。
  **mutation 四條**（SPEC L1742–1744）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**——與 Phase 6 止血閘為不同拒絕條件、不同 reason 來源
  （本 Task 走契約 `capability_unavailable_reasons`，Task 6.0 走
  `ic_report_contract.json` 之 `reasons.analysis_rejected`）⇒ 互不覆蓋，
  **亦不得合併為同一回應**（合併會使使用者無法分辨「洩漏不可證」與「特徵數過大」）。
  🔴 **須同步**：本 reason 之登記增量由 **Task 1.1 驗收④**以對凍結 fixture 之差集統一驗證，
  本 Task **不再自寫計數**。

### Task 1.9 — 答案窗宣告與 purge 下界（D-7 之 L2 使用者介面）（`票 #3-0(b)`）

- **依賴**：Task 1.10、1.11
- **SPEC ref**：L1751–1792　**目標**：CSV 上傳時收集答案窗宣告（**逐 tf**），
  寫入 `lookahead_bars_declared`（map）並投影到 `label_definition.window.horizon_bars`。
- **輸入**：CSV 之可用 horizon ＋使用者宣告　**輸出**：`lookahead_bars_declared`（map）、
  `declared_window_bars`（map）、`horizon_bars`（int）
- **實作要點**：
  1. 預設取**檔內最大可用 horizon**（有 `future_1..12` ⇒ 預設 12）；
     可往下調但**須勾選**「我的篩選條件未用到超過第 N 根」之聲明，
     UI 明示**此為無法驗證的聲明**；欄位接受**任意正整數**（不限 1..12）。
  2. 宣告值經 Task 2.1b 之 `depth(tf)` **逐 tf** 解析後寫入 derived 欄
     `lookahead_bars_declared`（**map，非 scalar**）。
  3. 以 `max(1, lookahead_bars_declared[該列 timeframe])` 寫入
     `label_definition.window.horizon_bars`（契約下限之投影）。
     🔴 **逐列**取該列自己的 `timeframe`（批內可有多 TF，「該批所屬 tf」無唯一值）。
  4. 🔴 **UI 逐 tf 收集**：批內單一 TF ⇒ 退化為單一輸入框；
     多 TF ⇒ **逐 tf 各一個輸入框**，**不得**以單一輸入框套用所有 tf。
  5. purge 寬度之下界式**唯一定義在 §D-3′-a（ii）**，本 Task 不重述、只呼叫。
- **修改檔案**：`frontend/src/app/`（答案窗宣告區塊，逐 tf）；
  `api/services/case_import_service.py::EventImportService`（寫入 derived 欄）；
  呼叫 `momentum/Analysis/event_samples/lookahead_registry.py::resolve_lookahead_bars()`
  **既有 caller**：Task 1.5 之上傳頁
- **不可做**：不得以「檔內有哪些 `future_N` 欄」**推斷**實際用到第幾根；
  不得給小於檔內最大 horizon 的預設值；不改 `event_split.py` 之 purge 演算法。
- **邊界**：
  ① 未勾聲明而調低 ⇒ fail-closed，**落檔數 `== 0`**。
  ② 多 TF 批以**單一輸入框**套用全部 tf ⇒ fail-closed。
- **風險緩解**：RISK-(a)。
- **驗證**：`pytest tests/api -q -k gap3_horizon_declaration` **≥5 條**——
  ①預設 `== 12`；②見邊界①；③宣告 `== 4` 之單一 1h 批 ⇒
  `embargo_ms_by_symbol` 值 `== 4 * TIMEFRAME_SECONDS['1h'] * 1000`；
  ④宣告 20（>12）⇒ 接受；⑤**深度公式一致性**——CSV 路徑與系統內篩選路徑對同一組輸入
  回傳**相同** depth（呼叫**同一 exported 函式**，非各自實作）；
  ⑥多 TF 批 ⇒ `declared_window_bars` 與 `lookahead_bars_declared` **鍵集皆恰為 `{'1h','12h'}`**。
  **mutation 兩條**（SPEC L1786–1787）。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——與 `/search` 路徑（Task 4.1 ③）為**同一欄位、同一寫入點**，
  兩路徑須呼叫 Task 2.1b 之同一深度函式。
  🔴 **須同步**：Task 2.1b 對系統內篩選路徑**鎖定下界且不可調低**，
  與本 Task「可調低但須勾選聲明」為**兩條路徑之不同規則** ⇒ 實作須以批次來源分派；
  統一為寬鬆版即 fail-open，統一為嚴格版則 CSV 路徑無法上傳。

---

**Phase 1 測試（三層）＋ Phase Gate**

- **單元**：`pytest tests/momentum/event_samples/ -q -k "lookahead_registry_complete or split_blocked"`
- **邊界層**：`pytest tests/api -q -k "gap3_contract_reason_registry or gap3_csv_import or
  gap3_csv_provenance or gap3_horizon_declaration or lookahead_declaration or lookahead_rename_attack"`
- **前端**：`npx vitest run gap3_csv canonicalSourceCoverage` ＋ `npm run build`
- 🔴 **Phase Gate**：上列三層 rc=0，**且** V-1／V-1b／V-1c／V-2／V-3／V-4／V-12 之
  對應 Task 驗證條目全綠，**且**本 Phase 全部 mutation 逐條實跑轉紅並還原轉綠（receipt 入 commit）。
## Phase 2 — 匯出前篩選（依賴：Task 1.1 之契約欄位定案；**不依賴** Task 1.2 端點）

**目標**：讓使用者在 `/search` 匯出前先篩掉不要的列，並把「答案窗宣告」從
**不可驗的使用者聲明**變成**機器可證事實**。
**完成後系統狀態**：系統內篩選路徑之答案窗下界由條件自動導出並**鎖定不可調低**。

> 🔴 **定位（D-7 改正）**：Phase 2 不是「方便功能」——它是本批**唯一**能把答案窗宣告機械化的路徑。
> 系統內篩選時系統確知使用者引用了哪些 `future_N` 欄，可自動導出下界。

### Task 2.1 — `/search` 匯出前篩選面板（`票 #3-0(a)`）

- **SPEC ref**：L1799–1810　**目標**：對搜尋結果任一**數值**欄設 `>=`／`<=`／區間，多條件 AND。
- **輸入**：搜尋結果列＋使用者條件　**輸出**：條件物件（供 2.1b／2.2／2.3 消費）
- **實作要點**：
  1. 面板**只讀**搜尋結果並產生條件物件；**不改任何原始欄位值**。
  2. 多條件以 AND 組合；每條件形如 `{column, op: '>='|'<='|'between', value|range}`。
  3. 條件物件為 2.1b（導深度）、2.2（寫 `filters`）、2.3（算筆數）之**唯一輸入來源**。
- **修改檔案**：`frontend/src/app/search/page.tsx`（新增篩選面板區塊）；
  型別入 `frontend/src/lib/types.ts`
  **既有 caller**：`/search` 頁之匯出流程
- **不可做**：不得在篩選中改動任何原始欄位值。
- **邊界**：① 只篩**數值**欄；字串欄不在本 Task（選到字串欄 ⇒ 該欄不出現在可選清單）。
  ② 條件為空 ⇒ 匯出筆數 `==` 原筆數（不得因面板存在而改變預設行為）。
- **風險緩解**：RISK-(b)——三個區塊（篩選／附帶欄／五維度）同處匯出面板，
  須共用 Task 2.3 之**同一筆數計算函式**，否則使用者會在同一畫面看到互相矛盾的筆數。
- **驗證**：`npx vitest run exportFilter` **≥6 條**；含「篩選後筆數 `==` 手算筆數」之數值斷言。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（只篩**數值**欄；字串欄不在本 Task（選到字串欄 ⇒ 該欄不出現在可選清單）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——面板不改原始值。
  🔴 **須同步**：Task 4.1 決定**哪些欄**、Task 7.1 決定**用什麼語意算**、本 Task 決定**哪些列**，
  三者疊加不互相覆蓋，但**須共用 2.3 之同一計數函式**。

### Task 2.1b — 由篩選條件自動導出答案窗下界（D-7 第 2 層）（`票 #3-0(a)`）

- **SPEC ref**：L1811–1864　**目標**：依 Task 1.10 registry 解析條件引用之**所有**欄位，
  取最大深度為答案窗**下界並鎖定**，使用者**不得調低**。
- **輸入**：條件物件＋`declared_window_bars`（map）＋registry
  **輸出**：`lookahead_bars_declared: Mapping[tf -> int]`
- **實作要點**：
  1. 🔴 **深度公式（本批唯一權威定義；Task 1.9 與 V-12 一律引用本式，禁第二份）**：
     ```
     depth(tf) = max( declared_window_bars[tf] ,
                      max over 所有實際被引用之欄位 c of  bars_of(c, tf) )

     bars_of(c, tf) = c.lookahead_bars                      # bar 命名欄
                    = c.lookahead_hours ÷ hours_per_bar(tf)  # 小時命名欄（禁寫死常數）

     lookahead_bars_declared = { tf: depth(tf) for tf in 批內出現之 timeframe 集合 }
     ```
  2. 🔴 左項為 **`declared_window_bars[tf]`**（**不含 floor**），
     **不是** `label_definition.window.horizon_bars`（該欄下限為 1，會把真實 0 讀成 1）。
     缺該 tf 之鍵 ⇒ **fail-closed**，不得以 `1` 或其他 tf 之值默認替代。
  3. 🔴 **輸出逐 tf**：`bars_of` 本就 tf-parameterized ⇒ `depth` 亦逐 tf 不同；
     對批內每個出現過的 `tf` 各求一次。
  4. 🔴 鍵集於**匯入驗證通過後、prepare／coverage 之前凍結**；coverage **不得重建**
     （§D-3′-a（ii））。
  5. 四種 scenario（A／B／C／two_stage）**一律適用同一式**，不另立公式。
  6. 使用者可**往上**調（保守方向永遠允許），**不得**調低於導出值。
- **修改檔案**：
  - 新增 `momentum/Analysis/event_samples/lookahead_depth.py`：
    `def depth_by_timeframe(referenced_columns, declared_window_bars, timeframes) -> dict[str,int]`
    （**唯一 exported 深度函式**；Task 1.9 亦呼叫它）
  - `frontend/src/app/search/page.tsx`（下界鎖定之 UI）
  **既有 caller**：Task 1.9（CSV 路徑）、Task 2.2（寫入 `filters` 時附帶）
- **不可做**：不得允許調低於導出值；`bars_of` 之小時分支**不得**直接取 `lookahead_hours` 當根數。
- **邊界**：
  ① 條件用 `future_2` 與 `future_7`（bar 命名，1h 批）⇒ 鎖定 `>= 7`；
     嘗試設 5 ⇒ 前端阻擋且 `fetch` call count `== 0`。
  ② 🔴 **附帶欄不得納入 `max`**：條件只引用 `future_2`、Task 4.1 附帶欄選 `[1,3,7]`
     ⇒ 導出下界仍 `== 2`（附帶欄與 label 判定無關；過度 purge 會吃掉訓練樣本，
     **保守過頭亦屬錯誤**）。
- **風險緩解**：RISK-(a)——這是把「不可驗聲明」變成「機器可證」的唯一路徑。
- **驗證**：`pytest tests/api -q -k gap3_lookahead_depth` **≥4 條**（①–④，SPEC L1846–1859）；
  其中②之 receipt 命令：
  `python3 -c "from momentum.core.constants import TIMEFRAME_SECONDS; print(72*3600//TIMEFRAME_SECONDS['1h'], 72*3600//TIMEFRAME_SECONDS['12h'])"` → `72 6`。
  **mutation 三條**（SPEC L1860–1862）。
  ⚠️ 驗收②**刻意不寫成**「`lookahead_bars…＝72`」之形態——那會暗示「根數恆為 72 而與 tf 無關」，
  正是檔頭 SYNC-FORBID 所禁之字面；本條要表達的恰是**相反**：**根數逐 tf 不同，時間長度才相同**。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**——完全依賴 Task 1.10 registry（存活至 Phase 7（終）且只增不改）。
  🔴 **須同步**：Task 4.1 之附帶欄多選**不得**納入 `max`，此區分須以邊界②之測試釘死。

### Task 2.2 — 篩選條件寫入 `label_definition.filters`（`票 #3-0(a)`）

- **SPEC ref**：L1865–1879　**目標**：把篩選條件寫進 Task 1.1 已登記之 `filters` 欄。
- **輸入**：條件物件　**輸出**：匯出檔之 `label_definition.filters`
- **實作要點**：
  1. 寫入 Task 1.1 已登記之 `label_definition.filters`（**不新增 schema 鍵**）。
  2. 序列化**一律依 §G S-1..S-9**（S-2 鍵序／S-5 NaN 與浮點／S-9 位元組 encoder）；
     🔴 本 Task **不自行定義**序列化規則，只引用。
  3. 與 Phase 7 之五維度（同一 `label_definition` 物件之其他鍵）**在同一序列化點寫出**。
- **修改檔案**：`api/services/case_import_service.py`（或匯出組裝點）之
  `label_definition` 序列化函式；引用 §G S-9 參考實作
  **既有 caller**：`/search` 匯出流程、Task 1.2 CSV 端點
- **不可做**：🔴 **不得把篩選條件納入 `event_id` 之輸入**（會使同事件跨批 id 不同，違反 D-2）。
- **邊界**：① 匯出檔 `label_definition.filters` 與送出條件**深度相等**（`==`）。
  ② `filters` 鍵**存在於**契約 `label_definition.fields`（防漂移斷言）。
- **風險緩解**：RISK-(b)。
- **驗證**：`npx vitest run exportFilterPersist` **≥2 條**——
  ①匯出檔 `label_definition.filters` 與送出條件**深度相等**（`==`，逐鍵遞迴比對）；
  ②`'filters' in contract['label_definition']['fields']` 為真（防漂移）。
  ＋ `python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));assert 'filters' in c['label_definition']['fields']"` rc=0。
  **mutation**：把 `filters` 併入 `event_id` 之輸入 ⇒ Task 1.3 之 `event_id` 集合相等斷言須紅。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：Phase 7 五維度與本欄須在**同一序列化點**寫出並依 §G。

### Task 2.3 — 即時筆數顯示（`票 #3-0(a)`）

- **SPEC ref**：L1880–1891　**目標**：顯示「將匯出 N 筆（原 M 筆）／你聲明的正例 X／反例 Y」。
- **輸入**：條件物件＋搜尋結果　**輸出**：純顯示（無持久產物）
- **實作要點**：
  1. 抽出**單一計數函式** `computeExportCounts(rows, filters) -> {N, M, X, Y}`。
  2. 🔴 該函式為 Task 1.5 上傳確認、Task 4.1b／7.3 動態揭露之**同一組事實之唯一來源**
     ——四處顯示點皆呼叫它，任一 Phase 改變計數口徑時全部同步改變。
  3. 純顯示，**不得以估算值**。
- **修改檔案**：`frontend/src/lib/`（新增 `computeExportCounts`）；
  `frontend/src/app/search/page.tsx`（顯示區塊）
  **既有 caller**：Task 1.5／2.1／4.1b／7.3
- **不可做**：不得以估算值顯示。
- **邊界**：① `N + 被濾掉數 == M`。② `X + Y == N`。
- **風險緩解**：RISK-(b)——四個顯示點共用同一函式，避免同畫面矛盾筆數。
- **驗證**：vitest 斷言邊界①②。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（無持久產物）。
  🔴 **須同步**：Task 7.5 把報酬表拆為正／反／全體三組後計數口徑不變（`X + Y == N` 仍成立），
  但 `control_kind == 'user_labeled_other'` 時全體組標 `not_computed`
  ⇒ 本 Task 文案**不得**讓使用者以為全體組必然可算。

---

**Phase 2 測試（三層）＋ Phase Gate**

- **單元**：`pytest tests/api -q -k gap3_lookahead_depth`
- **前端**：`npx vitest run exportFilter` ＋ 筆數守恆斷言 ＋ `npm run build`
- **邊界層**：附帶欄不入 `max` 之對照測（2.1b 邊界②）
- 🔴 **Phase Gate**：上列 rc=0，**且** V-12 之對應條目全綠，**且**本 Phase 全部 mutation
  逐條實跑轉紅並還原轉綠（receipt 入 commit message）。
## Phase 3 — 事件批次刪除（依賴：無）

**目標**：使用者可刪除整批事件與其全部產物。
**完成後系統狀態**：`DELETE /api/v1/case/events/{import_id}` 可用，磁碟無孤兒檔。

### Task 3.1 — `DELETE /api/v1/case/events/{import_id}`（`票 #3-4`）

- **SPEC ref**：L1894–1907　**目標**：刪除該批事件與其 artifact，**不留孤兒檔**。
- **輸入**：`import_id`　**輸出**：204／404
- **實作要點**：
  1. 刪除範圍＝事件檔 ＋ **Task 1.6 之 receipt** ＋ 該批 artifact
     （🔴 刪除範圍須隨 Phase 1／2 新增之產物**同步擴張**）。
  2. 不連帶刪 kline 快取或 Feature Library。
  3. 不存在之 `import_id` ⇒ 404（非 500）。
- **修改檔案**：`api/routes/case.py`（新增 `delete_event_import`，緊鄰 `get_event_import`）；
  `api/services/case_import_service.py::EventImportService`（新增刪除方法，涵蓋全部落檔路徑）
  **既有 caller**：無（新端點）；前端 caller 於 Task 3.2 接上
- **不可做**：不得提供「刪除全部」端點。
- **邊界**：① 刪後 `GET` status_code `== 404`。
  ② 🔴 該 `import_id` 之**所有落檔路徑殘留檔數 `== 0`**
     （僅驗 404 偵測不到磁碟殘留——端點回 404 但 receipt 仍在）。
- **風險緩解**：RISK-(b)。
- **驗證**：`pytest tests/api -q -k gap3_event_delete` **≥4 條**（含邊界①②）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（刪後 `GET` status_code `== 404`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：Phase 1 之 receipt 與 Phase 2 之 `filters` 皆屬「該批 artifact」
  ⇒ 刪除範圍須隨這兩個 Phase 新增之產物同步擴張，否則 Task 3.3 之警語與實況不符。

### Task 3.2 — 前端刪除鈕與二次確認（`票 #3-4`）

- **SPEC ref**：L1908–1918　**目標**：確認框顯示該批筆數與匯入時間。
- **輸入**：批列表之列　**輸出**：確認後呼叫 3.1 端點
- **實作要點**：
  1. 確認框顯示**該批筆數與匯入時間**（取自批列表既有欄位，不另查）。
  2. 未確認 ⇒ `fetch` **不得**被呼叫。
  3. **不得以 `window.confirm` 帶過**（須為可測之元件）。
- **修改檔案**：`frontend/src/app/`（批列表頁之刪除鈕與確認框元件）
  **既有 caller**：批列表頁
- **不可做**：不得以 `window.confirm` 帶過。
- **邊界**：① 未確認時 `fetch` call count `== 0`。② 只在批列表提供（其他頁面無入口）。
- **風險緩解**：RISK-(b)。
- **驗證**：vitest 斷言邊界①。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（未確認時 `fetch` call count `== 0`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（與 Task 4.3／5.3 之確認框為不同元件、不同觸發點）。
  🔴 **須同步**：Task 3.3 於**同一個**確認框疊加警語 ⇒ 兩者合併實作（3.2 先、3.3 後），
  且 3.3 上線後本 Task 之「未確認 `fetch` call count `== 0`」須維持通過（回歸），
  **不得因加警語而改動確認流程之控制流**。

### Task 3.3 — 已被引用批次之警語（`票 #3-4`）

- **SPEC ref**：L1919–1929　**目標**：仍可刪，但明示「引用它的分析結果將無法重現」。
- **輸入**：該批是否被引用　**輸出**：確認框內之警語
- **實作要點**：
  1. 於 **Task 3.2 之同一確認框**疊加警語（不另建元件）。
  2. **仍可刪**——只加警語，不改刪除行為本身。
  3. 🔴 警語之正確性依賴 3.1 之刪除範圍確實涵蓋該批全部產物 ⇒ **3.1 與 3.3 須同批驗收**。
- **修改檔案**：Task 3.2 之確認框元件（疊加警語段落）
  **既有 caller**：Task 3.2
- **不可做**：不得靜默刪除被引用批次。
- **邊界**：① 該字串出現於確認框（`toContain` 斷言）。
  ② 未被引用之批次 ⇒ 不顯示該警語（避免恆顯示而失去鑑別力）。
- **風險緩解**：RISK-(b)。
- **驗證**：vitest `toContain` 斷言（邊界①②）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（該字串出現於確認框（`toContain` 斷言）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：若 3.1 未隨 Phase 1／2 擴張刪除範圍，
  警語與實況不符（部分產物仍在、分析其實仍可重現）。

---

**Phase 3 測試＋Gate**：`pytest tests/api -q -k gap3_event_delete` ＋ vitest 確認框三條；
Gate＝V-5 對應條目全綠 ＋ 落檔殘留 `== 0`。

---

## Phase 4 — 匯出端之報酬欄與揭露（依賴：無）

**目標**：匯出檔可攜帶多個 `future_*` 欄供 Excel 分析；匯出端**不再**寫 `label_value`、
**不再**有「主答案窗」（依 §D-3′ 移到 IC 分析層）。
**完成後系統狀態**：匯出面板明文揭露 scenario／深度／purge／`control_kind` 四項事實。

> 🔴 **更名理由**：§D-3′ 把答案窗移到 IC 分析層 ⇒ 本 Phase 已不含答案窗。
> 答案窗之落點＝**Task 7.6（UI）＋ Task 7.0b（計算）**。
> 保留舊名會使實作者在此尋找答案窗 UI 而找不到，或反過來把它加回匯出面板。

### Task 4.1 — 匯出檔之附帶 `future_*` 欄；移除匯出端之答案窗與 `label_value`（D-3′）（`票 #3-1`）

- **SPEC ref**：L1940–1978　**目標**：三件事——加附帶欄多選、移除主答案窗與 `label_value`、
  釐清 `horizon_bars` 與 `lookahead_bars_declared` 之關係。
- **輸入**：使用者之附帶欄選擇＋深度導出結果
  **輸出**：匯出檔（含 `future_{h}bar_return` 諸欄、`lookahead_bars_declared` map、
  `label_definition.window.horizon_bars`）
- **實作要點**：
  1. **新增**「附帶報酬欄」多選（**預設全選 1..12**）；每個選中 h 帶 `future_{h}bar_return`
     ——**純供 Excel 攜帶**，不進 `ic_feed`、不決定任何 horizon。
  2. **移除**匯出面板之「主答案窗」單選；匯出端**不再**寫入 `label_value`
     （該欄於契約為 `optional_fields`，省略合法）。
  3. `label_definition.window.horizon_bars` **仍寫入**，值＝
     `max(1, lookahead_bars_declared[該列 timeframe])`（**下限 1 為契約 serialization floor**）；
     **真實深度**另寫 derived 欄 `lookahead_bars_declared`（map）。
     🔴 兩者**刻意可不相等**（深度 0 時前者為 1、後者為 0）。
- **修改檔案**：`frontend/src/lib/eventExport.ts`（移除主答案窗與 `label_value` 寫入；
  加附帶欄組裝）；`frontend/src/app/search/page.tsx`（附帶欄多選 UI）
  **既有 caller**：`/search` 匯出流程
- **不可做**：🔴 匯出端**不得以任何形式寫入 `label_value`**（含寫 `null`、寫 `0`、
  或另立 `label_value_status` 之類新欄——新欄須先改契約，D-6）；
  不得把附帶欄之 `max` 當成 lookahead 深度。
- **邊界**：
  ① 附帶欄選擇改變 ⇒ `lookahead_bars_declared` 與 `window.horizon_bars` **皆不變**。
  ② `scenario='C'` 且無品質過濾之 1h fixture ⇒ `lookahead_bars_declared['1h'] === 0`
     且 `window.horizon_bars === 1`（**兩者刻意不等**）。
- **風險緩解**：RISK-(a)——`label_value` 留在匯出端會讓「換 h 需重匯出」之錯誤心智模型復活。
- **驗證**：`npx vitest run eventExportHorizonColumns` **≥6 條**（①–⑥，SPEC L1957–1972）；
  其中②之 `'label_value' in records[0] === false` 須**逐列**斷言（非只第一列）；
  ④須**呼叫同一 exported 深度函式比對，非寫死數字**。
  **mutation 四條**（SPEC L1973–1976）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：本 Task **刻意覆蓋** R1 版之 (a) 方案（見 §D-3 撤回理由）。
  🔴 **須同步**：兩路徑（CSV 宣告 vs `/search` 導出）仍須呼叫 **Task 2.1b 之同一深度函式**。

### Task 4.1b — 匯出時揭露每個選項在動什麼（`票 #3-1`）

- **SPEC ref**：L1979–2005　**目標**：把四件「使用者從未被告知」之事實顯示在匯出面板。
- **輸入**：本批實際設定　**輸出**：UI 文案（**不進序列化產物**）
- **實作要點**：
  1. 🔴 下列四段**皆由實際設定導出，禁寫死**；缺任一段即視為未完成。
  2. **scenario ＝ {實際值} — {契約 doc 之白話}**。
  3. **lookahead 深度 ＝ {N} 根，來源＝{引用之欄位清單}**——`N` 取自
     `lookahead_bars_declared[本批 timeframe]`；C 無品質過濾時為 **0**；
     批內多 TF ⇒ **逐 tf 各顯示一行**。
     🔴 **不得**顯示 `window.horizon_bars`（有 floor，深度 0 會顯示成 1）。
  4. **本批之 purge 下界（事件事實層）＝ {N} 根**，並說明此深度之來源；
     同時明示「條件 IC 分析時之實際 purge 另取本次答案窗，**取兩者較大者**」
     ——公式權威在 §D-3′-a（ii），本欄**只揭露、不重述式子**。
  5. **`control_kind` 之值與白話**（現由 `eventExport.ts:104` **寫死**
     `user_labeled_same_trigger`，使用者從未選過亦不知其存在）。
- **修改檔案**：`frontend/src/app/search/page.tsx`（匯出面板揭露區塊）；
  文案取自契約 `_doc`（不另寫一份）
  **既有 caller**：匯出面板
- **不可做**：不得只寫在文件而不顯示於 UI。
- **邊界**：① 四段文字皆出現。② `control_kind` 顯示值 `==` 匯出檔實際值（防寫死漂移）。
- **風險緩解**：RISK-(a)。
- **驗證**：vitest 斷言邊界①②。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（四段文字皆出現。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：🔴 **會被 Task 7.3 刻意覆蓋**——7.3 為本 Task 四段揭露之**嚴格超集**。
  **超集關係須以逐項對照驗證，非口頭宣稱**（R7 事故：7.3 當時漏掉 `control_kind`，
  取代後 UI 反而少揭露一項）⇒ 移除本 Task 獨立實作前，
  須逐項比對兩邊揭露項集合並斷言 **4.1b ⊆ 7.3**。
  實作順序 **4.1b 先、7.3 後**；7.3 上線時**須移除本 Task 之獨立實作**
  （否則同一面板兩份文案來源，日後改一份漏一份）。此覆蓋不影響 G-2 golden（純 UI 文案）。

### Task 4.1c — 明文標示本批不提供 IC decay（`票 #3-1`）

- **SPEC ref**：L2006–2023　**目標**：釘死「換答案窗不需重新匯出」之正確心智模型。
- **輸入**：無　**輸出**：SPEC 與 UI 之說明文字
- **實作要點**：
  1. 明寫：條件 IC decay **曲線**非本批交付；附帶 `future_*` 欄**不進 `ic_feed`**；
     要看不同答案窗請**於 IC 分析頁改答案窗重跑分析**——**不需重新匯出事件批**。
  2. 一次得到整條 decay 曲線待 GAP-6 處理。
  3. 🔴 舊措辭「需要 decay 則換**主答案窗**重跑」已隨主答案窗移除而作廢，**不得殘留**。
- **修改檔案**：`frontend/src/app/search/page.tsx`（匯出面板說明段）
  **既有 caller**：匯出面板
- **不可做**：不得讓使用者以為多選附帶欄就會得到多條 IC。
- **邊界**：① 選 `[1,3,7]` 附帶欄 ⇒ `window.horizon_bars` **不變**。
  ② 文案中**不得**出現「重新匯出」作為換 h 之手段（斷言該字串不出現）。
- **風險緩解**：RISK-(a)。
- **驗證**：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；
  vitest 斷言說明出現於匯出面板 ＋ 邊界①②。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（選 `[1,3,7]` 附帶欄 ⇒ `window.horizon_bars` **不變**。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**GAP-6**。
- **覆蓋風險**：GAP-6 若交付 multi-horizon IC，本說明**須撤除**。

### Task 4.2 — 事件後報酬表顯示完整曲線（`票 #3-1`）

- **SPEC ref**：L2024–2036　**目標**：`horizons` 由呼叫端傳入，前端可選。
- **輸入**：`horizons` 集合　**輸出**：`analyze_tables` 之逐 horizon 列
- **實作要點**：
  1. `analyze_tables` 之 `horizons` 改由呼叫端傳入（現碼預設 `(1,2,4)`，`pipeline.py:98`）。
  2. **只改要算哪些 horizon**；**不改**每個 horizon 之計算式。
  3. 🔴 本 Task 一併建立 **§G S-9 參考實作**
     `canonical_serialize.py::canonical_event_table_bytes`，並附 S-9 之 6 條驗收。
- **修改檔案**：`momentum/Analysis/event_samples/pipeline.py`（`analyze_tables` 呼叫點，:98）；
  `momentum/Analysis/event_samples/tables.py`；
  新增 `momentum/Analysis/event_samples/canonical_serialize.py`
  **既有 caller**：`pipeline.py::run()`、`run_event_study_only()`（Task 1.12）
- **不可做**：不得因列數變多而改變 `n_eff` 之定義。
- **邊界**：① 列數 `== len(horizons)`。
  ② 🔴 **G-2 事件 golden 須同步更新並在 commit message 說明**
     （D-4：這是**合法的數值輸出變更**，**不得靜默重凍**）；
     重凍**須以 S-9 參考實作重算**，禁另寫序列化。
- **風險緩解**：RISK-(a)——golden 重凍為受管變更。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k horizon_curve` **≥3 條** ＋ S-9 之 6 條驗收。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（列數 `== len(horizons)`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：改變 `analyze_tables` 預設值之呼叫形態（**刻意**，已由 G-2 守）。

### Task 4.3 — 缺欄確認框逐 horizon 列出（`票 #3-1`）

- **SPEC ref**：L2037–2049　**目標**：訊息**逐附帶 horizon** 列出缺幾筆。
- **輸入**：各附帶 horizon 之缺欄筆數　**輸出**：確認框訊息
- **實作要點**：
  1. 逐**附帶** horizon 列缺筆數。
  2. 🔴 原文之「主答案窗與附帶欄**分開列**」已作廢——匯出端不再有「答案窗缺欄」這件事
     （`label_value` 不在匯出檔內）⇒ **只剩附帶欄一類**。
  3. 答案窗之可算／缺筆數改於 **IC 分析頁**揭露（落點＝Task 7.6）。
- **修改檔案**：`frontend/src/app/search/page.tsx`（缺欄確認框訊息組裝）
  **既有 caller**：匯出流程
- **不可做**：不得因缺欄而阻擋匯出；不得在此處揭露答案窗。
- **邊界**：① 訊息含每個缺欄附帶 horizon 之筆數數字。
  ② 訊息**不得**含「主答案窗」字樣（斷言不出現）。
- **風險緩解**：RISK-(b)。
- **驗證**：vitest 斷言邊界①②。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（訊息含每個缺欄附帶 horizon 之筆數數字。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：覆蓋現行單一 horizon 之訊息字串（**刻意**）。
  🔴 **須同步**：Task 5.3 原以「主答案窗 h：N/M 筆可算」為顯示內容，已隨本 Task 一併改寫。

---

**Phase 4 測試＋Gate**：`npx vitest run eventExportHorizonColumns` ＋
`pytest tests/momentum/event_samples/ -q -k horizon_curve` ＋ S-9 六條；
Gate＝V-6 對應條目全綠 ＋ G-2 golden 重凍已於 commit message 說明。
## Phase 5 — 錯誤訊息與表頭說明（依賴：Task 5.0）

**目標**：使用者看得懂每個指標與每則錯誤在講什麼。
**完成後系統狀態**：指標詞彙有單一 SoT；兩表表頭皆有 tooltip 且與 SoT 機械對證。

### Task 5.0 — 建立指標詞彙 SoT（`票 #3-3`）

- **SPEC ref**：L2052–2067　**目標**：新建 glossary 作為前後端**唯一**文案來源。
- **背景（實查事實）**：`event_import_contract.json` 之頂層 `_doc` 是**整份契約的敘事字串**，
  **不含** `macro mean`／`n_eff`／`lift_threshold`／`prevalence_full` 等表頭鍵
  ⇒ 原「取自契約 `_doc`」**不可執行**。
- **輸入**：現有兩表之表頭鍵集　**輸出**：新檔
  `momentum/Analysis/contracts/event_metrics_glossary.json`
- **實作要點**：
  1. 每個指標鍵對應 `{term, definition, formula_ref}`。
  2. 起始鍵集至少涵蓋：`macro_mean`／`micro_mean`／`n_eff`／`lift_threshold`／
     `prevalence_full`／`prevalence_learn`／`signal_frequency`／`tail_excluded`。
  3. **只放文案與公式指標，不放數值**。
- **修改檔案**：新增 `momentum/Analysis/contracts/event_metrics_glossary.json`；
  新增 loader `momentum/Analysis/event_samples/metrics_glossary.py::load_metrics_glossary()`
  **既有 caller**：無（新檔）；Task 5.2 為其唯一消費端
- **不可做**：🔴 不得把定義同時寫在前端（Task 5.2 以 `==` 斷言防漂移）。
- **邊界**：① 鍵集 `>=` 上列八鍵（`set(g) >= {...}` 斷言）。
  ② 任一鍵缺 `definition` ⇒ loader fail-closed。
- **風險緩解**：RISK-(b)。
- **驗證**：SPEC L2059 之 `python3 -c` 一行 rc=0。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（鍵集 `>=` 上列八鍵（`set(g) >= {...}` 斷言）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（Task 5.2 只讀不寫）。
  🔴 **須同步**：Task 7.5 把報酬表改為正／反／全體三組後，
  新增之**分組標籤**與 **`not_computed` 狀態文字**亦屬表頭文案 ⇒ **須登記進 glossary**；
  未登記則 5.2 之「tooltip `==` glossary `definition`」對新表頭無可比對來源，
  前端只能另寫一份定義——即本 Task「不可做」所禁之第二份副本。

### Task 5.1 — `.source.json` 誤傳之訊息追加正解（`票 #3-2`）

- **SPEC ref**：L2068–2080　**目標**：誤把來源對證檔當事件檔上傳時，訊息直接給正解。
- **輸入**：上傳檔內容　**輸出**：400 ＋含正解之訊息
- **實作要點**：
  1. 判別依據＝內容為 `canonicalSourceText` 形狀
     （symbol／timeframe／timestamp／positive_case／price_change）。
  2. 訊息**追加**「此為來源對證檔，請改放在 `source_file` 欄並勾選 `verify_source_digest`」。
  3. 🔴 `legacy_schema_detected` 之 **reason 字面不變**（只追加提示字串）。
- **修改檔案**：`api/routes/case.py::_rejected()`（或訊息組裝點）；
  判別函式入 `momentum/Analysis/event_samples/import_contract.py`
  **既有 caller**：`import_events_file`；🔴 **Task 1.2 之 CSV 端點須走同一則提示**
- **不可做**：不得因判別為 `source.json` 就自動改走 `source_file` 流程（靜默轉換＝契約禁止）。
- **邊界**：① status_code `== 400` 且訊息含 `source_file`。
  ② 🔴 誤送到 **CSV 端點**（副檔名非 `.csv`）⇒ **同一則正解提示**
     （否則使用者在新端點得到的訊息比舊端點更難排除，本修補在新路徑等於沒做）。
- **風險緩解**：RISK-(b)。
- **驗證**：`pytest tests/api -q -k source_json_hint`（含邊界①②）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（status_code `== 400` 且訊息含 `source_file`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**（reason 字面不變，下游不受影響）。

### Task 5.2 — 事件型兩表 tooltip（讀 Task 5.0 之 SoT）（`票 #3-3`）

- **SPEC ref**：L2081–2091　**目標**：兩表所有表頭加 tooltip，文案取自 glossary。
- **輸入**：glossary　**輸出**：表頭 tooltip
- **實作要點**：
  1. 前端於 build/runtime 讀 glossary（單一來源），**不在前端另寫定義**。
  2. 每個表頭鍵對應一個 tooltip。
  3. 只加 tooltip，**不改數值與版面**。
- **修改檔案**：`frontend/src/components/`（事件型兩表之表頭元件）；
  glossary 取得管道（build-time import 或 API）
  **既有 caller**：事件型兩表頁面
- **不可做**：不得在前端另寫一份定義。
- **邊界**：① 每個表頭之 tooltip 文字 `==` glossary 對應 `definition`。
  ② glossary 缺該鍵 ⇒ 顯示 fail-closed 之佔位而非空字串（避免靜默漏 tooltip）。
- **風險緩解**：RISK-(b)。
- **驗證**：vitest 斷言邊界①（逐表頭 `==`）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（每個表頭之 tooltip 文字 `==` glossary 對應 `definition`。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：Phase 6。
- **覆蓋風險**：**無**。🔴 **須同步**：Task 7.5 改為三組垂直排列後，
  三組**共用同一組表頭鍵** ⇒ 本斷言須在三組結構下**逐組重跑**；
  實作順序 **5.2 先、7.5 後**，且 7.5 **不得為分組另寫一份表頭文案**。

### Task 5.3 — 缺答案窗欄之確認框（`票 #3-2`）

- **SPEC ref**：L2092–2105　**目標**：匯出前**主動顯示**每個附帶 horizon 的可算／缺筆數。
- **輸入**：各附帶 horizon 之可算與缺筆數　**輸出**：確認框訊息
- **實作要點**：
  1. 匯出前主動顯示「附帶欄 h：N/M 筆可算、K 筆因資料尾端不足而缺」。
  2. 🔴 顯示對象改為**每個附帶 horizon**（原文之「主答案窗 h」已移出匯出層）；
     答案窗之可算／缺筆數於 **IC 分析頁**揭露（Task 7.6）。
  3. 與 **Task 4.3 為同一訊息區塊，兩者須合併實作（4.3 先）**。
- **修改檔案**：Task 4.3 之確認框訊息組裝（同一處）
  **既有 caller**：匯出流程
- **不可做**：不得阻擋匯出。
- **邊界**：① fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（數字精確比對）。
  ② 訊息**不得**含「主答案窗」字樣。
- **風險緩解**：RISK-(b)。
- **驗證**：vitest 斷言邊界①②。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（數字精確比對）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：與 Task 4.3 同一區塊，合併實作。

---

**Phase 5 測試＋Gate**：`pytest tests/api -q -k source_json_hint` ＋ vitest tooltip 逐表頭 ＋
Task 5.0 之一行斷言；Gate＝V-7／V-10 對應條目全綠。

---

## Phase 6 — IC 分析止血閘（依賴：Task 6.0）

**目標**：在 GAP-6 之分塊計算上線前，**過渡性**擋住會炸記憶體的 IC 分析請求。
**完成後系統狀態**：`/api/v1/ic/analyze` 於**啟動任務前**檢查特徵數並 fail-closed；
上限值有可重跑之量測 receipt，非拍腦袋。

### Task 6.0 — IC 錯誤 reason 之登記處（D-6）（`票 #3-9a`）

- **SPEC ref**：L2108–2122　**目標**：把 `feature_count_exceeds_cap` 登記到**IC 側**契約。
- **背景**：該 reason **不屬** `event_import_contract`（那是匯入契約）。
- **輸入**：`momentum/Analysis/contracts/ic_report_contract.json`（現有 `reasons` 三類：
  `net_ic_unavailable`／`event_fallback`／`xsec_not_applicable`）
  **輸出**：新增 `analysis_rejected` 分類並登記該值
- **實作要點**：
  1. 於 `reasons` 新增 `analysis_rejected` 分類。
  2. 程式與前端一律由該檔取字面，**不得硬寫**。
  3. 🔴 驗收斷言用**成員資格**而非等值——Task 7.7 會往**同一個** `analysis_rejected`
     再加兩個 reason，寫成 `== ['feature_count_exceeds_cap']` 會在 7.7 上線時**假紅**；
     該清單之**最終**內容由 Task 7.7 斷言。
- **修改檔案**：`momentum/Analysis/contracts/ic_report_contract.json`；
  其 loader（IC 側）
  **既有 caller**：`api/routes/ic_analysis.py`／`api/services/ic_analysis_service.py`
- **不可做**：不得在程式內硬寫該字串。
- **邊界**：① SPEC L2114 之 `python3 -c` 一行 rc=0（含 `len(r)==4`）。
  ② 硬編碼掃描數 `== 0`：
     `grep -rn 'feature_count_exceeds_cap' api/ frontend/src/ --include=*.py --include=*.ts --include=*.tsx | grep -v 'ic_report_contract' | wc -l`
- **風險緩解**：RISK-(b)。
- **驗證**：①`python3 -c` 一行（SPEC L2114）rc=0，含 `len(r)==4`；②硬編碼掃描 `grep -rn 'feature_count_exceeds_cap' api/ frontend/src/ --include=*.py --include=*.ts --include=*.tsx | grep -v 'ic_report_contract' | wc -l` `== 0`。
  **mutation**：把字面硬寫進 `api/routes/ic_analysis.py` ⇒ ②須紅。
- **存活至**：**GAP-6**。
- **覆蓋風險**：GAP-6 之規模防護可能新增更多 reason，屬**疊加**。

### Task 6.1 — analyze 前置特徵數檢查（`票 #3-9a`）

- **SPEC ref**：L2123–2133　**目標**：在**啟動任務前**擋下超量請求。
- **輸入**：該 run 之 `feature_count`　**輸出**：400 ＋ reason ＋實際數與上限數
- **實作要點**：
  1. 於 `/api/v1/ic/analyze` **啟動任務之前**檢查特徵數。
  2. 超過上限 ⇒ 400，reason 取自 Task 6.0 之登記檔，訊息含**實際數與上限數**。
  3. 🔴 **碼內須註明本 Task 為過渡止血，GAP-6 之分塊計算上線後取代**。
- **修改檔案**：`api/routes/ic_analysis.py`（analyze handler 之前置檢查）；
  `api/services/ic_analysis_service.py`（若檢查落在 service 層）
  **既有 caller**：IC 分析頁
- **不可做**：不得提供「強制略過上限」之開關。
- **邊界**：① 以 218369 特徵之 run 呼叫 ⇒ status_code `== 400`
     **且任務未被建立**（斷言 task store 筆數不變，非只驗 HTTP 碼）。
  ② 小 run（15 特徵）⇒ 200 **且任務確實被建立**（task store 筆數 +1）。
- **風險緩解**：RISK-(b)。
- **驗證**：`pytest tests/api -q -k ic_feature_cap` **≥3 條**（含邊界①②，後者即 V-9）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（以 218369 特徵之 run 呼叫 ⇒ status_code `== 400`）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**GAP-6**。
- **覆蓋風險**：**會**被 GAP-6 取代。

### Task 6.2 — 上限值之量測協定（D-5）（`票 #3-9a`）

- **SPEC ref**：L2134–2147　**目標**：上限值須有**可重跑**之量測 receipt，禁拍腦袋。
- **輸入**：多個 `feature_count` 之實跑　**輸出**：receipt（≥3 個量測點）＋設定值
- **實作要點**：
  1. 每個量測點須記**六欄**：①機器 RAM 總量與機型 ②目標 pid（**單一，不得混進程**）
     ③baseline footprint（發請求前）④peak footprint（採樣至任務結束或被 kill）
     ⑤採樣間隔與總時長 ⑥該 run 之 `feature_count`。
  2. 🔴 量測工具**固定為** macOS `sample <pid>` 之 **Physical footprint** 欄，
     **禁用 `ps rss`**——macOS 壓縮頁面使 RSS 失真（UAT 實測 RSS 96–400MB vs footprint 7.1GB）。
  3. 上限 ＝ **最小超標點之 `feature_count` × 安全係數 0.5**。
- **修改檔案**：新增 `scripts/measure_ic_footprint.sh`（量測協定之可重跑腳本）；
  receipt 落 `handoffs/run_receipts/`；設定值入 `api/core/config.py` 或 `momentum/core/config.py`
  **既有 caller**：Task 6.1 讀該設定值
- **不可做**：🔴 **禁拍腦袋填數字**；**無 receipt 不得寫入設定**；**禁以 `ps rss` 當量測值**。
- **邊界**：① receipt 含 **≥3 個量測點**且每點**六欄齊全**。
  ② 同一 run 重跑 2 次之 peak 差異 **`< 20%`**（否則量測不穩定，須增加採樣或改協定）；
     設定值 `<=` 最小超標點 × 0.5。
- **風險緩解**：RISK-(a)——量測工具選錯會讓上限差兩個數量級。
- **驗證**（`bash scripts/measure_ic_footprint.sh` 產出之 receipt，落 `handoffs/run_receipts/`；`>= 3` 點）：
  `handoffs/run_receipts/`）須滿足——
  ①量測點數 `>= 3` 且每點**六欄齊全**（缺任一欄即 fail-closed）；
  ②同一 run 重跑 2 次之 peak 差異 `< 20%`；
  ③設定值 `<=` 最小超標點之 `feature_count` `* 0.5`；
  ④receipt 內之量測工具欄位 `== 'sample:Physical footprint'`（**斷言不是 `ps rss`**）。
  **mutation**：把量測工具改回 `ps rss` ⇒ ④須紅；刪掉任一量測點使數 `< 3` ⇒ ①須紅。
- **存活至**：**GAP-6**。
- **覆蓋風險**：同 Task 6.1。

### Task 6.3 — 進度回報與前端狀態區分（`票 #3-9a`）

- **SPEC ref**：L2148–2159　**目標**：進度加 `feature_count` 與細分階段；
  前端區分「後端無回應」與「任務執行中」。
- **輸入**：任務進度　**輸出**：含 `feature_count` 之 progress response ＋兩種前端狀態
- **實作要點**：
  1. progress response 增 `feature_count` 鍵與細分階段。
  2. 前端以**不同字串**區分「後端無回應」與「任務執行中」。
  3. 🔴 階段字串須設計為**可擴充集合**，測試**不得**以固定 enum 之窮舉相等斷言鎖死
     （GAP-6 會細分更多階段；改測試是掩蓋行為變更的常見路徑）。
- **修改檔案**：`api/routes/ic_analysis.py`（progress response）；
  `frontend/src/app/ic-analysis/page.tsx`（狀態顯示）
  **既有 caller**：IC 分析頁之輪詢
- **不可做**：🔴 不得以固定假進度值填充（UAT 已證實 `progress==0.12` 卡 15 分鐘之誤導性）。
- **邊界**：① response 含 `feature_count` 鍵。
  ② 兩種狀態之顯示字串 `!==`。
- **風險緩解**：RISK-(b)。
- **驗證**：`pytest tests/api -q -k ic_progress_fields` ＋ vitest 斷言邊界②。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（response 含 `feature_count` 鍵。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：🔴 **GAP-6 之後仍保留**（Phase 6 五個 Task 中**唯一**之永久產出）。
- **覆蓋風險**：**無**。🔴 **須同步**：GAP-6 引入分塊計算後階段會更細
  ⇒ 測試須容許集合擴充。

### Task 6.4 — 止血閘之存活驗證（D-5）（`票 #3-9a`）

- **SPEC ref**：L2160–2171　**目標**：證明「未載入大矩陣」。
- **輸入**：218369 特徵之 run　**輸出**：三個採樣點之 footprint
- **實作要點**：
  1. 呼叫 analyze 後，**在 cap 檢查之後、回應之前與之後各採樣一次** footprint。
  2. 🔴 **不得在 cap 檢查之前採樣**就宣稱通過（明列之假綠形態）。
  3. 採樣時點由 **Task 6.1 之前置檢查位置**決定 ⇒ 兩者須**同批實作並以同一測試釘住先後順序**。
- **修改檔案**：`tests/api/`（存活驗證測試）；復用 Task 6.2 之量測腳本
  **既有 caller**：無（測試）
- **不可做**：不得在 cap 檢查之前採樣就宣稱通過。
- **邊界**：① V-8 之三項斷言（見 SPEC §V L3433）。
  ② 若 6.1 之檢查被移到任務啟動之後 ⇒ 本測試須**紅**（釘住先後順序）。
- **風險緩解**：RISK-(a)。
- **驗證**：`pytest tests/api -q -k ic_stop_gate_alive` rc=0，條目數 `>=` V-8 所列。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（V-8 之三項斷言（見 SPEC §V L3433）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**GAP-6**。
- **覆蓋風險**：🔴 GAP-6 之分塊計算取代 6.1 時本 Task **一併作廢**
  ⇒ 須在 GAP-6 之 SPEC **明列作廢並刪除**，**不得留著空跑而成為永遠通過的假綠**。

---

**Phase 6 測試＋Gate**：`pytest tests/api -q -k "ic_feature_cap or ic_progress_fields or
ic_stop_gate_alive"` ＋ Task 6.0／6.2 之一行斷言與 receipt；
Gate＝V-8／V-9 對應條目全綠 ＋ 量測 receipt 六欄齊全且重跑差異 `< 20%`。
## Phase 7 — 全棧接線：把後端既有能力接出前端（依賴：無）

**目標**：後端五維度皆已實作、前端**一個都沒接**（全走 `eventExport.ts` 寫死預設）
⇒ 本 Phase 全部接出，並把答案窗與報酬語意移到 IC 分析層（§D-3′）。
**完成後系統狀態**：五維度可見可改且有機械閘守；分析時 producer 上線；
報酬表分正／反／全體三組；特徵 run 覆蓋對證 fail-closed。

> 🔴 **病因（使用者問「怎麼又出現前後端無法串聯」）**：B5 之 SPEC 只寫「API 接線＋前端三頁」、
> 驗收條件是「UAT 能跑通」⇒ 做了能跑通的最小路徑，六個維度全走預設。
> 三輪 code review 未抓到，因**委員審的是有無被正確實作——SPEC 沒要求接，實作沒接就不算違規**。
> **規格層的漏，審查層抓不出來。** 且 `feedback_fullstack_wiring_audit`（全棧三欄稽核）未執行
> ——同病第二次。
> ⇒ **本 Phase 每個 Task 之驗收都必須含前端那一欄**，backend pytest 全綠不算完成。

> 🔴 **維度恰五個**：`scenario`／`control_kind`／`entry_price_semantic`／
> `label_return_mode`（**唯一巢狀者**，路徑 `label_definition.fields`）／`decision_offset_bars`。
> `counterexample_kind` **不是**第六個維度——它位於 `optional_fields`、語意為**逐列填寫**，
> 接成批次下拉會污染反例分類。

### Task 7.0 — 前置：擴 `EventExportOptions` 補齊五維度（`票 #3-全棧`）

- **依賴**：無（為 7.1／7.2 之前置）
- **SPEC ref**：L2308–2347　**目標**：**只做型別與參數化**，不加 UI、不動後端。
- **輸入**：`opts`　**輸出**：`buildEventContractRecords` 之記錄
- **實作要點**：
  1. `EventExportOptions`（`eventExport.ts:9-17`）補齊 `controlKind`／`labelReturnMode`／
     `decisionOffsetBars` 等欄位；把 `:92`／`:102`／`:104` 三處寫死改為 `opts.X ?? <現行預設>`。
  2. 🔴 **不含** `counterexample_kind`（逐列選填欄，非批次維度）。
  3. 🔴 **預設值之唯一例外**：依 §F-3′ 把 `entry_price_semantic` 之寫死預設由
     `trigger_open` 改為 **`trigger_close`**（D-4 合法變更；**不影響任何數值**，
     變的只有宣告欄字面——匯出端已不寫 `label_value`）。
  4. 🔴 `label_return_mode` 之寫入路徑為**巢狀**（`label_definition.label_return_mode`），
     與其餘四者之頂層路徑不同，須各自對應正確路徑。
- **修改檔案**：`frontend/src/lib/eventExport.ts`
  （`EventExportOptions` 型別、`buildEventContractRecords` 之 `:92/:102/:104`）
  **既有 caller**：`frontend/src/app/search/page.tsx:522-525`（🔴 現況「一個都沒傳」）
- **不可做**：🔴 **除 §F-3′ 明列之 `entry_price_semantic` 一項外**，不得調整任何其他預設值；
  不得把 `label_return_mode` 寫到頂層（寫錯位置會使 schema 檢核通過但語意落在錯的物件）。
- **邊界**：① 全部不傳 opts ⇒ 五欄值 `===` 預設（`'C'`／`user_labeled_same_trigger`／
     **`trigger_close`**／`close_to_close`／`0`），且 `counterexample_kind` **不出現於輸出**。
  ② 傳任一非 F-1′ 之三元組 ⇒ 匯出**照常成功**、每列**不含** `label_value`、
     `records[0].entry_price_semantic` **忠實等於所傳值**（宣告即事實）。
- **風險緩解**：RISK-(a)——本 Task 之「行為不變」指 **G-2 事件 golden byte 級不變**，
  宣告欄字面刻意改正。
- **驗證**：`npx vitest run eventExportOptions` **≥7 條**（①–⑤每維度一條、⑦、⑧，SPEC L2331–2344）；
  ②之巢狀斷言須為 `records[0].label_definition.label_return_mode`。
  **mutation 兩條**（SPEC L2345–2346）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**——被 7.1（接 UI）與 7.2（機械閘）**依賴而非覆蓋**；
  三者為 **7.0 → 7.1 → 7.2 之嚴格順序**。
  🔴 **須同步**：7.0 之邊界①是 7.1 golden byte 回歸之**基準**；
  若 7.0 順手改了任一其他預設值，7.1 之回歸就失去意義 ⇒ 兩者須同批驗。

### Task 7.0b — 分析時 `label_value` producer 與其 wiring（`票 #3-全棧`）

- **SPEC ref**：L2348–2844（本批**最大**之 Task）　**目標**：把 `label_value` 之產生
  由匯出層移到**分析層**，並定死兩階段函式、receipt hash 與 purge 下界之唯一路徑。
- **輸入**：`records`、`bars_by_tf`、`event_label_spec`、`event_import_id`、
  `lookahead_bars_declared`、`timeframe_seconds`
  **輸出**：`PreparedAnalysisWindows`（frozen dataclass）
- **實作要點**：
  1. 新建 `momentum/Analysis/event_samples/label_value_from_case.py`，
     **公開恰兩個**函式。🔴 **簽章逐字內聯於此（冷啟動可執行；與 SPEC 之一致性由下方
     驗證欄之同步斷言機械對證，非靠人眼）**：
     ```python
     def prepare_analysis_windows(
         records,
         bars_by_tf,
         *,
         event_label_spec,
         event_import_id,
         lookahead_bars_declared,
         timeframe_seconds) -> PreparedAnalysisWindows:
         """階段 2（prepare-windows）：唯一產生 receipt 與其 hash 之處。"""

     def resolve_label_value_at_analyze(
         prepared,
         bars_by_tf,
         *,
         event_label_spec) -> Mapping[str, float | None]:
         """階段 3：依 F-1′ 支援矩陣產生 label_value；偏離即回 supported=False。"""
     ```
     `*` 後為 **required keyword-only**（不是預設值）。
  2. `PreparedAnalysisWindows` 欄集**恰如** SPEC L2378–2396：
     `.supported`／`.windows: tuple[WindowRow, ...]`（**不是 dict**）／
     `.analysis_alignment_receipt_hash: str`（決定性）／`.per_tf: tuple[PerTfRow, ...]`／
     `.normalized_spec_bytes: bytes`（相等判定＝**bytes 相等**，非 `dict==`、非 `json.dumps`）／
     `.allowed_event_ids: frozenset[str]`。
     `WindowRow` 欄集恰 `{event_id, symbol, timeframe, decision_at_ms, entry_at_ms,
     label_start_ms, label_end_ms}`，按 `event_id` UTF-8 升冪。
  3. 🔴 **F-1′ 支援矩陣（封閉）**：本批只支援三元組
     `(trigger_close, close_to_close, k=0)`；**答案窗 `h` 為任意正整數，不受矩陣限制**。
     偏離 ⇒ **F-2′ fail-closed**：`capability_status == "unavailable"`、
     reason `== "label_producer_unsupported_for_declared_semantics"`
     （登記處**只引用 Task 1.1**，本 Task 不自寫登記祈使句或計數）。
  4. 🔴 **編排（`_run_analysis` 事件分支；唯一取得點）**：於**匯入驗證通過後、
     prepare-windows 之前**建構**一次** `timeframe_seconds`，並以**同一物件**
     傳入 `purge_lower_bound_ms` 與 feature-run gate（驗收以 `is` 比對）。
     **禁**各自建構、**禁**在 gate 內直讀 module 常數
     （`momentum/core/constants.py::TIMEFRAME_SECONDS` 僅為**建構素材**）。
  5. 🔴 **CSV 自帶 `label_value` 與分析時重算之互斥**：採 **fail-closed**——
     若使用者在 IC 頁給定與匯入宣告**不同**之 `h`，該次分析**拒絕**，
     reason 同 F-2′。理由：另一選項等於把不可驗之使用者數值當 oracle 沿用。
  6. 前端**不得**在 TS 產生、推導或攜帶 `label_value`（第二份副本必漂移）。
- **修改檔案**：
  - 新增 `momentum/Analysis/event_samples/label_value_from_case.py`
    （`prepare_analysis_windows`／`resolve_label_value_at_analyze`／
    `PreparedAnalysisWindows`／`WindowRow`／`PerTfRow`）
  - `api/services/ic_analysis_service.py::_run_analysis`（事件分支之五階段編排）
  - `momentum/Analysis/event_samples/event_split.py`（purge 下界之注入）
  - `momentum/Analysis/event_samples/ic_feed.py`（只吃 `prepared1`）
  **既有 caller**：`api/routes/ic_analysis.py`（analyze 端點）
- **不可做**：不得在不支援之組合下回傳任何非 `None` 之 `label_value`；
  不改 `event_id`；不得在匯出層產生 `label_value`。
- **邊界**：
  ① 尾端不足 ⇒ 該 eid 之 `label_value is None` 且**不出現**於餵給 `ic_feed` 之輸入
     （斷言鍵集不含該 eid；**非**填 0）。
  ② `h=3` 與 `h=7` 各跑一次 ⇒ event id 集合**相同**、`label_values` **不相同**、
     各 `WindowRow.label_end_ms` 各自對應自己的 h。
- **風險緩解**：RISK-(a)——本 Task 觸及數值正確性，§C0 不得降殘留。
- **驗證**（`pytest tests/momentum/event_samples/ -q -k analysis_label_producer` **≥7 條** ＋ `pytest tests/api -q -k event_analysis_horizon_purge` **≥5 條**；🔴 `eventContractOptions` 屬 **Task 7.1**，本 Task 不共用）：
  - 🔴 **簽章同步斷言（防本檔內聯副本與 SPEC 漂移）**：
    `python3 -c "import io,re;s=io.open('docs/GAP3_EVENT_UX_SPEC.md',encoding='utf-8').read();d=io.open('docs/GAP3_EVENT_UX_TODO.md',encoding='utf-8').read();import sys;sys.exit(0 if 'def prepare_analysis_windows(' in s and 'def prepare_analysis_windows(' in d else 1)"` rc=0，
    且兩檔之 `prepare_analysis_windows` 參數名序列**逐字相等**（以 `inspect`-style 文字比對；
    不相等即紅，須改 TODO 而非改 SPEC——SPEC 已 FROZEN）。
  - `pytest tests/momentum/event_samples/ -q -k analysis_label_producer` **≥7 條**
    （①–⑦，SPEC L2665–2677；①②之 `atol=0`）
  - `pytest tests/api -q -k event_analysis_horizon_purge` **≥5 條**（⑧–⑨，含 ⑨(h) **per-symbol**
    斷言：對每個 symbol scope，餵入 `purge_lower_bound_ms` 之 event_id 集合
    `== {w.event_id for w in prepared0.windows if w.symbol == scope}`，
    且 alignment-failure `event_id` 不得出現在 split assignments）
  - vitest 兩組（見 SPEC L2664 起）
  - 🔴 `windows` 為 tuple ⇒ **禁用 `windows[eid][...]` 之 dict API**（R15 明禁）
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（尾端不足 ⇒ 該 eid 之 `label_value is None` 且**不出現**於餵給 `ic_feed` 之輸入）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：本 Task **取代** R7 版之匯出端 producer（**刻意**）。

### Task 7.1 — 五維度全部接出前端（依賴 7.0）（`票 #3-全棧`）

- **SPEC ref**：L2845–2917　**目標**：`/search` 匯出面板與 `/data-preparation` 匯入表單
  各提供五個維度之選擇；預設維持現行但**必須可見可改**。
- **輸入**：契約之 `accepted`／`enum` ＋ `EVENT_DIM_PATH_EXCLUSIONS`
  **輸出**：可操作選項集合 ＝ `selectable(path, dim)`
- **實作要點**：
  1. `selectable(path, dim) = accepted(dim) − pathExclusions(path, dim)`。
     `accepted(dim)` ＝契約之 `accepted` 鍵；無該鍵者取 `enum` 全集。
  2. `pathExclusions` ＝**前端單一具名常數** `EVENT_DIM_PATH_EXCLUSIONS`，
     每筆帶**非空理由字串**；本批封閉內容見 SPEC L2854–2860（五列）。
     🔴 **`/ic-analysis` 沿用同一常數，不另建第二份排除清單**。
  3. 兩類不可選值之 UI 呈現**須分別顯示**：契約恆拒者顯示 `rejected_with_reason` 字面；
     路徑排除者顯示 `pathExclusions` 之理由字串。**兩者皆 disabled 且不計入 selectable**。
  4. 每個選項旁附白話說明，取自契約 `doc` 欄（**不另寫**）。
- **修改檔案**：`frontend/src/app/search/page.tsx`、`/data-preparation` 頁；
  新增 `frontend/src/lib/eventDimensions.ts`
  （`EVENT_DIM_PATH_EXCLUSIONS`、`selectable(path, dim)`）
  **既有 caller**：Task 7.0 之 `buildEventContractRecords`
- **不可做**：🔴 不得在前端硬寫 enum 清單（必須由契約導出）；
  不得在未交付 A／B label producer 前於 `/search` 開放 A／B。
- **邊界**：① `/search` 之 `scenario` 只開 `C`（`A`／`B`／`two_stage` disabled 並顯示理由）；
     同一維度在 `/data-preparation` 之 selectable `==` **全部 4 值**（證明限制**只在該路徑**）。
  ② 🔴 **五維度全部維持預設 ⇒ G-2 事件 golden byte 級不變**
     （證明**接出 UI 這件事本身不動任何數值**）。
- **風險緩解**：RISK-(a)——`entry_price_semantic`／`decision_offset_bars`／`label_return_mode`
  三者**直接改變報酬數字**；使用者主動改預設所致之 golden 改變屬 D-4 合法變更，
  **須在 commit message 說明，不得靜默重凍**。
- **驗證**：`npx vitest run eventContractOptions` **≥10 條**（①–⑩，SPEC L2870–2884）；
  ⑨之 `EVENT_DIM_PATH_EXCLUSIONS` 內容以**集合相等**斷言（🔴 **不用計數字面**
  ——R4 版寫「筆數 `=== 1`」，擴為三筆時未同步，兩家獨立命中）；
  ＋ `npm run build` rc=0。**mutation 兩條**（SPEC L2885）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**（Phase 7 為最後一個 Phase）。
  🔴 **回應 Task 1.3 之「須同步」（雙向登記）**：本 Task 之
  `decision_offset_bars`／`entry_price_semantic` 若被實作成**改動 t0 之取值**，
  同一事件將跨批得到不同 `event_id` ⇒ **實作本 Task 時須重跑 Task 1.3 之
  `event_id` 集合相等斷言**（JSON 匯出 vs CSV 回灌 `==`），
  **不得只跑本 Task 自身測試**。此條與 Task 1.3 之覆蓋風險欄互為雙向。

### Task 7.2 — 機械閘：可操作選項集合＝`selectable(path,dim)` 且選值真的傳到落檔（依賴 7.0／7.1）（`票 #3-全棧`）

- **SPEC ref**：L2918–2957　**目標**：對五個維度逐一驗**三層**
  （R3 版只驗第一層，三家全員判不足）。
- **輸入**：UI 選項 ＋ `buildEventContractRecords` 之落檔記錄
  **輸出**：測試（無產品碼變更）
- **實作要點**：
  1. **① 集合層**——「**可操作**（`disabled === false` 且可 focus）之 UI 選項集合」
     `==` `selectable(path, dim)`。**disabled／hidden 一律不計入**
     ⇒ 無法以放一個 disabled 的 `platform_random_bars` 湊足元素數。
  2. **② round-trip 層**——每維度選一個**非預設值** → 呼叫 `buildEventContractRecords`
     → 斷言落檔記錄之對應路徑 `===` 所選值。
     🔴 **這層才是擋住 B5 病因（「介面有、沒傳」）的那一層**；
     只有①時 UI 可以全對而 payload 仍是寫死預設。
  3. **③ 非 enum 欄**——`decision_offset_bars`：有可輸入且非唯讀之控制項、
     輸入 `-1` ⇒ fail-closed（契約 `min: 0`）、輸入 `k` ⇒ 落檔 `=== k`。
  4. 並禁止 `eventExport.ts` 出現無 UI 對應的寫死值。
- **修改檔案**：`frontend/src/lib/__tests__/contractEnumWiring.test.ts`（新增測試）
  **既有 caller**：無（測試）
- **不可做**：🔴 **不得以人工清單當比對基準**（那就是第三份副本）。
- **邊界**：① 契約新增第 5 個 `scenario` 值而不改 UI ⇒ ①**須紅**
     （該紅為設計意圖，**不得以更新人工清單消紅**）。
  ② 本閘**不擴及** `/ic-analysis`（其可操作集合由 Task 7.6 ⑤ 守、常數內容由 7.1 ⑨ 守）
     ——避免同一斷言出現兩份；若日後納入，須**同時刪除** 7.6 ⑤。
- **風險緩解**：RISK-(b)——這是 Phase 7 病因之直接對策。
- **驗證**：`npx vitest run contractEnumWiring` **≥14 條**（5×①＋5×②＋2×③＋2×路徑對照）；
  ①之斷言為 `new Set(uiEnabledOptions)` 等於 `new Set(selectable(path, dim))` 且長度相等。
  **mutation 四條**（SPEC L2949–2954）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**。🔴 **邊界**：本閘只保護**五個批次維度**、不保護契約全部欄位
  ——Task 1.1 之 reason 與 `filters` 屬非 enum 型欄位，**不在涵蓋面內**；
  此邊界須明寫於實作註解與測試名稱，避免日後誤以為「有機械閘＝契約全欄受保護」。

### Task 7.3 — 動態揭露本批設定（`票 #3-全棧`）

- **SPEC ref**：L2958–2981　**目標**：匯出前顯示七項，**全部由實際設定導出**。
- **輸入**：本批實際設定　**輸出**：UI 文案
- **實作要點**：
  1. 顯示：scenario／**`control_kind`**／進場價／報酬算法／決策位移／
     lookahead 深度（來源：欄位清單）／purge 將為 N 根。
  2. 🔴 `control_kind` 為必列項——4.1b 宣稱本 Task 為其嚴格超集，
     而原清單**漏掉它** ⇒ 取代後 UI 反而少揭露一項。
  3. 🔴 文案須來自 **Task 7.6 內容②所定義之欄位級 formatter registry**（每欄一個 formatter），
     本頁只**選取自己的欄集**；**不得**寫成硬編欄集之面板級 formatter
     （IC 分析頁欄集不同，面板級共用會逼其中一頁多顯示或少顯示）。
- **修改檔案**：`frontend/src/app/search/page.tsx`（揭露區塊，取代 4.1b 之獨立實作）；
  formatter registry 見 Task 7.6
  **既有 caller**：匯出面板
- **不可做**：不得寫死任何「正反例由 t0 條件決定」類之 scenario 專屬文案（D-7 通則化）。
- **邊界**：① 改任一維度 ⇒ 顯示字串隨之改變（前後 `!==`）。
  ② 本頁與 Task 7.6 取用**同一 registry 物件**（斷言同一 exported 參考），
     且兩頁之欄集**不相等**（證明共用的是 registry 而非欄集）。
- **風險緩解**：RISK-(b)。
- **驗證**：`npx vitest run eventExportDisclosure` **≥3 條**（①②③，SPEC L2971–2975）。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（改任一維度 ⇒ 顯示字串隨之改變（前後 `!==`）。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：本 Task **刻意取代** Task 4.1b（後者為其真子集）
  ⇒ 🔴 **移除 4.1b 獨立實作前須逐項比對兩邊揭露項集合並斷言 4.1b ⊆ 7.3**。
  🔴 **須同步**：本 Task 之驗證偵測不到「**新增**維度未被顯示」
  ⇒ 維度涵蓋率由 **Task 7.2 之 enum 對證閘**負責；兩者缺一，日後契約新增維度會靜默不揭露。

### Task 7.4 — 條件 IC decay 之邊界揭露（`票 #3-全棧`）

- **SPEC ref**：L2982–2996　**目標**：與 Task 4.1c **同一文案來源，不得各寫一份**。
- **輸入**：無　**輸出**：匯出面板之說明文字
- **實作要點**：
  1. 明寫 decay **曲線**非本批交付；附帶 `future_*` 欄**不進 `ic_feed``；
     換答案窗請於 **IC 分析頁重跑分析**，**不需重新匯出事件批**。
  2. 🔴 與 Task 4.1c 之文案來自**同一 exported 常數／formatter**
     ——兩處**不得各寫一份**（第二份副本必漂移）。
  3. 文案掛在匯出面板之揭露區塊（與 Task 7.3 同區），**不另開對話框**；
     GAP-6 交付 multi-horizon IC 時**整段撤除**（見「存活至」）。
- **修改檔案**：與 Task 4.1c 同一常數（`frontend/src/lib/` 之揭露文案模組）
  **既有 caller**：匯出面板
- **不可做**：不得讓使用者以為多選附帶欄就會得到多條 IC。
- **邊界**：① 選附帶欄 `[1,3,7]` ⇒ `window.horizon_bars` **不變**。
  ② 文案中**不得**出現「重新匯出」作為換 h 之手段。
- **風險緩解**：RISK-(b)。
- **驗證**：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；
  vitest 斷言說明現於匯出面板 ＋ 邊界①② ＋ **②同一參考**之斷言。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（選附帶欄 `[1,3,7]` ⇒ `window.horizon_bars` **不變**。）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**GAP-6**（屆時若交付 multi-horizon IC 則撤除）。
- **覆蓋風險**：GAP-6 可能取代。

### Task 7.5 — 事件後報酬表正／反／全體三組（`票 #3-全棧`）

- **SPEC ref**：L2997–3062　**目標**：三組**垂直排列**，掛在 `strata.by_label`。
- **輸入**：事件表 ＋ `control_kind`　**輸出**：`strata.by_label` 三組
- **實作要點**：
  1. 🔴 回傳頂層仍為 §G S-1 之**八鍵**；三組寫入 `strata.by_label`，
     鍵集固定恰為 `positive`／`negative`／`all`。
     **不得**新增第九頂層鍵、**不得**以三次呼叫各產一表代替。
  2. 🔴 **`control_kind` 之全體組規則**（四列，見 SPEC L3008–3013）：
     `user_labeled_same_trigger`／`platform_same_trigger_rule` ⇒ **正常計算**；
     `user_labeled_other` ⇒ `not_computed`／`control_kind_not_comparable`；
     批內 distinct 值 `> 1` ⇒ `not_computed`／`mixed_control_kind_in_batch`，
     **不取多數決**。
  3. 🔴 **兩個 reason 須先登記契約**：於
     `momentum/Analysis/contracts/ic_report_contract.json` 之 `report_sections` 新增
     `event_return_table` 物件（`not_computed_reasons`／`group_status_object_keys`）。
     ⚠️ 此為**表格層** reason，**不得**混入 Task 6.0 之 `reasons.analysis_rejected`。
  4. 🔴 **`control_kind` 之唯一傳遞點＝`build_event_manifest` 之 manifest context**
     ——現行 `dedupe.py:112-115` 之 merge 清單**無 `control_kind`**，
     `tables.py:88-93` 亦不收原始事件表 ⇒ 於該 merge 清單加入 `control_kind`，
     表格層一律由 `manifest.table` 取用。
     **禁止**另建第二份事件索引；**禁止**在表格層寫死或讀不到時當 `None` 放行。
  5. 狀態塊形狀見 §G **S-7a**（恰兩鍵），本 Task **不重述**。
- **修改檔案**：
  - `momentum/Analysis/event_samples/tables.py::event_forward_return_table()`（三組）
  - `momentum/Analysis/event_samples/dedupe.py:112-115`（manifest merge 清單加 `control_kind`）
  - `momentum/Analysis/contracts/ic_report_contract.json`（`report_sections.event_return_table`）
  - `frontend/src/components/`（`EventTablesPanel` 改讀 `strata.by_label`）
  **既有 caller**：`pipeline.py`；`EventTablesPanel`（🔴 現行只讀 `sensitivity_micro`）
- **不可做**：不得因分組而改變 `n_eff` 或 bootstrap 之定義；不得在表格層寫死 `control_kind`。
- **邊界**：① `positive`／`negative` 兩組之統計值在**三種 `control_kind` 下 byte 級相同**
     （證明 `control_kind` **只影響 `all`**）。
  ② 🔴 **前端實際顯示三組**——`EventTablesPanel` 垂直排列三組，
     `all` 為 `not_computed` 時顯示其 `reason` 而非空表。
     **本 Task 之驗收不得只有 backend pytest**（後端全綠仍可能前端顯示舊的單一組＝靜默失效）。
- **風險緩解**：RISK-(a)(b)——全棧三欄稽核之直接落點。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k return_table_by_label` **≥10 條**
  （①–⑩，SPEC L3029–3046）＋ `npx vitest run eventTablesPanelByLabel` **≥3 條**（⑪）。
  **mutation 六條**（SPEC L3047–3050）。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：與 Task 4.2 同一表格 ⇒ **兩者須合併實作（4.2 先）**。
  🔴 **須同步（兩件分開的事，勿混）**：
  (a) 新增 `strata.by_label` ＝**已核准之結構／數值輸出變更（D-4）**
      ⇒ **須同一 commit 依 §G S-9 重建 G-2 golden 並在 commit message 說明**，
      且新 golden 須以 §G S-8 之**獨立 oracle** 驗證，**不得以被測函式自產**。
  (b) 於 `dedupe.py` 加 `control_kind` 欄 ⇒ 該加欄**不應**改變 G-2 bytes
      （manifest 本身不進輸出）⇒ 仍須保留「加欄前後 G-2 byte 級不變」之回歸；
      若真變了代表加欄意外進了輸出，**須查明而非重凍**。

### Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（`票 #3-全棧`）

- **SPEC ref**：L3063–3174　**目標**：把「批次設定」拆成**兩類**——
  **批次事實欄（唯讀）** vs **分析參數（可設定、只作用於本次分析、不回寫）**。
- **輸入**：事件批 detail　**輸出**：唯讀揭露區 ＋ 分析參數區
- **實作要點**：
  1. **① detail 端點**回傳該批之五維度實際值。
  2. **② 批次事實欄唯讀揭露**——文案與 Task 7.3 共用**同一欄位級 formatter registry**，
     但**欄集各自選取**（兩頁欄集不同）。
  3. **③ 分析參數區**——`event_label_spec` 之四欄；
     🔴 可操作集合**仍鎖 F-1′**（其餘值 disabled ＋顯示 F-5′ 之開放前置理由），
     機制**沿用** Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`（路徑鍵新增 `'/ic-analysis'`），
     **不另創第四種機制**。
- **修改檔案**：`api/routes/case.py::get_event_import`（detail 回應增欄）；
  `frontend/src/app/ic-analysis/page.tsx`（唯讀揭露區＋分析參數區）；
  formatter registry（與 7.3 共用）
  **既有 caller**：IC 分析頁
- **不可做**：不得只在 tooltip 顯示 `importId` 就算揭露（使用者要的是**語意**，不是識別碼）；
  分析參數**不得回寫**事件批。
- **邊界**：① 🔴 **批次事實欄不可編輯**——斷言其 DOM 節點**無可輸入控制項**
     （`queryByRole('combobox'|'textbox')` 為 `null`）。
  ② detail 回應之批次事實欄鍵集**集合相等**於 `{scenario, control_kind, direction, t0, label}`，
     且**另含** F-0 種子三鍵 `{entry_price_semantic, label_return_mode, decision_offset_bars}`。
- **風險緩解**：RISK-(b)。
- **驗證**：pytest 一組（①②③，SPEC L3133–3140）＋ vitest 一組（①②③，SPEC L3146–3150）；
  ⑤守 `/ic-analysis` 之可操作集合。
  🔴 **mutation（V-M；本 Task 之可證偽性）**：移除或反轉本 Task「邊界①」所述之保護（🔴 **批次事實欄不可編輯**——斷言其 DOM 節點**無可輸入控制項**）⇒ 邊界① 之斷言**須轉紅**；還原後轉綠。receipt 路徑入 commit message。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**。🔴 驗收改以**明列鍵名之集合相等**（R4 版之計數寫法已被兩家命中）。

### Task 7.7 — Feature run `time_range` 與事件期之對證（`票 #3-全棧`）

- **SPEC ref**：L3175–3406　**目標**：`RunInfo` 補 `time_range`，並在分析前對證
  「特徵 run 是否涵蓋事件期」，不涵蓋即 fail-closed。
- **輸入**：`RunInfo.time_range`、事件窗、`timeframe_seconds`
  **輸出**：gate 通過或 `ValueError`
- **實作要點**：
  1. **① wiring**：`RunInfo.time_range: Optional[dict]`，形狀與 manifest **同形**
     `{"start": str|None, "end": str|None}`。
     🔴 **型別依實碼裁定**：`_resolve_l7_v2_time_range` 回傳 `Dict[str, Optional[str]]`
     ⇒ **值為字串，不是 epoch 毫秒整數**；實測現存 manifest 皆為 **epoch 秒數字字串**。
     `_browse_metadata_for_run` 由 manifest **原樣帶出（禁在此層轉型別）**；
     `/features/runs` response 與前端 `types.ts` 之 `RunInfo` 均須含此鍵。
  2. **② 時間基準**：`bar_ms(e) = timeframe_seconds[e.timeframe] * 1000`，
     🔴 其中 `timeframe_seconds` **即 §G G-3 ⑥(d) 注入之同一 map**
     ——**禁**在本 gate 內直讀 `momentum/core/constants.py::TIMEFRAME_SECONDS`。
  3. 🔴 **取得點（唯一）**：`_run_analysis` 事件分支，於**匯入驗證通過後、
     prepare-windows 之前**建構**一次**，以**同一物件**傳入 `purge_lower_bound_ms` 與本 gate；
     驗收以 **`is` 比對**（角色卡 (b) 之物件參考比對）。
     **禁**各自建構、**禁**「等位元組拷貝」之並列寫法。
  4. **③ gate 函式**：`check_feature_run_coverage(*, timeframe_seconds, feature_manifest_time_range,
     event_windows) -> None`——🔴 **本 Task 須新建**（現行碼字面數＝0）；
     由 `_run_analysis` 於 `prepare_analysis_windows` 之後、`apply_event_coverage` 之前
     以 **keyword-only 呼叫一次**；不符 ⇒ `ValueError`。
     **禁** `pipeline._assert_feature_run_covers_events`、禁 `args[N]`、禁未具名掛載、禁第二入口。
- **修改檔案**：
  - `api/models/feature_factory_models.py`（`RunInfo` 增 `time_range`，:116-133）
  - `api/services/ic_analysis_service.py`：新建 `check_feature_run_coverage()`；
    `_run_analysis` 事件分支之編排
  - `frontend/src/lib/types.ts`（`RunInfo` 增 `time_range`）
  **既有 caller**：`_browse_metadata_for_run`；`/features/runs`
- **不可做**：不得在 service 層轉型別；不得直讀 module 常數；不得開第二入口。
- **邊界**：① 特徵 run **不涵蓋**事件期 ⇒ fail-closed（非警告）。
  ② `timeframe_seconds` 之兩個 consumer 收到**同一物件**（`is` 為 `True`）。
- **風險緩解**：RISK-(a)——這是「特徵 run 根本不涵蓋事件期卻照送 IC」之直接對策。
- **驗證**：`pytest tests/api -q -k feature_coverage_gate` rc=0，條目數 `>=` SPEC 所列；
  containment 之唯一定義見 SPEC Task 7.7。
  🔴 **前端那一欄（Phase 7 之硬性要求，backend 全綠不算完成）**：
  `npx vitest run runInfoTimeRange` **≥2 條**——①`RunInfo` 型別含 `time_range` 且
  形狀為 `{start: string|null, end: string|null}`；②`/features/runs` 之回應經前端解析後
  `runs[0].time_range` **不為 `undefined`**（證明鍵有真的傳到前端，非只改型別宣告）。
  **mutation**：把 `time_range` 從 `types.ts` 之 `RunInfo` 移除 ⇒ ①須紅；
  service 層改為不帶出該鍵 ⇒ ②須紅。
- **存活至**：**Phase 7（終）**。
- **覆蓋風險**：**無**。

---

**Phase 7 測試（三層）＋ Phase Gate**

- **後端**：`pytest tests/momentum/event_samples/ -q -k "analysis_label_producer or
  return_table_by_label"` ＋ `pytest tests/api -q -k "event_analysis_horizon_purge or
  event_batch_detail_dims or feature_coverage_gate"`
- **前端**：`npx vitest run eventExportOptions eventContractOptions contractEnumWiring
  eventExportDisclosure eventTablesPanelByLabel icEventBatchDisclosure` ＋ `npm run build`
- **全棧三欄**：🔴 每個 Task 之驗收**必須含前端那一欄**——backend pytest 全綠不算完成
  （Phase 7 之病因即「後端有、前端沒接」）。
- 🔴 **Phase Gate**：上列三層 rc=0，**且** V-11／V-13／V-14／V-15／V-16／V-17 對應條目全綠，
  **且** G-2 golden 之任何改變皆已於 commit message 依 D-4 說明並以 S-8 獨立 oracle 驗過，
  **且**本 Phase 全部 mutation 逐條實跑轉紅並還原轉綠。
