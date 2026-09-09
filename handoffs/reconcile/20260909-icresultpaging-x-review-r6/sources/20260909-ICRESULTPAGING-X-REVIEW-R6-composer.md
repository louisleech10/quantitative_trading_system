brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R6
family: composer
findings-round: R6
標的 commit: HEAD（SPEC R5 修訂＋TODO；**尚未實作**）
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#ec0771609868
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#09e62c65bc1f

## Verdict：可派工

R5 群集 V1–V6（原 W1–W6 修訂）均已落文件；本輪原提出方重跑同一反例 **CLOSED**。本輪 **無 P0／P1**。**進 B0 前最後一件必做事**：無（可直接開 Task 0.1 golden／contract 凍結）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| template_check 兩份 | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → TEMPLATE PASS，rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' …` → `{"st":39346,"meta_keys":39398}` |
| baseline 未漂移 | **fact-verified** | `shasum -a 256 -c handoffs/20260909-icresult-r6-baseline.sha` → 全 OK，rc=0 |
| `_to_json_compatible` 對已 normalized 樹冪等 | **fact-verified** | 39k 報告：`n1==n2` True；canonical sha 兩次相同（見 V1 探針） |
| completed 後僅 refilter 改 result | **fact-verified** | `grep -n 'task_info\["result"\]' api/services/ic_analysis_service.py` → `:1623`／`:2339`／`:2631` |
| 前端無 IC 頁讀 per-feature 全量 map | **fact-verified** | `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` → 僅 pattern comparison；IC 頁仍單鍵讀 `rolling_ic_series`（B2 改吃 featureDetail，預期） |
| `selection_scope` 消費者 | **fact-verified** | `survivor_contract.py:598,615` 讀 `scope_id`；contract `metadata_keep_keys` 含 `selection_scope` |
| 匯出已有全量端點 | **fact-verified** | `GET /export/{task_id}/{format}` `ic_analysis.py:649`；`export_analysis` 讀 `task_info["result"]` `:1896` |
| G-9 TestClient 延遲可 PASS | **assumed（設計合理）** | 探針／gate 腳本尚不存在（Task 0.1）；39k 純 Python 投影已遠低於 §C-9 門檻 |
| refilter 守衛失敗回 422 | **assumed（文件一致）** | 現行 route `ValueError→400`、service 先寫後 `get_result` 可能 500；SPEC／TODO 已明定先驗後寫＋422，屬實作差異非文件矛盾 |

---

## V1–V6 群集複驗

| 群集 | R5 處置 | R6 複驗 | 狀態 |
|---|---|---|---|
| **V1** 單一 normalized 樹＋冪等 G-1 | §C-7 只保留 `task_info["result"]`；預設 `/result` 讀取碼不改 | `grep -c result_normalized docs/ICRESULT_PAGING*.md` → 0；Task 1.0 `:56` 斷言 `_to_json_compatible(normalized)==normalized`；39k 探針 `equal_structural True`；`export_analysis`／`apply_transforms` 讀同一 `task_info["result"]`（`:1896`／`:2532`），export `dict(report)` ＋ `sanitize_factor_returns` 回新物件、不寫回 `_tasks` | **CLOSED** |
| **V2** 守衛 raise／refilter 422 | §C-7 (a)(b)；Task 1.0 邊界④⑤ | 現行三寫點 `:1623`／`:2339`／`:2631` 仍直接賦值；completion callback `:1647-1654` catch deny 仍 completed；refilter `:2631` 先寫再 `get_result`（讀時 deny raise→500）。文件已列全差異＋目標語意（failed／422／先驗後寫）；422 vs 400：SPEC 定 422，現行 `refilter` route `:608-610` 僅 `ValueError→400`——實作時須顯式映射，文件無互斥 | **CLOSED** |
| **V3** gate `--size`／`--latency`／parser | G-9 `:57`；TODO `:18` gate 3；`test_phase_gate_parser` | SPEC G-9 消費點＝gate 1 `--size`、gate 3 `--size --latency`；TODO `:26`／`:119` 與 `SIZE_GATE` 同規則；腳本／測試檔尚未存在 ⇒ Task 0.1 `BLOCKED` 預期，不可繞過（無第二 parser） | **CLOSED** |
| **V4** snapshot 不可變＋投影成本 | R5 `CODEX-R5-P1-04`；淺 dict 投影 | TODO Task 1.3 `:101` light×2→summary→feature 七段 deep-equal；`project_light_view` 禁 pop、頂層建新 dict；39k 只 omit 七段鍵＋metadata 白名單/filter_log 計數，不複製 39k per-feature 子樹到新 dict ⇒ §C-9 可接受 | **CLOSED** |
| **V5** grep 殘留 | 清 `result_normalized`／`lock 內取 result`／`deny 先跑`／`order`／150 ms 去抖 | `result_normalized` docs → 0；`lock 內取 result\|deny 先跑` → 僅 SPEC `:4` 修訂史（非 Task 指令）；`150 ms\|sort_by, order` → 0 | **CLOSED** |
| **V6** debounce／cache／Omit | R5 debounce owner；`cache_bytes`；七段 Omit | TODO Task 2.1 hook 不去抖、表格搜尋框 300 ms；§C-9 `numpy.int32`＋32 task＋`cache_bytes()`；`ICReportLight` Omit 七段含 `rolling_ic_series`（TODO `:125`） | **CLOSED** |

### V1 冪等／就地改寫裁定

**冪等是否成立？** **是（結構相等）**。`_to_json_compatible` `:2819-2880` 對已是 `None`／有限 `float`／`str|int|bool` 早退；39k JSON 載入後第二遍 `n1==n2` True，sorted canonical sha 相同。

