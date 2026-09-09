# Reconcile — 20260909-icresultpaging-b2-review-r2

**來源** 20260909-ICRESULTPAGING-B2-REVIEW-R2-codex.md, 20260909-ICRESULTPAGING-B2-REVIEW-R2-composer.md, 20260909-ICRESULTPAGING-B2-REVIEW-R2-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可合併、可進 B3」（sentinel `COMPOSER-R2-P3-00`）／grok「可合併、可進 B3」（附 1 P2）；codex 1 P1＋1 P2。R1 N1–N6 三家皆 CLOSED。

### M1 — P1／P2 detail 回應 revision 不符（含 null）被丟棄後 `featureDetailStatus` 永停 loading、無重試（`CODEX-R2-P1-01`、`GROK-R2-P2-01`）
**處置**：丟棄時 `setFeatureDetail(null,'error',文案)`（null ⇒「缺少 result_revision（版本不相容）」；不符 ⇒「舊世代…請重試」）；既有 error UI 提供重試；vitest 斷言 status=error＋文案。

### M2 — P2 URL `limit` 未依 contract clamp，`?limit=99999` 讓 UI 頁數算錯（`CODEX-R2-P2-01`）
**處置**：URL 還原 `Math.min(limit, 500)`；page 測試 `?limit=99999` ⇒ 請求 `limit=500`、store 500。

Verdict: 可合併、可進 B3——M1／M2 已修（commit 見 HANDOFF）；composer／grok 已判可進 B3，codex 之 P1 為狀態機收斂、修法與其建議同形；不再開 R3，收案時三家 stamp。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R2-P3-00

**斷言**: 本輪（R2）對 R1 群集 N1–N6 及 composer 原提出之 COMPOSER-R1-P1-01／P2-01 重跑同一反例後，無新增可證偽之 P0／P1／P2 產品缺陷；修法未引入可重現的 revision 穿透、全量塞入或圖表靜默空白。

**碼證**: VERIFY 表（vitest 654 passed、tsc 8、pytest 41 passed、gate 3 PASS、baseline sha OK）；N1–N6 反例測試全綠（`useICAnalysis.paging.test.ts` 11 條、`ICSummaryTable.paging.test.tsx` 含 page50 取消＋search 同步、`FilterFunnelChart.funnel.test.tsx` input null、`icGrouped.test.ts`、`test_feature_detail_grouped_ic_three_level_projection`）；`useICAnalysis.ts:746-749` refilter 守衛與 fetchResult 對稱。

**來源摘要**: handoffs/20260909-ICRESULTPAGING-B2-REVIEW-R2-BRIEF.md#3a88f8d762b0

本輪逐項核對後無 finding。核對依據＝brief 必答 1–7 全表＋§0 前提挑戰＋R1 synth N1–N6 對照現碼（HEAD `4940f967`）；獨立重跑驗收命令；唯讀 review 未改 production／test／docs。

---

## GROK-R2-P2-01

**斷言**: `fetchFeatureDetail` 在 store `resultRevision` 非 null 且回應 `result_revision` 不符（含 null）時直接 `return resolve(null)`，不呼叫 `setFeatureDetail(..., 'error'|'idle')`，使 `featureDetailStatus` 永久停在先前寫入的 `loading`，舊 detail 圖表繼續顯示且無重試鈕。

**碼證**: `frontend/src/hooks/useICAnalysis.ts:211` 先 `setFeatureDetail(null,'loading')`（保留舊 detail）；`:235` 嚴格比較失敗僅 `return resolve(null)`。對照 summary `:170-173` 會 `setSummaryError`＋`summaryLoading` 於 finally 清掉。vitest `revision 嚴格比較…` 只斷言 `featureDetail===null`、不斷言 status。RECHECK：store revision=5、mock feature `result_revision=null`、先前 detail 非 null ⇒ 預期 status=`error`（或 idle）＋可重試；現行 status=`loading`。

**來源摘要**: frontend/src/hooks/useICAnalysis.ts#4f84c7c55861

[P2/MINOR] 信心度=High。N5 丟棄語意已對；缺的是丟棄後狀態機。部分升級／無戳 feature 端會讓基本分頁圖表遮罩永不消失。修法：與 summary 同形——null 戳⇒ setFeatureDetail(null,'error','後端回應缺少 result_revision（版本不相容')）；非 null 不符⇒ error 或 idle；補 vitest 斷言 status。不阻 B3／UAT B34。

---

