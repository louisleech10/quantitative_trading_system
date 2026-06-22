# Stateful Param Audit — Codex (read-only)

| 類別 | 層/計算 | 結論 | 證據 |
|---|---|---|---|
| A | L6.5 fracdiff d* | 須隨 run/model 留存；前500/校準窗搜 d*，換窗會漂 | `feature_preprocessor.py:175-187`, `3032-3050`, `3687-3772`; cache `:2950-2979`, `3284-3297` |
| A | L6.5 ADF integer differencing | 啟用時須留存每欄 chosen_diff；現況未見持久化，只即時計算套用 | `feature_config.py:174-180`; `feature_preprocessor.py:3301-3360` |
| D | L6.5 gaussian_normalize | 安全；不是 QuantileTransformer fit，而是 rolling rank + `ndtri` | `feature_config.py:218-221`; `feature_preprocessor.py:3434-3468`, `3470-3505`; no `QuantileTransformer` hit |
| D | L6.5 winsor/rank/zscore | 安全；rolling window/rolling quantile/rolling rank/rolling mean-std | `feature_preprocessor.py:2675-2733`, `3371-3410`, `3507-3555`; `_numba_transforms.py:312-333` |
| A | L2 near-zero denominator guard | 漏項：全欄 median(|denom|) 校準 threshold，影響 NaN/ratio 分布，須留存或改 causal | `numeric_guards.py:31-58`; pandas uses `derived_operators.py:394,406,415,580`; polars `polars_adapter.py:41-61,348-352` |
| A/schema | L3/L7 dead/drop gates | 須留存 schema/保留欄；全 run `nunique/std/nan_rate/valid_count` 決定欄是否存在 | L3 `rolling_aggregator.py:773-827,830-865`; L7 `dead_feature_filter.py:44-92`; apply `feature_factory.py:2691-2728,3195-3221` |
| A/schema | L3 skew/kurt low-cardinality skip | 須留存候選/輸出 schema；全欄 `nunique` 決定 skew/kurt 是否生成 | `rolling_aggregator.py:95-130`, `250-268`, `518-535`, `773-789` |
| B | TA-Lib OBV/AD/ADOSC | 路徑依賴；需一致 reset/burn-in 或帶 state | TA-Lib volume registry `talib_wrapper.py:101-102,204-206`; warmup notes `warmup_table.yaml:367-381` |
| D | custom VWAP | Claude 初版需修正：此 repo 自寫 VWAP 是 rolling(20)，非 cumulative | `volume_indicators.py:199-208`; yaml note `warmup_table.yaml:382-386` 只描述 cumulative case |
| D | entropy R/S cumsum | 安全；`cumsum` 在 rolling(window).apply 的窗口內，不是 from-start | rolling calls `entropy_indicators.py:122-168`; R/S `:240-250` |
| C | L5 cross-sectional | 需同一 reference symbol 同期資料；不是 fit，但 universe/reference 依賴 | `feature_factory.py:1770-1903`; `relative_strength.py:16-29` |
| D | L4 lag | 安全；純 `shift(lag)`，lag list 來自 config/固定生成 | `lag_processor.py:40-65`, `90-91`, `158-166` |
| D | native/multi-TF alignment | 安全；deterministic `searchsorted`/idx_map，無 fit；需保存/重建同版本 alignment | `tf_aligner.py:111-171`; `multi_tf_generator.py:249-279`; hash includes version `feature_factory.py:3699-3705` |
| D | L6 meta | 安全；逐列 mean/std/rank/sign、固定閾值、時間拆解；未見 fit | `consensus_features.py:35-108`; `interaction_features.py:29-62`; `time_features.py:44-58` |
| D/metadata | L7 validation quality gates | 不改 feature values；threshold 只寫 metadata/status | `feature_validator.py:145-178,189-214`; `feature_factory.py:3035-3055,3596-3615,3688-3690` |
| D/labels | labels | 非特徵 serving；`winsorized_return` 用 full-sample quantile，若作 label 研究需記錄但不上線 feature | `label_generator.py:71-80` |

結論：除已知 d* 外，新增高風險漏項是 L2 `safe_denominator` 全樣本 median threshold，以及所有全 run schema/drop 決策。Gaussian 不是 fitted。ADF order 啟用時必留存。OBV/AD/ADOSC 是 B；自寫 VWAP 是 rolling 安全。
