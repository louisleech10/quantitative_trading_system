# IC-LA-0(P0) TODO —（v2.3 DRAFT｜基於 `docs/IC_LA0_SPEC.md` v0.5.3（frozen）｜2026-07-15）

> 冷啟動執行端不需讀其他檔即可逐 Task 寫碼。套用 TODO-adv reconcile T1-T10（`handoffs/LA0-TODO-ADV-RECONCILE.md`）。**FR 已 descope 移出本票**（1c-FR-FULL epic 另做）。SPEC ID 100% 覆蓋見文末。

## §0 全域規則與約束
- **解耦**：helper 置 `momentum/Analysis/`;`momentum/` 不 import `api/`(grep `from api\.` momentum/→0);服務不互 import。
- **不可違反**：不弱化 NaN/inf gate;跨 symbol/TF 隔離;**PIT min_samples 依 SPEC §MS**——canonical=100=非 NaN 歷史 COUNT;valid⟺`effective_count(t)≥100`;`first_valid=min{t:count≥100}`(無 NaN→t=99,**禁 hard-code index=100**)。
- **輸出大小**：mono 保 scalar;**turnover time_series 刻意由 n-1→n**(S2,對齊源 index,warmup JSON null,禁 dropna)——此變更**須 B6 三方明確簽核 + 前端/API contract test**。
- **no-default-off**：驗過即預設 ON;`full_sample`/flag 僅逃生口。
- **防假綠**：不放寬/刪既有斷言;新斷言對應新行為;遷移舊 `fit_mask=None` 測試**禁改 assert 過測**;`test_ic_1a_cut1_leakage.py` 改 `pytest.raises`=**強化非弱化**。
- **Error**：`fit_mode=unset`+`fit_mask=None`→fail-closed raise(non-retryable)。
- **Logging**：`get_logger(__name__)`;hot loop 不 log。
- **斷路器**：Task ≤2 輪解不了→STATUS: BLOCKED 交委員會。
- **reconcile 未全 APPROVED→BLOCKED**：`handoffs/LA0-SPEC-FREEZE-RECONCILE.md`(已三家 APPROVED,sha256 cdb2d3c…)。

## §B 批次執行策略（DAG：B0 → B1 → {B2,B3,B4} → B6；FR/B5 已 descope）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|-------|---------|------|----------|------|
| **B0** | 0.1 baseline + 0.2 allowlist predeclare | 無 | §G 改前 reference(可重現)+ allowlist 先 commit | 中 |
| **B1** | 1.1 pit_stats 七原語(+Numba+FR-ready) | B0 | 共用底層;單模組 | 大 |
| **B2** | 2.1 P0-1 rolling IC | B1 | 單 caller | 中 |
| **B3** | 3.1 mono + 3.2 turnover | B1 | 同 stage5 分位家族 | 大 |
| **B4** | 4.1 preprocessor + 4.2 orchestrator/schema | B1 | 同 fit_mode 接線 | 大 |
| **B6** | 6.1 tests/golden/歸因 | B1-B4 | 匯聚 | 大 |
- 批次間 Gate：每 Batch 跑該 Batch 測試 + `pytest tests/momentum/`;B6 前所有 M-lookahead mutation 修前紅/修後綠。
- 實作端：Grok(依額度);code review=另一方(實作者不自審);**B6 三方 DATA-CORRECT 簽核**(a,d),含 S2 turnover size 明確項。
- 每 Batch 派工 prompt 前置=前批已綠 + Task 列表 + 驗收命令(如 `pytest tests/momentum/`)。

---

