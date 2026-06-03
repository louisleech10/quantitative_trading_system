# dq 快取真實 NaN + 版本失效 — SPEC（V13，2026-06-03）

> 來源：#2 修後實機仍 NaN均/峰=0。實測根因:dq disk 快取(dq_v4,pre-fix)無 nan_ratio 欄位。對應 TODO：N/A(中型)。

## §RISK 風險分級
- 大小：**中**。命中：(a) 資料品質「顯示」(非改特徵數值/NaN gate);(b) dq builder 共用(餵 data quality dashboard + 批次彙整)。→ cursor。

## §A 假設與待使用者確認
- 已驗證事實(實測):① `data_cache/features/*/1h/*/data_quality.json` schema `dq_v4`、mtime 20:50(修正前)、**`nan_ratio_mean/max` 欄位 = None**(根本沒寫);② #2 adapter `_to_batch_quality`:`dq.get("nan_ratio_mean") is None → fallback quality(summary null_count)=0`;③ Q3 把真實 nan 加進「重算」但**未 bump 快取 schema_version** → 舊 dq_v4 快取一直被載、不重算 → 修正套不到既有資料;④ dq builder 已有 per-column `col_nan_counts`(feature_factory_service.py:~2199);⑤ 真實 NaN均≈12%/峰≈85%(np.isnan 直掃 parquet);⑥ #2 測試只用 in-memory frame,**未涵蓋 dq 快取路徑** → 假性通過。
- 待確認:無。
- 已確認結果:使用者 2026-06-03 兩度回報 NaN均/峰/常數=0(含恢復後仍 0)。

## §C 約束
- 解耦 7 條;**不改特徵生成/NaN·inf gate/數值**(只讓 dq report 含真實 nan_ratio + 失效舊快取)。動 `api/services/feature_factory_service.py` dq builder/cache 版本。

## §G Golden / Baseline（輕量數值一致）
- 驗證:對真實 BTCUSDT 1h,重算後 dq report 的 `nan_ratio_mean/max` 與獨立 `np.isnan` 掃描 **abs 差 ≤ 0.01**,且 `nan_ratio_max > 0.5`(≈0.85),不可再是 0/None。

## §P Phase 與依賴
### Phase 1 — dq builder 補 nan_ratio + 快取失效（依賴：無）
**Task N1 — dq report 含真實 nan_ratio_mean/max**
- 檔案:`api/services/feature_factory_service.py` dq report 組裝(`_build_data_quality_cgsa` / `_assemble_data_quality_report`,用既有 `col_nan_counts`)。
- 改法:`nan_ratio_mean = mean(col_nan_counts / n_rows)`、`nan_ratio_max = max(...)`,寫入 dq report(供 adapter 與 dashboard 取真實值);不新掃全量(複用 col_nan_counts)。
- 驗證:`pytest tests/api/` 斷言 dq report 含 `nan_ratio_mean/max` 且 > 0(對有暖機 NaN 的 fixture);與獨立 isna abs≤0.01。
- 邊界:全 0 NaN → 0;無特徵 → 0 不報錯。
- 不可做:不新掃全量造成阻塞;不改特徵數值。

**Task N2 — bump dq 快取 schema_version 失效舊快取**
- 檔案:同上(dq schema_version 常數 `dq_v4`)。
- 改法:`dq_v4`→`dq_v5`;載入快取時 schema 不符 → 視為 miss、重算(沿用既有版本檢查機制);確認重算寫回含 nan_ratio 的新快取。
- 驗證:`pytest` 放一個 `dq_v4`(無 nan_ratio)舊快取 → 載入判定 miss → 重算 → 新快取 schema=dq_v5 且含 nan_ratio。
- 邊界:無舊快取 → 直接算;dq_v5 快取存在 → 命中不重算。
- 不可做:不刪使用者磁碟資料(靠版本失效,非 rm)。

**Task N3 — 測試補 dq 快取路徑（防再假性通過）**
- 檔案:`tests/api/test_feature_factory_batch_quality.py`(或對應)。
- 改法:新增測試**走 dq 快取/恢復路徑**(非僅 in-memory frame):模擬有 dq report 快取時,批次彙整 adapter 取到的 `nan_ratio_max>0.5`、`grade` 反映 real_problem;舊 dq_v4 快取存在時不得回 0。
- 驗證:該測試在「舊 dq_v4 快取」情境下**會抓到 0(若版本沒升)**,版本升後通過。
- 邊界:有/無快取、dq_v4/dq_v5。
- 不可做:不放寬既有斷言。

## §V 驗證策略與邊界測試目錄
- 層級:單元(dq builder nan_ratio)、整合(快取失效→重算)、Golden(§G nan_ratio==isna)、防回歸(快取路徑測試)。可獨立 `pytest tests/api/`。
- 防假綠:不得放寬;新斷言對應「dq 含真實 nan_ratio、舊快取失效重算、快取路徑非 0」。
- 邊界:dq_v4 舊快取 / dq_v5 新快取 / 無快取 / 全 0 NaN / 全暖機。

## §R 回退
- 單 commit 可 revert;純 dq report 欄位 + 快取版本,不動特徵資料(版本回退即用回舊快取),零數值風險。

## §N N/A 登記
- §0.A 反幻覺:N/A(執行端合約覆蓋)。§1.1 C-OPT 表:N/A(無新效能硬約束;聚合 col_nan_counts 不新增掃描成本)。
