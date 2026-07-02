# P1-FF-5 / P1-FF-7 測試設計 — Codex 修訂版

來源: `handoffs/20260702-FF-P1-57-DESIGN-CLAUDE.md`、`handoffs/20260627-FF-AUDIT-RECONCILE.md` 第 5/7 項。
讀碼範圍: `FeatureFactory.generate_features/_generate_features_impl/run_multi_symbol/_worker_entry`、CGSA workdir/registry、L5 reference cache、d-star cache、TA-Lib wrapper、Polars/L3 Numba 路徑、現有 atomic differential 與 multi-symbol 測試。

## 0. 對 Claude 版的主要挑戰

1. **FF-5 三跑全鏈成本過高且訊號太鈍**: only-A / [A,B] / [B,A] 都跑全鏈會把設計變成 1.5h+ 慢測；失敗時也難定位是 feature value、CGSA resume、d-star、L5 reference、L7 parquet 還是 batch checkpoint。應拆成快測牙齒 + 中測工件隔離 + 慢測真 run MR。
2. **FF-5 威脅面漏掉實際狀態**: `FeatureFactory` 實例含 `_current_symbol/_current_timeframe/_current_config_hash/_current_raw_data/_reference_data_cache/_cgsa_registry`；`_generate_features_impl` 會重設大部分 current/cgsa 狀態，但不清 `_reference_data_cache`。L5 cache key 是 `(reference_symbol, timeframe)`，run_multi_symbol 又把 reference data 透過 IPC 注入 worker cache。只比 A 最終 parquet 會漏掉 reference-symbol 錯 key、cache stale、resume gate 與同一 factory 連跑污染。
3. **d-star 不應 byte compare 整份 JSON**: v3 key 是 `d_star_{symbol}_{timeframe}_{fracdiff_hash}.json`，entry 允許 per-column value alias，`computed_at`/GC 也會造成非語義差異。應比有效 `d_star` map、metadata isolation fields、path token 與 cross-context miss。
4. **「工件不得出現 B symbol 字串」太粗**: manifest/checkpoint 可以合法記錄 batch symbols；真正要禁止的是 A 的 run dir、CGSA group/shard path、d-star payload metadata、L7 artifact metadata/columns/value 來源被 B 污染。
5. **FF-7 不能靠「B1 產物清單 diff」**: 現有已有 registry coverage 與抽樣 differential，但抽樣不等於全 registry correctness。設計應落在可執行矩陣: 全 registry input semantics byte equality、代表性 output direct-call differential、adapter-computed price_transform policy、MAVP special case、advanced hand-coded engines。
6. **路徑證據不能用 log capture 當主證據**: Polars/Numba 路徑可 silent fallback。應用 monkeypatch sentinel/counter 包住被選中的函式，並在 fallback 被允許/禁止兩種 mode 下分別驗證。

## 1. P1-FF-5 修訂設計: 跨 symbol 值隔離 MR

### 威脅模型

- A 的 feature value / NaN mask / columns / row index 因 B 存在或順序改變。
- A 的 CGSA workdir、registry group、shard、L7 run dir、lock、manifest 與 B 共用或覆寫。
- L5 reference cache 使用錯 symbol/timeframe key，或同一 `FeatureFactory` 連跑後把上一個 symbol 的 raw/reference 狀態帶入下一個 symbol。
- d-star cache path 或 payload metadata 缺 symbol/timeframe isolation；同值 alias 合法，但外來 context 不得命中。
- API batch 強制序列不代表底層 `run_multi_symbol()` 多 worker 安全。

### 測試分層

**FF5-fast: path/cache key 單元牙齒，秒級**

