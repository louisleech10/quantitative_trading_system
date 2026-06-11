# fail-open 鏈修復(統一)— Manifest(扁平 ID)

> 決策:FF_FAILOPEN_FIX_BRIEF.md + LAYER_RESULT_BRIEF.md｜深稽:FF_FAILOPEN_AUDIT.md｜adversarial:FF_FAILOPEN_ADVERSARIAL.md + LAYER_RESULT(兩輪)
> 取代 FF_FAILOPEN_FIX_MANIFEST(42ID)與 LAYER_RESULT_MANIFEST(28ID)。每個 `[X-n]` 須落進 SPEC(§P/§V/§G)與 TODO。
> **誠實框定**:健康 run(無故障)byte 不變;故障路徑刻意改變(catch+標記+gate)=fail-open 的目的。

## P. 協議(LayerExecutionResult,catching 明示)
- [P-1] `LayerExecutionResult(data, status, failed_engines: tuple[str,...], reason, configured_engines, present_engines, required_engines, dependency_error)`(放 `momentum/core/contracts.py`;frozen,tuple 真不可變)
- [P-2] status enum **窮盡互斥**(per-layer 真值表):`ok/engine_partial/all_engines_failed/empty_disabled/empty_short_data/empty_not_applicable/offloaded_to_registry/dependency_failed/layer_failed`
- [P-3] **catching=明示改控制流**:L1/L2 per-engine catch 記 `failed_engines`(required 仍最終 fail,但先記原因);L5 reference fetch 例外→`dependency_failed`(非 not_applicable);L2 parallel `continue` 記原因。**故障路徑行為改變=預期**(健康路徑不變)
- [P-4] per-layer 真值表(L1/L2 engine型、L3 offloaded、L5 多空成因、L6 sub-engine 全關):每組唯一映射,SPEC 內嵌
- [P-5] 6 層回傳 result;`derive_status` 由 catch 後的完整資訊判定(非純觀察)
- [P-6] **完整 caller 清單**(grep 全 repo 重產確認):主 generate `:269-284`、`_run_l1_l6_for_ic_first` `:300-319`、multi-TF 4組(serial`:169`/parallel primary`:373`/legacy`:1187`/worker`:1503`)、memmap spill `:335`、`_combine_layers:2817`、CGSA persist `_persist_single_tf_l3_l6_to_cgsa`、測試/scripts factory(test_feature_factory_batch2*/test_golden_output_generation/test_primary_self_align_skip/test_multi_tf_generator stub/profile_*.py)。全部原子同 commit 遷移取 `.data`
- [P-7] zero-copy:`result.data is original_df`(wrap 不複製)+ spill 路徑允許既有 block-copy 但 wrapper 不再複製、結果與 memmap `np.shares_memory`;不用 RSS 精確零增量當判據

## M. manifest 語義完整性
- [M-1] manifest 加 `expected_layers/present_layers/failed_layers`(由 LayerExecutionResult status 衍生)
- [M-2] 加 `expected_timeframes/actual_timeframes/failed_timeframes`
- [M-3] 加 `quality_status` + `failure_reasons[]`;寫入 CGSA(`feature_factory.py:2304+`)+ 非CGSA(`:2611+`)+ `feature_storage.py:1529,1550,978`(不再無條件 complete)
- [M-4] schema_version 用**新字串**(`raw_v2`/`processed_v2`,非 +1)

## S. 狀態模型(B2/G-2)
- [S-1] enum 全集 `complete|partial|failed|empty_selection|legacy|unknown`;artifact-level + run-level 雙層
- [S-2] `merge_quality_status(artifacts)->run_status` 偽碼:偏序(failed>unknown>legacy>partial>empty_selection>complete)+ 原子 read-modify-aggregate(不被單一 processed artifact 覆蓋成更樂觀)
- [S-3] consumer 讀 **run-level** gate;`empty_selection`(使用者明選空)白名單放行,其餘非 complete 拒
- [S-4] **遷移偵測**(B1):`unknown` 判定 = 缺新 schema_version **或**缺 expected/present/failed 欄(非看 quality_status 是否存在;現碼已寫 complete);legacy adapter `:354,367,384` 不再無條件 complete:True

## G. 消費者 gate
- [G-1] IC Gatekeeper(`ic_engine.py:476-501`)拒 `run_status!=complete`,`allow_partial_ic` 才放行;驗 layer/timeframe 完整(非只 complete 布林)
- [G-2] training/xgboost(`cross_symbol_training_service.py`、`xgboost_batch_service.py:486-488`)拒 partial;交集前先驗完整不掩蓋缺欄
- [G-3] reader(`feature_reader.py:335-340`)gate 看 run_status;UI/browser/coverage 可讀 partial 但回 status 標示(不擋讀)
- [G-4] cache/resume 命中驗 run_status:CGSA resume `:607`、registry resume `column_group_registry.py:183`、legacy `_try_load_cache:2772`(不只 config_hash/每層≥1組)

