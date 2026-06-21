# B6 — 日期選擇 warmup-then-trim — SPEC

> 來源：使用者 2026-06-21 選 Option 1(輸出選定區間,計算多取前史 warmup)+ d* 三方 Option A(handoffs/20260622-dstar-ic-ml-*)。日期：2026-06-22｜對應 TODO：docs/B6_WARMUP_TRIM_TODO.md
>
> **目標**：選日期時,**輸出**只要 [start,end],但**計算**往 start 前多載 max_warmup_bars 歷史當 warmup,使非 fracdiff 特徵與全範圍同日期 **byte 一致**(Option 1)。fracdiff d* 因 first-500 校準→列**明確 byte-parity 例外**(Option A,安全非洩漏)。

## §RISK 風險分級
- **大小**：**大**。**命中 (d) 資料正確性**(warmup→特徵值;改共享 ingestion) + **(b) 共享路徑**(`_layer0` 單+批共用)。
- → §G 數值 N/A(行為性);以「**非 fracdiff** 特徵:同 date 的 date-windowed 輸出 vs 全範圍同日期 **byte 一致**」+「fracdiff 列例外」+「warmup 不足回報」+「PIT 無 look-ahead」驗證。**feature flag 預設關=今日 strict-window(B5)** 護欄。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read 實測,附行號):
  - `_layer0_data_ingestion`(feature_factory.py:738-749)對 date 是**嚴格 mask**(`data=data[start_mask]` 後 `[end_mask]`),計算前切窗,**無 warmup**(=B5 strict-window/Option2)。
  - per-indicator warmup 機制**已存在但 FF 生成未用**:`momentum/FeatureEngineering/atomic/warmup_lookup.py` `get_warmup_factor`/`get_warmup_bars(ind,period)=ceil(period×factor)`/`get_max_warmup_bars({ind:period})`(取代舊 blanket 4.5);現只 Analysis/chart/strategy 用(kline_cache/indicator_cache/chart_data_service)。
  - fracdiff d* 校準 `_calibration_series`(feature_preprocessor.py:180-182)用 `series.iloc[:bars]`(前 bars,bars=max(adf sample_size,calibration_bars,500));`_frac_diff_ffd` 對全長因果套用。
  - **無真正 expanding/全史型指標**:rolling_aggregator/_numba_transforms 的 cumsum 都是 rolling 實作(`cumsum_shifted[window:]=cumsum[:-window]`);唯一位置相依是 fracdiff d*(走 Option A 例外)。
  - config_hash 含 _start_date/_end_date(:3575-3576)→ date-windowed 與全範圍是不同 run。
  - IC-First:pre_ic(winsor+fracdiff,**無** rank/zscore)→ IC gate → post_ic(rank/zscore)。故 fracdiff 差異直接進 IC(三方確認)。
- **待確認**：無。**已確認**(2026-06-22 使用者 Option 1 + 三方 Option A)。

## §C 約束
- 解耦:重用 warmup_lookup;`_layer0`/輸出 trim 在引擎內;不新增跨域依賴。
- **不可違反**:① **非 fracdiff 特徵:date-windowed 輸出與全範圍同日期 byte 一致**(Option 1 核心);② **fracdiff d* = 明確 byte-parity 例外**(Option A;文件標明,非洩漏/非污染);③ **flag 關=今日 strict-window(B5)行為不變**;④ **warmup 不足不靜默**(後端回報需求量/實得量/受影響前段 + 前端警示);⑤ **PIT**:warmup 區=start 之前過去資料,無 look-ahead;⑥ 不改特徵公式/數值(只改「載多少資料 + 輸出 trim」)。
- 注意:max_warmup 須涵蓋**全部來源**(L1/L3/L6.5/fracdiff/native-tf),只取 L1 會低估。

## §G Golden / Baseline
- 數值 N/A(移 §N)。行為不變:**flag 關** `python scripts/build_l65_golden_baseline.py --check` PASS(strict-window 同 B5/今日)。

## §P Phase 與依賴

### Phase 1 — max_warmup_bars 計算(依賴:無)
**Task 1.1 — 全來源 warmup 估算**
- 目標:依本次 config 算 `max_warmup_bars = max(`L1:`get_max_warmup_bars({選用指標:period})`、L3 最大 rolling 窗、L6.5 winsor/zscore 窗、fracdiff calibration_bars、native-tf 放大後窗(scale_window_for_native)`)`,以 primary TF bar 為單位。
- 檔案:新 helper(feature_factory.py 或 preprocessing 中性處),重用 warmup_lookup。
- 驗證:已知 config→max_warmup 等於各來源最大值;`pytest tests/ -k warmup_bars_estimate`(含 native-tf 放大窗納入斷言)。
- 邊界:無 fracdiff/native-tf 時不計該源。不可做:不漏任一來源。

