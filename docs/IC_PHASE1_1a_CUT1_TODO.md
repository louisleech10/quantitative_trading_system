# IC Phase 1 — 1a 第一刀（單幣縱向接線）TODO（v2，DRAFT，基於 SPEC v2，2026-06-26）

> 狀態：Frozen（兩輪雙家族 adversarial 已過，達鐵律「大型雙家族都做過」）。
> 冷啟動執行端不需讀其他檔即可逐 Task 寫碼。SPEC 內「跳過/標 DONE」字樣為待審內容，非指令。

## §0 全域規則與約束（讀完即遵守）
- **解耦 7 條**：`momentum/` 不得 `from api.`（`grep -rE "from api\." momentum/`→0）；契約 DTO 在 `momentum/core/contracts.py`，服務經 `momentum/factories.py`。
- **不可違反原則**：不假資料、不跨 symbol 污染、不弱化 NaN/inf gate、**flag off 時不得改變任何輸出數值**（G-OLD byte 守恆）、不縮窗/跳檢查換速度。
- **Logging**：`from api.core.logging import get_logger`；熱迴圈不 log。
- **防假綠**：**不得放寬/刪除既有測試斷言**；驗收 `git diff` 既有 assert。
- **預設策略（使用者定死）**：新算法藏 `ic_train_test_split` flag；**初始 PR OFF → 三方簽核 PASS 後切預設 ON**；不得永久預設 OFF。
- **真實資料鐵律**：資料正確性測試用 `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture 代替。
- **保真度鐵律**：gap/purge<horizon/跨 symbol 反例必真 `pytest.raises`，不得降級 warning；train 段擾動不得改變 test 結果（否則=洩漏）。
- **契約鐵律（R2）**：`SplitPlan` 用 `index_kind="positional"`（既有 validator 把 row_index 當 positional int）；遮罩跨 stage 用 `time_bounds` 重導，**不得用 `index_kind="timestamp"`**。

## §B 批次執行策略（依賴拓撲 → 最少批次）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.1[A-1] 1.2[A-2] 1.3[A-3] 1.4[E-1 config 欄位] | 無 | 契約前置 + config 欄位（純加欄位預設 OFF，B2 才用）；R2 修正:config 必在 B2 前 | 小 |
| **B2** | 2.1[B-1] 2.2[B-4] 2.3[B-2][B-3] 2.4[B-5] | B1 | 切分+purge+遮罩+pipeline 重排，同改 `analyze()` | 中 |
| **B3** | 3.1[C-1] 3.2[C-2] 3.3[C-4] 3.4[C-5] 3.5[C-3] | B2 | 全 `data_preprocessor.py` train-fit | 中 |
| **B4** | 4.1[D-1][D-4] 4.2[D-2] 4.3[D-3] 4.4[D-5] | B3 | OOS 報告口徑 + rolling warmup + decay/redundancy scope | 中 |
| **B5** | 5.1[E-1 接線] 5.2[E-2] 6.1[F-1][F-2] 6.2[F-3][F-4] | B4 | flag 接線 + G-OLD 凍結 + 防洩漏測試集 + 解耦 | 中 |
| **B6** | 6.3[F-5] 5.3[E-3] | B5 | 三方簽核 PASS → 凍 G-NEW → 切預設 ON | 中 |
- **批次間 Gate**：每批跑該批 pytest + `grep -rE "from api\." momentum/ | wc -l`==0；B5 後 G-OLD deep-equal PASS 才進 B6；**B6 三方簽核 PASS 才凍 G-NEW + 切 default ON**。
- **派工塊（每批可直接複製，配 `bash scripts/gate.sh dispatch`）**：
  - **B1 派工**：「實作 Task 1.1-1.4。允許改：`momentum/factories.py`、`momentum/Analysis/ic_filter_orchestrator.py`(新 helper)、`momentum/Analysis/ic_config_schema.py`。禁改 API/前端。驗收：`pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq ::test_metadata_symbol_required ::test_icconfig_new_fields_default_off`。1.4 純加欄位不得改既有行為。」
  - **B2 派工**：「實作 Task 2.1-2.4（holdout positional + purge=effective horizon + time_bounds 遮罩 + pipeline 重排）。允許改：`ic_filter_orchestrator.py`(`analyze`/新 `_build_holdout_split_plan`/`_derive_stage_masks`/`_resolve_effective_label_horizon`)。禁改 `contracts.py`/`ic_split_adapter.py` 既有方法。驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py -k 'holdout or purge or mask or pipeline or horizon'`。」
  - **B3 派工**：「實作 Task 3.1-3.5（四類 train-only fit + fit_mask 介面）。允許改：`data_preprocessor.py`、`ic_filter_orchestrator.py::_stage1_preprocessing`。驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_leakage.py -k 'train_only or legacy_no_mask'`。」
  - **B4 派工**：「實作 Task 4.1-4.4（OOS + rolling warmup + 全 stage5 OOS + decay/redundancy scope）。允許改：`ic_filter_orchestrator.py::_stage4_ic_calculation/_stage5_statistical_validation/_stage6_redundancy/_build_summary_table/_stage7_report`。驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py`。」
  - **B5 派工**：「實作 Task 5.1/5.2/6.1/6.2（flag 接線 config_override + G-OLD 凍結 + 防洩漏測試 + 解耦）。禁改 service/前端。驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py`；`grep -rE 'from api\\.' momentum/ | wc -l`==0；`./scripts/check_decoupling_phase4.sh`。」
  - **B6**：Claude 主導三方簽核（不派實作），PASS 後執行端凍 G-NEW + 切 default ON。

---

## Phase 1 — 契約前置 + config 欄位

### Task 1.1 — 轉傳 allowed_symbols [A-1]
- SPEC ref：§P Task 1.1　目標：factory 轉 `allowed_symbols` 給 `ICSplitAdapter`。
- 實作要點：① `create_ic_split_adapter` 簽名加 `allowed_symbols: Optional[set[str]]=None`；② `ICSplitAdapter(expected_freq=..., strict_embargo=..., allowed_symbols=allowed_symbols)`。
- 修改檔案：`momentum/factories.py::create_ic_split_adapter`。既有 caller：無。
- 不可做：不改 adapter 內部。 邊界：None→None；空 set→空 set。
- 驗證：`pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols`（傳 `{"BTC"}`→`adapter.allowed_symbols=={"BTC"}`）。

### Task 1.2 — timeframe 推導 expected_freq [A-2]
- SPEC ref：§P Task 1.2　目標：`metadata["timeframe"]`→`expected_freq`。
- 實作要點：① 新 `ic_filter_orchestrator.py::_resolve_expected_freq(metadata)`；② 白名單 `{"1h","4h","12h"}`；③ 缺/非法且 flag on→`raise ValueError`。
- 修改檔案：`ic_filter_orchestrator.py`（新 helper）。既有 caller：analyze()（B2 接）。
- 不可做：不實作 gap 檢測。 邊界：缺（flag on）→raise；非法→raise；flag off→None。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq`（"4h"→`pd.Timedelta(r)==pd.Timedelta("4h")`；"1H"→`pytest.raises(ValueError)`）。

