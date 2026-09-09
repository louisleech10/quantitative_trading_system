# ICRESULT_PAGING B2 前端實作 code review R1（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R1  
family: grok  
findings-round: R1  
標的 commit: `bf3afad1`（B2）＋`ddbcca84`／`fdccd3ee`（B1 R1 修補）→ HEAD `4c14f5b2`  
SCOPE: review-only；禁改 production／test／docs  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#c0780c361456  

---

## Verdict：需修補後派工

本輪 **無 P0**；**2 P1**。light 路徑／分頁表格／revision／abort／漏斗／URL 同步大體對齊 SPEC §C-7／§C-10；B1 Q1–Q4（本家 Q1／Q2）原反例已閉合。阻擋進 B3／UAT B34 前應修：①`project_feature` 的 `grouped_ic` 一層 `v.get(name)` 對實機 `{by_*: {label: {feature: value}}}` 全回 null，前端 reshape 亦無法還原 → GroupedIC／Regime 圖相對改前丟光數值；②`refilter` 未做 `view==='light'` 守衛（對照 `fetchResult`），舊後端回全量時會 `setReport` 吃進 store。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `(cd frontend && npx vitest run)` | **一跑** 1 failed／646 passed（`page.paging` ① flaky）；**二跑** **83 檔 647 條 rc=0** |
| `(cd frontend && npx tsc --noEmit -p tsconfig.json)` → `grep -c 'error TS'` | **8**（既有：`FactorReturnChart.test.tsx`×4＋`useFeatureFactory.batchDate.test.ts`×4）；無新錯 |
| `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` | **40 passed／0 skip**；rc=0（含 Q1–Q4 錨：`test_set_result_does_not_hold_lock_during_normalize`／`test_sort_golden_feature_name_desc_is_reverse_string_order`／`test_cache_key_distinguishes_none_and_empty_string`／`test_size_probe_blocked_on_setup_failure`） |
| `bash scripts/icresult_paging_phase_gate.sh 3` | `SIZE_GATE=PASS`；`LATENCY_GATE=PASS`；`GATE PASS: phase=3`；rc=0 |
| `shasum -a 256 -c handoffs/20260909-icresult-b2-baseline.sha` | 審查範圍內碼 OK；**2 檔 FAILED**：`docs/site/GAP-3驗收清單.html`／`docs/site/現在做到哪.html`（非本批 diff；未改碼） |

HEAD=`4c14f5b2`

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| 掛載後 `/summary` 只多拉一次 | **部分**：`useEffect` 依賴 `[taskId, reportLight, resultRevision, summaryParams, fetchSummaryPage]`；`setSummaryParams` 換物件參考才重拉。page 測試未鎖呼叫次數；實機未開 network |
| URL `replaceState` 不迴圈 | **讀碼**：掛載還原只跑一次（`urlSyncedRef`）；寫 URL 不經 `useSearchParams` 回寫。實機未驗 |
| ExportButtons PNG 只含當頁 50 列 | **讀碼**：`summaryTable={summaryPage?.rows}`；PNG 語意＝可見區，可接受；未改匯出 API |
| deep 分頁圖改吃 featureDetail | **讀碼**：`TurnoverTimeSeriesChart`／`FactorEquityCurveChart` 吃 `sectionSplit.turnover/quantile`（來自 featureDetail）；turnover／quantile 投影 `node.get(name)` 與 legacy 相等（實跑） |
| 事件 run light metadata 齊鍵 | **未跑**事件 fixture；contract keep 含 `event_filter`／`oos_downgrade`／`isolation`／`period_alignment` |

---

## B1 R1 四條修補複驗（原提出方）

