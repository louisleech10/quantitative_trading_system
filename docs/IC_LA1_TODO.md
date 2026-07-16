# IC-LA-1(P1) TODO —（v2.3｜基於 `docs/IC_LA1_SPEC.md` v0.4.3（frozen,sha `41499dae…`）｜2026-07-16｜R1 adversarial 8 BLOCKING+MAJOR 已修,見 `handoffs/LA1-TODO-ADV-RECONCILE.md`）

> 冷啟動合約:執行端只讀本檔即可逐 Task 寫碼;衝突時以凍結 SPEC 為準(需改 SPEC=BLOCKED 上報)。
> 憲法:`AGENTS.md` + CLAUDE.md「Multi-Agent 協作協議/驗證保真度鐵律/三方數據正確性簽核鐵律」。

## §0 全域規則與約束
1. **環境**:`source venv/bin/activate`;**測試域=`tests/momentum/` + `tests/api/` + `frontend/`(npm)**;「禁 run_api.py」語意=任何測試不得依賴啟動中的伺服器(tests/api 用 TestClient)。真實 kline=`data_cache/feature_klines/kline_cache.h5`(唯讀;group key 格式 `/{SYMBOL}/{tf}/data`;`BTCUSDT/1h` rows=20352 sha₁₆=`1c93c37938a4917a`、`ETHUSDT/12h` rows=1696 sha₁₆=`00d1ee985ad3f09f`),**禁合成 fixture**。
2. **兩輪斷路器**:任何 bug/test/疑問兩輪解不了 → `STATUS: BLOCKED` 上報,禁 solo 硬幹。
3. **禁**:weaken NaN/inf gate;per-t 降 q;config percent 整數直灌 fraction 參數;放寬/刪既有斷言換綠(Task 2.2 migration 表除外);改 `passed_features` 型別;fallback raise/fail-closed;kmeans 當 golden control;擴 scope 碰 FR(`factor_return_analyzer.py`)或 `_fit_global`;私自重編 SPEC oracle 編號。
4. **§MS**:min_samples=COUNT;valid⟺effective_count≥m;bin/regime 分配統一 m=100;long_short 模組門檻 30 保留(兩層)。
5. **RULING-3**:fallback 仍出報表不 raise;本票只加可觀測性(root 紅標),不改數學出口。
6. **每 Task 完成**:列改動檔+新/改測試 nodeid+實跑輸出摘要;pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 每次 revert。
7. **commit/review 節奏**:每批(B0/B1/B2/B3/B4)過 Codex+Composer 雙家 review 後由編排端 commit;實作者不自審。
8. **回退(SPEC §R)**:每批獨立 commit 可單獨 revert;逃生旗標=`grouped_analysis.by_regime`/`LongShortAnalysisConfig.enabled`(既有,預設 ON 不改,僅作緊急逃生口);golden control FAIL→不 merge。
9. **行號=輔助錨**:本檔行號皆附函式名;行號漂移時以函式名為準,漂移>20 行→BLOCKED 上報。

## §B 批次執行策略（DAG：B0 → {B1,B2,B3 可並行} → B4;修改 legacy 輸出的批次一律不得早於 B0）
| 批 | 內容 | 依賴 | 批內順序(鎖死) |
|----|------|------|----------------|
| B0 | baseline+allowlist predeclare+測試骨架 | 無 | 0.1→0.2→0.3 |
| B1 | regime PIT(rule+fallback+kmeans)+**pit_stats 兩改** | B0 | 1.1→{1.2,1.3}→1.4 |
| B2 | long_short PIT | B0+**Task 1.1(pit_stats 檔序列化,避免並行衝突)** | 2.1→2.2 |
| B3 | fallback loud | B0 | 3.1→3.2→3.3 |
| B4 | mutation 全家+golden+歸因+三方簽核 | B1,B2,B3 | 4.1→4.2 |

**allowlist predeclare 流程(§G 相容)**:B0=schema+空 rows(宣告 class_enum);B1/B2/B3 各批完成時把**該批預期 diff** append 進 allowlist(隨批 review 一起審);B4 validator 驗 unlisted=FAIL。「擅擴」定義=B4 開始後或未經雙家 review 的 append。

