# IC Phase 1 — 1a 第一刀（單幣縱向接線）SPEC（v2，已納兩輪雙家族 adversarial）

> 來源 PLAN/診斷：handoffs/20260626-ic-PHASE1-1a-{BRIEF,cut1-MANIFEST}.md + CONVERGED §Phase1 + B3-FINAL-SIGNOFF §殘留
> Adversarial：R1 handoffs/20260626-1a-cut1-ADVERSARIAL-{CODEX,COMPOSER,RECONCILE}.md；R2 handoffs/20260626-1a-cut1-ADVERSARIAL2-{CODEX,COMPOSER,RECONCILE}.md（Codex gpt-5.5 + Composer 2.5 各兩輪，皆「需修補後派工」，R1 4 BLOCKING + R2 5 BLOCKING 全採納）
> 日期：2026-06-26　|　對應 TODO：docs/IC_PHASE1_1a_CUT1_TODO.md

## §RISK 風險分級
- RISK-HIT: a,d
- **大小**：大。接線動 IC 主流程（`analyze()`）共用路徑、難回退、碰防洩漏。
- **命中高風險原則**：(a) 數值/資料品質（train-fit 邊界、OOS 報告值、flag-off byte 守恆）；(b) 跨模組/共用路徑（`ic_filter_orchestrator.analyze`、`data_preprocessor`、`factories`、`core/contracts`，多下游讀 `get_result()`）；(c) 多 phase/難回退；(d) ML 正確性/防洩漏（train-only fit、OOS、purge、label horizon 前瞻、rolling warmup、單幣連續性）。
- 命中 (a)+(d) → **§G Golden 必填、雙家族 adversarial 必跑（已跑兩輪）、三方數據簽核必跑**。

## §A 假設與待使用者確認
- **已查證事實**（附查證方式，皆實讀/實跑）：
  - `analyze()` 8 階段順序：stage0 ingestion→**stage1 preprocessing**→stage2 label→**stage3 event_filter**→feature_filter→stage4 ic→stage5 stat→stage6 redundancy→stage7 report（`ic_filter_orchestrator.py:94-166`）。**event_filter 在 preprocessing 之後**以 `loc[idx]` 改 row universe（`:1096-1097`）。
  - **依賴倒置（R2 抓）**：stage1 preprocessing 早於 stage2 label；而 split 需 label horizon、preprocessing 需 train mask → 須重排（§P Task 2.4）。`labels_df` 在 **stage0 已載入**，故 horizon 可早解。
  - **label horizon fallback**：`default_horizon not in labels_cfg.horizons → horizons[0]`（`:1049-1051`）→ purge 不可硬綁 `default_horizon`，須解 effective horizon。
  - 現行洩漏點（全段 fit）：winsor `series.quantile`（`data_preprocessor.py:154-155`）、standardize `df.mean/std(axis=0)`（`:136-137`）、handle_missing coverage `notna().mean()`（`:113-116`）、remove_constant `nunique`（`:120-124`）。
  - **契約 row_index 為 positional（R2 抓）**：`validate_split_integrity` 一律 `np.asarray(plan.row_index, dtype=int)` 當 positional 索引（`contracts.py:511,528-537`）；`ICSplitAdapter` 用 `index_kind="positional"`（`ic_split_adapter.py:234-246`）。**故 cut1 SplitPlan 必用 positional，遮罩重導改用 time_bounds**（不得用 timestamp index_kind，否則 validator crash）。
  - **rolling IC 窗口感知**：`compute_rolling_ic` 每窗需 `window` 列歷史（`ic_engine.py:268-302`），預設 `rolling_windows=[21,63,126]`（`ic_config_schema.py:64-68`）；純 test 子集前 window-1 列無有效 IC → 須 warmup（§P Task 4.1 option A）。
  - **`ICConfig` 無 `embargo` 欄（R2 抓）**：頂層無（`ic_config_schema.py:330-365`）→ B1 新增。
  - **freeze 腳本路徑（R2 抓）**：repo **無** `scripts/freeze_baseline.py`，實為 `tests/golden/ic_phase1_contract/freeze_baseline.py`（含寫死 hash `a384e6d2...`）。
  - `metadata["symbol"]`/`["timeframe"]` 主流程可取（`:1039-1040`）；service 傳 `req_symbol/req_timeframe`（`ic_analysis_service.py:74-75`）。
  - **timeframe→expected_freq 已實跑驗證**：`pd.Timedelta('1h')=01:00:00`、`'4h'=04:00:00`、`'12h'=12:00:00`（雙家各自實跑確認）。
  - `analyze()` 單幣輸入**無 row-level symbol 欄**（feature matrix + DatetimeIndex，metadata 僅全域 symbol）→ allowlist 僅驗 metadata symbol，row-level 污染 cut1 N/A（§N）。
  - `create_ic_split_adapter()` 未轉 `allowed_symbols`（`factories.py:574-581`）；`ICSplitAdapter` 已支援該欄（`ic_split_adapter.py:39`）。
  - `ICAnalyzeRequest.config_override` 已 deep-merge 透傳（`ic_analysis_service.py:1061-1097` + `_apply_config_override` `:1828-1835`）→ flag 走 config_override，**cut1 不改 service**（§P Task 5.1）。
  - `InsufficientDataError` 現行 `<100` 列（`:1442-1443`）。
  - `ic_config.py` 僅 re-export，schema 在 `ic_config_schema.ICConfig`。
  - 真實 kline：`data_cache/feature_klines/kline_cache.h5`（10 symbols × {1h,4h,12h}）。
