# ICRESULT_PAGING SPEC＋TODO adversarial review R2（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R2  
family: grok  
findings-round: R2  
標的 commit: `0ca66d8b`（SPEC R1 修訂＋TODO；尚未實作）  
R1 收斂: `handoffs/reconcile/20260909-icresultpaging-x-review-r1/synth.md` Z1–Z7  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#376e43979064  

---

## Verdict：需修補後派工

R1 自家六條（P0-01／P1-01‥03／P2-01‥02）對照 R1 修訂版**皆已閉合**；G-4∩G-5 互斥、顯式白名單、revision、排序契約宣告、匯出零改、grouped_ic 刪段均落文件且與 probe／碼證一致。本輪**無 P0**；新洞 **1 P1＋1 P2**：SPEC §G-6 與 TODO Task 1.1 對四列並列 fixture 的 **asc 期望序互相矛盾**；`IP-RESID-4` 的 `needs-research` 理由已被碼證推翻（應改 reason_code，不必收回為 Task）。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r2-baseline.sha` | **rc=0** 全 OK |
| `venv/bin/python handoffs/_light_size_probe.py` | `light_bytes 28019`（≤262144） |

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：`grep -n 'task_info\["result"\] =' api/services/ic_analysis_service.py` → 僅 `:1623`／`:2339`／`:2631`（analyze 完成／full-analysis 完成／refilter）。completed 後僅 refilter 覆寫；前兩者為寫入 completed 當下。 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys(report`／`Object.entries(report` 於 `frontend/src` **無命中**；`page.tsx` 以 `activeFeature` 單鍵取 `ic_decay`／`quantile`／`grouped`／`turnover`／`rolling_ic_series`。 |
| `metadata.selection_scope` 消費者 | **fact-verified**：orchestrator 寫入；`survivor_contract.py:598,615` 只取 `scope_id`；`frontend/src` **無**讀取。light 將 list→`*_count` 後 `scope_id` 標量仍在，不阻 survivor（survivor 讀全量 result／落檔，非 light）。 |
| 既有匯出端點 | **fact-verified**：`api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`；`ExportButtons.tsx:64-66` 已組該 URL；`module_statuses` 仍讀 `report.module_statuses`（G-4d 保留）。 |
| 加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`、回 dict（`:347-360`）。G-1 raw sha 才是機器證據（Phase 1）。 |

---

## R1 自家 finding 複驗（原反例重跑）

| R1 ID | Z | 複驗 | 狀態 |
|---|---|---|---|
| GROK-R1-P0-01（G-4∩G-5 互斥） | Z1 | §C-6 刪七段含 `grouped_ic`；`collection_to_count_paths` 瘦 `filter_log.*`／`selection_scope`；G-4 改 (a)–(e)；G-5≤262144；probe `light_bytes 28019` | **CLOSED** |
| GROK-R1-P1-01（selection_scope 啟發式） | Z2 | `metadata_keep_keys` 改顯式列舉；TODO 0.1 禁 fixture 推導；list→count | **CLOSED** |
| GROK-R1-P1-02（逐頁匯出） | Z5 | Task 2.3 改「匯出不動」；只改 `summaryTable`→`hasRows` | **CLOSED** |
| GROK-R1-P1-03（排序未宣告變更） | Z4 | §C-8／sort_policy 明文「分頁序取代前端本地序＝有意行為變更」；禁用 `_finite_or_neg_inf` | **CLOSED**（但見本輪 P1-01：SPEC/TODO G-6 數值互斥） |
| GROK-R1-P2-01（refilter 無世代） | Z3 | Task 1.0 `result_revision`；三寫點；409；G-7；前端 abort＋重拉 | **CLOSED** |
| GROK-R1-P2-02（grouped_ic 摘要不清） | Z1 | light **刪** `grouped_ic`；單特徵由 Task 1.2 投影 | **CLOSED** |

### Z1 補充：`filter_log.*` 通配

實機 stage 名＝`stage0_ingestion`／`stage1_preprocessing`／`stage3_event_filter`／`feature_filter`／`stage5_thresholds`／`stage6_redundancy`。TODO 1.3 `_collections_to_counts` 對 path 節點「list／dict→`<key>_count`、標量原樣」＝**結構通配**（不凍結 stage 名清單）⇒ stage 名漂仍會被瘦身。封閉性足夠；無新 finding。

### Z4 排序自洽（自行重算）

契約：缺值兩向沉底 `(1,0,name)`；有限 `(0, ±value, name)`；次鍵名升冪。

| fixture | desc | asc |
|---|---|---|
| A=B 有限、A\<B 名；C=D=None | `[A,B,C,D]` | `[A,B,C,D]` |
| A=0.5、B=0.9、C=None | `[B,A,C]` | `[A,B,C]` |

venv 實跑同上。**與 SPEC §G-6 一致；與 TODO Task 1.1 驗證句 `asc == [B,A,C,D]` 不一致** → P1-01。

G-1 raw bytes：TestClient `response.content` 依賴 dict 插入序（Py3.7+）＋現行無 `response_model`；同 process 重放可穩定。風險在加 `response_model`／改 normalize 鍵序——mutation P6＋G-1 可抓。

### Z6 G-5 `pytest.fail("blocked-by:artifact")`

**要的行為（fail-closed）**：本專案無 CI、尺寸 gate 依賴本機 `data_cache` 受控 artifact；skip 會假綠（R1 CODEX-R1-P2-01）。B1 gate 須文件化「缺 artifact ⇒ B1 紅＝UNCOVERED／blocked-by，非產品回歸」。不另開 finding。B2a／B2b 拆分仍留「表格已 light、圖表尚未改吃 featureDetail」中間態；`page.tsx` 以 `map?.[activeFeature] \|\| null` 不會因缺段 throw——可接受（R1 Z6／Z7 已裁）。

---

## 必答（成對）

### 1a. 預設 `/result` 仍可能被改變的方式
① `view` 預設誤非 `None`（誤走 light）；②為新模型替 `get_result` 加 `response_model` ⇒ 丟鍵／改序列化；③`deny_factor_in_ok_oos` 挪到投影後、或預設路徑多跑 normalize／鍵排序。

### 1b. G-1 能否抓到
**能抓多數**：誤套 light、丟鍵、normalize 改字面 ⇒ raw sha 紅。抓不到：只改 OpenAPI 簽名不動 body。須搭配 mutation P6「無 view 零分支」。

### 2a. light 會刪但前端仍在讀的鍵
依現行 §C-6＋顯式 keep（含 §A 前端鍵），IC 頁消費者（`n_timestamps`／`n_symbols`／`mode`／`event_filter`／`oos_downgrade`／`isolation`／`ic_window_disclosure`／`period_alignment`）**應保留**。本輪未找到「前端仍讀且會被刪」的 metadata 鍵。

### 2b. 該刪卻沒進刪段、會破 G-5 的段
在 R1 修訂後：七段已刪、集合已計數。若 agent **忘刪** `turnover_analysis`（51 MB）或忘轉 `selection_scope` 兩 list ⇒ G-5 必紅（mutation P4／P9）。反向「該刪未列」清單在修訂後**無新增遺漏段**（相對 39k 實機）。

### 3a. 後端 sort_policy vs 前端 getSortValue——同序？
**不同序**（有意）。前端：非有限→`-Infinity`；tie→`0` 無次鍵（stable 保輸入序）；asc 時缺值置頂。後端：缺值兩向沉底＋`feature_name` 次鍵。反例輸入 `[b:None,a:None,c:0.5,d:0.5]` desc：前端≈`[c,d,b,a]`；後端=`[c,d,a,b]`。

### 3b. 哪邊對
**後端決定性次鍵**（分頁跨頁穩定）。SPEC 已宣告有意變更。實作禁 `sorted(..., reverse=True)` 作用於含次鍵 tuple。

### 4a. G-2／G-3 在 refilter 後；競態
G-2a／2b／G-3 綁**同一 `result_revision`**。不符 ⇒ 409＋`current_revision`；前端 abort＋重拉一次。語意已定。

### 4b. 不做版本戳的代價
跨頁混代、G-2 無法區分投影 bug vs 競態。本票已要求戳——代價已付在 Task 1.0。

### 5a. Task 2.3 匯出：逐頁 vs 既有端點
**既有 `/export` 對**；Task 2.3 已改零改匯出。碼證：`ExportButtons.tsx:64-66`；route `:649`；另需保留 `report.module_statuses`（`:24-34`，G-4d）。

### 5b. 逐頁 39k 可接受時間
不採納（已刪）。若序列 79×(50–200ms)≈4–16s，劣於一次 export。

### 6. ≥10× 不必要複雜？
R1 修訂後：**否**。golden＝小 fixture 全特徵（14）＋受控尺寸 probe；contract JSON 值得留；mutation 骨架對 §V 十條必要。Task 0.1 不再 200 抽樣。

### 7. B2a vs 先只換表格；殘留；IP-RESID-3
- **風險較小**：B2a（2.1＋2.2）→ B2b（2.3）——已落 TODO §B。不可「只換表格仍拉 119MB」。
- **IP-RESID-1／2**：`blocked-by` 落檔／golden（命中 a）**成立**。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣**成立**；不取代、不刪。
- **IP-RESID-4**：鍵名錯配已碼證（見 P2-01）；`needs-research` 不成立，應改 reason_code；**不必**並入本票 Task（2.3 已明示不修）。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **有**——SPEC §G-6 vs TODO 1.1 G-6 asc 序（P1-01） |
| 2 | 漏項 | 無新漏項；R1 Z1–Z7 已補 |
| 3 | 不可測 | G-1～G-7 可證偽；G-4∩G-5 已解 |
| 4 | quant | 無（不改數值／落檔） |
| 5 | 過度工程 | 無（匯出／抽樣已簡） |
| 6 | OOM | light 實測 28KB；無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 預設路徑＋v2 矩陣足夠；簽名風險見 1a |
| 9 | 測試 | G-5 fail-closed 正確；B1 須標 artifact 前提 |
| 10 | Agent 可執行 | Task 具體；G-6 互斥會讓 agent 寫錯 golden（P1-01） |
| 11 | 短命工 | 無（存活至＝永久；B2a→B2b 圖表中間態可接受） |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| G-4(a)–(e) 與 G-5≤262144 可同時滿足 | **真（本輪複驗）** | probe 28019 |
| TODO G-6 四列 asc=`[B,A,C,D]` 與 §C-8／SPEC 同序 | **假** | 見 P1-01；venv 重算 |
| IP-RESID-4 仍需研究才能確認鍵名 | **假** | types `input`/`output` vs 實機 `input_features`/`output_features`（且多為 int） |
| completed 後僅 refilter 改 result | **真** | 三賦值點 |
| ExportButtons light 後仍需 `module_statuses` | **真** | `:24-34`；G-4d 保留 |

---

## GROK-R2-P1-01

**斷言**: SPEC §G-6 與 TODO Task 1.1 對「四列並列 fixture」的 asc 期望序互相矛盾（SPEC=`[A,B,C,D]`，TODO=`[B,A,C,D]`），且與 §C-8／TODO comparator 偽碼（次鍵 `feature_name` 升冪、缺值兩向沉底）只有 SPEC 一側自洽。

**碼證**: SPEC `:51`「desc 序 == `[A,B,C,D]`、asc 序 == `[A,B,C,D]`」；TODO Task 1.1 驗證 `:75`「desc == `[A,B,C,D]`、asc == `[B,A,C,D]`」。venv 依 TODO 偽碼 `(1,0,name)`／`(0,±value,name)` 重算四列 → desc/asc 皆 `[A,B,C,D]`。`RECHECK:` `grep -n '\[A,B,C,D\]\|\[B,A,C,D\]' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md`＋重跑 comparator。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MAJOR] 信心度=High。失敗：agent 依 TODO 寫 `sort_golden`／測断言會與 SPEC G-6 永久對打，或私下改 comparator 讓次鍵在 asc 反序（破壞 §C-8）。修法：把 TODO `:75` 的 asc 改為 `[A,B,C,D]`（與 SPEC／偽碼一致）；勿改 SPEC 去就錯誤的 `[B,A,C,D]`。

---

## GROK-R2-P2-01

**斷言**: §N `IP-RESID-4` 以 `needs-research` 為「為何現在不做」已不成立——FilterFunnelChart／型別期望的 `input`／`output` 與實機 `filter_log` 鍵名錯配可在本輪碼證，無需再研究。

**碼證**: `frontend/src/lib/types.ts:2155-2158` `FilterLogStage{input,output}`；`FilterFunnelChart.tsx:19-22` 讀 `values.input`／`values.output`；實機六 stage **皆無** `input`／`output` 鍵，僅部分有 `input_features`／`output_features`（且常為 int／dict，非圖表假設的成對計數名）。`RECHECK:` 本檔「IP-RESID-4」表＋`jq '.filter_log|to_entries[]|{stage:.key,keys:(.value|keys)}'`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472

[MINOR] 信心度=High。失敗：殘留登記誤導下一輪以為「還不知道鍵名」；不阻擋本票派工（Task 2.3 已明示不修漏斗鍵名）。修法：將 `為何現在不做` 改為 `blocked-by:out-of-scope`（或 `user-ruling:本票不修改前漏斗；觸發仍為 B34 漏斗空白`），保留殘留、**不**收回為 Task。

---

ASSUMPTIONS_VERIFIED: template_check 兩份 PASS；jq 39346/39398；baseline sha 全 OK；light probe 28019；result 三賦值點；selection_scope／export／module_statuses 消費者；sort_policy 四列／三列重算；filter_log 鍵名 vs FilterFunnelChart；R1 六條閉合對照  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r2-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py` → 28019；grep／讀碼／venv comparator（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R2-grok.md`

STATUS: DONE