**export／apply-transforms 是否就地改寫 `_tasks` 內樹？** **否（讀路徑）**。`export_analysis` 淺拷貝 `dict(report)`；json 分支 `sanitize_factor_returns(report)` docstring 標「冪等 pure function」且回新物件（`factor_return_sanitizer.py:80-92`），未回寫 `task_info["result"]`。`apply_transforms` 只讀 `:2532` 取 status 寫 HDF5，不 mutate report。

**記憶體**：R5 雙樹問題已收斂為單樹（§C-7）；本輪無新翻倍主張。

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a**：`view` 預設誤走 light；route 加 `response_model`（現 `:346-353` 無）；`deny_factor_in_ok_oos` 順序／突變；投影 `pop` 污染 live 樹；`_set_result` 誤改 default 分支跳過第二遍 normalize。
- **1b**：**能**——G-1 `raw_body_sha256`＋mutation P6；冪等前提下預設路徑仍 `_to_json_compatible`→`deny`→return，與今日位元組等價；抓不到純 OpenAPI 漂移。

### 2a／2b light 刪段＋metadata

- **2a**：B2 前 `page.tsx:880-882` 仍讀 `report.rolling_ic_series[activeFeature]`（已列 drop，B2 改 featureDetail）。metadata：§A receipt 前端鍵 ⊆ `metadata_keep_keys`；無新「前端仍讀卻被刪」鍵。
- **2b**：漏刪七段或漏 `collection_to_count_paths`（`winsorized_features` ~1.6MB）⇒ G-5 紅；無新漏段。

### 3a／3b 排序

- **3a**：後端 contract `sort_policy`（缺值兩向沉底＋`feature_name` 次鍵）vs 現 `ICSummaryTable.getSortValue`（`:91-106`：非有限→`-Infinity`、tie 0 無次鍵）**不同序**；39k `icir` 全 null ⇒ 字母序 vs 插入序。
- **3b**：**後端為準**（§C-8 明文「分頁序取代前端本地序＝有意行為變更」）。

### 4a／4b refilter／競態

- **4a**：`result_revision` 遞增；summary／feature 帶 `revision` 不符 ⇒ 409；lock 內 snapshot `(normalized, revision)`；G-7a/b/c；前端 abort＋revision 不符丟棄。
- **4b**：無戳 ⇒ 跨 refilter 混頁、G-2 不可證偽；§A 已 fact-verify 三寫點會替換 result。

### 5a／5b 匯出

- **5a**：**既有** `GET /export/{task_id}/{format}` 讀全量 `task_info["result"]`；Task 2.3 明列匯出零改動／不做逐頁匯出。
- **5b**：逐頁 39k（787 頁×50）為分鐘級且無 UI 規格；本票不採；使用者走既有端點一次下載。

### 6 ≥10× 不必要複雜

**無**。14 特徵 fixture 全量 golden（不抽樣）、contract SoT、mutation P1–P16 對應 §G／§V；G-9 `--latency` 延伸同一探針合理。

### 7 B2／IP-RESID

- **B2 單批 cutover** 風險小於拆分（light 已開而六圖仍讀已刪段＝退化中間態）。
- **IP-RESID-1/2/4/5**：三值 `blocked-by:` 成立。
- **IP-RESID-3**：`user-ruling:` 並存＋四格矩陣，不取代 v2。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無（V5 殘留已清；V2 現行 vs 目標語意已分列） |
| 2 | 漏項 | 無 blocking |
| 3 | 不可測 | G-1～G-9／八案例 page 整合可機械驗 |
| 4 | quant | 無新 leakage；deny 守衛不可省 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 單樹 ~119MB 落檔；排序 LRU 有上限；`_tasks` 無界登記 IP-RESID-5 |
| 7 | cache | revision 失效＋32 task LRU 可測 |
| 8 | API | FF `sort_by`／`sort_order` 對齊；v2×light ⇒ 400 |
| 9 | 測試 | G-7b sentinel＋page 八案例足 |
| 10 | Agent | Task 精確到檔案／函式 |
| 11 | 短命工 | 無 |

---

## COMPOSER-R6-P3-00

**斷言**: 本輪對 R5 群集 V1–V6、必答 1–7、§1 十一類與 §0 可覆核前提逐項重判後，無需新增 P0／P1／P2 finding。

**碼證**: `bash scripts/template_check.sh spec|todo` rc=0；`jq` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r6-baseline.sha` rc=0；V1 39k `_to_json_compatible` 冪等探針 `equal_structural True`；V5 `grep -c result_normalized docs/ICRESULT_PAGING*.md` → 0；V2 三寫點 `:1623/:2339/:2631` + §C-7 (a)(b)；V3 SPEC G-9 `:57` + TODO gate 3 `:18`；V4 TODO Task 1.3 `:101` snapshot 測試；V6 TODO `:125` Omit 七段；brief「我沒查的」四項均已 RECHECK（見 §0 表）。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ec0771609868; docs/ICRESULT_PAGING_TODO.md#09e62c65bc1f

[NON-BLOCKING] 信心度=High。R5 V1–V6 修訂已閉合；停輪三條件①必答雙向有碼證 ②無 P0 ③必答 6/7 明確——均滿足。Verdict：**可派工**；B0 前無額外文件修補。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha rc=0；V1–V6 逐段對照 SPEC/TODO；39k 冪等探針；grep result_normalized/selection_scope/export/Object.keys；三寫點與 export/apply-transforms 讀路徑
TESTS_RUN: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` rc=0；`bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` rc=0；`jq -c '{st:(.summary_table|length), meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r6-baseline.sha` rc=0；39k idempotency probe rc=0；brief greps rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R6-composer.md`

/tmp workdir: 無需清理之 probe 檔（僅 inline python）；保留 `claude-501`

STATUS: DONE