- **待使用者確認**：無。
- **已確認結果**（使用者，2026-06-26）：① 切兩刀，本刀=cut1=單幣縱向。② 三方簽核 PASS 後**新算法預設開啟**，flag 只當逃生口（[[feedback_no_default_off_after_validation]]）。③ 先全力 Phase 1 正確性。④ 複用切分索引邏輯，不重寫切分數學。
- **委員會裁決（技術，兩輪雙家族 adversarial 收斂，對使用者透明不另問）**：① **切分=單一時間順序 chronological holdout**（非 CPCV/WF adapter，兩輪兩家一致）。② **SplitPlan index_kind="positional"**，遮罩重導用 time_bounds（R2）。③ **rolling OOS=option A**（train+test warmup，只報 test 時間索引值，R2）。④ **config 欄位移 B1**（R2）。

## §C 約束
- 解耦 7 條：`grep "from api\." momentum/`→0；契約 DTO 引擎側 `core/contracts.py`、API 側 `api/models/ic_models.py` 不互 import；服務經 factory。
- 不可違反原則：跨 tier 可重複、多 symbol 不 OOM、資料品質（不假資料/不跨 symbol 污染/不靜默降級）、不弱化 NaN/inf gate、**flag off 時不擅改輸出數值**（G-OLD byte 守恆）。
- 本任務特別注意（共用路徑/下游）：`analyze()` 影響 decay/quantile/correlation/grouped/export route + 前端 ic-analysis；新行為一律藏 flag 後，**簽核後 default ON、flag=逃生口**（不永久關閉）。

## §G Golden / Baseline（高風險必填）
- **凍結時機 / reference（deterministic）**：動工前。reference = symbol **BTC**、timeframe **1h**、mode longitudinal。**G-OLD = flag-off = 現行為，可用現行碼凍**。
  - **config_hash（已凍，2026-06-26）＝`a384e6d22ca15fc639757cb3162e7cb3`**（BTC/1h longitudinal，沿用 1-contract reference run：90857 feature × 20352 row，max_features=50 決定性子集避免 OOM）。
  - 凍結命令：`python tests/golden/ic_phase1_1a_cut1/freeze_baseline.py --max-features 50 --timeout-seconds 900`（沿用 1-contract 同 inputs，out 目錄 `tests/golden/ic_phase1_1a_cut1/`）。檔名 `baseline_old_btc_1h_a384e6d2.json`。
  - **gate 把關**：baseline 檔 + config_hash 未凍 → dispatch gate 擋。skip-if-absent 僅供 clean checkout，不當 CI 假綠。
