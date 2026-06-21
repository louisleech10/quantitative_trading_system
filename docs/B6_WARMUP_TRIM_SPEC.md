# B6 — 日期選擇 warmup-then-trim（選項 1）— SPEC v2

> 來源：使用者選 Option 1(2026-06-22) + d* Option A 三方(handoffs/20260622-dstar-ic-ml-*) + B6 Option-1 設計委員會三方(handoffs/20260622-b6-opt1-*)。日期：2026-06-22｜對應 TODO：docs/B6_WARMUP_TRIM_TODO.md
>
> **選項 1 定義**：選日期時載入 `[start-max_warmup, end]` 因果計算,**所有公開輸出 trim 到 [start,end]**。**不承諾與全範圍 byte parity**(fracdiff/ADF/cumulative/post-IC 本質位置相依)。目標=**前段特徵可用(非 NaN 降級)+ run 內自洽因果**。

## §RISK 風險分級
- **大小**：**大**。**命中 (b)** 共享 ingestion/多 persist 路徑 + **(d)** 資料正確性(warmup→前段特徵可用性;因果)。
- → §G 數值 N/A;以「品質增益(flag-on 前段 NaN 降)+ 子集 allclose(輔)+ 因果(ingest<start)+ 自洽 + warmup 不外露」驗證(見 §V)。**flag 預設關=今日 strict-window(B5)** 護欄。

## §A 假設與待使用者確認（三方驗證）
- **已驗證事實**(grep/Read 實測,附行號):
  - `_layer0_data_ingestion`(feature_factory.py:738-749)date strict mask(計算前切窗,無 warmup)=B5 行為。
  - warmup 機制 `warmup_lookup.py`(get_warmup_factor/get_max_warmup_bars/get_pattern_default_bars)**FF 生成未用**;`burn_in_from_dataset_start` **僅 yaml 註記未實作**(`_cached_cumulative`:67 載入後無人消費)→cumulative 對給定範圍累加。
  - `_calibration_series`(:180-182)`iloc[:bars]` 前 bars 列→消費端 dropna→head;**僅 fracdiff(:3594/3699)+ADF(:3334)用**(位置相依→排除 parity)。
  - cumulative OBV/AD/ADOSC/VWAP(warmup_table.yaml:360-390)自 ingest 起累加,絕對值 run-relative(yaml 註「absolute level not comparable」)→排除 parity。
  - labels(label_generator.py)`shift(-horizon)` binary[3,5,8,13,21]/reg[5,13]→尾端 max=21 根自然 NaN(end 側,B6 start-scope 外)。
  - 多 TF 各自 `_layer0`(multi_tf_generator);多 persist 路徑:normal L7、CGSA `_layer7_raw/_validate`、multi-TF primary_raw、IC-first raw+processed。
  - config_hash 含 _start_date/_end_date(:3575)→date-windowed 與全範圍是不同 run。
- **待確認**：無。**已確認**(2026-06-22 使用者 Option 1 + 三方 Option-1 設計委員會)。

## §C 約束
- 解耦:重用 warmup_lookup;OutputWindow/trim 在引擎內;不新增跨域依賴。
- **不可違反**:① **不承諾 byte parity**(明示);成功定義=品質增益+因果+不外露;② **warmup 列絕不外露**(features/labels/HDF5/CGSA raw/registry row_count/manifest row_index·time_range/browse/batch checkpoint 全從 requested start 起);③ **因果**:ingest 區 index 全 < start(過去),無 look-ahead;校準列取自 ingest 前段非 start 後;④ **排除 parity 表**(位置相依,文件標、allclose 子集排除):**cumulative(OBV/AD/ADOSC/VWAP)、fracdiff d*、ADF order、post-IC/API rank-zscore、labels horizon**;⑤ **flag 關=今日 strict-window(B5)完全不變**;⑥ warmup 不足不靜默(回報+UI);⑦ 不改特徵公式/數值/不弱化 NaN·inf gate;⑧ **resume**:strict-window checkpoint 不得偽裝成 warmup-enabled(B6 初版可禁 warmup+stream-resume 或 resume 後重算 L7 裁切)。
- 注意:cumulative anchor=ingest_start(文件 `cumulative_anchor`);labels metadata `label_tail_nan_bars`/`label_valid_through`。

