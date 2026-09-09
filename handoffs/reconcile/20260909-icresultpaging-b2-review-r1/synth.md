# Reconcile — 20260909-icresultpaging-b2-review-r1

**來源** 20260909-ICRESULTPAGING-B2-REVIEW-R1-codex.md, 20260909-ICRESULTPAGING-B2-REVIEW-R1-composer.md, 20260909-ICRESULTPAGING-B2-REVIEW-R1-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

三家「需修補後派工」；無 P0。codex 5 P1＋1 P2、composer 1 P1＋1 P2、grok 2 P1，皆前端／投影實作缺陷、皆附反例、皆已修並加測試。

### N1 — P1 `refilter` 回應無 `view:'light'` 仍 `setReport`（`CODEX-R1-P1-01`、`COMPOSER-R1-P1-01`、`GROK-R1-P1-02`）
**處置**：與 `fetchResult` 同形守衛：setError、不 setReport、保留舊 report；vitest 對稱案例。

### N2 — P1 `grouped_ic` 實機為三層 `{kind:{label:{feature:value}}}`，一層投影回全 null ⇒ 兩圖靜默空白（`GROK-R1-P1-01`）
**處置**：`project_feature` 改 `{kind:{label:value_for_feature}}`；探針參考實作同步、golden `--rebuild`（raw sha 不變）；前端 `reshapeGroupedForFeature` 還原 `{kind:{label:{feature:value}}}`；後端測試逐 label 對照 fixture 且斷言有有限值；前端 lib 測試。

### N3 — P1 取消表頭全選清掉所有頁（`CODEX-R1-P1-02`）
**處置**：取消＝只移當頁；測試 page50 取消後 page0 之勾選保留。

### N4 — P1 漏斗 `input=null, output=n` 以 output 回填（`CODEX-R1-P1-03`）
**處置**：任一 null ⇒ 不適用；測試。

### N5 — P1 detail 409 無重拉；revision null 當萬用（`CODEX-R1-P1-04`、`CODEX-R1-P1-05`）
**處置**：detail 409 ⇒ 以 `current_revision` 重拉一次、第二次 409 ⇒ error；summary／detail 對 `result_revision` 嚴格比較（null 亦丟棄並標「版本不相容」）；三條 vitest。

### N6 — P2 批次 Watchlist／Auto-Suggest 僅當頁未揭露（`CODEX-R1-P2-06`）；URL 還原 `search` 搜尋框不同步（`COMPOSER-R1-P2-01`）
**處置**：批次回寫回報「N 個不在當頁未處理」、Auto-Suggest 文案標「僅評分當頁」；表格以 effect 同步 `params.search`；測試。

