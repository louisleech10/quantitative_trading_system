# 批次品質彙整修復 — SPEC（V13，2026-06-03）

> 來源：2026-06-03 多 symbol run 實測(case_search_api_20260603.log + 直接掃 BTCUSDT 1h parquet)。對應 TODO：N/A(中型,直接派工)。

## §RISK 風險分級
- 大小：**中**。命中原則：(a) 邊緣——**僅修品質「彙整顯示/評級」取數,不改特徵生成/NaN gate/數值**,故非實質 (a);(b) 動 `feature_factory_service` 共用路徑(讀,非寫資料)。→ 中型,派 cursor。

## §A 假設與待使用者確認
- 已驗證事實(實測 BTCUSDT 1h 真實 run 輸出,np.isnan 直接掃 parquet):**真實 NaN均≈12.17%、NaN峰≈85.32%**(非彙整顯示的 0.0%);**>10%NaN 特徵≈1565,其中純 leading 暖機 3387 / 含 mid-hole 真問題僅 19**;`null_count`(parquet metadata)盲於 IEEE-754 float NaN → 彙整 NaN均/峰 顯示 0;dq 子系統已有 `warmup_only_high_nan / real_problem / mid_holes / trailing_nans` 誠實分類(feature_factory_service.py:2569-2689)。
- 待確認:無。
- 已確認結果:使用者回報截圖(NaN峰0%卻警告1120、3 symbol 全 Watch)即此 bug,2026-06-03。

## §C 約束
- 解耦 7 條;**不得改特徵生成/NaN·inf gate/數值**(此為「顯示與評級取數」修正,非資料修正)。動 `feature_factory_batch_adapters.py` + 必要時 `feature_factory_service` 品質欄位。

## §G Golden / Baseline（輕量數值一致 gate）
- 凍結/驗證:對真實 BTCUSDT 1h 輸出,獨立 `np.isnan` 掃描得 baseline(NaN均≈0.12、NaN峰≈0.85、real_problem 數)。
- 通過條件(可證偽):修後彙整的 `nan_ratio_mean`/`nan_ratio_max` 與獨立 isna 掃描 **abs 差 ≤ 0.01**(不可再是 0);`alert_count`/評級以 **real_problem(非暖機含量)** 為準。

## §P Phase 與依賴
### Phase 1 — 批次彙整取數修正（依賴：無）
**Task Q1 — NaN均/峰 改用真實 NaN（去 null_count 盲點）**
- 檔案:`api/services/feature_factory_batch_adapters.py` → `_to_batch_quality()`(L70-104);若 `summary["quality"]` 的 nan_ratio 來自 null_count/catalog,改取真實來源(dq 分類已掃過的真實 nan,或 browse_summary 的真 isna 值)。
- 改法:`nan_ratio_mean/max` 取**真實 NaN**(與警告同源);保留 round。
- 驗證:`pytest` 用真實 parquet fixture,斷言 `nan_ratio_max > 0.5`(≈0.85)、`nan_ratio_mean` 與 np.isnan 掃描 abs≤0.01。
- 邊界:全 0 NaN 的 symbol → 0%;空目錄 → 不 crash。
- 不可做:不得回退成 null_count;不得改特徵資料。

**Task Q2 — 警告數/評級以 real_problem 為準,暖機分開顯示**
- 檔案:同上 `_to_batch_quality()` `alert_count`/grade 邏輯(L79-93)。
- 改法:`alert_count`(警告數)= dq `counts.real_problem`(mid-hole/all-NaN),**不取含暖機的 quality_alerts**;grade 用 real_problem 判(暖機不灌 Watch);回傳新增 `warmup_only_count` 供前端分開顯示。
- 驗證:`pytest` 全暖機 symbol(real_problem=0)→ grade=="pass" 且 alert_count==0、warmup_only_count>0;有 mid-hole(real_problem>0)→ grade∈{watch,reject}。
- 邊界:real_problem=0 但有暖機 → pass(不 Watch);real_problem>5 → watch。
- 不可做:不得把暖機 leading NaN 當警告/Watch。

**Task Q3 —（若 Q1 需要）後端品質欄位暴露真實 nan + warmup 拆分**
- 檔案:`feature_factory_service.py` 品質/summary 回傳(`browse_summary` 或 dq report),確保有「真實 nan_ratio」+「warmup_only vs real」欄位供 adapter 取用(多半已存在於 dq report,確認接通即可)。
- 驗證:`pytest` 斷言 dq report 含 real_problem 與真實 nan;adapter 取到非 0。
- 邊界:dq 未 warmup 完成時 → 有合理 fallback(標 computing 或用已算部分)。
- 不可做:不得新掃全量造成 summary 阻塞數分鐘(複用 dq 已算的)。

## §V 驗證策略與邊界測試目錄
- 層級:單元(adapter 取數)、整合(真實 parquet fixture 算彙整)、Golden(§G nan_ratio==isna)。可獨立 `pytest tests/api/`。
- 防假綠:不得放寬既有斷言;新斷言對應「NaN均非0、警告=real_problem」。
- 邊界:全暖機/有mid-hole/全0NaN/空目錄/dq warmup 未完成。

## §R 回退
- 單 commit 可 revert;純顯示/評級取數修正,不動特徵資料,回退零數值風險。

## §N N/A 登記
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(§C 已述,無新效能硬約束)。
