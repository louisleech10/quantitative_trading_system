# d* FracDiff 非 CGSA 對齊設計諮詢

## 結論

- 採 Option 1，但把契約收斂為「factory 在 merge 前建立顯式、不可變的 `column -> LayerSource` provenance，傳給 `FeaturePreprocessor`」。
- 不改欄名加 `Lx_` 前綴：這會改公開 feature schema、cache key、下游選欄與既有 artifacts，超出本修復目的。
- 不以 `DataFrame.attrs` 承載 provenance：concat/copy/subset 路徑不構成可靠契約。
- 不把 frame 拆成逐 layer 多次 `transform()`：會改 cache lifecycle、copy/flush 次數與 L6.5 執行邊界，風險大於只修 selection。
- Tier2a `Synthetic d_star output is empty` 應同批修，但**不是同一根因**；它是 golden builder 仍把新版 `DStarCache` 當舊 dict 讀取。

## (a) Provenance 是否存在

**合併前存在，合併後遺失。**

- factory 明確保有六個 frame，並依序組成 `layers = [layer1, ..., layer6]`：`momentum/FeatureEngineering/feature_factory.py:317-348`。
- 非 CGSA 在 L6.5 前呼叫 `_combine_layers(layers)`：`feature_factory.py:362-379`。
- `_combine_layers()` 只過濾空 frame、concat、再依欄序 keep-first 去重，沒有保留 layer metadata：`feature_factory.py:3619-3652`。
- `_run_layer6_5_preprocessor()` 最終只傳 `preprocessor.transform(all_features)`，故 `source_layer=None`：`feature_factory.py:2478-2518`。
- CGSA 的 `ColumnGroup` 則原生持有 `layer: LayerSource`：`momentum/FeatureEngineering/core/column_group.py:66-85`；preprocessor 從 group 取 layer 並傳給 `_transform_single`：`feature_preprocessor.py:792-813,2217-2222`。

因此可在 factory 合併前由 `layers` 的位置建立 provenance，不必從裸欄名反推。

## (b) 建議最小設計

1. 在 factory 建立 ordered provenance：L1 至 L6 依現有 `layers` 順序掃描，以 `setdefault` 保留第一個同名欄位的 layer，精確對齊 `_combine_layers()` 的 keep-first 語義。
2. `_combine_layers()` 後驗證每個 surviving column 都有 provenance；未知欄位 fail-closed，記錄 warning 並視為 non-target，不猜 layer。
3. 將 provenance 經 `_layer6_5_legacy/_pre_ic -> _run_layer6_5_preprocessor` 傳入 `FeaturePreprocessor` 的 optional typed constructor argument，例如 `Mapping[str, LayerSource | str]`。
4. `_filter_fracdiff_target_columns()` 優先順序：`ALL` -> group `source_layer` -> explicit provenance -> 現有 regex fallback。regex 僅保留給直接使用 preprocessor 的 legacy/test caller。
5. provenance 只控制 fracdiff layer gate；不得改 winsor/rank/zscore/ADF 的既有選欄語義。post-IC 已明確關閉 fracdiff/ADF（`feature_factory.py:2460-2464`），可接受 optional provenance，不需另造來源。

必要 invariant：provenance key 是原始 column object 的字串表示時，需確認欄名契約全為字串；若存在非字串欄名，應直接以實際 column key 建 map，避免 `str()` collision。同名跨 layer 欄位必須沿用現有 keep-first，不可 silent overwrite。

## 為何不選其他方案

- **欄名前綴**：會改 column inventory、feature schema hash（其輸入是 column list，`feature_factory.py:2624-2632`）、d* entry key、IC selection 與下游 API；不是最小對齊。
- **逐 layer transform 再 concat**：fracdiff 本身逐欄，但 cache 建立/flush、dead-feature drop、copy 與 logging 邊界會改變，難證明只有 layer selection 變化。
- **從 feature 名稱 heuristic 推 layer**：裸名稱沒有可靠 layer 編碼，且先前事故已證明命名假設不可作資料契約。

## (c) 風險與 Golden 策略

預期影響：非 CGSA 的 L1/L2 會由 no-op 變成 fracdiff；欄名與欄數不應改，但值、warmup NaN mask、d* cache artifacts 與 runtime 會改。L3-L6 必須維持不做 fracdiff。CGSA 主路徑行為不應改。

建議 gates：