## Phase B0 — §G Baseline 凍結 + allowlist predeclare
### Task 0.1 — 可重現的改前 golden baseline（T1）
- SPEC ref：[§G]　目標：改碼前用**真實 orchestrator 呼叫**產可重現 baseline。
- 輸入：`data_cache/feature_klines/kline_cache.h5`,BTCUSDT/1h + ETHUSDT/12h。
- 輸出：`tests/golden/la0/{BTCUSDT_1h,ETHUSDT_12h}_baseline.json`。
- **輸入契約(T1,冷啟動可執行)**:`ICFilterOrchestrator.analyze(:845)` 需 `features_path`/`labels_path` — B0 須先 grep/讀 orchestrator 確定實際 features/labels artifact path 與 keys、feature manifest 生成命令(若不存在則用 orchestrator 內建 feature 生成路徑)、label 定義(return_5)、meta/expected schema 枚舉。若 features artifact 不存在於 repo,gen_baseline 須經 orchestrator 從 kline 生成(記 config hash)。
- 實作要點：
  1. **鎖完整輸入契約**:h5 group key(`/{SYMBOL}/{tf}/data`)、feature/label artifact path+keys(見上)、config hash、末 2000 bar 切法=**以 timestamp 尾切(非位置 index)**、expected schema。
  2. 經真實 `ICFilterOrchestrator` 跑 stage1/4/5(非手刻),記:rolling IC 序列 per feature×window sha256 + ICIR/hit_rate;mono_score + per-bar bin_t + quantile_mean_returns;turnover scalar + time_series(記 legacy n-1 長度)+ rank_change;stage1 winsorize value hash + NaN mask hash;passed_features sha256;schema/count。
  3. **control 欄**(改後必不變):pearson rolling IC、train_mask 段 winsorize。
  4. 記 **before perf telemetry**(wall+RSS,實際 N,[21,63,126],非 gate)。
- 修改檔案：新建 `tests/golden/la0/gen_baseline.py`。無既有 caller。
- 不可做：禁合成 fixture;**禁手工抽驗**(全機械可重跑);禁位置切 2000 bar(用 timestamp)。
- 邊界(≥2)：①全 NaN 欄→記 nan_ratio ②window>剩餘 bar→空序列。
- 風險緩解：⊘。
- 驗證：`python tests/golden/la0/gen_baseline.py` exit 0;兩 json 含上列全鍵 + control 非空;重跑 sha256 一致(可重現)。
### Task 0.2 — attribution allowlist predeclare（T5）
- SPEC ref：[§G L2]+[RULING-4]　目標：歸因 allowlist 動工前先 commit。
- 實作要點：predeclare `tests/golden/la0/attribution_allowlist.json`,含固定 rows(每 metric/component)+ 允許 mutation ID + expected class + reason;schema=`{name,before,after,delta,component,oracle_passed:{m_lookahead,control},class,reason}`。
- 修改檔案：新建 `tests/golden/la0/attribution_allowlist.json`。
- 不可做：B6 禁增列 expected(只填 before/after/delta);未列 diff=unexpected。
- 邊界(≥2)：①control 列(pearson/train_mask)預期 |Δ|≈0 ②未列 metric 出現=unexpected。
- 驗證：json schema valid;含全 P0 component + control 列;`python -c "import json;json.load(open('tests/golden/la0/attribution_allowlist.json'))"` exit 0。

---

## Phase B1 — PIT 原語家族（+Numba +FR-ready）
### Task 1.1 — 新建 `momentum/Analysis/pit_stats.py` 七原語
- SPEC ref：[LA0-0.1]+[T2]+[T3]+[T4]　目標：七原語,簽名鎖死,Numba/chunk,constant per-bar mask。
- 實作要點(含簽名)：
  1. `rolling_window_rank_corr(x: np.ndarray, y: np.ndarray, window: int, stride: int, ties="average") -> np.ndarray`:每窗內跨特徵向量化 rank + batch corr;**Numba 加速** + N 大時 **chunk 分批(不改結果)**;回 emitted window-ends×features。
  2. `pit_expanding_qcut_label(series, q, min_samples=100, duplicates="drop") -> pd.Series`:per-t [0..t] current-inclusive 分位→當前 bar **label**;`effective_count(t)<min_samples`→NaN(依 §MS,非 t<min_samples);index 對齊。
  3. `pit_expanding_bounds(series, lo_q, hi_q, min_samples=100) -> (pd.Series, pd.Series)`:winsor 邊界;**warmup 唯一回值=(-inf,+inf)(no-clip)**。
  4. `pit_expanding_rank(series, min_samples=100, ties="average") -> pd.Series`:per-t 當前 bar rank。
  5. `pit_expanding_mean_std(series, min_samples=100) -> (pd.Series, pd.Series)`:**ddof=1**。
  6. `pit_expanding_mad(series, min_samples=100) -> (median, mad)`:回 (median, mad) 兩者。
  7. `pit_train_fit(df, fit_mask, transform_fn)`:mask 內 fit→全段 transform 邊界(禁 fit 洩漏);orchestration policy。
