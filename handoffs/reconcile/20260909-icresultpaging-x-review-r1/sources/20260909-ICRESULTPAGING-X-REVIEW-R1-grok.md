# ICRESULT_PAGING SPEC＋TODO adversarial review R1（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R1  
family: grok  
findings-round: R1  
標的: `docs/ICRESULT_PAGING_SPEC.md`／`docs/ICRESULT_PAGING_TODO.md`（尚未實作）  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#cd1471b99995  

---

## Verdict：需修補後派工

本輪有 **1 個 P0**（G-4 與 G-5 在 39k 實機報告上互斥，Phase 1 無法同時綠）＋數條 P1／P2。方向（後端投影＋前端伺服器分頁、不動落檔／orchestrator）正確，但 light 刪留清單與 2 MB 預算、以及 Task 2.3 匯出設計須先改文件再進 B0。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r1-baseline.sha`（rc 直接取、未經 pipe） | **rc=1**；2210 OK／**2 FAILED**＝`docs/ICRESULT_PAGING_SPEC.md`、`docs/ICRESULT_PAGING_TODO.md`（baseline 期望 `fad4ec16…`／`2fe9f02c…`；工作區現為 `ee307ca7…`／`cd1471b9…`）。本輪唯讀未改檔；漂移供主委核對。 |

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：三處賦值＝analyze `:1623`、full-analysis `:2339`、refilter `:2631`；前兩者在 status→completed 當下寫入，之後僅 refilter 覆寫 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys(report`／`Object.entries(report` 無 IC 命中；`page.tsx` per-feature 四段皆 `activeFeature` 單鍵。pattern 頁 `Object.entries(report.engine_performances)` 非本票 |
| `metadata.selection_scope` 消費者 | **fact-verified**：寫入 orchestrator；survivor 只取 `scope_id`；`frontend/src` **無**讀取；api services／hooks／store **無**讀取 |
| 既有匯出端點 | **fact-verified**：`GET /export/{task_id}/{format}` 含 `csv_summary`；`ExportButtons` 已打此端點（見 P1-02） |
| 無 `response_model` 時加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`、回 dict；加 `Query(None)` 理論上不改 body。G-1 才是機器證據（Phase 1） |

---

## 必答（成對；逐條有碼證）

### 1a. 預設 `/result` 位元組級不變：SPEC 照做仍可能改變它的一種方式

**有。** 現行 `api/routes/ic_analysis.py:347` 無 `response_model`，service 回 `_to_json_compatible` 後的 dict。照做時仍可能變的路徑：

1. `view` 預設誤判（例如把缺省當 light、或 `Optional` 預設字串非 `None`）⇒ 預設走 `project_light_view`。  
2. 為 light／新模型顺手幫 `get_result` 加上 `response_model` ⇒ Pydantic 丟未宣告鍵／改序列化。  
3. 把 `deny_factor_in_ok_oos` 挪到投影之後、或對預設路徑多跑一輪 normalize／key sort。

### 1b. 反向：G-1 golden 能否抓到？

**能抓多數、非全部。** G-1＝預設回應 canonical sha == B-1。誤套 light、多刪鍵、normalize 改字面 ⇒ 紅。抓不到的：只改 OpenAPI／簽名不動 body；或非決定性鍵序若 scrub 與 golden 同規則會偶合（低風險）。結論：G-1 必要但須搭配「無 view 時零分支」的單元斷言（TODO mutation P6 方向對）。

### 2a. light 刪段＋metadata 白名單：前端仍在讀但會被刪的鍵

**依現行「非描述子＝保留」啟發式，下列前端鍵會被保留（若報告有寫）**：`event_filter`、`oos_downgrade`、`isolation`、`period_alignment`、`ic_window_disclosure`、`n_timestamps`、`n_symbols`、`mode`（page／DegradedBanner／IsolationNote／PeriodAlignmentBanner）。本機 39k 報告實際有：`event_filter`、`ic_window_disclosure`；`isolation`／`period_alignment`／`oos_downgrade`／`n_*`／`mode`＝ABSENT（事件／對齊未觸發）。

**真正會壞的是「該瘦卻當保留」**：`metadata.selection_scope`（3,273,340 bytes；`universe_features`／`evaluated_features` 各 ~39k 名）——啟發式會留、G-5 必爆；前端不讀。另：G-4 要求 `filter_log` 全段逐鍵相等，但 `FilterFunnelChart` 型別只要每階段 `input`／`output` 數字（且與實機 `input_features` 形狀本就不一致）——全量 3.28 MB 對 UI 無增益。

### 2b. 反向：該刪卻沒列進刪段、會讓 G-5 超 2 MB 的段

**`filter_log`（3,282,725 B）** 與 **`grouped_ic`（~9.7 MB；`by_year` 單層即 4.86 MB×39,346 特徵）**。SPEC／TODO 把二者列為 light 保留（G-4「逐鍵相等」／Task 1.3「原樣」），卻又要求 G-5 ≤ 2,097,152。實測投影下界：

| 組合 | canonical JSON bytes（venv 實測） |
|---|---|
| 保留 filter_log＋grouped_ic＋瘦 metadata | ~13,054,965 |
| 去 grouped_ic、留 filter_log | ~3,309,731（仍 > 2 MB） |
| 去二者＋無 selection_scope | ~26,997 |

⇒ **只要 G-4 堅持全量 `filter_log`，G-5 在此實機報告上不可達。**

### 3a. 排序：`_finite_or_neg_inf`＋次鍵 vs 前端 `getSortValue`——同序？

**不同序。**  

- 前端 `ICSummaryTable.tsx:91-106`：非有限 → `Number.NEGATIVE_INFINITY`；`aVal===bVal` → `return 0`（**無** `feature_name` 次鍵；現代 JS stable ⇒ 保留輸入相對序）。  
- 後端既有 `get_top_features`：`key=_finite_or_neg_inf(...)`，**無**次鍵（`ic_filter_orchestrator.py:2969-2972`）。  
- SPEC Task 1.1：主鍵 `_finite_or_neg_inf`＋次鍵 `feature_name`。

反例（desc）：列序輸入 `[b:None, a:None, c:0.5, d:0.5]`  

- 前端穩定序 ≈ `[c, d, b, a]`  
- SPEC 次鍵名（`-icir, name`）⇒ `[c, d, a, b]`（None 並列時 `a` 先於 `b`）

首屏第一列在大量同 icir／全 None（事件路徑）時會變。

### 3b. 若不同序，哪邊才是對的？

**後端決定性次鍵較對（分頁／跨頁穩定），但屬可見行為變更，須在 SPEC 明示。** None／NaN 沉底與前端一致（都映射 -inf）；爭議只在並列打平。建議：文件寫明「與舊前端 stable 序不同；以 `feature_name` 升序為並列次序」，並用固定並列 fixture 測 G-2，避免 agent 用 `reverse=True` 元組誤把次鍵也反轉。

### 4a. G-2／G-3 在 refilter 換 result 後的語意；競態

completed 後只有 refilter 換 `task_info["result"]`（上表）。G-2／G-3 定義在**單一不變 result 快照**上「投影∪＝全量」。refilter 中：頁 A 用舊 result、頁 B 用新 result ⇒ 串接既不等於舊全量也不等於新全量；`q`／`pass_class` 下 `total` 亦可能中途跳變。SPEC **未**定 version／etag／generation。

### 4b. 不做版本戳的代價

使用者翻頁／匯出串接時可能得到混代列、重複或遺漏；除錯時 G-2 失敗無法區分「投影 bug」vs「競態」。最低代價替代：前端 refilter 時 abort 所有 in-flight summary／feature 請求並 `offset=0`（TODO 2.1 有重置 offset，**未**寫 abort 分頁請求）；或回應帶 `result_generation` 整數、客戶端發現變更即丟棄頁面。

### 5a. Task 2.3 匯出：逐頁 vs 既有端點，哪個對？

**既有後端端點對；逐頁 79 次是錯的／多餘。** 碼證：

- `api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`  
- `ic_analysis_service.export_analysis` `:1961` `csv_summary` → `reporter.generate_summary_csv(payload_for_export)`，payload 來自 **記憶體內** `task_info["result"]`  
- `ExportButtons.tsx:64-66` 已 `fetch(/api/v1/ic/export/${taskId}/${format})`；`summaryTable` 只用在 PNG 按鈕 disable（`:201`），**不**用於 CSV  

TODO 2.3 改「內部 `fetchSummaryPage` 逐頁拉齊」會在前端重做後端已有的事，且 39k×79 往返更慢、更易與 refilter 競態。

### 5b. 逐頁匯出 39k 列在 UI 的可接受時間

若真走 79 次序列化 HTTP（limit_max=500）：即使每次 50–200 ms，也要 **4–16 秒**量級，差網路更長；需進度條且仍不如一次 `/export/.../csv_summary`。可接受上限應 ≪ 串接方案——故不應採納。

### 6. ≥10× 不必要複雜？

**部分是。**  

- Task 0.1：200 特徵等距抽樣＋多段 sha 對 G-3 合理，可再縮（例如固定 20 個具名 fixture 特徵＋全量 feature-set sha）而不失證偽力。  
- contract JSON 作白名單 SoT：**值得留**。  
- Task 2.3 逐頁匯出：**≥10× 多餘**（見 5a）。  
- B2 把 2.3 與 2.1／2.2 綁死：理由「切一半會 light 缺段又沒分頁」對 **2.1＋2.2** 成立，對 **2.3 重做匯出**不成立。

### 7. B2 一次切換 vs 先只換表格；殘留三值；IP-RESID-3

- **風險較小路徑**：B1 後先做 **2.1（fetch light）＋2.2（表格伺服器分頁）**；匯出維持既有 `/export`（只改 props 型別／`canExportData` 依賴 `reportLight`）。「先只換表格、仍下載 119 MB」**不能**解 UAT 凍結，故不可取。  
- **IP-RESID-1**：blocked-by 改 reporter／落檔＋golden ⇒ **成立**（本票紅線②）。  
- **IP-RESID-2**：同落檔格式 ⇒ **成立**。  
- **IP-RESID-3**：`schema_version=2` 預設關、前端無呼叫（SPEC §A FACT-RECEIPT）——**並存可接受**（user-ruling 2026-06-25），但應在 SPEC 寫明「UI 消費以 light 為準；v2 僅 artifact／top-N 契約，不取代本票」。**不必本票刪除 v2**；互斥 400 已足夠。若日後無消費者，另票 deprecate。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **有**——G-4 保留全量 filter_log／grouped_ic vs G-5 ≤2MB（P0-01） |
| 2 | 漏項 | refilter 競態未定 generation；metadata 保留鍵未顯式列出前端鍵（啟發式可救但 selection_scope 誤留） |
| 3 | 不可測 | G-1～G-5 可證偽，但 G-5 與 G-4 同時不可滿足 ⇒ 驗收矩陣自相矛盾 |
| 4 | quant | 不改數值／落檔——無；排序次鍵為 UX 序變更非數值 |
| 5 | 過度工程 | Task 2.3 逐頁匯出；B2 綁死 2.3 |
| 6 | OOM | light 若照 G-4 仍可能數 MB～十 MB，緩解不足 |
| 7 | Cache | N/A（只讀 task result） |
| 8 | API／相容 | 預設路徑不變意圖正確；簽名／response_model 風險見 1a |
| 9 | 測試 | mutation P1–P6 方向對；缺「G-5 與保留段」對實機段位元組的預檢 |
| 10 | Agent 可執行 | Task 夠具體；`grouped_ic`「摘要」語意不清易實作分歧 |
| 11 | 短命工 | 無（各 Task 存活至＝永久）；若 2.3 改回既有 export 則刪「逐頁匯出」設計即可 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| light 保留 filter_log＋非描述子 metadata 仍 ≤2MB | **假（本輪證偽）** | 見 P0-01／必答 2b |
| metadata 非描述子鍵皆應進 light | **假（selection_scope）** | 3.27 MB；UI 不讀 |
| 前端匯出依賴全量 summary_table／需逐頁 API | **假** | ExportButtons 已走 `/export` |
| completed 後只有 refilter 改 result | **真** | 三賦值點 |
| 排序與現行表格同序 | **假** | 次鍵差異 |

---

## GROK-R1-P0-01

**斷言**: SPEC §G G-4（light 保留全量 `filter_log`／`grouped_ic` 摘要並與全量逐鍵相等）與 G-5（39k 實機 light canonical JSON ≤ 2,097,152 bytes）在 `data_cache/reports/ic_report_ic_gatekeeper.json` 上互斥，照做則 Phase 1 無法同時通過。

**碼證**: FACT-RECEIPT 段位元組 `filter_log 3282725`、`grouped_ic 9745300`、`metadata` 內 `selection_scope 3273340`；venv 投影實測留 filter_log 去 grouped_ic ≈ 3,309,731 > 2,097,152；去二者 ≈ 26,997。SPEC §G G-4／G-5；TODO Task 1.3 實作要點③。`RECHECK:` 重跑本檔「必答 2b」表內三組 dumps 長度。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[BLOCKING] 信心度=High。失敗：agent 實作後 G-5 紅或為過 G-5 私自砍 G-4 段造成漏斗／圖表空白。修法：①G-4 改為「漏斗標量投影」（每 stage 只留計數／理由摘要，不留 39k 名清單）且 `grouped_ic` 不進 light（改走 Task 1.2／featureDetail，與 TODO 2.3 圖表方向一致）；②`metadata_keep_keys` **排除** `selection_scope` 或只留 `scope_id`／`n_tests`／`method`／hash；③G-5 門檻對齊修後實測（可仍 ≤2MB）。

## GROK-R1-P1-01

**斷言**: TODO Task 0.1 以「值為 `{category,layer,name}` 描述子以外皆保留」建 `metadata_keep_keys`，會把 3.27 MB 的 `selection_scope.universe_features`／`evaluated_features` 塞进 light，本身即可單獨打破 G-5。

**碼證**: 實機 `selection_scope` keys＝`scope_id,universe_features,evaluated_features,n_tests,method,base_universe_hash,split_label`；兩 list 各 ~39k、字串化各 ~1.63 MB。`frontend/src` 無 `selection_scope` 讀取；survivor 只取 `scope_id`（`survivor_contract.py:598`）。TODO `:26` 啟發式。`RECHECK:` `jq '.metadata.selection_scope|keys' …`＋`grep -rn selection_scope frontend/src`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：contract 顯式列出保留鍵（含前端揭露鍵）並 **deny-list／省略** 大 list；或 light 內 `selection_scope` 瘦身為無 list 的摘要物件。

## GROK-R1-P1-02

**斷言**: TODO Task 2.3 規定 `ExportButtons` 改以 `fetchSummaryPage` 逐頁串接匯出，與現行已可用的後端 `GET /api/v1/ic/export/{task_id}/csv_summary`（讀記憶體 result）重複且更差。

**碼證**: `ExportButtons.tsx:47-66` 已呼叫 `/export/${taskId}/${format}`；`summaryTable` 僅 PNG disable（`:201`）。`ic_analysis_service.py:1961-1967` `csv_summary` 路徑。TODO Task 2.3「逐頁拉齊」「79 頁」。`RECHECK:` 讀上述行號；對 completed task `curl` export（若有 task）應一次回 CSV。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：2.3 改為「匯出繼續走既有 `/export`；只把 props／型別改吃 `ICReportLight`（需 `module_statuses`）；PNG 用 `summaryPage.total>0` 代替全量表」。從 B2 合併理由中移除「匯出必須同批重寫」。

## GROK-R1-P1-03

**斷言**: Task 1.1 排序加 `feature_name` 次鍵後，與現行前端 `getSortValue`（並列 return 0）及 `get_top_features`（無次鍵）不同序，會改變使用者看到的第一列，SPEC 未標為有意行為變更。

**碼證**: `ICSummaryTable.tsx:91-106`；`ic_filter_orchestrator.py:2969-2972`；SPEC Task 1.1「次鍵 feature_name」。反例見必答 3a。`RECHECK:` 四列並列 fixture 比對三實作序。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MAJOR] 信心度=High。修法：在 §C／Task 1.1 寫明「分頁排序以決定性次鍵為準，允許與舊前端 stable 序不同」；禁止 `sorted(..., reverse=True)` 作用於含次鍵的 tuple；測試鎖定並列序。

## GROK-R1-P2-01

**斷言**: SPEC／TODO 未定義 refilter 置換 result 時分頁／G-2 串接的世代語意，存在跨頁混代競態。

**碼證**: `refilter` `:2627-2631` 覆寫 result；TODO 2.1 只重置 `offset=0`，未 abort 進行中的 summary 請求；SPEC §G G-2 無 generation。`RECHECK:` 讀 refilter 與 TODO 2.1 邊界。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MINOR] 信心度=Medium。修法：回應加單調 `result_generation`（或 etag=sha 前 12）；或文件規定 refilter 時前端 abort＋丟棄舊頁，G-2 僅適用單一 generation。

## GROK-R1-P2-02

**斷言**: Task 1.3／G-4 所稱 `grouped_ic`「摘要（非 per-feature 部分）」未定義可機檢形狀，而實機 `grouped_ic.by_year`／`by_category`／`by_layer` 皆為每特徵 map（合計約 9.7 MB），agent 極可能整段原樣保留。

**碼證**: `by_year` bytes≈4,862,625、每 year 鍵數=39346；`page.tsx:225`／`GroupedICBarChart` 依 `featureName` 取單特徵——Phase 2 應改吃 `featureDetail`（TODO 2.3）。`RECHECK:` 對 `grouped_ic.by_year` 任一 year `length`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MINOR] 信心度=High。修法：明文「light **刪除** `grouped_ic` 全段；單特徵投影由 Task 1.2 回 `{group: value}`」；G-4 刪除對 grouped_ic 的逐鍵相等要求。

---

ASSUMPTIONS_VERIFIED: template_check 兩份 PASS；jq 39346/39398；result 三賦值點；export 端點與 ExportButtons 接線；selection_scope／filter_log／grouped_ic 位元組；前端 metadata 消費者清單；排序三路差異  
TESTS_RUN: template_check spec/todo rc=0；jq 形狀；shasum baseline rc=1（僅 SPEC/TODO 2 檔漂移）；venv 投影尺寸三組；grep／讀碼（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: baseline SPEC/TODO hash 與工作區不一致（唯讀未修）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R1-grok.md`

STATUS: DONE