- **G-OLD（flag off）[E-2][F-3]**：`ic_train_test_split=off` 時 `analyze()` 全輸出與 baseline **deep equality，唯一豁免欄＝`generated_at`**（`ic_reporter.py:38` `datetime.utcnow()` 易變時間戳；實測：同碼兩次 run 僅此欄差，餘 52MB byte 全等）。比較前 pop `generated_at`（兩側皆 pop），**其餘任一鍵/值 diff=FAIL**。豁免清單寫死＝`{"generated_at"}`，不得擴張（多一欄差即代表行為變動）。
- **G-NEW（flag on）[E-3]**：flag on 輸出另凍 `baseline_new_btc_1h_<config_hash>_<split_id>.json`，**三方數據簽核 PASS 才凍**；內容＝名稱集合 sha256 + 數量/schema + 每 feature mean/std/nan_ratio + 抽樣 value/NaN mask hash + **split train/test 邊界 timestamp + purge_gap + min_test_rows**。通過：nan_ratio exact；mean/std/value `abs≤1e-9 或 rel≤1e-7`（float64）；超出列 feature+diff=FAIL。
- 範圍：僅 flag-off 對照 + flag-on 單幣 BTC/1h longitudinal；cross_sectional 不覆蓋（cut2）。

## §P Phase 與依賴

### Phase 1 — 契約啟用前置 + config 欄位（依賴：無）
**Task 1.1 — 轉傳 allowed_symbols [A-1]**
- 目標：factory 把 `allowed_symbols` 傳進 `ICSplitAdapter`。檔案：`momentum/factories.py::create_ic_split_adapter`（加 `allowed_symbols: Optional[set[str]]=None`）。
- 改法：簽名加 `allowed_symbols`，轉入 `ICSplitAdapter`。
- 驗證：`pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols`（傳 {"BTC"}→`adapter.allowed_symbols=={"BTC"}`）。
- 邊界：None→None；空 set→空 set（不誤轉 None）。
- 不可做：不改 adapter 內部校驗。

