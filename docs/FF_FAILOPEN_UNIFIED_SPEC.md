# Feature Factory fail-open 鏈修復(統一)— SPEC

> 來源:FF_FAILOPEN_AUDIT.md + UNIFIED_MANIFEST(37 ID)｜日期:2026-06-09｜TODO:待生成
> 取代 FF_FAILOPEN_FIX_SPEC(v2,暫停)與 LAYER_RESULT_SPEC(作廢合併)。
> **誠實框定**:健康 run(無故障)golden 證 byte 不變;故障路徑刻意改變(catch+標記+gate)=fail-open 目的。協議+gating 一體,跨層重構只做一次。

## §RISK 風險分級
- **大小**:大。
- **命中**:(a) 殘缺/NaN artifact 餵 ML=資料品質;(b) 改 6 層回傳型別 + manifest schema = 跨 8+ 模組共用路徑;(c) 多 phase + 改既有測試契約難回退;(d) partial/leakage 餵回測=真實性。
- §G Golden 必填(全量 canonical hash)+ adversarial 雙家族 + **三方數據正確性簽核**(CLAUDE.md 鐵律,真實 kline)。

## §A 假設與待使用者確認
- **已驗證事實(實測,含 `kline_cache.h5` 與 `feature_factory.py` 行號)**:
  - 真實 kline `data_cache/feature_klines/kline_cache.h5`:10 symbols × {1h,4h,12h},OHLCV+taker/quote/trades(h5py 實讀)。
  - `_safe_execute`(`:382-411`)`except→pd.DataFrame()`,無 configured/required 資訊;層編排 `:269-284` 直接當 DataFrame 用。
  - L1 **optional** engine 例外被吞(`:527`),**required** engine **re-raise**(`:529-535`,serial `:544`);L2 parallel `continue`(`:1035`)、serial 無 per-category catch(`:1014`);L3 CGSA streaming 成功回空(`:1136`);L5 空多成因含 reference fetch 例外(`:1180-1246`);L6 sub-engine 全關(`:1308`);L2 blacklist 清空(`:960-967`)。
  - manifest **雙層** `quality_status`:`feature_storage.py:1529`(artifact)+`:1550`(run)+`:978`(CGSA stream 固定 "complete");既有值含 `empty_selection`(`:1057`)、`legacy`(`feature_reader.py:354,367,384`);IC/Reader 已 gate `complete` 布林但被源頭錯標+legacy 強制 complete 繞過。
  - multi-TF **4 組** direct caller:serial `:169`、parallel `:373`、legacy `:1187`、worker `:1503`。
  - **動工前 Phase1/2 須各重跑印出上述分支確認**(驗證保真度鐵律)。
- **待使用者確認**:**無**(使用者 2026-06-09:委派技術 + 範圍四主軸+第5軸全包 + 合回單一任務 + 資料正確性三方簽核)。
- **已確認結果**:合回單一 fail-open 任務(2026-06-09);誠實框定(健康不變/故障刻意改);終極目標=硬性驗收(跨tier/多symbol/OOM/品質/時間/最小輸出);三方數據正確性簽核(CLAUDE.md 鐵律)。

## §C 約束
- 解耦 7 條:`LayerExecutionResult` 放 `momentum/core/contracts.py`;`grep "from api\." momentum/`→0;consumer gate 在 api 服務讀 momentum reader 給的 status。
- 不弱化既有 NaN/inf gate(本任務加強);**故障路徑行為刻意改變**(非「不變」),健康路徑 byte 不變。
- **[C-1] flag 契約**:6 flag(`allow_partial_layers/timeframes/ic/training`+`max_inf_ratio/max_nan_ratio`)定義所屬 model(`feature_config.py::FactoryConfig` engine 或 `api/core/config.py` API)、API 欄位、Pydantic↔TS 型別、作用域 per-run、是否進 config_hash(partial flag 不進、gate flag);**[C-2] 預設矩陣 + phase-specific 回退**(§R)。
- memmap zero-copy:wrap 不複製。

