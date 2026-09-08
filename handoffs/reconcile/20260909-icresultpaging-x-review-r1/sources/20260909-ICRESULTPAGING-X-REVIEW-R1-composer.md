brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R1
family: composer
findings-round: R1
標的：`docs/ICRESULT_PAGING_SPEC.md`、`docs/ICRESULT_PAGING_TODO.md`（**尚未實作**）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 兩份文件 template | **fact-verified** | `bash scripts/template_check.sh spec|todo` → TEMPLATE PASS, rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}` |
| **`ASSUME-1`**：completed 後僅 refilter 改寫 `task_info["result"]` | **部分成立** | `grep` → 寫入點 `:1623`（主分析完成）、`:2339`（含 deep_analysis 完成）、`:2631`（refilter）；分頁中途僅 refilter 會換整份 result，但 deep 完成亦會覆寫 → P1-02 |
| **`ASSUME-2`**：前端無元件讀 per-feature 段全量 map | **fact-verified** | `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` → 僅 pattern comparison 元件，與 IC 報告無關 |
| G-5 light ≤2MB 與 G-4 逐鍵保留可同時成立 | **推翻** | 實機段 `filter_log` 3.28MB、`grouped_ic` 9.74MB、`metadata.selection_scope` 3.27MB（刪 per-feature 四段後仍遠超 2MB）→ P0-01 |
| 後端 `_finite_or_neg_inf`＋次鍵與前端 `getSortValue` 同序 | **推翻** | 39k 報告 **全部** `icir=null`（0 個有限值）；前端 tie 回傳 0（保 insertion order）、後端次鍵 `feature_name` → 首列必變 → P1-01 |

---

## 必答（成對 verdict）

### 1a／1b 預設 `/result` 位元組級不變

- **1a（仍可能改變預設回應的一種方式）**：`get_result` 實作若在 `view is None` 時誤走 `project_light_view`，或共用序列化路徑對 dict 做 copy／重排鍵序（即使 `deny_factor_in_ok_oos` 順序正確也會變 canonical sha）。現 route **無** `response_model`（`api/routes/ic_analysis.py:346-353`），加 `view` query 本身不必然變 bytes；風險在 service 分支。
- **1b（G-1 能否抓到）**：**能**——`§G` B-1 `report_canonical_sha` 對預設 `/result` 位元組級比對；mutation P6「預設誤套 light」亦對應。抓不到的是「OpenAPI 文件漂移」類非 bytes 問題（本票不宣稱）。

### 2a／2b light 刪段＋metadata 白名單

- **2a（前端仍讀但會被刪的鍵）**：依 Task 0.1「非描述子全保留」演算法，**不會**刪 `event_filter`／`oos_downgrade`／`period_alignment`／`isolation`（`DegradedBanner`／`PeriodAlignmentBanner`／`IsolationNote`／`MarginalICTable` 消費）。`EventBatchDisclosurePanel` **不讀** `report.metadata`（吃 `config`／`disclosure` prop）。per-feature **metadata 描述子**會刪，但前端未直接讀描述子 map。
- **2b（應刪未列、致 G-5 超標）**：`filter_log`（3.28MB）、`grouped_ic`（9.74MB）、`metadata.selection_scope`（3.27MB）——G-4 要求 light 與全量**逐鍵相等**保留，卻使 G-5 ≤2MB **數學不可達**（見 P0-01）。`turnover_analysis` 等 per-feature 段已列刪除，非此矛盾主因。

### 3a／3b 排序同序

- **3a（同序？反例）**：**不同序**。後端：`paginate_summary` 次鍵 `feature_name`（SPEC Task 1.1／TODO 1.1）。前端：`ICSummaryTable.tsx:91-106` `aVal===bVal` ⇒ `return 0`，無次鍵；`feature_name` 欄位經 `isFiniteNumber` 全變 `-inf`。UAT 報告 39,346 列 `icir` **全 null** ⇒ 排序完全由 tie-break 決定：前端保 `summary_table` 生成序，後端保字母序 ⇒ **第一可見列必變**（行為變更）。
- **3b（哪邊對）**：後端次鍵 `feature_name` 較可預測、可測（G-2）；前端現行 tie=0 在 39k 事件路徑下等於「隨機首列」。SPEC 應**明訂**切換後以後端序為準，並在 §G 加「預設 icir desc＋次鍵 feature_name 下首列 feature_name」回歸（或接受行為變更並寫入 B34）。

### 4a／4b G-2／G-3 與 refilter 競態

- **4a**：G-2 只寫「`limit=max` 逐頁串接 == 全量 `summary_table` 同鍵排序」，**未定義** `q`／`pass_class` 篩選下「全量」指篩前或篩後集合；refilter 以整份新 `report` 替換（`:2631`）但 summary API **無** `result_revision`／ETag，in-flight 第 N 頁可能混舊新兩份 result（Task 2.1 只重置 `offset=0`，不 abort 進行中請求）。
- **4b（不做版本戳代價）**：門檻 refilter 期間表格短暫顯示過期列、勾選 Set 與實際倖存者不一致；無法寫可證偽測試覆蓋競態。

### 5a／5b Task 2.3 匯出

- **5a（逐頁 vs 既有端點）**：**JSON／CSV／Markdown／HDF5 應走既有** `GET /api/v1/ic/export/{task_id}/{format}`（`ExportButtons.tsx:64-66` → `export_analysis` 讀完整 `task_info["result"]`，`generate_summary_csv` 用全量 `summary_table`）。逐頁 79 次 `summary?limit=500` **多餘且更慢**。僅「全部 PNG」依 `summaryTable` prop（`:201`），light 後需改為當頁或停用——與資料匯出無關。
- **5b（39k 逐頁 UI 時間）**：79 次序列化請求（TODO 禁併發）粗估 79×(RTT+投影) ≈ **數十秒～數分鐘**級，劣於單次 `csv_summary`；不應作預設匯出路徑。

### 6 ≥10× 不必要複雜

**無**。Task 0.1 的 200 特徵等距抽樣對 39k 規模合理（G-3 全量 sha 仍覆蓋集合）；contract JSON 為 Rule 5 單一來源必要物。B0 golden 不可再縮成固定 5 列而不失 G-1/G-3 覆蓋。

### 7 B2 一次切換／IP-RESID 三值

- **風險**：**先上 Phase 1 後端、前端仍打全量 `/result`** 可零風險驗 G-1；**最小有效前端**＝Task 2.1 light＋2.2 分頁（否則仍下載 118MB）。Task 2.3 可與 2.1/2.2 **拆 commit**（匯出已走後端）。B2「切一半中間態」主要指 light 已開但表格仍全量 DOM——**2.1+2.2 同批必要，2.3 非必要**。
- **IP-RESID-1/2**：`blocked-by` 落檔格式成立；本票不動 reporter。
- **IP-RESID-3**：`schema_version=2` 預設關、前端未呼叫（§A FACT-RECEIPT）；v2 僅 `top_n_summary`+artifact，**不能**取代 light＋feature detail 圖表路徑 ⇒ **並存合理**，非本票取代；待 v2 消費者出現再統一 API 面。

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | G-4 逐鍵保留 vs G-5 ≤2MB → P0-01 |
| 2 漏項 | G-2 篩選語意、refilter 版本戳、匯出路徑分流 → P1-02、P1-03 |
| 3 不可測 | G-5 有 bytes 門檻但與 G-4 衝突致永紅 |
| 4 quant | 投影不重算，無 leakage；排序變序為 UX 行為變更 |
| 5 過度工程 | Task 2.3 逐頁匯出對 JSON/CSV 過度 → P1-03 |
| 6–11 | OOM 靠分頁/light 合理；cache N/A；§N 三殘留理由成立 |

---

## COMPOSER-R1-P0-01

**斷言**: G-4 要求 light 保留 `filter_log`／完整 `grouped_ic`／`metadata` 非描述子鍵（含 `selection_scope`）與全量**逐鍵相等**，與 G-5「39,346 特徵 light canonical JSON ≤ 2 MB」在實機報告上**互斥**，按現 SPEC 實作 G-5 必永 FAIL。

**碼證**: `jq -c '{filter_log:(.filter_log|tojson|length), grouped_ic:(.grouped_ic|tojson|length), selection_scope:(.metadata.selection_scope|tojson|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"filter_log":3282724,"grouped_ic":9745299,"selection_scope":3273340}`（單三段已 16.3MB）；SPEC §G G-4／G-5；Task 1.3／0.1 `metadata_keep_keys` 演算法。RECHECK: 實作 `project_light_view` 後對 fake task 載入同檔量 canonical bytes。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[BLOCKING] 信心度=High。修法（二選一）：①放寬 G-4——light 只保留 UI 必要段（`filter_log` 摘要、`grouped_ic` 聚合層、`selection_scope` 改 `scope_id` 摘要或移出 light）；②放寬 G-5——改為「首屏可互動」延遲指標（B34）為主、bytes 門檻僅對 `summary_page`+`feature/{name}`。不可雙標逐鍵相等又 ≤2MB。