- `features_run_dir(root, A, tf, hash) != features_run_dir(root, B, tf, hash)`；path parents 不互含。
- `cgsa_work_dir(root, A, tf, hash) != cgsa_work_dir(root, B, tf, hash)`；patch `safe_token` 或 `cgsa_work_dir` 去掉 symbol 時必紅。
- `DStarCache._build_path(tmp, ctx(A,tf), same_frac_hash) != ...ctx(B,tf)`；patch `_build_path` 去掉 symbol 或 timeframe 時必紅。
- `ColumnGroupRegistry` same `group_id` / same values shape 在兩個 per-symbol workdir 讀回不同值，延伸現有 shard isolation，額外斷言 `manifest.context.symbol` 或 workdir token。

**FF5-mid: 同一 factory 連跑/狀態污染，分鐘級**

- 用同一個 `FeatureFactory` instance，真 kline 短窗、minimal config，順序跑 `A -> B -> A2`，`force_regenerate=True`，`FFACT_CGSA_WORK_DIR` 指到 run-specific tmp 根但每次用 production path helper 形成 symbol/tf/hash leaf。
- 斷言 A 與 A2 的 selected representative artifacts 等值: row index、columns、NaN mask、抽樣 value hash、feature count、layer_counts、L7 manifest artifact schema hash。
- 開啟 L5 cross_sectional，reference_symbol 固定第三方 R；另跑 B 時不得改變 A2 的 L5 `cs_*` 值。探針: monkeypatch `_reference_data_cache` lookup 或 `_worker_entry` IPC ref_symbol key 使用錯 symbol，`cs_*` hash 必紅。

**FF5-slow: 真 run MR，排在 P0 mutation run 後，requires_kline**

- A=BTCUSDT, B=ETHUSDT 或從 `data_cache/feature_klines/kline_cache.h5` 選兩個具備 1h/12h 的 symbols；窗長沿 B2 600 bars 或更小但必覆蓋 L3/L4/L6.5 warmup。
- 跑兩次即可作主驗收: `only A` vs `[B,A]`。第三跑 `[A,B]` 只保留為 nightly/diagnostic，因 two-run 已覆蓋「B 存在 + B precedes A + same batch path」。若懷疑 order-specific append/overwrite，再加第三跑。
- 對 A 比:
  - L7 raw/processed selected columns、row_index、NaN mask、finite value allclose；float32/float16 用現有 L7 caveat，不引入新容忍。
  - manifest: run_status/quality_status、artifact row_count、feature_count、schema hash、group ids、parquet part mapping 相同；created_at/path 絕對前綴可排除。
  - d-star: `read_d_star_json` 的有效 map 相同；payload `symbol/timeframe/row_count/time_range/source_data_version` 指向 A；path basename 含 A/tf。
  - CGSA: A run 的 `manifest.context.symbol`、workdir、shard parents 只屬 A；group columns 不含 B symbol token。

### FF5 mutation probes

- M5.1 `cgsa_work_dir`/`features_run_dir` 去掉 symbol: path/key 單元必紅。
- M5.2 `DStarCache._build_path` 去掉 symbol 或 `_payload_matches` 忽略 `symbol`: d-star isolation 必紅。
- M5.3 `_worker_entry` 注入 reference IPC 時把 key 固定 `"BTCUSDT"` 或用 worker symbol: L5 `cs_*` value MR 必紅。
- M5.4 同一 factory 連跑時 monkeypatch `_generate_features_impl` 不重設 `_current_raw_data` 或 `_cgsa_registry`: mid test 必紅。

## 2. P1-FF-7 修訂設計: wrapper / 多路徑 correctness

### 威脅模型

- TA-Lib wrapper registry/input_type/source/param/output naming 錯，底層公式正確也會全錯。
- 現有抽樣 differential 只覆蓋 15 個代表指標；全 registry input semantics 有覆蓋，但 output correctness 未全覆蓋。
- Polars path default-on，pandas fallback 仍存在；CGSA path 中 Polars result 用於主 output，但 per-category persist 仍調 pandas `compute_category`，可能 result 與 persisted groups 分歧。
- L3 streaming + Numba multi-window/single-window + pandas fallback 三路徑可能數值、NaN mask、低基數 skew/kurt gate 或 persist_callback 行為不一致。
- L6.5 causal winsor/rank/zscore 已有 P0 測試，本項只補「路徑證據 + 等值矩陣」，不重跑全鏈。