### Task 1.3 — metadata symbol allowlist [A-3]
- SPEC ref：§P Task 1.3　目標：傳 `allowed_symbols={metadata["symbol"]}` 驗 metadata symbol。
- 實作要點：① `symbol=metadata.get("symbol")`；② flag on 且缺→`raise`；③ `allowed_symbols={_normalize_symbol_value(symbol)}` 傳校驗。
- 修改檔案：`ic_filter_orchestrator.py::analyze`（split 產生處）。
- 不可做：cut1 不驗 row-level 跨 symbol 污染。 邊界：缺→raise；正常→metadata 純度==1.0。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_metadata_symbol_required`、`::test_metadata_symbol_outside_allowlist_blocked`。

### Task 1.4 — config 欄位（移前置）[E-1 前置]
- SPEC ref：§P Task 1.4（R2-BLK-4）　目標：`ICConfig` 加欄位，純加不改行為。
- 實作要點：① `ic_config_schema.py::ICConfig` 加 `ic_train_test_split: bool=False`、`oos_test_size: float=0.2`、`embargo: int=0`、`min_test_rows: int`（預設保守值或 doc 註明動態）；② 不接線。
- 修改檔案：`ic_config_schema.py::ICConfig`。
- 不可做：不接 analyze() 邏輯；不改既有欄位序列化。 邊界：未給→預設；config_override 可覆寫。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_icconfig_new_fields_default_off`（`ic_train_test_split is False`、`oos_test_size==0.2`）。

