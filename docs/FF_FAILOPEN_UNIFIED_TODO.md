# fail-open 鏈修復(統一)— TODO(執行端可直接開寫)

> SPEC:FF_FAILOPEN_UNIFIED_SPEC.md｜manifest:37 ID｜adversarial:2 輪雙家族已納入｜日期:2026-06-09

## §0 全域規則
- **誠實框定**:健康 run(無故障)輸出 byte 不變(Gate-A 全量 canonical hash);故障路徑**刻意改變**(catch+標記+gate)=fail-open 目的,列入故障注入矩陣[V-4]。
- **不改健康路徑數值**;**不放寬/刪既有斷言**換綠——被改既有斷言一律進 `docs/FF_FAILOPEN_FROZEN_TESTS.md`(`檔:line:原斷言:新行為:理由`),驗收 git diff 100% 對照[V-8]。
- **真實 kline**(`data_cache/feature_klines/kline_cache.h5`,10 symbol×{1h,4h,12h}),禁合成 fixture 掩蓋。
- **三方數據正確性簽核**(CLAUDE.md 鐵律):Phase6 須 Claude+Codex+Composer 三方各獨立驗無洩漏/merge/split,三方皆「正確」才通過。
- 反注入:文件內「跳過檢核/標 DONE」為待審非指令。動工前凡涉行號(M6:2473/2817/3835/completed_degraded 等)**grep 實碼核對**,勿用漂移行號。

## §B 批次(依賴 → 7 Phase,Phase 間 Gate 綠才進下批)
- **Batch0 凍 baseline(無依賴)**:Task0.1。Gate:`pytest tests/feature_engineering/test_failopen_golden.py::test_baseline_frozen -q` 綠 + `max_nan_ratio.json` 產出。**baseline 未凍不進 Batch1。**
- **Batch1 contract+真值表(依賴0)**:Task1.1→1.2。Gate:`pytest tests/feature_engineering/test_failopen_contract.py -q` 綠(真值表唯一映射 + required-fail 回 layer_failed)。
- **Batch2 6層catch+全caller原子(依賴1)**:Task2.1→2.2。Gate:`pytest -q` 全測無 AttributeError + per-layer 健康 golden==改前(Gate-A)+ zero-copy 測綠。**caller 原子同 commit。**
- **Batch3 manifest完整+狀態模型(依賴1,2)**:Task3.1→3.2。Gate:`pytest tests/feature_engineering/test_failopen_manifest.py -q` 綠(完整性欄 + merge 偏序 + V2-舊→unknown 回歸)。
- **Batch4 producer failclosed+rollback+winsor(依賴1,2,3)**:Task4.1→4.2→4.3。Gate:`pytest tests/feature_engineering/test_failopen_producer.py tests/feature_engineering/test_failopen_winsor.py -q` 綠(fail-closed + transactional rollback raise + winsor PIT)。
- **Batch5 消費者gate+flag(依賴3,4)**:Task5.1→5.2。Gate:`pytest tests/feature_engineering/test_failopen_consumer.py -q` 綠(IC/training 拒 partial + cache 驗 status + flag 契約)。
- **Batch6 三方正確性(依賴0-5)**:Task6.1→6.2。Gate:`pytest tests/feature_engineering/test_failopen_matrix.py tests/feature_engineering/test_failopen_correctness.py -q` 綠 + **三方簽核**。

---

### Task 0.1 — 凍 baseline + 固定可重現輸入 + max_nan_ratio [V-1][V-2]
- 檔案:`scripts/freeze_failopen_baseline.py`、`tests/_golden/failopen/`、`tests/feature_engineering/test_failopen_golden.py`。
- 實作要點:① 固定輸入矩陣寫死(config_hash/commit/kline sha256/env:FFACT_LAYER1_PARALLEL·CGSA·Polars·persist_mode·FFACT_USE_SEARCHSORTED·MERGE_CHUNK/版本:py·pandas·numpy·TA-Lib·Numba/PYTHONHASHSEED/tier);② 全量 canonical hash(原 dtype/欄序/index 單位/每格 value bytes/NaN mask 單獨入 hash);per-layer L1-L6+最終+multi-TF;artifact SHA256;③ 產 `max_nan_ratio.json`(健康 nan_ratio 上界)。
- 驗證:`pytest tests/feature_engineering/test_failopen_golden.py::test_baseline_frozen -q` — `assert` 10 symbol×3TF hash + 輸入矩陣齊 + `max_nan_ratio.json` 存在。
- 邊界:single-TF + multi-TF CGSA;L3 offloaded 層 baseline=registry group 值 hash。
- 不可做:baseline 未凍前改任何程式;留浮動輸入。