## Phase B0 — §G Baseline 凍結（依賴:無）
### Task 0.1 — `tests/golden/la1/gen_baseline.py` 可重現改前 baseline
- **入口契約(LA-0 級,直接以 `tests/golden/la0/gen_baseline.py` 為模板)**:`ICFilterOrchestrator.analyze(features_path, labels_path, meta_path, kline_reader=…)`;inputs=features/labels HDF5+meta JSON(`symbol/timeframe/config_hash`+per-feature 條目);kline group key=`/{SYMBOL}/{tf}/data`;沿用 LA-0 的 `_canonical_json_bytes/_sha256_*/_hash_float_array/_hash_bool_array/_hash_string_set` helpers 與 `_isolate_orchestrator_persist`(persist 導 tmp,防污染 data_cache)。
- 內容:凍結**五**路徑 legacy 輸出:①regime rule grouped IC(config override:`grouped_analysis.by_regime=True`+`report.include_regime_analysis=True`+`regime_method="rule"`)②kmeans grouped IC(`regime_method="kmeans"`)③`RegimeDetector.detect_phases_for_index(close, volume)`(XGBoost 路徑,經 `momentum.factories.create_regime_detector(n_clusters=4, lookback=55)`)④long_short(`LongShortAnalysisConfig.enabled=True`,num_quantiles=5)⑤fallback(短樣本觸發 `insufficient_data`)。
- baseline 內容(SPEC §G 逐項):per-regime grouped IC(high/low/bull/bear)+long_short 聚合(long/short ic/mean_return/recommendation/num_quantiles_used)+regime mask 成員 hash+**名稱集合 sha256+每量 value hash+NaN mask hash**+early-flip 分層 manifest(兩側可測翻轉)。
- canonical mutation 常數內嵌(SPEC §G):M-trunc=`n_keep=int(0.75*n)`;early window=`[0,int(2/3*n_keep))`;mid-segment trunc=`prev_end+REFIT_INTERVAL//2`。
- 驗證:`python tests/golden/la1/gen_baseline.py --check` exit 0(內含三類 assert:①§0.1 兩 input sha 重驗 ②manifest early-flip 集合兩側 len>0 ③baseline JSON 五路徑鍵齊全——任一不符 exit 1)。
- 邊界:短樣本(觸發 fallback)、全 warmup 標的。
- 不可做:合成 fixture;aggregate-only;動 data_cache;呼叫尚未存在的新 API。
### Task 0.2 — allowlist predeclare + validator
- 內容:`tests/golden/la1/attribution_allowlist.json`(schema=`schema_version`+`class_enum ["P1-1","P1-1b","P1-1c","P1-2","P1-3-obs"]`+`rows: []`(B0 時點空,見 §B 流程))+ **validator=`tests/golden/la1/attribution_validator.py`**(diff vs allowlist:unlisted=FAIL;row 格式=exact JSON path+index+old/new discriminator)。
- 驗證:`python -c "import json; json.load(open('tests/golden/la1/attribution_allowlist.json'))"` exit 0;`pytest tests/golden/la1/test_attribution_validator.py`:空 diff PASS、未列 diff FAIL、格式錯 row(缺 path/index)FAIL 三測。
- 邊界:rows 空=合法(B0 時點)。
- 不可做:填實際 diff(B1-B3 隨批 append);只寫 class 名不綁 path。
### Task 0.3 — `tests/momentum/test_la1_lookahead.py` 骨架(解雞蛋)
- 內容:建骨架檔+全部 B1-B4 nodeid 以 `pytest.mark.skip(reason="LA1-B<n> pending")` placeholder:`test_regime_pit`(parametrize:rule/kmeans/mid_segment)、`test_regime_pit_empty_vol`、`test_regime_fallback_truth_table`、`test_long_short_pit`、`test_long_short_fixed_q`、`test_return_nan_mask_invariance`、`test_fallback_loud_and_status`。fixture 讀 Task 0.1 inputs。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py --collect-only -q` collect==**9**(7 function;`test_regime_pit` parametrize rule/kmeans/mid_segment=3 items,其餘 6 各 1;多/少皆 FAIL);`pytest tests/momentum/test_la1_lookahead.py -q` 全 skip 0 fail。
- 邊界:collect 不觸 data_cache 副作用。
- 不可做:寫實測邏輯(各批填);nodeid 命名偏離本表。

## Phase B1 — regime PIT（依賴:B0;批內 1.1→{1.2,1.3}→1.4）
### Task 1.1 — pit_stats 兩改:wrapper + `require_full_q`
- 內容:`momentum/Analysis/pit_stats.py` ①新增 `pit_expanding_quantile_thresholds(series, lo_q, hi_q, min_samples=MIN_SAMPLES) -> tuple[pd.Series, pd.Series]`(內部呼 `pit_expanding_bounds`,零新演算法)+regime 契約測試鎖 warmup=(-inf,+inf)(mutation:改回 NaN 必打紅)②`pit_expanding_qcut_label(series, q, min_samples=MIN_SAMPLES, require_full_q=False)` 加參數:True 且 per-t `nunique(bins)<q`→當根 NaN;**預設 False=舊行為**(LA-0 caller 零回歸)。
- 驗證:`pytest tests/momentum/test_pit_stats.py` 全綠(既有 35+新增);`-k quantile_thresholds` 與 bounds 零 diff(atol=1e-12);`-k require_full_q`:2-unique×q=5,t≥100→isna(True 時)/label==0.0(False 時)兩斷言。
- 邊界:空序列、全 NaN、lo_q≥hi_q(raise)、恰 q 個 unique。
- 不可做:改 bounds/qcut 既有行為;動其他原語。
### Task 1.2 — P1-1 `ic_engine._compute_regime_groups_rule` PIT(SPEC B1.1)
- 內容:`ic_engine.py` 函式 `_compute_regime_groups_rule`(def :1089;洩漏行 :1106-1107 nanpercentile)。vol 因果不變;`lo_q=low_pct/100.0, hi_q=high_pct/100.0`(config `regime_definitions.{low,high}_vol_percentile` 預設 20/80=**合法 percent**);**驗界**:`low_pct<0 or high_pct>100 or low_pct>=high_pct → raise InvalidInputError`;`(lo_t,hi_t)=pit_expanding_quantile_thresholds(vol, lo_q, hi_q, min_samples=100)`;`high_vol=vol>=hi_t`、`low_vol=vol<=lo_t`。bull/bear 不動。空 vol guard(:1103-1105 `vol_values.empty→return {}`)保留。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit -k rule -q`(exit 0)(M-trunc→early high/low mask flip 改前>0 改後==0;bull/bear diff==0 atol=1e-12);**以下三項皆為同測試(rule case)內部斷言,由上列命令一次覆蓋**:①hand-calc 小序列(n=120)expanding p20/p80 對照 numpy quantile;`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit_empty_vol -q`(exit 0)——assert `analyze 輸出 by_regime=={}`;②percent 轉換:config 80(int)→內部門檻==`np.quantile(vol_prefix, 0.8)`(合法,禁 raise);③非法界:config `{low:110}` 或 `{low:50,high:30}`→`pytest.raises(InvalidInputError)`。
- 邊界:vol 全 NaN(→{})、len(close)<55、warmup 全期。
- 不可做:改 bull/bear;殘留全域門檻;把 80 直灌 fraction 參數。
### Task 1.3 — P1-1b `regime_detector._fallback_rule_based` PIT(SPEC B1.2)
- 內容:`regime_detector.py` 函式 `_fallback_rule_based`(hardcode :306-307)→wrapper(lo_q=0.20,hi_q=0.80,m=100)。**真值表**:①`len(vol_values)<2`→全 `"unknown"`②warmup(effective_count<100)→high/low=False,bull/bear/mid 照舊(**不得 unknown**)③非 warmup→PIT 門檻。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py::test_regime_fallback_truth_table -q`(exit 0)——三列各至少一斷言(len<2 全 unknown/warmup bar label in {mid_vol_ranging,bull 家族}/非 warmup==PIT 手算);M-trunc early flip 改後==0。
- 邊界:全 NaN vol、恰 100 樣本。
- 不可做:動 `detect()` kmeans 主幹(Task 1.4)。
### Task 1.4 — P1-1c kmeans Segment-causal(SPEC B1.3 偽碼全文照抄)
- 內容:`regime_detector.py` `_fit_expanding`(def :214)+`_align_labels`(def :259)。**SPEC 偽碼全文(不壓縮,逐行實作)**:
  ```
  REFIT_INTERVAL = REFIT_INTERVAL_CONST(=50, config 可調;禁依最終 n 推導)
  warm_up      = min_samples_for_fit
  refit_points = list(range(warm_up, n, REFIT_INTERVAL)); 末段補 n
  for 段 [prev_end, end_idx) in refit_points 切分:
      if prev_end < min_samples_for_fit:                    # 含首段 prev_end=0
          labels[prev_end:end_idx] = B1.2_PIT_rule(該段)     # 委派 Task 1.3 真值表
          continue
      scaler_t, model_t = kmeans.fit( valid_df[0:prev_end] )
      prefix_raw = model_t.predict( scaler_t.transform(valid_df[0:prev_end]) )   # same-model re-predict
      name_map   = align_by_vol( prefix_raw, vol[0:prev_end] )
      labels[prev_end:end_idx] = name_map( model_t.predict(scaler_t.transform(段)) )
  ```
  段內 predict 出現 map 未涵蓋 raw id→`"unknown"`(map 不回頭擴充)。config key=**`regime_kmeans.refit_interval`**(新增,default 50,進 `ic_config_schema.py` `RegimeKmeansConfig`;傳遞鏈:schema→`ic_engine._compute_regime_groups_kmeans`(:1139 kmeans_cfg)→`RegimeDetector.__init__` 新參數)。**禁 IC/XGBoost 傳 `expanding=False`**:`detect()` 加 assert(或 caller 兩處 assert)+`_fit_global` 不動(§N exclude)。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit -k kmeans -q`(exit 0;M-trunc early label flip 改後==0)+`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit -k mid_segment -q`(exit 0;mid-segment trunc→early-in-segment flip==0,以固定 refit 段界 [50,100,150,…] 為對照鍵);**同測試(kmeans case)內部斷言**:`detect_phases_for_index` 改前/改後對照 diff 寫入歸因(P1-1c,非阻擋)+`expanding=False`→`pytest.raises`;selection 防呆=`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit --collect-only -q`(collect==3,rule/kmeans/mid_segment 各 1,防 -k 全 deselect)。
