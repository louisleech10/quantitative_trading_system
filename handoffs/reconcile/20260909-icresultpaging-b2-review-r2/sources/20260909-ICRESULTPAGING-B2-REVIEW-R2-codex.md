# ICRESULT_PAGING B2 前端實作 code review R2（codex）
task-id: 20260909-ICRESULTPAGING-B2-REVIEW-R2；family: codex；findings-round: R2
標的：`bf3afad1`＋`ddbcca84`／`fdccd3ee`；scope：`git diff ed7563f4..HEAD -- frontend/src api/services api/routes tests handoffs/20260909-*.py`
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#7a407bf1d440；TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#92df48946601
## Verdict：需修補後派工（無 P0；1 P1、1 P2）
R1 的 N1–N6 原反例均已在現行碼閉合；本輪新增 P1 仍阻擋 B3/UAT，P2 應一併修正。

## CODEX-R2-P1-01

**斷言**: feature detail 回應的 `result_revision` 不符（包含 `null`）時雖被丟棄，但 `featureDetailStatus` 永遠停在 `loading`，沒有「版本不相容」錯誤或重試入口。

**碼證**: `useICAnalysis.ts:211` 先設 `loading`；store `icAnalysisStore.ts:330-332` 在 loading 保留舊 detail；`useICAnalysis.ts:233-236` mismatch 直接 `resolve(null)`，未呼叫 `setFeatureDetail`。page `page.tsx:928-945` 只有 loading/missing/error UI。VERIFY：`(cd frontend && npx vitest run src/hooks/useICAnalysis.paging.test.ts -t 'revision 嚴格比較')` → 1 passed、9 skipped；該測試只斷言 detail 為 null，未斷言 status。RECHECK：以既有 detail＋store revision=2，mock feature response `result_revision=null`，重跑 hook 後應見 `featureDetailStatus='error'`／版本不相容文案與 retry；現行會是 `loading` 且保留舊 detail。

**來源摘要**: frontend/src/hooks/useICAnalysis.ts#4ebdb3b7eaab; frontend/src/store/icAnalysisStore.ts#4a7c7236d53c; frontend/src/app/ic-analysis/page.tsx#0f9a05b66678; docs/ICRESULT_PAGING_TODO.md#92df48946601

[P1/MAJOR] 信心度=High；refilter 與切特徵競速會正常觸發這條路徑，使用者會看到新特徵標籤覆蓋在舊圖上但永遠載入中，且無法自行重試。三值理由：使用者影響是錯誤世代被靜默保留；修法成本低（mismatch/null 轉 error，或明確清除並顯示版本不相容）；驗證成本低（補 status/error assertion）。

## CODEX-R2-P2-01

**斷言**: URL 還原接受任意正 `limit`，未套用 contract `limit_max=500`；`limit=99999` 時後端只回 500 rows，但 UI 以 99999 計算頁數並禁用下一頁，導致大部分結果不可瀏覽。

**碼證**: `page.tsx:161-172` 對 URL limit 只檢查 `>0`；`ICSummaryTable.tsx:120-122,539-545` 以 `params.limit` 計算頁數／下一頁；contract `ic_result_paging_contract.json:7-8` 為 max 500，後端 `ic_result_projection.py:141-145` 確實 clamp。RECHECK：以 `?limit=99999&page=1` 掛載 39k fixture，預期將 limit clamp 到 500 並可翻頁；現行顯示約 1 頁且下一頁 disabled。

**來源摘要**: frontend/src/app/ic-analysis/page.tsx#0f9a05b66678; frontend/src/components/ic-analysis/ICSummaryTable.tsx#c57c651465fe; momentum/Analysis/contracts/ic_result_paging_contract.json#022b5d819bea; api/services/ic_result_projection.py#c49dd6ece513

[P2/MINOR] 信心度=High；正常 UI 按鈕（50/100/200）不觸發，僅 URL／分享連結可觸發；修法是依 contract clamp 或拒絕超界 URL，並以回應 limit 同步狀態。

## 必答 1–7
1a/1b：`fetchResult` 與 `refilter` 均有 light guard；非 light response 不寫入 report。未見保留 full `summary_table`／per-feature 段的新路徑；後端舊版反例已有錯誤＋不吃測試。
2a/2b：summary/detail 均 abort 舊請求、嚴格比較 revision（含 null），409 最多重拉一次；本輪新發現是 detail mismatch 的 loading 卡死（P1-01）。
3a/3b：表格排序由後端決定；Auto-Suggest／批次 Watchlist 明示僅當頁。跨頁勾選以 Set membership 合併，deep-analysis／transform 仍送同一 `selectedFeatures` 名單；未見跨頁 payload 污染。
4a/4b：三層 `grouped_ic` 投影與 `reshapeGroupedForFeature` 逐值對齊 Grouped／Regime；`coverage_analysis` 改前即無消費者，未見新回歸。
5a/5b：目標 Vitest 84 檔／654 測試 rc=0；paging/圖表 targeted 5 檔／16 測試 rc=0。退化仍全綠：revision mismatch test 未鎖 detail status（P1-01）；150 ms detail debounce 與 300 ms search owner 不衝突。
6：無 ≥10× 不必要複雜；目前新增狀態與分頁邏輯均對應 contract。
7：B1 R1 四條修補與 R1 N1–N6 原反例已閉合；因本輪新增 P1-01，修補並補測後才可進 B3／UAT B34。

## §1／§0 摘要
矛盾／quant／cache／短命工：無新 finding。端到端／API／測試覆蓋：P1-01、P2-01。被當成事實的未驗證假設：事件 run metadata、deep 分頁圖表語意、URL replaceState 迴圈仍未以實機驗證；本輪不將其列為 blocking。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、SPEC/TODO、review skill；R7 stamp approved；R1 N1–N6 逐碼核對；feature mismatch targeted test rc=0；contract/backend limit clamp 逐碼核對。
TESTS_RUN: `(cd frontend && npx vitest run)` → 84 files/654 tests rc=0；`npx tsc --noEmit -p tsconfig.json` error TS 計數=8；`venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` → 41 passed/0 skipped rc=0；targeted paging/chart Vitest → 5 files/16 tests passed；`bash scripts/icresult_paging_phase_gate.sh 3` → rc=1，SIZE/LATENCY 均 BLOCKED（setup 連線 Binance 失敗，非產品 finding）。
FAILURES_SEEN: phase gate 受環境網路 setup 阻塞；未改碼、測試或 data_cache。
SCOPE_CHANGES: none（唯讀 review；僅新增本交件檔，未改根 HANDOFF.md）。
NUMERIC_OR_SCHEMA_IMPACT: 未修改產品數值、API schema 或輸出大小；僅記錄兩項前端狀態／分頁缺口。
HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R2-codex.md
TMP_CLEANUP: 已移除本輪建立的 `/tmp/icresult_frontend.diff`、`/tmp/icresult_b2r2_tsc.log`（後者原已不存在）；保留 `/tmp/claude-501`。
STATUS: DONE
