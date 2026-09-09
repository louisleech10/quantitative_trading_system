# Reconcile — 20260909-icresultpaging-x-review-r5

**來源** 20260909-ICRESULTPAGING-X-REVIEW-R5-codex.md, 20260909-ICRESULTPAGING-X-REVIEW-R5-composer.md, 20260909-ICRESULTPAGING-X-REVIEW-R5-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可派工，W1–W6 CLOSED，無新 P0／P1，進 B0 前最後一件＝無」（sentinel `COMPOSER-R5-P3-00`）；codex 4 P1＋2 P2；grok 2 P1＋1 P2。皆文件層，已修訂為 SPEC（R5 修訂）／TODO；R6 複驗。

### V1 — P1 同時保留 `result` 與 `result_normalized` ⇒ 每 task 兩棵 119 MB 樹（`CODEX-R5-P1-01`）
**處置**：只留一棵：`task_info["result"]` 即 normalized 物件；既有讀者照讀；預設 `/result` 讀取碼不改，靠冪等（`_to_json_compatible(n)==n` 測試）維持 G-1；多 task memory receipt。

### V2 — P1 守衛 raise 之寫點語意與現行不一致；refilter 先寫壞再讀時 500（`CODEX-R5-P1-02`）
**處置**：明定 (a) 初次完成 raise ⇒ failed、無 result；(b) refilter 先驗後寫、舊 result／revision 不變、completed、422（現行為缺陷，本票修）；各一條 TestClient 斷言。

### V3 — P1 `LATENCY_GATE` 無收案消費點（`CODEX-R5-P1-03`）
**處置**：`icresult_paging_phase_gate.sh 1` 跑 `--size`；`… 3` 跑 `--size --latency` 兩者須 PASS；parser 負向測試 `test_phase_gate_parser`；B1／B3 gate 行改寫。

### V4 — P1 snapshot 宣稱不可變但偽碼 `pop`（`CODEX-R5-P1-04`）
**處置**：投影禁 pop／就地改寫，一律鍵過濾建新 dict；測試 light×2→summary→feature 七段仍在且 deep-equal。

### V5 — P1 Task 1.1「lock 內取 result」、Task 1.3「deny 先跑」與 §C-7 互斥（`GROK-R5-P1-01`、`GROK-R5-P1-02`）
**處置**：兩處改為「經 `_snapshot_result`、守衛已於 `_set_result`、投影不再呼叫」；§0 同句改寫。

### V6 — P2 debounce owner 未定（`CODEX-R5-P2-01`）；快取 accounting／第 9 組／scope 未定（`CODEX-R5-P2-02`）；`ICReportLight` Omit 未含 rolling（`GROK-R5-P2-01`）
**處置**：owner＝表格搜尋框、hook 不去抖、fake timer 測試；`cache_bytes()`＝Σ nbytes、第 9 組淘汰 task 內 LRU、module 單例、兩 instance 共用測試；`IP-RESID-5` 射程限縮；Omit 對齊七段。

Verdict: 需修補後派工——V1–V6 已落文件；R6 三家複驗（單樹＋冪等 G-1、寫點失敗語意、gate 3 消費、不可變測試、Omit）。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P1-01
**斷言**: §C-7 同時保留 `result` 與完整 `result_normalized`，會把每個完成 task 的 119 MB 報告至少保留兩棵樹；只留 normalized 可行，但目前 export、task status、apply-transforms 仍直接讀 `task_info["result"]`，不是無條件替換。
**碼證**: SPEC:37,41／TODO:47-49；`ls -la data_cache/reports/ic_report_ic_gatekeeper.json`=118894891、`jq`=`{"st":39346,"meta_keys":39398}`；`_to_json_compatible` 會遞迴新建 dict/list（`api/services/ic_analysis_service.py:2819-2880`），既有 result 寫點 `:1623,:2339,:2631`，export 讀 `:1896`、apply-transforms 讀 `:2532`。RECHECK: `rg -n 'task_info\["result"\]|task_info.get\("result"\)' api/services/ic_analysis_service.py`。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4
P1 信心度=9/10；這直接違反跨 tier／多 task OOM 優先序，且 `IP-RESID-5` 不能替新造的第二棵樹背書。修法：選一個 canonical normalized storage（或明確 accessor），把所有 direct consumer 遷移後刪 duplicate；G-1 raw-body sha、export、status、apply-transforms 回歸須同過，並補多 task memory receipt。

