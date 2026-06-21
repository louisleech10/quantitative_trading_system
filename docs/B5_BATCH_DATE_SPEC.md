# B5 — 批次特徵生成日期範圍 bug 修復 — SPEC

> 來源：使用者 2026-06-21 實測（選 167 天但批次跑 848 天全史）。日期：2026-06-21｜對應 TODO：docs/B5_BATCH_DATE_TODO.md
>
> **問題**：批次（≥2 symbol）worker `_compute_single` 不接收/不傳 `start_date`/`end_date` → `generate_features` 在全史生成，無視使用者日期選擇。單 symbol path 正確。

## §RISK 風險分級
- **大小**：中-大。
- **命中**：**(b) 批次 worker 共用路徑**(`_compute_single` 是所有 batch symbol 入口,B1/B2/B3 動過、有 mock/測試) + **(d) 資料正確性**(日期→生成用哪段資料,錯範圍=錯特徵,下游 IC/回測受影響)。
- → §G 數值 N/A(行為性);以「無 date 不變(`build_l65_golden_baseline.py --check`+spy)」+「date 生效(167天→~4009列 非20352)」+「config_hash 與單 path 一致」3 不變量驗證。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read/log 實測,附行號):
  - 批次 worker `_compute_single`(api/services/feature_factory_batch_service.py:1282)簽名 `(symbol,timeframe,config_override,force_regenerate,cache_dir=None,batch_id="")`——**無 start_date/end_date**;其 `factory.generate_features(symbol=,timeframe=,...)`(:~1340)**未傳 date**。
  - `run_in_executor` 呼 compute_fn(:581-590)只傳 symbol/timeframe/config_override/force_regenerate/batch_cache_dir/batch_id——**無 date**。
  - `generate_features`(momentum/FeatureEngineering/feature_factory.py:226)**有** start_date/end_date(:8-9),且 **config_hash 含 date**(`_compute_config_hash(config,symbol,timeframe,start_date=,end_date=)`:241)→ 傳 date 後 cache key 與單 path 一致,**無 stale 風險**。
  - 單 symbol path(api/services/feature_factory_service.py:251-272)正確讀 `getattr(request,"start_date")` 並傳 generate_features。
  - `BatchGenerateRequest`(api/models/feature_factory_models.py:39-40)**有** start_date/end_date(已從前端收到,只是 worker 沒用)。
  - **實測證據**:1 symbol primary 12h → native_rows=4009(=167 天,date 生效✓);2 symbol primary 12h → native_rows=20352(=848 天全史,date 失效✗)。
- **待確認**：無。**已確認**(2026-06-21 使用者:「有設日期就該只跑那段」=預期 date 生效,批次失效是 bug)。

## §C 約束
- 解耦:純 threading 既有參數,不新增跨域依賴。
- **不可違反**:① **無 date(None)=今日全史行為完全不變**(向後相容,golden+spy 驗);② date 傳入後 config_hash 含 date(與單 path 一致,cache 連貫不 stale);③ **不改數值計算邏輯**(只改「用哪段資料」的入口,不碰特徵公式/NaN gate);④ **同步更新所有 patch `_compute_single` 的 test mocks**(B1/B2/B3 加 batch_id 的前例:漏更會 TypeError 假綠)。
- 注意:date 改變生成輸出是**本修復的目的**(批次該尊重 date);非 date 路徑零變動。

## §G Golden / Baseline
- 數值 N/A(移 §N)。行為不變:**無 date** 時 `python scripts/build_l65_golden_baseline.py --check` PASS(golden 用全史,不傳 date→與今日一致)。date 生效另以新測驗。

## §P Phase 與依賴

### Phase 1 — threading date 穿批次路徑(依賴:無)
**Task 1.1 — _compute_single 接收 + 傳 date**
- 目標:`_compute_single` 加 `start_date`/`end_date` 參數,傳入 `factory.generate_features(...,start_date=,end_date=)`,比照單 path。
- 檔案:feature_factory_batch_service.py(`_compute_single`:1282 簽名 + generate_features 呼叫:~1340)。
- 改法:簽名加 `start_date: Optional[str]=None, end_date: Optional[str]=None`(位置與 run_in_executor 對齊);generate_features 呼叫補 `start_date=start_date, end_date=end_date`。
- 驗證:date 傳入時 generate_features 收到對的 date;`pytest tests/api/ -k batch_date_threading`。
- 邊界:None→不傳(今日行為)。　不可做:不改特徵公式/數值。

**Task 1.2 — run_in_executor 傳 request 的 date**
- 目標:`run_in_executor`(:581-590)補傳 `request.start_date, request.end_date` 到 compute_fn。
- 檔案:feature_factory_batch_service.py:581-590。
- 改法:args 加 request.start_date/request.end_date(與 _compute_single 簽名位置一致)。
- 驗證:批次 worker 收到 request 的 date;整合測 date-selected 批次生成列數=選定範圍(非全史);`pytest tests/api/ -k batch_date_applied`。
- 邊界:request 無 date(None)→全史(今日)。

**Task 1.3 — 更新 test mocks(防假綠)**
- 目標:所有 patch/mock `_compute_single` 的測試(B1/B2/B3 retention/logging/progress)簽名同步加 start_date/end_date,避免 TypeError 假綠。
- 檔案:tests/api/test_batch_retention.py、test_worker_logging.py、test_batch_*.py 等所有 _compute_single mock。
- 驗證:既有批次測試全綠(無 TypeError);`pytest tests/api/ -k batch -q`。
- 邊界:mock 簽名須與真實一致。　不可做:不放寬既有斷言。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(date threading)/整合(真實小 batch date-selected→列數=選定範圍)/行為不變(無 date golden+spy)/既有批次回歸。
- **防假綠**:不放寬既有測試;新斷言碰真實 generate_features date 參數 + 真實列數,非 smoke;所有 _compute_single mock 同步更新。
- **核心不變量(可證偽)**:
  ① **無 date 不變**:start_date/end_date=None 時批次 generate_features 收到 None、輸出與今日一致(spy 比對 call 參數 + `build_l65_golden_baseline.py --check` PASS)。
  ② **date 生效**:date-selected 批次的 generate_features 收到該 date,且生成列數=選定範圍(167 天→~4009 1h 列,**非 20352 全史**)——整合測 assert 列數/或 spy date 參數。
  ③ **config_hash 一致**:同 (symbol,tf,date,config) 批次與單 path 算出相同 config_hash(date 已入 hash)。
  ④ **既有批次測試綠**:mocks 更新後 `pytest tests/api/ -k batch` 全綠無 TypeError。
- **行為不變**:無 date `build_l65_golden_baseline.py --check` PASS(abs≤1e-6)。
- **邊界目錄**:None=今日全史/date 生效列數/config_hash 與單 path 一致/mocks 同步/不改特徵數值。

## §R 回退
- 純 threading,單點可 revert。無 date(None)即今日行為=天然向後相容護欄。byte 變(無 date 情境)=立即 revert。

## §N N/A 登記
- §G Golden 數值:**N/A — 改「用哪段資料」入口,非特徵數值公式**;改以無 date `build_l65_golden_baseline.py --check` PASS(abs≤1e-6,byte 不變)+ spy 驗 call 參數 + date 生效列數 + config_hash 一致 驗證。