---

## COMPOSER-R1-P1-01

**斷言**: 後端 `paginate_summary` 次鍵 `feature_name` 與前端 `ICSummaryTable` `getSortValue`（tie 回傳 0、字串欄位全 `-inf`）不同序；UAT 39k 報告 `icir` 全 null 時，**使用者首列必變**，SPEC 未宣告此行為變更亦無 §G 釘選。

**碼證**: `ICSummaryTable.tsx:91-106`；`momentum/Analysis/ic_reporter.py:23-29` `_finite_or_neg_inf`；`jq '[.summary_table[].icir]|map(select(.!=null))|length' data_cache/reports/ic_report_ic_gatekeeper.json` → `0`；SPEC Task 1.1「次鍵 feature_name」。RECHECK: 對同報告比對前端 desc icir 首列 vs `/summary?sort_by=icir&order=desc&limit=1` 首列 `feature_name`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MAJOR] 信心度=High。修法：§G 增 G-6「icir 全 null 時首列 `feature_name` 等於 paginate 結果」；或 SPEC §C 明訂「分頁序取代前端本地序」並更新 B34 預期。實作時 `sort_by=feature_name` 須用字串比較，不可走 `_finite_or_neg_inf`。

---

## COMPOSER-R1-P1-02

**斷言**: G-2 未定義 `q`／`pass_class` 下「逐頁串接==全量」的基線集合；refilter 替換 `task_info["result"]`（`:2631`）卻無 result 版本戳，summary 分頁 API 無法偵測 stale 頁，與 Task 2.1「refilter 重置 offset」不足以消除 in-flight 競態。