## CODEX-R5-P1-02
**斷言**: 守衛 raise 的 task 狀態語意與現行行為不一致且 refilter 沒有失敗轉態；現行讀取時 raise 回 500 但 task 仍可見為 completed，現行 refilter 還會先寫入壞 report 再在 `get_result` raise。
**碼證**: 初次完成在 `api/services/ic_analysis_service.py:1618-1623` 設 completed，例外轉 failed 只在 `:1676-1685` 的背景 try；讀取守衛在 `:1772-1791`，route `:346-358` 只轉 500；refilter `:2621-2637` 先 `task_info["result"] = report` 再 `get_result`。TODO:48,56,100,111 卻要求 guard raise「不寫、revision 不變、task failed」且宣稱與現行等價。RECHECK: 以 guard 注入分別跑初次完成與 refilter，查 `/task/{id}`、舊 result、revision。
**來源摘要**: docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4; api/routes/ic_analysis.py#95216b9ddbf0
P1 信心度=10/10；需在 SPEC 固定每個 write path 的 failed/old-result/revision 組合，並加兩條 TestClient 斷言；否則實作會在「保留舊 completed」與「標 failed」間分叉。

## CODEX-R5-P1-03
**斷言**: G-9 的 warm-up、20 次、nearest-rank 第 19 小與固定請求集已可重現，但 LATENCY_GATE 尚未被批次 gate 的收案路徑 fail-closed 消費。
**碼證**: SPEC:57 宣稱 phase gate 與 SIZE_GATE 同規則；TODO:18、119 的 Phase 1/B1 gate 只寫 SIZE_GATE，TODO:189 只要求 `--latency` 印 PASS；`test -e scripts/icresult_paging_phase_gate.sh`→absent，repo 目前沒有 LATENCY_GATE parser。RECHECK: `rg -n 'icresult_paging_phase_gate|LATENCY_GATE|SIZE_GATE' scripts handoffs`，再餵缺行／多行／未知 LATENCY_GATE 的 probe output。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P1 信心度=9/10；若 B3 只看 probe rc 或人工 stdout，150/300、100/200、50/100 ms 預算可被跳過。修法：明列 `--latency` 的 gate invocation、唯一行數與 rc 0/1/2 轉換，並以 receipt/negative parser tests 鎖死。

## CODEX-R5-P1-04
**斷言**: 文件稱 snapshot 不可變，但 `_snapshot_result` 回傳可變 `dict`，而 `project_light_view` 偽碼明寫對 report `pop`；未要求 copy-on-write 或 source-unchanged 測試，第一次 light 請求可能破壞後續 summary/feature 投影。
**碼證**: SPEC:37「不可變 snapshot」；TODO:49 型別為 `tuple[dict,int]`，TODO:100 寫 `drop_sections` 各段 `pop`；Phase 1 測試清單 TODO:115-119 沒有「投影後 source 未變／連續兩次 light 相同／light 後 feature 仍可取」斷言。RECHECK: 對同一 fake task 連呼兩次 light，再呼 summary、feature，檢查 normalized snapshot 的七段仍在。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P1 信心度=8/10；修法：明定 immutable mapping 或 top-level/deep copy-on-write，並把 source immutability、重複請求、light→feature 順序列入 G-4/G-7 測試。

## CODEX-R5-P2-01
**斷言**: 搜尋 300 ms debounce 同時被分派給 hook (`TODO:125`) 與表格 (`TODO:144`)，責任未定義；兩層都做會變 600 ms，任一層漏做又會使另一條規格失真。
**碼證**: `docs/ICRESULT_PAGING_TODO.md:125` 寫 `fetchSummaryPage` 搜尋去抖 300 ms，`:144` 又寫搜尋框 300 ms；SPEC:42 只定數值未定 owner。RECHECK: `rg -n '去抖|300 ms' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md`。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P2 信心度=9/10；修法：指定唯一 debounce 層，另一層只傳值；測試 fake timer 只允許一次 300 ms 延遲與一次 API call。