**Task 1.2 — timeframe 推導 expected_freq [A-2]**
- 目標：由 `metadata["timeframe"]` 推導 `expected_freq`。檔案：`ic_filter_orchestrator.py::_resolve_expected_freq(metadata)`。
- 改法：白名單 map "1h"/"4h"/"12h"；缺/非法（`"1H"`/`"60m"`）且 flag on→fail-closed raise（不靜默 None）。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq`（"4h"→`pd.Timedelta` 解析 `04:00:00`；"1H"→`pytest.raises`）。
- 邊界：timeframe 缺（flag on）→raise；flag off→不要求。
- 不可做：不在此實作 gap 檢測。

**Task 1.3 — metadata symbol allowlist [A-3]**
- 目標：傳 `allowed_symbols={normalized(metadata["symbol"])}`，驗 metadata symbol。檔案：`ic_filter_orchestrator.py` split 產生處。
- 改法：symbol 缺/不在 allowlist（flag on）→raise。
- 驗證：`pytest ...::test_metadata_symbol_required`（缺→`pytest.raises`）；`test_metadata_symbol_outside_allowlist_blocked`。
- 邊界：symbol 缺→raise；正常→metadata 層純度==1.0。
- 不可做：cut1 不驗 row-level 跨 symbol 污染（§N，留 cut2）。

**Task 1.4 — config 欄位（移前置，R2-BLK-4）[E-1 前置]**
- 目標：`ICConfig` 新增 `ic_train_test_split: bool=False`、`oos_test_size: float=0.2`、`embargo: int=0`、`min_test_rows: int`（預設＝`max(rolling_windows)+purge_gap` 動態或保守常數）。**純欄位、預設 OFF、不改任何行為**（保 G-OLD）。檔案：`momentum/Analysis/ic_config_schema.py::ICConfig`。
- 改法：Pydantic 欄位 + 預設；不接線（B2 才用）。
- 驗證：`pytest ...::test_icconfig_new_fields_default_off`（預設 `ic_train_test_split is False`、`oos_test_size==0.2`；`ICConfig()` 不改既有序列化）。
- 邊界：未給→預設；config_override 可覆寫。
- 不可做：此 Task 不接 analyze() 邏輯（只加欄位）。

### Phase 2 — 切分產生 + 紅線接線 + pipeline 重排（依賴：Phase 1）
**Task 2.1 — 單幣 chronological holdout（positional）[B-1]**
- 目標：產單一時間順序 holdout train/test `SplitPlan`（排序後尾段 test，**`index_kind="positional"`**）。檔案：`ic_filter_orchestrator.py::_build_holdout_split_plan`。
- 凍結參數：`test_size`＝`config.oos_test_size`（0.2）；`split_point=floor((1-oos_test_size)*n)`；train rows＝positional `[:split_point]`，test rows＝positional `[split_point+purge_gap:]`（purge 見 2.2）；`embargo=config.embargo`；`min_test_rows` 不足→`SkippedResult`；`row_index` 存 positional int、`time_bounds`＝該段首尾 timestamp、`base_universe_hash`＝stage0 features_df.index deterministic hash、`symbol`、`expected_freq`。複用 `SplitPlan`，不重寫切分數學。
- 驗證：`pytest ...::test_analyze_builds_holdout`（真實 BTC/1h→train/test positional 不重疊、test 尾段、time_bounds 單調；`index_kind=="positional"`）。
- 邊界：`test<min_test_rows` 或 `train<min`→`SkippedResult`；flag off→不產 split。
- 不可做：不用 CPCV/WF adapter；不重寫切分數學；**不用 `index_kind="timestamp"`**。

**Task 2.2 — purge_gap 綁 effective label horizon [B-4]**
- 目標：`purge_gap >= effective label horizon`，杜絕 train 末 forward-return 標籤用 test 價格。檔案：Task 2.4 helper 提供 horizon。
- 改法：`purge_gap = max(requested_purge, effective_horizon)`；傳 holdout + `validate_split_pair_integrity`。
- 驗證（可證偽）：`pytest ...::test_holdout_purge_covers_horizon`（已知切點→train 末 `horizon` 列落 purge、不在 train row_index；`purge_gap=horizon-1`→偵測「train 末列 label 需 test 價格」並 raise）；`test_purge_uses_effective_not_default`（`default_horizon=5` 但 `labels.horizons=[13]`→purge 綁 13）。
- 邊界：horizon 變→purge 隨動；horizon 缺→raise。
- 不可做：不允許 `purge_gap < effective_horizon`。

**Task 2.3 — split 紅線校驗 + time_bounds 遮罩貫穿 [B-2][B-3]**
- 目標：[B-2] `validate_split_pair_integrity`（帶 expected_freq+allowed_symbols）；[B-3] 遮罩跨 stage 重導 `_derive_stage_masks(split_plan, current_index)` 用 **train/test `time_bounds` ∩ current_index**（positional row_index 不直貫跨 row-filter stage）。檔案：`analyze()` + 新 `_derive_stage_masks`，各 stage 簽名加 `split_plan`（flag off→None）。
- 改法：每個改 row 的 stage（event_filter）後以 `(current_index >= train_lo) & (current_index <= train_hi)` 得布林遮罩；不變量＝train/test 時間互斥 + purge，row 移除不破壞；校驗 base_universe_hash 相容。
- 驗證：`pytest ...::test_analyze_split_gap_blocked`（BTC/1h 刪 3 bar→`pytest.raises(TimestampDiscontinuityError)`）；`test_split_valid_passes`；`test_mask_survives_event_filter`（event_filter 刪列後遮罩仍時間互斥、無錯位）。
- 邊界：含 gap→raise；event_filter 刪列→遮罩重導正確；flag off→各 stage None。
- 不可做：不降級 raise 為 warning；不用 positional mask 直貫跨 row-filter stage。

**Task 2.4 — pipeline 重排 + effective horizon 早解 [B-5]**
- 目標：stage0 後解 effective horizon、建 split，再 stage1 train-fit（解依賴倒置 + horizon fallback）。檔案：`ic_filter_orchestrator.py::analyze` + 新 `_resolve_effective_label_horizon(config, labels_df)`。
- 改法：flag on 流程＝stage0 → `_resolve_effective_label_horizon`（沿用 stage2 fallback 規則：`default_horizon in horizons ? default_horizon : horizons[0]`）→ `_build_holdout_split_plan`（purge=horizon）→ `validate_split_pair_integrity` → `_stage1_preprocessing(fit_mask=train_mask)` → stage2 → stage3（重導遮罩）→ stage4/5。**禁先全段 preprocess 再補 mask**。flag off→現行順序不變。
- 驗證：`pytest ...::test_pipeline_order_split_before_preprocessing`（flag on：preprocessing 收到的 fit_mask 非 None 且對應 holdout train；split 建立早於 stage1）；`test_effective_horizon_resolution`（fallback 路徑）。
- 邊界：labels_df 缺→走 label 既有錯誤路徑；flag off→順序不變。
- 不可做：不改 flag-off 順序；不重複跑 label generation。

### Phase 3 — 訓練段 fit 防洩漏（依賴：Phase 2）
**Task 3.1 — winsorize train-only fit [C-1]**
- 檔案：`data_preprocessor.py::winsorize/_clip_series`（加 `fit_mask`）。改法：邊界用 `series[fit_mask]`，clip 套全 series；None→全段。
- 驗證（可證偽）：`pytest ...::test_winsor_bounds_from_train_only`（test 段注入極端值→clip 邊界 `==` 無極端值時；變動=FAIL）。
- 邊界：train 全 NaN col→skip；fit_mask 全 False→raise。 不可做：不改 clip 套用範圍。

**Task 3.2 — standardize train-only fit [C-2]**
- 檔案：`data_preprocessor.py::standardize`。改法：`axis=0` mean/std 用 `df[fit_mask]`；None→全段。
- 驗證：`pytest ...::test_standardize_params_from_train_only`（test 段改動→train 段標準化值不變）。
- 邊界：std=0→`replace(0,nan)`；axis=1 cut1 不碰（§N）。 不可做：不改 axis 語義。

**Task 3.3 — handle_missing coverage train-only [C-4]**
- 檔案：`data_preprocessor.py::handle_missing`。改法：`coverage = filled[fit_mask].notna().mean()` 決定刪欄；None→全段。**ffill 仍全段（僅向後看無 lookahead，R2 確認可接受）**。
- 驗證（可證偽）：`pytest ...::test_coverage_from_train_only`（test 段注入全 NaN 列→刪欄集合不變；變動=FAIL）。
- 邊界：train 全 NaN col→刪；fit_mask 全 False→raise。 不可做：不改填值邏輯。

**Task 3.4 — remove_constant_features train-only [C-5]**
- 檔案：`data_preprocessor.py::remove_constant_features`。改法：`nunique` 用 `df[fit_mask]`；None→全段。
- 驗證：`pytest ...::test_constant_from_train_only`（test 段使某 col 變常數→刪欄集合不變）。
- 邊界：train 內常數→刪；fit_mask 全 False→raise。 不可做：不改套用範圍。

**Task 3.5 — preprocessing 介面接受 train 遮罩 [C-3]**
- 檔案：`data_preprocessor.py::preprocess`、`ic_filter_orchestrator.py::_stage1_preprocessing`。改法：`preprocess(features_df, metadata, fit_mask=None)` 透傳四類統計；`_stage1_preprocessing` flag on 取 split train 遮罩（Task 2.4 重排後可得）傳入；flag off→None。
- 驗證：`pytest ...::test_preprocess_legacy_no_mask_unchanged`（無 mask→與改前 deep-equal，接 G-OLD）。
- 邊界：無 mask→全段；有 mask→train fit。 不可做：不刪舊全段路徑。

### Phase 4 — 測試段 OOS 報告（依賴：Phase 3）
**Task 4.1 — IC 在 OOS 計算 + rolling warmup（option A）[D-1][D-4]**
- 目標：[D-1] stage4 IC scope 標 test；[D-4] **rolling_ic 在 train+test 連續算（warmup 用 train，無洩漏），icir/p/threshold/summary 只取 test 時間索引上的 rolling 值**；`min_test_rows >= max(rolling_windows)+purge_gap` 不足→`SkippedResult`。檔案：`ic_filter_orchestrator.py::_stage4_ic_calculation`。
- 改法：flag on→rolling 用連續 train+test，輸出後依 test time index 切片供 icir/p；selection scope 標 "test"（不實作 FDR）。flag off→全段。
- 驗證（可證偽）：`pytest ...::test_oos_ic_rolling_warmup`（test 前 window-1 列為 in-sample warmup 標記/NaN，icir/p 僅基於 test 索引值）；`test_min_test_rows_skipped`（test < max(window)+purge→`SkippedResult`）。
- 邊界：test 不足→`SkippedResult`；flag off→全段。
- 不可做：不實作 FDR；不碰 cross_sectional；不純 test subset 算 rolling（窗不足）。

**Task 4.2 — summary/passed_features 切 OOS [D-2]**
- 檔案：`_build_summary_table`/`_apply_thresholds`。改法：flag on→summary 由 OOS 指標衍生，threshold 套 OOS。
- 驗證：`pytest ...::test_summary_and_threshold_same_scope`（passed_features 的 IC 與 summary 同源 OOS）。
- 邊界：全不過→空 passed+log；flag off→舊行為。 不可做：不改 threshold 數值語義。

**Task 4.3 — 全 stage5 指標 OOS 口徑 [D-3]**
- 目標：所有進 summary/threshold/passed 的指標一律 test scope（icir/p/monotonicity/coverage/turnover）。檔案：`_stage5_statistical_validation`（compute_all 傳 test 遮罩）。
- 驗證（可證偽）：`pytest ...::test_stage5_metrics_all_oos`（改 train 不動 test→p/coverage/turnover 不變；變=FAIL）。
- 邊界：test 空→skip；flag off→全段。 不可做：不得讓全段值決定 passed。

**Task 4.4 — decay/grouped/redundancy scope [D-5]**
- 目標：flag-on 時 decay/grouped/stage6-redundancy **不得以全段值入 summary/passed/filtered**；進選擇/輸出者一律 test scope（含 stage6 corr 對 test 算），decay/grouped informational 且 report metadata 標 `scope=test`。檔案：`_stage4_ic_calculation`（decay/grouped）、`_stage6_redundancy`、`_build_summary_table`（`ic_half_life`）、`_stage7_report`。
- 改法：flag on→decay/grouped/redundancy 對 test subset 算；`ic_half_life` 進 summary 者為 test scope；report metadata 標 scope。
- 驗證：`pytest ...::test_decay_redundancy_scope_test`（flag on→stage6 filtered_df 相關矩陣用 test rows；report metadata `scope=="test"`）。
- 邊界：test 不足→informational 標記不可用；flag off→全段。
- 不可做：不得讓全段 redundancy 決定最終 filtered features。

### Phase 5 — Flag / 預設 / Golden（依賴：Phase 2-4）
**Task 5.1 — flag 接線（config_override，無 service churn）[E-1]**
- 目標：`analyze()` 依 `config.ic_train_test_split`（Task 1.4 已加欄位）切 Phase 2-4 新/舊路徑；flag 走既有 `config_override` 透傳（**cut1 不改 service、不改前端**）。初始 OFF。檔案：`ic_filter_orchestrator.py::analyze`（讀 flag 分支）。
- 改法：flag on→Task 2.4 重排路徑；flag off→現行。**初始 PR OFF，B6 簽核 PASS 後切預設 ON**。
- 驗證：`pytest ...::test_flag_toggles_path`（off→舊路徑，on→新路徑）；`test_flag_via_config_override`（API config_override 設 flag→透傳 ICConfig 生效）。
- 邊界：flag 缺→預設值。
- 不可做：不永久預設 OFF（[[feedback_no_default_off_after_validation]]）；cut1 不改 service/前端（§N）。

**Task 5.2 — G-OLD flag-off byte 守恆 [E-2]**
- 檔案：`tests/golden/ic_phase1_1a_cut1/`。改法：動工前用 `tests/golden/ic_phase1_contract/freeze_baseline.py` 凍 `baseline_old_btc_1h_<config_hash>.json`（config_hash 寫死於 §G+此）。
- 驗證：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_off_deep_equal_baseline`（`==` 全等）。
- 邊界：clean checkout 缺檔→skip-if-absent（gate 擋派工）。 不可做：不放寬為「舊鍵存在」；config_hash 不「取最新」。

