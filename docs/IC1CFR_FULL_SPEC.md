# IC1C-FR-FULL — canonical 單標的因子擇時多空報酬序列重建 — SPEC

> 來源:handoffs/1cFRFULL-RECON-SYNTHESIS.md(四方偵察)+ R1/R2 adversarial(handoffs/1cFRFULL-SPEC-ADV-R1-RECONCILE.md + 1cFRFULL-SPEC-R2-{codex,composer,grok}.md)　|　日期:2026-07-15　|　對應 TODO:docs/IC1CFR_FULL_TODO.md(凍結後生)　|　版本:**v0.4 DRAFT(R1+R2 全 CLOSED;R3 唯一 BLOCKING=hand-calc 數字已 pandas 實跑修正+winsorize 分位鎖+look-ahead 稽核補;待 R4 確認)**

> **R3→v0.4 修補**:R3 三家唯一剩 BLOCKING=§G hand-calc 數字與 qcut 演算法矛盾(Claude 手算錯)→ 改 **7-bar pandas 實跑鎖定**(feature=[20,40,10,55,30,5,50]→position=[0,0,-1,1,0,-1,1]);winsorize 分位來源鎖 0.01/0.99+small-sample no-op;新增 **look-ahead 全檔稽核**(nanstd skip 守衛/quantile_summary 描述性標註);stale 5-bar→7-bar;F2 `generate_enhanced_markdown`。

> **R2 補洞摘要(v0.3)**:R1 三家全 CLOSED;R2 新開(PIT scope):①§G 具體 7-bar hand-calc 填實(pandas 實跑);②warmup_periods config 鎖定;③PIT 分位演算法細節鎖(per-t top/bottom/fallback/空邊→position=0);④**winsorize 亦改 PIT**(composer 抓:full-sample winsorize 殘留前瞻);⑤turnover `|Δp|` 尺度語意;⑥§U value 分層;⑦active_bar_count 定義;⑧consumer-map 補 export/assert_no_finite/_CONDITIONAL;⑨F2 出口枚舉;⑩F3 vitest fixture。

## §RISK 風險分級
- **大小**:大。
- **命中**:(a) 數值/資料品質——報酬序列/Sharpe/net_ic 全依賴其正確;(b) 跨模組——analyzer→orchestrator→sanitizer→reporter→API→前端→net_ic→trend 全鏈;(d) ML/回測正確性——因子預測力評估核心 + PIT 無前瞻。
- RISK-HIT: a,b,d
- 命中 (a)(d) → §G Golden 必填、adversarial 必跑(三家,R1 已跑一輪)。

## §A 假設與待使用者確認
- FACT-RECEIPT(根因): `sed -n '70,88p' momentum/Analysis/factor_return_analyzer.py` → `:70-71` reset_index 丟 index;`:87` iloc 位置相減(四方一致)。
- FACT-RECEIPT(overlap=0): codex/composer/grok 各實跑 single-symbol qcut `overlap=0` → 「逐 t mean(high)−mean(low)」不可構造(handoffs/1cFRFULL-RECON-*)。
- FACT-RECEIPT(逐因子): `compute_batch:175-176` for name in selected_columns 逐因子。
- FACT-RECEIPT(無 Series 通道,R1 B1): `sed -n '96,104p' momentum/Analysis/factor_return_analyzer.py` → 現僅回 `ls_cumulative_sampled: list[float]`+標量,**無 per-timestamp pd.Series**;`net_ic_analyzer.py:183-190` `batch_analyze` `del factor_returns`。
- FACT-RECEIPT(§U 不 unwrap,R1 B3): grok python 模擬 `ic_reporter._safe_nested` 對 §U union 頂層取 feature key→None;unwrap `.value`→0.01;`sharpe` 鍵→None,`sharpe_ratio`→1.2。
- FACT-RECEIPT(turnover top-only,R1 B5): `turnover_analyzer.py:37-40` 只對 top_mask diff;`_run_net_ic`(orchestrator:2010-2016)傳 scalar。
- FACT-RECEIPT(net_ic 模板): `net_ic_analyzer.py:78-110` `compute_net_factor_return` index-align gross−cost 無 ×2。
- **待使用者確認:無**。**已確認結果**:
  - `2026-07-15 使用者`:canonical=**P1 單標的逐因子擇時多空**;正名禁冒充橫截面;P3 橫截面另立未來 epic。
  - `2026-07-15 使用者(look-ahead 決策)`:**本票一併修 PIT**(P1 分位改 point-in-time,乾淨無前瞻)→ **enabled 預設 ON**(符合 feedback_no_default_off)。