### V7.1 TA-Lib wrapper

- 保留並加強現有:
  - `test_registry_coverage_excludes_adapter_and_mavp`: 每個 non-adapter/non-MAVP registry name 必須在獨立 `TALIB_INPUT_SEMANTICS`。
  - `test_prepare_inputs_byte_equal_to_semantics_table`: 從抽樣改成全 registry parameterized；CDL/HL/HLC/HLCV/OHLC/close_volume 每類至少全覆蓋 input arrays byte equality。
  - `test_wrapper_matches_talib_direct`: 保留代表性 output differential；新增未覆蓋類別代表: `PLUS_DI/MINUS_DM/AROON/MIDPRICE/MFI/SAREXT/VAR/TSF/CDL*` 中各抽 1-2 個，避免只測現有 15 個。
- Price transform 是 adapter-computed，`TALibWrapper.compute()` 回空 DF 是 policy；另對 adapter 層的 AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE 補 direct formula differential。
- MAVP 單獨測 periods array 長度、params pop 不污染 column naming。

### V7.2 L2 Polars vs pandas / persisted groups

- 小型真 kline slice + synthetic pathological columns（含 NaN、inf、近零 denominator、constant/binary）組成 deterministic input。
- 強制 `FFACT_USE_POLARS=0` 跑 `_layer2_derived_pandas`，強制 `FFACT_USE_POLARS=1` 且 monkeypatch `polars_enabled` return True 跑 `_layer2_derived_polars`。
- 比較 common columns: column order set、NaN mask、finite values allclose；ratio/distance/momentum 近零 denominator 應同為 NaN 非 inf。
- CGSA on 時，額外載入 `_persist_layer2_category_group` 產生的 registry groups，與 Polars主 result 同 category columns 對齊比較，抓「主 output Polars、persisted pandas」分歧。
- 路徑證據: monkeypatch `DerivedOperatorEngine.compute_all_polars` sentinel counter；若 `FFACT_USE_POLARS=1` 且 polars installed，counter 必增。另 monkeypatch pandas `compute_all` raise sentinel，證明 Polars 主路徑不 silent fallback。

### V7.3 L3 Numba streaming / pandas fallback / persist callback

- 對 `RollingAggregator.compute_all()` 建三路徑:
  - `FFACT_L3_STREAMING=1, FFACT_USE_NUMBA_ROLLING=1, FFACT_L3_MULTI_WINDOW=1`
  - `FFACT_L3_STREAMING=1, FFACT_USE_NUMBA_ROLLING=1, FFACT_L3_MULTI_WINDOW=0`
  - `FFACT_L3_STREAMING=1, FFACT_USE_NUMBA_ROLLING=0`
- 小矩陣 80-200 rows × 4-8 columns，windows 覆蓋 5/13/21，aggregators 覆蓋 mean/std/min/max/range/zscore/rank/slope/skew/kurt。
- 比較 common output columns、NaN mask、finite values；pandas fallback 作 oracle。高階 moment 對低基數欄應一致被 gate 掉。
- persist_callback path: 用收集器代替 CGSA，斷言 callback 收到的 chunk concat 後等於 returned in-memory output 或等於 persisted offload contract；若 multi-window numba 支援 callback，counter 必增。若 fallback 不支援 callback，測試要明確 fail 或標 known contract，不可只看 output。
- 路徑證據: monkeypatch `fused_rolling_stats_multi_window` / `fused_rolling_stats` / pandas rolling fallback sentinel；對應 env 下只有目標 sentinel 增。

### V7.4 L7 codec / float16 明示

