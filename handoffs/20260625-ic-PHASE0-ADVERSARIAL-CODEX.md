## Verdict：需修補後派工

## Findings

1. [BLOCKING] 信心度 High  
證據：SPEC §A「IC-TIMEAXIS... bug 在真實路徑必觸發」；程式 `ic_engine.py:_get_time_index` 對 `raw_data[col]` 這個 Series 呼叫 `pd.to_datetime(values, unit="ms")`。我用純 pandas 驗證：輸入 Series 時回傳的是 `Series`，不是 `DatetimeIndex`，因此 `_iter_time_groups` 的 `time_index.to_series()` 會先 `AttributeError`。  
會怎麼失敗：實作端只修秒/毫秒，測 by_year 可能仍過不了真實 RangeIndex+timestamp 路徑；不是穩定產出 1970 錯鍵，而是可能先崩。  
修法：Task 2.1/2.2 必須明確要求 `_get_time_index` 回傳與 `raw_data.index` 對齊的時間 Series/DatetimeIndex；`_iter_time_groups` 回傳的 group labels 必須是 `raw_data.index` labels，不能是 timestamp 值本身。

2. [BLOCKING] 信心度 High  
證據：`ic_config_schema.py:80 by_volatility: bool = True`；SPEC Task 2.3 若選 fail-closed「by_volatility=True 時 raise」。  
會怎麼失敗：default config 目前就是 `True`。Phase 1 修完 GroupedConfig 後，如果 Task 2.3 直接 fail-closed，任何預設 grouped run 都會從原本 AttributeError 變成 by_volatility unsupported，仍不可用。  
修法：我建議選 b fail-closed，但必須同時把預設改為 `False` 或做 config migration/override，並加測「預設 config 不因未顯式要求 volatility 而失敗；顯式 by_volatility=True 才 raise」。

3. [BLOCKING] 信心度 High  
證據：frontend store 預設 `featureFilter.max_features: 30`（`icAnalysisStore.ts:182-187`）；`useICAnalysis.ts:156-176` 只要 `max_features > 0` 就送 `feature_filter`。SPEC Task 3.2 要讓 max_features 真生效。  
會怎麼失敗：一落地就會把所有一般 IC analyze 預設截成 30 個特徵，即使使用者沒有明確套用預過濾。這違反 §C「不靜默截斷特徵」。metadata 可審計不足以抵消語義改變。  
修法：前端預設 `max_features` 應為 undefined，或 payload 增加明確 `filter_applied/user_applied`；後端只在顯式套用時截斷。測試要覆蓋「無顯式 filter → 全量」。

4. [MAJOR] 信心度 High  
證據：SPEC Task 3.2「按 features_df 既有欄位順序取前 N」。  
會怎麼失敗：確定性足夠，但語義不夠。欄位順序可能只是 feature factory/storage 產出順序，不代表重要性；max_features 會改 feature universe，尤其配合前端 default 30 會造成看似「前 30 個特徵」其實是任意生成順序。  
修法：Phase 0 若只止血，max_features 應命名/呈現為 deterministic cap，不要暗示 top/best。排序可用「顯式 include_features 順序 → artifact/metadata 穩定順序 → features_df 欄位順序」；不得用本次 label 算出的 IC 排序，避免 look-ahead。若要 top-N quality，需用已凍結的 prior training IC artifact，另立 Phase。

5. [MAJOR] 信心度 High  
證據：SPEC §G「grouped_ic... 各組 IC 值集合 = ... 值守恆，只是分組正確」。  
會怎麼失敗：這個 golden 只驗分組結果集合，可能漏掉 row-to-time 對齊錯誤、group labels 用 timestamp 值 `.loc` 失敗、或同值重排。timestamp 修錯後最危險的是 index alignment，不只是年份鍵。  
修法：golden 要加入每個 group 的 row index mask/hash、group sizes、feature/value/NaN-mask hash；並要求真實 `read_klines` 形狀 `RangeIndex + timestamp seconds` 打完整 `compute_grouped_ic`。