- 邊界:單 cluster、段內新 raw id(→unknown)、恰在 refit 點截斷、prev_end=0。
- 不可做:動 `_fit_global`;段尾/全期命名;用歷史 raw_labels 建 map(必 same-model re-predict)。
### Task 1.5 — B1 批尾:該批預期 diff append 進 allowlist(§B 流程)
- 內容:P1-1/P1-1b/P1-1c 造成的 baseline diff(regime membership/kmeans 命名/XGBoost phase)逐筆填 `attribution_allowlist.json`(exact path+index+old/new),class 歸 {P1-1,P1-1b,P1-1c}。
- 驗證:`pytest tests/golden/la1/test_attribution_validator.py` PASS(該批 diff 全 listed;control 路徑 0 diff)。
- 邊界:diff 數 0(僅當該路徑真無變化,需說明)。
- 不可做:塞 control 路徑 diff;歸錯 class。

## Phase B2 — long_short PIT（依賴:B0+Task 1.1;批內 2.1→2.2）
### Task 2.1 — `long_short_analyzer` PIT 分箱(SPEC B2.1)
- 內容:`long_short_analyzer.py`。①**feature 原時序分箱(RB-3)**:`analyze()`(:27-93)重排——bins=`pit_expanding_qcut_label(feature.dropna() 僅自身 NaN, q=use_quantiles, min_samples=100, require_full_q=True)`,**禁**現行 :33-36 `concat(feature,future_returns).dropna()` 後才 :44-45 分箱;分箱後 reindex 對齊 finite future_returns 只算 metrics ②刪 `_assign_quantiles_with_fallback`(:191-210)全域降 q ③`num_quantiles_used=use_quantiles`(固定)④`batch_analyze`(:95-116)同改 ⑤recommendation enum {雙向交易,只做多,只做空,不建議}(`_recommendation` :179-189 不動,新增:空側/IC 全 NaN 路徑必落"不建議")。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py::test_long_short_pit -q`(exit 0;M-trunc early bin/long_mask flip 改前>0 改後==0);`pytest tests/momentum/test_la1_lookahead.py::test_return_nan_mask_invariance -q`(exit 0;竄改未來報酬 NaN 分布→bins 逐元素相等,不等=FAIL);`pytest tests/momentum/test_la1_lookahead.py::test_long_short_fixed_q -q`(exit 0;n≥200→`num_quantiles_used==5`);reduced-bin 斷言(2-unique×q=5→該根 isna+該側空+recommendation=="不建議")=`pytest tests/momentum/test_la1_lookahead.py::test_long_short_pit -q` 同測試內部 case,由該命令覆蓋(exit 0)。
- 邊界:常數尾端(legacy 降 q 觸發點)、warmup 全 NaN、單 bin、2-unique×q=5、**重複 timestamp(qcut duplicates,§V)**——duplicate index 輸入→分箱不炸且 per-t 語意保持(斷言輸出長度==輸入長度)。
- 不可做:改 `_compute_side_metrics` 描述統計;per-t 降 q;analyzer 端另做 full-q 檢查(單軌=`require_full_q`)。
### Task 2.2 — 既有測試 migration(SPEC B2.1 表 6 列)+ B2 allowlist append
- 內容(nodeid→新預期):`test_insufficient_ls_samples`→不變;`test_quantile_exceeds_samples`(q=10,n=60,含 :23 `>=2`)→SkippedResult("cannot form quantiles");`test_both_sides_negative_ic`→fixture n≥200 斷言不變;`test_empty_side`→該側 NaN+recommendation=="不建議";`test_asymmetric_quantile_def`→固定 q 重寫;新增 `test_long_short_fixed_q`(Task 2.1 已建)。B2 預期 diff(recommendation/num_quantiles_used/samples)append allowlist(class P1-2)。
- 驗證:`pytest tests/momentum/Analysis/test_long_short_analyzer.py -q` 全綠且 collect==5;validator PASS。
- 邊界:migration 後無 xfail/skip 殘留。
- 不可做:放寬其他斷言;刪測試。

## Phase B3 — fallback loud（依賴:B0;批內 3.1→3.2→3.3）
### Task 3.1 — root 紅標 + 禁內層 persist(SPEC B3.1)
- 內容:`ic_filter_orchestrator.py`。①root:`report["analysis_status"] ∈ {"ok_oos","degraded_full_sample"}`+`report["oos_guarantees"]: bool`(root 鏡像)②`_run_full_sample_fallback`(def :1033)加 `logger.warning`(reason/train_rows/test_rows/min_test_rows/fit_mode)③**禁內層 persist**:context flag 跳過 `_persist_outputs`(:2988 附近呼叫點),唯一寫出=wrapper 加 root 欄位後 ④正常路徑寫 `"ok_oos"` ⑤`summary_table[]` 每列 `pass_class`(degraded="full_sample_research_only";觸點=`_apply_thresholds`(:3150+)與 summary 組裝處)。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py::test_fallback_loud_and_status -q`(exit 0)——注入 fallback→`caplog` 含 warning+`report["analysis_status"]=="degraded_full_sample"`+`report["oos_guarantees"] is False`+內層無檔案落地(tmp 目錄 file count==wrapper 寫出 1 次);非觸發路徑:metadata 外 deep-equal+`=="ok_oos"`+`oos_guarantees is True`。
- 邊界:insufficient_data/rolling_warmup_insufficient 兩觸發源;cache-hit 紅標不丟。
- 不可做:raise;改數學出口;欄位雙軌;動 `passed_features` 型別。
### Task 3.2 — SPEC 五 oracle 逐出口 gate(編號逐字沿用 SPEC B3.1)
- 內容+測試落點(`tests/api/test_ic_la1_degraded_gate.py`,TestClient 不啟伺服器):
  | SPEC oracle | 實作 | 命名測試 |
  |---|---|---|
  | ① `summary_table` top-ICIR | degraded 時每列 `pass_class!="oos"` | `test_summary_table_pass_class_gate` |
  | ② `filter_log.stage5_thresholds.output_features` | degraded 時附 `pass_class`/degraded 標 | `test_filter_log_output_features_gate` |
  | ③ filtered HDF5 | `ic_reporter.py` writer 寫 `analysis_status` attr | `test_hdf5_attr_gate` |
  | ④ `generate_ai_json` top_features | degraded 時 OOS 文案 fail-closed(research-only 標) | `test_ai_json_oos_text_gate` |
  | ⑤ API 三出口 carrier | HDF5 FileResponse=檔內 attr;CSV=header `X-Analysis-Status`+檔首註解行;transforms=`ApplyTransformsResponse.analysis_status`+輸出 HDF5 attr | `test_api_hdf5_carrier`/`test_api_csv_carrier`/`test_api_transforms_carrier` |
  另:task payload(`ic_analysis_service.py` completion 組裝 :246-252)含 root 紅標→`test_task_payload_status`。`api/models/ic_models.py` response schema 加 `analysis_status`。