- **簽名鎖(T2,依 §MS)**:`first_valid=min{t:effective_count(t)≥min_samples}`(**非 hard-code index=min_samples**;dense→t=99);min_samples canonical=100 單一常數;current-inclusive;effective-count=非 NaN 計數 per-t;shape/index 對齊輸入;rolling emitted-ends shape。
- **constant/coverage per-bar mask(T3)**:`pit_valid_mask(series, min_samples) -> pd.Series[bool]`(shape=輸入對齊,per-bar validity);**保欄不 drop**(取代現 `remove_constant_features:133`/`handle_missing:118` 的 `(df, removed)` drop-column),下游用 mask 排除 invalid bar;metadata key=`validity_mask`;截尾欄集合 oracle(early 欄宇宙不受未來影響)。
- **mutation test 骨架(T8,B1 先建供各批引用)**:B1 建 `tests/momentum/test_la0_lookahead.py` **骨架 + 共用 fixture**:`la0_real_kline`(真實 kline load,BTCUSDT/1h+ETHUSDT/12h)、`truncate_future(df, n)`(截尾 helper);各批(B2-B4)填自己 mutation nodeid;B6 補 `test_cross_symbol_isolation`(BTC perturb→ETH hash unchanged)+ `test_attribution_schema_valid`(validator)。**B6 不再「新建」該檔**(B1 已建,B6 只 append)。
- **Numba chunk equivalence test(T4)**:chunk 版 vs 非 chunk 版 element-equal;Numba vs 純 numpy element-equal。
- **FR-ready(T10)**:單元測試證 `pit_expanding_qcut_label`/`pit_expanding_bounds` 可服務 FR 語意(qcut label+winsor bounds),**不呼叫** production `factor_return_analyzer`。
- 修改檔案：新建 `momentum/Analysis/pit_stats.py`;`tests/momentum/test_pit_stats.py`。無既有 caller。
- 不可做：禁 expanding 冒充 rolling;禁 cross_sectional_zscore 併入;禁 qcut 回值(須 label);禁 constant 一次 drop 全欄(per-bar mask)。
- 邊界(≥2)：空序列/全 NaN/n<100(no-op raw)/std=0/mad=0/ties/constant 截尾欄集合一致。
- 驗證：`pytest tests/momentum/test_pit_stats.py`;每原語 M-lookahead 截尾→早期 equal(atol 1e-12);**first_valid==min_samples-1 斷言(dense;有 NaN 則 effective_count 定義,依 §MS,非 index==min_samples)**;ddof==1 斷言;bounds warmup==(-inf,+inf) 斷言;chunk/Numba equivalence 斷言;rolling≠expanding rank corr 斷言。

---

## Phase B2 — P0-1 rolling IC 窗內 rank
### Task 2.1 — `ic_engine.py` compute_rolling_ic spearman 改窗內 rank
- SPEC ref：[LA0-1.1]+[RULING-1]　目標：spearman 窗內 rank(Numba/chunk);pearson/kendall 不動。
- 實作要點：
  1. 移除 `ic_engine.py:290-291` 全序列 `rank(axis=0)`;spearman 分支呼 `pit_stats.rolling_window_rank_corr`。
  2. pearson(`:294-296`)、kendall(raw pearson 路徑)不動。
  3. 輸出 list 長度=emitted window-ends,warmup 對齊契約。
- 修改檔案：`momentum/Analysis/ic_engine.py::compute_rolling_ic`。既有 caller：`ic_filter_orchestrator._stage4_ic_calculation`(不改簽名)。
- **既有測試 migration(T9,真 nodeid)**：`test_ic_engine.py::{test_compute_rolling_ic_and_icir(spearman 早期值變=expected-leakfix),test_rolling_window_adjustment_by_timeframe,test_compute_rolling_ic_empty_alignment,test_compute_rolling_ic_pearson_short_window(pearson control 不變)}`;逐列 migration expectation;收尾 diff 既有 assert。
- 不可做：禁改 pearson;禁 scipy 逐窗迴圈;perf 不達標不擋 merge(perf epic)。
- 邊界(≥2)：window>n(空)、單特徵、ties、stride>1、float32。
- 驗證：M-lookahead 截尾→早期 pure-TEST IC element-equal(emitted ends,atol float64=1e-12/float32=1e-6);**mutation nodeid**=`test_la0_lookahead.py::test_rolling_ic_pit` 回退全域 rank→FAIL;pearson control 仍 pass;**after perf telemetry**(對照 B0 before,非 gate)。

