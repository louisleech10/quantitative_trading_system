# B7 — L6.5 raw-sink 並行（方案 A）— SPEC

> 來源：L6.5 並行委員會階段1設計(handoffs/20260622-l65-parallel-*) + 階段2 profiling(handoffs/20260622-l65-profile-*,三方 CPU-bound 確認)。使用者 2026-06-22 選「先做 A(並行),完成後手動跑收時間/RSS」。日期：2026-06-22｜對應 TODO：docs/B7_L65_PARALLEL_TODO.md
>
> **方案 A**：把 L6.5 raw-sink 目前 `effective_workers=1`(序列)的**窄 native-tf compute 群** ThreadPool 並行;父維持**單一有序 sink**(磁碟安全);RSS gate 防爆;寬群維持序列。**byte-parity 為核心閘:並行輸出必須與序列 byte 一致**。

## §RISK 風險分級
- **大小**：**大**。**命中 (b)** L6.5 共用 hot path + 併發(race/sink 順序/RSS) + byte-parity。**不命中 (d)**——並行不改 winsor 數值(byte-parity 閘保證輸出不變);非改特徵公式。
- → §G 數值 N/A;以「**serial vs parallel byte 一致**(核心)+ golden + RSS 不超 tier + 窄寬分流 + flag 關不變」驗證。**flag 預設關=今日序列(effective_workers=1)** 護欄。

## §A 假設與待使用者確認（profiling 實證）
- **已驗證事實**(grep/Read/profiling,附行號):
  - raw-sink 現 `effective_workers=1`(feature_preprocessor.py:441/448-449,序列 for 磁碟安全);`group_plan`(:470-496) 有序;ThreadPool 已用於 `_transform_registry_parallel`(:379/1441),`from concurrent.futures import ThreadPoolExecutor, as_completed`(:9)。
  - **profiling 三方 CPU-bound**:native-tf transform 佔 95-99%,load+sink<5%,idx_map<0.2%,per-group 物件/讀盤開銷<0.5%(handoffs/20260622-l65-profile-codex/composer)。
  - **瓶頸=scaled-window winsor**:`_rolling_quantile_sliding_numba`(_numba_transforms.py:218)維護排序陣列但**插入/移除 O(window) 陣列搬移**(:33-34/51-52)→ 整體 **O(n×window)**;1h→12h primary 窗 252→3024 → 同 20352 列 7.6x/群(profiling)。
  - 群獨立(各 group_id 自有 native_arr→transform→idx_map→sink);numba `@njit` 釋 GIL(`_numba_transforms.py:38-46` 註 numba parallel=True+外層 ThreadPool **不安全**,禁)。
  - tier:`get_current_tier_gb`(8/16/24/32);本機 `os.cpu_count()=8`。
- **待確認**：無。**已確認**(2026-06-22 使用者:先做 A,完成手動驗時間/RSS)。

## §C 約束
- 解耦:沿用既有 ThreadPool 模式;不新增跨域依賴。
- **不可違反**:① **byte-parity(核心)**:並行輸出與序列**逐欄 byte 一致**(allclose≤1e-6+NaN mask;群獨立→完成順序不影響);② **單一有序 sink**:父端依 `group_plan` 順序單 writer 寫盤(保磁碟/manifest 安全,現序列主因);③ **RSS 不爆**:per-worker peak 估 × workers + current ≤ tier budget,超→背壓暫停+drain;④ **窄並行/寬序列**:寬群(高 RSS/slow-path fracdiff·ADF·gaussian)維持序列;⑤ **flag 預設關=今日序列**(effective_workers=1);⑥ **不用 ProcessPool**(pickle/記憶體×N,registry 不可 pickle);⑦ 禁 numba parallel=True + 外層 ThreadPool。
- 注意:queued 完成結果 bytes 須計入 RSS gate(父端有序寫前暫存)。

## §G Golden / Baseline
- 數值 N/A(移 §N)。行為不變:flag 關 `python scripts/build_l65_golden_baseline.py --check` PASS(序列=今日)。

## §P Phase 與依賴

