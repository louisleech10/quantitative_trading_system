# IC-LA-0(P0) — IC Analysis look-ahead 統一整治(P0 三點 + PIT 原語家族) — SPEC

> 來源 PLAN/診斷：`handoffs/ICLOOKAHEAD-MASTER.md` + `handoffs/LA0-RECON-SYNTHESIS.md` + `handoffs/LA0-SPEC-ADV-R1-RECONCILE.md`(R1 三家 adversarial) | 日期：2026-07-15 | 對應 TODO：`docs/IC_LA0_TODO.md`(凍結後生成) | 版本：**v0.5.3**(修 freeze5 codex+grok REJECT:3 處殘留 index=m 全傳播 §MS;待重 freeze-stamp)

### §MS min_samples/first-valid canonical 定義(v0.5.2,單一權威,§P0-2/§G/LA0-0 引用本節)
`min_samples`(canonical=**100**)=**required 非 NaN 歷史觀測 COUNT(含當前 bar)**。令 `effective_count(t)`=`series[0..t]` 非 NaN 數。**valid at t ⟺ effective_count(t) ≥ min_samples**。`first_valid = min{ t : effective_count(t) ≥ min_samples }`(無 NaN → t=99=min_samples-1,0-based;有 NaN 更晚)。**禁 hard-code index=min_samples**(off-by-one)。

**誠實 scope**：本票 = P0 三點(rolling IC / stage5 分位門檻 / stage1 fit 範圍) + 統一 PIT 原語家族 + fallback 出口。**非**「全 IC look-ahead 統一整治」——P1(regime 全期 percentile / deep long_short)預留 helper API,LA-1 修;P2 另立。default-on report leakage 清單見 §N。
**FR descope(v0.5,使用者 2026-07-15 定)**：**FR 移出 LA-0**。實況=`_run_factor_return:1808` 現 `ModuleUnavailableError`、FR-FULL(warmup/position/§U/runner)未建 → LA-0 **僅交付 pit_stats 原語(FR-ready)**,FR 實際接線歸**獨立 1c-FR-FULL epic**(消費本票原語)。本票**不接** production FR、不驗 FR byte-equivalence。

## §RISK 風險分級
- **大小**：**大**(改 IC Analysis 核心計算、跨模組共用路徑、多 phase、回測正確性生死)。
- **命中高風險原則**：(a) 數值/資料品質;(b) 跨模組共用路徑(ic_engine / monotonicity / turnover / data_preprocessor + 新 PIT helper 多消費者);(c) 多 phase 難回退(改預設數值→全 golden 重基準);(d) ML/回測正確性(look-ahead=回測作弊)。
- RISK-HIT: a,b,c,d
- → §G Golden 必填、adversarial review 必跑、三方 DATA-CORRECT 簽核(a,d)。

## §A 假設與待使用者確認
> 偵察四方 CONVERGED;R1 adversarial 三家實跑覆核。下列 FACT-RECEIPT 交叉佐證。

