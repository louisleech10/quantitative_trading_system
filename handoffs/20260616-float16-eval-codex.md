# CGSA L7_raw float16 vs float32 評估（Codex）

日期: 2026-06-16  
範圍: 讀取型技術評估；未改 production；未 commit。

## 結論

建議短期維持現行「per-column float16 with float32 fallback」寫盤，不建議立刻全面改 float32。理由是現行 gate 已把 overflow/underflow/相對誤差超標欄位退回 float32，且本機現有 manifest 顯示 float32 fallback 確實大量觸發；全面 float32 會把 L7_raw 未壓縮數值 payload 約放大 1.7x-2x，直接衝擊 8GB/disk headroom。  

但要把這個決策明確標成「有界 lossy storage」，不能再用 CGSA raw 與 frame path 做 value-exact parity。若後續要提高研究可重現性，優先做 A/B 量化影響測試；若要改 code，較合理的是新增可配置 dtype policy 或對 sensitive consumers 讀取後統一轉 float32 運算，而不是直接全域改 float32 寫盤。

## 1. 哪裡決定 float16

主路徑是 `momentum/FeatureEngineering/feature_storage.py`:

- `write_raw_from_registry_stream()` 的 `_write_group()` 先把 CGSA group data 經 `_coerce_persistence_array()` 轉成 float32，再呼叫 `_select_parquet_storage_columns()` 寫 parquet。
- `_select_parquet_storage_columns()` 對每一欄呼叫 `_select_parquet_storage_array()`，所以是 per-column 判斷，不是整個 raw artifact 一刀切。
- `FLOAT16_MAX_REL_ERROR = 1e-3`，`FLOAT16_MAX_ABS_ERROR = 1e-12`。
- 判斷流程: source 先 float32；嘗試 `astype(np.float16)`；roundtrip 回 float32 後若 finite 值變 non-finite，或任一 finite 值 `abs_error > max(1e-12, abs(source) * 1e-3)`，該欄 fallback float32；否則存 float16。
- manifest 會記錄 `dtype_summary`、每個 part 的 `dtype_counts` 與 `float32_columns`。

補充: frame path / HDF5 factory output 另一路在 `save_factory_output()` 將 features array 存 float32；processed artifact 則有另一套 int16/uint16 codec，只在 `artifact_kind == "processed"` 且 codec flag 開啟時使用，不是這次 L7_raw float16 的主因。

## 2. 動機與代價

動機主要是磁碟與峰值資源:

- float16 每 cell 2 bytes，float32 每 cell 4 bytes；disk precheck 也用 float16 final bytes 估算 L7_raw final size，另用 float32 估 max in-flight part。
- 這符合前期 CGSA/L7_raw 為 8GB tier、巨寬特徵矩陣做的 disk-safe streaming 設計。
- 本機現有 manifest 抽樣:
  - `BTCUSDT/12h`: 209,122 欄；201,220 float16、7,902 float32；raw parquet 約 0.64 GiB；未壓縮 cell 估算 mixed 0.69 GiB vs 全 float32 1.32 GiB，省約 48%。
  - `ETHUSDT/1h`: 437,819 欄；354,838 float16、82,981 float32；raw parquet 約 7.55 GiB；未壓縮 cell 估算 mixed 19.74 GiB vs 全 float32 33.19 GiB，省約 41%。
  - `ETHUSDT/12h`: 3,471 欄；2,842 float16、629 float32；省約 41%。

精度代價:

- 對尺度約 1 的 ratio/normalized 特徵，`1e-3` relative gate 允許最大約 0.001 絕對誤差；#2 調查看到 max abs diff 約 0.0009，正好是現行門檻允許的典型 float16 量化，不是 bug。
- `FLOAT16_MAX_ABS_ERROR=1e-12` 幾乎只保護接近 0 的值；一般尺度下主要由 `1e-3` relative gate 控制。
- 對大尺度 price/volume 類欄位，若 float16 overflow 或量化誤差超門檻會 fallback float32；本機 manifest 的 fallback 清單包含不少 volume、trend、rolling max/mean/range 等欄位，證明這條保護有實際生效。

## 3. 下游吃 raw 還是 processed

已確認:

- IC Gatekeeper 的 `compute_ic_from_l7_raw()` 讀 `artifact_kind="raw"` manifest，逐 group `pd.read_parquet()` 後直接計算 IC，所以 raw 存儲精度會進 IC 選特徵。預設 method 在程式中是 rank-oriented Spearman path；Spearman 對 monotonic rounding 通常較鈍，但 tie/邊界特徵仍可能受影響。
- IC-first pipeline: 先寫 raw，IC gate 讀 raw，選中後再 `load_columns_v2(..., artifact_kind="raw")` 取 selected raw 做 post-IC transform，最後寫 processed；預設還可能 cleanup raw。
- `FeatureLibrary.load_for_training()` / `load_multi(... for_training=True)` 優先讀 raw parquet，不是 processed。`xgboost_batch_service` 會先嘗試 FeatureLibrary，因此 XGBoost/LightGBM 批次訓練在有 library cache 時會吃 raw parquet 值。
- 舊 `case_id` / HDF5 路徑仍是 `load_features_from_hdf5()`，factory output 寫入時轉 float32。
- Strategy backtest objective 不直接讀 L7_raw；它吃 `predicted_proba`、prices、ATR。float16 的影響若存在，是經 IC/ML 模型輸出間接傳導，不是回測引擎直接用 raw feature。

