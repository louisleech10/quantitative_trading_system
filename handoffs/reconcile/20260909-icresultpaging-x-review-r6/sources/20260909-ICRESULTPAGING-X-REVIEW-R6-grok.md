# ICRESULT_PAGING SPEC＋TODO adversarial review R6（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R6  
family: grok  
findings-round: R6  
標的 commit: `c4579cf7`（SPEC R5 修訂＋TODO；尚未實作）  
R5 收斂: `handoffs/reconcile/20260909-icresultpaging-x-review-r5/synth.md` V1–V6  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#ec0771609868  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#09e62c65bc1f  

---

## Verdict：需修補後派工

V1／V3／V5／V6 原反例文件層 **CLOSED**。V2 主文（§C-7 (a)(b)＋TODO Task 1.0 邊界④⑤）已對，但 **SPEC Task 1.0 邊界④仍寫「守衛 raise ⇒ task 標 failed」**，與 §C-7(b)／TODO ⑤（refilter → completed＋422）互斥——V2 未完全閉合。V4 主文禁 pop／建新 dict 已寫，但 `_collections_to_counts` 仍描述成對節點就地改值，且不可變測試只鎖七段 drop，淺拷貝＋就地計數會污染 `filter_log`（本輪 P2）。

本輪 **無 P0**；**1 P1＋1 P2**。**進 B0 前最後一件必須改**：①SPEC Task 1.0 `:67` 邊界④拆成與 TODO／§C-7 同形的④初次 failed／⑤refilter completed＋422；②Task 1.3 明文 `_collections_to_counts` 只改 light 私有副本（或新建 stage dict），不可變測試加「light 後 source `filter_log`／`selection_scope` deep-equal 未變」。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r6-baseline.sha` | **rc=0** 全 OK |
| HEAD | `c4579cf7` |

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：賦值點 `:1623`／`:2339`（完成）／`:2631`（refilter）。completed 後僅 refilter 覆寫。 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys/entries(report` 僅 pattern comparison；IC `page.tsx:881` 仍單鍵讀 `report?.rolling_ic_series?.[activeFeature]`（B2 改吃 featureDetail）。 |
| `metadata.selection_scope` 消費者 | **fact-verified**：orchestrator 寫入；`survivor_contract.py:598,615` 只取 `.scope_id`；frontend 無讀。 |
| 既有匯出端點 | **fact-verified**：`api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`；`export_analysis` 讀 `task_info["result"]` `:1896`。 |
| 加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`（`:346-353`）。G-1 raw sha 才是機器證據。 |

---

## V1–V6 原反例複驗

| V | 複驗 | 狀態 |
|---|---|---|
| V1 單一 normalized 樹＋冪等 G-1 | `grep result_normalized docs` → 0；§C-7／TODO Task 1.0 只留 `task_info["result"]`；venv 探針：已 JSON 型別／report-like `_to_json_compatible(n)==n` **True**（dict/list **重建** identity=False，值相等＋json dumps 相等）；NaN／±inf／numpy → None／scalar 後第二遍穩定。export `:1896` 淺拷貝＋`sanitize_factor_returns` 回新物件；apply-transforms 讀 status 不回寫 result。預設路徑仍走 normalize＋deny（碼不改）⇒ G-1 可成立。 | **CLOSED** |
| V2 寫點失敗語意 | §C-7 (a) failed／(b) 先驗後寫＋422；TODO `:56` ④⑤已拆。**SPEC Task 1.0 `:67` 邊界④仍統一「標 failed」** → 見 P1-01。現行碼：completion 先寫再 catch deny；refilter 先寫再 `get_result`（可 500）——文件已列為待修缺陷。 | **部分 CLOSED**（主文／TODO CLOSED；SPEC Task 邊界未閉） |
| V3 gate 消費 LATENCY | G-9：gate 1 `--size`、gate 3 `--size --latency` 皆須 PASS；parser 與 SIZE 同規則；`test_phase_gate_parser` 負向。腳本尚未存在＝B0 產物，無第二 parser 可繞。 | **CLOSED** |
| V4 snapshot 不可變 | §C-7／TODO `:100-101` 禁 pop、建新 dict、light×2→summary→feature 七段 deep-equal。**`_collections_to_counts` 字面＝就地改值**；七段測試不覆蓋 `filter_log` 污染 → P2-01。頂層淺 dict 省略 39k 子樹對 §C-9 可接受（前提：計數路徑不共享可變節點）。 | **部分 CLOSED** |
| V5 grep 殘留 | `result_normalized` → 0；`lock 內取`／`deny 先跑` 僅 SPEC `:4` 修訂史；Task 1.1 `:64` 已 `_snapshot_result`；Task 1.3 守衛已於 `_set_result`。`order`／150 ms 去抖 → 0。 | **CLOSED** |
| V6 debounce／cache／Omit | owner＝表格搜尋框、hook 不去抖；`cache_bytes()`＝Σ nbytes、第 9 組／32 task／module 單例；`ICReportLight` Omit 七段含 `rolling_ic_series`（TODO `:125`）；`IP-RESID-5` 射程限縮。 | **CLOSED** |

### V1 冪等碼證摘要

- `_to_json_compatible` `:2819-2880`：None／有限 float／str|int|bool 早退；dict/list 新建容器遞迴；NaN／inf → None；`np.generic` → `.item()`。
- 實跑（venv）：`none/bool/int/float/str` identity＋值冪等；`nan/inf` → `None` 後冪等；`dict/list/union` 值冪等、identity 否；report-like `n2==n3` True、`json.dumps` 相等。

---

## 必答（成對）

### 1a. 預設 `/result` 仍可能被改變的方式
① `view` 預設誤非 `None`；②為 `get_result` 加 `response_model` ⇒ 丟鍵／重排；③預設路徑改吃已投影樹並**跳過**既有 `_to_json_compatible`；④投影／export 就地 `pop` 污染 live `task_info["result"]`；⑤`deny_factor_in_ok_oos` 挪序或預設路徑省略。

### 1b. G-1 能否抓到
**能抓多數**：誤套 light、丟鍵、normalize 字面變 ⇒ raw sha 紅（＋mutation P6）。抓不到純 OpenAPI 簽名漂移。冪等前提下「單樹＋讀取碼不變」⇒ G-1 應綠。

### 2a. light 會刪但前端仍在讀的鍵
B2 前：`page.tsx:881` `report.rolling_ic_series`（已列 drop，B2 改 `featureDetail`）。metadata：§A receipt 前端鍵 ⊆ keep 聯集；本輪無「前端仍讀且會被刪」的 metadata 鍵。

### 2b. 該刪卻沒進刪段、會破 G-5 的段
無新漏段。漏刪七段任一（尤 `turnover_analysis` ~51MB）或漏 `collection_to_count_paths`（`winsorized_features` ~1.6MB）⇒ G-5 紅。

### 3a. 排序同序？
**不同序**。後端 contract：缺值兩向沉底＋`feature_name` 次鍵。前端 `getSortValue` `:91-106`：非有限→`-Infinity`、tie 回 0 無次鍵。反例：`icir` 全 null（39k 實機）⇒ 後端字母升冪 vs 前端保留輸入序；asc 時前端 null 置頂、後端沉底。

### 3b. 哪邊對
**後端為準**（§C-8 明文分頁序取代前端本地序＝有意變更）；前端排序應移除。

### 4a. G-2／G-3 在 refilter 後語意；競態
`result_revision` 遞增；帶舊 `revision` ⇒ 409；不帶 ⇒ 新世代；lock 內 snapshot；G-7a/b/c；前端 abort＋revision 不符丟棄。

### 4b. 不做版本戳代價
跨 refilter 混頁／混 detail；G-2 集合相等不可證偽（§A 已證三寫點會換 result）。

### 5a. 匯出：逐頁 vs 既有
**既有** `GET /export/{task_id}/{format}`（`:649-687`）讀全量 result；Task 2.3 明列匯出不動／不做逐頁。

### 5b. 逐頁 39k UI 時間
~787 頁×50 為分鐘級且無規格；不可接受；本票不採。

### 6. ≥10× 不必要複雜？
**無**。14 特徵全量 golden（不抽樣）、contract SoT、mutation P1–P16 對 §G／§V 合理；G-9 延伸同探針合理。

### 7. B2／殘留
- **B2 一次切換**風險小於「先只換表格」（light 已開而六圖仍讀已刪段＝退化中間態）。
- **IP-RESID-1/2/4/5**：三值 `blocked-by:` 成立；5 射程已限縮。
- **IP-RESID-3**：`user-ruling:` 並存＋四格矩陣，**不取代** v2。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **P1-01**：SPEC Task 1.0 邊界④ vs §C-7(b)／TODO ⑤ |
| 2 | 漏項 | 無 blocking（V2 實作差異已列目標語意） |
| 3 | 不可測 | G-1～G-9／八案例可機械驗 |
| 4 | quant | 無；deny 守衛不可省 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 單樹；快取有上限；`_tasks`→IP-RESID-5 |
| 7 | cache | revision 失效＋32×8 可測 |
| 8 | API | FF 命名對齊；v2×light⇒400 |
| 9 | 測試 | **P2-01**：不可變測試未鎖 filter_log |
| 10 | Agent | Task 多精確；邊界④殘留會誤導 |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 |
|---|---|
| template／jq／baseline | fact-verified（上表） |
| `_to_json_compatible` 冪等 ⇒ G-1 | fact-verified（值／json）；identity 非要求 |
| G-9 本機可 PASS | assumed（探針未建；設計合理） |
| refilter 422 映射 | assumed（文件一致；現行 route ValueError→400，實作須顯式映射） |

---

## GROK-R6-P1-01

**斷言**: SPEC Task 1.0 邊界④仍寫「守衛 raise ⇒ … task 標 failed」，與同檔 §C-7(b) 及 TODO Task 1.0 邊界⑤「refilter 守衛 raise ⇒ completed＋422」互斥；agent 依 SPEC Task 邊界實作會把 refilter 守衛失敗標成 failed，破壞 V2 已裁定的寫點語意。

**碼證**: SPEC `:67` 原文「④守衛 raise ⇒ 不寫入、revision 不變、task 標 failed（與現行讀取時 raise 語意等價）」；對照 SPEC `:37`「(b) refilter 時 raise ⇒ 先驗後寫：舊 result／revision 不變、task 仍 completed、POST /refilter 回 422」；TODO `:56` 已拆④初次 failed／⑤refilter completed＋422。TODO `:48` 括號「上層標 failed」亦易誤讀，但同句後段已澄清。`RECHECK:` `sed -n '67p' docs/ICRESULT_PAGING_SPEC.md` 修後須含 refilter≠failed；與 TODO `:56` 對齊。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ec0771609868; docs/ICRESULT_PAGING_TODO.md#09e62c65bc1f

[MAJOR] 信心度=High。失敗：refilter 注入守衛後 task 變 failed、舊 result 被清或 UI 當終態錯誤；與 G-7／TestClient「422＋舊 revision」斷言分叉。修法：SPEC Task 1.0 邊界改寫為與 §C-7／TODO ④⑤同形；刪「與現行讀取語意等價」笼統句（改指向 (a)(b)）。

---

## GROK-R6-P2-01

**斷言**: Task 1.3 一方面禁就地改寫，另一方面把 `_collections_to_counts` 寫成對節點 list／dict「改」為 `*_count`；若 `project_light_view` 頂層淺拷貝後對共享的 `filter_log`／`selection_scope` 就地計數，會污染 snapshot；現行不可變測試只斷言七段 drop deep-equal，抓不到此污染。

**碼證**: TODO `:100`「`_collections_to_counts(node)`＝… list／dict 值改 `f"{k}_count": len(v)`」＋「再對 light 的 `filter_log` 做計數」；`:101`「禁 pop／就地改寫，一律建新 dict」＋測試「light×2 → summary → feature，**七段**仍在且 deep-equal」。本機反例：`out={k:v for k,v in report.items() if k not in drop}` ⇒ `out['filter_log'] is report['filter_log']` True；就地改 count 後 source `filter_log` 變 `{input_features_count:2}`。第二輪 light 的 `funnel_from_filter_log(report["filter_log"])` 會吃到已計數樹。`RECHECK:` 修後偽碼須「對 path 目標 deepcopy／新建 stage dict 再計數」；測試加 assert source `filter_log`／`selection_scope` 在 light 後未變。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#09e62c65bc1f; docs/ICRESULT_PAGING_SPEC.md#ec0771609868

[MINOR] 信心度=High。失敗：第一次 light 後 raw `filter_log` 被毀 ⇒ 第二次 light funnel／G-8 漂移，或 export／預設 `/result` 讀到已縮水的 filter_log。修法：計數只作用於 light 私有副本；擴不可變測試超出七段。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha rc=0；V1–V6 逐段對照；`_to_json_compatible` 冪等探針；grep result_normalized／lock內／deny先跑／Omit／debounce；三寫點＋export／selection_scope／Object.keys；淺拷貝 filter_log 污染反例  
TESTS_RUN: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` rc=0；`bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` rc=0；`jq -c '{st:(.summary_table|length), meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r6-baseline.sha` rc=0；venv 冪等探針；brief greps（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R6-grok.md`

STATUS: DONE