6. [MAJOR] 信心度 Med  
證據：SPEC §G「decay 回傳 dict... byte 級一致」與通過條件「abs≤1e-6 或 rel≤1e-4」。  
會怎麼失敗：「byte 級一致」和浮點容差是兩種 gate；如果只做 JSON byte diff，dict 順序/NaN 序列化會假 fail；如果只做容差，可能漏掉 feature order 或 NaN-mask 變化。  
修法：分層定義：feature key order hash、每 feature `ic_values` NaN-mask hash exact、finite floats `allclose`，scalar fields exact/typed。不要把 byte-level 當單一口號。

7. [MAJOR] 信心度 High  
證據：SPEC §A #4「service.py:967-969 僅 `metadata["feature_filter"]`=...」；實碼是 `_build_config_override` 把 `feature_filter` 放進 config override，非 metadata。  
會怎麼失敗：實作端可能去 metadata 錯位置找資料，或測錯 contract。根因仍成立：`ICConfig` 無欄位、momentum 無消費。  
修法：修正 SPEC 文字：API request → service config_override → `ICConfig` model_validate 目前丟棄/忽略未知欄位 → orchestrator 無消費。

8. [MAJOR] 信心度 Med  
證據：SPEC Task 4.3 只寫 longitudinal `analyzer.analyze` 改 `to_thread`；service cross-sectional 分支 `analyze_cross_sectional` 也是同步重計算（`ic_analysis_service.py:154-159`）。  
會怎麼失敗：cross-sectional 大批次仍會堵 event loop；Phase 0 UX 修完一半。  
修法：U-1 擴為兩條主計算路徑都用 `asyncio.to_thread`，或明確記 N/A 理由與測試範圍。

9. [MINOR] 信心度 High  
證據：SPEC Task 3.4「preview_limit 改名 + API 版本化」；我在 API/frontend 搜尋未找到 IC analyze request 的 `preview_limit` 欄位，只有 feature list/top-features/其他 domain limit。  
會怎麼失敗：實作端找不到目標，容易亂改 unrelated API。  
修法：補明確檔案/欄位/現名/新名；若不是 Phase 0 必需，移出本 SPEC。

## IC-BYVOL 建議：b fail-closed

理由：Phase 0 是止血與硬閘，不是新增 quant 分組功能。波動度分組需要定義收益/價格來源、lookback、分位數、min sample、NaN 行為、是否 rolling/PIT，現在補做很容易引入新的正確性風險。正確做法是：顯式 `by_volatility=True` 時 fail-closed 報「not supported in Phase 0」，但預設必須改成不觸發，否則預設 grouped analysis 仍不可用。

## 被當成事實的未驗證假設

- SPEC §A #2「bug 在真實路徑必觸發」：`read_klines` 的 RangeIndex、秒級 timestamp 是 fact-verified；但「會產出 1970 grouped 結果」不是完整 fact。實際 numeric branch 對 Series 會先回傳 Series，`_iter_time_groups` 可能先因 `.to_series()` 崩潰。
- SPEC §A #4「service 僅 metadata feature_filter」：事實錯位；實碼是 config_override，不是 metadata。
- SPEC §A #6「event loop 阻塞」：碼證支持同步計算在 async task 中直接執行，但 SPEC 沒附 heartbeat/並發實測輸出；屬於高可信推論，不是實跑 fact。
- SPEC Task 3.2「features_df 既有欄位順序」：可證 deterministic，但未證明是正確或使用者期望的 feature universe 語義。
- SPEC §G grouped 值守恆：未證明能捕捉 index alignment 與 row mask 回歸。

ASSUMPTIONS_VERIFIED: 已讀指定 SPEC/manifest/brief/analysis/template/code；只讀實測確認 HDF5 BTCUSDT/1h timestamp=1704067200 且 seconds=2024、ms=1970；純 pandas 驗證 Series timestamp branch 不是 DatetimeIndex。  
TESTS_RUN: `rg`/`nl`/`sed` 讀碼；`python -c` HDF5 只讀檢查 pass；一次直接 import ICEngine 因 read-only 觸發 numba cache locator RuntimeError，未作為程式行為證據。  
FAILURES_SEEN: here-doc 因 read-only 無法建 temp file，已改 `python -c`；ICEngine import 因 numba cache 在 read-only 下失敗。  
SCOPE_CHANGES: none，未改檔。  
NUMERIC_OR_SCHEMA_IMPACT: none，僅審查。  
HANDOFF_NOT_UPDATED: read-only sandbox，且根規範禁止覆寫 root HANDOFF。  
STATUS: DONE