**Task 5.3 — G-NEW 新預設 golden（簽核後凍）[E-3]**
- 檔案：同上目錄 `baseline_new_btc_1h_<config_hash>_<split_id>.json`。改法：B6 三方簽核 PASS 後凍（內容見 §G）。
- 驗證：`pytest ...::test_flag_on_matches_new_golden`（nan_ratio exact；mean/std/value `abs≤1e-9 或 rel≤1e-7`）。
- 邊界：見 §G。 不可做：簽核前不得凍 G-NEW。

### Phase 6 — 測試 / 簽核（依賴：Phase 1-5）
**Task 6.1 — 防洩漏可證偽測試集（真實 kline）[F-1][F-2]**
- 檔案：`tests/momentum/Analysis/test_ic_1a_cut1_leakage.py`。改法：真實 `kline_cache.h5` BTC/1h（含刪 bar gap 反例），涵蓋 winsor/standardize/coverage/constant 四類 + rolling warmup。
- 驗證：注入 test 段擾動→fit/刪欄不變=PASS；gap→`pytest.raises(TimestampDiscontinuityError)`；連續正例→純度==1.0。
- 邊界：見各 Task。 不可做：禁合成 fixture 代替真實 kline。

**Task 6.2 — flag-off byte 等價 + 解耦 [F-3][F-4]**
- 檔案：golden + 解耦腳本。驗證：G-OLD deep-equal PASS；`grep -rE "from api\." momentum/ | wc -l`==0；`./scripts/check_decoupling_phase4.sh` exit 0。
- 邊界：N/A。 不可做：不為過綠改既有斷言。