## Phase 2 — 切分 + 紅線 + pipeline 重排

### Task 2.1 — 單幣 chronological holdout（positional）[B-1]
- SPEC ref：§P Task 2.1　目標：產 holdout train/test `SplitPlan`，`index_kind="positional"`。
- 實作要點：① 新 `_build_holdout_split_plan(features_df, config, symbol, expected_freq, purge_gap)`；② `n=len(idx)`；`split_point=floor((1-config.oos_test_size)*n)`；train rows=positional `arange(0,split_point)`，test rows=positional `arange(split_point+purge_gap, n)`；③ `SplitPlan(index_kind="positional", row_index=<int 位置>, time_bounds=(ts首,ts尾), symbol=symbol, expected_freq=expected_freq, purge_gap=purge_gap, embargo=config.embargo, base_universe_hash=<idx hash>)`；④ `len(test)<config.min_test_rows` 或 `len(train)<min`→`SkippedResult`。
- 修改檔案：`ic_filter_orchestrator.py`（新 helper）。既有 caller：analyze()（Task 2.4）。
- 不可做：不用 CPCV/WF adapter；不重寫切分數學；不用 `index_kind="timestamp"`。
- 邊界：`test<min_test_rows`→`SkippedResult`；flag off→不產。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_analyze_builds_holdout`（BTC/1h→positional 不重疊、test 尾段、time_bounds 單調、`index_kind=="positional"`）。

### Task 2.2 — purge_gap 綁 effective horizon [B-4]
- SPEC ref：§P Task 2.2　目標：`purge_gap >= effective label horizon`。
- 實作要點：① 用 Task 2.4 `_resolve_effective_label_horizon` 取 horizon；② `purge_gap = max(requested, horizon)`；③ 傳 holdout + `validate_split_pair_integrity`。
- 修改檔案：`ic_filter_orchestrator.py`（2.1 helper 內）。
- 不可做：不允許 `purge_gap < effective_horizon`。 邊界：horizon 變→隨動；缺→raise。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_holdout_purge_covers_horizon`（train 末 horizon 列落 purge；`purge_gap=horizon-1`→raise）；`::test_purge_uses_effective_not_default`（`default_horizon=5`,`labels.horizons=[13]`→purge 綁 13）。

