# ICRESULT_PAGING SPEC＋TODO adversarial review R5（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R5  
family: grok  
findings-round: R5  
標的 commit: `99e986a7`（SPEC R4 修訂＋TODO；尚未實作）  
R4 收斂: `handoffs/reconcile/20260909-icresultpaging-x-review-r4/synth.md` W1–W6  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#54626e187238  

---

## Verdict：需修補後派工

W1–W6 原反例（`order`／150 ms 去抖、rolling page ⑤、LATENCY 文法、int32／32-task、`cache_bytes`、八案例 overlay／重試）**文件層已落地**。本輪**無 P0**；新洞 **2 P1＋1 P2**：W1「寫入時一次正規化＋投影只讀 snapshot」未同步進 Task 1.1／1.3 字面（仍寫 `lock 內取 result`、仍寫投影前 `deny_factor_in_ok_oos`），agent 照 Task 實作會繞過 §C-7／P15 意圖；Task 2.1 `ICReportLight` Omit「四段」未含 `rolling_ic_series`，tsc 不擋 W2 回歸。

**進 B0 前最後一件必須改**：①TODO Task 1.1 `:64` 改「經 `_snapshot_result` 取 `result_normalized`」；②SPEC Task 1.3 `:89`＋TODO `:101` 改寫為「守衛已於 `_set_result` 完成；light／summary／feature **不得**再呼叫 `deny_factor_in_ok_oos`／`_to_json_compatible`」（與 Task 1.0 spy==0／P15 一致）。P2 Omit 可同輪補。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` | **rc=0** 全 OK |
| HEAD | `99e986a7` |

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：`:1623`／`:2339`（完成寫入）／`:2631`（refilter）。completed 後僅 refilter 覆寫。 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys/entries(report` 僅 pattern comparison；IC `page.tsx:881` 仍單鍵讀 `report?.rolling_ic_series?.[activeFeature]`（B2 改吃 featureDetail）。 |
| `metadata.selection_scope` 消費者 | **fact-verified**：orchestrator 寫入；`survivor_contract.py:598,615` 只取 `.scope_id`；frontend 無讀。 |
| 既有匯出端點 | **fact-verified**：`api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`；`export_analysis` 讀 `task_info["result"]`。 |
| 加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`（`:347`）。G-1 raw sha 才是機器證據。 |

---

## W1–W6 原反例複驗

| W | 複驗 | 狀態 |
|---|---|---|
| W1 寫入時 normalize＋守衛；投影只讀 snapshot；預設 `/result` 不變 | §C-7／Task 1.0 有 `_set_result`＋`result_normalized`＋`_snapshot_result`＋spy==0＋P15。**但** Task 1.1 仍「lock 內取 `result`」；Task 1.3／SPEC `:89` 仍「deny 先跑／在投影之前」→ 與 W1 互斥（見 P1-01／P1-02）。記憶體：本機 rough 物件樹 ~431 MB；若 `result` 保留 raw 且 `result_normalized` 另樹 ⇒ ~2×。`_to_json_compatible` 對磁碟 JSON **冪等**（sorted／unsorted sha 皆 True）⇒ **可**只存 normalized（或兩鍵同引用）而預設路徑仍走既有 `get_result` 正規化，G-1 可成立。守衛 raise：Task 1.0 邊界④＝不寫入／revision 不變／標 failed；對齊**現行讀取** raise（`get_result:1788`），**非**現行寫入路徑（`:1647-1654` catch 後仍 `completed`＋已寫 result）。 | **部分 CLOSED**（契約主文 CLOSED；Task 1.1／1.3 字面未閉） |
| W2 `rolling_ic_series`＋page ⑤ | §C-6 (i) 六段供圖；Task 2.3 `sectionSplit`／`ICFeatureDetail` 含 `rolling_ic_series`；案例⑤斷言 `RollingICChart` 收序列。現行 `page.tsx:881` 仍讀 report（B2 改）。 | **CLOSED**（文件）；型別 Omit 殘洞 → P2-01 |
| W3 `LATENCY_GATE` | G-9：warm-up 3＋20、p95＝第 19 小、固定請求集、恰一行文法、rc 0／1／2；gate 與 `SIZE_GATE` 同規則（TODO `:26`）。B1 批次列仍以 `SIZE_GATE` 為主；LATENCY PASS 在 Task 3.1／B3。 | **CLOSED** |
| W4 int32＋32-task＋`cache_bytes`；IP-RESID-5 | §C-9／TODO `:65`／`:76`：`numpy.int32`（實測 157384 B）、32 task、`cache_bytes()`、P16。IP-RESID-5 三值 `blocked-by` 成立（§N `:141`）；registry 同步標 B3（TODO `:194` 仍寫 1～4，殘留計 5——收案時補登）。 | **CLOSED** |
| W5 `order`／150 ms | `grep` 獨立鍵 `order`：TODO `:143` 已 `sort_order`（typed `SummaryPageParams`，註「無 `order` 鍵」）；去抖全文 300 ms；「150 ms」僅 light p50 預算非去抖。 | **CLOSED** |
| W6 page 八案例 | SPEC `:114`／TODO `:160`／`:169`：④初始 null／⑦切換舊 detail＋overlay／⑧mock reject⇒重試；§C-10 禁清空。 | **CLOSED** |

### W1 記憶體／只留 normalized 裁定（碼證）

- 序列化體 ~119 MB；本機 rough 樹 ~431 MB；雙樹估 ~862 MB。
- `venv` 對 39k 報告：`_to_json_compatible` 兩次後 sorted／unsorted sha **皆相等**（冪等）。
- **裁定**：不必為 G-1 深拷貝雙持有。建議明文 `task_info["result"] = task_info["result_normalized"] = normalized`（**同物件引用**），或只留一鍵；預設 `/result` 仍呼叫既有 `get_result`（再 normalize＋deny）⇒ 位元組與今日路徑等價。若 agent 保留 raw＋另存 normalized 深拷貝，則每 completed task RSS 近翻倍，與 IP-RESID-5 疊加。

### 守衛 raise 語意裁定

- **新契約**（寫入時 raise ⇒ 不寫／failed）≠ **現行寫入**（先寫 completed，deny 只影響 callback 降級）。
- **＝現行讀取**（`get_result` 對違規 raise）。SPEC「與現行讀取時 raise 語意等價」措辭正確；實作須改三寫點外層，使 deny 失敗不再標 completed。

---

## 必答（成對）

### 1a. 預設 `/result` 仍可能被改變的方式
① `view` 預設誤非 `None`；②為新模型替 `get_result` 加 `response_model` ⇒ 丟鍵／改序列化；③預設路徑改吃已排序／已刪段的 `result_normalized` 且**跳過**既有 `_to_json_compatible` 鍵序／null 規則；④`deny_factor_in_ok_oos` 挪到投影後或預設路徑省略。

### 1b. G-1 能否抓到
**能抓多數**：誤套 light、丟鍵、normalize 改字面 ⇒ raw sha 紅。抓不到：只改 OpenAPI 簽名不動 body。須搭配 mutation P6。冪等前提下「只存 normalized 仍走 get_result」⇒ G-1 應綠。

### 2a. light 會刪但前端仍在讀的鍵
B2 前：`page.tsx:881` `report.rolling_ic_series`（已列 drop）。metadata：依 keep 白名單，本輪未找到「前端仍讀且會被刪」的鍵。`ICReportLight` Omit 若漏 `rolling_ic_series` ⇒ 型別仍允許讀（P2-01）。

### 2b. 該刪卻沒進刪段、會破 G-5 的段
七段已列。若 agent **忘刪** `turnover_analysis`（~51 MB）⇒ G-5／P4 紅。無新增遺漏段。

### 3a. 後端 sort_policy vs 前端 getSortValue——同序？
**不同序**（有意）。反例 `[b:None,a:None,c:0.5,d:0.5]` desc：前端≈`[c,d,b,a]`（`-inf`、無次鍵、stable；`ICSummaryTable.tsx:91-106`）；後端=`[c,d,a,b]`（缺值沉底＋`feature_name` 次鍵）。

### 3b. 哪邊對
**後端決定性次鍵**（跨頁穩定）。SPEC §C-8 已宣告有意變更。

### 4a. G-2／G-3 在 refilter 後；競態
綁同一 `result_revision`；不符 ⇒ 409。投影用 lock 內 snapshot。G-7a/b/c 覆蓋交錯／中途 refilter／`view=light` handshake。

### 4b. 不做版本戳的代價
跨頁混代；G-2 無法區分投影 bug vs 競態。

### 5a. Task 2.3 匯出：逐頁 vs 既有端點
**既有 `/export` 對**；Task 2.3 零改匯出。碼證：route `:649`；service 讀全量 `result`。

### 5b. 逐頁 39k 可接受時間
不採納。序列約 79×(50–200ms)≈4–16s，劣於一次 export。

### 6. ≥10× 不必要複雜？
**否**（契約／mutation／LRU 必要）。雙樹深拷貝若實作則屬不必要記憶體（見 W1 裁定）；應同引用或單鍵。

### 7. B2「一次切換」vs「先只換表格」；殘留；IP-RESID-3
- **風險較小**：B2 單批 cutover（已落 §B）。
- **IP-RESID-1／2**：`blocked-by` 落檔／golden（命中 a）**成立**。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣**成立**；不取代。
- **IP-RESID-4**：keep_keys 單一來源，`blocked-by` Task 0.1 **成立**。
- **IP-RESID-5**：`blocked-by` 另票 task 生命週期 **成立**；本票只鎖排序快取上限。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **有**——Task 1.1／1.3 與 §C-7／Task 1.0 寫入時守衛契約互斥（P1-01／P1-02） |
| 2 | 漏項 | W1 未同步到 1.1／1.3 字面；Omit 漏 rolling（P2-01） |
| 3 | 不可測 | G-1～G-9／P15／P16／八案例可證偽 |
| 4 | quant | 無 |
| 5 | 過度工程 | 無；雙樹深拷貝若做則過量（裁定：同引用） |
| 6 | OOM | 排序快取 ≤~40 MB 已鎖；雙持有 raw+normalized 為風險（非新 P0） |
| 7 | Cache | revision 鍵＋P14／P16；無 |
| 8 | API／相容 | 預設路徑＋v2 矩陣足夠；1.3 deny 字面會破壞延遲契約 |
| 9 | 測試 | W6 八案例足夠；spy／P15 可擋誤實作，但 Task 字面仍誤導 |
| 10 | Agent 可執行 | Task 1.1／1.3 字面會讓 agent 跟錯（P1） |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| W1–W6 文件已閉合 | **假（W1 Task 字面）** | 上表；§C-7 主文真、1.1／1.3 假 |
| 同時存 `result`＋`result_normalized` 必翻倍記憶體 | **假（若同引用）** | 冪等＋同物件 ⇒ 1×；深拷貝才 2× |
| 守衛 raise 與現行寫入語意相同 | **假** | 現行寫入 catch；新契約＝讀取 raise／標 failed |
| `order`／150 ms 去抖已清 | **真** | grep |
| IP-RESID-5 三值理由成立 | **真** | §N |
| completed 後僅 refilter 改 result | **真** | 三賦值點 |

---

## GROK-R5-P1-01

**斷言**: TODO Task 1.1 仍寫 `get_result_summary_page`「lock 內取 `result`」，與 §C-7／Task 1.0「所有投影只經 `_snapshot_result` 讀 `result_normalized`、不得再全樹正規化」互斥；agent 依 Task 1.1 字面實作會繞過寫入時正規化快照。

**碼證**: TODO `:64` 原文「lock 內取 `result`，lock 外投影」；對照 TODO `:49`／SPEC `:37`「`_snapshot_result` → `(result_normalized, result_revision)`；投影不得再呼叫 `_to_json_compatible`／`deny_factor_in_ok_oos`」；mutation P15 假設 snapshot 路徑。`RECHECK:` `grep -n 'lock 內取' docs/ICRESULT_PAGING_TODO.md` 應在修後改為 snapshot／`result_normalized`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#54626e187238; docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd

[MAJOR] 信心度=High。失敗：summary 吃 raw（含 numpy／未守衛樹）或在請求路徑補跑 normalize⇒§C-9／P15 意圖落空。修法：Task 1.1（及 1.2 service 層）統一「`_snapshot_result` → 投影」。

---

## GROK-R5-P1-02

**斷言**: SPEC Task 1.3 與 TODO Task 1.3 仍要求在投影前執行 `deny_factor_in_ok_oos`，與 R4 W1「寫入時一次守衛、投影請求 spy 呼叫 == 0」直接矛盾；照做會把 light 路徑拉回全樹守衛（實測 ~1461 ms）而破 §C-9。

**碼證**: SPEC `:89`「改法：`deny_factor_in_ok_oos` 先跑」；TODO `:101`「①`deny_factor_in_ok_oos(normalized)` 在投影**之前**」；對照 SPEC `:37`／TODO `:49`「light／summary／feature **不得**再走守衛」＋P15／單元 spy。現行讀取 `get_result:1788` 仍 deny（預設路徑）；投影路徑不得再跑。`RECHECK:` 修後 `:89`／`:101` 不得再指令投影前 deny；改為「守衛已於 `_set_result`；投影只讀 snapshot」。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4

[MAJOR] 信心度=High。失敗：agent 在 `view=light` 每請求 deny⇒G-9 light p95 必紅，或為過門檻省略守衛⇒資料品質紅線。修法：刪／改 Task 1.3 該句；TODO §0「視圖前先跑」改註「寫入時一次＝視圖前」。

---

## GROK-R5-P2-01

**斷言**: Task 2.1 將 `ICReportLight` 寫成 `Omit<ICReport, per-feature 四段|…>`，未把 `rolling_ic_series` 列入 Omit；與 §C-6 七段 drop／Task 2.3 六圖改吃 `featureDetail` 不一致，tsc 不擋 `report.rolling_ic_series` 回歸。

**碼證**: TODO `:125` 原文「per-feature 四段」；drop 含 `rolling_ic_series`（SPEC `:36`）；Task 2.3 `:159` 改 `featureDetail.rolling_ic_series`；現行 `page.tsx:881` 仍讀 report。`ICReport` 確有 `rolling_ic_series` 鍵。`RECHECK:` Omit 應顯式列出與 `drop_sections` 對齊之段名（含 `rolling_ic_series`／`grouped_ic` 等），或 pointer 至 contract `drop_sections`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#54626e187238; docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd

[MINOR] 信心度=High。失敗：B2 gate 綠但型別仍允許讀已刪段⇒W2 回歸無編譯期網。修法：Omit 與 drop 七段對齊。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；W1–W6 逐段對照；`_to_json_compatible` 冪等；int32 157384 B；order／150ms 去抖清零；三 result 賦值點；selection_scope／export／page rolling 讀點  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` rc=0；venv 冪等／int32／rough 樹；`grep` order／150ms／deny／snapshot／Omit（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R5-grok.md`

STATUS: DONE
