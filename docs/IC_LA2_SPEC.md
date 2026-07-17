# IC-ANALYSIS-LOOKAHEAD Phase LA-2(P2) — SPEC

> **版本 v0.5**(Claude 起草;R1+R2+R3+R4 各三家 adversarial 全 REJECT→重寫;reconcile `handoffs/LA2-SPEC-ADV-R{1,2,3,4}-RECONCILE.md`)。來源 `handoffs/LA2-RECON-SYNTHESIS.md` 四方偵察。
> **v0.5 修訂(R4)**:V5-1 OOT 改**嚴格 `<`**(修 `≤` off-by-one eval 首 bar 洩漏,grok R4-B1);V5-2 winsorized 定案禁用→§G 移出 baseline/mutation(oracle=raises,codex NEW-1);V5-3 DEC-3 加 close carrier 進 `_ic_cache`(codex NEW-2);V5-4 cross_symbol 本票不做 oot 分支(對齊 §N,codex NEW-3);V5-5 §V skip 同步 OMITTED;V5-6 regime 殘句同步(參數已刪);V5-7 horizon=row 空間 bar 數;V5-8 命名 rename 非並存;V5-9 compound 鎖 connective;V5-10 表逐列單 enum;V5-11 全路徑;V5-12 刪 §C 重複 server 段+補 metadata。B 邊界三家接受(安全語義留 SPEC/結構歸 TODO)。
> **v0.4 修訂(R3)**:A1 engine 不得 silent 回退(修矛盾);A2 train_auc 命名收斂單一(`in_sample_train_auc`+`fit_pool_auc`);A3 compound rule DTO 無損 round-trip;A4 cross_symbol 有 LOSO receipt 才 ok;A5 DEC-1 定案禁用(非待裁)+移除 config 宣告;A6 regime 單一移除(非 or raise);A7 欄位表純三 enum+補欄;A8 skip 單一 union(缺集 metrics omit+deny,違序 hard raise);A9 server guard 涵蓋 create+PUT;A10 OOT horizon/bar/embargo 單位鎖+既有 pair 不足須新 check;A11 DEC-3 lag≥1 鎖;A12 行號 warn@1016/lgbm recommend_k@651。**B(SPEC/TODO 邊界裁決)**:receipt/plan-hash/nested-path/discriminated-union 確切結構歸 TODO,SPEC 只鎖要求(不可偽造/fail-closed/同一 plan identity)。
> **v0.3 修訂(R2)**:R2-1 OOT 恆真式改可證偽;R2-2 綁 canonical `SplitPlan`(刪自造 SplitManifest);R2-3 欄位級 allowlist 閉集表;R2-4 OOF receipt;R2-5 service 全矩陣+LGBM;R2-6 pattern 晉升 server;R2-7 caller cutoff;R2-8 calibrator receipt;R2-9 DTO migration;R2-10 DEC-1;R2-11 final gate;R2-12 skip;R2-13 regime;R2-14 factor typed;R2-15 DEC-3;R2-16 config;R2-17 行號。
> 前身:LA-0(P0)、LA-1(P1)已合併 main。`momentum/Analysis/pit_stats.py` 七原語(`la0_b1_v1`, `MIN_SAMPLES=100`);**canonical split 契約** `momentum/core/contracts.py:360 SplitPlan`(row_index/time_bounds/purge_gap/embargo/base_universe_hash/symbol + fail-closed `SplitPairLeakageError`/`CrossSymbolLeakageError`)。權威盤點 `handoffs/ICLOOKAHEAD-MASTER.md` P2 節。**本 phase = IC look-ahead epic 最後一站**(收官 LA-1 §N `_fit_global` 殘留)。

## §RISK 風險分級
- **大小**：**大**。
- **命中高風險原則**：(a) 數值/資料品質、(b) 跨模組共用路徑(label_generator/lightgbm/xgboost analyzer/pattern_extractor/regime_detector/factor_* + orchestrator + api services + 前端)、(c) 多 phase(B0-B4)、(d) ML/回測正確性(in-sample 樂觀診斷偽造可部署品質 + label/門檻 look-ahead)。
- **RISK-HIT 宣告**：
RISK-HIT: a,b,c,d
- → §G Golden 必填、adversarial review 必跑(三家)。
- **taxonomy 三分 + 軌2(修法/oracle 不得跨類借用)**：
  - **類 C-1 causal-PIT(截未來 bar→早期輸出變;修=PIT/train-fit)**：winsorized(**定案禁用**,oracle=raises 非 early-flip)、regime `_fit_global`(移除)。mutation=M-lookahead(early flip 改前>0 改後=0,atol=1e-12)。
  - **類 C-2 promotion-train-mask(截 bar 洩漏+晉升鏈固化;修=train-mask 門檻+train-y 統計+OOT 晉升+server guard)**：pattern_extractor 門檻/confidence/lift。mutation=M-lookahead(門檻 flip) **且** 晉升 provenance oracle(缺 OOT receipt→fail-closed)。
  - **類 C-3 diagnostic-loud(全樣本 fit 但 report-only 不進 gate;修=loud 標註,不改算法)**：factor_orthogonalizer/factor_exposure。oracle=loud 欄位存在+factor OFF control deep-equal;**不列軌1 early-flip**。DEC-3 proxy 因果化=獨立數值 class。
  - **軌2 in-sample 樂觀(截 bar 不變 fit 集指標,但高估可部署品質;修=eval_scope 契約+SplitPlan provenance/embargo)**：model 診斷(cal/PR/train_auc)+ service 全矩陣。mutation=provenance oracle(§C-OOT;非截 bar、非 metric 排序)。
  - **鐵律**:C-3/軌2 禁用 C-1 截 bar early-flip 充數;C-1/C-2 禁只測「欄位存在」假綠。

