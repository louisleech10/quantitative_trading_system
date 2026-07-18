# IC1C-FR-FULL — canonical 單標的因子擇時多空報酬序列重建 — TODO

> 對應 SPEC:`docs/IC1CFR_FULL_SPEC.md` **v0.6 FROZEN**(+v0.6.1 EXPANDING FINAL+v0.6.2 修正 pit_stats 複用自撞) | 起草 Claude 2026-07-18 | **狀態:✅ FROZEN(2026-07-19;三家 codex+composer+grok RECONCILE-STAMP APPROVED,`reconcile_stamps_check.sh` PASS body sha256:5c95551a;R1→R2→R3→R3.1 四輪 adversarial 收斂;reconcile=handoffs/1cFRFULL-TODO-ADV-R1-RECONCILE.md)**
> 分工:Grok 實作 / Codex+Composer 雙家 review(每批) / 三方 DATA-CORRECT(a,d)。批次階梯 F0→F1→F2→{F3,F4}→F5;同批兩輪斷路器換手。
> 行號鎖定(rg 2026-07-18):sanitizer reporter `ic_reporter.py:{405,408,495,498,546,549,626,629,683,686,796,799,1187,1189}`;reporter sharpe 鍵 `ic_reporter.py:981-984`;service `ic_analysis_service.py:{35,502,789,1334}`、conditional `1358-1360`;`_run_factor_return@1990`、`_run_net_ic@2259-2275`、cache key `1910-1939`(orchestrator);`compute_factor_returns@25`、`compute_batch@166`、`_assign_quantiles_with_fallback@198`(factor_return_analyzer);`FactorReturnConfig@187`(ic_config_schema,現無 warmup/min_samples 欄);`net_ic_analyzer.batch_analyze@183-190`(現 `del factor_returns`);前端 `icAnalysisStore.ts:{81,108,135,154}`(factor_return:false)、`page.tsx:808`(命中「Factor Return/分位收益」);`pit_stats.pit_expanding_qcut_label@311`(MIN_SAMPLES=100,count-based)。

## §0 前置原則(gate 錨點)
- **解耦(baseline-delta,D4;機械 comparator R2 補)**:`momentum/` 不 import `api/`(R1);跨域 Protocol(R2);factories(R3);config 單源(R5);`pytest tests/momentum/` standalone(R6)。**gate=不新增違規**:`check_decoupling.sh` 現況 baseline **紅**(R2=1/R3=17/R4=2 pre-existing 債,另票)→**機械驗收命令(寫死,codex R2-2)**:`bash scripts/check_decoupling.sh 2>&1 | grep -oE 'R2=[0-9]+ R3=[0-9]+ R4=[0-9]+'` 輸出**必須 == `R2=1 R3=17 R4=2`**(B0.1 凍 `handoffs/ic1cfr_full_baseline/decoupling_baseline.txt`;final gate diff 該檔,計數增=FAIL、減=允許並更新 baseline);**不得**要求全綠、亦不得默認忽略。
- **不可違反**:禁 fake data;不弱化 NaN/inf gate;不動 `data_cache/`;不縮窗/刪特徵換速度;真實 kline `data_cache/feature_klines/kline_cache.h5`(禁合成當正確性 oracle)。
- **PIT 鐵律**:主序列 `ls_return_full = position × future_return`(raw identity,winsorize 已移除 v0.6);分位=**PIT expanding**(RULING-FINAL,rolling→未來另票)、禁 full-sample qcut;每批附 M-lookahead(截未來 bar→早期輸出不變,可證偽)。
- **正名鐵律**:輸出/UI/export 稱「單標的因子擇時多空」;禁冒充橫截面;schema `semantics:"single_asset_factor_timing_ls"`。
- **回退**:每 Phase 獨立 commit 可 revert;enabled ON 整體 gate=F0+F2+F3+F4 全綠才開。