---

## Phase B3 — P0-2 stage5 分位 + rank_change PIT
### Task 3.1 — monotonicity `_assign_quantiles` PIT + §P0-2-AGG
- SPEC ref：[LA0-2.1]+[RULING-2]+[§P0-2-AGG]　目標：bin PIT;mono pit_pool→scalar;long_short_spread 同 PIT。
- 實作要點：
  1. `monotonicity_tester.py:185 _assign_quantiles` qcut→`pit_expanding_qcut_label`。
  2. §P0-2-AGG:`effective_count(t)<100`→bin=NA(依 §MS,非 t<100);`μ_k=mean(label_t|bin_t==k,t∈Ω)`,缺 bin→該 diff 不計;`score=mean(diff(μ_{Q1..QK})>0)` scalar。
  3. `compute_long_short_spread`(`:104`)同 PIT。
- 修改檔案：`monotonicity_tester.py::_assign_quantiles,compute_monotonicity_score,compute_long_short_spread`。caller：stage5+`_apply_thresholds`。
- **既有測試 migration(T9,真 nodeid)**：`test_monotonicity_tester.py::{test_assign_quantiles_error_paths,test_assign_quantiles_actual_bins_less}` 逐列 migration。
- 不可做：禁破 scalar 契約;禁 pit_timeavg 作閘。
- 邊界(≥2)：n<100 warmup(bin=NA)、duplicates="drop"、全同值、缺 bin。
- 驗證：M-lookahead 主錨=early bin_t equal(atol 1e-12);mutation nodeid=`test_la0_lookahead.py::test_mono_pit` 回退全窗 qcut→FAIL;mono 型別 float scalar 斷言;`pytest tests/momentum/test_monotonicity_tester.py`。
### Task 3.2 — turnover qcut + 全域 rank PIT（S2 size）
- SPEC ref：[LA0-2.2]+[RULING-5]+[S2]　目標：turnover 分位+rank_change PIT;**禁 dropna,對齊源 index=n,warmup JSON null**。
- 實作要點：
  1. `turnover_analyzer.py:31,80` qcut→`pit_expanding_qcut_label`;`:49,92` `rank()`→`pit_expanding_rank`;再 diff。
  2. **移除 `diff().dropna()` 的 dropna**;陣列對齊源 index(長度=源 n),warmup **`[0, first_valid)`**(依 SPEC §MS,非 `[0,min_samples)`——t=first_valid 本身 valid 不 null)=JSON `null`(非 NaN)。
- **S2 前端 null 契約(T9/codex)**：`frontend/src/lib/types.ts:2022-2025` 現 `number[]` → 改 **`(number|null)[]`**;`TurnoverTimeSeriesChart.tsx:58-62` 現 `Number(null)==0` → 改 **skip null**;**「源 n」定義=raw feature index(非 `feature.dropna()` 後)**。
- 修改檔案：`turnover_analyzer.py::compute_quantile_turnover,compute_turnover_time_series,compute_rank_change_rate`;**`frontend/src/lib/types.ts`**;`frontend/.../TurnoverTimeSeriesChart.tsx`。caller：stage5+`net_ic_analyzer`。
- **既有測試 migration(T9,repo 真 nodeid,composer grep 校正)**：`test_turnover_analyzer.py::{test_quantile_turnover_matches_expected,test_compute_turnover_time_series_structure,test_rank_change_rate_for_increasing_series}`(scalar qcut/rank n<100 亦變)+ time-series 長度 tests;逐列 migration expectation(長度 n-1→n=expected)。實作端 grep `turnover` under tests/ 最終對齊。
- 不可做：禁 dropna;JSON null 非 NaN;禁破 scalar;types.ts 不改則前端 build 破。
- 邊界(≥2)：warmup null、單分位、全同值 diff=0、len==源 raw n。
- 驗證：M-lookahead early turnover/rank_change equal(atol 1e-12);mutation nodeid=`test_la0_lookahead.py::test_turnover_pit` 回退全域 qcut/rank→FAIL;**contract test nodeid=`test_la0_lookahead.py::test_turnover_array_len_and_warmup_null`(斷言 `len(array)==源 raw n` 且 warmup `[0,first_valid)` 為 JSON null)**;前端 `cd frontend && npm run build` 綠(types.ts `(number|null)[]` 相容);net_ic cost_drag 隨之變。