### PRESET-RULING(六決策;R2 committee 可挑戰,凍結前轉 RULING-FINAL)
| # | 決策 | RULING |
|---|------|--------|
| ① mid 分位權重 | **0**(空手=現金);唯一序列 `ls_return_full`(全對齊 index,flat=0);cumprod/risk_metrics/mean 全用 full 序列;附 metadata `active_bar_count` |
| ② enabled 預設 | **ON**(PIT 本票修→乾淨→驗後預設開) |
| ③ Equity 圖資料源 | 本票**不接**,保持 unavailable + 正名空態;Equity→P1 wiring 另票 |
| ④ qcut look-ahead | **本票修 PIT expanding-window + warmup**(DEFAULT=expanding;R2 可挑 rolling) |
| ⑤ Newey-West | 二期;`newey_west_adjusted:false` 測鎖 |
| ⑥ breakeven 公式 | 見 §P F4 顯式閉式 |

## §C 約束與 consumer-map
- 解耦 7 條不破;`check_decoupling.sh` 全綠;離線可 collect;不弱化 NaN/inf gate;不動 `data_cache/`。
- **P1 canonical 定義(正名核心,公式鎖定)**:逐因子、單標的。
  - **warmup**:新 config 欄 `FactorReturnConfig.warmup_periods: int = 20`(進 cache key/schema);與既有 `_min_samples=30`(全序列最低列數 gate)獨立——warmup 管「分位/winsorize 冷啟動」,min_samples 管「整段是否 SkippedResult」。`t < warmup_periods` → position=0(不進 active)。
  - **分位(PIT,演算法鎖定 R2-3/4)**:每 t 用 **expanding window `feature[0..t]`(含當根)**;`q_eff = min(num_quantiles, window 內 nunique)`;`label_t = pd.qcut(window, q_eff, labels=False, duplicates="drop").iloc[-1]`;`top = (q_eff−1)`、`bottom = 0`;`position_t = +1 if label_t==top; −1 if label_t==bottom; 0 otherwise(含中間分位)`。**該 t 無法形成 ≥2 有效邊(q_eff<2)→ position_t=0(不整段 skip)**。**禁 full-sample qcut**(前瞻)。僅當 post-warmup 全程無法形成任何 ±1 或有效列 <min_samples → 整段 SkippedResult。
  - **winsorize(PIT,R2-4 composer;分位來源鎖 R3 codex;no-op 門檻鎖 R4 grok)**:`returns_w_t` 用 **expanding(≤t)** 分位裁尾,`lower=0.01`/`upper=0.99`(對齊現 `_winsorize_series` 預設);**禁 full-sample winsorize**(殘留前瞻)。**no-op 門檻(整數,鎖定)**:`winsorize_min_samples = ceil(1/lower) = 100`——expanding 窗 `n < 100` → **no-op(returns_w=raw future_return)**;`n ≥ 100` 才施 `clip(quantile(0.01), quantile(0.99))`。理由:少於 100 點無法有意義估 1% 尾端,且 `Series.quantile` 線性內插在小樣本會誤 clip min/max(grok R4 實證 identity 假設不成立)。`winsorize_mode:"pit_expanding"`+`winsorize_min_samples:100`。**§G 7-bar(n≤7<100)→ no-op→identity**,故 golden 向量成立。
  - **look-ahead 稽核(R3 使用者提問觸發,全檔掃描)**:signal 級全期前瞻僅 qcut(:209)+winsorize(:194),皆改 PIT(上)。另兩處**非 signal 級**:①`nanstd(全期 future_returns)` skip 守衛(:50)——只決定是否 SkippedResult,不入報酬值,**本票保留但標註**(不改行為);②`quantile_summary`(各分位平均報酬,:83)——描述性 ex-post 統計,**須標 `descriptive_full_sample:true` 非可交易訊號**,不得與 P1 ls_return 混淆語意。無其他全期 signal 前瞻(掃描 `qcut|quantile|winsor|rank|rolling|expanding|nanstd|percentile`)。
  - **持倉/報酬序列(唯一)**:`ls_return_full_t = position_t × returns_w_t`(對齊同 DatetimeIndex;flat bar=0)。
  - `ls_cumulative = (1+ls_return_full).cumprod()-1`(含 flat 0 期,淨值不變);`long_short_mean_return = float(ls_return_full.mean())`(含 0 期);risk_metrics 全用 `ls_return_full`;`active_bar_count = int((position != 0).sum())`。
  - **turnover(供 F4,尺度鎖 R2-5)**:`turnover_t = abs(position_t − position_{t−1})`(∈{0,1,2};首 bar=0);`turnover_semantics:"abs_delta_position_p1"`。
  - **正名**:輸出/UI/export 必稱「單標的因子擇時多空」;schema 帶 `semantics:"single_asset_factor_timing_ls"`+`schema_version:"fr_full_v1"`+`quantile_fit:"pit_expanding"`+`winsorize_mode:"pit_expanding"`+`turnover_semantics`。