## §G-NOTE — golden 與 min_samples test seam(D1/D17)
- **production 不弱化**:`compute_factor_returns` 全序列 gate `_min_samples`(現 30)保留;新增 `FactorReturnConfig.min_samples:int=Field(default=30,ge=2)` 使**可配置**(預設 30 不變)。
- **synthetic 7-bar golden 走 test-config**:測試建 analyzer `min_samples=2, warmup_periods=2, num_quantiles=3` 跑 7-bar(不弱化 production 預設);**另**獨立 numpy/pandas reference(測試內,不經 analyzer 碼路)產同向量逐元素比 `abs≤1e-12`。
- **§C 演算法權威(不改凍結 §G)**:F0.1 依 §C L45 鎖定演算法**手刻**(`q_eff=min(num_quantiles,window.nunique())`、`qcut(window,q_eff,...).iloc[-1]`、top=q_eff−1/bottom=0、per-t 空邊→0、index-based warmup `t<warmup_periods`→0);**不直接複用 `pit_expanding_qcut_label`**(語意差:它 fixed-q + count-based min_samples=100 + 無 index warmup,直接用會改動凍結 §G 7-bar 向量)。**可複用**其 `effective_count`/`pit_valid_mask` 原語做 NaN/gate(不改 golden)。此分歧記於 handoffs/1cFRFULL-TODO-ADV-R1-RECONCILE.md D17。

## §B 批次與 Task

### 批 B0 — 動工前 before-full baseline 凍結(依賴:無)
**Task B0.1 — before-full baseline 凍結 + freeze profile 遷移(D19)**
- 修改檔案:`scripts/ic1cfr_stopgap_freeze.py`(擴 `--profile before-full/after-full`;既有 caller:CI/手動)。
- 實作要點:①`--profile before-full` 產 stopgap 現態(FR unavailable)+非 FR 模組 path 值→`handoffs/ic1cfr_full_baseline/before.json`+sha256;②profile 遷移表(D19,完整 flag↔profile 對照):舊 `--check-nodeids`(stopgap AST)不變沿用;新 `--profile before-full`=現態凍結;新 `--profile after-full`=F0 後 ok union 凍結+AST allowlist 追加 ok 形狀;③**凍 decoupling baseline**:`bash scripts/check_decoupling.sh 2>&1 | grep -oE 'R2=[0-9]+ R3=[0-9]+ R4=[0-9]+' > handoffs/ic1cfr_full_baseline/decoupling_baseline.txt`(§0 comparator 用)。
- 不可做:不改 analyzer 本體;before.json 不當 FULL 相等基準(值大變 scope-expected)。
- 邊界:①fixture 不存在→raise;②profile 未知→raise。
- 驗證:`source venv/bin/activate && python scripts/ic1cfr_stopgap_freeze.py --profile before-full --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/before.json && sha256sum handoffs/ic1cfr_full_baseline/before.json` exit 0;before.json 含頂層 `results` 鍵集合;FR 節=unavailable。

### 批 F0 — 計算根重建(PIT + 序列 artifact + 公式鎖)(依賴:B0)
**Task F0.1 — PIT 分位 + P1 序列(SPEC §C L44-49;D1/D7/D8/D14/D17)**
- 修改檔案:`momentum/Analysis/factor_return_analyzer.py` `compute_factor_returns@25-104`、`_assign_quantiles_with_fallback@198-217`;`ic_config_schema.py` `FactorReturnConfig@187` 加 `warmup_periods:int=Field(default=20,ge=0)`+`min_samples:int=Field(default=30,ge=2)`(進 cache key/schema)。既有 caller:`compute_batch@166`、`_run_factor_return@1990`。
- 實作要點(偽碼;§C 手刻,不改凍結 golden):
  ```
  frame = pd.concat([feature.rename("feature"), future_returns.rename("y")], axis=1).dropna()  # D7:同一 dropna frame index
  if len(frame) < self._min_samples: return SkippedResult("insufficient samples")
  returns_w = frame["y"]                                   # raw identity(winsorize 移除 v0.6)
  position = pd.Series(0, index=frame.index, dtype=int)    # D7:用 frame.index 非原 feature.index
  for t in range(len(frame)):
      if t < warmup_periods: continue                      # D-golden:index-based warmup→0
      window = frame["feature"].iloc[:t+1]
      q_eff = min(num_quantiles, window.nunique())
      if q_eff < 2: continue                                # 空邊→0(不整段skip)
      label = pd.qcut(window, q_eff, labels=False, duplicates="drop").iloc[-1]
      if label == q_eff-1: position.iloc[t] = 1
      elif label == 0:     position.iloc[t] = -1
  ls_return_full = position * returns_w                     # index=frame.index
  ls_cumulative  = (1+ls_return_full).cumprod()-1
  long_short_mean_return = float(ls_return_full.mean()); active_bar_count = int((position!=0).sum())
  ```
