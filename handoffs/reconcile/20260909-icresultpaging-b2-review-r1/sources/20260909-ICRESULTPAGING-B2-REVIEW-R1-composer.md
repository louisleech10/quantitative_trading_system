brief-kind: review
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R1
family: composer
findings-round: R1
標的 commit: `bf3afad1`（B2 前端）＋`ddbcca84`／`fdccd3ee`（B1 R1 四條修補）
審查範圍: `git diff ed7563f4..HEAD` — `frontend/src/{lib/types,store/icAnalysisStore,hooks/useICAnalysis,components/ic-analysis/{ICSummaryTable,FilterFunnelChart},app/ic-analysis/page}.tsx`、對應 vitest、`api/services/{ic_analysis_service,ic_result_projection}.py`、`tests/api/test_icresult_paging.py`

## Verdict：需修補後派工（1×P1）

B2 Task 2.1–2.3 主線（light 視圖、伺服器分頁、六圖／漏斗接線、revision／abort）與 brief 必驗命令全 PASS；B1 R1 四條修補複驗 CLOSED。**阻塞項**：`refilter` 未複製 `fetchResult` 之 `view:'light'` 守衛，舊後端 refilter 路徑仍可把全量 `summary_table` 塞進 store（brief 必答 1b 反例）。修補後可進 B3／UAT B34。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| vitest 83 檔 647 條 rc=0 | **fact-verified（子集）** | 本輪 paging 專項 3 檔 20 條 rc=0；brief 宣稱全套 647 條未重跑 |
| tsc `error TS` == 8 | **fact-verified** | `(cd frontend && npx tsc --noEmit -p tsconfig.json \| grep -c 'error TS')` → 8 |
| pytest paging 40 0 skip | **fact-verified** | `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` → 40 passed rc=0 |
| gate 3 SIZE/LATENCY PASS | **fact-verified** | `bash scripts/icresult_paging_phase_gate.sh 3` → `SIZE_GATE=PASS` `LATENCY_GATE=PASS` `GATE PASS: phase=3` |
| light 可指派 ICReport、元件不讀已刪段 | **fact-verified（靜態）** | `ICReportLight=Omit<…七段>`（`types.ts`）；tsc 新錯未增（仍 8）；page 六段改吃 `featureDetail` |
| 掛載後 `/summary` 只多拉一次 | **assumed（未跑）** | brief NOT_RUN；`page.tsx:186-189` 依賴 `summaryParams` 物件參考 |
| URL `replaceState` 不觸發迴圈 | **assumed（未跑）** | brief NOT_RUN；`page.tsx:174-184` 僅寫 URL、不讀 |
| 事件 run light metadata 齊鍵 | **assumed（未跑）** | brief NOT_RUN |
| deep 分頁圖表語意不變 | **assumed（未跑）** | brief NOT_RUN；`page.tsx:1029-1039` 改吃 `featureDetail` 投影 |

---

## 必答（成對）

### 1a／1b 不吃全量

- **1a（仍可能保留全量之路徑）**：`fetchResult`／`refilter` 請求雖帶 `?view=light`，但 **`refilter` 成功回應未驗 `view:'light'` 即 `setReport(result)`**（`useICAnalysis.ts:724-729`）。對照 `fetchResult` 在 `:134-137` 無 light ⇒ `setError`、**不** `setReport`。舊後端忽略 `view` 時 refilter POST 可回整棵含 `summary_table` 的樹 ⇒ store.report 持有 39k 列（表格雖吃 `summaryPage?.rows` 可能空，但記憶體仍全量）。`fetchDeepAnalysisResult` 走獨立 deep 端點，屬 deep 分頁預期行為，非 basic 表格路徑。
- **1b（後端未升級）**：**`/result?view=light` 能**——`useICAnalysis.paging.test.ts`「後端舊版」case：`report` 仍 null、`error` 含「後端版本過舊」。**`/refilter?view=light` 不能**——同上 P1；全量可進 store 且無錯誤提示。

### 2a／2b revision／abort

- **2a（舊世代套用序列）**：`abortProjections()` 於 `fetchResult`／`refilter` 開頭 abort summary＋detail（`:115-124`、`:728`）；`fetchSummaryPage` 在 `page.result_revision !== store.resultRevision` 時 return null 丟棄（`:170-172`）；`fetchFeatureDetail` 同形（`:217`）。翻頁中 refilter：進行中 summary 被 abort；revision 更新後 `page.tsx:186-189` effect 重拉。切特徵中 refilter：detail abort＋`resultRevision` 變更觸發 `:265-269` 重拉。未找到可讓舊 rows **commit** 的競態（abort ＋ revision gate）。
- **2b（409 一次上限／revision=null）**：409 僅 retry 一次（`:165-184`，測試「409 ⇒ 重拉一次」PASS）；連續 409 ⇒ catch 設 `summaryError`。`resultRevision=null` 時 revision 比對短路（`:170` 要求 `current !== null`）⇒ 舊後端不 discard stale page——可接受向後相容；B1 後端恆有 revision。