---

## Phase B4 — P0-3 preprocessor fit_mode 四出口
### Task 4.1 — `data_preprocessor.py` fit_mode 分流 + constant/coverage per-bar
- SPEC ref：[LA0-3.1]+[RULING-3]+[T3]+[T7]　目標：四出口;fit_mode 進 canonical schema;constant/coverage per-bar mask。
- 實作要點：
  1. `preprocess`/`winsorize`/`handle_missing`/`remove_constant_features`/`standardize`/`_select_fit_*` 加 `fit_mode`(**含 standardize,T7**);**`fit_mode` 進 `ic_config_schema.py` 的 `PreprocessingConfig` class + `config/ic_config.yaml`**;metadata 寫入點=stage1 log,重算入口=orchestrator。
  2. `unset`+None→raise;`pit_expanding`→用 pit_stats(mad 用 `pit_expanding_mad` 回 (median,mad) 算 `median±k*MAD`);`full_sample`→metadata `oos_guarantees=False`;`train_mask`→`pit_train_fit`。
  3. constant/coverage 用 **per-bar validity mask**(不一次 drop 全欄,T3)。
- 修改檔案：`data_preprocessor.py`(上列);`momentum/.../ic_config_schema.py::PreprocessingConfig`;`config/ic_config.yaml`。caller：`_stage1_preprocessing`。
- 不可做：禁 silent None;禁 global default=pit_expanding(schema default=unset)。
- 邊界(≥2)：`unset`+None→raise;`pit_expanding` n<100 no-op;constant 尾端才現;mad=0。
- 驗證：M-lookahead fit_mask=None+pit_expanding→early equal(atol 1e-12);mutation nodeid=`test_la0_lookahead.py::test_preproc_pit` 回退全樣本 fit→FAIL;`pytest.raises` unset+None;`pytest tests/momentum/test_data_preprocessor.py`。
### Task 4.2 — orchestrator fit_mode 注入 + fallback + refilter revalidate + deep key
- SPEC ref：[LA0-3.2]+[M3]+[M4]+[T7]　目標：全入口注入 mode;fallback 鎖 full_sample;refilter revalidate;deep key 含 version。
- 實作要點：
  1. orchestrator(`:2154-2156`)全入口注入 fit_mode(split ON→train_mask;OFF→pit_expanding)。
  2. `_run_full_sample_fallback`(`:1015`)呼叫前注入 `fit_mode=full_sample`。
  3. `_compute_deep_cache_key`(`:1738`)含 `pit_stats_version`+`fit_mode`;**refilter(`:1505` 無獨立 key)**→前檢查 `_ic_cache.metadata` version/mode 不符 invalidate 重算。
- 修改檔案：`ic_filter_orchestrator.py::_stage1_preprocessing,_run_full_sample_fallback,refilter,_compute_deep_cache_key`。
- **遷移矩陣(M3,全 nodeid,T6/codex 提供)**:先 grep 全 `DataPreprocessor(...).preprocess(`。真 nodeid=`test_ic_1a_cut1_leakage.py::test_preprocess_legacy_no_mask_unchanged`(**改 `pytest.raises`=強化**)、`test_ic_1a_cut1_oos.py::test_winsorize_type_branch_uses_train_slice_only`、`test_data_preprocessor.py::{test_preprocess_handles_winsorize_missing_and_constant,test_preprocess_empty_df_raises}`;orchestrator:2156(train_mask 注入);**新建獨立 `full_sample` escape 測試**(名 `test_preprocess_full_sample_escape`);deep key API test 真路徑=**`tests/api/test_ic_deep_analysis.py`**(非 momentum;:735 是 cache-key call → **另建 fit_mode API test**)。**不列** `profile_gate3_to_4.py`(FeatureEng)。
- 不可做：禁 raise 發生在 analyze() happy path;禁改既有 assert 過測。
- 邊界(≥2)：空 mask、全 True mask、fallback 注入、refilter version 不符 invalidate。
- 驗證：invariant:所有進 `_stage1_preprocessing` 路徑 `fit_mode!=unset`;raise 不發生在 happy path;refilter version 不符 invalidate 斷言;train_mask control 排尾→train 段 equal;`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py`。