- 不可做:不接橫截面;不改 monotonicity 本體;不用 full-sample qcut;**不恢復任何 winsorize**;不直接複用 `pit_expanding_qcut_label`(§G-NOTE;SPEC v0.6.2 已同步修正)。**舊 full-sample helper `_assign_quantiles_with_fallback@198` 刪除或私有化為 PIT 迴圈內部 helper(composer-14:禁留雙路徑)**,`rg -n '_assign_quantiles_with_fallback' momentum/` 驗證無 full-sample 呼叫殘留。
- 邊界(≥2):①`t<warmup_periods`→0;②`q_eff<2`(ties)→0 不整段 skip;③post-warmup 全無 ±1 或有效列<min_samples→SkippedResult;④NaN dropna 後不足→SkippedResult(不靜默)。
- 風險緩解:R-lookahead/R-pos/R-nan。
- 驗證(可證偽,測試檔 `tests/momentum/Analysis/test_factor_return_analyzer.py` **新建**):`pytest tests/momentum/Analysis/test_factor_return_analyzer.py -q`——`test_golden_7bar`(test-config min_samples=2)`position==[0,0,-1,1,0,-1,1]`+`ls_cumulative` `abs≤1e-12` vs numpy reference;`test_index_subset`(時間不相交/NaN fixture)→輸出 index⊆frame.index、`nan_mask` exact、非 RangeIndex 等長。mutation 見 §V-matrix。

**Task F0.2 — 序列 artifact + ok schema + 鍵名 + descriptive 標註(SPEC §C L51-52;D9/D14/D18)**
- 修改檔案:`factor_return_analyzer.py`(新 dataclass `FactorTimingReturnSeries`)、`compute_batch@166`(回 ok §U union);`ic_reporter.py:984` `"sharpe"`→`"sharpe_ratio"`(D9)。既有 caller:orchestrator/net_ic/trend/reporter。
- 實作要點:①internal artifact `FactorTimingReturnSeries(feature:str, ls_return:pd.Series, position:pd.Series, index_policy:str)`;②external §U `{status,value{schema_version:"fr_full_v1",semantics:"single_asset_factor_timing_ls",quantile_fit:"pit_expanding",return_transform:"identity",turnover_semantics:"abs_delta_position_p1",warmup_periods:<int>,features:{<name>:{long_short_mean_return,ls_cumulative_sampled,risk_metrics{sharpe_ratio},active_bar_count,turnover,quantile_summary{...,descriptive_full_sample:true}}}},reason:null}`(D18 標 descriptive);③analyzer 出 `sharpe_ratio` **且** reporter:984 讀 `sharpe_ratio`(D9 兩端同步);④`index_policy` 型別=str 枚舉、hash canonical encoding(D14:value/index 序列化規格鎖 ISO8601+float64 bytes)。
- 不可做:不重用 legacy `FactorReturnLegacyMap` 名於 ok 路徑;不 scalar 廣播成 series;不留 reporter 讀 `sharpe` 舊鍵。
- 邊界:①單 vs 多 feature;②某 feature SkippedResult→不入 features、其餘正常。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_analyzer.py -q`——`isinstance(artifact.ls_return,pd.Series)`+index=DatetimeIndex;analyzer 鍵 `sharpe_ratio`==reporter 讀取鍵(`test_reporter_sharpe_key_aligned`);ok union 頂層含 `schema_version`+`warmup_periods`。

**F0 Phase Gate**:`--profile after-full` 首次重凍 `after_full.json`+sha256(SPEC §G L62 硬順序);§V-matrix 全 mutation 可證偽;decoupling baseline-delta 不增。

### 批 F1 — runner 接線 + series owner + 預設 ON(依賴:F0)
**Task F1.1 — `_run_factor_return` 真計算 + series in-memory owner(SPEC §P F1.1;D2/D16)**
- 修改檔案:`ic_filter_orchestrator.py` `_run_factor_return@1990`(raise→factory+`compute_batch`;走 R3);**新增 owner** `self._factor_return_series: dict[str,FactorTimingReturnSeries]`(F1.1 寫,F4 讀)。既有 caller:`_run_deep_analysis`。
- 實作要點:①移 raise/stub;`create_factor_return_analyzer`+`compute_batch(selected_features)`→§U ok union;②**存 series owner(產出 API 唯一鎖定,grok R2-1/codex R3)**:analyzer 暴露 **`get_series_map() -> dict[str, FactorTimingReturnSeries]`**(唯一方式,**不改 `compute_batch` 回傳簽名**以免破既有 caller;`compute_batch` 內部 populate,`get_series_map` 取最近一次批次結果);orchestrator 於 `_run_factor_return` 呼 `analyzer.compute_batch(...)` 後 `self._factor_return_series = analyzer.get_series_map()`(同一 cleaned DatetimeIndex;runner ordering=factor_return 先於 net_ic;cache/force-merge 時 series owner 一併重建或 invalidate——cache hit 無 series→F4 讀不到→net_ic 走 unavailable 不得崩);③F1 出口暫經 sanitizer;**F1 只斷言內部 artifact ok,不斷言 `module_summary.factor_returns=="completed"`(D16:completed 斷言移 F2 後)**。
- 不可做:不繞 factory 直 import(破 R3);不在 F1 動 sanitizer 判準;F1 不宣稱 API/completed ok。
- 邊界:①selected_features 空→SkippedResult+owner 不寫該 name;②force run vs tier-gated。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_analyzer.py -k orchestrator -q`——force run 內部 artifact `status=="ok"`+有限葉;`self._factor_return_series[name].ls_return` is pd.Series(`test_series_owner_reachable`)。

