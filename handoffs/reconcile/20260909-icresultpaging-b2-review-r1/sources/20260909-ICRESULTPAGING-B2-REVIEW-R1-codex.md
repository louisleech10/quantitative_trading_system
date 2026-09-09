# ICRESULT_PAGING B2 前端 code review R1（codex）
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R1；scope: review-only；target: bf3afad1＋B1 R1 修補；RECONCILE-STAMP: R7 APPROVED。
## Verdict：需修補後派工（無 P0；5 P1、1 P2）
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
