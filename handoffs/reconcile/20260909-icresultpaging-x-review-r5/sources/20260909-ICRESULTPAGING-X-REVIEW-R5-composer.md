brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R5
family: composer
findings-round: R5
標的 commit: HEAD（SPEC R4 修訂＋TODO；**尚未實作**）
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#54626e187238

## Verdict：可派工

R4 六群集 W1–W6 均已落文件；本輪原提出方重跑同一反例 **CLOSED**。本輪 **無 P0／P1**。**進 B0 前最後一件必做事**：無（可直接開 Task 0.1 golden／contract 凍結）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| template_check 兩份 | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → TEMPLATE PASS，rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' …` → `{"st":39346,"meta_keys":39398}` |
| baseline 未漂移 | **fact-verified** | `shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` → 全 OK，rc=0 |
| completed 後僅 refilter 改 result | **fact-verified** | `grep -n 'task_info\["result"\]' api/services/ic_analysis_service.py` → `:1623`／`:2339`／`:2631`；SPEC §A FACT-RECEIPT 已列 |
| 前端無 IC 頁讀 per-feature 全量 map | **fact-verified** | `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` → 僅 pattern comparison 元件，無 `ic-analysis` 命中 |
| `selection_scope` 消費者 | **fact-verified** | `survivor_contract.py:598,615` 讀 `scope_id`；contract `metadata_keep_keys` 含 `selection_scope`（TODO Task 0.1） |
| 匯出已有全量端點 | **fact-verified** | `GET /export/{task_id}/{format}` `ic_analysis.py:649`；`export_analysis` 讀 `task_info["result"]` `:1896` |
| G-9 TestClient 延遲可 PASS | **assumed（設計合理）** | 探針函式尚不存在（Task 0.1 `--latency`）；39k 檔案級 JSON 載入＋純 Python 投影遠低於 §C-9 門檻 |
| 雙樹記憶體可接受 | **assumed（有量化）** | `deepcopy` 探針：單樹 ~195MB、雙持有 ~390MB in-process（118.9MB 落檔）；本票登記 `IP-RESID-5` 只限排序快取，未限 `_tasks` 總 RSS |

---

## W1–W6 群集複驗

| 群集 | R4 處置 | R5 複驗 | 狀態 |
|---|---|---|---|
| **W1** 寫入時正規化＋守衛快照 | §C-7 `_set_result` 存 `result_normalized`；投影 spy==0；預設 `/result` 不變 | SPEC `:37`／TODO Task 1.0 `:47-49` 一致；`get_result` 仍 `:1783-1788` 對 `result` 現算正規化＋守衛（G-1 路徑不變）；雙持有記憶體見下節裁定 | **CLOSED** |
| **W2** `rolling_ic_series` 接回 | Task 2.3 `sectionSplit`／page 案例⑤ | TODO `:159-160` 六段含 `rolling_ic_series`；page 案例⑤斷言 `RollingICChart` 收到序列；現行 `page.tsx:880-882` 仍讀全量（實作前預期） | **CLOSED** |
| **W3** `LATENCY_GATE` 文法 | G-9 warm-up 3＋20、p95 第 19 小、固定請求集 | SPEC G-9 `:57`；TODO `:26` gate 偽碼對 `LATENCY_GATE=` 與 `SIZE_GATE=` 同規則 | **CLOSED** |
| **W4** 快取容量 | `numpy.int32`＋32 task process-wide LRU＋`cache_bytes()` | SPEC §C-9 `:41`；TODO `:65`／`:76` 33 task×8 組容量測；`IP-RESID-5` 三值 `blocked-by:` 成立 | **CLOSED** |
| **W5** `order`／150 ms | 統一 `sort_order`、300 ms 去抖 | `grep 'sort_by, order'` TODO → 0（`:143` 已改 `sort_order`）；`grep '150 ms'` docs → 0 | **CLOSED** |
| **W6** UX 遮罩／重試 vitest | page 案例⑦⑧＋§C-10 禁止清空 | SPEC Task 2.3 `:114`／TODO `:160` 八案例含 overlay＋reject 重試 | **CLOSED** |

### W1 記憶體／守衛語意裁定（brief 必追）

**記憶體會不會翻倍？** **會（in-process 物件樹）**。§C-7 明定同時存 `task_info["result"]` 與 `result_normalized`。VERIFY：`venv/bin/python` `copy.deepcopy` 探針 → 單樹 ~195MB、雙持有 ~390MB（118.9MB 落檔 JSON）。排序 LRU 上限 ~40MB（SPEC §C-9）與雙樹相比為次級。

**可否只留 normalized 且 G-1 不變？** **否（在不改 G-1 定義下）**。預設 `/result` golden 綁定現行 `get_result`：讀 `result` → `_to_json_compatible` → `deny_factor_in_ok_oos` → `response.content`（route `:346-353` 無 `response_model`）。`export_analysis` 亦讀 raw `task_info["result"]`（`:1896`）。刪 raw 樹或改寫入點會動匯出／golden 語意，超出本票「預設路徑一 byte 不變」。