**Task F1.2 — 四處 tier truth table 接線(enabled 維持 False;SPEC §A②/§C L54①②;D13)**
- 修改檔案:`ic_config_schema.py` `FactorReturnConfig@187`(**本批 enabled 仍 False**;僅補 tier 接線)、`config/ic_config.yaml`、`api/models/ic_models.py`(單數 `factor_return`)、`frontend/src/store/icAnalysisStore.ts:{81,108,135,154}`;`_apply_tier_config`。既有 caller:tier 解析、orchestrator `:1943 return bool(config.factor_return.enabled)`。
- 實作要點:①**enabled 本批維持 False**(codex R3-BLOCK:default-ON 半態 runtime 鎖=**flip 延到 F5.2**,即 F0+F2+F3+F4 全綠後才由 F5.2 單一 commit 改 `enabled=True`;不用 runtime gate 檔,用**批次順序**當機械鎖——F1.2 只接 tier 骨架,`:1943` 消費點屆時自然生效);②**tier truth table(D13,逐 field exact;tier 選中且 enabled=True 時才入 run)**:
  | tier | factor_return |
  |------|---------------|
  | foundation | **false**(輕量,不含) |
  | intermediate | **true** |
  | advanced | **true** |
  | custom/default request | **true** |
  ③**整體 ON=批次順序機械鎖(codex R2-8/R3;無 runtime gate 檔)**:F1.2 `enabled=False`;flip=F5.2 單一 commit(F0+F2+F3+F4 全綠後);`:1943` 消費點屆時生效。§R 一鍵回退=revert F5.2 commit。