**碼證**: SPEC §G G-2；`api/services/ic_analysis_service.py:2627-2637`；TODO Task 2.1 邊界③。RECHECK: refilter 中途並發兩個 `/summary?offset=0` 與 `offset=50`，比對 `total`／首列是否一致。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：G-2 分兩條——無篩選串接==全量；有篩選串接==同參數單次 materialize。light／summary 回應加 `result_revision`（config_hash 或 refilter 計數）；前端 refilter 後 abort 全部 summary/detail 請求。

---

## COMPOSER-R1-P1-03

**斷言**: Task 2.3 要求 `ExportButtons` 以 `summary?limit=limit_max` 逐頁串接匯出，但現行 JSON／CSV 已走 `/export/{task_id}/{format}` 全量後端路徑；照 SPEC 改逐頁會**降級**匯出且與 §C 不變式 1（匯出走完整 result）精神衝突。

**碼證**: `ExportButtons.tsx:46-66`（`triggerDownload` → `/api/v1/ic/export/...`）；`api/routes/ic_analysis.py:649-656`；`ic_analysis_service.py:1961-1967` `generate_summary_csv` 讀全量 `summary_table`；SPEC Task 2.3／TODO 2.3「逐頁串接」。RECHECK: `rg "summaryTable" frontend/src/components/ic-analysis/ExportButtons.tsx` → 僅 PNG 按鈕用 prop。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：Task 2.3 改寫——`csv_summary`／`json`／`markdown`／`hdf5` **維持**既有 export 端點（讀預設 `/result` 全量，G-1 保護）；light 後僅調整 `module_statuses` prop 來源。刪「79 次請求」驗收，改斷言 export 端點仍 200 且列數==`total_features`。

---

## COMPOSER-R1-P2-01

**斷言**: TODO §B B2 稱 2.1+2.2+2.3 必須一次切換，但 2.3 匯出與後端 export 重疊，可延後；真正中間態風險僅「light 已開但表格仍全量」——**2.1+2.2 同批即可**，不必捆 2.3。

**碼證**: `docs/ICRESULT_PAGING_TODO.md` §B B2 合併理由；`ExportButtons.tsx` 現況（見 P1-03）。RECHECK: 評估 B2 拆為 `{2.1,2.2}` + `{2.3}` 兩 commit 是否仍滿足 B34。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MINOR] 信心度=Medium。修法：§B 表註明 2.3 可跟隨 2.1/2.2 之後獨立合併；合併理由限縮為 hook+表格。

---

## Verdict：需修補後派工

P0-01（G-4∩G-5）必先解——否則 Phase 1 Gate 尺寸測試與 UAT B34 無一致通過標準。P1 修排序宣告、G-2 篩選語意、refilter 版本戳、匯出路徑分流後可進 B0。IP-RESID 三殘留理由成立；`IP-RESID-3` 並存可接受。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS, rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `jq` 段尺寸（filter_log／grouped_ic／selection_scope） | 見 P0-01 |
| `jq` icir 非 null 列數 | `0`（見 P1-01） |
| `grep -n 'task_info\["result"\]' api/services/ic_analysis_service.py` | `:1623` `:2339` `:2631` |
| `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` | 僅 pattern comparison，IC 無全量 per-feature 讀取 |

---

ASSUMPTIONS_VERIFIED: 模板 PASS；39k jq；ASSUME-1/2 覆核；G-5 與 G-4 實機段尺寸；排序/icir 分布
TESTS_RUN: 見 VERIFY 表（未跑 pytest tests/governance；未改碼）
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查；標記 G-5 門檻與實機矛盾）
產出檔: handoffs/20260909-ICRESULTPAGING-X-REVIEW-R1-composer.md

STATUS: DONE
