# ICRESULT_PAGING B2 review R1 六群集修補複驗 R2（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R2  
family: grok  
findings-round: R2  
標的 commit: `4940f967`（B2 review R1 六群集修補；範圍含 `bf3afad1` B2＋`ddbcca84`／`fdccd3ee` B1 R1）  
SCOPE: review-only；禁改 production／test／docs  
HOOK-DIGEST: frontend/src/hooks/useICAnalysis.ts#4f84c7c55861  
GROUPED-DIGEST: frontend/src/lib/icGrouped.ts#cf23a3d85040  
TABLE-DIGEST: frontend/src/components/ic-analysis/ICSummaryTable.tsx#46e1645b632b  
FUNNEL-DIGEST: frontend/src/components/ic-analysis/FilterFunnelChart.tsx#a0cb1510ffc0  
PAGE-DIGEST: frontend/src/app/ic-analysis/page.tsx#319d42dff447  
PROJ-DIGEST: api/services/ic_result_projection.py#ed7142b1848e  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#c0780c361456  
R1-SYNTH: handoffs/reconcile/20260909-icresultpaging-b2-review-r1/synth.md#3932b12bb471  
BASELINE: `shasum -a 256 -c handoffs/20260909-icresult-b2r2-baseline.sha` → 全 OK；rc=0  

---

## Verdict：可合併、可進 B3（使用者 UAT B34）

R1 六群集（N1–N6）原提出方反例皆閉合；本輪 **無新 P0／P1**。唯一新洞＝detail 路徑在 revision 嚴格丟棄後未離開 `loading`（P2）。驗收命令全綠；B1 R1 四修補（lock 外 normalize、feature_name desc、None≠"" 快取、probe setup→BLOCKED）測試綠。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `(cd frontend && npx vitest run)` | **84 files／654 passed**；rc=0（~32s） |
| `(cd frontend && npx tsc --noEmit -p tsconfig.json \| grep -c 'error TS')` | **8**（既有：`FactorReturnChart.test.tsx`×4＋`useFeatureFactory.batchDate.test.ts`×4）；tsc 本身 rc=1 |
| `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` | **41 passed／0 skip**；rc=0（~18–22s） |
| `bash scripts/icresult_paging_phase_gate.sh 3` | **SIZE_GATE=PASS**；**LATENCY_GATE=PASS**；**GATE PASS: phase=3**；rc=0 |
| `shasum -a 256 -c handoffs/20260909-icresult-b2r2-baseline.sha` | 全 OK；rc=0 |

N1–N6 對症 vitest（5 檔）：29 passed rc=0。B1 閉合 pytest：`does_not_hold_lock`／`feature_name_desc`／`cache_key_distinguishes_none_and_empty_string`／`size_probe_blocked`／`grouped_ic_three_level` 皆 PASS。

### N1–N6 原反例複驗（本家族 N1＝refilter light；N2＝三層 grouped）

| ID | 反例 | 結果 |
|---|---|---|
| N1 | refilter 回無 `view:'light'` 之全量 | `useICAnalysis.ts:747-750` setError、不 setReport；vitest「舊 report 保留」綠 |
| N2 | fixture 首特徵三層 `grouped_ic` | `project_feature` 有限值 7、mismatches=0；reshape≡legacy `by_regime`（bull≈-0.231…）；`icGrouped.test`＋pytest three_level 綠 |
| N3 | page50 取消表頭全選 | 只移當頁；`feat_0` 保留；paging.test 綠 |
| N4 | funnel `{input:null,output:7}` | N/A、不回填；funnel.test 綠 |
| N5 | detail 409 一次重拉；store=5／resp null | 重拉＋第二次 409→error；summary／detail 皆丟棄；vitest 綠（見 P2：detail 丟棄後 status 仍 loading） |
| N6 | 批次 Watchlist 跨頁＋URL search | 文案含「不在當頁未處理」／「僅評分當頁」；`params.search` effect 同步搜尋框；綠 |

---

## 必答（成對）