- Claude 版說 float16，但目前 L7 有 float32 fallback、rank uint16、zscore int16、parquet codec與部分測試允許 float16 roundtrip。設計應先讀 manifest `l7_encoding_registry`/`float32_columns`，不要硬假設所有 lossy 都是 float16。
- 測試:
  - 寫入小 registry group，讀回 parquet/FeatureReader 後與 source float32 比；若 encoded integer codec，decode 後誤差符合 codec 定義；若 float16，沿既有 `atol=1e-2` caveat 且必在 manifest 明示。
  - 若超出 int codec lossless gate，應 fallback float32，manifest `float32_fallback_group_count` 或 `float32_columns` 可見。

### FF7 mutation probes

- M7.1 刪/改 `TALibWrapper._INPUT_TYPE_MAP["hlc"]` 的 ATR 或 STOCH: 全 registry input semantics 必紅。
- M7.2 wrapper 將 RSI close 改 open: output differential 必紅。
- M7.3 `polars_enabled=True` 但 `_layer2_derived_polars` 偷走 pandas `compute_all`: path counter 必紅。
- M7.4 `RollingAggregator` env 宣稱 numba multi-window 但跳 pandas fallback: sentinel 必紅。
- M7.5 L7 codec metadata 移除 lossy/fallback registry: V7.4 必紅。

## 3. 慢測成本與排程

- PR gate: FF5-fast + FF7.1 selected/full input semantics + FF7.2 small matrix + FF7.3 small matrix，目標 < 5-8 分鐘。
- requires_kline medium: FF5-mid 同 factory A/B/A2 + L5 reference cache，目標 < 20 分鐘。
- nightly/receipt slow: FF5-slow two-run `[B,A]` MR，排在 P0-FF-3 mutation run 與 B2 回歸後；第三跑 `[A,B]` 僅 diagnostic。
- 每個 mutation probe 必有「正向測試在 raises 外」與 receipt；不允許用 smoke 替代慢測 claim。

## 4. 回答 Claude §D 三問

1. **V5.1 可否三跑縮兩跑?** 可以，主驗收縮成 `only A` vs `[B,A]`。這同時覆蓋 B 存在、B 先跑、同批次/同環境污染。`[A,B]` 對「A 先跑後 B 覆寫 A artifact」有價值，但更像 diagnostic/nightly；主 gate 不應為它付 50% 額外成本。
2. **V7.2 路徑證據機制?** 首選 monkeypatch sentinel/counter 包目標函式與反路徑 raise sentinel。內部 counter 次之。log capture 只當輔助，不能作主證據，因為 fallback/錯路徑也能輸出相同 log 或被 logger level 吃掉。
3. **漏的跨 symbol 污染面?** L5 `_reference_data_cache` 與 IPC ref key、同一 factory instance current state、CGSA resume/workdir、RunLease/feature run dir、d-star path/payload/value alias、batch checkpoint completed/queued/resume、L7 manifest parquet path map、環境變數 `FFACT_CGSA_WORK_DIR` 若設成單一固定目錄造成多 symbol 共用、Layer metrics/child metrics JSONL 以 symbol/tf 聚合時的錯配。

## 5. 建議交付檔案

- `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`
- `tests/feature_engineering/test_ff_wrapper_path_correctness.py`
- 可選 helper: `tests/feature_engineering/ff_artifact_compare_helpers.py`

## 6. 驗收命令草案

- 快測: `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py tests/feature_engineering/test_ff_wrapper_path_correctness.py -q`
- 真 kline medium: `pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py -m requires_kline -q --tb=short`
- 慢測 receipt: `python scripts/run_with_receipt.py --task-id FF-P1-57 -- pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py -m requires_kline -q --tb=short`

ASSUMPTIONS_VERIFIED: read HANDOFF.md, CLAUDE.md, Claude P1-57 design, 20260627 reconcile items 5/7; inspected FeatureFactory state reset/run_multi_symbol, CGSA workdir, d-star v3 path/payload, TA-Lib wrapper/input semantics tests, Polars and L3 Numba routing, existing multi-symbol tests.
TESTS_RUN: read/design only; no pytest run because task requested test-design committee output, not implementation.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; wrote only this handoff.
NUMERIC_OR_SCHEMA_IMPACT: none; no production/test code changed.
STATUS: DONE