## §G Golden / Baseline
- 數值 N/A(移 §N)。行為不變:**flag 關** `python scripts/build_l65_golden_baseline.py --check` PASS(strict-window 同 B5)。

## §P Phase 與依賴

### Phase 1 — max_warmup + OutputWindow(依賴:無)
**Task 1.1 — max_warmup_bars 全來源 + OutputWindow**
- 目標:generate 入口算一次 `OutputWindow(ingest_start, output_start=start, output_end=end)`;`max_warmup_bars(primary TF)=max(` **L1** get_max_warmup_bars(ind:period)+CDL get_pattern_default_bars+**L1 advanced atomic 獨立窗**(microstructure/entropy/tail_risk/hurst/perm/mdd 的 config windows,warmup_lookup 未必涵蓋→逐 config 列舉,Codex MAJOR2);**L2** max(momentum lags,WQ windows,decay_linear);**L3** max(rolling windows);**L4** max(config lags|adaptive seq×ratio);**L5 cross-sectional**(RelativeStrengthProcessor.compute_beta rolling window,feature_factory.py:1812;**reference symbol(BTC)也須同 warmup**,Codex MAJOR1);**L6/meta** 任何顯式 rolling 窗(cycle/entropy/tail-risk/microstructure);**L6.5** max(winsor窗,rank窗,zscore windows,fracdiff max_lag,ADF max_lag,calibration_bars);**native-tf** 各次 TF scale_window_for_native 取 max;**validator** winsor fallback 窗(僅 L6.5 winsor off)`)`。**排除**(位置相依不靠有限 warmup):cumulative/fracdiff d*/ADF order/post-IC/labels。
- 檔案:新 helper(feature_factory.py/preprocessing 中性),重用 warmup_lookup。
- 驗證:已知 config→max_warmup=各源最大(含 native-tf 放大);`pytest tests/ -k warmup_bars_estimate`(逐源單測)。
- 邊界:無 fracdiff/native-tf 不計該源。不可做:不漏源、cumulative 不納。

### Phase 2 — 載 warmup + 單 trim choke(依賴:Phase 1)
**Task 2.1 — _layer0 per-TF 載 [ingest_start, end]**
- 目標:flag 開+有 start→各 TF `_layer0` 載入起點回推 warmup(primary 用 max_warmup_bars;**次 TF 用 primary ingest_start 反推 source 時間跨度**,非共用 primary bar 數);flag 關=strict。
- 檔案:feature_factory.py:738-749 + multi_tf_generator(per-TF)。
- 驗證:flag 開各 TF ingest 起點 ≤ 對應 warmup 起;`pytest tests/ -k warmup_ingest_range_multitf`。
- 邊界:前史不足→載最早+記不足(Task2.3);flag 關 strict。
**Task 2.2 — 單一 trim choke 貫穿 4 persist 路徑**
- 目標:`_trim_to_output_window(OutputWindow)` 於**每個公開輸出前**套用:features/labels + manifest row_count/time_range + sidecar。
- 檔案:feature_factory.py(normal L7、CGSA `_layer7_raw/_validate`、multi-TF primary_raw、IC-first raw+processed)+ feature_storage。
- 改法:單 helper 依 index∈[start,end] 裁;各 persist 面呼叫;CGSA L3 stream 中間 shard 可暫含 warmup→L7 finalize 裁 manifest(或標中間非公開)。
- 驗證:**T2 warmup 不外露**:所有公開輸出(features/labels/HDF5/CGSA raw manifest/registry row_count/browse/checkpoint)首列==start、row_count==|[start,end]|;`pytest tests/ -k warmup_trim_no_leak`(逐 persist 路徑)。
- 邊界:多 TF 對齊後 trim;native-tf 對齊後對。不可做:不改特徵值。
**Task 2.3 — warmup 不足偵測 + metadata**
- 目標:`needed=max_warmup_bars` vs `available`(ingest_start 前實得 bar);不足→`warmup_insufficient` metadata(needed/available/受影響前段)。labels:`label_tail_nan_bars=max(horizons)`/`label_valid_through`。cumulative:`cumulative_anchor=ingest_start`。
- 檔案:feature_factory.py + contracts/metadata。
- 驗證:模擬 start 近開頭→needed/available 正確;`pytest tests/ -k warmup_insufficient_report`。
- 邊界:足夠不報;無前史 available=0/needed=max_warmup 強制警示。

