# ICRESULT_PAGING SPEC＋TODO adversarial review R3（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R3  
family: grok  
findings-round: R3  
標的 commit: `5ea2f231`（SPEC R2 修訂＋TODO；尚未實作）  
R2 收斂: `handoffs/reconcile/20260909-icresultpaging-x-review-r2/synth.md` Y1–Y6  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#054e03748587  

---

## Verdict：需修補後派工

R2 六群集 Y1–Y6 **原反例重跑皆已閉合**（見下表）。本輪**無 P0**；新洞 **1 P1＋2 P2**：`project_light_view` 若依 TODO 所列順序先 `_collections_to_counts` 再跑 `funnel_stage_adapter`，實機 `stage5_thresholds.output_features`（dict）會被改成 `output_features_count`，adapter 候選鍵找不到 ⇒ output 變 `null`，與 G-8 `int(len(dict))` 互斥。另 G-8 寫「六 stage」卻漏列 `stage3_event_filter`；phase gate 對 `SIZE_GATE=FAIL` 的機檢偽碼未寫死。

**進 B0 前最後一件必須改**：在 §C-6／Task 1.3 明文規定「`filter_log_funnel` 必須對**計數轉換前**的 `filter_log` 計算（或等價：先 funnel 再 counts）」，並把該順序釘進 G-8／mutation（建議 P11 旁加「先 counts 再 funnel ⇒ G-8 紅」）。其餘 P2 可同輪順手補。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` | **rc=0** 全 OK |
| `venv/bin/python handoffs/_light_size_probe.py` | `light_bytes 28019`（≤262144） |
| HEAD | `5ea2f231`（docs R2 修訂） |

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：`grep -n 'task_info\["result"\] =' api/services/ic_analysis_service.py` → `:1623`（analyze 完成）／`:2339`（`_run_full_analysis` 完成）／`:2631`（refilter）。completed 後僅 refilter 覆寫。 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys(report`／`Object.entries(report` 於 `frontend/src` 僅命中 pattern comparison（非 IC）；`page.tsx` 以 `activeFeature` 單鍵取段。 |
| `metadata.selection_scope` 消費者 | **fact-verified**：orchestrator 寫入；`survivor_contract.py:598,615` 只取 `.scope_id`；`frontend/src` 無讀取。light 將兩 list→`*_count` 後 `scope_id` 標量仍在。 |
| 既有匯出端點 | **fact-verified**：`api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`；`ExportButtons.tsx:64-66` 已組該 URL。 |
| 加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`（route `:347`）。G-1 raw sha 才是機器證據（Phase 1）。 |

---

## Y1–Y6 原反例複驗

| Y | 複驗 | 狀態 |
|---|---|---|
| Y1 G-6 兩檔 `[A,B,C,D]`／`[B,A,C]`／`[A,B,C]` | SPEC `:51` 與 TODO `:76` 皆 `asc==[A,B,C,D]`；venv 依 §C-8 偽碼重算四列／三列與兩檔一致 | **CLOSED** |
| Y2 snapshot＋refilter handshake＋`:2339` | §C-7／Task 1.0 有 `_snapshot_result`＋G-7a/b/c＋`POST /refilter?view=light`；`:2339`＝`_run_full_analysis` 完成寫點，Task 1.0 已要求三寫點皆經 `_set_result` | **CLOSED**（見 P1 外之實作順序新洞） |
| Y3 G-5 三態＋gate | G-5 移出 pytest；探針 `SIZE_GATE=PASS\|FAIL\|BLOCKED`；B1「BLOCKED 不假綠不紅」、B3 要 PASS；腳本尚未存在（Task 0.1 建）—設計可機檢，但 FAIL⇒gate rc 偽碼偏弱 → P2-02 | **CLOSED＋P2** |
| Y4 funnel adapter／G-8／stage1 null | 實機六 stage 手算：stage0 `{39373,null}`、stage1 `{null,null}`、stage3 `{null,null}`、feature_filter `{39346,39346}`、stage5 `{39346,2}`、stage6 `{0,0}`。stage1 維持 null（不由前 stage 推導）＝正確（不靜默補值）。但 counts→funnel 順序破 stage5 → **P1-01**；G-8 漏 stage3 → P2-01 | **部分 CLOSED** |
| Y5 B2 單批＋三案例 page 測試 | §B B2＝2.1+2.2+2.3 單批；Task 2.3 三案例含「載入中」文案（不只不 throw）足以擋「light 已開、圖表讀已刪段」 | **CLOSED** |
| Y6 wildcard＋selection_scope | `*`＝一層直接子鍵、目標須 dict、no-op；實機 `selection_scope` 兩 list（39346／39337）→`*_count` 後 `scope_id` 仍為 string，survivor `:598,615` 可讀 | **CLOSED** |

### Y4 順序反例（本輪新）

```
BEFORE counts: stage5_thresholds output=2
AFTER counts:  stage5_thresholds output=None
  （output_features dict → output_features_count；候選鍵 output_features／feature_count_filtered 皆不在）
