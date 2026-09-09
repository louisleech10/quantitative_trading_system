# ICRESULT_PAGING SPEC＋TODO adversarial review R4（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R4  
family: grok  
findings-round: R4  
標的 commit: `ad02df91`（SPEC R3 修訂＋TODO；尚未實作）  
R3 收斂: `handoffs/reconcile/20260909-icresultpaging-x-review-r3/synth.md` X1–X6  
SCOPE: review-only；禁改碼／文件  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241  
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418  

---

## Verdict：需修補後派工

X1–X5 原反例重跑皆已閉合。§C-9 延遲預算在本機對 39k 列實測可達（見下）。本輪**無 P0**；新洞 **1 P1＋1 P2**：TODO Task 2.2 檔案描述仍殘留 `order`（與 FF／SPEC／同檔 Task 2.3 的 `sort_order` 互斥）；§C-10「切特徵舊圖保留／錯誤重試」寫在實作要點與 UAT，但 vitest 未鎖，且 page 案例④以 `featureDetail=null` 鼓勵清空。

**進 B0 前最後一件必須改**：TODO Task 2.2 `:143` 把 `onParamsChange({sort_by, order, offset:0})` 改成 `{sort_by, sort_order, offset:0}`（與 Task 2.3／SPEC 一致）。P2 可同輪補 vitest。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` | TEMPLATE PASS；rc=0 |
| `bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` | TEMPLATE PASS；rc=0 |
| `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` | `{"st":39346,"meta_keys":39398}` |
| `shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` | **rc=0** 全 OK |
| `venv/bin/python handoffs/_light_size_probe.py` | `light_bytes` 路徑仍可跑（本輪未改碼） |
| HEAD | `ad02df91` |

### 延遲實測（X6／§C-9；純函式層，暖機後）

對 `data_cache/reports/ic_report_ic_gatekeeper.json` 的 39,346 列：

| 操作 | p50 | p95 | 對照預算 |
|---|---|---|---|
| `icir` 排序（§C-8 缺值沉底＋名次鍵） | 23.4 ms | 23.5 ms | summary ≤100／200 |
| `feature_name` 排序 | 8.5 ms | 8.9 ms | 同上 |
| `search=close`＋排序＋切片（11133 命中） | 11.1 ms | 11.1 ms | 同上 |
| light 投影＋`json.dumps`（含首頁 50 列） | 26.7 ms | 28.1 ms | light ≤150／300 |
| feature 單鍵投影＋dumps | 0.02 ms | 0.02 ms | feature ≤50／100 |
| 排序索引 list×8 粗估 | ~11 MB | — | 無 byte 上限；8 組／task 合理 |

結論：預算數字在 FastAPI＋TestClient 下**可達**（純算已遠低於 p50 門檻；TestClient 路由開銷通常遠小於剩餘裕度）。LRU 命中後只切片，≪ 20 ms。G-9「同探針三態＋20 次 p50／p95」可重現；與 G-5 共用探針合理（artifact 缺席 → BLOCKED）。

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| `task_info["result"]` completed 後只有 refilter 改寫 | **fact-verified**：`:1623`／`:2339`（`_run_full_analysis`）／`:2631`（refilter）。completed 後僅 refilter 覆寫。 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified（IC 頁）**：`Object.keys/entries(report` 僅 pattern comparison；IC 頁以單鍵取段。 |
| `metadata.selection_scope` 消費者 | **fact-verified**：orchestrator 寫入；`survivor_contract.py:598,615` 只取 `.scope_id`；frontend 無讀。 |
| 既有匯出端點 | **fact-verified**：`api/routes/ic_analysis.py:649` `GET /export/{task_id}/{format}`。 |
| 加 `view` 不改預設序列化 | **assumed（讀碼）**：現行 `get_result` 無 `response_model`（`:347`）。G-1 raw sha 才是機器證據。 |

---

## X1–X6 原反例複驗

| X | 複驗 | 狀態 |
|---|---|---|
| X1 AST 守衛 | SPEC `:65`／TODO `:49`：`_set_result` 體內恰 1、體外 0；不用註記排除。AST 走訪可行。 | **CLOSED** |
| X2 `SIZE_GATE` | 唯一文法 `SIZE_GATE=PASS\|FAIL\|BLOCKED`＋`SIZE_REASON=`；gate：≠1 行⇒rc=1；FAIL⇒rc=1；BLOCKED 轉印不改 rc；PASS 繼續。 | **CLOSED** |
| X3 `dict_count_key`＋順序 | contract `dict_count_key:"count"`；先 `filter_log_funnel` 再 counts；G-8 stage5 `output:0`；P12／P13。實機 before counts output=0（count 鍵）、after counts 鍵變 `output_features_count`⇒funnel 會 null——順序釘死後閉合。 | **CLOSED** |
| X4 G-7b sentinel | `NEW__` 前綴＋不同 total；斷言 revision／total／列名皆舊世代；feature 同法。 | **CLOSED** |
| X5 page 六案例 | fixture 不含 `summary_table`；①`<tr>==51` ②排序 callback ③detail ④載入中 ⑤六圖 ⑥漏斗不適用。 | **CLOSED** |
| X6 效能／體驗／FF 名 | §C-9／10、G-9、LRU、預算實測可達；**無 `q` 殘留**；**仍殘 `order`**（P1-01）；體驗項 vitest 缺口（P2-01）。 | **部分 CLOSED** |

---

## 必答（成對）

### 1a. 預設 `/result` 仍可能被改變的方式
① `view` 預設誤非 `None`；②為新模型替 `get_result` 加 `response_model` ⇒ 丟鍵／改序列化；③`deny_factor_in_ok_oos` 挪到投影後、或預設路徑多跑 normalize／鍵排序。

### 1b. G-1 能否抓到
**能抓多數**：誤套 light、丟鍵、normalize 改字面 ⇒ raw sha 紅。抓不到：只改 OpenAPI 簽名不動 body。須搭配 mutation P6。

### 2a. light 會刪但前端仍在讀的鍵
依 §C-6＋顯式 keep，IC 頁消費者應保留。本輪未找到「前端仍讀且會被刪」的 metadata 鍵。`page.tsx` 仍讀的 per-feature 段屬 B2 同批改吃 `featureDetail`。

### 2b. 該刪卻沒進刪段、會破 G-5 的段
七段已列。若 agent **忘刪** `turnover_analysis`（51 MB）或忘轉 `selection_scope` 兩 list ⇒ G-5 紅（P4／P9）。無新增遺漏段。

### 3a. 後端 sort_policy vs 前端 getSortValue——同序？
**不同序**（有意）。反例輸入 `[b:None,a:None,c:0.5,d:0.5]` desc：前端≈`[c,d,b,a]`（缺值 `-inf`、無次鍵、stable；`ICSummaryTable.tsx:91-106`）；後端=`[c,d,a,b]`（缺值沉底＋`feature_name` 次鍵）。

### 3b. 哪邊對
**後端決定性次鍵**（分頁跨頁穩定）。SPEC §C-8 已宣告有意變更。

### 4a. G-2／G-3 在 refilter 後；競態
G-2／G-3 綁同一 `result_revision`；不符 ⇒ 409。投影用 lock 內 snapshot。G-7a/b/c 覆蓋交錯／中途 refilter／`view=light` handshake。前端丟棄 `revision != store`。

### 4b. 不做版本戳的代價
跨頁混代；G-2 無法區分投影 bug vs 競態。本票已要求戳。

### 5a. Task 2.3 匯出：逐頁 vs 既有端點
**既有 `/export` 對**；Task 2.3 零改匯出。碼證：route `:649`；`ExportButtons` 組該 URL。

### 5b. 逐頁 39k 可接受時間
不採納（已刪）。序列約 79×(50–200ms)≈4–16s，劣於一次 export。

### 6. ≥10× 不必要複雜？
**否**。golden＝小 fixture 全特徵；contract JSON 必要；mutation P1–P14 對應 §V；LRU 8 組是對 O(n log n) 的最小必要快取，非框架膨脹。Task 0.1 無 200 抽樣。

### 7. B2「一次切換」vs「先只換表格」；殘留；IP-RESID-3
- **風險較小**：B2 單批 cutover（已落 §B）。
- **IP-RESID-1／2**：`blocked-by` 落檔／golden（命中 a）**成立**。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣**成立**；不取代。
- **IP-RESID-4**（keep_keys 單一來源，blocked-by Task 0.1）**成立**。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **有**——Task 2.2 `order` vs 全檔 `sort_order`（P1-01） |
| 2 | 漏項 | §C-10 舊圖保留／重試未進 vitest（P2-01）；B3 批次 Gate 列只寫 `SIZE_GATE=PASS`，`LATENCY_GATE` 只在 Task 3.1（不另開 finding——Task 層已鎖） |
| 3 | 不可測 | G-1～G-9 可證偽；延遲預算本輪實測可達 |
| 4 | quant | 無（不改數值／落檔） |
| 5 | 過度工程 | 無（LRU 8 組必要） |
| 6 | OOM | light ~28KB；索引×8 ~11MB；無 |
| 7 | Cache | 排序索引 key 含 revision；P14 鎖；無 |
| 8 | API／相容 | 預設路徑＋v2 矩陣足夠；FF 名對齊除 `order` 殘留外完整 |
| 9 | 測試 | X5 六案例足夠；體驗兩項未鎖（P2-01） |
| 10 | Agent 可執行 | Task 具體；`order` 殘留會讓 agent 跟錯檔案描述（P1-01） |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| X1–X5 文件已閉合 | **真** | 上表 |
| §C-9 預算對 39k 可達 | **真（本機純函式）** | 上表實測；TestClient 全路徑仍待 G-9 實作後驗 |
| FF 參數名已無 `order`／`q` 殘留 | **假（有 `order`）** | TODO `:143` |
| §C-10 各項皆有 vitest | **假** | 舊圖保留／重試缺測 |
| completed 後僅 refilter 改 result | **真** | 三賦值點 |
| LRU 8 組記憶體可接受 | **真（粗估 ~11MB）** | 無 byte 上限；建議實作時只快取 index 不快取 row 複本 |

---

## GROK-R4-P1-01

**斷言**: TODO Task 2.2 檔案描述仍寫 `onParamsChange({sort_by, order, offset:0})`，與 SPEC／TODO 其餘處及 Task 2.3 驗證期望的 `sort_order`（FF `/browse` 對齊）互斥；agent 依字面實作會送錯鍵。

**碼證**: TODO `:143` 原文含 `{sort_by, order, offset:0}`；同檔 `:144`／`:160`／SPEC `:43`／`:72`／`:114` 皆為 `sort_order`；`grep -n order docs/ICRESULT_PAGING_TODO.md | grep -v sort_order` 僅命中 `:143`；無 `q` 殘留。FF 實碼：`frontend/src/hooks/useFeatureFactory.ts:280-281` 組 `sort_by`／`sort_order`。`RECHECK:` 同上 grep；修後該行不得再含獨立鍵名 `order`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418

[MAJOR] 信心度=High。失敗：SortButton 回呼帶 `order` ⇒ API／store 忽略或 400；或 Task 2.3 vitest 期望 `sort_order` 紅。修法：`:143` 一字改 `sort_order`（與 `:160` 案例②一致）。

---

## GROK-R4-P2-01

**斷言**: SPEC §C-10／Task 3.1 要求「切特徵時保留舊圖＋loading 遮罩」與「請求失敗可重試」，但 Task 2.2／2.3 的 vitest 清單未鎖這兩項；page 案例④以 `featureDetail=null ⇒ 載入中` 反而鼓勵切換時清空，可能通過測試卻違反不閃白。

**碼證**: SPEC `:42`「切換期間保留舊圖並加 loading 遮罩」「請求失敗顯示可重試按鈕」；TODO `:144`⑦ 有重試實作要點，`:153`／`:160` 驗證列無「舊 detail 仍在 DOM」「重試按鈕」斷言；`:160`④＝`featureDetail=null`。`RECHECK:` 對照上述行；修法建議：案例改「切換中 `featureDetail` 仍為舊值且出現遮罩」；另加失敗→重試按鈕一案。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241

[MINOR] 信心度=Medium。失敗：agent 切特徵先 `setFeatureDetail(null)` 通過現有六案例，UAT 仍閃白。修法：補 vitest；案例④改為「初始 null」與「切換保留舊值」分開。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；X1–X5 文件閉合；39k 排序／light／feature 延遲實測；`order` 唯一殘留於 TODO:143；三 result 賦值點；selection_scope／export／FF sort_by|sort_order  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` rc=0；venv 39k sort／light／feature 計時；`grep` order／q／AST／SIZE_GATE／NEW__／六案例（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-grok.md`

STATUS: DONE