### Phase 1 — 窄/寬分流 + worker 公式 + RSS gate(依賴:無)
**Task 1.1 — 分群 eligibility + tier worker + RSS budget**
- 目標:每 group 估 `working_peak = native_rows*cols*4*3 + primary_rows*cols*4 + idx_map_bytes`;**narrow eligible** iff `working_peak ≤ min(512MiB, rss_budget/(workers+1))` 且 `cols ≤ split_threshold/2` 且非 slow-path(fracdiff/ADF/gaussian-non-all);否則 wide→serial。worker:`cpu_cap=min(max(os.cpu_count()-1,1),8)`;tier_base `{8GB:2,16:4,24:6,32:8}`;`effective=min(tier_base,cpu_cap,floor(rss_budget/p95_task_peak))`。`rss_budget=tier_gb*0.55-current_rss_gb-reserve`;reserve `{8:2,16:3,24:4,32:5}`GiB。
- 檔案:feature_preprocessor.py(raw-sink 區 :440-560)。
- 驗證:已知 group shape→eligibility/worker 數正確;`pytest tests/ -k l65_parallel_gate`。
- 邊界:unknown shape/RSS 不可得→serial(fail-closed)。不可做:寬群不並行。

### Phase 2 — ThreadPool compute + 父有序 sink(依賴:Phase 1)
**Task 2.1 — 並行窄群 compute + 單一有序 sink + RSS 背壓**
- 目標:窄群 `ThreadPoolExecutor(effective)` 並行跑 compute(transform→aligned array);worker 回傳 array+metadata;**父依 group_plan 順序單 writer sink**;提交前 RSS gate(Σ inflight peak+current≤budget)否則暫停 drain。
- 檔案:feature_preprocessor.py(raw-sink 迴圈)。
- 改法:flag 開且有 narrow 群→並行 compute、有序 sink;寬群+flag 關→現序列路徑不變。
- 驗證:**serial vs parallel byte 一致**(見 §V);RSS 不超 budget;`pytest tests/ -k "l65_parallel_parity or l65_parallel_rss"`。
- 邊界:numba 不可 parallel=True;sink 單 writer;flag 關=今日。不可做:不改 winsor 數值/sink 順序語意。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(分群/worker/RSS 估算)/整合(serial vs parallel byte,**真實 kline**)/行為不變(flag 關 golden)/RSS。
- **防假綠**:真實 kline 非合成;parity 真逐欄比序列輸出;不放寬既有測試。
- **核心不變量(可證偽)**:
  ① **byte-parity(核心)**:同 config/symbol/TF,**flag-on(並行)輸出 == flag-off(序列)輸出**,所有 L7 raw 欄 `np.allclose(atol≤1e-6)` + NaN mask 一致 + row_count/group 數/manifest 一致(真實 kline,含多窄 L3 群觸發並行)。
  ② **RSS 不爆**:並行峰值 RSS ≤ tier budget(mock tier + 監測 peak);超閾值→背壓暫停而非 OOM。
  ③ **窄寬分流**:寬群(高 RSS/slow-path)走序列、窄群走並行(spy 路徑)。
  ④ **flag 關不變**:`build_l65_golden_baseline.py --check` PASS + effective_workers=1 行為同今日。
  ⑤ **sink 有序**:輸出 group/欄順序與序列一致(byte-parity 涵蓋)。
- **行為不變**:flag 關 `build_l65_golden_baseline.py --check` PASS。
- **邊界目錄**:flag 關=序列/unknown shape→serial fail-closed/寬群序列/RSS 超→背壓不 OOM/numba 非 parallel=True/sink 單 writer 有序/parity allclose+NaN mask。
- **hermetic**:整合測重導 tmp(data_cache_path+FFACT_CGSA_WORK_DIR),跑前後 data_cache 全量 diff 空(B5 教訓)。

## §R 回退
- **feature flag**(env,預設關=今日 `effective_workers=1` 序列)總護欄;關閉即回今日。byte-parity 失敗或 RSS 爆=立即 revert/關 flag。每 Phase 獨立 commit。

## §N N/A 登記
- §G Golden 數值:**N/A — 並行不改 winsor 數值(byte-parity 閘保證)**;改以 **serial vs parallel byte 一致(allclose≤1e-6+NaN mask)** + flag 關 `build_l65_golden_baseline.py --check` PASS + RSS 不超 tier 驗證。