**守衛 raise 時 task 狀態？** **寫入路徑將比現行更嚴**（刻意）。現行 completion `:1623` 先寫 `result`，callback `:1647-1654` 對 deny **catch** 僅降級 payload；`get_result` `:1788` deny **raise** → 500。Task 1.0 邊界④／§C-7：`_set_result` 內 deny raise ⇒ 不寫入、revision 不變、task **failed**——三寫點全改經 helper 後統一；與「讀取時 raise 同一例外類型」一致，但**終態**由現行 completed+degraded 改為 failed（可接受，因 deny 本來就阻 `/result`）。

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a**：`view` 預設誤走 light；route 加 `response_model` 重序列化；`deny_factor_in_ok_oos` 順序／突變；對 live dict 原地 `pop`（違 snapshot）；`_set_result` 誤改 default 分支。
- **1b**：**能**——G-1 `raw_body_sha256`（TestClient `response.content`）＋mutation P6；抓不到純 OpenAPI 描述漂移（route 現無 `response_model`）。

### 2a／2b light 刪段＋metadata

- **2a**：**當下無**——§A receipt 前端鍵（`oos_downgrade`／`period_alignment`／`isolation` 等）⊆ Task 0.1 `metadata_keep_keys`；per-feature 段改走 `featureDetail`（B2 同批）。
- **2b**：漏刪七段或漏 `collection_to_count_paths`（`winsorized_features` ~1.6MB）⇒ G-5 紅；無新漏段。

### 3a／3b 排序

- **3a**：後端 contract `sort_policy`（缺值兩向沉底＋`feature_name` 次鍵）vs 現 `ICSummaryTable.getSortValue`（`:91-106`：非有限→`-Infinity`、tie 回 0 無次鍵）**不同序**；39k `icir` 全 null ⇒ 分頁字母序 vs 現插入序。
- **3b**：**後端為準**（§C-8 明文「分頁序取代前端本地序＝有意行為變更」）。

### 4a／4b refilter／競態

- **4a**：`result_revision` int 遞增；summary／feature 帶 `revision` 不符 ⇒ 409；lock 內 snapshot `(result_normalized, revision)`；G-7a/b/c；前端 abort＋revision 不符丟棄（§C-7）。
- **4b**：無戳 ⇒ 跨 refilter 混頁、G-2 不可證偽；§A 已 fact-verify 三寫點會替換 result。

### 5a／5b 匯出

- **5a**：**既有** `GET /export/{task_id}/{format}`（`csv_summary`／`csv_detailed`／`json` 等）讀全量 `task_info["result"]`；Task 2.3 明列「匯出零改動／不做逐頁匯出」。
- **5b**：逐頁 39k（787 頁×50）為分鐘級且無 UI 規格；本票不採；使用者匯出走既有端點一次下載。

### 6 ≥10× 不必要複雜

**無**。14 特徵 fixture 全量 golden（不抽樣）、contract SoT、mutation P1–P16 對應 §G／§V；G-9 `--latency` 延伸同一探針合理。

### 7 B2／IP-RESID

- **B2 單批 cutover** 風險小於拆分（light 已開而六圖仍讀已刪段＝退化中間態；R2 `CODEX-R2-P1-05`）。
- **IP-RESID-1/2/4**：`blocked-by:` 落檔／Task 0.1 成立。
- **IP-RESID-3**：`user-ruling:` 並存＋四格矩陣，不取代 v2。
- **IP-RESID-5**：`blocked-by:` 另票；本票只限排序快取 bytes。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無（W5 已清） |
| 2 | 漏項 | 無 blocking |
| 3 | 不可測 | G-1～G-9／八案例 page 整合可機械驗 |
| 4 | quant | 無新 leakage；deny 守衛不可省 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 雙樹 ~390MB/task 已知；LRU ~40MB 有上限；`_tasks` 無界登記 IP-RESID-5 |
| 7 | cache | revision 失效＋32 task LRU 可測 |
| 8 | API | FF `sort_by`／`sort_order` 對齊；v2×light ⇒ 400 |
| 9 | 測試 | G-7b sentinel＋page 八案例足 |
| 10 | Agent | Task 精確到檔案／函式 |
| 11 | 短命工 | 無 |

---

## COMPOSER-R5-P3-00

**斷言**: 本輪對 R4 群集 W1–W6、必答 1–7、§1 十一類與 §0 可覆核前提逐項重判後，無需新增 P0／P1／P2 finding。

**碼證**: `bash scripts/template_check.sh spec|todo` rc=0；`jq` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` rc=0；W5 `grep '150 ms\|sort_by, order' docs/ICRESULT_PAGING*.md` → 0；W2/W6 TODO `:159-160` 八案例；W3 SPEC G-9 `:57`；W4 §C-9 `:41`＋`IP-RESID-5`；W1 §C-7 `:37`＋`get_result` `:1783-1788`＋deepcopy 雙樹探針；brief「我沒查的」四項均已 RECHECK（見 §0 表）。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238

[NON-BLOCKING] 信心度=High。R4 W1–W6 修訂已閉合；停輪三條件①必答雙向有碼證 ②無 P0 ③必答 6/7 明確——均滿足。Verdict：**可派工**；B0 前無額外文件修補。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha rc=0；W1–W6 逐段對照 SPEC/TODO；brief 四項 NOT_RUN 已 RECHECK；deepcopy 雙樹記憶體；grep order/150ms/Object.keys；export route 649；get_result route 346
TESTS_RUN: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` rc=0；`bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` rc=0；`jq -c '{st:(.summary_table|length), meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` rc=0；`grep` order/150ms/selection_scope/export；deepcopy memory probe
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R5-composer.md`

STATUS: DONE