### 1a. 不吃全量：仍拿到／保留整份 `summary_table` 的路徑？
**R1 缺口已封。** `fetchResult`（`:134-137`）與 `refilter`（`:747-750`）同形：無 `view:'light'` ⇒ setError、不 setReport。deep-analysis 寫獨立 `deepAnalysisReport`，不經 light report。`resetReport` 清 `report`／`summaryPage`／`featureDetail`。構造「舊後端 refilter 全量」⇒ 舊 light report 保留且無 `summary_table`（vitest）。

### 1b. 後端未升級（回全量）時是否「錯誤＋不吃」？
**是。** 兩入口皆 setError（文案含「後端版本過舊」）且 return null；store 不寫入全量。

### 2a. revision／abort：舊世代 rows／detail 被套用的序列？
**未再構造成功套用。** 翻頁中 refilter：`abortProjections`＋`resultRevision` 更新⇒ effect 重拉；舊 summary 若 revision≠current 丟棄。切特徵中 refilter：detail abort；新 revision 重拉。409 連續兩次：summary／detail 皆 attempt&lt;2 重拉一次，第二次 throw→error。null revision 回應在 store 非 null 時丟棄（N5）。

### 2b. 409 一次上限；`resultRevision=null`（舊後端）？
**一次上限夠用（與 SPEC 一致）。** store `resultRevision=null` 時比較條件 `current !== null` 為假⇒不丟棄（舊後端無戳時仍可顯示）；light 若帶數字戳則 setReport 寫入後即啟用嚴格比較。detail 丟棄路徑見 P2。

### 3a. 表格語意：icir 全 null 時本地序假設？Watchlist「僅當頁」？
**伺服器序；Watchlist／Auto-Suggest 已揭露僅當頁。** 表格 rows＝`/summary` 回傳；Auto-Suggest 文案 `僅評分當頁 ${sortedData.length} 列`；批次跳過回報 `N 個不在當頁未處理`。

### 3b. 全選＝當頁＋跨頁 Set；deep-analysis payload？
**一致。** 全選／取消只動當頁 names；`selectedFeatures: string[]` 仍為跨頁 Set 對外 API；`buildDeepAnalysisRequest` 吃該陣列。取消全選不再 `onSelectFeatures([])`（N3）。

### 4a. 圖表：`grouped_ic` 還原 vs 改前逐值？
**相同。** 後端投影 `{kind:{label:value}}`；`reshapeGroupedForFeature`→`{kind:{label:{feature:value}}}`；對 fixture 首特徵 `reshape_eq_legacy=True`，`by_regime.bull≈-0.2316`。Grouped／Regime 吃 `featureGroupedMap`。

### 4b. `coverage_analysis` 消費者？
**無（改前即孤兒）。** types 有欄；page／圖表無讀取。light Omit 已刪該段。

### 5a. UX 預算 vitest 是否真鎖到？一種仍全綠的退化？
**八案例類測試有鎖 N1–N6 反例；未鎖 P2。** 退化例：detail 回應 `result_revision=null` 且 store 非 null⇒丟棄後 `featureDetailStatus` 留在 `loading`，vitest 只斷言 `featureDetail===null` 仍綠。

### 5b. 搜尋 300 ms vs detail 150 ms？
**不衝突。** 300 ms＝表格 `search`→`onParamsChange`（§C-10）；150 ms＝單特徵 detail 去抖（非搜尋）。

### 6. ≥10× 不必要複雜？
**無。** light＋summary／feature 分端＋revision handshake＋單特徵 reshape，與 39k／119MB 問題匹配。

### 7. B1 R1 四修補閉合？可進 B3？
**閉合；可進 B3（UAT B34）。**  
①`_set_result` normalize／deny 在 lock 外（`test_set_result_does_not_hold_lock_during_normalize`）  
②`feature_name` desc＝`sorted(..., reverse=True)`（`test_sort_golden_feature_name_desc_is_reverse_string_order`）  
③`pass_class`／`search` 之 None≠""（`test_cache_key_distinguishes_none_and_empty_string`）  
④setup 失敗⇒`SIZE_GATE=BLOCKED` rc=2（`test_size_probe_blocked_on_setup_failure`）  
本輪 P2 不阻 UAT；建議 UAT 前或並行修 detail 丟棄→error。