- 不可做:不把驗過工作藏預設關閉(feedback_no_default_off,但本批未驗完故暫 False 合理);不改 data_cache;不 foundation 誤開;**F1.2 不得逕改 enabled=True(半態)**。
- 邊界:①intermediate request+enabled=True(F5.2 後)→factor_return 模組**入 run**;②enabled=False(F1.2~F4)→stopgap unavailable;③foundation→不含 factor_return。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_analyzer.py::test_tier_truth_table -q`——四 tier×`enabled` 矩陣逐格 assert(mock enabled=True 時 foundation 仍不含);**F1.2 後 `config.factor_return.enabled is False`**(`test_f12_enabled_still_false`);**定向 rg(修 grok R2-2 假紅)**:`rg -n 'factor_return:\s*(true|false)' frontend/src/store/icAnalysisStore.ts` 四命中僅 foundation=false。

### 批 F2 — sanitizer §U discriminator + reporter unwrap + 全出口(依賴:F1)
**Task F2.1 — sanitizer discriminator + 全出口 unwrap + export(SPEC §C L54④⑤⑩⑬⑭⑮⑯;D10/D16)**
- 修改檔案:`momentum/Analysis/factor_return_sanitizer.py`(discriminator+冪等);`ic_reporter.py` 觸點 `{405-408,495-498,546-549,626-629,683-686,796-799,1187-1189}`+新 `_unwrap_factor_returns()`;**`momentum/Analysis/ic_filter_orchestrator.py` `_sanitize_deep_report_factor_returns@1998`(呼叫點 @1902/1908;codex R2-3/composer-3:orchestrator 出口同套 discriminator,ok union 不得被擋)**;`api/services/ic_analysis_service.py:{502,789,1334}`+conditional `_CONDITIONAL_METRIC_KEYS@1358-1360`(⑯);cache `_compute_deep_cache_key@1910-1939` 加 `schema_version`;export `tests/api/test_export_api.py`+`tests/momentum/test_export_formats.py`(D10 ⑭)。
- 實作要點:①discriminator:ok union(有 status+schema_version)→放行+unwrap `.value.features`;無 status 裸 map→擋(新 reason `legacy_misaligned_factor_return_shape`,⑬);②全枚舉出口套 `_unwrap_factor_returns()`;③`assert_no_finite_in_factor_returns_subtree` 對 ok union **豁免**(僅 legacy 裸 map 斷言,⑮);④cache hit/force-merge 用 schema_version 重算或 invalidate(⑩);⑤**completed 斷言在此上線**(D16:F1 半態→F2 completed);⑥serializer conditional 三鍵 §U 形狀守恆(⑯)。
- 不可做:不誤擋 ok union;hot loop 不 log;不破冪等。
- 邊界:①ok union 二次 sanitize=冪等;②cache 命中舊 schema→invalidate;③legacy 裸 map→擋+新 reason。
- 驗證:`pytest tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py tests/momentum/test_export_formats.py -q`——A=ok §U→保留有限葉+summary 三欄 `is not None`+`module_summary.factor_returns=="completed"`;B=無 status 裸 map→無有限葉(擋);ok payload 經**全枚舉出口(含 orchestrator @1902/1908)逐一 assert**後 `status=="ok"`;**ok-reason 契約測試(codex R2-7)**:`test_ok_reason_null`——ok union `reason is None` 且全出口後不得出現 `ls_returns_timestamp_misaligned`(⑬:ok 路徑禁舊 reason);CSV/export ok 形狀更新;mutation M-unwrap/M-key 見 §V-matrix。

### 批 F3 — 前端上架 + 正名(依賴:F2)
**Task F3.1 — FactorReturnChart ok 路徑 + 正名 + page(SPEC §C L54⑥⑫;D5)**
- 修改檔案:`frontend/src/components/ic-analysis/FactorReturnChart.tsx`、`frontend/src/lib/types.ts`(§U ok 形狀)、`FeatureTierPanel.tsx`/`DeepAnalysisConfigPanel.tsx`、**`frontend/src/app/ic-analysis/page.tsx`(:808 正名,D5)**;Equity 圖保持 unavailable。既有 caller:ic-analysis page。
- 實作要點:①ok 路徑繪 `ls_cumulative_sampled`+title 含「單標的擇時」;②types.ts §U discriminated union;③全 user-facing label/help/card(含 page.tsx:808)改「單標的因子擇時多空」;④Equity unavailable 空態。
- 不可做:不接 Equity→P1(另票);不留 `Factor Return`/`分位收益` user-facing 文案。
- 邊界:①ok union→繪 7 點;②legacy 裸 map→空態警示不繪。
- 驗證:vitest `frontend/src/components/ic-analysis/FactorReturnChart.test.tsx`(**新建/擴**)三 test 名 `renders_ok_series`/`legacy_finite_payload_rejected`/`equity_stays_unavailable`(fixture=SPEC §P F3 L99 寫死 ok union,含 `return_transform:"identity"`);`npm --prefix frontend run build` 綠;`rg -n "Factor Return|分位收益" frontend/src/components/ic-analysis frontend/src/app/ic-analysis/page.tsx` user-facing 0 命中(內部 module key 除外)。

### 批 F4 — net_ic breakeven/profitable 回填(依賴:F0-F2)
**Task F4.1 — `_run_net_ic` PIT series 交接 + breakeven(SPEC §C L50;D2/D6)**
- 修改檔案:`ic_filter_orchestrator.py` `_run_net_ic@2259-2275`(讀 `self._factor_return_series`,D2);`net_ic_analyzer.py` `batch_analyze@183-190`(新簽名收 series,移除 `del factor_returns`)。既有 caller:deep analysis。
- 實作要點:①`_run_net_ic` 從 `self._factor_return_series[name]` 取 `gross=ls_return`、`position`;②turnover series=**`position.diff().abs().fillna(0.0)`**(D6:首 bar=0,非 NaN-drop)雙邊;③`batch_analyze` 用 series 算 `net_factor_return`、`breakeven_cost_bps=mean(gross)/mean(turnover)*10000`(align dropna;`mean(turnover)==0`→unavailable)、`profitable_after_cost=(mean(net)>0)`、`evaluable_count`;④cost_enabled=False→守 1c SCHEMA_GROSS_ONLY。
- 不可做:不用 top-only turnover;不恢復 Archived「Net IC=0」;不 scalar 廣播當分子;不 `del factor_returns`。
- 邊界:①`turnover.mean()==0`→unavailable;②首 bar turnover=0(exact);③series NaN dropna 後不足→unavailable。
- 驗證:`pytest tests/momentum/Analysis -k net_ic -q`+`tests/api/test_ic_deep_analysis.py`——合成 gross_mean=0.001/turnover_mean=0.5→`breakeven_cost_bps==20.0`(±1e-9)+三鍵 `status=="ok"`+`evaluable_count>0`;`turnover.mean()==0`→unavailable;`test_turnover_first_bar_zero`(`[0,0,-1,1]`→turnover `[0,0,1,2]`);API E2E 注入 ok P1→serializer 三鍵非 unavailable(後端層);M-turnover 見 §V-matrix。

**Task F4.2 — NetICChart 三鍵接線 + 驗證(codex R2-10/R3/composer-12;依賴 F4.1+F3)**
- 修改檔案:`frontend/src/components/ic-analysis/NetICChart.tsx`(**須實接**——實測現況**不讀** `breakeven_cost_bps`/`profitable_after_cost`/`net_factor_return`,codex R3:F4.2 非只加測、須接線)、`frontend/src/lib/types.ts`(三鍵 §U 形狀)、`NetICChart.test.tsx`(既有 T4 cost wiring 測試沿用+新增三鍵測)。既有 caller:ic-analysis page。
- 實作要點:①NetICChart 讀 §U 三鍵:`breakeven_cost_bps`(ok/unavailable)、`profitable_after_cost`(bool)、`net_factor_return`;②ok→顯示 breakeven 值+profitable 標記;unavailable(turnover=0)→空態文案(沿用現有 `shows_no_data` 樣式);③不破既有 T4 cost wiring 測試。
- 不可做:不改 NetICChart cost-request 語意(T4);不接 Equity;不代入 0 造假(沿用現有 `shows_no_data_when_turnover_missing` 精神)。
- 邊界:①三鍵全 ok→繪 breakeven;②breakeven unavailable→空態非 spinner。
- 驗證:`npm --prefix frontend test -- NetICChart`——既有 T4 測全綠(不回歸)+新 `renders_breakeven_ok`/`breakeven_unavailable_empty_state` 綠;`rg -n 'breakeven_cost_bps|profitable_after_cost' frontend/src/components/ic-analysis/NetICChart.tsx` 有命中(證實接線)。

### 批 F5 — 測試/freeze/quarantine 反轉(依賴:F0-F4)
**Task F5.1 — stopgap 測試改寫 + after-full 重凍 + quarantine(SPEC §C L54⑧⑨;D15/D19)**
- 修改檔案:`tests/momentum/Analysis/test_factor_return_stopgap.py`(舊斷言→新斷言表,每條註記為何舊錯)、`scripts/ic1cfr_stopgap_freeze.py`(after-full profile+AST allowlist 重凍)、`scripts/phase29_perf_validation_tmp.py`(quarantine 解除,D15 exact path)、`tests/phase24/`(加 M-pos/M-lookahead 證偽測,D15 exact path)、`config/ic_config.yaml`。
- 實作要點:①三態測試改寫(unavailable→ok,每條註記);②after-full AST allowlist 重凍;③quarantine 解除(系列正確後);④phase24 mutation 存在且改回舊行為 FAIL;⑤**TrendAnalyzer N/A 一致性測(codex R2-9)**:`tests/momentum/Analysis/test_factor_return_analyzer.py::test_trend_dimension_consistent`——config `dimensions` 含 `factor_return` 但 payload 無 `factor_return_trend`=一致通過(或移除該 default dimension,二選一實作端鎖定並註記)。
- 不可做:不刪既有斷言假綠;不 commit `tests/golden/l65/test_inventory.txt`;不 skip/xfail 遮蓋。
- 邊界:①改寫斷言 diff 有註記;②mutation 改回舊行為→FAIL。
- 驗證:`pytest tests/momentum/Analysis/test_factor_return_analyzer.py tests/momentum/Analysis/test_factor_return_stopgap.py -q` 綠;`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids`(after-full)exit 0;`tests/phase24/` M-pos/M-lookahead 改回舊行為 FAIL。

**Task F5.2 — enabled=True 最終 flip(批次順序機械鎖;codex R3;依賴 F0+F2+F3+F4 全綠)**
- 修改檔案:`ic_config_schema.py` `FactorReturnConfig.enabled`→**True**、`config/ic_config.yaml`、`api/models/ic_models.py`、`frontend/src/store/icAnalysisStore.ts`(intermediate+ tier default 對齊 True;foundation 仍 false)。既有 caller:orchestrator `:1943`。
- 實作要點:**單一 commit**(整份 TODO 最後一個功能 commit),前置=F0/F2/F3/F4 各 Phase Gate 綠+§V-matrix mutation 紅 receipt 齊;flip 後 `:1943` 消費點使預設 request 走 FR ok 路徑。
- 不可做:不在 F0-F4 任一批提前 flip(半態);flip commit 不夾帶其他邏輯改動(純預設值,易 revert)。
- 邊界:①flip 後預設 request→`module_summary.factor_returns=="completed"`;②revert 此 commit→回 stopgap unavailable(§R 逃生口)。
- 驗證:flip 後跑 final gate(§DATA-CORRECT)全綠;`test_enabled_true_after_flip`——`config.factor_return.enabled is True`+預設 request completed;`git show --stat` 此 commit 僅動預設值檔(無邏輯檔)。

## §V-matrix — mutation 可證偽矩陣(D3/D5/D8;RISK-HIT a,d 必附)
全 nodeid **repo-relative 完整路徑寫死(codex R2-1)**;每 mutation 以「in-test reference/雙實作對照」形式常駐(非改 production 後手動跑),TEST_DESIGN_CHARTER §B1.1:
| mutation | 測試檔::nodeid(完整) | 竄改(in-test 變體實作) | 期望 | oracle |
|----------|----------------|------|------|--------|
| M-pos | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_pos` | in-test 重現 reset_index+iloc 位置相減變體 | 變體輸出≠reference(assert 不等=綠;若相等=FAIL 抓不到) | 7-bar numpy reference+real-kline `position_hash` |
| M-lookahead | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_lookahead` | in-test full-sample qcut 變體 | 截未來 bar 後變體早期 position 變、PIT 版不變 | PIT 不變式 |
| M-winsorize-regress | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_winsorize_regress` | in-test winsorize 變體 | 變體 `ls_return` hash≠raw 鎖定 hash | real-kline `ls_return_value_hash` |
| M-mid | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_mid` | in-test 中間分位非 0 權重變體 | 變體 `long_short_mean_return`≠reference(D8) | 7-bar reference |
| M-key | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_key` | in-test 模擬 reporter 讀 `sharpe` 舊鍵 | 讀值 None(偵測) | reporter summary 三欄 |
| M-unwrap | `tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_unwrap` | in-test 不 unwrap `.value.features` | summary null(偵測) | reporter summary |
| M-turnover | `tests/api/test_ic_deep_analysis.py::test_mutation_turnover` | in-test top-only turnover 變體 | 變體 breakeven>雙邊版(偏樂觀,assert 嚴格大於) | breakeven_cost_bps |
- real-kline hash 產生/比對命令(寫死):`source venv/bin/activate && python scripts/ic1cfr_stopgap_freeze.py --profile after-full --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/after_full.json`;mutation 施於 production 碼→重跑→hash 分歧=FAIL(基線→變異紅 receipt 存 handoffs)。引 `docs/TEST_DESIGN_CHARTER.md §B1.1/B4`。