- **§U ok schema(B3,結構分層 R2-6)**:`{"status":"ok","value":{"schema_version","semantics","quantile_fit","winsorize_mode","features":{<name>:<payload>}},"reason":null}`(**metadata 與 features 分層,unwrap 迭代 `value.features` 不誤吃 metadata**)。legacy 判準=**無 status/schema 的裸 feature map**→sanitizer 擋;ok union→放行。reporter/CSV/export 統一 `_unwrap_factor_returns()` 讀 `.value.features`。
- **consumer-map(反轉 + R1 補漏)**:
  ①四處預設(`ic_config_schema.py` FactorReturnConfig.enabled=**True**/`ic_config.yaml`/`api/models/ic_models.py` 單數 `factor_return`/`icAnalysisStore.ts`);②tier `_apply_tier_config`(恢復 factor_return);③runner `_run_factor_return`(raise→compute_batch);④sanitizer `factor_return_sanitizer.py`+orchestrator/reporter/API 全出口(降級為「擋無 status legacy 裸 map/放行 ok union」);⑤reporter summary 三欄+鍵名 `sharpe`↔`sharpe_ratio`+`_unwrap_factor_returns`;⑥前端 `FactorReturnChart`+types.ts §U ok 形狀;⑦net_ic `_run_net_ic`→傳 PIT position/gross series;⑧freeze `ic1cfr_stopgap_freeze.py` after-full profile+AST allowlist 重凍;⑨`phase29_perf_validation_tmp.py` quarantine 解除(系列正確後);⑩**cache key** `_compute_deep_cache_key` 加 `schema_version` 或 FULL 後 invalidate(防命中 stopgap 舊 unavailable);⑪**TrendAnalyzer** `dimensions` 含 `factor_return`——本票決策見 §N(不接+註記);⑫**正名 deny/allow**:`FeatureTierPanel.tsx`/`DeepAnalysisConfigPanel.tsx`/chart title `C13 Factor Return`/`分位收益`/`FactorReturnLegacyMap` 型名全改;⑬reason 枚舉:ok 路徑禁 `ls_returns_timestamp_misaligned`;legacy 擋→新 reason `legacy_misaligned_factor_return_shape`;⑭**export 測試**`tests/api/test_export_api.py`/`tests/momentum/test_export_formats.py`(ok CSV 形狀更新);⑮`factor_return_sanitizer.assert_no_finite_in_factor_returns_subtree`(stopgap 用)→FULL 後對 ok union **豁免**(僅對 legacy 裸 map 斷言);⑯`api/services/ic_analysis_service.py` serializer `_CONDITIONAL_METRIC_KEYS`(net_ic 三鍵 §U 形狀守恆)。