## CODEX-R5-P2-02
**斷言**: 32-task／8-key LRU 的 `cache_bytes()` 可測性仍不足以證明 process-wide memory cap：未定義是否計入 dict/key overhead，也未鎖定每 task 第 9 組 key 的淘汰策略；`IP-RESID-5` 的 blocked-by 理由只涵蓋既有 `_tasks` lifecycle，不涵蓋本票新增 normalized/cache amplification。
**碼證**: SPEC:41、TODO:65,76 只給 `32×8×index_bytes(n)` 與 33 task case，未定義 `cache_bytes()` accounting 或 9th-key case；現行 `_tasks` 是無界 `api/services/ic_analysis_service.py:432-436`。RECHECK: 33 task×8 key、單 task 9 key、兩個 service instance 分別建立 cache，逐項驗 oldest eviction、`cache_bytes()` 與 process-wide scope。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4
P2 信心度=8/10；修法：定義 bytes accounting（至少 array.nbytes＋明確 metadata policy）、每 task eviction、module/process scope，並將三態理由改成「既有 task lifecycle 可另票；本票新增記憶體不得以此豁免」。

### 必答 1–7
1a/1b：一種可變 raw body 的實作是給 `/result` 加 response_model／讓 Pydantic 過濾或重排欄位；G-1 `response.content` sha 能抓到該 fixture 的變化，但不能代替多形狀 coverage。2a：現行 `page.tsx:880-882` 仍讀會被 light 刪的 `rolling_ic_series`；metadata 的 `n_timestamps`、`n_symbols`、`mode`、`event_filter`、`oos_downgrade` 都在 keep 聯集。2b：無；39k artifact 所有 >2 MB 段均在 drop_sections 或經 metadata/filter_log 投影處理，raw metadata 8.4 MB 不是保留 raw 證據。
3a/3b：現行 `ICSummaryTable.tsx:91-106` 把非有限值映成 `-Infinity`、並列回 0，故全 null 時保留輸入序且 asc 會置頂；新 backend contract 的兩向沉底＋feature_name 次鍵才是正確契約，前端舊序應被移除。4a/4b：refilter 後舊 revision 請求 409、無 revision 取新世代；不做戳會把舊 page 與新 total/feature 混在一個 UI，或讓舊 detail 覆蓋新 detail。
5a/5b：既有 `/api/v1/ic/export/{task_id}/{format}`（`ExportButtons.tsx:64-66`→`api/routes/ic_analysis.py:649-687`）是正確出口，Task 2.3 不應逐頁匯出；39k 逐頁在 UI 組裝不可接受且無必要。6：無明顯 ≥10× 不必要複雜；14-feature fixture 的全特徵 sha、contract JSON、mutation 是本票共享出口的合理固定成本。7：B2 一次切換風險較小；IP-RESID-1/2/3/4 三值理由成立，IP-RESID-5 對既有 lifecycle 成立但不能豁免 P1-01 的雙樹。

CHECKLIST: 矛盾/端到端/不可測＝P1-02/03/04；quant＝無；≥10×＝無；OOM/cache＝P1-01＋P2-02；API/型別＝無新 finding；測試＝P1-03/04、P2-01/02；必要性/短命工＝無。
ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` rc=0；todo 同命令 rc=0；`jq -c '{st:(.summary_table|length),meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json`→`{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` rc=0；order/150ms grep 無 stale query key；rolling、export、selection_scope、result writes 已逐碼對照。
TESTS_RUN: `bash scripts/template_check.sh ...`×2；jq；baseline sha；`grep -n 'task_info["result"] =' api/services/ic_analysis_service.py`→1623/2339/2631；`rg -n 'Object.keys(report|Object.entries(report' frontend/src`→僅 pattern comparison；未跑 `pytest tests/governance`、`npm run build`（brief 禁止）。
FAILURES_SEEN: 唯讀複合搜尋曾被 PreToolUse gate 誤判 dispatch；拆成窄命令後完成，無審查驗證失敗。
SCOPE_CHANGES: none（唯讀；只新增本交件檔）。
NUMERIC_OR_SCHEMA_IMPACT: 未改實作；提出結果儲存、task failure semantics、gate/test contract 修補建議。
HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-X-REVIEW-R5-codex.md
NEXT_BEFORE_B0: 關閉四個 P1，尤其先定 single normalized storage、refilter guard 狀態、LATENCY gate 收案接線、snapshot immutability；再重跑 brief 三條驗收與 baseline。
STATUS: DONE
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