| Q | 原 ID | 複驗 | 狀態 |
|---|---|---|---|
| Q1 | GROK-R1-P1-01 | `_set_result`：normalize／deny 在 lock 外；lock 內只賦值＋revision；三寫點（完成 `:1635`、full `:2436`、refilter `:2739`）皆 lock 外呼叫。`test_set_result_does_not_hold_lock_during_normalize` PASS | **CLOSED** |
| Q2 | GROK-R1-P2-01 | `build_sort_index` 字串欄 `sorted(..., reverse=(sort_order=="desc"))`；`_rev` 已刪。`test_sort_golden_feature_name_desc_is_reverse_string_order` PASS | **CLOSED** |
| Q3 | CODEX-R1-P1-01 | cache key 區分 None vs `""`（註解＋測試）。`test_cache_key_distinguishes_none_and_empty_string` PASS | **CLOSED** |
| Q4 | CODEX-R1-P1-02 | 探針 setup 失敗 → `*_GATE=BLOCKED`。`test_size_probe_blocked_on_setup_failure` PASS；gate 3 PASS | **CLOSED** |

---

## 必答（成對）

### 1a. 不吃全量：仍可能拿到／保留整份 summary_table 或 per-feature 段的路徑
**有**：`refilter`（`useICAnalysis.ts:724-729`）打 `?view=light` 後**無條件** `setReport(result)`，缺 `fetchResult` 的 `view!=='light' ⇒ setError、不 setReport` 守衛。舊後端忽略 `view` 回全量 ⇒ store.report 持有 `summary_table`／六段（119 MB 級）。`reportLight` 因無 `view:'light'` 為 null ⇒ 表格／圖不掛載，但記憶體已吃進。`resetReport` 有清；deep-analysis 寫獨立 `deep_analysis_result` 不經 setReport。見 **P1-02**。

### 1b. 後端未升級時是否「錯誤＋不吃」
**僅 `fetchResult` 路徑是**（測試鎖定）。**`refilter` 路徑否**——靜默 `setReport` 全量。

### 2a. revision／abort：舊世代仍被套用的序列
①翻頁中 refilter：refilter **先** await 再 `abortProjections`；await 期間完成的 summary 若 revision 仍等於舊 store 會先 `setSummaryPage`，隨後 `setReport(light)` 用 light 內 `summary_page` 覆蓋＋effect 重拉——短暫舊列可接受。②切特徵中 refilter：abort detail＋`setReport` 更新 revision；後到舊 detail 因 `result_revision !== current` 丟棄。③409 連續兩次：`attempt < 2` 只重拉一次；第二次 409 ⇒ throw ⇒ `setSummaryError`，不套用舊 page。

### 2b. 409 一次上限；`resultRevision=null`
一次上限與 SPEC handshake 一致（夠用；連續 refilter 风暴靠 abort＋丟棄）。`resultRevision=null`（舊後端無欄）：不送 `revision` query；丟棄條件 `current !== null && …` 短路 ⇒ **不丟棄**。升級後 light 帶 number 即恢復保護。

### 3a. 表格語意：本地序殘留；Auto-Suggest
**無本地排序**（`sortedData`＝`page.rows` 或 legacy `data` 原序）。Auto-Suggest／`markSelectedAsVerified` 只掃**當頁** `sortedData`，UI **未**標「僅當頁」——語意縮水相對改前全表，屬 UX 殘留（非阻擋；建議標示）。icir 全 null 時首列＝後端字串序，UI 不再假設本地序。

### 3b. 全選＝當頁＋跨頁 Set；deep-analysis payload
全選只 add／remove 當頁名；`selectedFeatures` 無硬上限（自動預選首頁前 30）。deep-analysis／apply-transforms 送的是**名字列表**，與分頁無關——一致。跨頁勾選可累積遠超一頁，與改前「從全表勾」能力接近。

### 4a. 圖表接線：grouped_ic 還原 vs 改前逐值
**不相等（全丟）**。實機 `grouped_ic`＝`{by_year:{year:{feat:val}}, by_regime:{regime:{feat:val}},…}`。`project_feature` `:272` 對 top-level kind 做 `v.get(name)` ⇒ 全 null（golden sha 亦鎖此全 null 物件）。page reshape `{kind: {feat: null}}` 後 RegimeRadar／GroupedICBar 讀到的值皆 null；legacy 同特徵 radar 有有限數值。見 **P1-01**。其餘段（ic_decay／quantile／turnover／rolling）`node.get(name)` 與 legacy 相等（實跑）。