## §DATA-CORRECT — 三方簽核(F0-F5 全綠後,scope a,d;D11/D12)
- 真 kline;**cross-symbol/TF isolation(D11;fixture 具體化 codex R2-5,已實測 kline_cache.h5 確有)**:主 `ic_api_real_kline`(ETHUSDT/12h)+**第二 symbol=`BTCUSDT/12h`+第二 TF=`ETHUSDT/4h`**(fixture 擴參數化 loader `load_real_kline(symbol,timeframe)`,cache key manifest 各自獨立);**順序置換**(BTC 先跑後 ETH 結果 hash 不變)+**故意混 key fail case**(以 BTC series 配 ETH key 餵 comparator→必 FAIL 證明隔離檢查真的在看);`handoffs/ic1cfr_full_baseline/DATACORRECT-{claude,codex,composer}.md` 各簽:①PIT 無前瞻(M-lookahead 實跑紅);②value/index hash 逐元素;③跨 symbol/TF 隔離(第二組實跑);④正名無橫截面冒充。**三方全簽才過;任一方有疑→不通過**。
- **final gate(D12;0 skip/xfail 機械化 codex R2-4;`set -euo pipefail` 防吞錯 codex R3)**:
  ```
  set -euo pipefail                                    # codex R3-BLOCK:無此則 `pytest|tee` 吞 pytest 退出碼(實測 false|tee→0)
  source venv/bin/activate
  pytest tests/momentum/Analysis/test_factor_return_analyzer.py tests/momentum/Analysis/test_factor_return_stopgap.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py tests/momentum/test_export_formats.py -rA -q | tee /tmp/claude-501/final_gate_a.log   # 含 mutation;pipefail→pytest 非0 即中止
  ! grep -qE 'SKIPPED|XFAIL|XPASS' /tmp/claude-501/final_gate_a.log        # 0 skip/xfail 機械檢查
  pytest tests/momentum/Analysis -k net_ic -rA -q | tee /tmp/claude-501/final_gate_b.log
  ! grep -qE 'SKIPPED|XFAIL' /tmp/claude-501/final_gate_b.log
  npm --prefix frontend run build && npm --prefix frontend test -- FactorReturnChart && npm --prefix frontend test -- NetICChart
  python scripts/ic1cfr_stopgap_freeze.py --profile after-full --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/after_full.json && sha256sum handoffs/ic1cfr_full_baseline/after_full.json  # real-kline 重凍
  bash scripts/check_decoupling.sh 2>&1 | grep -oE 'R2=[0-9]+ R3=[0-9]+ R4=[0-9]+' | diff - handoffs/ic1cfr_full_baseline/decoupling_baseline.txt  # delta=0(§0)
  ```
  三方 DATA-CORRECT 簽核(上節)為 final gate 之後置必要條件(receipt/簽核檔齊才算過);mutation 基線→變異紅 receipt 存 `handoffs/ic1cfr_full_baseline/mutation_receipts.md`。