## §A 假設與待使用者確認

**已驗證事實(FACT-RECEIPT,四方真 kline 實跑;R1/R2 三家行號釘正;golden sha256 見 §G)：**
- FACT-RECEIPT: P2-① winsorized — `label_generator.py:79` `ret.quantile(0.01/0.99)` 全序列;`generate_returns_by_type` def@**:82**、dispatch@:95;BTC/1h early n_changed=**298** max|Δ|=1.23e-3;ETH/12h early_equal=false;PIT/train-fit early_equal=true;simple control=0（四方 2026-07-17）
- FACT-RECEIPT: P2-① 零產線 — `rg 'return_type.*=.*winsorized'` 產碼=0(僅 `momentum/Analysis/ic_config_schema.py:43-52` Literal+dispatch+test);預設 `config/ic_config.yaml:27 simple`;前端 tip 無 winsorized（四方）
- FACT-RECEIPT: P2-① 附帶 — ①死欄位 `ic_config_schema.py:52 winsorize_returns=True`(零 reader) ②`ic_engine._compute_returns` def@**:1010** warn@**:1016** 對**一切**非 simple/log 回退 simple(含 excess/risk_adjusted),與 orch `:2400` 硬接 return_type 分歧（grok M5）
- FACT-RECEIPT: P2-② 全樣本診斷 — `lightgbm_analyzer.py:359 predict_proba(X_ordered)`(train∪val)→:360 train_auc/:367 cal/:368 pr 全樣本;`xgboost_analyzer.py:448` train_auc 只 X_train 但 `validate_model:1147-1174` 又全樣本;`validate_oot`(lgbm:415/xgb:1298)只驗長度（四方+codex B-04）
- FACT-RECEIPT: P2-② service 全矩陣 — task `xgboost_task_service.py`:`get_predictions:256`/`recommend_k`(def@`xgboost_analyzer.py:683`,precision@K def@:627)/`permutation:315`/`fold_importance:321`/`shap:326`/`feature_importance(_all):234`;batch `xgboost_batch_service.py`:feature_importance@734/739、recommend_k@803、permutation@860、shap@894;**LGBM 通用路徑** `api/services/model_task_service.py:88-90`（codex B6+composer）
- FACT-RECEIPT: P2-② config 債 — `config/model_config.yaml:47 probability_calibration.enabled=true`/`:65 sample_weight.enabled=true` 但 `train_model` 無 sample_weight 參、無 wiring;`model_enhancement_service.py:255` 優先 `fit_from_predictions` 繞過 `fit`;`probability_calibrator.py fit@43 / fit_from_predictions@64` 無 provenance 輸入（codex B-09）
- FACT-RECEIPT: P2-③a factor — 預設 OFF(`ic_config_schema.py:231-238`);advanced UI 開;`run_deep_analysis`(orch:1835-1840)不改 stage5/6 gate;GS leak `factor_orthogonalizer.py gram_schmidt:25-68`;`_run_factor_exposure market_proxy=label_series`(forward,`ic_filter_orchestrator.py:2107`);factor result 進 `ic_models.py:219-226 results:Dict[str,Any]`(無 typed boundary)（四方,行號釘正）
- FACT-RECEIPT: P2-③b pattern — `pattern_extractor.py:149,199` 全樣本 quantile 門檻 + `base_prob@:119`/`confidence=y[mask].mean()@:165` 全樣本;`extract_decision_rules:58-66` 無 split 參;caller `xgboost_task_service.py:249`/`xgboost_batch_service.py:751` 傳全樣本;不進 IC gate;晉升 `page.tsx saveAsPattern@408`→`:417 threshold:rule.confidence`(bug+compound 壓成單 feature/operator 固定`>=`)+持久化 `train_auc` 無 scope→`create_pattern@34`(pattern_management_service)`status='active'@:82` 不驗 provenance;`CreatePatternRequest`(`pattern_management_models.py:27`)收 client `performance_metrics:Dict`;LGBM batch(:747)跳過 pattern（四方+行號釘正）
- FACT-RECEIPT: P2-③c regime — `regime_detector.py:143-146` expanding=False→`_fit_global:217-230` 全期 KMeans;ETH/12h flip=**975/1416(68.9%)** BTC/1h 487;expanding=True flip=0;caller 鎖 True(`ic_engine:1220-1223`+`detect_phases_for_index:164-181`);依賴 False 的 test:`tests/test_regime_detector.py:86-356`+`tests/momentum/test_la1_lookahead.py:575-628`（codex B-08）
- 註:各家 flip 精確數因 symbol/method 不同;mutation 以 `tests/golden/la2/gen_baseline.py` 內嵌為 canonical,不鎖口頭數字。