**Task 6.3 — 三方數據正確性簽核（含機械 checklist）[F-5]**
- 目標：Claude+Codex+Composer 獨立 adversarial 簽「split/holdout/purge-horizon/train-fit/rolling-warmup/OOS 無洩漏」。檔案：handoffs/簽核報告 + checklist。
- **機械 checklist（可證偽，R2 補）**：① `data_cache/feature_klines/kline_cache.h5` 存在；② purge 反例測試 `test_holdout_purge_covers_horizon` PASS；③ `test_winsor/coverage/constant_from_train_only`、`test_stage5_metrics_all_oos`、`test_oos_ic_rolling_warmup` 全 PASS；④ G-OLD `test_flag_off_deep_equal_baseline` diff==0；⑤ `git diff` 既有測試斷言無放寬（`grep` 比對）。
- 改法：各方獨立獵漏（非 confirm-review，[[feedback_adversarial_beats_signoff]]）；任一方疑→reconcile。三份 handoffs `20260626-1a-cut1-SIGNOFF-{CLAUDE,CODEX,COMPOSER}.md`。
- 驗證：機械 checklist ①-⑤ 全綠（含 `pytest` 全 PASS + G-OLD `diff==0` + `grep` 既有 assert 無放寬）+ 三方齊簽 PASS。
- 邊界：任一方疑→reconcile。 不可做：不以 confirm-review 代替 adversarial；簽核未過不得凍 G-NEW、不切 default ON。