- 驗證:`pytest tests/api/test_ic_la1_degraded_gate.py -q` 全綠且 collect==**16**(8 gate 測試+8 對應**負例測試**);負例=可重放 mutation:每 gate 一支 `test_<oracle>_missing_marker` 以 fixture 構造「degraded 但缺標」的 report/檔案;**唯一 oracle=gate 檢測 helper 一律 raise 自訂 `DegradedOOSViolation`**(定義於 `momentum/Analysis/ic_reporter.py` 或 orchestrator,全 8 gate 同一 exception),負例全部 `pytest.raises(DegradedOOSViolation)` 收斂(禁 return-False 雙軌、禁 meta-test)。
- 邊界:export 三 format;degraded HDF5 仍可下載。
- 不可做:重編 oracle 號;漏任一 carrier;fixture 自帶 pass_class 假綠。
### Task 3.3 — 前端(types+兩圖+banner)+ B3 allowlist append
- 內容:①`frontend/src/lib/types.ts` `ICReport` 加 `analysis_status?`/`oos_guarantees?`(optional,舊 artifact 相容)②`GroupedICBarChart.tsx`(函式內 `?? 0`,現 :51)/`RegimeRadarChart.tsx`(:21)缺失 IC→null/N/A ③**banner=`frontend/src/components/ic-analysis/DegradedBanner.tsx`**(store 讀 `analysis_status!=="ok_oos"` 顯示)+測試 `DegradedBanner.test.tsx`。B3 預期 diff(新 root 欄位)append allowlist(class P1-3-obs)。
- 驗證:`cd frontend && npm run build` exit 0;`cd frontend && npx vitest run src/components/ic-analysis/DegradedBanner.test.tsx`(exit 0;degraded→render,ok→null,欄位缺→null 不炸);兩圖 NaN input 測試=`cd frontend && npx vitest run src/components/ic-analysis/GroupedICBarChart.test.tsx src/components/ic-analysis/RegimeRadarChart.test.tsx`(exit 0;斷言 NaN input 無 `0` bar/point)。
- 邊界:舊報表無欄位。
- 不可做:動 debt 清單圖(`LongShortComparisonChart`/`OOSDistributionChart`);重構 store。