已核實事實(附 receipt)：
- `FACT-RECEIPT`: P0-1 全序列 pre-rank → 截尾未來 bar,早期 pure-TEST 窗 rolling spearman IC 全變(composer max|Δ|≈0.0049;grok n_diff=80/80、1788/1788),pearson/window-spearman control=0(composer+grok 實跑 2026-07-15,真實 kline BTCUSDT/1h + ETHUSDT/12h)。
- `FACT-RECEIPT`: P0-1 perf 於**預設窗集 [21,63,126]**(`config/ic_config.yaml:41`)——**逐特徵 python 迴圈**:31–100feat = 26–83s(composer);**每窗跨特徵向量化 `DataFrame.rank`+batch corr**:50–150feat = 1.36–3.16s(grok);現況 global pre-rank ~13–61ms;scipy `_rolling_spearman` 迴圈 45–117s(composer+grok 實跑 2026-07-15)。
- `FACT-RECEIPT`: P0-2 mono 硬閘 0.6 可翻——ret1 full 0.50(FAIL) vs trunc 0.75(PASS);`turnover_analyzer.py:49,92` 全域 `rank()` early rank_change n_diff=312–317/400;三種 PIT 聚合(pit_pool/pit_timeavg/pit_last)數值分叉(grok+composer 實跑 2026-07-15)。
- `FACT-RECEIPT`: P0-3 `fit_mask=None` winsorize early n_diff=14~31/400;train_mask control n_diff=0;`standardize` 預設 method=`none` 且不在 `PreprocessingConfig` schema → 預設洩漏主體=percentile winsorize;小樣本 quantile 線性內插 n=7..100 identity=False(必 clip)→ min_samples 須 per-t history length(grok+composer 實跑 2026-07-15)。
- `FACT-RECEIPT`: 窗內乾淨版 `ic_engine.py:1265 _rolling_spearman` 存在但 `compute_rolling_ic` 未呼叫;turnover 同時輸出 scalar 與 time_series(`compute_all:164-168`),前端 `TurnoverTimeSeriesChart.tsx:51-72` 消費 `quantile_turnovers[]/rank_change_rates[]`(grep+讀碼實證,codex+Claude 2026-07-15)。
- **待使用者確認：無**。(技術待裁走委員 adversarial,見 LA0-RULING-FINAL。)
- **已確認結果**：`2026-07-15 使用者裁定=IC Analysis look-ahead 深修,先 P0 統一整治`(HANDOFF/project_ic_analysis_lookahead_remediation)。**FR 併入**於 v0.5 經 TODO-adv 揭 FR-FULL 未建後**使用者裁定 descope 移出本票**(見 §開頭 FR descope 段 + Phase LA0-4)。