### 4b. `coverage_analysis` 消費者
**無**前端讀點（僅 types／Omit）；改前即孤兒欄。後端投影仍回該段。

### 5a. UX 預算 vs vitest
表格 7＋page 6＋hook 7 鎖：light 拒絕全量、409 重拉、舊 revision 丟棄、abort detail、refilter offset0、skeleton／overlay、漏斗 null stage、detail 重試。**退化仍全綠例**：GroupedIC／Regime 全 null（P1-01）——page 測試只斷言 RollingICChart windows，不斷言 bar／radar 數值。另：全套 vitest 曾 1 條 flaky（二跑綠）。

### 5b. 搜尋 300 ms vs detail 150 ms
**不衝突**：搜尋唯一 owner＝`ICSummaryTable`；detail 去抖在 hook，非搜尋。符合 §C-10。

### 6. ≥10× 不必要複雜？
**無**。contract Omit、伺服器分頁、單特徵投影、Abort＋revision 與 §C-9 預算相稱。

### 7. B1 修補閉合？可進 B3／UAT B34？
B1 Q1–Q4 **CLOSED**。**不可直接進 B3／UAT B34**：須先修 P1-01（grouped／regime 圖）與 P1-02（refilter light 守衛）；否則 UAT 會看到空 Regime／Grouped 圖，且舊後端 refilter 有凍頁風險。

---

## Findings

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

## §1 必查摘要（碼 vs SPEC）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **P1-01** SPEC G-3 `{group:value}` vs 實機三層＋現行一層 get；**P1-02** refilter vs fetchResult light 守衛 |
| 2 | 漏項 | grouped／regime 無數值 vitest；refilter 無舊版負向測 |
| 3 | 不可測 | 事件 light metadata、URL 迴圈實機未跑 |
| 4 | quant | 無弱化 NaN／inf；grouped 丟值＝正確性缺陷（P1-01） |
| 5 | 過度工程 | 無（必答 6） |
| 6 | OOM | light＋分頁主路徑 OK；refilter 舊後端例外見 P1-02 |
| 7 | cache | B1 Q3 已閉；前端 revision 丟棄＋abort |
| 8 | API／型別 | `ICReportLight` Omit 七段；tsc 新錯 0（總 8 既有） |
| 9 | 測試 | 647 綠可繞過 grouped 空圖；vitest 全套曾 flaky 一次 |
| 10 | Agent | 無 |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）
- G-3／golden `grouped_ic` sha 代表「正確單特徵值」（實為全 null 物件被鎖死）← **已否證**，見 P1-01
- refilter 與 fetchResult 同等拒絕非 light ← **已否證**，見 P1-02
- 事件 run light metadata 齊鍵（NOT_RUN）
- URL replaceState 無迴圈（讀碼 only）

---

ASSUMPTIONS_VERIFIED: vitest 647／tsc error TS==8／pytest 40／gate3 SIZE+LATENCY PASS；Q1–Q4 測試綠；grouped_ic 實跑 VALUES_LOST；refilter 缺 light 守衛碼證
TESTS_RUN: `(cd frontend && npx vitest run)` → 647 passed（二跑；一跑 1 flaky）；`npx tsc --noEmit` error TS=8；`pytest tests/api/test_icresult_paging.py -q -rs` → 40 passed；`bash scripts/icresult_paging_phase_gate.sh 3` → GATE PASS
FAILURES_SEEN: vitest 一跑 `page.paging` ① tr 計數 flaky（單檔重跑＋全套二跑綠）；baseline 2×`docs/site/*.html` FAILED（非本批）
SCOPE_CHANGES: none（唯讀）；P1-01 根因跨 B1 `project_feature`（在 brief 審查 diff 內）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）；修 P1-01 將改 grouped_ic 投影 schema／golden sha

產出: `handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R1-grok.md`

STATUS: DONE