## §N N/A 登記(承 SPEC §N)
- rank_correlation_gross_vs_net / 持有期矩陣:N/A(本票聚焦序列重建+breakeven/profitable)。
- TrendAnalyzer factor_return dimension:N/A 接線(F5 加測 config 含 dimension 但 payload 無 trend=一致,或移除 dimension 預設)。
- P3 橫截面 / Equity→P1 wiring / turnover 模組 qcut PIT / rolling 窗:N/A(各另立 epic/票)。

## §追溯 — SPEC ID → TODO 覆蓋
- §C L44-49 PIT/公式→F0.1;L51-52 §U schema/正名→F0.2;L54 consumer-map ①②→F1.2、③→F1.1、④⑤⑩⑬⑭⑮⑯→F2.1、⑥⑫→F3.1、⑦→F4.1、⑧⑨→F5.1、⑪→§N;§G baseline→B0.1+§G-NOTE+F0 Gate;§A RULING④ expanding→§0/F0.1;§P F0-F5→B/F 批;§V mutation→§V-matrix;§R 回退→§0。
- **R1 三家 findings D1-D19 對照**:D1→§G-NOTE/F0.1;D2→F1.1/F4.1;D3→§V-matrix;D4→§0;D5→F3.1;D6→F4.1;D7→F0.1;D8→§V-matrix;D9→F0.2;D10→F2.1;D11→§DATA-CORRECT;D12→final gate;D13→F1.2;D14→F0.1/F0.2;D15→F5.1;D16→F1.1/F1.2/F2.1;D17→§G-NOTE;D18→F0.2;D19→B0.1/F5.1。
- **R2 殘餘 10 項對照**:codex R2-1(nodeid 完整路徑)→§V-matrix;R2-2(decoupling comparator)→§0/B0.1/final gate;R2-3(orchestrator sanitize)→F2.1;R2-4(0 skip/xfail 機械)→final gate;R2-5(第二 fixture 具體)→§DATA-CORRECT;R2-6(SPEC 自撞)→SPEC v0.6.2 修正;R2-7(ok-reason)→F2.1;R2-8(enabled gate 機械)→F1.2;R2-9(trend nodeid)→F5.1;R2-10(NetICChart)→F4.2。composer-3→F2.1;composer-10→F1.2;composer-12→F4.2;composer-14→F0.1。grok R2-1(series API)→F1.1;R2-2(rg 假紅)→F1.2;R2-3(SPEC 自撞)→v0.6.2;R2-4(用語)→F1.2 邊界。

STATUS: DONE(R3 Draft;待三家 R3 閉合確認→凍結)