**待使用者確認(白話檢查點決策)：**
- **DEC-1 winsorized(定案=禁用;白話階段為使用者否決權,非「未定」)**：四方一致=零產線→**禁用**。**本凍結版 SPEC 依禁用撰寫且為定案(B1 含移除 config/schema 宣告)**;白話階段使用者若**否決**要保留→另立 `DEC-1-KEEP` delta addendum(train-fit 邊界 mini-spec,類 C-1),不改本凍結(A5 消歧義)。
- **DEC-2 config 債(calibrator/sample_weight 未接線)scope**：預設=本票加不可偽造 provenance receipt 契約 + 標 `enabled≠wired`;完整接線+PIT sample_weight 另立 productionization epic。
- **DEC-3 factor market_proxy=forward label**：預設=本票並修(proxy 改 trailing close-ret,契約見 §C),獨立 class `P2-3a-proxy-causal`;白話階段確認 vs 另票。

**已確認結果**：
- **已確認(2026-07-17 使用者)**：裁定全力 Phase 1(LA-2→1c-FR-FULL→1d→1f),LA-2 下一站;P2 scope 三面來自 master P2 節。
- 本 phase 收官 LA-1 §N `_fit_global` 完整因果化(既定 mandate)。
- DEC-1 定案禁用(白話階段=否決權);DEC-2/3 待白話檢查點使用者裁;修法選型(taxonomy/pattern promotion/OOT provenance/regime 移除)為 R1+R2+R3 九輪 adversarial 收斂,走委員會不問使用者。

## §C 約束

### C-基本
- 解耦 7 條不變(`momentum/` 不 import `api/`;原語留 `pit_stats.py`)。
- RULING-3(LA-0)/LA-1 loud 家族:degraded 鎖可觀測欄位(`analysis_status`/`oos_guarantees`);C-3 factor loud 沿用,不另創欄位語意。§MS min_samples=100。
- taxonomy 不得跨類借用;禁 weaken NaN/inf gate;禁 metric 排序(IS>OOT)當 OOS 證明;禁「impl 前委員定」式 defer。

### C-OOT/OOF 契約(R2-1/R2-2/R2-4 + R3-A10,復用 canonical `SplitPlan`,可證偽)
- **一律復用 `momentum/core/contracts.py:360 SplitPlan`**(train/val/test 各一;row_index/time_bounds/purge_gap/embargo/base_universe_hash/symbol);**禁自造 split 型別**。跨 symbol/timestamp 沿用既有 `CrossSymbolLeakageError`/`TimestampDiscontinuityError`。
- **canonical 單位/來源(A10+V5-7,寫死)**:`horizon`=**該 model 的 label horizon(bar 數;`config` label horizon,多值任務用該次分析步數)**;**check 在 row-index 空間做**(horizon=bar 數,不需 bar_duration);`bar_duration` **僅** `index_kind=timestamp` 時=該 TF 固定間隔;**embargo 單位=rows**(對齊 SplitPlan `forbidden_end=end+purge_gap+embargo`)。
- **OOT horizon-aware check(A10+V5-1 嚴格不等式;既有 pair 不足)**:既有 `validate_train_test_pair`(`contracts.py:566-595`)**只查 row purge/embargo 禁區、不含 label horizon** → B2.1 須**新增** horizon-aware 檢查:
  `fit_label_end := max(fit_row_index) + horizon`(row 空間,label 觀測窗右端);**要求嚴格** `fit_label_end + embargo **<** min(eval_row_index)`(**嚴格 `<`,非 `≤`**;等號會放行 eval 首 bar 洩漏;timestamp 空間 `max(fit_ts)+(horizon+embargo)*bar_duration < min(eval_ts)`)。違反→`SplitPairLeakageError`(fail-closed)。反例:train 尾 row=96、horizon=5、embargo=0、eval_start=**101** → 96+5=101,`101<101`=False → **FAIL**(擋 `close.shift(-5)`@96 讀 close[101]=eval 首 bar;`≤` 會誤放)。
- **OOF 不可偽造(安全語義留 SPEC;確切結構 TODO)**:每筆 OOF pred 綁「未含該列的 fold model artifact」;receipt 必含 `split_plan_hash`(=hash(SplitPlan.row_index))+`fit_idx_hash`+`eval_idx_hash`+`model_artifact_digest`+`trusted_issuer`,`fit_idx∩eval_idx=∅`;**允許** eval_index ⊆ 全 train pool(不誤殺)。binding checker 由 artifact digest **重算比對**;不符/缺→fail-closed(禁「有 receipt 欄位」空殼)。反例:完整模型產全 pred + 真 model_artifact_id + 假 fit_idx_hash → digest 重算對不上 → FAIL。
- **LOSO receipt(A4 安全語義)**:cross-symbol 若要 `oot` 分支,receipt 須證明 **held-out symbol ∉ train-symbol 集合 + 每 fold artifact digest**;否則→in_sample_research_only+deny(本票**不做** oot 分支,見欄位表 V5-4)。
- **plan identity(R2-2)**:pattern/model/calibrator **消費同一 `SplitPlan` instance 或同一 `plan_hash`**;跨模組 plan_hash mismatch → fail-closed(禁各造同 cutoff 不同 row_index 的 plan)。
- **receipt 不可偽造**:由**後端**從可信來源(SplitPlan + model artifact digest)產生,**禁信 client/前端 metadata**;consumer 無 receipt/不符 → fail-closed。