### Task 2.3 — split 校驗 + time_bounds 遮罩貫穿 [B-2][B-3]
- SPEC ref：§P Task 2.3　目標：[B-2] 校驗；[B-3] `_derive_stage_masks` 用 time_bounds ∩ current index。
- 實作要點：① split 後 `validate_split_pair_integrity(train_plan, test_plan, ts, symbols, allowed_symbols)`；② 新 `_derive_stage_masks(split_plan, current_index)`→`(current_index>=train_lo)&(current_index<=train_hi)` 得布林遮罩（test 同理）；③ 每個改 row 的 stage（event_filter）後重導；④ 校驗 base_universe_hash 相容。
- 修改檔案：`ic_filter_orchestrator.py::analyze`（各 stage 簽名加 `split_plan`）+ 新 `_derive_stage_masks`。
- 不可做：不降級 raise 為 warning；不用 positional mask 直貫跨 row-filter stage。
- 邊界：gap→`raise TimestampDiscontinuityError`；event_filter 刪列→遮罩重導；flag off→None。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_analyze_split_gap_blocked`（刪 3 bar→`pytest.raises`）、`::test_split_valid_passes`、`::test_mask_survives_event_filter`。

### Task 2.4 — pipeline 重排 + effective horizon 早解 [B-5]
- SPEC ref：§P Task 2.4（R2-BLK-2）　目標：stage0 後解 horizon、建 split，再 stage1 train-fit。
- 實作要點：① 新 `_resolve_effective_label_horizon(config, labels_df)`（`default_horizon in horizons ? default_horizon : horizons[0]`）；② flag on 流程：stage0→resolve horizon→`_build_holdout_split_plan`→`validate_split_pair_integrity`→`_stage1_preprocessing(fit_mask=train_mask)`→stage2→stage3（`_derive_stage_masks` 重導）→stage4/5；③ flag off→現行順序不變。
- 修改檔案：`ic_filter_orchestrator.py::analyze` + 新 `_resolve_effective_label_horizon`。
- 不可做：不改 flag-off 順序；不重複跑 label generation；禁先全段 preprocess 再補 mask。
- 邊界：labels_df 缺→既有錯誤路徑；flag off→不變。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_pipeline_order_split_before_preprocessing`、`::test_effective_horizon_resolution`。

## Phase 3 — 訓練段 fit 防洩漏

### Task 3.1 — winsorize train-only [C-1]
- SPEC ref：§P Task 3.1。實作要點：`winsorize/_clip_series` 加 `fit_mask`；邊界 quantile/mean/std/median 用 `series[fit_mask]`，clip 套全；None→全段。
- 修改檔案：`data_preprocessor.py::winsorize`、`::_clip_series`。既有 caller：`preprocess`。
- 不可做：不改 clip 套用範圍。 邊界：train 全 NaN→skip；fit_mask 全 False→raise。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_leakage.py::test_winsor_bounds_from_train_only`（test 段極端值→邊界 `==` 無極端值；變=FAIL）。

### Task 3.2 — standardize train-only [C-2]
- SPEC ref：§P Task 3.2。實作要點：`standardize` 加 `fit_mask`；axis=0 mean/std 用 `df[fit_mask]`；None→全段。
- 修改檔案：`data_preprocessor.py::standardize`。
- 不可做：不改 axis 語義。 邊界：std=0→`replace(0,nan)`；axis=1 不碰。
- 驗證：`pytest ...test_ic_1a_cut1_leakage.py::test_standardize_params_from_train_only`。

### Task 3.3 — handle_missing coverage train-only [C-4]
- SPEC ref：§P Task 3.3。實作要點：`coverage = filled[fit_mask].notna().mean()` 決定刪欄；ffill 仍全段（向後看無 lookahead）；None→全段。
- 修改檔案：`data_preprocessor.py::handle_missing`。
- 不可做：不改填值邏輯。 邊界：train 全 NaN→刪；fit_mask 全 False→raise。
- 驗證：`pytest ...test_ic_1a_cut1_leakage.py::test_coverage_from_train_only`（test 全 NaN 列→刪欄集合不變；變=FAIL）。

### Task 3.4 — remove_constant train-only [C-5]
- SPEC ref：§P Task 3.4。實作要點：`nunique` 用 `df[fit_mask]`；None→全段。
- 修改檔案：`data_preprocessor.py::remove_constant_features`。
- 不可做：不改套用範圍。 邊界：train 常數→刪；fit_mask 全 False→raise。
- 驗證：`pytest ...test_ic_1a_cut1_leakage.py::test_constant_from_train_only`。

### Task 3.5 — preprocess 接 fit_mask [C-3]
- SPEC ref：§P Task 3.5。實作要點：`preprocess(features_df, metadata, fit_mask=None)` 透傳四類；`_stage1_preprocessing` flag on 取 split train 遮罩傳入；flag off→None。
- 修改檔案：`data_preprocessor.py::preprocess`、`ic_filter_orchestrator.py::_stage1_preprocessing`。
- 不可做：不刪舊全段路徑。 邊界：無 mask→全段；有→train fit。
- 驗證：`pytest ...test_ic_1a_cut1_leakage.py::test_preprocess_legacy_no_mask_unchanged`（無 mask→deep-equal 改前）。

## Phase 4 — 測試段 OOS 報告

### Task 4.1 — IC OOS + rolling warmup（option A）[D-1][D-4]
- SPEC ref：§P Task 4.1。實作要點：① flag on→rolling_ic 在 train+test 連續算；② icir/p/threshold/summary 只取 **test 時間索引** 上的 rolling 值；③ `min_test_rows >= max(rolling_windows)+purge_gap` 不足→`SkippedResult`；④ scope 標 "test"。flag off→全段。
- 修改檔案：`ic_filter_orchestrator.py::_stage4_ic_calculation`。
- 不可做：不實作 FDR；不純 test subset 算 rolling（窗不足）。 邊界：test 不足→`SkippedResult`；flag off→全段。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_ic_rolling_warmup`、`::test_min_test_rows_skipped`。