影響判斷:

- IC rank/Spearman: 多數情況影響小，但接近 IC 閾值的 feature 可能 pass/fail flip。這需要 A/B 實測，不能靠直覺保證。
- XGB/LGBM: 樹模型主要依排序/分裂閾值，`~1e-3` 對多數連續因子未必實質；但大量 near-tie、低方差、threshold-like feature 可能改 split。訓練前轉 float32只能避免 float16 dtype 運算，無法恢復已量化資訊。
- 線性/NN/距離類模型: 對 level noise 較敏感，raw float16 更不理想。
- 回測真實性: 間接風險，重點在模型信號是否被量化改變；回測本身不應因此改 prices/returns。

## 4. 量化最佳實務

float16 存 feature 可以接受，但條件很窄:

- 適合: 冷存、超寬 feature store、下游以 rank/分箱/樹模型為主，且 manifest 清楚披露 dtype 與誤差門檻。
- 不適合: 用於 golden value exact、Pearson/線性模型的嚴格研究 artifact、或要比較不同 execution path 的 bit/value parity。
- ratio/normalized 特徵尺度約 1 時，`1e-3` relative error 不是「很小到可忽略」的數值工程事實；它是可接受上限，應用層要知道這是 lossy storage。

我同意 Claude 自產觀點的一半: ratio/normalized 特徵相對風險確實高於 price-scale 特徵，因為 price-scale 欄更容易被 fallback float32 或其 signal tolerance 相對大。需要修正的是「若下游吃 raw 風險較高」這句要分 consumer: Spearman IC/樹模型通常中低風險，Pearson/線性/NN/threshold 邊界才是高風險。

## 5. 建議方案

推薦: 維持現行條件式 float16/fallback float32，但把風險顯性化並補 A/B 驗證。

具體建議:

1. 不立刻全面改 float32 寫盤。這會顯著放大 L7_raw，且不保證解決 Batch2D T4 的所有差異，因為還有 index dtype、raw/frame topology、dead-drop 等既有結構差異。
2. 在後續 ticket 補「float16 vs float32 A/B」: 對同一 symbol/tf/config 以同一 raw source 寫兩份 artifact，量測 Spearman/Pearson IC top-k overlap、IC threshold flip count、XGB/LGBM AUC/feature importance drift、model proba drift、backtest metric drift。這是決定是否改 float32 的必要證據。
3. 若 A/B 顯示 IC/ML 邊界翻轉可忽略，維持現行 gate，並在文件/manifest 補明確 storage policy: raw parquet 允許 `rtol<=1e-3` lossy quantization，value-exact parity 不適用。
4. 若 A/B 顯示敏感，優先考慮可配置 dtype policy，例如 `raw_storage_dtype_policy={auto,float32}` 或對特定 layer/category/feature family 強制 float32。比「大尺度 float32、小尺度 float16」更合理的是「敏感語義 float32」: ratio/normalized/low-variance/IC-boundary candidates 可提高精度，大尺度且 gate-safe 欄位可仍 float16。
5. training strict reader 可統一輸出 float32 dtype，降低下游 library 差異，但這只能避免 float16 dtype 進模型，不會消除已落盤量化誤差；不要把它當作替代 float32 storage 的完整修復。

不建議:

- 為了通過 parity 測試調大 tolerance 或放寬斷言。這是把 storage policy 混成假綠。
- 靜默把全域改 float32。這改變輸出大小與 cache/schema 行為，需 SPEC、tier disk/RAM 驗證與使用者明確批准。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md/CLAUDE.md；已核對 feature_storage.py float16 gate、L7_raw stream 寫盤、FeatureReader/FeatureLibrary/IC/XGBoost/backtest 消費路徑；已只讀抽樣 data_cache/features 3 份 manifest 的 dtype_summary 與大小估算。
TESTS_RUN: 讀取型未跑 pytest；執行只讀命令: rg/nl/jq/find/du/git status；未生成或修改 data_cache。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增指定 handoff 報告，未改 production，未 commit。
NUMERIC_OR_SCHEMA_IMPACT: none；本報告不改 dtype/schema/輸出大小。
STATUS: DONE — 建議維持現行 auto float16 + float32 fallback，不立即全域改 float32；另開 A/B 驗證與可配置 dtype policy，若證實 IC/ML drift 才針對敏感 feature family 或 strict artifact 改 float32。