## Phase B4 — mutation 全家+golden+三方（依賴:B1,B2,B3;4.1→4.2）
### Task 4.1 — M-lookahead 入庫 + golden 重基準 + validator 收口
- 內容:①填實 Task 0.3 骨架全部測試(去 skip)②golden 重基準:control(regime OFF/LS OFF/非觸發 fallback)vs B0 deep-equal(atol=1e-12);修改路徑 diff 與 allowlist 逐筆對帳(B1/B2/B3 已 append,B4 只驗不加)③**wash mutations ≥5 打紅**(竄 early mask 冒充 P1-1/control 塞 diff/刪紅標稱 P1-3 closed/wrong-side swap/擅擴 allowlist)④跨 symbol 隔離(ETHUSDT/12h 獨立 baseline 對照)⑤XGBoost `detect_phases_for_index` 對照入歸因。
- 驗證:`pytest tests/momentum/test_la1_lookahead.py tests/golden/la1/ -q` 全綠 0 skip;歸因 unexpected==0(validator 輸出 machine line `UNEXPECTED=0`);**5 wash=parametrize 測試**:`pytest tests/golden/la1/test_attribution_validator.py -k wash -q` collect==5 全綠(每支對 in-memory 竄改後的 diff/allowlist 斷言 validator FAIL,`pytest.raises` 收斂=可重放,無外部 runner);control deep-equal(atol=1e-12)。
- 邊界:全 warmup 標的、恰觸發 fallback 樣本數。
- 不可做:sanitized fixture;放寬容差;kmeans 入 control;B4 期 append allowlist。
### Task 4.2 — 三方 DATA-CORRECT 簽核(編排端執行)
- 內容:Claude+Codex+Composer 獨立驗(Grok=實作者不簽);任一方有疑→不通過。
- 驗證:三方各附實跑 receipt=`pytest tests/momentum/test_la1_lookahead.py tests/golden/la1/ -q`(exit 0)+validator 輸出 `UNEXPECTED=0`+`pytest tests/golden/la1/test_attribution_validator.py -k wash -q`(collect==5 exit 0);簽核文件三份入 handoffs/。
- 邊界:任一方 BLOCKED→兩輪斷路器交委員會。
- 不可做:確認式簽核(至少一腿 explicit adversarial);實作者代跑 receipt。