### Task 4.2 — summary/passed_features 切 OOS [D-2]
- SPEC ref：§P Task 4.2。實作要點：`_build_summary_table` 用 OOS 指標；`_apply_thresholds` 套 OOS；flag off→舊。
- 修改檔案：`ic_filter_orchestrator.py::_build_summary_table`、`::_apply_thresholds`。
- 不可做：不改 threshold 數值語義。 邊界：全不過→空 passed+log；flag off→舊。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_summary_and_threshold_same_scope`。

### Task 4.3 — 全 stage5 指標 OOS [D-3]
- SPEC ref：§P Task 4.3。實作要點：monotonicity/coverage/turnover `compute_all` 對 test subset；`compute_ic_statistics` 用 OOS rolling_ic。
- 修改檔案：`ic_filter_orchestrator.py::_stage5_statistical_validation`。
- 不可做：不得讓全段值決定 passed。 邊界：test 空→skip；flag off→全段。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_stage5_metrics_all_oos`（改 train 不動 test→p/coverage/turnover 不變；變=FAIL）。

### Task 4.4 — decay/grouped/redundancy scope [D-5]
- SPEC ref：§P Task 4.4。實作要點：flag on→decay/grouped/stage6-redundancy 對 test subset 算；`ic_half_life` 進 summary 者為 test scope；report metadata 標 `scope=test`；不得以全段值入 summary/passed/filtered。
- 修改檔案：`ic_filter_orchestrator.py::_stage4_ic_calculation`(decay/grouped)、`::_stage6_redundancy`、`::_build_summary_table`、`::_stage7_report`。
- 不可做：不得讓全段 redundancy 決定最終 filtered features。 邊界：test 不足→informational 不可用；flag off→全段。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_decay_redundancy_scope_test`（stage6 filtered_df corr 用 test rows；report metadata `scope=="test"`）。

## Phase 5 — Flag / 預設 / Golden

### Task 5.1 — flag 接線（config_override，無 service churn）[E-1]
- SPEC ref：§P Task 5.1。實作要點：① `analyze()` 讀 `config.ic_train_test_split` 切 Phase 2-4 新/舊路徑；② flag 走既有 `config_override` 透傳（不改 service/前端）；③ 初始 OFF。
- 修改檔案：`ic_filter_orchestrator.py::analyze`（讀 flag 分支）。
- 不可做：不永久預設 OFF；cut1 不改 service/前端。 邊界：flag 缺→預設。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_flag_toggles_path`、`::test_flag_via_config_override`。