- **明確排除**:`monotonicity_tester` 本體、`long_short_analysis`、真 residual IC(Phase 2B)、factor_exposure 幽靈(1d)、P3 橫截面(未來 epic)、Equity→P1 wiring(另票)、turnover 模組自身 qcut 債(另計)。

## §G Golden / Baseline
- feature/kline 命中 → 真實 `data_cache/feature_klines/kline_cache.h5` 衍生 fixture(`tests/fixtures/ic_api_real_kline.py`,ETHUSDT/12h);禁合成當正確性 oracle。三方 DATA-CORRECT 簽核(Claude+codex/grok+composer),簽核檔 `handoffs/ic1cfr_full_baseline/`。
- **兩層 oracle(B4)**:
  - **synthetic**:驗代數 + mutation;純 numpy membership reference 逐元素比;`atol=1e-12`(float64)。7-bar hand-calc:見下。
  - **real-kline**:凍 `handoffs/ic1cfr_full_baseline/before.json`(存 sha256;產生命令寫死);FR 節主錨=**未抽樣** `ls_return` series 的 `index_hash/position_hash/ls_return_value_hash/nan_mask_hash/schema_version`;`ls_cumulative_sampled`(100 點)僅 UI 契約非正確性錨。**stopgap before.json ≠ 相等基準**(FULL 值大變 scope-expected)。
  - **F0 merge 後** `--profile after-full` 重凍(硬順序):`source venv/bin/activate && python scripts/ic1cfr_stopgap_freeze.py --profile after-full --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/after_full.json && sha256sum handoffs/ic1cfr_full_baseline/*.json`(before.json 同法 `--profile before-full`,動工前跑)。腳本擴 `--profile before-full/after-full`。
  - **三方 DATA-CORRECT 簽核 checklist**(R2 composer-12):`handoffs/ic1cfr_full_baseline/DATACORRECT-{claude,codex/grok,composer}.md` 各簽:①PIT 無前瞻(M-lookahead 實跑紅);②value/index hash 逐元素;③跨 symbol/TF 隔離;④正名無橫截面冒充。三方全簽才過。
- **7-bar hand-calc receipt(進 synthetic golden;num_quantiles=3, warmup_periods=2, PIT expanding qcut;n=7<winsorize_min_samples=100→winsorize no-op→returns_w=raw;pandas 實跑鎖定 2026-07-15)**:
  - `feature = [20, 40, 10, 55, 30, 5, 50]`;`future_return = returns_w = [0.02, -0.01, 0.03, -0.02, 0.04, -0.03, 0.05]`
  - per-t 分位(`pd.qcut(window, min(3,nunique), labels=False, duplicates="drop").iloc[-1]`;top=q_eff−1、bottom=0):t0/t1=warmup→0;t2 window[20,40,10] last=10→label 0(bottom)→−1;t3 [..,55] last=55→label 2(top)→+1;t4 [..,30] last=30→label 1(mid)→0;t5 [..,5] last=5→label 0(bottom)→−1;t6 [..,50] last=50→label 2(top)→+1
  - `position = [0, 0, -1, 1, 0, -1, 1]`;`ls_return_full = [0, 0, -0.03, -0.02, 0, 0.03, 0.05]`
  - `long_short_mean_return = 0.03/7 = 0.004285714285714286`;`active_bar_count = 4`
  - `ls_cumulative = [0, 0, -0.03, -0.0494, -0.0494, -0.020882, 0.028073900]`
  - 通過:逐值 `abs≤1e-12`;reference numpy/pandas 實作(測試內,獨立於 analyzer 碼路)產同向量。此向量由 `pd.qcut` 實跑產生,禁手改(改 feature 須重跑 reference)。