### Phase 3 — API + 前端警示(依賴:Phase 2)
**Task 3.1 — warmup_insufficient 穿 API + UI(不靜默)**
- 目標:不足 metadata 穿 Pydantic **凍結欄位 `warmup_insufficient{needed:int, available:int, affected_bars:int}`** + WS/REST + batch checkpoint 保留 → 前端警示(needed/available/前 affected_bars 根降級);vitest selector 對應。
- 檔案:api/models、feature_factory_ws/routes、frontend types/元件。
- 驗證:`cd frontend && npm run build` + **vitest 2 案例**(不足顯/足夠不顯);`pytest tests/api/ -k warmup_warning`。
- 邊界:足夠不顯;flag 關不顯。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(warmup 估算)/整合(品質增益+子集 allclose,**真實 kline_cache.h5**)/前端(vitest)/行為不變(flag 關 golden)。
- **防假綠**:用真實 kline 非合成;品質增益測位置不變欄;不外露逐 persist 路徑驗;不放寬既有測試。
- **核心驗收(可證偽,三方定)**:
  ① **A 品質增益(主)**:同 symbol/TF/[start,end],flag-on vs flag-off,對 **POSITION_INDEPENDENT 欄**,start 後 K=min(50,max_warmup/4) 根 `valid_frac`(非 NaN 比例)assert on≥off+δ(δ=0.05 起,真實 kline 校);warmup 不足→可 on≈off+標 warmup_insufficient。**POSITION_INDEPENDENT 判定式(兩家 MAJOR,防量錯欄假綠)**=`L7 pre-IC 持久化欄 − 排除表`(regex 排除:`OBV|AD|ADOSC|VWAP`、`fracdiff_*`、`adf_*`/`*diff_order`、`label_*`、`post_ic_*`);fixture 明列受測欄。**品質增益測限 non-IC-first 或 mock IC**(IC-first 選特結構差異不追,Composer non-blocking)。
  ② **B 子集 allclose(輔,非阻塞)**:排除表外欄,same window+available≥needed 時 date-windowed vs 全範圍同日期 `allclose≤1e-6`+NaN mask 一致;失敗僅 regression 記錄不擋。
  ③ **C 因果**:`max(ingest_index)<start`;features/IC 輸出 index∈[start,end];fracdiff/ADF 校準列取自 ingest 前 min(500,len) 非 start 後(assert calibration slice 上界<start 後段)。
  ④ **D 自洽**:同參數重跑 byte 一致;`row_count==|[start,end]|`;metadata 與列數一致。
  ⑤ **T2 不外露**:逐 persist 路徑(normal/CGSA raw/multi-TF/IC-first/browse/checkpoint)首列=start。
  ⑥ **flag 關不變**:strict `build_l65_golden_baseline.py --check` PASS。
- **行為不變**:flag 關 `build_l65_golden_baseline.py --check` PASS。
- **邊界目錄**:flag 關=strict/前史不足→載最早+回報/完全無前史/多TF per-TF warmup/native-tf 對齊後 trim/排除表欄不納 allclose/labels 尾 NaN 標記/PIT ingest<start/resume 不偽裝。

## §R 回退
- **feature flag `FFACT_WARMUP_TRIM`**(env,預設 `"0"`=今日 strict-window B5)總護欄;關閉即回 B5。**flag 不納 config_hash**(strict 與 warmup 同 hash→cache 不分裂;但 strict checkpoint 不得偽裝 warmup-enabled,見 §C⑧)。每 Phase 獨立 commit。byte 變(flag 關)=立即 revert。

## §N N/A 登記
- §G Golden 數值:**N/A — 改「載多少資料+輸出trim」,非特徵公式**;改以 flag 關 `build_l65_golden_baseline.py --check` PASS(abs≤1e-6) + 品質增益(flag-on valid_frac≥off+0.05) + 子集 allclose(輔) + 因果(ingest_index<start) + 自洽(row_count==|[start,end]|) + T2 不外露 驗證。