Verdict: 需修補後派工——N1–N6 已修；vitest 全套綠、tsc 既有 8、pytest 41 綠；R2 由三家以同一反例複驗（refilter 全量 mock、三層 grouped、page50 取消、input null、detail 409、revision null、URL search）。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `refilter` 未驗證回應仍為 `view:'light'`，舊／部分升級後端可把全量 report 寫入 store，未顯示「後端版本過舊」且不阻止消費。 **碼證**: `frontend/src/hooks/useICAnalysis.ts:721-730` 直接 `setReport(result)`；同檔 `:133-138` 的 `fetchResult` 才有 view guard。RECHECK: mock `/refilter` 回 full report，斷言 `report===null` 且有版本錯誤。 **來源摘要**: frontend/src/hooks/useICAnalysis.ts#8386a196b35c; docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；修法是 refilter 與 fetchResult 共用 light response guard，非 light 回應不得寫入 report／summary。
## CODEX-R1-P1-02
**斷言**: 伺服器分頁表頭取消全選會清掉所有頁的 Set，而規格要求全選／取消只作用於當頁並保留跨頁選取。 **碼證**: `frontend/src/components/ic-analysis/ICSummaryTable.tsx:154-165`，unchecked 分支固定 `onSelectFeatures([])`。RECHECK: page0 勾選、page50 勾選、在 page50 取消表頭，預期只移除 page50 names。 **來源摘要**: frontend/src/components/ic-analysis/ICSummaryTable.tsx#63f62cf65a6; docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；會靜默改變 deep-analysis／transform 的 `selected_features` payload；修法是以當頁 names 從 Set 移除，其餘頁保留。
## CODEX-R1-P1-03
**斷言**: `FilterFunnelChart` 對 `input=null, output=number` 以 output 回填 input 並渲染，違反 null stage 顯示不適用且不得補假值。 **碼證**: `frontend/src/components/ic-analysis/FilterFunnelChart.tsx:25-35` 只檢查 output，並執行 `input: typeof input === 'number' ? input : output`；現有測試只覆蓋 output null／兩者 null。RECHECK: 傳 `{stage:{input:null,output:7}}`，預期 N/A、不出 chart row。 **來源摘要**: frontend/src/components/ic-analysis/FilterFunnelChart.tsx#ed2b78372385; docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；這會把未知資料呈成保留 7 個特徵，誤導篩選漏斗；修法是 input 或 output 任一為 null 即列 N/A。
## CODEX-R1-P1-04
**斷言**: feature-detail 端點回 409 時沒有依 `current_revision` 自動重拉一次，與 summary 的一次 retry 契約不一致。 **碼證**: route `api/routes/ic_analysis.py:404-417` 明確回 409；hook `frontend/src/hooks/useICAnalysis.ts:210-228` 只特判 404，其餘（含 409）直接 error。RECHECK: first feature response 409/current_revision=2，預期第二次帶 revision=2；現行僅一次 request。 **來源摘要**: frontend/src/hooks/useICAnalysis.ts#8386a196b35c; docs/ICRESULT_PAGING_TODO.md#42ea1a3af3b8
[P1/MAJOR] 信心度=High；refilter／寫入競速會讓合法特徵圖表落入 error，需加入與 summary 相同的上限一次 retry，第二次 409 才顯示錯誤。
## CODEX-R1-P1-05
**斷言**: revision 比對把 null 當 wildcard；response `result_revision=null` 與 store 的非 null revision 時仍會套用，違反「任何不等於 store revision 都丟棄」。 **碼證**: `frontend/src/hooks/useICAnalysis.ts:170-173,216-218` 條件同時要求兩側 non-null。RECHECK: store revision=5，mock summary／feature revision=null＋stale rows/detail，現行會 set 入 store。 **來源摘要**: frontend/src/hooks/useICAnalysis.ts#8386a196b35c; docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；部分升級／舊後端的無戳回應可穿透世代隔離；修法是嚴格比較（包括 null），並將未帶戳回應視為不相容錯誤或明確丟棄。
## CODEX-R1-P2-06
**斷言**: 跨頁選取的批次 Watchlist 操作只在目前頁找 row，跨頁 feature 會被靜默跳過；Auto-Suggest 也只評分目前頁且無「僅當頁」揭露。 **碼證**: `frontend/src/components/ic-analysis/ICSummaryTable.tsx:216-220,246-259` 使用 `sortedData.find`／只 map `sortedData`。RECHECK: selectedFeatures 含 page0＋page50，在 page0 執行批次 action，應更新兩筆但現行只更新 page0 可見筆。 **來源摘要**: frontend/src/components/ic-analysis/ICSummaryTable.tsx#63f62cf65a6; docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P2/MINOR] 信心度=High；不影響 deep-analysis payload，但會造成 UI 顯示的已選數與 Watchlist 實際更新數不一致；修法是提供跨頁 row/detail 來源，或明確標示 action 僅當頁並回報 skipped names。
必答 1–7：1a/1b refilter guard 缺口如 P1-01，fetchResult 本身有 guard；2a summary 有一次 retry、detail 無如 P1-04，null revision 會穿透如 P1-05；3a server sort 正確但 Auto-Suggest 僅當頁如 P2-06，3b Set payload 正常但取消全選破壞跨頁如 P1-02；4a grouped map 還原接線與既有圖表形狀一致，4b coverage_analysis 仍是型別註明的孤兒欄；5a 647 tests 綠但未覆蓋上述反例，故不能以全綠宣稱 UX／revision 完整，5b 300 ms 搜尋 debounce owner 不衝突；6 無 ≥10× 不必要複雜；7 B1 R1 四修補之 code/receipt 觀測閉合，但 phase gate 因 Binance DNS setup 失敗而 BLOCKED，B2 不可直接派工。
§1/§0 摘要：無新 P0；矛盾／quant／過度工程／短命工無新增 finding；端到端、API 相容、測試覆蓋問題即 P1-01～05；所有結論均有行號與 RECHECK，未把 network BLOCKED 誤判成產品失敗。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、SPEC/TODO、review skill；R7 stamp approved；baseline hash 只見既有 dirty files，未改其內容；候選 finding 均以現行碼與 SPEC 原文交叉核對。
TESTS_RUN: `(cd frontend && npx vitest run)` → rc=0，83 files/647 passed；`(cd frontend && npx tsc --noEmit -p tsconfig.json | grep -c 'error TS')` → 8（既有）；`venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` → rc=0，40 passed/0 skipped；`bash scripts/icresult_paging_phase_gate.sh 3` → rc=1，SIZE/LATENCY BLOCKED，Binance HTTPS DNS ConnectionError。
FAILURES_SEEN: phase gate setup network failure；未改 receipts/data_cache，未將環境 BLOCKED 當 finding。
SCOPE_CHANGES: none；唯讀 review，僅新增本交件檔；未跑禁止的 governance pytest／npm build。
NUMERIC_OR_SCHEMA_IMPACT: 未修改產品數值、API schema 或輸出大小；僅指出前端錯誤消費／選取語意。
HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R1-codex.md
STATUS: DONE
## COMPOSER-R1-P1-01