```

`RECHECK:` 對 `data_cache/reports/ic_report_ic_gatekeeper.json` 實跑 adapter；或讀 TODO Task 1.3 `:100` 元件列序。

---

## 必答（成對）

### 1a. 預設 `/result` 仍可能被改變的方式
① `view` 預設誤非 `None`（誤走 light）；②為新模型替 `get_result` 加 `response_model` ⇒ 丟鍵／改序列化；③`deny_factor_in_ok_oos` 挪到投影後、或預設路徑多跑 normalize／鍵排序。

### 1b. G-1 能否抓到
**能抓多數**：誤套 light、丟鍵、normalize 改字面 ⇒ raw sha 紅。抓不到：只改 OpenAPI 簽名不動 body。須搭配 mutation P6。

### 2a. light 會刪但前端仍在讀的鍵
依 §C-6＋顯式 keep，IC 頁消費者應保留。本輪未找到「前端仍讀且會被刪」的 metadata 鍵。`page.tsx` 仍讀的 per-feature 段（`ic_decay` 等）屬 B2 同批改吃 `featureDetail` 的範圍，非 metadata。

### 2b. 該刪卻沒進刪段、會破 G-5 的段
七段已列。若 agent **忘刪** `turnover_analysis`（51 MB）或忘轉 `selection_scope` 兩 list ⇒ G-5 紅（P4／P9）。無新增遺漏段。

### 3a. 後端 sort_policy vs 前端 getSortValue——同序？
**不同序**（有意）。反例輸入 `[b:None,a:None,c:0.5,d:0.5]` desc：前端≈`[c,d,b,a]`（缺值 `-inf`、無次鍵、stable）；後端=`[c,d,a,b]`（缺值沉底＋`feature_name` 次鍵）。

### 3b. 哪邊對
**後端決定性次鍵**（分頁跨頁穩定）。SPEC §C-8 已宣告有意變更。

### 4a. G-2／G-3 在 refilter 後；競態
G-2／G-3 綁同一 `result_revision`；不符 ⇒ 409。投影用 lock 內 snapshot。G-7a/b/c 覆蓋交錯／中途 refilter／`view=light` handshake。前端丟棄 `revision != store`。

### 4b. 不做版本戳的代價
跨頁混代；G-2 無法區分投影 bug vs 競態。本票已要求戳。

### 5a. Task 2.3 匯出：逐頁 vs 既有端點
**既有 `/export` 對**；Task 2.3 零改匯出。碼證：`ExportButtons.tsx:64-66`；route `:649`。

### 5b. 逐頁 39k 可接受時間
不採納（已刪）。序列約 79×(50–200ms)≈4–16s，劣於一次 export。

### 6. ≥10× 不必要複雜？
**否**。golden＝小 fixture 全特徵；contract JSON 必要；mutation P1–P11 對應 §V。Task 0.1 無 200 抽樣。唯一多餘風險＝漏斗／counts 順序未釘死造成返工（P1-01）。

### 7. B2「一次切換」vs「先只換表格」；殘留；IP-RESID-3
- **風險較小**：B2 單批 cutover（R2 Y5）——已落 §B。
- **IP-RESID-1／2**：`blocked-by` 落檔／golden（命中 a）**成立**。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣**成立**；不取代。
- **IP-RESID-4**（新＝keep_keys 單一來源，blocked-by Task 0.1）**成立**；舊漏斗殘留已收回為 Task。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **有**——counts 後跑 funnel vs G-8 stage5（P1-01）；G-8「六 stage」vs 列五條（P2-01） |
| 2 | 漏項 | Y2 handshake／snapshot 已補；Task 1.1 仍寫「lock 內取 result」而未點名 `_snapshot_result`（被 Task 1.0「所有投影只吃 snapshot」覆蓋，不另開 finding） |
| 3 | 不可測 | G-1～G-8 可證偽；G-5 三態設計成立，FAIL 機檢偽碼偏弱（P2-02） |
| 4 | quant | 無（不改數值／落檔） |
| 5 | 過度工程 | 無 |
| 6 | OOM | light 實測 28KB；無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 預設路徑＋v2 矩陣足夠 |
| 9 | 測試 | B2 三案例足夠；G-8 應含 stage3 |
| 10 | Agent 可執行 | Task 具體；漏斗順序歧義會讓 agent 寫出與 G-8 對打的實作（P1-01） |
| 11 | 短命工 | 無（B2 不再拆批） |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| Y1 G-6 兩檔與 comparator 自洽 | **真** | venv 重算 |
| 先 counts 再 funnel 仍滿足 G-8 stage5 | **假** | 實機 stage5 after-counts output=None |
| stage1 `{null,null}` 應改由前 stage 推導 | **假（應維持 null）** | 推導＝靜默補值，違 §C-5 |
| completed 後僅 refilter 改 result | **真** | 三賦值點 |
| selection_scope 計數後 survivor 仍可讀 scope_id | **真** | `:598,615`＋實機鍵型別 |
| B1 gate 對 SIZE=FAIL 必紅 | **assumed（文件暗示，未寫死偽碼）** | 見 P2-02 |

---

## GROK-R3-P1-01

**斷言**: TODO Task 1.3 將 `_collections_to_counts` 列於 `funnel_from_filter_log(report["filter_log"])` 之前，且 §C-6 (iii) 把 list／dict **改為** `<key>_count`；若實作依此序對同一 `filter_log` 先計數再跑 adapter，實機 `stage5_thresholds.output_features`（dict）消失，G-8 期望的 `output=int(len(dict))` 變成 `null`。

**碼證**: TODO `:100` 元件列序＝counts → summary_page → `funnel_from_filter_log(report["filter_log"])`；SPEC §C-6 (iii)「改為 `<key>_count`」＋(iv) 候選鍵只有 `output_features`／`feature_count_filtered`（無 `output_features_count`）；G-8（SPEC `:53`）`stage5_thresholds {input:int, output:int(len(dict))}`。venv 對實機報告：counts 前 stage5 output=2，counts 後 output=None（鍵變 `output_features_count`）。`RECHECK:` 同上模擬；或實作後跑 G-8。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#054e03748587

[MAJOR] 信心度=High。失敗：agent 依字面順序實作 ⇒ G-8 紅，或私下把 `*_count` 塞進候選鍵／改 G-8 期望造成假綠。修法：§C-6／Task 1.3 明文「funnel 必須吃計數前的 filter_log（建議：先自原 stage 算 `filter_log_funnel`，再對 light 的 filter_log 做 counts）」；G-8／shape fixture 鎖定 stage5 output≠null；mutation 加「顛倒順序 ⇒ G-8 紅」。

---

## GROK-R3-P2-01

**斷言**: G-8 宣稱「六 stage」經 adapter 的 golden，但括號列舉只含五個 stage、漏掉實機存在的 `stage3_event_filter`（候選鍵皆缺 ⇒ `{null,null}`），golden 不完整會讓測試只鎖五段。

**碼證**: SPEC `:53`／TODO `:111` G-8 列 `stage0`／`feature_filter`／`stage1`／`stage5`／`stage6`；實機 `jq` 六 stage 含 `stage3_event_filter`（鍵無 input_features／output_features／feature_count_*）。手算 stage3=`{null,null}`。`RECHECK:` `jq -r '.filter_log|keys[]' data_cache/reports/ic_report_ic_gatekeeper.json`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[MINOR] 信心度=High。失敗：shape／G-8 漏 stage3 ⇒ 該 stage 投影漂移不被抓。修法：G-8 golden 顯式加 `stage3_event_filter {null,null}`（維持 null、不推導）。

---

## GROK-R3-P2-02

**斷言**: G-5 三態設計對 `BLOCKED` 有明確「不假綠不紅」規則，但 `scripts/icresult_paging_phase_gate.sh`（尚未存在）對 `SIZE_GATE=FAIL` 是否使 B1 gate `rc≠0` 沒有可機檢偽碼；「只轉印三態」可被實作成 FAIL 亦不紅，尺寸回歸拖到 B3 才爆。

**碼證**: SPEC `:50`「對 G-5 **只轉印三態**：`BLOCKED` 不使 B1 gate 假綠亦不使之紅」；TODO §B `:18`／Phase1 Gate `:119` 同只點名 BLOCKED 例外，未寫 `FAIL ⇒ gate rc=1`。腳本 `test -e scripts/icresult_paging_phase_gate.sh` ⇒ 不存在（Task 0.1 建）。`RECHECK:` 對照上述行；B0 實作 gate 時注入 `SIZE_GATE=FAIL` 應使 phase 1 rc≠0。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[MINOR] 信心度=Medium。失敗：gate 只 `cat` receipt ⇒ FAIL 假綠至 B3。修法：Task 0.1／gate 偽碼寫死「解析一行 `SIZE_GATE=`；`FAIL`⇒rc=1；`BLOCKED`⇒印 `SIZE=BLOCKED` 且不改 rc；`PASS`⇒印並繼續；缺行／未知⇒rc=1」。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；light probe 28019；result 三賦值點（含 :2339=_run_full_analysis）；selection_scope／export／page sectionSplit；G-6 四列／三列重算；funnel adapter before/after counts（stage5 2→None）；wildcard／scope_id；Y1–Y6 對照  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀＋filter_log keys；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py` → 28019；venv comparator＋funnel/count 順序模擬（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R3-grok.md`

STATUS: DONE