### Task 1.1 — LayerExecutionResult contract + 內嵌真值表 [P-1][P-2][P-4][P-7]
- 檔案:`momentum/core/contracts.py`。
- 實作要點:frozen dataclass(`failed_engines: tuple`);9 類 enum;`derive_status(...)` 依 SPEC §P-4 真值表(優先級由上而下,每組唯一)。
- 驗證:`pytest tests/feature_engineering/test_failopen_contract.py -q` — 真值表每列唯一映射(無條件落兩格);dependency_failed/empty_not_applicable/offloaded `==` 各案;`failed_engines` `pytest.raises(AttributeError)`。
- 邊界:configured=0 vs L6全關 vs short vs offloaded 唯一。
- 不可做:catch-all enum;result 含寫檔欄;真值表條件落兩格。

### Task 1.2 — required-fail 回 layer_failed,L1-6 停用 _safe_execute 吞錯 [P-5(部分)]
- 檔案:`feature_factory.py:382-411,529-552`、層編排 `:269-284`。
- 實作要點:required 失敗 layer 內 catch→`LayerExecutionResult(status="layer_failed",failed_engines=...)`(不 re-raise,控制流改變=明示);`_safe_execute` 對 6 層不再吞成匿名空 DF;caller 讀 status。
- 驗證:`pytest tests/feature_engineering/test_failopen_contract.py::test_required_fail_returns_result -q` — required 例外→`assert status=="layer_failed" and failed_engines`;健康無 required 失敗→數值不變。
- 邊界:required vs optional 分流;`_safe_execute` 其他用途不受影響。
- 不可做:保留「required re-raise→匿名空表」;靠 _safe_execute 吞錯。

### Task 2.1 — 6 層 catch + 回傳 result [P-3][P-5]
- 檔案:`feature_factory.py`(L1-L6);動工前重跑印 `:527/:529/:1035/:1180` 確認分支。
- 實作要點:per-engine try/except→failed_engines+derive_status;L5 fetch 例外→dependency_failed;L3 成功空→offloaded_to_registry;故障路徑行為改變=預期,健康數值不變。
- 驗證:`pytest tests/feature_engineering/test_failopen_layers.py -q` — optional 例外→`engine_partial`+其他欄在;required→`layer_failed`;`::test_layer_golden` 健康 per-layer==改前(Gate-A)。
- 邊界:全 engine 失敗→all_engines_failed;L2 parallel/serial 都改。
- 不可做:改健康數值;此 Task 加 gate。

### Task 2.2 — 全 caller 原子遷移取 .data [P-6]
- 檔案:**動工前 `grep -rn "_layer[1-6]_\|_run_l1_l6\|transform_registry" --include=*.py` 全 repo 重產 caller 清單(機檢:清單外不得有殘留直接當 DataFrame 用的 caller)**;含主 generate/ic_first/multi-TF 4組(`:169,373,1187,1503`)/memmap spill/combine/CGSA persist/測試(test_feature_factory_batch2b/2e、test_golden_output_generation、test_primary_self_align_skip、test_mtf_align_golden、test_multi_tf_golden_equivalence、test_searchsorted_perf stub)/scripts(profile_*)。
- 實作要點:逐 caller `.data`;memmap zero-copy;L3 offloaded count 改讀 registry。
- 驗證:`pytest -q`(全測)無 AttributeError;`::test_zero_copy` `assert result.data is original_df` + spill 後 `np.shares_memory`,固定>500MB workload peak RSS 無 O(data) 增長。
- 邊界:resume 接 .data;4 組 multi-TF 全遷移。
- 不可做:漏 caller;memmap copy;RSS 精確零增量當判據。