---

## Phase B6 — 測試/golden/freeze + 三方簽核
### Task 6.1 — M-lookahead 入庫 + golden 重基準 + 歸因表 + 跨 symbol oracle
- SPEC ref：[LA0-5.1]+[RULING-4]+[§G L2]+[T8]　目標：mutation 入庫;修後 golden vs B0;歸因表填數值;跨 symbol perturb oracle。
- 實作要點：
  1. `tests/momentum/test_la0_lookahead.py` 集中各 P0 mutation(nodeid 見各 Task,修前紅/修後綠);每 mutant 附 patch fixture + expected fail。
  2. 跑修後 vs B0 baseline,填 `tests/golden/la0/attribution.json`(用 B0 predeclare allowlist schema);只填 before/after/delta,禁增 expected。
  3. **跨 symbol oracle(T8,nodeid)**:`test_la0_lookahead.py::test_cross_symbol_isolation`(BTC-only perturb→ETH hash unchanged);`test_la0_lookahead.py::test_attribution_schema_valid`(attribution JSON schema validator)。
  4. **S2 簽核**:turnover time_series len n-1→n 列入三方 DATA-CORRECT 明確簽核項。
- 修改檔案：`tests/momentum/test_la0_lookahead.py`(新建);`tests/golden/la0/attribution.json`。
- 不可做：禁放寬既有斷言;分類禁全標 expected;control 列 Δ≠0→FAIL。
- 邊界(≥2)：BTC perturb→ETH 不變;control 列 |Δ|≈0 否則 FAIL。
- 驗證：`pytest tests/momentum/` 全綠;歸因表無 unexpected 且 control-stable;跨 symbol oracle pass;**三方 DATA-CORRECT 簽核**(分類另一委員 receipt 覆核 + S2 size 明確簽);雙 symbol hash 並列。

---

## SPEC ID 100% 覆蓋追溯表
| SPEC ID | 節錄 | TODO |
|---------|------|------|
| LA0-0.1 | 七原語 | Task 1.1 |
| LA0-1.1 | rolling IC 窗內 rank | Task 2.1 |
| LA0-2.1 | mono PIT | Task 3.1 |
| LA0-2.2 | turnover PIT | Task 3.2 |
| LA0-3.1 | preprocessor fit_mode | Task 4.1 |
| LA0-3.2 | orchestrator+refilter+deep key | Task 4.2 |
| LA0-4 | **FR descoped(移出)** | — (1c-FR-FULL epic) |
| LA0-5.1 | 測試/golden/歸因 | Task 6.1 |
| RULING-1 | perf telemetry+Numba/chunk | Task 1.1/2.1 |
| RULING-2 | pit_pool mono | Task 3.1 |
| RULING-3 | fit_mode 四出口 | Task 4.1 |
| RULING-4 | 歸因 machine-readable | Task 0.2/6.1 |
| RULING-5 | turnover warmup null+size | Task 3.2 |
| §P0-2-AGG | pit_pool 公式 | Task 3.1 |
| §G baseline | 可重現 reference | Task 0.1 |
| §G allowlist | predeclare | Task 0.2 |
| §G L1/L2/L3 | 三層 | Task 6.1+各 Task |
| S2 turnover size | n-1→n 簽核 | Task 3.2/6.1 |
| T1-T10 | reconcile 修補 | 已分散各 Task(見括註) |
| 合計 | 7 active Task IDs(LA0-4 descoped)+5 RULING+§P0-2-AGG+§G+S2+T1-10 | 全覆蓋 |

**Frozen 狀態**：`Internal DRAFT v2` — 待 TODO adversarial 複驗(`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`),Blocking 修補後 Frozen。
`SPEC=docs/IC_LA0_SPEC.md TODO=docs/IC_LA0_TODO.md FOCUS=T1-T10 閉合 + 冷啟動可執行性`
