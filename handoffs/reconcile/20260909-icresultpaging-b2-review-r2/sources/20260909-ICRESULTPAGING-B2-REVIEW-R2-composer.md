brief-kind: review
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R2
family: composer
findings-round: R2
標的 commit: `4940f967`（B2 review R1 六群集 N1–N6 修補）
審查範圍: `git diff ed7563f4..HEAD -- frontend/src api/services api/routes tests handoffs/20260909-*.py`

## Verdict：可合併、可進 B3（使用者 UAT B34）

R1 群集 N1–N6 已由本輪（composer 原提出方）重跑同一反例並 **CLOSED**；brief 必答 1–7 全格有碼證；驗收命令全 PASS。本輪無新 P0／P1。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| vitest 84 檔 654 條 rc=0 | **fact-verified** | `(cd frontend && npx vitest run)` → 84 passed / 654 passed, rc=0 |
| tsc `error TS` == 8 | **fact-verified** | `(cd frontend && npx tsc --noEmit -p tsconfig.json \| grep -c 'error TS')` → 8 |
| pytest paging 41 0 skip | **fact-verified** | `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` → 41 passed, rc=0 |
| gate 3 SIZE/LATENCY PASS | **fact-verified** | `bash scripts/icresult_paging_phase_gate.sh 3` → `SIZE_GATE=PASS` `LATENCY_GATE=PASS` `GATE PASS: phase=3`, rc=0 |
| baseline sha 未改 | **fact-verified** | `shasum -a 256 -c handoffs/20260909-icresult-b2r2-baseline.sha` → 全 OK, rc=0 |
| 掛載後 `/summary` 只多拉一次 | **assumed（NOT_RUN）** | brief 成本項；`page.tsx` effect 依 `summaryParams` 物件參考 |
| URL `replaceState` 不觸發迴圈 | **assumed（NOT_RUN）** | brief 成本項 |
| 事件 run light metadata 齊鍵 | **assumed（NOT_RUN）** | brief 成本項 |
| deep 分頁圖表語意不變 | **assumed（NOT_RUN）** | brief 成本項；`page.tsx:1029-1039` 改吃 `featureDetail` 投影 |
| ExportButtons PNG 僅 50 列語意 | **assumed（NOT_RUN）** | brief 成本項 |

---

## R1 群集複驗（N1–N6；composer 原提出方重跑反例）

| 群集 | R1 主張 | R2 複驗 | 狀態 |
|---|---|---|---|
| **N1** refilter 無 `view:'light'` 仍 setReport | `useICAnalysis.ts:746-749` 同形守衛；`useICAnalysis.paging.test.ts:154-163` mock 39k 全量無 view ⇒ error、舊 light report 保留 | **CLOSED** |
| **N2** `grouped_ic` 三層投影＋前端還原 | `ic_result_projection.py:271-275`；`icGrouped.ts:8-22`；`test_feature_detail_grouped_ic_three_level_projection` 41 條之一 PASS；`icGrouped.test.ts` 逐值對照 | **CLOSED** |
| **N3** 取消表頭全選只移當頁 | `ICSummaryTable.tsx:160-165`；`ICSummaryTable.paging.test.tsx:99-111` page50 取消後 page0 勾選保留 | **CLOSED** |
| **N4** 漏斗任一 null ⇒ 不適用 | `FilterFunnelChart.tsx:27-29`；`FilterFunnelChart.funnel.test.tsx:43-47` input=null output=7 ⇒ N/A | **CLOSED** |
| **N5** detail 409 重拉一次；revision 嚴格（null 丟棄） | `useICAnalysis.ts:222-228`、`:170-173`、`:235`；`useICAnalysis.paging.test.ts:165-201` 三條 | **CLOSED** |
| **N6** 批次 Watchlist 僅當頁揭露；URL search 同步 | `ICSummaryTable.tsx:226-253`、`:304`、`:131-132`；`ICSummaryTable.paging.test.tsx:113-117` | **CLOSED**（composer R1-P2-01 亦閉合） |

---

## 必答（成對）

### 1a／1b 不吃全量

- **1a（仍可能保留全量之路徑）**：`fetchResult`／`refilter` 皆帶 `?view=light` 且回應缺 `view:'light'` 時 `setError`、**不** `setReport`（`:134-137`、`:746-749`）。`fetchDeepAnalysisResult` 走 `/deep-analysis/.../result` 全量 deep 端點，屬 deep 分頁預期，非 basic 表格路徑。`resetReport`／`setReport(null)` 僅清 store，不引入全量。
- **1b（後端未升級）**：**能**——`useICAnalysis.paging.test.ts:47-54`（fetchResult）與 `:154-163`（refilter）對稱：舊版全量 mock ⇒ `report` 仍 null／保留舊 light、`error` 含「後端版本過舊」。

### 2a／2b revision／abort

- **2a（舊世代套用序列）**：`abortProjections()` 於 `fetchResult`／`refilter` 開頭；`fetchSummaryPage`／`fetchFeatureDetail` 在 `result_revision !== store.resultRevision`（含 null 戳）時丟棄；翻頁中 refilter、切特徵中 refilter 均由 abort＋revision 更新觸發重拉。未找到可讓舊 rows／detail **commit** 的競態。
- **2b（409 一次上限／revision=null）**：summary／detail 各最多 retry 一次（`:180-183`、`:225-228`）；連續 409 ⇒ error（測試 PASS）。`store.resultRevision` 非 null 時 `result_revision=null` 回應丟棄並標「版本不相容」（`:170-173`、`:186-201`）。`store=null` 時允許首載（向後相容）；B1 後端恆帶 revision。

### 3a／3b 表格語意