### 3a／3b 表格語意

- **3a（本地序假設）**：`ICSummaryTable` 已移除本地 sort（`:110-118`「排序一律在後端」）；legacy `data` 模式亦不 sort。**Residual UX**：Auto-Suggest（`:246-259`）對 `sortedData`（= 當頁 ≤200 列）打分，非全域 top-N；UI 未標「僅當頁」——屬產品揭露缺口，非排序錯誤。
- **3b（全選＝當頁＋跨頁 Set）**：全選 merge Set（`:162-165`）；`toggleFeature` 用 Set（`:168-172`）；deep-analysis `buildDeepAnalysisRequest` 仍送 `selectedFeatures` 陣列（store），與跨頁勾選一致；無硬編碼上限。

### 4a／4b 圖表接線

- **4a（grouped_ic 還原）**：`featureGroupedMap`（`page.tsx:287-295`）把 `{group: value}` 包成 `{group: {activeFeature: value}}`，餵 `GroupedICBarChart`／`RegimeRadarChart`；等價改前 `report.grouped_ic[group][featureName]`。`page.paging.test.tsx` ⑤ RollingICChart 收到 `rolling_ic_series` PASS。
- **4b（coverage_analysis）**：自 `ICReportLight` omit（`types.ts:3319-3321`）；改前即無消費者（僅型別 optional），仍為孤兒欄。

### 5a／5b UX 預算

- **5a（vitest 是否鎖住）**：表格 7＋hook 7＋page 6＋漏斗 2 覆蓋 skeleton 舊列保留、跨頁勾選、409 重拉、overlay、重試。**退化仍綠之例**：URL 還原（`page.tsx:157-172`）無 vitest——`useSearchParams` mock 空；且搜尋框 `searchText` 不跟 `params.search` 同步（P2），重整帶 `?search=` 時資料對、輸入框空。
- **5b（搜尋去抖 owner）**：表格 `SEARCH_DEBOUNCE_MS=300` 唯一 owner（`:55-56`）；hook `fetchFeatureDetail` 150 ms 去抖為 detail 端點，非 summary 搜尋——與 §C-10 不衝突。

### 6 ≥10× 不必要複雜

**無**。分頁狀態集中在 store＋兩支 fetch；表格 legacy `data` 模式保留但 page 只用 server mode；複雜度與 OOM 風險相称。

### 7 B1 R1 修補＋B3

- **B1 Q1–Q4（複驗）**：Q1 normalize lock 外——`ic_analysis_service.py:1801-1806`＋`test_set_result_does_not_hold_lock_during_normalize` PASS。Q2 字串 desc——`ic_result_projection.py:134` `sorted(..., reverse=…)` PASS。Q3 cache key None/""——`:114-116` `_key_part`＋`test_cache_key_distinguishes_none_and_empty_string` PASS。Q4 probe setup fail——`probe-icresult-size.py:43-46`＋`test_size_probe_blocked_on_setup_failure` PASS。**四條 CLOSED。**
- **B3／UAT B34**：**P1 refilter 守衛修補後可進**；其餘 blocking 無。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無（fetchResult 與 refilter 守衛不一致＝P1，非 SPEC 自相矛盾） |
| 2 | 漏項 | P1 refilter 缺 light 驗證；P2 URL 搜尋框未同步 |
| 3 | 不可測 | paging vitest＋pytest 40＋gate 3 可機械驗 |
| 4 | quant | 無 leakage；light 不補假 funnel 值（null⇒不適用） |
| 5 | 過度工程 | 無 |
| 6 | OOM | basic 路徑設計不吃全量；refilter P1 可破壞此保證 |
| 7 | cache | 前端無跨 task cache；revision discard 已實作 |
| 8 | API/型別 | TS light omit 七段；舊後端 fail-closed 在 fetchResult 有、refilter 缺 |
| 9 | 測試 | 20 paging 用例 PASS；URL 還原／refilter 舊版未測 |
| 10 | Agent | Task 2.1–2.3 落到檔案／函式，可執行 |
| 11 | 短命工 | legacy `data` prop 保留供其它 caller，非本 epic 白工 |

---

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