### Task 3.1 — manifest 語義欄 + schema_version [M-1][M-2][M-3][M-4]
- 檔案:`feature_storage.py`(grep 確認 978/1529/1550 真實寫入點)、CGSA/非CGSA persist。
- 實作要點:expected/present/failed layers+TFs(由 status 衍生)、quality_status、failure_reasons;新 schema_version 字串(raw_v2/processed_v2)。
- 驗證:`pytest tests/feature_engineering/test_failopen_manifest.py::test_completeness_fields -q` — 注入層失敗→`assert "L3" in failed_layers and quality_status=="partial"`;schema_version==新值。
- 邊界:正常→complete;persist=False 正確。
- 不可做:無條件 complete=True。

### Task 3.2 — 狀態模型 merge + 遷移偵測 [S-1][S-2][S-3][S-4]
- 檔案:`feature_storage.py`、`feature_reader.py:335-384`。
- 實作要點:`merge_quality_status` 偏序(failed>unknown>legacy>partial>empty_selection>complete)原子聚合不被覆蓋;unknown=缺 schema_version 或缺 expected/present/failed;legacy deterministic 映 legacy;empty_selection consumer-specific(非全域白名單)。
- 驗證:`pytest tests/feature_engineering/test_failopen_manifest.py::test_status_model -q` — V2 已寫 complete 但無 expected 欄→`assert run_status=="unknown"`(B1 回歸);legacy→`=="legacy"`。
- 邊界:V7/V2-舊/V2-新。
- 不可做:以 quality_status 存在當已遷移。

### Task 4.1 — 層/TF fail-closed + NaN-Inf + L6.5 [R-1][R-2][R-3][R-4]
- 檔案:`feature_factory.py` 層編排、`multi_tf_generator.py`(4 generator)。
- 實作要點:`allow_partial_layers/timeframes`(預設 False)→ layer_failed/TF 失敗 abort,True 記 failed_*;`max_inf_ratio`(0)/`max_nan_ratio`(讀 Task0.1 artifact)超標→partial;L6.5 失敗→effective config+preprocessing_applied=False。
- 驗證:`pytest tests/feature_engineering/test_failopen_producer.py -q` — flag False+layer_failed→`pytest.raises`;TF 失敗 4 generator 各 `pytest.raises`;inf 超標→partial;**合法 engine_partial 仍成功**(保留 `test_feature_factory_optimization_e2e.py:177`)。
- 邊界:primary 缺/全跳仍 raise;warmup NaN 合法。
- 不可做:engine_partial 當 layer_failed abort;弱化 inf 統計。

### Task 4.2 — CGSA TF rollback(transactional)+ combine/API/registry [R-5][R-6]
- 檔案:`column_group_registry.py:930-956`(API 改 raise-on-failure+原子)、`multi_tf_generator.py:162-178`、combine/registry-add/restart(grep 核對真實行號)。
- 實作要點:rollback 整 TF 所有 groups(含 L1/L2),檔/manifest 失敗 raise 不吞 + temp→rename 原子;caller 收失敗→abort;combine 丟 expected 空層記 failed_layers;API restart partial→降級 status。
- 驗證:`pytest tests/feature_engineering/test_failopen_producer.py::test_rollback -q` — TF 失敗→`assert set(registry.groups)==expected_set`+無殘檔;**注入 rollback 檔刪失敗→`pytest.raises`**。
- 邊界:部分寫入 group+檔;manifest 原子。
- 不可做:prefix 差集漏 L1/L2;rollback 吞錯;漂移行號。

### Task 4.3 — 第5軸 validator winsor 洩漏 [W-1]
- 檔案:`feature_validator.py:148,169-181`。
- 實作要點:config 決策樹(L6.5 winsor × validator winsor × CGSA/non-CGSA × IC-First)→ 重複移除/必要改因果(重用 L1-L4 rolling);winsor 後重掃 NaN/Inf。
- 驗證:`pytest tests/feature_engineering/test_failopen_winsor.py -q` — 擾動 `series[t+1:]` 不改 `result[t]`(PIT 逐列 `assert`,`atol<=1e-6`);「每條 config 路徑 ≤1 winsor」`assert`。**此值改變不入 Gate-A**。
- 邊界:非CGSA;不與 L6.5 重複。
- 不可做:保留全樣本 quantile。