## R. producer fail-closed
- [R-1] 層失敗(LayerExecutionResult.status∈{layer_failed,all_engines_failed,dependency_failed})+ `allow_partial_layers=False`(預設)→ abort;True→記 failed_layers
- [R-2] multi-TF 非primary TF 失敗 + `allow_partial_timeframes=False`(預設)→ abort(4 generator 都改);primary缺/全跳仍 raise
- [R-3] NaN-Inf gate:`max_inf_ratio`(預設0)+`max_nan_ratio`(Phase0 baseline 上界+裕度,寫死值)超標→partial/failed
- [R-4] L6.5 失敗:persist 用 effective config + `preprocessing_applied=False` + `preprocessing_steps_applied=[]`(config↔artifact 一致)
- [R-5] CGSA TF rollback:失敗 rollback 該 TF **所有** groups(含 layer 內已 persist 的 L1/L2)用 `unregister_group`(`:1136`)+ parquet/npy cleanup + manifest 原子;rollback 失敗即 abort
- [R-6] combine 丟 expected 空層→記 failed_layers(`:2817`);API restart 讀 quality→partial 標 `completed_degraded`(`feature_factory_service.py:3835`);registry add 失敗依 allow_partial 處置(`:2473`)

## W. 第5軸 winsor 洩漏
- [W-1] `feature_validator.py:169` 全樣本 quantile winsor = look-ahead → config 決策樹(L6.5 winsor on × validator winsor on × CGSA/non-CGSA × IC-First)判保留/移除/改因果;winsor 後重掃 NaN/Inf;「每條 config 路徑 ≤1 winsor」測試

## C. flag/config contract
- [C-1] 6 flag(`allow_partial_layers/timeframes/ic/training`+`max_inf_ratio/max_nan_ratio`)定義:所屬 model(`feature_config.py::FactoryConfig` 或 `api/core/config.py`)、API 欄位、Pydantic↔TS 型別、作用域(per-run)、是否進 config_hash(partial flag 不進、gate flag)
- [C-2] flag 預設矩陣(producer×consumer×UI)+ phase-specific 回退(schema 不可靠 flag 回退,配 migration)

## V. 驗證(三方數據正確性 + golden 全量)
- [V-1] **Phase0 凍 baseline**:真實 kline `data_cache/feature_klines/kline_cache.h5`(10 symbol×{1h,4h,12h});固定可重現輸入(config_hash/commit/kline sha256/env:FFACT_LAYER1_PARALLEL·CGSA·Polars·persist_mode·FFACT_USE_SEARCHSORTED·MERGE_CHUNK/版本:py·pandas·numpy·TA-Lib·Numba/PYTHONHASHSEED/tier);可執行產生命令
- [V-2] **§G 全量 canonical hash(非抽樣)**:整張表有序 index(含 timestamp 型別+單位)+有序欄+dtype(float32)+每格 value bytes(定義 endian/-0.0/NaN payload)+完整 NaN mask;per-layer + 最終 L7 + multi-TF 合併;artifact 檔 SHA256(非只大小)
- [V-3] **Gate-A 精確一致**(健康 run 行為不變):改後==改前全量 hash,任一格不同=FAIL;**Gate-B 容差**(僅浮點 reduction 必要,known 清單,三方同意)分離
- [V-4] **故障注入矩陣**:整層失敗/NaN超標/部分TF失敗/CGSA TF失敗/L6.5失敗→各自預期 quality_status + gate 行為(故障路徑刻意改變,真實 generate 非合成)
- [V-5] **無洩漏(全欄)**:prefix 截斷不變性——擾動/截斷尾端 N 根,前綴每欄每格==未截斷版;既有 PIT 測試清單(test_causal_winsor/test_mtf_align_golden)綠
- [V-6] **merge 正確(獨立 oracle)**:手寫獨立 as-of oracle(非呼叫 TimeframeAligner 本身)——驗 maximal eligible source timestamp + 實際欄值逐格;合併後 index 與 primary **完全相等**(順序/重複/長度/dtype)
- [V-7] **split/隔離**:多 symbol 各 artifact 改前後一致 + 打亂 symbol/TF 執行順序 hash 不變;cache 冷/熱一致;resume vs fresh 一致
- [V-8] **防假綠 frozen list**:被改既有斷言列 `檔:line:原斷言:新行為:理由`,git diff 100% 對照
- [V-9] **三方簽核**:Claude+Codex+Composer 各獨立跑 V-3~V-7 + 親查 diff,三方皆「正確」才過(任一疑→不過)

## 覆蓋總數
P:7 / M:4 / S:4 / G:4 / R:6 / W:1 / C:2 / V:9 = **37 項**。SPEC §P 與 §V 須涵蓋全部 37 ID。