## §G Golden / Baseline(全量 canonical,非抽樣)
- **[V-1] 凍結時機**:Phase 0 動工前,真實 kline 10 symbol×3TF;**固定可重現輸入**:config_hash/commit SHA/kline sha256/env(FFACT_LAYER1_PARALLEL·CGSA·Polars·get_l3_persist_mode·FFACT_USE_SEARCHSORTED·MERGE_CHUNK_SIZE)/版本(py·pandas·numpy·TA-Lib·Numba)/PYTHONHASHSEED/tier;`scripts/freeze_failopen_baseline.py` 可執行;存 `tests/_golden/failopen/`。
- **[V-2] baseline 內容(全量;Codex#8 別只 hash 正規化後)**:每 symbol×TF 分開記 `sha256(① 原始 column order 序列 + ② 各欄原始 dtype + ③ index metadata(timestamp 型別+單位+name) + ④ 每格 value bytes(固定 endian/-0.0/NaN payload,**用原 dtype 非強轉 float32**) + ⑤ 完整 NaN mask)`——**dtype 與欄序單獨入 hash**(抓 float64→float32 退化/欄重排,不被 canonicalize 掩蓋);per-layer L1-L6 + 最終 L7 + multi-TF 合併;artifact 檔 SHA256(非只大小);group 集合 sha256。
- **[V-3] 通過條件(兩 gate 分離)**:**Gate-A 精確**(健康 run 行為不變):改後==改前全量 hash,任一格不同=FAIL+列 symbol/TF/layer/欄/列/diff,不抽樣不靠聚合。**Gate-A 排除清單(Codex#1 解 Gate-A vs W-1 矛盾)**:W-1 winsor 修洩漏**刻意改值的受影響欄**從 Gate-A 排除,改受 Task4.3 的 PIT 因果正確性 gate(獨立 baseline);排除欄清單明列、三方同意,非全表豁免。**Gate-B 容差**(僅浮點 reduction 必要,known 清單+理由,三方同意)。

## §P Phase 與依賴

### Phase 0 — Golden 凍結 + 可重現輸入(依賴:無)[V-1][V-2]
**Task 0.1 — 凍結改前 baseline(最終+per-layer,固定輸入)**
- 目標:程式改動前凍全量 baseline。檔案:`scripts/freeze_failopen_baseline.py`、`tests/_golden/failopen/`、`tests/feature_engineering/test_failopen_golden.py`。
- 驗證:`pytest tests/feature_engineering/test_failopen_golden.py::test_baseline_frozen -q`——`assert` 10 symbol×3TF 全量 canonical hash(最終+per-layer L1-L6)+ artifact SHA256 + 固定輸入矩陣(config_hash/env/commit/版本)齊全;**[M4] 同時產出 `tests/_golden/failopen/max_nan_ratio.json`(健康 run 各 symbol/TF 正常 nan_ratio 上界,供 R-3 `max_nan_ratio` 預設值,打破 Task4.1↔Phase0 循環依賴)**。
- 邊界:single-TF + multi-TF CGSA;L3 offloaded 層 baseline=registry group 值 hash(非空表)。
- 不可做:baseline 未凍不改任何程式;不留浮動輸入(否則無法重現對照=假綠)。

### Phase 1 — 協議 contract + 真值表(依賴:Phase0)[P-1][P-2][P-4][P-7]
**Task 1.1 — LayerExecutionResult contract + enum 真值表(B1:表格內嵌)**
- 目標:typed 結果 + 窮盡互斥 enum + **內嵌真值表**。檔案:`momentum/core/contracts.py`。
- 改法:`@dataclass(frozen=True) LayerExecutionResult(data, status, failed_engines: tuple[str,...], reason, configured_engines, present_engines, required_engines, dependency_error)`;[P-2] 9 類 enum;[P-4] `derive_status(layer, configured, present, required, blacklisted_all, offloaded, dep_exc, layer_exc)` 依下表。
- **P-4 真值表(內嵌,優先級由上而下;每組唯一映射,消除歧義)**:
  | 條件(由上而下首個命中) | status |
  |---|---|
  | layer 整體未啟用 / configured==0 | `empty_disabled` |
  | layer_exc(整層致命例外) | `layer_failed` |
  | dep_exc(外部依賴 fetch 例外,如 L5 reference fetch) | `dependency_failed` |
  | required 引擎全失敗 或 present==0 且 required>0 | `all_engines_failed` |
  | 資料列數 < 最小窗(短資料合法空) | `empty_short_data` |
  | L3 成功但值已轉 registry(streaming) | `offloaded_to_registry` |
  | configured>0 但經 blacklist/filter/reference=self/無交集 後無適用輸入(present==0,非失敗) | `empty_not_applicable` |
  | 部分 optional 引擎失敗(failed_engines 非空)但有輸出 | `engine_partial` |
  | 其餘正常 | `ok` |
  - **歧義消除**:configured==0(整層停用)優先於 L6「sub-engine 全關」→ 後者歸 `empty_not_applicable`(configured>0 但全關無輸出);第10類「blacklist 清空」已收進 `empty_not_applicable`(condition: configured>0 且 present==0 且無例外)。
- 驗證:`pytest tests/feature_engineering/test_failopen_contract.py -q`——`assert` 真值表每列唯一映射(9 status 互斥,無條件落兩格);reference fetch 例外→`dependency_failed`(`==`);L2 blacklist 清空→`empty_not_applicable`(`==`);L6 全關→`empty_not_applicable`(`==`);`failed_engines` tuple `pytest.raises(AttributeError)`。
- 邊界:configured=0 vs L6 全關 vs short data vs offloaded,各自唯一。
- 不可做:enum 不留 catch-all;result 不含寫檔欄;真值表不得有條件落兩格。

**Task 1.2 — required-fail contract:layer 回 layer_failed 不再 re-raise(B2/Codex#2)**
- 目標:閉合 required engine 失敗的傳遞模型。**現碼 required re-raise→`_safe_execute` 吞成匿名空表**(`:529-535,544,382-411`);改成 layer **catch required 失敗→回 `LayerExecutionResult(status="layer_failed", failed_engines=[...], reason=...)`**(不再 re-raise);**L1-L6 不再經 `_safe_execute` 的吞錯路徑**(該函式對這些層停用/移除,改由 caller 讀 status)。檔案:`feature_factory.py:382-411,529-552`、層編排 `:269-284`。
- 改法:① required 失敗 layer 內 catch→layer_failed result(控制流改變=明示允許);② `_safe_execute` 對 6 層不再吞成匿名空 DF(寫死:移除/旁路);③ caller 讀 `result.status`,gate(Phase4)決定 abort。
- 驗證:`pytest tests/feature_engineering/test_failopen_contract.py::test_required_fail_returns_result -q`——注入 required engine 例外→`assert result.status=="layer_failed" and result.failed_engines`(非拋到 `_safe_execute` 變匿名空表);健康路徑無 required 失敗→數值不變(Gate-A)。
- 邊界:required vs optional 失敗分流;`_safe_execute` 對非層呼叫的其他用途不受影響。
- 不可做:不保留「required re-raise→匿名空表」舊路徑;不靠 `_safe_execute` 吞錯。

### Phase 2 — 6 層 catching + 全 caller 原子遷移(依賴:Phase1)[P-3][P-5][P-6]
**Task 2.1 — 6 層 catch 失敗 + 回傳 result**
- 目標:[P-3] L1/L2 per-engine catch 記 `failed_engines`(required 仍最終 fail 但先記原因);L5 fetch 例外→dependency_failed;6 層回傳 LayerExecutionResult。檔案:`feature_factory.py`(L1-L6)。
- 改法:① 動工前重跑印 `:527/:529/:1035/:1180` 確認(§A 鐵律);② per-engine try/except→failed_engines + derive_status;③ **故障路徑行為改變=預期**(健康路徑數值不變)。
- 驗證:`pytest tests/feature_engineering/test_failopen_layers.py -q`——注入 optional engine 例外→`assert status=="engine_partial" and engine in result.failed_engines`,其他 engine 欄仍在;required 例外→`assert status=="layer_failed"`;**健康 run per-layer golden==改前**(`pytest ...::test_layer_golden`,Gate-A)。
- 邊界:全 engine 失敗→all_engines_failed;L3 offloaded;L2 parallel/serial 都改。
- 不可做:不改健康路徑數值;此 Task 不加 gate(gate 在 Phase4)。

**Task 2.2 — 全 caller 原子遷移取 .data**
- 目標:[P-6] 所有 caller 同 commit 遷移。檔案:見 manifest [P-6] 完整清單(主 generate/ic_first/multi-TF 4組/memmap/combine/CGSA persist/測試/scripts);**動工前 `grep -rn "_layer[1-6]_\|_run_l1_l6" --include=*.py` 重產確認無漏**。
- 改法:逐 caller `.data` unwrap;memmap spill 維持 zero-copy;L3 offloaded count 改讀 registry(`_collect_layer_counts`,消除漂移)。
- 驗證:`pytest -q`(全測)無 AttributeError;`pytest tests/feature_engineering/test_failopen_layers.py::test_zero_copy -q`——`assert result.data is original_df` + spill 後 `np.shares_memory(spilled.data.values, memmap_base)`,固定 >500MB workload peak RSS 無 O(data) 增長。
- 邊界:resume/retry 接 .data;4 組 multi-TF 全遷移(漏一=假綠)。
- 不可做:漏 caller;memmap 複製;RSS 精確零增量當判據。

### Phase 3 — manifest 完整性 + 狀態模型 + 遷移(依賴:Phase1,2)[M-1][M-2][M-3][M-4][S-1][S-2][S-3][S-4]
**Task 3.1 — manifest 語義欄 + schema_version**
- 目標:[M-1][M-2][M-3][M-4] 加 expected/present/failed layers+TFs、quality_status、failure_reasons;新 schema_version 字串。檔案:`feature_storage.py:978,1529,1550`、CGSA/非CGSA persist。
- 驗證:`pytest tests/feature_engineering/test_failopen_manifest.py::test_completeness_fields -q`——注入層失敗→`assert "L3" in manifest["failed_layers"] and manifest["quality_status"]=="partial"`;schema_version==新值(`==`)。
- 邊界:正常→complete、failed_* 空;persist=False 也正確。
- 不可做:不無條件 complete=True。

**Task 3.2 — 狀態模型 merge + 遷移偵測**
- 目標:[S-1][S-2][S-3] enum 全集 + `merge_quality_status` 偏序聚合;[S-4] 遷移偵測。檔案:`feature_storage.py`、`feature_reader.py:335-384`。
- 改法:`merge_quality_status(artifacts)->run_status` 偽碼:偏序 `failed>unknown>legacy>partial>empty_selection>complete`,原子 read-modify-aggregate 不被覆蓋;[S-4] `unknown` = 缺新 schema_version **或**缺 expected/present/failed(非看 quality_status 存在);legacy adapter 改 **deterministic** 一律映 `legacy`(現碼強制 complete `:354,367,384`,Codex#11)。**[S-3 修正 Codex#6]`empty_selection` 不用單一 run-status 白名單放行,改 consumer-specific policy**:browser/coverage 放行、IC/training 仍拒(空特徵集對訓練無意義),由各 consumer allow 規則決定。
- 驗證:`pytest tests/feature_engineering/test_failopen_manifest.py::test_status_model -q`——`raw=complete+processed=empty_selection`→run `==` 規則值;**V2 已寫 quality_status=complete 但無 expected 欄→`assert run_status=="unknown"`**(B1 關鍵回歸);legacy→`assert run_status=="legacy"`(deterministic 單值,非集合)且 consumer 拒。
- 邊界:V7 legacy / V2-舊 / V2-新。
- 不可做:不以「quality_status 存在」當已遷移。

### Phase 4 — producer fail-closed + rollback + 第5軸(依賴:Phase1,2,3)[R-1][R-2][R-3][R-4][R-5][R-6][W-1]
**Task 4.1 — 層/TF fail-closed + NaN-Inf + L6.5**
- 目標:[R-1][R-2][R-3][R-4]。檔案:`feature_factory.py` 層編排、`multi_tf_generator.py`(4 generator)。
- 改法:`allow_partial_layers/timeframes` 預設 False→layer_failed/TF 失敗 abort;True 記 failed_*;`max_inf_ratio`(0)/`max_nan_ratio`(Phase0 baseline 上界+裕度,SPEC 寫死值)超標→partial;L6.5 失敗→effective config + preprocessing_applied=False。
- 驗證:`pytest tests/feature_engineering/test_failopen_producer.py -q`——`allow_partial_layers=False`+layer_failed→`pytest.raises`;TF 失敗 4 generator 各 `pytest.raises`;inf 超標→`assert quality_status in {"partial","failed"}`;合法 engine_partial 仍成功(保留 `test_feature_factory_optimization_e2e.py:177` 語義)。
- 邊界:primary 缺/全跳仍 raise;warmup NaN(合法)vs 異常。
- 不可做:不把 engine_partial 當 layer_failed abort;不弱化 inf 統計。

**Task 4.2 — CGSA TF rollback + combine/API/registry [R-5][R-6]**
- 目標:[R-5] TF 失敗 rollback 整 TF 所有 groups(含 L1/L2)。**現碼 `unregister_group`(`column_group_registry.py:930-956`)先刪記憶體再吞 shard/file/manifest 的 OSError、非原子**→**擴 scope 加 transactional rollback API:失敗 raise 不吞 + manifest temp→rename 原子**;caller 收 rollback 失敗→abort。[R-6] combine 丟 expected 空層記 failed_layers、API restart partial→降級 task status、registry add 失敗依 flag。**M6:`unregister_group`/combine/registry-add/restart 的真實函式名與行號動工前 grep 核對,勿用漂移行號(2473/2817/3835/completed_degraded 須實碼確認)**。
- 驗證:`pytest tests/feature_engineering/test_failopen_producer.py::test_rollback -q`——注入 TF 失敗→`assert registry.groups == expected_set`(集合相等)+ `assert` 無 4h npy/parquet 殘檔;API restart partial→`assert task_status=="completed_degraded"`。
- 邊界:部分寫入 group + 磁碟檔;rollback 後 manifest 原子一致。
- 不可做:prefix 差集漏 L1/L2;留孤兒檔。

**Task 4.3 — 第5軸 validator winsor 洩漏 [W-1]**
- 目標:`feature_validator.py:169` 全樣本 quantile winsor=look-ahead → config 決策樹判保留/移除/改因果 + winsor 後重掃 NaN/Inf。檔案:`feature_validator.py:148,169-181`。
- 改法:決策樹(L6.5 winsor on × validator winsor on × CGSA/non-CGSA × IC-First)→ 重複則移除、必要則改因果(重用 L1-L4 rolling)。
- 驗證:`pytest tests/feature_engineering/test_failopen_winsor.py -q`——擾動 `series[t+1:]` 不改 `result[t]`(PIT 逐列 `assert`,`atol<=1e-6`);「每條 config 路徑 ≤1 winsor」`assert`;winsor 後 NaN/Inf 重掃。**此值改變不納入 Gate-A 凍結**(刻意修洩漏)。
- 邊界:非CGSA;與 L6.5 不重複套。
- 不可做:不保留全樣本 quantile。

### Phase 5 — 消費者 gate + cache + flag 契約(依賴:Phase3,4)[G-1][G-2][G-3][G-4][C-1][C-2]
**Task 5.1 — IC/training/reader/UI gate**
- 目標:[G-1][G-2][G-3] IC/training 拒 partial(`allow_partial_*` 才放),UI 標示不擋,reader gate 看 run_status。檔案:`ic_engine.py:476-501`、`cross_symbol_training_service.py`、`xgboost_batch_service.py:486`、`feature_reader.py:335`。
- 驗證:`pytest tests/feature_engineering/test_failopen_consumer.py -q`——partial/unknown→`pytest.raises(ICReadError)`/training 拒;`allow_partial_ic=True`→`assert` 放行;browser 讀 partial `assert` 成功且回 status;交集前驗完整不掩蓋缺欄。
- 邊界:complete 照常;unknown 預設拒。
- 不可做:交集階段掩蓋缺欄。

**Task 5.2 — cache/resume gate + flag 契約 [G-4][C-1][C-2]**
- 目標:[G-4] cache/resume 命中驗 run_status;[C-1] flag 契約落 model/API/TS;[C-2] 預設矩陣+回退。檔案:`feature_factory.py:607,2772`、`column_group_registry.py:183`、config models。
- 驗證:`pytest tests/feature_engineering/test_failopen_consumer.py::test_cache_gate -q`——partial/unknown artifact 命中檢查回 `False`(重生成);complete `assert` 命中;flag 在 FactoryConfig + API + TS 型別存在(`grep`)。
- 邊界:unknown legacy cache 不命中。
- 不可做:殘缺靜默命中;flag 靠 `extra=allow`。

### Phase 6 — 三方數據正確性驗證(依賴:Phase0-5)[V-3][V-4][V-5][V-6][V-7][V-8][V-9]
**Task 6.1 — 故障注入矩陣 + 防假綠 [V-4][V-8]**
- 目標:[V-4] 故障注入各自預期;[V-8] frozen list。檔案:`tests/feature_engineering/test_failopen_matrix.py`、`docs/FF_FAILOPEN_FROZEN_TESTS.md`。
- 驗證:`pytest tests/feature_engineering/test_failopen_matrix.py -q`——整層失敗/NaN超標/部分TF失敗/CGSA TF失敗/L6.5失敗各 `assert quality_status==` 預期(真實 generate 非合成);被改既有斷言 `git diff` 100% 在 frozen list(`grep` 對照)。
- 邊界:故障路徑刻意改變 vs 健康不變。
- 不可做:合成 fixture;放寬既有斷言不入 frozen。

**Task 6.2 — 三方數據正確性簽核(真正確性,非只沒變)[V-3][V-5][V-6][V-7][V-9]**
- 目標:三方各獨立驗無洩漏/merge/split。檔案:`tests/feature_engineering/test_failopen_correctness.py` + 三方接回。
- 驗證:`pytest tests/feature_engineering/test_failopen_correctness.py -q`——
  - [V-3 健康不變] 改後==改前全量 hash(`==`);
  - [V-5 無洩漏] prefix 截斷:截尾端 N 根,前綴每欄每格 `==` 未截版(全欄非抽樣)+ 既有 PIT 清單綠;
  - [V-6 merge] **獨立手寫 as-of oracle(M3/Codex#7:非複製 TimeframeAligner 公式)**:從**原始時間戳 + timeframe duration 獨立逐列選取** maximal eligible source row,獨立定義 bar availability(source_close≤decision_time)、open/close decision boundary、exact-boundary、首列無來源、gaps、duplicate;**兩 backend(searchsorted/merge_asof)都對照同一 oracle**;欄值逐格 `==` oracle;合併後 index 與 primary 完全相等(順序/重複/長度/dtype/timestamp 單位);
  - [V-7 split] 多 symbol 改前後一致 + 打亂 symbol/TF 順序 hash 不變(`==`)+ cache 冷/熱一致 + resume==fresh;
  - [V-9 三方] Claude+Codex+Composer 各獨立跑 + 親查 diff,三方皆「正確」才過,接回記錄(任一疑→不過)。
- 邊界:真實 kline 全欄;cache 冷熱;順序置換。
- 不可做:before/after 一致冒充「正確」;抽樣代全欄;合成 fixture;任一方疑當過。

## §V 驗證策略與邊界測試目錄
- 層級:單元(contract/enum 真值表)、整合(層+caller)、Golden(健康 byte 級全量)、故障注入矩陣、三方正確性(無洩漏/merge/split)、邊界。可獨立 `pytest` 跑。
- **防假綠**:diff 既有斷言進 frozen list;改既有 fail-open 斷言對應「故障路徑刻意改變」+理由;Gate-A 容差不放寬。
- **邊界目錄**:空DF(empty_disabled)/全engine失敗/短資料/dependency例外/CGSA offloaded/memmap大array(zero-copy)/多symbol隔離/4 generator/cache冷熱/resume/API restart/legacy unknown manifest。

## §R 回退(phase-specific matrix)
- 每 Phase 獨立 commit 可 revert。flag 預設矩陣:`allow_partial_layers/timeframes/ic/training`=False、`max_inf_ratio`=0、`max_nan_ratio`=baseline 上界+裕度;UI 永遠可讀。**schema 不可靠 flag 回退**(新 schema_version 已寫不因關 flag 變回)→ 回退配 migration(reader 讀新欄、舊 consumer 容忍)。Golden Gate-A FAIL→不 merge;Phase0 未凍→不進 Phase1。
- 健康路徑與故障路徑分離:flag 全開=近似舊 fail-open 行為(緊急回退)。

## §N N/A 登記
- 無省略必填段(§RISK/§A/§C/§G/§P/§V/§R 全填)。
