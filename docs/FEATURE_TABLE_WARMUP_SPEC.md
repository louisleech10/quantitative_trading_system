# Feature Table 暖機排序 UX 修復 — SPEC（V13，2026-06-03）

> 來源：2026-06-03 使用者回報 + log(CGSA stats deferred to warmup)+ grep 確認進度未暴露。對應 TODO：N/A(中型)。

## §RISK 風險分級
- 大小：**中**(前端為主 + 小後端 status 欄位)。命中原則：無 (a)-(d)(純 UX/狀態暴露,不改 stats 計算與數值)。→ 派 cursor。

## §A 假設與待使用者確認
- 已驗證事實:Feature Table 排序欄(mean/std/skew/kurt)由背景 `_start_cgsa_stats_warmup` thread **增量填**(log:`CGSA stats: N deferred to warmup (M computed now)`);後端**內部知道 computed/deferred 數但未暴露給前端**(grep 無 warmup_pct/stats_progress 對外欄位);前端在不完整 stats 上排序 → 暖機中一直重排,使用者不知進度/不知何時定案。
- 待確認:無。
- 已確認結果:使用者回報「排序一直變、不知 warmup 等多久才正確」即此,2026-06-03。

## §C 約束
- 解耦 7 條;**不得改 stats 數值計算邏輯**(只暴露進度 + 前端呈現)。後端動 `feature_factory_service`(stats warmup 進度暴露),前端動 `FeatureTable.tsx`。

## §G Golden / Baseline
- N/A(純 UX/狀態,無數值不變性需驗)→ 見 §N。

## §P Phase 與依賴
### Phase 1 — 後端暴露進度 + 前端呈現（依賴：無）
**Task W1 — 後端暴露 stats-warmup 進度**
- 檔案:`api/services/feature_factory_service.py`(stats warmup 內部已有 computed/total 計數,如 `_start_cgsa_stats_warmup` / stats cache),於 `browse_summary` 或新增/沿用 status 回傳 `stats_warmup: {computed, total, pct, complete}`。
- 改法:把已知的 computed/deferred 數對外暴露為結構化欄位;complete = (computed>=total)。
- 驗證:`pytest tests/api/` 斷言該欄位存在、warmup 進行中 0<pct<100、完成後 pct==100 且 complete==True。
- 邊界:stats 已 100% 快取 → 立即 complete=True;尚未啟動 → pct=0。
- 不可做:不改 stats 數值;不新增阻塞計算只為算進度(用已知計數)。

**Task W2 — 前端 Feature Table 顯示進度 + 標排序暫定**
- 檔案:`frontend/src/components/feature-factory/FeatureTable.tsx`(+ 相關 store/type)。
- 改法:讀 W1 的 `stats_warmup`;**complete 前**顯示進度條/「暖機計算中 X%,排序為暫定」提示;complete 後移除提示(排序已定案)。可選:未算的列標 computing。
- 驗證:前端 unit test——`stats_warmup.complete=false` 時渲染進度/暫定提示;`complete=true` 時不顯示;`npm run build` pass。
- 邊界:無 stats_warmup 欄位(舊 API)→ 不報錯、退回現狀;pct=100 → 無提示。
- 不可做:不得移除排序功能;不得在 complete 後仍顯示暫定。

## §V 驗證策略與邊界測試目錄
- 層級:單元(後端進度欄位)、前端 unit(提示顯示/隱藏)。可獨立 `pytest tests/api/` + `npm run test`。
- 防假綠:不得放寬既有斷言;新斷言對應進度欄位 + 前端提示條件。
- 邊界:pct=0 / 0<pct<100 / pct=100 / 已快取 / 舊 API 無欄位。

## §R 回退
- 單 commit 可 revert;純狀態暴露 + 前端呈現,零數值風險。

## §N N/A 登記
- §G Golden:N/A — 純 UX/狀態,無數值不變性可驗(以前端 unit + 後端進度斷言替代)。
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(無新效能硬約束)。