### C-邊界裁決(SPEC 鎖安全語義 / TODO 定結構;R3+R4 reconciler ruling,三家接受,供稽核)
**SPEC 必凍結安全語義**(不可淪 TODO 空殼):①receipt **最小欄位 + 推導**(`split_plan_hash=hash(row_index)`/fit·eval idx hash/artifact digest/trusted issuer/disjointness/**重算失敗即 deny**)②plan identity mismatch deny ③LOSO held-out/train-symbol 證據 ④discriminant variant 集合 + root/nested conflict **recursive deny**(見各 §C 條文)。
**只 TODO/B-task**:確切 dataclass 名、序列化 envelope、binding checker 函式名、`model_performance`/nested 欄位 **exact path inventory**(→B0.1 allowlist 逐欄 enumerate,漏標=FAIL)、factor discriminated union 型別名。理由:SPEC 鎖行為契約,否則淪實作碼(LA-1 R5 範式)。**B 邊界三家 R4 接受,不再開輪**。

### C-欄位級 eval_scope allowlist 閉集表(R2-3+A7,scope 欄**只准三 enum**,禁「或」/禁非 enum 值)
scope enum = `{oot, cv_oof, in_sample_research_only}`。`in_sample_research_only` 欄位 **consumer/promotion deny**。cal/PR **per-欄二選一**(擇定 oot XOR cv_oof,禁寫「或」)。B0 predeclare 於 `attribution_allowlist.json`(含下表 + nested `model_performance` 逐欄 exact path),漏標=FAIL。
| 欄位(analyzer+service) | scope(單一) | promotion/consumer |
|---|---|---|
| `train_auc`→`in_sample_train_auc` | in_sample_research_only | deny |
| `fit_pool_auc`(LGBM 含 ES-val 池化,A2) | in_sample_research_only | deny |
| `overfitting_score`(=in_sample_train_auc−cv_auc_mean) | in_sample_research_only | deny(不當泛化) |
| `precision`/`recall`/`f1_score` | cv_oof | research_only |
| `cv_auc_mean`/`cv_auc_std` | cv_oof | ok |
| `oot_auc` | oot | ok |
| `calibration_curve`/`brier`/`ece` | cv_oof | ok |
| `pr_curve`/`pr_auc` | cv_oof | ok |
| `precision_at_k` | oot | ok |
| `recommend_k`(threshold) | oot | ok(建 signal) |
| `expectancy`/`sharpe_proxy` | oot | ok |
| `bootstrap_ci` | oot | ok |
| `get_predictions`(train 列) | in_sample_research_only | deny |
| `get_predictions`(oot 列) | oot | ok |
| `feature_importance`/`feature_importance_all` | in_sample_research_only | deny |
| `permutation_importance` | in_sample_research_only | deny |
| `fold_importance_stability` | cv_oof | research_only |
| `shap_sample` | in_sample_research_only | deny |
| `regime_analysis`(model phase) | in_sample_research_only | deny |
| `cross_symbol_validation`(V5-4;本票不做 oot 分支,§N 只 B4 抽查) | in_sample_research_only | deny |
- **skip 語意(R2-12+A8,單一 response union,禁「或」)**:①**違序(fit_label_end 跨界)= hard raise `SplitPairLeakageError`**(不降級);②**缺 held-out/OOT 集 = metrics OMITTED(該欄不輸出)+ status reason + consumer/promotion deny**;**禁**保留 full-sample 值標 research_only 仍供 consumer 展示。

### C-晉升 server 權威(R2-6+A9+V5-12,涵蓋 create+PUT;單一權威段)
- 晉升(pattern 可交易/model promotion)旗標由**後端從可信 `task_id`→task 結果 receipt 推導**;**`CreatePatternRequest` 移除** client `rules`/`performance_metrics`/`xgboost_importance`/`case_id`/**任意 `metadata`**,改帶 `task_id`;server lookup 重建 rules/performance/scope。
- **create + PUT 兩路徑**(`api/routes/pattern_management.py:34-48` create、`:129-139` PUT update;service `:68-85`/`:190-229`)status='active' **iff OOT receipt 存在**否則 draft/拒;PUT 亦不得由 client `status`/`metadata` 直設 active。反例:無 OOT receipt 的 create/PUT(含偽造 metadata)設 active → server 無 receipt 鏈→拒。

### C-下游消費者(不得破)
- model 前端 `model_performance`(train_auc **rename→`in_sample_train_auc`(不並存舊名)**=已裁可接受,附 DTO/TS migration+對照);pattern 前端 `xgboost-analysis/page.tsx`;regime IC/XGBoost(已鎖 True);factor advanced report(typed boundary,見 B3.3)。

## §G Golden / Baseline（RISK-HIT a,d → 必填）
- **feature/kline 條件**：命中→真實 `data_cache/feature_klines/kline_cache.h5`;禁合成;B4 三方 DATA-CORRECT。symbol×TF=BTCUSDT/1h+ETHUSDT/12h(跨 symbol 隔離)。存 `tests/golden/la2/{gen_baseline.py, <sym>_<tf>_baseline.json, attribution_allowlist.json, attribution_validator.py, inputs/*}`。
- **baseline 內容(V5-2:winsorized 已 B1 禁用→不列 baseline/mutation,其 oracle=raises)**：C-2(pattern 門檻+confidence,element 級+early-flip manifest)+C-1(regime `_fit_global` 標籤,legacy 凍結供 removal 對照);C-3(factor GS/PCA/exposure 值,enabled=True);軌2(model 診斷+service 全矩陣+**fit/eval index identity hash**,供 provenance oracle)。名稱 sha256+value hash+NaN mask hash+index identity hash。
- **通過條件(可證偽,分尺度)**：
  - **control deep-equal**：`return_type=simple`、regime 預設 PIT(參數已刪,V5-6)、`factor enabled=False`、pattern **未呼叫 extract 的 IC/model 預設**(extract 本身=修改路徑) → 改前==改後 byte 級。
  - **C-1 winsorized oracle(V5-2,禁用→非 early-flip)**：`return_type=winsorized`→三層 raise(§P B1.1);**不列 early-flip mutation**(路徑已刪)。
  - **C-1 regime oracle**：`_fit_global`/`expanding` 移除後不可達(正向斷言);legacy baseline 供 removal 歸因。
  - **C-3 factor oracle**：enabled=True→payload 含 `oos_guarantees=false`/`fit_scope="full_sample"`(typed module result,無則 FAIL);GS/PCA 數值 deep-equal(算法不改);DEC-3:`market_proxy` 不含 forward label(見 §C DEC-3 契約)+ exposure 數值變歸 `P2-3a-proxy-causal`。
  - **C-2 mutation**：截未來→pattern 門檻/confidence early flip 改前>0 改後=0(train-mask/train-y 後);pattern 缺 split→extract fail-closed。
  - **軌2 provenance oracle(§C-OOT;嚴格 `<`;非 gap 排序、非 naive subset)**：`oot`=`fit_label_end+embargo **<** min(eval_row_index)`(SplitPlan;餵 train row/違序/等號邊界→`SplitPairLeakageError`);`cv_oof`=per-fold `fit_idx∩eval_idx=∅`+model_artifact_digest 重算(合法 OOF 不誤殺);`in_sample_research_only`=欄位標記+consumer/promotion **deny 斷言**;缺 held-out→metrics OMITTED(非展示)。
  - **歸因表 schema**：`attribution_allowlist.json` — `schema_version`+`class_enum ∈ {P2-1-disable, P2-2-oot, P2-2-scope-tag, P2-3a-factor-loud, P2-3a-proxy-causal, P2-3b-pattern-trainmask, P2-3b-promotion-guard, P2-3c-regime-remove}`+`rows[]`(exact JSON path+index+old/new discriminator)+unlisted diff=FAIL;**wash ≥5 打紅**(validator `attribution_validator.py`):①竄改 control 塞 diff ②軌2 全樣本值標成已修 OOT ③刪 loud/scope 欄稱已標 ④wrong-class swap ⑤擅擴 allowlist。
  - **mutation canonical + 可重放**：dataset sha 寫死 gen_baseline;M-trunc 前 75%、early 前 2/3 內嵌;`python tests/golden/la2/gen_baseline.py --check` 單命令。

## §P Phase 與依賴
**DAG**：`B0 → {B1, B2, B3 可並行} → B4`。修改 legacy 輸出不得早於 B0。

### Phase B0 — baseline 凍結 + 測試骨架（依賴：無）
**Task B0.1** — legacy P2 baseline
- 檔案：`tests/golden/la2/gen_baseline.py`+`attribution_validator.py`。凍結五面+control+軌2 index identity;allowlist predeclare(含 §C 欄位表逐欄 scope)。
- 驗證：`python tests/golden/la2/gen_baseline.py --check` sha atol=1e-12;C-1/C-2 分層 manifest 可翻轉;軌2 index identity 記錄。不可做:合成 fixture;aggregate-only。

**Task B0.2** — 測試骨架(R2-11)
- 檔案：`tests/momentum/test_la2_lookahead.py`。predeclare nodeid:`test_winsorized_disabled`/`test_model_oot_contract`/`test_model_service_oot`/`test_calibrator_receipt`/`test_pattern_train_mask`/`test_pattern_promotion_guard`/`test_regime_no_global_fit`/`test_factor_loud`/`test_adversarial_validator_diagnostic_only`(§N 最小標註)。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py --collect-only` 列全 nodeid(骨架 xfail,B1-B3 填實);glob 非 0。**B4 final gate 禁殘留 skip/xfail**。

### Phase B1 — P2-① winsorized 禁用（依賴：B0;DEC-1 凍結版=禁用）
**Task B1.1** — winsorized fail-closed(三層,固定 reason-code)+ 死欄位移除 + engine/orch 全 Literal 對齊
- 檔案：`momentum/FeatureEngineering/labels/label_generator.py:82,95`、`ic_filter_orchestrator.py:2400`、`ic_engine.py:1010-1016`、`ic_config_schema.py:43-52`、`config/ic_config.yaml:27-30`。
- 改法：①**三層同一 reason-code literal(R2-M8)**:generator `generate_returns_by_type` winsorized→raise(固定 `LOOKAHEAD_LABEL_UNSUPPORTED` reason)+schema Literal 移除 winsorized(Pydantic 422 帶同 reason)+orch fail-closed;測試覆蓋三層。②移除死欄位 `winsorize_returns` + `config/ic_config.yaml:27-30` winsorized/winsorize_returns 宣告(A5;grep reader=0)。③**engine `_compute_returns` 不得 silent 回退(A1,修 v0.3 矛盾)**:對非 simple/log **不 silent fallback simple**;winsorized→raise(同 reason-code);excess/risk_adjusted→**統一走 `LabelGenerator` dispatch**(與 orch 同源)或明確 raise;附各 return_type 兩路徑**一致**行為表(禁 engine simple / orch 硬接的分歧)。
- 驗證：`test_winsorized_disabled` — winsorized→三層 raise(reason-code 一致,任一層漏→FAIL);simple/log/excess/risk_adjusted engine==orch(atol=1e-12,禁 engine silent simple);`winsorize_returns` reader=0+yaml 宣告移除;行為表逐列一致。
- 不可做：engine silent 回退;留死欄位/yaml 宣告;只測一層。

### Phase B2 — P2-② model OOT-only 契約（依賴：B0）
**Task B2.1** — analyzer 診斷 eval_scope 契約 + SplitPlan provenance/embargo
- 檔案：`lightgbm_analyzer.py:355-374,415-426`、`xgboost_analyzer.py:445-465,1147-1174,1298-1343`、`calibration_analyzer.py`。
- 改法(軌2,禁 PIT/禁 metric 排序)：①**命名收斂單一(A2)**:`train_auc`→`in_sample_train_auc`(canonical);LGBM 含 ES-val 池化 AUC=**獨立欄位** `fit_pool_auc`(非第三套;兩者 in_sample_research_only);`overfitting_score=in_sample_train_auc−cv_auc_mean` 公式跟改名。②cal/PR/Brier/ECE→per-欄擇定 oot XOR cv_oof(§C 表)+ `eval_scope` 欄位;LGBM/XGB **路徑對稱**。③**OOT horizon-aware check(A10+V5-1 嚴格 `<`)**:`validate_oot` 綁 **SplitPlan** + **新增** horizon check `fit_label_end(=max(fit_row_index)+horizon)+embargo **<** min(eval_row_index)`(**嚴格 `<`,非 `≤`**;既有 `validate_train_test_pair` 只查 row 禁區不含 horizon,不足);④**skip 單一 union(A8)**:**違序(跨界)= hard raise `SplitPairLeakageError`**;**缺 held-out/OOT = metrics OMITTED(該欄不輸出)+ status reason + deny**(禁保留 full-sample 標 research_only 仍展示)。
- 驗證：`tests/momentum/test_la2_lookahead.py::test_model_oot_contract` — 欄位帶 `eval_scope`(§C 三 enum 逐欄);OOT horizon check `fit_label_end+embargo **<** min(eval)`(train 尾 row96+h5+embargo0=101 vs eval_start=**101**→`101<101`False→FAIL,等號邊界可證偽;既有 pair 會漏放);OOF per-fold `fit_idx∩eval_idx=∅`+artifact digest(合法 OOF 不誤殺);`in_sample_train_auc`/`fit_pool_auc` 命名+deny;缺 held-out→metrics omit(非 research_only 展示)。
- 不可做：截 bar mutation 充軌2;metric 排序;naive index-subset。

**Task B2.2** — service 全矩陣 scope + calibrator receipt + config 債 + DTO/前端 migration
- 檔案：`api/services/xgboost_task_service.py:234-409`、`api/services/xgboost_batch_service.py:734-1009(含 cross_symbol:907-933)`、`api/services/model_task_service.py:85-91(LGBM)`、`api/services/model_enhancement_service.py:251-275`、`probability_calibrator.py:43-70`、`xgboost_analyzer.py:683(recommend_k)`+`lightgbm_analyzer.py:651(lgbm recommend_k)`、`api/models/pattern_analysis_models.py:554-570`、`frontend/src/lib/patternTypes.ts:158-177,287-303`、`frontend/src/app/patterns/xgboost-analysis/page.tsx:154-161`、`frontend/src/components/pattern/CreatePatternForm.tsx:109-122`。
- 改法：①**逐欄 scope(§C 三 enum 表)**:含 `feature_importance(_all)`/`regime_analysis`/get_predictions/recommend_k(xgb:683+lgbm:651)/permutation/fold/shap/precision/recall/f1/precision@K/expectancy/bootstrap;recommend_k→OOT;importance/SHAP→research_only+deny;**`cross_symbol_validation`(V5-4):本票標 `in_sample_research_only`+deny(不做 oot 分支,對齊 §N;batch:907-933 全路徑同標;未來 LOSO receipt 另票)**;**LGBM `model_task_service` 路徑同步**(防不對稱假綠)。②**calibrator receipt(R2-8,要求級)**:`fit`+`fit_from_predictions` 兩分支共用不可偽造 receipt(必含 `split_plan_hash`/`model_artifact_digest`/issuer,結構歸 TODO);signal-facing 缺→fail-closed(非 warn/自由 dict)。③**config 債(R2-16)**:`config/model_config.yaml:47-74` enabled 但未 wired→config reader/DTO/UI 標 `enabled≠wired`+測試證(runtime 不受 yaml 控)。④**DTO/前端 migration(R2-9/A2/V5-8 rename-only)**:`train_auc`→`in_sample_train_auc`(+`fit_pool_auc`)**rename(不並存舊名)** + DTO/TS/UI/CreatePatternForm 同步 + 測試。
- 驗證：`tests/momentum/test_la2_lookahead.py::test_model_service_oot` — 全矩陣逐欄 scope(§C 表);recommend_k OOT(餵全樣本→FAIL);importance/shap research_only+deny;LGBM 路徑同標;`test_calibrator_receipt` — 兩分支缺 receipt→raise(可證偽);config `enabled≠wired` 標註+測試;DTO/TS train_auc 改名不破前端(migration 測試)。
- 不可做：完整接線 sample_weight(另票);warn 代 fail-closed;漏 feature_importance/LGBM 路徑。

### Phase B3 — P2-③ 條件模組（依賴：B0;可與 B1/B2 並行）
**Task B3.1** — regime `_fit_global` 硬移除 + 逐測試遷移(P2-③c,C-1)
- 檔案：`regime_detector.py:111-146,217-230`。caller `ic_engine:1220-1223`/`detect_phases_for_index:164-181`(已 True)。
- 改法(R2-13+A6,**鎖單一方案**)：**移除 `expanding` 參數 + `_fit_global` 方法**(**非「或 raise」二選一**;徹底刪逃生口);`detect` 固定 PIT Segment-causal(承 LA-1 B1.3);`detect_phases_for_index` 移除傳 expanding=True(參數不存在);**逐測試遷移表(TODO 落每 nodeid→改法)**:`tests/test_regime_detector.py:86-356`(每個 expanding=False→改 expanding path,禁只 mark skip)+`tests/momentum/test_la1_lookahead.py:575-628`(LA-1 residual 改「參數不存在」斷言)。
- 驗證：`test_regime_no_global_fit` — `detect(expanding=False)` raise/參數不存在 + `_fit_global` 直呼不可達(**正向斷言 `_fit_global` 已移除**,可證偽:能全期 fit→FAIL);產線 caller deep-equal(atol=1e-12);遷移後 `pytest tests/test_regime_detector.py tests/momentum/test_la1_lookahead.py` 全綠(**非 skip**)。
- 不可做：保留雙路徑;只 public raise 留 `_fit_global` 逃生口;靜默 skip 舊測試。

**Task B3.2** — pattern train-mask + SplitPlan caller 契約 + train-y 統計 + 晉升 server 閉環(P2-③b,C-2)
- 檔案：`pattern_extractor.py:58-66,119,149,165,199`、`api/services/xgboost_task_service.py:249`、`api/services/xgboost_batch_service.py:751`、`api/services/pattern_management_service.py:34,68,82,190-229`、`api/models/pattern_management_models.py:12-29`、`api/routes/pattern_management.py:34-48,129-139`、`frontend/src/app/patterns/xgboost-analysis/page.tsx:408,417`、`frontend/src/lib/patternTypes.ts`、`frontend/src/components/pattern/CreatePatternForm.tsx:109-122`。
- 改法(第三類 promotion-train-mask)：①**caller 契約(R2-7)**:`extract_decision_rules` 加 `split: SplitPlan`(必填,`split_label='train'` 硬鎖,復用 §C plan identity);mask ≡ `train_model` 時序 train 段(**固定絕對 cutoff**,禁 random/比例重切/禁傳 test/OOT 段);缺→fail-closed。②**train-y 統計(R2-M6,禁 OOT 逃生)**:quantile 門檻+`base_prob@:119`+`confidence@:165`+lift **一律 train-y-only**(非「或 OOT」;晉升時另計 OOT lift)。③**晉升 server 閉環(R2-6+A3+A9)**:`CreatePatternRequest`(`pattern_management_models.py:20-29`)**移除** client `rules`/`performance_metrics`/`xgboost_importance`/`case_id`→改帶 `task_id`;server lookup 可信 task 結果**重建** rules/performance/scope;**create + PUT 兩路徑**(`pattern_management.py:34-48`+`:129-139` update)status='active' **iff OOT receipt** 否則 draft/拒(PUT 亦不得 client 直設 active);`in_sample_rules` server 推導;**compound rule DTO(A3+V5-9 鎖 connective)**:`PatternRuleRequest:12-17` 單 feature/operator/threshold→支援 `feature_conditions[]` compound,**鎖 connective=AND、順序保留、空集拒、每條 feature/operator/threshold/description 無損 round-trip 否則 extract 拒**(`page.tsx:417` 壓成單 feature 修正);修 threshold=condition 分位值(非 confidence);移除 client `metadata`;持久化 `in_sample_train_auc` 帶 scope。
- 驗證：`test_pattern_train_mask` — 缺 split/傳非 train split→extract fail-closed;trunc 未來→門檻/confidence early_equal(改前 flip>0 改後=0,train-y-only);`test_pattern_promotion_guard` — 偽造 client metadata/importance POST→拒(create+PUT 兩路徑,server 級,可證偽);缺 OOT receipt→status≠active;threshold=condition 分位值;compound rule 無損 round-trip。
- 不可做：等同 IC-gate 全族 PIT;純 loud 無 train-mask;信前端 metadata/importance;比例重切;confidence 用 OOT 逃生。

**Task B3.3** — factor typed loud boundary + market_proxy 因果化(P2-③a,C-3 + proxy class)
- 檔案：`factor_orthogonalizer.py gram_schmidt:25-68`、`factor_exposure_analyzer.py:46-73`、`ic_filter_orchestrator.py:2082-2115`、`api/models/ic_models.py:219-226`、`api/services/ic_analysis_service.py:255-265`。
- 改法：①**C-3 typed loud(R2-14)**:factor module result = **typed contract**(非 `Dict[str,Any]`)含 `oos_guarantees=false`/`fit_scope="full_sample"`;root `ok_oos` 與 nested factor degraded 並存時 consumer/export **deny gate**;GS/PCA 算法不改;orthogonalized 矩陣若 advanced export→標 research_only deny(不重寫算法)。②**DEC-3 proxy(獨立 class,契約 R2-15+A11 鎖值+V5-3 carrier)**:`_run_factor_exposure market_proxy=label_series`(forward,:2107)→trailing close-ret。**close carrier(V5-3,codex NEW-2)**:現 `_ic_cache`(orch:3119-3133)**未存 close**→本票**新增 close 進 `_ic_cache`**(明列 scope,proxy 才拿得到 trailing close,否則實作被迫重用 forward label 重犯洩漏)。**鎖**:`lag≥1`(decision-ts=**前一 bar close**,不見當 bar close)、frequency=該 TF、return 定義=`close.pct_change().shift(1)`、NaN drop 對齊、typed payload;exposure 數值變歸 `P2-3a-proxy-causal`。
- 驗證：`test_factor_loud` — enabled=True→typed payload 含 `oos_guarantees=false`/`fit_scope`(無則 FAIL);root ok_oos+nested degraded→consumer deny;GS/PCA deep-equal(atol=1e-12);factor OFF control deep-equal;market_proxy 契約(不含 forward label+決策時點不見當 bar close)+exposure 變歸 proxy-causal class。
- 不可做：blanket PIT 重寫;proxy 數值變混進 loud class;`Dict[str,Any]` 無 typed gate。

### Phase B4 — tests/golden/歸因/三方 DATA-CORRECT（依賴：B1,B2,B3）
**Task B4.1** — 完整測試套 + golden 重基準 + 三方簽核
- 改法：golden 重基準(control byte-equal;歸因表 0 unexpected,class_enum §G);`attribution_validator.py` 擋 ≥5 wash;ETHUSDT/12h 隔離;軌2 SplitPlan provenance oracle。**final gate 禁 skip/xfail/--runxfail**+mutation coverage(R2-11)。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py tests/golden/la2/` 全綠(0 skip/xfail);三方 DATA-CORRECT(Claude+Codex+Composer PASS;Grok=實作者不簽);歸因表 0 unexpected、control deep-equal(atol=1e-12)、C-1/C-2 mutation 全紅+C-3 loud oracle+軌2 provenance oracle 全紅。
- 不可做：sanitized fixture;廉價綠燈;taxonomy 跨類混用;殘留 skip 充綠。

## §V 驗證策略與邊界測試目錄
- **mutation 條件(分類)**：C-1 winsorized→三層 raise(禁用非 flip)/regime `_fit_global` 移除不可達(atol=1e-12);C-2 pattern 門檻/confidence flip 改後=0 + 晉升 provenance(缺 OOT receipt/偽造 metadata→fail-closed);C-3 loud 欄位存在+control deep-equal(不用截 bar)+proxy-causal 數值歸因;軌2 SplitPlan provenance oracle(OOT `fit_label_end+embargo < min(eval)` 嚴格;OOF per-fold disjoint+artifact 綁定;research_only deny),**禁** metric 排序/naive subset。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級：單元/整合(orchestrator+service)/Golden/邊界。獨立 `pytest tests/momentum/` 跑。
- **防假綠**：diff 既有測試斷言;model/pattern schema 改名 migration(禁放寬換綠);validator 擋洗歸因;C-3/軌2 禁截 bar 充數;**final gate 禁 skip/xfail**。
- **邊界目錄(打勾)**：☑空DF ☑全NaN列 ☑無 held-out(軌2 metrics OMITTED+deny,非全樣本) ☑短樣本 ☑跨 symbol 隔離(SplitPlan CrossSymbolLeakageError) ☑winsorized 三層 raise ☑`_fit_global`/`expanding` 已移除不可達 ☑pattern 缺 split fail-closed ☑偽造前端 metadata 晉升被拒 ☑OOF 不誤殺 ☑embargo 不足被擋。

## §R 回退
- B0-B4 各獨立 commit 可單獨 revert。config flag(return_type/enabled)即逃生口(禁把驗過工作藏預設關閉;winsorized 禁用=移除洩漏能力非藏功能)。Golden control FAIL→不 merge。

## §N N/A 登記
- 無省略必填段。§RISK/§A/§C/§G/§P/§V/§R 全填。
- **scope exclude**：①sample_weight 完整接線+PIT(本票只 provenance 契約+標債;完整化歸 productionization epic,DEC-2)②`adversarial_validator`(train∪test 域分類刻意測 shift,非交易 signal;本票**最小標註** `diagnostic_only`+B4 一條 `analysis_status` 斷言 nodeid)③`cross_symbol_validator`(LOSO walk-forward,四方未 establish 洩漏,B4 抽樣複查)④feature winsorize(`data_preprocessor`)=LA-0 族**非本 P2**⑤factor orthogonalized 矩陣完整 PIT 重寫(本票只 typed loud+export research_only deny,不改算法)。
- **記錄非修(asymmetry)**：LightGBM batch(`xgboost_batch_service.py:747`)跳過 pattern rules(XGB 有晉升 LGB 無);本票 XGB 晉升鏈,LGB pattern asymmetry 記 §C 不強制對齊(但 B2.2 LGBM model_task_service 診斷 scope **要**同步,勿混)。
- **本 phase 收官**:`_fit_global`/`expanding=False` 於 B3.1 完整移除,IC look-ahead epic 全 phase(LA-0/1/2)收畢。