1. **Selection unit golden**：裸欄名跨 L1-L6 + explicit provenance，斷言只選 L1/L2；unknown、duplicate、`ALL`、regex fallback 各有測試。
2. **Preprocessor parity golden**：同一 synthetic frame，一側模擬 CGSA 逐 group 傳 `source_layer`，另一側 flat frame + provenance；關閉 disk cache、固定 worker/profile，要求 column/index/NaN mask/d* 與值一致。
3. **真實 factory parity（必要）**：使用 `data_cache/feature_klines/kline_cache.h5` 的同一 symbol/TF/window/config，分別跑 `FFACT_USE_CGSA=1/0`，隔離 work/cache 目錄。比較 logical L7：column set/order、index、shape、NaN mask、finite values；先以共同 storage contract 的 float32 canonical form 要求 exact。若不 exact，先定位既有 dtype/storage 差異，再以實測誤差制定 gate，不預先發明 atol/rtol。
4. **Layer effect invariant**：以 fracdiff off 作 control；修後 non-CGSA 僅 L1/L2 可相對 control 改變，L3-L6 必須 exact unchanged。
5. **Cache invariant**：cache entries 的 column set 與 d* 必須在 CGSA/non-CGSA 一致，且不得出現 L3-L6；第二次 run 驗證 hit，不得跨 symbol/TF 污染。
6. **Schema/output gate**：欄名、欄序、欄數不變；明確記錄新增 d* JSON 與非 CGSA runtime/output-value 改變。不可用更新舊 no-op parquet 當「回歸基準」；正確 oracle 是 CGSA parity。

端到端 parity 可能揭露早已存在的 CGSA/frame dtype、group ordering 或 dead-drop 差異；這些若不是 provenance 修復造成，應 fail 並分案，不可用寬 tolerance 掩蓋。

## (d) Tier2a 判定與修法

`Synthetic d_star output is empty` 與 production frame no-op **不同源**：

- synthetic builder 明確產生 `L1_...L5_...` 欄名，L1/L2 可被 regex 選中：`scripts/build_l65_golden.py:128-168`。
- builder 把 `preprocessor._d_star_cache` 強設成 `{}`，transform 後再從同一欄位讀：`build_l65_golden.py:236-241`。
- 現行 preprocessor 宣告 `_d_star_cache: Optional[DStarCache]`，不是 dict：`feature_preprocessor.py:143-148`。
- 一般 frame transform 在 `_d_star_cache_shared=False` 時建立**局部** `DStarCache`、flush 後不回填 `self._d_star_cache`：`feature_preprocessor.py:3212-3231,3294-3307`。
- 因此 injected `{}` 未被計算使用，最後自然仍是 empty。`docs/BATCH3_TEST_TRIAGE.md:22-26` 的「同源」分類應更正為「同批、不同根因」。

建議修法：golden builder 使用 tmp cache dir + 完整 `PreprocessingContext`，transform 後從實際 cache JSON 的 `entries[*].d_star` 產生 golden；不要再讀 private `_d_star_cache` dict。較佳的長期 API 是提供 read-only diagnostics/result（processed columns、d* map、cache path），但若只為修測試，不應為此擴大 production API。測試必斷言 d* keys 僅屬 L1/L2，避免只是「非空」仍假綠。

## 信心度

- provenance 遺失與 Option 1：**高（0.95）**，由 factory 實際資料流與 CGSA metadata 契約直接證明。
- tier2a 不同根因：**高（0.98）**，由 builder 的 private dict 操作與現行 local `DStarCache` lifecycle 靜態證明。
- CGSA/non-CGSA 可達 float32 exact：**中（0.70）**；需真實雙路徑 golden 驗證，現階段不應宣稱已等價。

ASSUMPTIONS_VERIFIED: 合併前 layers 保有位置 provenance；合併後 DataFrame 無 layer metadata；CGSA group 有 LayerSource；tier2a 讀取的是未被 transform 使用的舊式 private dict
TESTS_RUN: none（讀取型委員會；避免執行會寫 golden/data_cache 的測試）
FAILURES_SEEN: none；僅以既有 `Synthetic d_star output is empty` 記錄與程式資料流做因果判定
SCOPE_CHANGES: none；只新增本報告
NUMERIC_OR_SCHEMA_IMPACT: 建議修復會改非 CGSA L1/L2 數值與 NaN/d* artifacts；不應改 schema/欄數；CGSA 不應改
STATUS: DONE