- **非 FR 模組**:path 值 exact。`NON_FR_PATHS` 清單寫死(執行端由 before.json 頂層 `results` 鍵集合減 `factor_returns`/`net_ic` 生成);排除欄=`total_execution_time_s`/`generated_at`/error timestamp/`completed_count`/`skipped_count`/`deep_analysis_summary.completed`。
- **通過條件(可證偽)**:hash 全等 + hand-calc `abs≤atol`;nan_ratio exact;超出列 path diff=FAIL。**只比 mean/Sharpe 不足**(排列不變性反例必須被 value hash 抓)。

## §P Phase 與依賴(DAG:F0→F1→F2;F2→{F3,F4};F0..F4→F5)

### Phase F0 — 計算根重建(PIT + 序列 artifact + 公式鎖)(依賴:無)
**Task F0.1 — PIT 分位 + P1 序列**
- 目標:`compute_factor_returns` 以 PIT expanding 分位 + membership 序列取代 full-sample qcut + 位置相減。檔案:`factor_return_analyzer.py:57-104` + `_assign_quantiles_with_fallback:198-217`。
- 改法:刪 `:70-72,:87` reset_index/iloc/paired;分位+winsorize 改 PIT expanding(§C 鎖定演算法:`q_eff=min(num_quantiles,nunique)`、`qcut(...labels=False,duplicates="drop").iloc[-1]`、top/bottom label、per-t 空邊→position=0);`position`/`returns_w` Series(index=aligned);`ls_return_full=position*returns_w`;cumprod/risk_metrics/mean 全用 `ls_return_full`(§C 鎖定)。新增 config `warmup_periods=20`。
- **驗證(可證偽)**:`pytest tests/momentum/Analysis -k factor_return -q`——7-bar §G hand-calc `position==[0,0,-1,1,0,-1,1]`+`ls_cumulative` 逐值 `abs≤1e-12`;時間不相交 fixture→輸出 index⊆原 index、非 RangeIndex 等長;mutation M-pos(改回 reset_index+iloc)必 FAIL;M-lookahead(改回 full-sample qcut)必 FAIL(PIT 早期 position 不受未來影響);M-winsorize(改回 full-sample winsorize)必 FAIL(早期 returns_w 不受未來影響)。
- **邊界(≥2)**:①`t<warmup_periods`→position=0→ls=0;②per-t `q_eff<2`(ties)→position_t=0(**不整段 skip**);③post-warmup 全程無 ±1 或有效列<min_samples→SkippedResult;④NaN 對齊 dropna 後不足→SkippedResult(不靜默出數)。
- 不可做:不接橫截面;不改 monotonicity 本體;不用 full-sample qcut/winsorize。

**Task F0.2 — 序列 artifact + ok schema + 鍵名(B1/B3)**
- 目標:定義 **internal artifact** `FactorTimingReturnSeries(feature, ls_return: pd.Series, position: pd.Series, index_policy)` 供 orchestrator/cache-in-memory/net_ic/trend;external JSON=ok §U `{status,value{...,schema_version,semantics,quantile_fit},reason}`;鍵名 `sharpe_ratio` 與 reporter 讀取一致。
- **驗證**:`pytest tests/momentum/Analysis -k factor_return -q`——`isinstance(artifact.ls_return, pd.Series)` 且 index 為 DatetimeIndex;reporter summary 三欄 `is not None`;analyzer 鍵 `sharpe_ratio` 與 reporter 讀取鍵 `==`。
- 不可做:不重用 legacy `FactorReturnLegacyMap` 名於 ok 路徑;不 scalar 廣播成 series。