### LA0-RULING-FINAL(R1 reconcile 定;R2 可再挑戰後轉凍結)
- **RULING-1(P0-1 實作,v0.3 定)**：正確性優先(原則 #1/#3 > 執行時間 #4)——look-ahead 修正**不被 perf 阻擋**。LA0-1 交付「每窗跨特徵向量化 rank + batch corr」+ **Numba/chunked**(非「Numba 後續」);chunked 分批(不改結果)讓其 scale 到真實 universe。**禁** naive 逐特徵/scipy 迴圈上線(A 僅 slow oracle)。**perf = non-blocking telemetry(非 merge gate,v0.4 修契約矛盾)**:codex R3 實證即使向量化 batch 相對 wall 仍 67–109×(N50=109×/N100=87×/N150=67×),故 50× **不作 pass/fail gate**(否則 perf 擋 correctness,違原則 #1/#3>#4)。改:baseline-freeze 記錄**實際預設 N 的 wall+RSS telemetry**(對照現況)寫 receipt 供 perf epic 追蹤,不擋 merge。**memory 注記**:真實 default N=161031(無 cap),161k×三窗約 9.3 億輸出值,**chunk 只降中間 buffer 不降結果容器/RSS**;8GB tier scale/stability + Numba 加速 + 可能的 default cap 皆屬**獨立 perf epic**,本票 correctness 不依賴其解決。
- **RULING-2(P0-2 mono)**：**① 進閘 PIT 版 mono(保 scalar)**,鎖唯一聚合=**pit_pool**(見 §P0-2-AGG);M-lookahead **主錨=early `bin_t` 序列 equal**,scalar 僅 selection mutation 輔證,**不要求** scalar 截尾恒等;`long_short_spread` 同 PIT。退閘②為 R2 fallback(若 pit_pool 仍洩漏)。
- **RULING-3(P0-3 fit_mode)**：`fit_mode ∈ {train_mask, pit_expanding, full_sample, unset}`;**schema default=`unset`(fail-closed)+ orchestrator 強制注入**(禁 global default pit_expanding);caller 映射見 §C。`_run_full_sample_fallback` 鎖 `full_sample`+`oos_guarantees=False`。
- **RULING-4(golden 歸因)**：machine-readable JSON allowlist + **三態分類**(expected-leakfix/expected-downstream/unexpected)+ **強制 control 列**(pearson/train_mask 必 Δ≈0);見 §G/§V。

### RULING-5(B6 warmup policy,v0.3 定;v0.5 校正 size 語意)
turnover/rank_change time_series **warmup 期 `[0, first_valid)` 值 = JSON `null`(first_valid 依 §MS,非 `[0, min_samples)`——t=first_valid 本身 valid 不 null),對齊源序列 index(長度=源 n)**(不裁除、禁 dropna)。理由:前端 `TurnoverTimeSeriesChart.tsx`/reporter 按 index 對齊。**注意(v0.5 S2)**:legacy 現碼 `diff().dropna()` 輸出長度=n-1;本修法對齊源 index=n → **相對 legacy +1,為刻意 schema 變更**(非「大小不變」),須 contract test(`len==源 n`+warmup null)+ B6 三方明確簽核。

### §P0-2-AGG(mono PIT 聚合公式,鎖定)
```
for t in range(len(feature)):
  if effective_count(t) < min_samples: bin_t = NA   # 見 §MS(非 t<min_samples)
  else: bin_t = pit_expanding_qcut_label(feature[0..t], q)[-1]   # 當前 bar 標籤
Ω = {t : bin_t != NA}  (split 時 ∩ test 有效 bar)
μ_k = mean(label_t | bin_t==k, t∈Ω)         # 缺 bin → 該 diff 不計(寫死,非整分位 drop)
monotonicity_score = mean(diff(μ_{Q1..QK}) > 0)   # 與現行 compute_monotonicity_score 同構,輸出 scalar
# 禁 pit_timeavg 作閘分數(可另出 diagnostic)
```

## §C 約束與 consumer-map
- 解耦 7 條:helper 置 `momentum/Analysis/`,`momentum/` 不 import `api/`;不弱化 NaN/inf gate;**不擅改輸出大小**(P0-2 mono scalar 契約=硬約束;turnover time_series 陣列長度/warmup null policy 見 §G,output-size 影響已評估)。
- PIT 修法禁引入新未來資訊管道;warmup 期不 fit(min_samples **per-t history length**)。
- **caller→fit_mode 表(RULING-3)**：
  | Caller | fit_mode | fit_mask | 紅標 |
  |--------|----------|----------|------|
  | `analyze`+split applied(`orchestrator:924`) | `train_mask` | train | oos=True |
  | `analyze`+split off | `pit_expanding` | None | pit metadata |
  | `_run_full_sample_fallback`(`:1015`) | **`full_sample`(鎖)** | None | oos=False+reason |
  | 單元測試/研究直呼 | 顯式三選一 | 依 mode | 禁 None+unset |
  | cache replay(`:1505 refilter`) | 無獨立 key→revalidate(見 M4) | — | metadata 不符則 invalidate 重算 |
  | `analyze_cross_sectional`(`:1044`) | N/A(跳 stage1) | — | — |
- **consumer-map(下游)**：
  - P0-1 → `compute_icir`(ICIR/hit_rate,`icir_min=0.5` 硬閘)→ centrality/trend/deep。
  - P0-2 → `_apply_thresholds`(`monotonicity_score_min=0.6`)+ `net_ic_analyzer`(turnover scalar→cost_drag,`:2011`)+ `long_short_spread`(同 `_assign_quantiles:104`,P0-2 同源修)+ `refilter`(重套門檻)+ `redundancy.tiebreaker=monotonicity`(非預設)。
  - P0-3 → 全 stage1 下游特徵 → 所有 IC/metric;constant/coverage 改特徵宇宙。
  - **regime**(P1,LA-1 修,本票 helper 預留 `pit_expanding` percentile API):`_compute_regime_groups_rule` 全期 `nanpercentile`,`include_regime_analysis=True` 預設進 grouped report(非硬閘)。
  - **cache/version 傳播(M4,v0.4 修正 codex R3)**:`deep_analysis` cache 有實體 `_compute_deep_cache_key` → key **必含 `pit_stats_version`+`fit_mode`**;但 **`refilter()` 無獨立 cache key**(`:1505` 直接重用 `self._ic_cache`,`:835`)→ 須 **revalidate**:`refilter` 前檢查 `_ic_cache.metadata` 的 `pit_stats_version`/`fit_mode` 與當前一致,不符則 **invalidate 重算**(禁重用舊污染 `_ic_cache`)。
- **feature-count guard(B1)**:rolling IC 入口 N 大時 **chunk 分批算**(不改結果);另加**可選** `feature_filter.max_features` 逃生(研究用,**預設不設 cap**,不改預設行為→符 no-default-off)。真實 manifest 可達 161k(default filter=None),故 LA0-1 實作須 chunked 以 scale。
  - **前端**:scalar `monotonicity_score`/`turnover_rate` 型別不變(`ICSummaryTable.tsx`/`types.ts`)=安全;**turnover time_series 陣列**(`quantile_turnovers[]`/`rank_change_rates[]`,`TurnoverTimeSeriesChart.tsx`)PIT 後值變、warmup 改長度/NaN → 鎖 array keys/length/warmup null policy + contract test。`*_fit_scope` 新 metadata 欄須 optional(舊 reader 忽略)。
  - PIT helper 新消費者:FR v0.4(expanding 族)、未來 long_short/regime(預留 API)。

## §G Golden / Baseline
- **feature/kline 條件**：命中 → 真實 `data_cache/feature_klines/kline_cache.h5` + 三方 DATA-CORRECT;禁合成 fixture。
- **凍結時機 / reference**：動工前固定 symbol+config baseline;symbol=BTCUSDT/1h(主)+ETHUSDT/12h(跨 TF),末 ~2000 bar。**baseline 須經真實 orchestrator 呼叫可重現(v0.5 T1)**:鎖完整輸入=`data_cache/feature_klines/kline_cache.h5` 的 group key、feature manifest 路徑、config hash、末 2000 bar 切法(以 timestamp 尾切非位置)、expected schema;config=預設(spearman rolling [21,63,126] / mono_min=0.6 / turnover on / split on / winsor on / standardize=none)。存 `tests/golden/la0/<symbol>_<tf>_baseline.json`,含 `pit_stats_version` + control 欄。**無「手工抽驗」**——全 baseline 由 `gen_baseline.py` 機械產出可重跑。
- **allowlist predeclare(v0.5 T5)**:§L2 attribution allowlist(固定 rows/component/reason)**於 B0 baseline 階段先 commit** `tests/golden/la0/attribution_allowlist.json`;B6 只填 before/after/delta,**禁增列 expected**。
- **baseline 內容**：rolling IC 序列(per feature×window)sha256 + ICIR/hit_rate;mono_score + per-bar bin_t 序列 + quantile_mean_returns;turnover scalar + time_series 陣列 + rank_change;stage1 winsorize value hash + NaN mask hash;passed_features 集合 sha256;數量/schema。
- **oracle 索引集合(鎖,v0.5.2 依 §MS)**：令 n=len,TR=trunc,W=window。EXPANDING first_valid 依 §MS(`min{t: effective_count(t)≥min_samples}`,**computed 非 hard-code**) →
  `EXPANDING equal: t ∈ [first_valid, n-TR)`;`ROLLING equal: 僅比較 emitted window-end indices(含 stride)end ∈ {W-1+k·stride : end < n-TR}`。effective-count 依 §MS per-t 非 NaN 計數(非位置)。
- **通過條件(三層,可證偽)**：
  1. **L1 元素級**:early series/bin/turnover/rank_change/winsor element-equal;**dtype-aware atol**(float64=1e-12;float32 特徵路徑=1e-6 標 dtype);**禁** mean-only/過短 weak prefix 作唯一 gate;mono/turnover **scalar 不得當主 M-lookahead 錨**(主錨=per-bar bin_t)。
  2. **L2 歸因表(B4 schema 落文)**:machine-readable JSON,每列欄位 = `{name, before, after, delta, component, oracle_passed:{m_lookahead, control}, class, reason}`;`class ∈ {expected-leakfix, expected-downstream, unexpected}`。**allowlist 須動工前 predeclare**(mutation/component 對應先寫死,禁看到 drift 後補 expected);**強制 control 列**(pearson rolling IC/train_mask 段 winsorize 必 |Δ|≈0=control-stable,否則 FAIL);未列 diff=unexpected;scalar 變但 component oracle 未變=unexpected;分類**須另一委員 receipt 覆核**(三方 DATA-CORRECT)。意外任一=FAIL 不 merge。
  3. **L3 mutation**:回退全域 rank/qcut/rank/fit → L1 FAIL(修前紅/修後綠)。
  4. 跨 symbol/TF 隔離:BTC 改動不影響 ETH(雙 symbol hash 並列)。

## §P Phase 與依賴(DAG:LA0-0 → {LA0-1,LA0-2,LA0-3} → LA0-5;**LA0-4 FR 已 descope 移出本票**)

### Phase LA0-0 — PIT 原語家族模組(依賴：無)
**Task 0.1 — 新建 `momentum/Analysis/pit_stats.py`(名待 TODO 確認)**
- 目標:**七原語**(6 stats operations + `pit_train_fit` policy),統一 min_samples(per-t)/warmup/紅標 metadata。檔案:新建,無既有 caller。
- 匯出(B5):
  - `rolling_window_rank_corr(x, y, window, stride, ties="average")`:**每窗內跨特徵向量化** rank + batch corr;P0-1 專用。
  - `pit_expanding_qcut_label(series, q, min_samples, duplicates)`:分位**標籤**(非值);P0-2/FR。
  - `pit_expanding_bounds(series, lo_q, hi_q, min_samples)`:winsor 邊界;P0-3/FR。
  - `pit_expanding_rank(series, min_samples, ties="average")`:P0-2 rank_change(新增)。
  - `pit_expanding_mean_std(series, min_samples)`:P0-3 zscore。
  - `pit_expanding_mad(series, min_samples) -> (median, mad)`:**回傳 (median, mad) 兩者**(非只 mad),使 production `median ± k*MAD` bounds(`data_preprocessor.py:186-192`)可重現(codex R3)。
  - `pit_train_fit(df, fit_mask, transform_fn)`:P0-3 split policy(標明=orchestration policy 非 stats primitive;明定 **fit(mask 內)→ transform(全段)** 邊界,禁 fit 洩漏)。
- **簽名鎖(v0.5 T2 / v0.5.2 first-valid 修,逐原語唯一契約,TODO 須落死)**:每原語鎖——輸入型別(Series/ndarray/DataFrame)、回傳 shape/index(與輸入對齊)、**current-inclusive**(含當前 bar)、**first-valid 依 §MS**(=`min{t: effective_count(t)≥min_samples}`,**非 hard-code index=min_samples**;無 NaN→t=99)、effective-count=非 NaN 計數 per-t、`min_samples` **canonical=100**(單一常數)、`mean_std` **ddof=1**、`bounds` warmup **唯一回值=(-inf,+inf)(no-clip)**、`pit_train_fit(df, fit_mask, transform_fn) -> pd.DataFrame`、per-bar validity mask helper `pit_valid_mask(series, min_samples) -> pd.Series[bool]`、rolling emitted-ends shape。
- **constant/coverage per-bar ruling(v0.5 T3)**:`remove_constant_features`/`handle_missing` 在 PIT 下**唯一契約=保欄不 drop,改標 per-bar validity mask**(避免未來尾端變異使早期欄被 drop/keep 翻轉);截尾後**欄集合 oracle**:early 欄宇宙不受未來 bar 影響。
- **FR-ready 驗證(v0.5,不接 production FR)**:單元測試證 `pit_expanding_qcut_label`/`pit_expanding_bounds` 可服務 FR 語意(qcut label + winsor bounds),**不**呼叫 production `factor_return_analyzer`。
- 驗證:各原語單元測試 + M-lookahead 截尾→早期 equal(`pytest tests/momentum/test_pit_stats.py`,atol 1e-12);同輸入 rolling ≠ expanding rank corr 斷言(防混用);**first_valid==min_samples-1 斷言(dense/無 NaN 情形;有 NaN 則 effective_count 定義,依 §MS,非 index==min_samples)**;ddof==1 斷言。
- 邊界(≥2):空序列 / 全 NaN / n<min_samples(no-op raw,per-t) / std=0 / ties 重複值(average) / qcut 回 label 非值 / mad=0 / constant 欄截尾前後欄集合一致。
- 不可做:禁 expanding 冒充 rolling(P0-1 窗內);禁 cross_sectional_zscore 併入;禁 `pit_train_fit` 隱藏 fit/transform 洩漏;禁 constant/coverage 一次性 drop 全欄(須 per-bar mask)。

### Phase LA0-1 — P0-1 rolling IC 窗內 rank(依賴：LA0-0)
**Task 1.1 — `ic_engine.py:289-296` compute_rolling_ic spearman 改窗內 rank**
- 目標:spearman 用 `rolling_window_rank_corr`(每窗跨特徵向量化);pearson/kendall 維持現況(kendall 走 raw pearson 路徑,本票僅改 spearman)。caller:`_stage4_ic_calculation`。
- 改法:移除 `:290-291` 全序列 `rank(axis=0)`;spearman 分支改窗內原語(向量化 batch + Numba;N 大時 chunk 分批,不改結果);pearson 不動;list 長度/warmup 對齊契約。
- 驗證:M-lookahead 截尾→早期 pure-TEST IC equal(索引集合=emitted window-ends,atol dtype-aware);mutation 回退全域 rank→FAIL;pearson control 仍 pass;**perf telemetry(非 gate)**:記錄實際 N wall+RSS 對照現況寫 receipt(不擋 merge,歸 perf epic);ICIR/hit_rate 隨之修正。
- 邊界:window>n(空)、單特徵、ties、stride>1、float32 特徵、N≫預算(chunk 路徑結果一致)。
- 不可做:禁改 pearson;禁逐特徵/scipy 迴圈上線(RULING-1);perf 不達標不擋 correctness merge(開 perf epic)。

### Phase LA0-2 — P0-2 stage5 分位 + rank_change PIT(依賴：LA0-0)
**Task 2.1 — monotonicity `_assign_quantiles`(:185)改 PIT + §P0-2-AGG 聚合**
- 目標:bin 用 `pit_expanding_qcut_label`;mono 依 §P0-2-AGG pit_pool 聚合→**scalar**。caller:stage5+`_apply_thresholds`。`long_short_spread`(:104 同 `_assign_quantiles`)同 PIT。
**Task 2.2 — turnover(:31,80)qcut + (:49,92)`rank()` 皆 PIT**
- 改法:qcut → `pit_expanding_qcut_label`;`rank()` → `pit_expanding_rank`;再 diff。**禁 dropna**(現碼 `diff().dropna()` 使長度 n-1);改 **對齊源序列 index(長度=源 n)**,warmup 段 = JSON `null`。
- **S2 刻意 schema 變更(v0.5)**:turnover time_series 陣列長度由 legacy **n-1 → n**(對齊源 index,前端可 skip null)。此為刻意輸出大小變更(PIT index 對齊所需),須前端/API/reporter contract test + **B6 三方 DATA-CORRECT 明確簽核此項**。
- 驗證:M-lookahead **主錨=early bin_t 序列 equal**(atol 1e-12);turnover/rank_change early equal;mutation 回退全域 qcut/rank→FAIL;selection mutation(構造 full mono<0.6≤trunc)→passed_features 變→FAIL;net_ic cost_drag 隨之變;**contract test:len(array)==源 n 且 warmup 段為 JSON null**。scalar 僅輔證。
- 邊界:n<min_samples warmup(bin=NA)、duplicates="drop"、全同值、單分位、缺 bin(diff 不計)。
- 不可做:禁破 scalar 輸出契約;禁遺漏 rank_change/long_short_spread;禁 dropna;JSON 用 `null` 非非標準 NaN。

### Phase LA0-3 — P0-3 preprocessor fit_mode 四出口(依賴：LA0-0)
**Task 3.1 — `data_preprocessor.py` winsorize/zscore/constant/coverage fit_mode 分流**
- 目標:四出口(RULING-3);`fit_mode` 進 canonical `PreprocessingConfig`;`unset`+None→**fail-closed raise**;無 split→`pit_expanding`(用原語);`full_sample`→metadata `oos_guarantees=False` 紅標。constant/coverage 隨 fit 範圍。
**Task 3.2 — orchestrator 傳遞 fit_mode + fallback 注入**
- 改法:orchestrator 全入口注入 mode(現僅傳 fit_mask,`:2154-2156`);`_run_full_sample_fallback` 呼叫前注入 `fit_mode=full_sample`;cache key/report metadata 含 mode。
- 驗證:M-lookahead fit_mask=None+PIT→early 值 equal(atol 1e-12);mutation 回退全樣本 fit→FAIL;train_mask control 排尾→train 段 equal(防誤傷);`pytest.raises` 覆蓋 unset+None;invariant 測試:所有進 `_stage1_preprocessing` 路徑 `fit_mode!=unset`、raise 不發生在 analyze() happy path;`pytest tests/momentum/test_data_preprocessor.py`。
- 邊界:空 mask、全 True mask、n<min_samples per-t、constant 尾端才現、coverage 未來密度改刪欄。
- **遷移矩陣(M3,逐 caller,v0.4 修正 codex R3)**:僅列**本票 Analysis `DataPreprocessor`** 真 caller(排除 `profile_gate3_to_4.py:66`——那是 FeatureEngineering `FeaturePreprocessor`,非本票):`tests/momentum/Analysis/test_ic_1a_cut1_oos.py:312-313`(已傳 `fit_mask=train_mask`→對映 `train_mask` mode,預期不變)、`tests/momentum/test_data_preprocessor.py:29,51`(unset 直呼→遷 `pit_expanding` 或顯式 mode,否則 fail-closed 打斷)、`test_ic_1a_cut1_leakage.py:141-142`(保 fail-closed 契約)。TODO 階段須 grep 全 `DataPreprocessor(...).preprocess(` 補全清單。**禁為過測改既有 assert**(防假綠)。
- 不可做:禁沿用 643c5c2 過嚴弄斷 golden(留 full_sample 逃生口);禁 silent None;禁 global default=pit_expanding(架空 fail-closed)。

### Phase LA0-4 — ~~FR 併入~~ **已 descope 移出本票(v0.5)**
- **裁決(使用者 2026-07-15)**:FR-FULL 未建(`_run_factor_return:1808` `ModuleUnavailableError`)→ LA-0 **僅交付 pit_stats 原語(FR-ready)**;FR 實際接線歸**獨立 1c-FR-FULL epic**(該 epic 建 F0-F2 因子報酬序列時消費本票 `pit_expanding_qcut_label`/`pit_expanding_bounds`)。本票**不含** FR production 接線、不驗 FR byte-equivalence。原語的 FR-ready 驗證併入 LA0-0 Task 0.1(單元測試證原語可服務 FR 語意,不接 production FR)。

### Phase LA0-5 — 測試/golden/freeze(依賴：LA0-0..LA0-3;LA0-4 已 descope)
**Task 5.1 — 全套 M-lookahead 入庫 + golden 重基準 + 歸因表**
- 目標:每點 mutation 紅測入 `tests/`;修後 golden 重基準 + RULING-4 machine-readable 歸因表(強制 control 列);freeze gate。
- 驗證:`pytest tests/momentum/` 全綠;歸因表無 unexpected 且 control-stable;跨 symbol 隔離(BTC/ETH 雙 hash)。
- 不可做:禁放寬既有斷言換綠燈(防假綠)。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**:RISK-HIT 含 a,d → 每點附 M-lookahead(引 `docs/TEST_DESIGN_CHARTER.md`);**rolling(比 emitted window-ends,含 stride)vs expanding(warmup 後 `[first_valid, n-TR)`,first_valid 依 §MS)兩套 oracle 分開**;主錨 element/bin 級,禁 mean-only/scalar 誤錨。
- 測試層級:單元(pit_stats 七原語)/ 整合(stage4/5、stage1、orchestrator fit_mode invariant)/ Golden(截尾不變式 + machine-readable 歸因)/ 邊界 / perf telemetry(非 gate)。可獨立 `pytest tests/momentum/`,不需 run_api.py。
- **防假綠**:diff 既有測試斷言,不得放寬/刪除;新斷言對應新 PIT 行為;`test_ic_1a_cut1_leakage.py` 契約不得弱化;遷移舊 None 測試禁改 assert 過測。
- **邊界目錄(打勾)**：☑空DF ☑全NaN列 ☑std=0 ☑重複/亂序 timestamp ☑n<min_samples per-t warmup ☑大尺度浮點 reduction(rolling corr cumsum/rank 數值穩定性)☑float32/float64 dtype;☐API重啟 ☐並發(不涉)。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert;`fit_mode`/PIT——但**驗後預設 ON**(feedback_no_default_off:flag 僅逃生口,不藏驗過的修復;`full_sample` 是研究逃生非預設關閉);Golden FAIL / 歸因表有 unexpected / control 非 stable → 不 merge。

## §N N/A 登記
- §V 並發/重啟:N/A — 離線分析計算路徑,無並發寫/重啟語意。
- LA0-RULING 待使用者:N/A — 技術取捨走委員 adversarial(feedback_delegate_technical_decisions)。
- **default-on report leakage 清單(非本票 P0,LA-1 修,helper 預留 API)**:P1-1 regime 全期 `nanpercentile`(`include_regime_analysis=True`)/ P1-2 deep long_short 全 qcut(`enabled=True`,threshold off)。stage5 在 test labels 選 feature=evaluation-selection policy,PIT bins 不冒充 OOS selection 保證。