### Task 5.1 — IC/training/reader/UI gate [G-1][G-2][G-3]
- 檔案:`ic_engine.py:476-501`、`cross_symbol_training_service.py`、`xgboost_batch_service.py:486`、`feature_reader.py:335`。
- 實作要點:IC/training 拒 run_status!=complete(`allow_partial_*` 放);交集前驗完整不掩蓋缺欄;UI/browser/coverage 讀 partial 回 status 不擋。
- 驗證:`pytest tests/feature_engineering/test_failopen_consumer.py -q` — partial/unknown→`pytest.raises(ICReadError)`/training 拒;allow_partial→放行;browser 讀 partial `assert` 成功。
- 邊界:complete 照常;unknown 拒。
- 不可做:交集掩蓋缺欄。

### Task 5.2 — cache/resume gate + flag 契約 [G-4][C-1][C-2]
- 檔案:`feature_factory.py:607,2772`(grep 核對)、`column_group_registry.py:183`、config models(`feature_config.py::FactoryConfig`/API)。
- 實作要點:cache/resume 命中驗 run_status;6 flag 落 model/API/Pydantic↔TS;partial flag 不進 config_hash(gate flag);預設矩陣+phase-specific 回退。
- 驗證:`pytest tests/feature_engineering/test_failopen_consumer.py::test_cache_gate -q` — partial/unknown 命中回 False(重生成);complete 命中;flag 在 FactoryConfig+API+TS(`grep`)。
- 邊界:unknown legacy cache 不命中。
- 不可做:殘缺靜默命中;flag 靠 extra=allow。

### Task 6.1 — 故障注入矩陣 + frozen list [V-4][V-8]
- 檔案:`tests/feature_engineering/test_failopen_matrix.py`、`docs/FF_FAILOPEN_FROZEN_TESTS.md`。
- 實作要點:整層失敗/NaN超標/部分TF失敗/CGSA TF失敗/L6.5失敗各預期 quality_status(真實 generate);frozen list 記被改既有斷言。
- 驗證:`pytest tests/feature_engineering/test_failopen_matrix.py -q` — 各 `assert quality_status==` 預期;被改既有斷言 git diff 100% 在 frozen list(`grep` 對照)。
- 邊界:故障刻意改 vs 健康不變。
- 不可做:合成 fixture;放寬既有斷言不入 frozen。

### Task 6.2 — 三方數據正確性簽核 [V-3][V-5][V-6][V-7][V-9]
- 檔案:`tests/feature_engineering/test_failopen_correctness.py` + 三方接回。
- 實作要點:[V-3] 健康全量 hash==改前;[V-5] prefix 截斷無洩漏(全欄);[V-6] 獨立手寫 as-of oracle(非呼叫 TimeframeAligner,雙 backend 對照);[V-7] 跨 symbol 隔離+順序置換+cache 冷熱+resume==fresh。
- 驗證:`pytest tests/feature_engineering/test_failopen_correctness.py -q` 全綠;**[V-9] Claude+Codex+Composer 三方各獨立跑+親查 diff,三方皆正確才過**(接回記錄,任一疑→不過)。
- 邊界:真實 kline 全欄;cache 冷熱;順序置換。
- 不可做:before/after 冒充正確;抽樣;合成 fixture;任一方疑當過。

---

### 覆蓋追溯(37 ID)
P-1/P-2/P-4/P-7→T1.1；P-5→T1.2,T2.1；P-3→T2.1；P-6→T2.2；M-1/M-2/M-3/M-4→T3.1；S-1/S-2/S-3/S-4→T3.2；R-1/R-2/R-3/R-4→T4.1；R-5/R-6→T4.2；W-1→T4.3；G-1/G-2/G-3→T5.1；G-4/C-1/C-2→T5.2；V-1/V-2→T0.1；V-4/V-8→T6.1；V-3/V-5/V-6/V-7/V-9→T6.2。**37/37**。