## §V 驗證策略與邊界測試目錄
- 層級：單元（factory/freq/contract/config 欄位）、整合（holdout+pipeline 重排+time_bounds 遮罩貫穿 event_filter+train-fit+rolling warmup+OOS 全口徑）、Golden（G-OLD byte / G-NEW OOS）、邊界。全可 `pytest tests/momentum/ tests/api/` 獨立跑（Rule 6）。
- **防假綠**：diff 既有斷言不得放寬；**gap/purge<horizon/跨 symbol 反例必真 `pytest.raises`，不得降級 warning**；**train 段擾動不得改變 test 結果**；不引用 ML 孤島 synthetic 測試代替真實 kline。
- **邊界目錄**（打勾對應 Task）：☑空DF ☑全NaN列(3.1,3.3) ☑Inf ☑std=0(3.2) ☑常數列(3.4) ☑重複/亂序 timestamp(2.3) ☑缺bar/gap(2.3,6.1) ☑purge<horizon(2.2) ☑horizon fallback(2.2,2.4) ☑event_filter 刪列後遮罩(2.3) ☑test<min_test_rows(2.1,4.1) ☑rolling warmup(4.1) ☑flag off byte 守恆(5.2) ☑大尺度浮點(G-NEW)。

## §R 回退
- 每 Task 獨立 commit 可單獨 revert；新路徑藏 `ic_train_test_split` flag；**初始 PR flag 預設 OFF（=舊行為，G-OLD byte 守恆）→ 三方簽核 PASS 才切預設 ON**；G-NEW 簽核前不凍；任一 Golden FAIL→不 merge。

## §N N/A 登記
- **cross_sectional split/leakage**：N/A 本刀 — 留 cut2。
- **row-level 跨 symbol 污染**：N/A — `analyze()` 單幣輸入無 row-level symbol 欄；allowlist 僅驗 metadata。留 cut2/multi-symbol。
- **standardize axis=1（cross-sectional）train-fit**：N/A 本刀（Task 3.2 只 axis=0）。
- **handle_missing ffill 全段**：N/A 改動 — 僅向後看無 lookahead（R2 確認）；只改 coverage 刪欄判據 scope。
- **cut1 改 service/前端**：N/A — flag 走既有 `config_override` 透傳；前端接線留 cut2/另刀。
- **`_ic_cache` split-aware key / partial rerun**：N/A 本刀（單幣風險低）；註明 flag 變更須清 cache（同實例連跑 on/off 勿混）。
- **FDR/Net IC/attribution/HAC/空圖**：N/A — 1b-1f。
- **多 symbol 主流程切分**：N/A — cut1 單幣。
- 其餘必填段（§RISK/§A/§C/§G/§P/§V/§R）全填。