**斷言**: `refilter` 成功回應未驗 `view:'light'` 即 `setReport`，舊後端 refilter 全量回應會把整份 `summary_table` 留在 store，違反「不吃全量」且與 `fetchResult` 守衛不一致。

**碼證**: `frontend/src/hooks/useICAnalysis.ts:130-137`（fetchResult 無 light ⇒ setError、return null）；`:721-729`（refilter 直接 setReport）；`useICAnalysis.paging.test.ts:47-54` 僅覆蓋 fetchResult 舊版 case、無 refilter 對照。RECHECK：mock refilter 回 `{ summary_table: Array(39000) }` 無 `view` ⇒ 斷言 `store.report.summary_table.length===39000`（現行會 PASS，應 FAIL）。

**來源摘要**: frontend/src/hooks/useICAnalysis.ts#8386a196b35c; docs/ICRESULT_PAGING_SPEC.md#c0780c361456

[P1/MAJOR] 信心度=High。門檻 auto-refilter 600 ms 去抖為高頻路徑；後端滾動部署若 refilter 端點未升級，使用者改門檻即 OOM。修法：複製 fetchResult 之 `view !== 'light'` 分支（setError、不 setReport）；補 vitest 與 fetchResult 對稱。

---

## COMPOSER-R1-P2-01

**斷言**: URL query 還原 `search` 時只更新 `summaryParams.search`，表格搜尋框 `searchText` 本地 state 不同步，§C-10「重整還原」搜尋條件 UI 不可見。

**碼證**: `page.tsx:157-172` 從 URL 寫入 `patch.search` → `setSummaryParams`；`ICSummaryTable.tsx:92` `useState(params?.search ?? '')` 僅初值、無 `params.search` effect；`page.paging.test.tsx:12-15` mock 空 `URLSearchParams`。RECHECK：帶 `?search=close` 開頁 ⇒ network `/summary` 含 search=close 但 `[data-testid=ic-summary-search]` value 仍空。