---

## Findings

## GROK-R2-P2-01

**斷言**: `fetchFeatureDetail` 在 store `resultRevision` 非 null 且回應 `result_revision` 不符（含 null）時直接 `return resolve(null)`，不呼叫 `setFeatureDetail(..., 'error'|'idle')`，使 `featureDetailStatus` 永久停在先前寫入的 `loading`，舊 detail 圖表繼續顯示且無重試鈕。

**碼證**: `frontend/src/hooks/useICAnalysis.ts:211` 先 `setFeatureDetail(null,'loading')`（保留舊 detail）；`:235` 嚴格比較失敗僅 `return resolve(null)`。對照 summary `:170-173` 會 `setSummaryError`＋`summaryLoading` 於 finally 清掉。vitest `revision 嚴格比較…` 只斷言 `featureDetail===null`、不斷言 status。RECHECK：store revision=5、mock feature `result_revision=null`、先前 detail 非 null ⇒ 預期 status=`error`（或 idle）＋可重試；現行 status=`loading`。

**來源摘要**: frontend/src/hooks/useICAnalysis.ts#4f84c7c55861

[P2/MINOR] 信心度=High。N5 丟棄語意已對；缺的是丟棄後狀態機。部分升級／無戳 feature 端會讓基本分頁圖表遮罩永不消失。修法：與 summary 同形——null 戳⇒ setFeatureDetail(null,'error','後端回應缺少 result_revision（版本不相容')）；非 null 不符⇒ error 或 idle；補 vitest 斷言 status。不阻 B3／UAT B34。

---

## §1 必查摘要（碼 vs SPEC §C-7／§C-10）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無新 P0／P1；P2＝detail 丟棄 vs summary 錯誤態不對稱 |
| 2 | 漏項 | N1–N6 測試已補；P2 測試未鎖 status |
| 3 | 不可測 | 驗收＋對症 vitest／pytest 可證偽 |
| 4 | quant | 無；投影有限值對照 fixture |
| 5 | 過度工程 | 無（必答 6） |
| 6 | OOM | light 守衛封全量；gate3 SIZE PASS |
| 7 | Cache | B1 None≠"" 閉合；前端 revision 丟棄 |
| 8 | API／相容 | 無 light ⇒ 錯誤不吃；舊 store null revision 仍可讀 |
| 9 | 測試 | 654 vitest／41 pytest；P2 為覆蓋洞 |
| 10 | Agent 可執行 | 已實作；R2 複驗 |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| N1–N6 修補閉合 | **fact-verified** | 上表＋vitest／pytest |
| B1 Q1–Q4 閉合 | **fact-verified** | 四測試 PASS |
| 掛載 `/summary` 不多於一次額外 | **未跑次數斷言**（cost；brief NOT_RUN） | effect 依 `summaryParams`；讀碼無每 render 新建 |
| URL `replaceState` 不迴圈 | **讀碼**；實機 network **NOT_RUN** | 讀 URL 僅 mount 一次 `urlSyncedRef` |
| ExportButtons PNG 僅 50 列可接受 | **NOT_RUN**（cost；已知產品取捨） | — |
| deep 分頁圖改吃 featureDetail 語意＝改前 | **讀碼**；專測 **NOT_RUN** | quantile／turnover 同源投影 |
| 事件 run metadata 齊鍵 | **讀碼 contract keep**；事件 fixture light **NOT_RUN** | — |

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF／brief／R1 synth／SPEC 輸出格式；baseline 全 OK；N1–N6 與 B1 四修補以碼＋測試複驗；grouped reshape≡legacy 實跑；驗收四命令實跑。
TESTS_RUN: vitest 654 passed rc=0；tsc error TS=8；pytest icresult_paging 41 passed 0 skip rc=0；gate3 SIZE/LATENCY/GATE PASS rc=0；N 對症 vitest 29 passed；B1 閉合五測 PASS。
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none（唯讀；僅本交件＋handoff）
NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R2-grok.md

STATUS: DONE