- **3a（本地序假設）**：`ICSummaryTable` 已移除本地 sort；Auto-Suggest 僅評分 `sortedData`（當頁），UI 已標「僅評分當頁 N 列」（`:304`）；批次 Watchlist 跨頁 skipped 有回報（`:252`）。
- **3b（全選＝當頁＋跨頁 Set）**：全選 merge Set、取消只移當頁（`:158-170`）；`selectedFeatures` 無硬編碼上限，deep-analysis payload 仍送完整 Set 陣列，與跨頁勾選一致。

### 4a／4b 圖表接線

- **4a（grouped_ic 還原）**：`reshapeGroupedForFeature` 把 `{kind:{label:value}}` 還原為 `{kind:{label:{feature:value}}}`；`page.tsx:288-291` 餵 `GroupedICBarChart`／`RegimeRadarChart`；後端 `test_feature_detail_grouped_ic_three_level_projection` 逐 label 對 fixture；前端 `icGrouped.test.ts` 逐值 `-0.23`/`-0.18`。
- **4b（coverage_analysis）**：自 `ICReportLight` omit（`types.ts:3321`）；grep 前端無消費者，仍為孤兒欄。

### 5a／5b UX 預算

- **5a（vitest 是否鎖住）**：表格 7＋hook 11＋page 6＋漏斗 3＋icGrouped 1＝paging 專項 29 條 PASS。R1 反例（refilter 全量、page50 取消、input null、detail 409、revision null、URL search）均已鎖。**殘留 NOT_RUN**：brief「我沒查的」掛載 `/summary` 次數、實機 URL 迴圈、deep 分頁圖表——非本輪新洞。
- **5b（搜尋去抖 owner）**：表格 `SEARCH_DEBOUNCE_MS=300` 唯一 owner；hook detail 150 ms 去抖非 summary 搜尋——與 §C-10 不衝突。

### 6 ≥10× 不必要複雜

**無**。分頁狀態集中 store＋兩支 fetch；legacy `data` prop 保留供其它 caller。

### 7 B1 R1 四修補＋B3

- **B1 Q1–Q4（複驗）**：Q1 lock 外 normalize——`ic_analysis_service.py:1801-1806`＋`test_set_result_does_not_hold_lock_during_normalize` PASS。Q2 字串 desc——`ic_result_projection.py` `sorted(..., reverse=...)`＋golden sort PASS。Q3 cache key None/""——`test_cache_key_distinguishes_none_and_empty_string` PASS。Q4 probe setup fail——`test_size_probe_blocked_on_setup_failure` PASS。**四條 CLOSED。**
- **B3／UAT B34**：**可進**——N1–N6 閉合、無新 P0／P1。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無 |
| 2 | 漏項 | 無新漏（R1 六群集已閉） |
| 3 | 不可測 | vitest＋pytest 41＋gate 3 可機械驗 |
| 4 | quant | 無 leakage；漏斗 null 不補假值 |
| 5 | 過度工程 | 無 |
| 6 | OOM | basic 路徑不吃全量；refilter 守衛已閉合 |
| 7 | cache | revision discard＋abort 已實作 |
| 8 | API/型別 | light omit 七段；fetchResult／refilter 守衛對稱 |
| 9 | 測試 | 29 paging 專項＋41 pytest；brief NOT_RUN 項已登記 |
| 10 | Agent | Task 2.1–2.3 落到檔案／函式 |
| 11 | 短命工 | legacy `data` prop 非白工 |

---

## COMPOSER-R2-P3-00

**斷言**: 本輪（R2）對 R1 群集 N1–N6 及 composer 原提出之 COMPOSER-R1-P1-01／P2-01 重跑同一反例後，無新增可證偽之 P0／P1／P2 產品缺陷；修法未引入可重現的 revision 穿透、全量塞入或圖表靜默空白。

**碼證**: VERIFY 表（vitest 654 passed、tsc 8、pytest 41 passed、gate 3 PASS、baseline sha OK）；N1–N6 反例測試全綠（`useICAnalysis.paging.test.ts` 11 條、`ICSummaryTable.paging.test.tsx` 含 page50 取消＋search 同步、`FilterFunnelChart.funnel.test.tsx` input null、`icGrouped.test.ts`、`test_feature_detail_grouped_ic_three_level_projection`）；`useICAnalysis.ts:746-749` refilter 守衛與 fetchResult 對稱。

**來源摘要**: handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R2-BRIEF.md#3a88f8d762b0

本輪逐項核對後無 finding。核對依據＝brief 必答 1–7 全表＋§0 前提挑戰＋R1 synth N1–N6 對照現碼（HEAD `4940f967`）；獨立重跑驗收命令；唯讀 review 未改 production／test／docs。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `(cd frontend && npx vitest run)` | **84 files / 654 passed**, rc=0 |
| `(cd frontend && npx tsc --noEmit -p tsconfig.json \| grep -c 'error TS')` | **8**, rc=0 |
| `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` | **41 passed**, rc=0 |
| `bash scripts/icresult_paging_phase_gate.sh 3` | **SIZE_GATE=PASS LATENCY_GATE=PASS GATE PASS: phase=3**, rc=0 |
| `shasum -a 256 -c handoffs/20260909-icresult-b2r2-baseline.sha` | **全 OK**, rc=0 |
| paging 專項 vitest 5 檔 | **29 passed**, rc=0 |

---

ASSUMPTIONS_VERIFIED: N1–N6 反例碼證＋測試；B1 Q1–Q4 四測試；驗收五命令全 PASS
TESTS_RUN: 見 VERIFY 表
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）

產出: `handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R2-composer.md`
TMP_CLEANUP: 嘗試刪 `/private/tmp/icresult_b2r2_*`、`icresult_frontend.diff`、`sessions` → Permission denied（sandbox）；保留 `claude-501`

STATUS: DONE