## SPEC ID 100% 覆蓋追溯表(一錨點一列)
| SPEC 錨點 | TODO 落點 |
|---|---|
| §RISK(大/a,b,c,d/adversarial 必跑) | 本檔頭+§0.7 雙家 review+Task 4.2 三方 |
| §A r1 nanpercentile 行號 | Task 1.2 |
| §A r2 P1-1 leak receipt | Task 0.1 manifest+Task 1.2 mutation |
| §A r3 P1-2 leak receipt | Task 0.1+Task 2.1 mutation |
| §A r4 P1-3 silent receipt | Task 3.1 caplog |
| §A r5 原語簽名 | Task 1.1 |
| §A r6 雙閘 | Task 0.1 config override |
| §A r7 P1-1b hardcode | Task 1.3 |
| §A r8 min_samples/first_valid 154 | §0.4+Task 1.2(m=100) |
| §A r9 P1-1c align_labels | Task 1.4 |
| §A r10 oos 只寫不讀 | Task 3.1/3.2 |
| §A r11 reduced-bin 非 NaN | Task 1.1(require_full_q)+2.1 |
| §A r12 caller 圖(xgboost/lightgbm) | Task 1.4 XGBoost 對照;LightGBM 無 Task(0 hits) |
| §C RULING-3 | §0.5+Task 3.1 |
| §C §MS/雙 min_samples | §0.4+Task 2.1 |
| §C consumer debt(`??0`) | Task 3.3(兩圖)+不可做(debt 圖) |
| §C 禁令(NaN gate/降 q/percent/defer) | §0.3 |
| §G input receipt/canonical mutation | §0.1+Task 0.1 |
| §G baseline 三 hash+manifest | Task 0.1 |
| §G control/修改路徑分界 | Task 4.1 |
| §G 歸因 schema+≥5 wash | Task 0.2+4.1+§B predeclare 流程 |
| §G B3 OOS-gate 斷言 | Task 3.2 |
| §P B0.1(五路徑) | Task 0.1 |
| §P B1.1(PIT/percent 驗界/空 vol Opt-A/wrapper D3) | Task 1.1+1.2 |
| §P B1.2(真值表) | Task 1.3 |
| §P B1.3(偽碼/same-model/refit 公式/expanding=False/XGBoost 對照/§N _fit_global) | Task 1.4 |
| §P B2.1(RB-3 原時序/Policy-Strict/降 q 移除/num_quantiles_used/migration/rec enum) | Task 2.1+2.2 |
| §P B3.1(root 單名/G-A2/禁內層 persist/五 oracle/carrier/前端/task payload) | Task 3.1+3.2+3.3 |
| §P B4.1(golden/歸因/validator/跨 symbol) | Task 4.1 |
| §V mutation 條件(a/d) | Task 0.3 骨架+各批 mutation |
| §V 防假綠(migration 逐 nodeid) | Task 2.2 |
| §V 邊界:空DF/全NaN/std=0/重複timestamp/短樣本/跨symbol | Task 1.2、2.1(duplicate ts)、3.1、4.1 各邊界欄 |
| §R 每批 revert/逃生旗標/golden FAIL 不 merge | §0.8 |
| §N FR exclude | §0.3 |
| §N _fit_global exclude+expanding=False 禁令 | Task 1.4 |
| §N debt 圖清單 | Task 3.3 不可做 |