**來源摘要**: frontend/src/components/ic-analysis/ICSummaryTable.tsx#63f62cf65a6e; frontend/src/app/ic-analysis/page.tsx#0022f3a03f17

[P2/MINOR] 信心度=High。資料過濾正確、僅 UI 不一致；不阻 B3 但應在 UAT B34 前修或標示已知限制。

---

ASSUMPTIONS_VERIFIED: paging vitest 20/20 rc=0；tsc error TS=8；pytest paging 40/40 rc=0；gate 3 PASS；B1 Q1–Q4 四測試 PASS；fetchResult light 守衛碼證；grouped_ic 還原碼證
TESTS_RUN: `npx vitest run`（paging 三檔）rc=0；`(cd frontend && npx tsc --noEmit -p tsconfig.json | grep -c 'error TS')`→8；`venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` rc=0；`bash scripts/icresult_paging_phase_gate.sh 3` rc=0
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）

產出: `handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R1-composer.md`

TMP_CLEANUP: 嘗試刪 `/tmp/icresult_b2_*.log`、`/tmp/sessions` → Permission denied（sandbox）；保留 `claude-501`

STATUS: DONE
## GROK-R1-P1-01

**斷言**: `project_feature` 對實機巢狀 `grouped_ic`（`{by_*: {label: {feature: value}}}`）以一層 `v.get(name)` 投影，回傳五個 kind 全為 null；B2 前端 reshape 後 GroupedICBarChart／RegimeRadarChart 相對改前丟失全部有限 IC 值。

**碼證**: `api/services/ic_result_projection.py:271-272`；`frontend/src/app/ic-analysis/page.tsx:286-295`／`:985-996`。VERIFY：fixture 特徵 `close_12h_cycle_HT-PHASOR-Quadrature_Std_W34` → projected `{"by_year":null,...,"by_regime":null}`（sha=`3e6b8541a97a`＝golden 所鎖）；reshape 後 radar 全 null；legacy `by_regime` → `[('bull',-0.231…),('bear',-0.183…),…]`。`ic_decay`／`rolling`／`quantile` 同特徵 `equal True`。page.paging ⑤只鎖 RollingICChart。RECHECK：修投影為 `{kind: {label: value_for_feature}}`（或 chart 相容 `{kind:{label:{feat:val}}}`）＋前端對齊；加 vitest／G-3 斷言 regime／by_year 有限值；重凍 golden。

**來源摘要**: api/services/ic_result_projection.py#6c8c0234ff11

[MAJOR] 信心度=高；非 OOM／非錯頁，但 Task 2.3「六圖接對」中兩圖靜默空白；根因在 B1 投影＋B2 reshape 假設扁平 `{group:value}`，與實機三層 map 不符。

## GROK-R1-P1-02

**斷言**: `refilter` 在回應缺少 `view:'light'` 時仍 `setReport(result)`，可把舊後端全量報告（含 `summary_table`／per-feature 段）寫入 store；與 `fetchResult` 的「錯誤＋不吃」不對稱。

**碼證**: `frontend/src/hooks/useICAnalysis.ts:130-138`（fetchResult 守衛）vs `:721-731`（refilter 無守衛）。hook 測試只鎖 fetchResult 舊版路徑與 refilter happy-path `view=light`。後端新碼 `refilter(..., view=light)` → `get_result(view=light)` 正確；缺口在**前端相容／防呆**。RECHECK：refilter 回應無 `view:'light'` ⇒ `setError`、不 `setReport`、保留舊 report；加與 fetchResult 對稱的 vitest。

**來源摘要**: frontend/src/hooks/useICAnalysis.ts#8386a196b35c

[MAJOR] 信心度=高；升級後後端路徑安全；未重啟／舊行程 refilter 仍可能塞 119 MB。修法與 fetchResult 同形即可。

---