### Phase F1 — runner 接線(依賴:F0)
**Task F1.1 — `_run_factor_return` 恢復真計算**:raise→`create_factor_return_analyzer`+`compute_batch`;產 §U ok union。**F1 出口暫維持經 sanitizer(直至 F2 判準上線)**——F1 驗證只斷言 orchestrator 內部 artifact ok,不斷言 API 出口 ok(避免 B8 半態)。驗證:`pytest tests/momentum/Analysis -k factor_return -q`——force run 內部 artifact `status=="ok"`+有限葉。
**Task F1.2 — 四處預設 ON + tier**:enabled 預設 **True**(PIT 乾淨);`_apply_tier_config` 恢復 factor_return。驗證:`pytest tests/momentum/Analysis/test_factor_return_stopgap.py -q` 改寫後綠;預設 request→`module_summary.factor_returns=="completed"`;intermediate tier→factor_return 入 run。**enabled ON 之整體 gate=F0+F2+F3+F4 全綠**(§R 一鍵回退)。

### Phase F2 — sanitizer §U discriminator + reporter unwrap + 全出口(依賴:F1)
- sanitizer 改「擋無 status/schema 裸 legacy map / 放行 ok union」+冪等;reporter/CSV/export/API 全出口套 `_unwrap_factor_returns()` 讀 `.value.features`;cache hit/force-merge 用 schema_version 重算或 invalidate。**出口枚舉(實測觸點,執行端逐一 assert;`rg -c sanitize_factor_returns` 現況 reporter=14、service=4)**:reporter 側 `generate_detailed_csv`/`generate_ai_json`/`generate_enhanced_markdown`(@:289)/`export_all`/`save_report`/`_serialize_deep_analysis`/`_build_deep_summary_columns`;service 側 raw JSON serialize/task storage read/export/get_result。TODO 生成時以 `rg -n 'sanitize_factor_returns\|assert_no_finite' momentum/Analysis/ic_reporter.py api/services/ic_analysis_service.py` 鎖行號成表。
- **驗證**:`pytest tests/api/test_ic_deep_analysis.py -q`——雙注入:A=ok §U(含 status/schema)→保留有限葉+summary 三欄 `is not None`;B=無 status 裸 legacy map→無有限葉(擋);ok payload 經全枚舉出口後 `status=="ok"`(逐出口 assert)。

### Phase F3 — 前端上架 + 正名(依賴:F2)
- `FactorReturnChart` ok 路徑繪 `ls_cumulative_sampled`;types.ts §U ok 形狀;正名 deny/allow——全 user-facing label/help/card 改「單標的因子擇時多空」。**Equity 圖保持 unavailable**(正名空態,禁接 quantile_returns 位置相減)。
- **驗證**:vitest `renders_ok_series`+`legacy_finite_payload_rejected`+`equity_stays_unavailable`。**ok union fixture(寫死)**:`{status:"ok", value:{schema_version:"fr_full_v1", semantics:"single_asset_factor_timing_ls", quantile_fit:"pit_expanding", features:{f1:{long_short_mean_return:0.0042857, ls_cumulative_sampled:[0,0,-0.03,-0.0494,-0.0494,-0.020882,0.0280739], risk_metrics:{sharpe_ratio:...}}}}, reason:null}` → 斷言 chart 繪出 `ls_cumulative_sampled` 7 點、title 含「單標的擇時」;legacy fixture(無 status 裸 map)→ 斷言空態警示、不繪。`npm --prefix frontend run build` 綠;`rg -n "Factor Return|分位收益" frontend/src/components/ic-analysis frontend/src/app/ic-analysis/page.tsx` user-facing 文案 0 命中(內部 module key 除外)。