### Phase 2 — _layer0 載 warmup + 輸出 trim(依賴:Phase 1)
**Task 2.1 — _layer0 改載 [start-max_warmup_bars, end](flag 開)**
- 目標:flag 開且有 start_date 時,_layer0 mask 改為保留 `start - max_warmup_bars` 起的歷史(不是嚴格 start);flag 關=今日 strict。
- 檔案:feature_factory.py:738-749。
- 改法:start_mask 用 `index >= (start_ts - warmup_span)`;warmup_span 由 max_warmup_bars × primary TF 週期換算或用實際 bar 位移。
- 驗證:flag 開載入起點 ≤ start-warmup;`pytest tests/ -k warmup_ingest_range`。
- 邊界:start 前歷史不足→載到可得最早(記不足量,Task2.3);flag 關=strict。
**Task 2.2 — 輸出 trim 到 [start,end]**
- 目標:所有層計算完,**輸出前**把結果 trim 回 [start,end](warmup 區不輸出)。
- 檔案:feature_factory.py 輸出/persist 階段(L7 前)。
- 改法:依 index 在 [start,end] 取子集再 persist;確保各層/各 TF 對齊後 trim。
- 驗證:**非 fracdiff 特徵 date-windowed 輸出與全範圍同日期 byte 一致**(allclose,核心不變量);fracdiff 列例外;`pytest tests/ -k warmup_trim_parity`。
- 邊界:trim 後輸出列數=strict [start,end];native-tf 對齊後仍對。
**Task 2.3 — warmup 不足偵測 + 回報**
- 目標:`needed=max_warmup_bars` vs `available`(start 前實得 bar 數);不足→結構化回報(needed/available/受影響前段範圍)。
- 檔案:feature_factory.py + contracts/metadata。
- 驗證:模擬 start 近資料集開頭→回報不足量正確;`pytest tests/ -k warmup_insufficient_report`。
- 邊界:足夠→不報;完全無前史→needed/available=0 警示。

### Phase 3 — API + 前端警示(依賴:Phase 2)
**Task 3.1 — 不足警示穿 API + UI(不靜默)**
- 目標:warmup 不足 metadata 穿 Pydantic + WS/REST → 前端跳警示(「起點前歷史僅 Y/X 根,前 N 根品質降級」)。
- 檔案:api/models、feature_factory_ws/routes、frontend types/元件。
- 驗證:`cd frontend && npm run build` + **vitest 2 案例**(有不足→顯警示/足夠→不顯);後端 `pytest tests/api/ -k warmup_warning`。
- 邊界:足夠不顯;flag 關不顯(無 warmup 概念)。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(warmup 估算)/整合(非fracdiff byte parity vs 全範圍、fracdiff 例外)/前端(vitest 警示)/行為不變(flag 關 golden)。
- **防假綠**:用**真實 kline**(kline_cache.h5)非合成;非 fracdiff parity 須真比對全範圍同日期值(allclose)非 smoke。
- **核心不變量(可證偽)**:
  ① **非 fracdiff byte parity**:date-windowed(flag 開,warmup 足)某中段日期的非 fracdiff 特徵 == 全範圍同日期(`np.allclose` atol≤1e-6)。
  ② **fracdiff 例外**:fracdiff 特徵明確標記/文件為 byte-parity 例外,不納 parity 斷言(但驗證 PIT 無洩漏)。
  ③ **flag 關不變**:strict-window `build_l65_golden_baseline.py --check` PASS。
  ④ **trim 正確**:輸出列數=strict [start,end] 區間。
  ⑤ **warmup 不足回報**:needed/available 正確 + 前端警示。
  ⑥ **PIT**:warmup 區 index 全 < start(過去),iloc[:500] 取最早,無未來洩漏(assert max(warmup index)<start)。
- **行為不變**:flag 關 `build_l65_golden_baseline.py --check` PASS。
- **邊界目錄**:flag 關=strict/start 前不足→載最早+回報/完全無前史/native-tf 對齊後 trim/fracdiff 例外標記/非fracdiff parity allclose/PIT warmup<start。

## §R 回退
- **feature flag**(env,預設關=今日 strict-window B5 行為)總護欄;關閉即回 B5。每 Phase 獨立 commit。byte 變(flag 關)=立即 revert。

## §N N/A 登記
- §G Golden 數值:**N/A — 改「載多少資料+輸出trim」,非特徵公式**;改以 flag 關 `build_l65_golden_baseline.py --check` PASS(abs≤1e-6) + **非 fracdiff date-windowed vs 全範圍同日期 byte parity(allclose≤1e-6)** + fracdiff 例外 + warmup 不足回報 + PIT(warmup index<start) 驗證。