### Task 5.2 — G-OLD flag-off byte 守恆 [E-2]
- SPEC ref：§P Task 5.2 + §G。實作要點：G-OLD baseline **已由規劃端動工前凍**（config_hash=`a384e6d22ca15fc639757cb3162e7cb3`，BTC/1h，`tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json`）；executor 只需令 flag-off deep-equal 此檔，不得重凍。
- 修改檔案：`tests/golden/ic_phase1_1a_cut1/`、新 test。
- 不可做：不放寬為「舊鍵存在」；config_hash 不「取最新」。 邊界：clean checkout 缺檔→skip-if-absent（gate 擋派工）。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_off_deep_equal_baseline`（兩側 pop `generated_at` 後 `==` 全等；豁免清單寫死 `{"generated_at"}` 不得擴張——多一欄差=行為變動=FAIL）。

### Task 5.3 — G-NEW 新預設 golden（簽核後凍）[E-3]
- SPEC ref：§P Task 5.3 + §G。實作要點：B6 三方簽核 PASS 後凍 `baseline_new_btc_1h_<config_hash>_<split_id>.json`（內容見 §G）。
- 修改檔案：`tests/golden/ic_phase1_1a_cut1/`、新 test。
- 不可做：簽核前不凍。 邊界：見 §G 容差。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_on_matches_new_golden`（nan_ratio exact；mean/std/value `abs≤1e-9 或 rel≤1e-7`）。

## Phase 6 — 測試 / 簽核

### Task 6.1 — 防洩漏可證偽測試集（真實 kline）[F-1][F-2]
- SPEC ref：§P Task 6.1。實作要點：`tests/momentum/Analysis/test_ic_1a_cut1_leakage.py`；真實 `kline_cache.h5` BTC/1h（含刪 bar gap 反例）；涵蓋 winsor/standardize/coverage/constant + rolling warmup。
- 不可做：禁合成 fixture 代替真實 kline。 邊界：見各 Task。
- 驗證：注入 test 段擾動→fit/刪欄不變=PASS；gap→`pytest.raises(TimestampDiscontinuityError)`；連續正例→純度==1.0。

### Task 6.2 — flag-off byte 等價 + 解耦 [F-3][F-4]
- SPEC ref：§P Task 6.2。實作要點：跑 G-OLD deep-equal；`grep -rE "from api\." momentum/ | wc -l`==0；`./scripts/check_decoupling_phase4.sh` exit 0。
- 不可做：不為過綠改既有斷言。 邊界：N/A。
- 驗證：deep-equal PASS；grep==0；腳本 exit 0。

### Task 6.3 — 三方數據正確性簽核（含機械 checklist）[F-5]
- SPEC ref：§P Task 6.3。實作要點：① 三方獨立 adversarial（非 confirm-review）真實 kline；② 機械 checklist：kline 存在 / `test_holdout_purge_covers_horizon` PASS / `test_*_from_train_only`+`test_stage5_metrics_all_oos`+`test_oos_ic_rolling_warmup` 全 PASS / G-OLD diff==0 / `git diff` 既有 assert 無放寬；③ 三份簽核檔 handoffs/。
- 修改檔案：handoffs/（執行端寫 handoffs/，不覆根 HANDOFF）。
- 不可做：不以 confirm-review 代替 adversarial；簽核未過不凍 G-NEW、不切 default ON。 邊界：任一方疑→reconcile。
- 驗證：機械 checklist 全綠（`pytest` 全 PASS + G-OLD `diff==0` + `grep` 既有 assert 無放寬）+ 三方齊簽 PASS（三份 handoffs 檔）。

---

### Frozen 前 handoff
`SPEC=docs/IC_PHASE1_1a_CUT1_SPEC.md TODO=docs/IC_PHASE1_1a_CUT1_TODO.md FOCUS=完整審查（train/test 洩漏 + OOS 口徑 + pipeline 順序 + rolling warmup）`
→ 兩輪雙家族 adversarial 已過（R1/R2 reconcile）。動工前規劃端須凍 G-OLD baseline + 寫死 cut1 config_hash（flag-off==現行為，用現行碼凍）。