### Phase F4 — net_ic breakeven/profitable 回填(依賴:F0-F2)
- `_run_net_ic` 傳 PIT `gross`(=`ls_return_full` per feature)+ turnover series(=**PIT position `position.diff().abs()` 雙邊**,非 top-only);`batch_analyze` 用 series 算:`net_factor_return`、`breakeven_cost_bps=mean(gross)/mean(turnover)*10000`(align dropna;`mean(turnover)==0`→unavailable)、`profitable_after_cost=(mean(net)>0)`、`evaluable_count`。cost_enabled=False→守 1c SCHEMA_GROSS_ONLY。禁 gross_ic/scalar 廣播當分子。
- **驗證**:`pytest tests/momentum/Analysis -k net_ic -q` + `tests/api/test_ic_deep_analysis.py`——傳合成 gross_mean=0.001/turnover_mean=0.5→`breakeven_cost_bps==20.0`(±1e-9)且三鍵 `status=="ok"`+`evaluable_count>0`;`turnover.mean()==0`→`breakeven_cost_bps` unavailable;API E2E 注入 ok P1→NetICChart 非 unavailable。
- 不可做:不用 top-only turnover(系統性偏樂觀);不恢復 Archived「Net IC=0」語意。

### Phase F5 — 測試/freeze/quarantine 反轉(依賴:F0-F4)
- stopgap 三態測試改寫(舊斷言→新斷言表,每條註記為何舊錯);`ic1cfr_stopgap_freeze.py` after-full profile + AST allowlist 重凍;phase24 加 M-pos/M-lookahead 證偽測;quarantine 解除。
- **驗證**:`pytest tests/momentum/Analysis/test_factor_return_analyzer.py tests/momentum/Analysis/test_factor_return_stopgap.py -q` 綠;`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids`(after-full)exit 0;M-pos/M-lookahead mutation 在 phase24 存在且改回舊行為時 FAIL(可證偽)。

## §V 驗證策略與邊界測試目錄
- **mutation(RISK-HIT a,d 必附)**:M-pos=位置相減必 FAIL;M-lookahead=full-sample qcut(PIT 早期 position 不變式)必 FAIL;M-winsorize=full-sample winsorize(PIT 早期 returns_w 不變式)必 FAIL;M-mid=中間權重竄改可偵測;M-key=`sharpe` 鍵錯位→summary null 可偵測;M-unwrap=reporter 不讀 `.value.features`→summary null 可偵測;M-turnover=top-only turnover→breakeven 偏樂觀可偵測。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級:單元(analyzer 序列+PIT)/整合(orchestrator force run + API E2E)/Golden(真 kline hash + 7-bar hand-calc)/邊界。可獨立 pytest。
- **防假綠**:diff stopgap 既有斷言,舊斷言改寫註記(unavailable→ok);新斷言對應 P1/PIT 新行為;§G value hash 抓排列不變性(只比 mean 不足)。
- **邊界目錄**:空DF/全NaN列/std=0/單值 feature/亂序 timestamp/warmup 前全 flat/中間分位全佔/turnover=0/cache 命中舊 schema。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert;F1.2 enabled 預設 feature flag 一鍵回 stopgap unavailable(整體 ON gate=F0+F2+F3+F4 全綠才 ON);Golden FAIL → 不 merge。

## §N N/A 登記
- **rank_correlation_gross_vs_net(1c 拆票項,GROK-12)**:N/A——本票不做(1c-FR-FULL 聚焦序列重建+breakeven/profitable);持有期矩陣同 N/A。若 1c 封存條件要求,另立 follow-up。
- **TrendAnalyzer factor_return dimension(CODEX-4)**:本票 N/A 接線——不注入 P1 cumulative;F5 加測 config `dimensions` 含 factor_return 但 payload 無 `factor_return_trend`=一致(或移除 dimension 預設),避免宣稱含卻未接。
- **P3 橫截面 / Equity→P1 wiring / turnover 模組 qcut PIT**:N/A——各另立 epic/票(§C 排除)。
- 其餘必填段(§RISK/§A/§C/§G/§P/§V/§R)皆填。
