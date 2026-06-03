# NaN 5-number summary + real_problem 主指標 + Overview NaN 修 — SPEC（V13，2026-06-03）

> 來源：使用者指出 NaN均/峰 統計意義弱、易誤導;要改「真實 NaN 的 5-number(Min/Q1/Median/Q3/Max)」;警告數=real_problem 留用;Overview NaN 仍 0%(#4)。對應 TODO：N/A(中型)。

## §RISK 風險分級
- 大小：**中**。命中：(a) 資料品質「顯示指標」(非改特徵數值/NaN gate);(b) dq builder + browse_summary 共用路徑。→ cursor。

## §A 假設與待使用者確認
- 已驗證事實:① 批次 adapter `alert_count = real_problem`(警告數即 real_problem,使用者觀察正確);② dq builder 已有 per-column `col_nan_counts`(真實 NaN),可直接算分位數;③ **Overview「NaN Avg」走 `browse_summary` quality.nan_ratio_mean,仍 null_count → 0%**(批次那條 dq_v5 已修但 Overview 沒);④ raw parquet 實體欄位(~28k)≠ manifest 邏輯特徵(115,544),dq 母體為後者(故 NaN峰 95.8% 是對的);⑤ NaN均(被特徵組成稀釋)+ 單一NaN峰 統計意義弱。
- 待確認:無(使用者已定:NaN 統計改 5-number Min/Q1/Median/Q3/Max,警告數續用 real_problem)。
- 已確認結果:使用者 2026-06-03 指定「NaN 統計寫真實資料的 5-number;警告=real 數」。

## §C 約束
- 解耦 7 條;**不改特徵生成/NaN·inf gate/數值**(只改「顯示哪些品質指標」)。動 `feature_factory_service.py`(dq builder + browse_summary)、`feature_factory_batch_adapters.py`、前端 `BatchQualityOverview.tsx` + Overview dashboard。

## §G Golden / Baseline（5-number 數值一致）
- 驗證:dq/summary 算出的 NaN `{min,q1,median,q3,max}` 與獨立 `np.percentile(真實 per-feature isna 比例, [0,25,50,75,100])` **abs 差 ≤ 0.01**;Overview NaN 指標 **不再是 0**(median/分布反映真實)。

## §P Phase 與依賴
### Phase 1 — 後端算 5-number + 前端改欄（依賴：無）
**Task A1 — dq builder + browse_summary 算真實 NaN 5-number**
- 檔案:`api/services/feature_factory_service.py`(dq report 組裝用 `col_nan_counts`;`browse_summary` quality 區)。
- 改法:由真實 per-feature nan_ratio 算 `nan_ratio_quantiles = {min,q1,median,q3,max}`(np.percentile [0,25,50,75,100]);寫入 dq report **與** browse_summary.quality(供批次彙整 + Overview 同源);保留 real_problem/warmup_only。**browse_summary 不得再回 null_count 0**(#4)。
- 驗證:`pytest tests/api/` 斷言 dq report 與 browse_summary 皆含 `nan_ratio_quantiles` 五值、與 np.percentile(真實 isna)abs≤0.01、median 合理、max>0.5;**Overview 用的 summary 路徑 nan 指標 >0**。
- 邊界:全 0 NaN → 五值皆 0;無特徵 → 0 不報錯;沿用 dq_v5 快取(已含真實 nan,確認也存 quantiles,必要時 bump dq_v6)。
- 不可做:不新掃全量(複用 col_nan_counts);不改特徵數值。

**Task A2 — 批次 adapter:主指標 real_problem + 5-number;評級依 real_problem**
- 檔案:`api/services/feature_factory_batch_adapters.py` `_to_batch_quality`。
- 改法:回傳 `real_problem_count`(=警告數,已是)、`warmup_only_count`、`nan_quantiles{min,q1,median,q3,max}`;grade 依 real_problem 判(暖機不灌 Watch,沿用既有)。NaN均/峰 可保留於回傳但前端降級。
- 驗證:`pytest` 全暖機(real_problem=0)→ grade=pass;有 mid-hole → watch;回傳含 nan_quantiles 五值。
- 邊界:real_problem=0+高暖機 → pass;real_problem>5 → watch。
- 不可做:評級不得被暖機/NaN均灌成 Watch。

**Task A3 — 前端:批次彙整 + Overview 改顯示 5-number + real_problem 主位**
- 檔案:`frontend/src/components/feature-factory/BatchQualityOverview.tsx`、Overview dashboard(`OverviewDashboard.tsx`/相關)、`types.ts`。
- 改法:批次彙整表**主欄改 real_problem(真問題數)**,NaN 欄改顯示 **Min/Q1/Median/Q3/Max**(取代單一均/峰,或均/峰標「含暖機僅參考」降級);Overview 的「NaN Avg」改顯示真實(median 或 5-number),不再 0%。評級說明同步更新。
- 驗證:前端 unit——mock 回 nan_quantiles + real_problem → 表格渲染五值 + real_problem 欄;Overview NaN 顯示非 0;`npm run build` pass。
- 邊界:舊 API 無 quantiles → 退回顯示(不報錯);全 0 → 五值 0。
- 不可做:不移除既有欄位致崩;不顯示 null_count 的 0 當真實。

## §V 驗證策略與邊界測試目錄
- 層級:單元(5-number 計算)、整合(dq+summary 同源)、Golden(§G 5-number==np.percentile)、前端 unit。可獨立 `pytest tests/api/` + `npm run test`。
- 防假綠:不得放寬既有斷言;新斷言對應「5-number 與 percentile 一致、Overview 非0、評級依 real_problem」。
- 邊界:全0NaN / 全暖機 / 有mid-hole / 舊快取 / 舊 API 無 quantiles。

## §R 回退
- 單 commit 可 revert;純品質顯示指標,不動特徵資料,零數值風險。

## §N N/A 登記
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(複用 col_nan_counts 不增掃描成本)。
