# IC-LA-2(P2) TODO —（v0.4｜基於 `docs/IC_LA2_SPEC.md` v0.5（frozen, file sha `4b70bf7d…`）｜2026-07-18｜R1+R2+R3 各三家 REJECT 已修）

> **v0.4 修訂（R3，三家 18 項全修）**：U2 verify 四步補 oof disjointness；U3 canonical bytes 鎖 ndim==1（[1,2] vs [[1,2]] 同 bytes，codex 實跑）+canonical JSON 式；R3-4 envelope_digest 涵蓋 kind/version；R3-2 issuer server allowlist（tamper-evident 誠實邊界）；U8 ts array 參（discontinuity）；U14 raise 入口=四（補 engine `_compute_returns`）；U9 補 `test_detect_expanding_fit`+LA-1 residual nodeid 化；U11 batch+LGBM receipt 同鏈（無 receipt=不可晉升）；U12 覆蓋表定案句；R3-3 UI=`EngineConfigPanel.tsx`+`model_config.py:66-88`；N1 28 path；N2 §0.4 交叉引用正名；N3 `PatternOotReceipt` 別名入 §0.6-A；N4 晉升 OOT-lift 來源斷言；U15 LGB 記債正文（batch:748）；U17 deterministic 前 2 symbol；U18 marker 綁 consumer deny；R3-1 SPEC errata 2（SPEC:68 XOR 以 TODO cv_oof 為準）；U4 top-level→nested 遷移對照。

> **v0.3 修訂（R2，U1-U20）**：U1 刪 XOR（cal/PR=cv_oof only）；U2 verify 簽名加 model_artifact+重算步驟；U3 canonical sha256（禁 Python hash()）+envelope_digest；U4 predictions/importance RFC6901 拆列；U5 真 variant payload+`deny_factor_in_ok_oos` named verifier；U6 dataset sha literal 寫死；U7 幽靈 fn 名改正=`validate_split_pair_integrity:559`（SPEC errata）；**SPEC errata 2=SPEC:68「oot XOR cv_oof」以本 TODO cv_oof only 為準**（凍結 SPEC 不重開，TODO 權威）；U8 timestamp 分支 hard-fail；U9 regime nodeid→改法表嵌入（15+5 實列）；U10 model promotion 收口（現無 surface，§N 記）；U11 OotReceipt 寫入鏈；U12 DEC-2 cross-ref 修；U13 old→new migration map；U14 raise path 三入口寫死；U15 LGB 記債正文；U16 §0.10 min_samples；U17 cross_symbol 抽查具體化；U18 analysis_status 驗收；U19 B0 批內鎖序；U20 TODO 12 nodeid 為權威（SPEC B0.2 列 9 為凍結時未含 R1 新增，TODO 擴充合法）。

> **v0.2 修訂（R1，三家收斂）**：新增 **§0.6-APPENDIX** 確切結構（`OofReceipt`/`OotReceipt`/`CalibratorReceipt` dataclass+envelope+`verify_*` fn+`FactorModuleResult` union+`model_performance` RFC6901 全 path 表）；T4 cal/PR=cv_oof；T5 winsorized raise-only 歸因；T6 覆蓋表補 11 錨；T7 B0 冷啟動契約；T8 OOT check 落 `contracts.py` 公共 fn+timestamp 分支；T10 promotion 含 UpdatePattern+model；T11 plan identity 負測；T12 DEC-2 定案歸 B2.2（無逃生句）；T13 regime 逐 nodeid 表；T14 cross_symbol B4 抽查；T16 骨架 12 nodeid 精確計數。

> 執行端合約：`AGENTS.md`。實作=Grok（`--sandbox workspace`）；review=Codex+Composer 雙家（機器閘 `review_quorum_check.sh`；實作者不自審）；每批過 review 即 commit；B4 三方 DATA-CORRECT。branch `feat/ic-la2-p2-impl`（從 main 起）。
> 使用者決策定案（2026-07-18）：DEC-1=winsorized 標籤**禁用**；DEC-2=config 債**要修，placement 已定案歸 Task 2.3(B2.2)**；DEC-3=factor proxy**本票修到對**；model OOT**本票完成**（不拆）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
1. **解耦 7 條**：`momentum/` 不 import `api/`；原語留 `momentum/Analysis/pit_stats.py`；canonical split 契約 `momentum/core/contracts.py:360 SplitPlan`（禁自造 split 型別）。
2. **taxonomy 三分 + 軌2（SPEC §RISK；修法/oracle 不得跨類借用）**：
   - **C-1 causal-PIT**（截 bar 洩漏）：winsorized（**禁用**→oracle=raises 非 early-flip）、regime `_fit_global`（移除）。
   - **C-2 promotion-train-mask**：pattern 門檻/confidence（train-mask + train-y-only + OOT 晉升 + server guard）。
   - **C-3 diagnostic-loud**：factor（loud 欄位標註，不改算法）；DEC-3 proxy 因果化=獨立數值 class。
   - **軌2 in-sample 樂觀**：model 診斷 + service 全矩陣（eval_scope 契約，非 PIT/非截 bar mutation）。
3. **OOT 契約（軌2 核心）**：綁 `SplitPlan`；`fit_label_end(=max(fit_row_index)+horizon)+embargo **<** min(eval_row_index)`（**嚴格 `<`**，擋 off-by-one；違反→`SplitPairLeakageError`）；horizon=該 model label horizon（bar 數，row 空間）；embargo 單位=rows。
4. **欄位級 eval_scope allowlist**（SPEC §C 表）：scope enum=`{oot, cv_oof, in_sample_research_only}`（**只三值**）；`in_sample_research_only` 欄位 consumer/promotion **deny**；缺 held-out→metrics **OMITTED**（非保留全樣本標 research_only）；違序→hard raise。
5. **晉升 server 權威**（create+PUT）：旗標由後端 `task_id`→receipt 推導；`CreatePatternRequest` 移除 client `rules`/`performance_metrics`/`xgboost_importance`/`case_id`/`metadata`→改帶 `task_id`；status='active' iff OOT receipt；禁信前端 metadata。
6. **SPEC/TODO 邊界裁決（三家接受）**：SPEC 已鎖安全語義（不可偽造/fail-closed/plan identity/disjointness/digest 重算 deny/LOSO 證據/recursive deny）；**本 TODO 落確切結構**：receipt dataclass 欄位、binding checker 函式名、`model_performance` nested 逐欄 exact path（進 B0 allowlist）、factor discriminated union 型別。
7. **禁**：weaken NaN/inf gate；taxonomy 跨類 mutation 混用；silent fallback；metric 排序（IS>OOT）當 OOS 證明；final gate 殘留 skip/xfail。
8. **回退（SPEC §R）**：每批獨立 commit 可單獨 revert；逃生旗標=config flag（return_type/enabled）；golden control FAIL→不 merge。
9. **Logging/Error**：`get_logger(__name__)`；hot loop 不 log；fail-closed 用明確 exception（`SplitPairLeakageError`/`NotImplementedError` reason-code），非 silent warn。
10. **§MS/RULING-3（SPEC §C-基本）**：min_samples=100；loud 家族沿用既有 `analysis_status`/`oos_guarantees` 欄位語意，不另創。

## §0.6-APPENDIX — 確切結構落地（SPEC §C 邊界裁決委派 TODO；三家 R1 BLOCKING 必落）

### A. Receipt dataclasses（於 `momentum/core/contracts.py`，與 `SplitPlan` 同檔，皆 `@dataclass(frozen=True)`）
- **canonical hash（U3；禁 Python `hash()`——numpy array unhashable，codex 實跑證）**：`split_plan_hash = hashlib.sha256(b'|'.join([np.ascontiguousarray(plan.row_index, dtype='<i8').reshape(-1).tobytes(), str(plan.split_label).encode(), str(plan.symbol).encode(), str(plan.base_universe_hash).encode()])).hexdigest()`（**斷言 row_index ndim==1**；納 `split_label`/`symbol`/`base_universe_hash` 防 BTC/ETH 或 train/test 同 row_index 撞 hash——codex U3 實跑證 `[1,2]`/`[[1,2]]` 撞、且 plan identity 需區分 symbol/split）；`fit_idx_hash`/`eval_idx_hash`/`calib_idx_hash`/`train_idx_hash` 同法；`model_artifact_digest = sha256(artifact bytes)`；canonical JSON = `json.dumps(fields, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode()`。
- `OofReceipt`：`split_plan_hash: str`、`fold_id: int`、`fit_idx_hash: str`、`eval_idx_hash: str`、`model_artifact_digest: str`、`trusted_issuer: str`。
- `OotReceipt`：`split_plan_hash: str`、`fit_label_end: int`、`eval_start: int`、`horizon: int`、`embargo: int`、`model_artifact_digest: str`、`trusted_issuer: str`（**`PatternOotReceipt` = 此型別之別名**，Task 3.2 晉升用同一結構）。
- `CalibratorReceipt`：`split_plan_hash: str`、`calib_idx_hash: str`、`train_idx_hash: str`、`model_artifact_digest: str`、`trusted_issuer: str`（無 fold/eval_idx；verify 時由 caller 提供兩 index array 重算 hash 比對 + 斷言交集=∅）。
- **serialization envelope**（canonical）：`{"receipt_kind": "oof"|"oot"|"calibrator", "version": 1, "fields": {<asdict>}, "envelope_digest": sha256(canonical-JSON({receipt_kind,version,fields}) bytes)}`（digest 涵蓋 kind/version，防換 kind 重用）；`trusted_issuer` = 後端 service 名 literal（如 `"xgboost_task_service"`），verify 端以 **server 內建 issuer allowlist 常數**比對（誠實邊界：tamper-evident 非密碼學防偽，同 gate 慣例）；所有 API/service 一律用此 envelope，禁各造 dict。
- **binding checker（contracts.py 公共函式；U2 簽名皆含 model_artifact）**：`verify_oof_receipt(receipt, plan, fit_idx, eval_idx, model_artifact) -> None`（plan 供重算 split_plan_hash）、`verify_oot_receipt(receipt, train_plan, eval_plan, horizon, model_artifact) -> None`、`verify_calibrator_receipt(receipt, train_plan, calib_idx, model_artifact) -> None`——**重算步驟寫死**：①`sha256(artifact bytes)` 比對 `model_artifact_digest` ②重算各 idx/plan hash 比對 ③**disjointness 斷言**：oof=`fit_idx ∩ eval_idx = ∅`；calibrator=`calib_idx ∩ train_plan.row_index = ∅` ④envelope_digest 重算。任一不符/缺→`raise`（fail-closed，禁「有欄位即 pass」）。

### B. Factor discriminated union（`momentum/core/contracts.py`；U5 真 variant + named verifier）
- `@dataclass(frozen=True) OrthogonalizationPayload`：`method: str`、`orthogonalized_hash: str`、`summary: dict`；`@dataclass(frozen=True) ExposurePayload`：`proxy_kind: Literal["trailing_close_ret"]`、`exposure_hash: str`、`summary: dict`。
- `@dataclass(frozen=True) FactorModuleResult`：`module: Literal["orthogonalization","exposure"]`（discriminator）、`oos_guarantees: Literal[False]=False`、`fit_scope: Literal["full_sample"]="full_sample"`、`payload: OrthogonalizationPayload | ExposurePayload`（`__post_init__` 互驗：module↔payload 型別匹配、**`oos_guarantees is False` 硬斷言**〔非只 Literal 型別提示〕、`fit_scope=="full_sample"`，任一不符→raise）。
- **named recursive verifier（U5）**：`deny_factor_in_ok_oos(report: dict) -> None`（contracts.py）——recursive 掃 report，root `analysis_status=="ok_oos"` 且任一 `FactorModuleResult`（或其 envelope dict）present→`raise`；consumer/export/persist 出口一律先呼此 fn——**具名出口**：`ic_analysis_service.py:255-265`（root status 正規化）、`ic_reporter`（persist/export writer）、API report 直通出口；raw dict（未經 `FactorModuleResult`）present 亦 deny（掃 `oos_guarantees` 鍵）。

### C. `model_performance` nested exact-path inventory（RFC6901；進 B0 `eval_scope_field_map` allowlist；= SPEC §C 表嵌入，**28 path**）
| JSON path | eval_scope | consumer |
|---|---|---|
| `/model_performance/in_sample_train_auc` | in_sample_research_only | deny |
| `/model_performance/fit_pool_auc` | in_sample_research_only | deny |
| `/model_performance/overfitting_score` | in_sample_research_only | deny |
| `/model_performance/precision` | cv_oof | research_only |
| `/model_performance/recall` | cv_oof | research_only |
| `/model_performance/f1_score` | cv_oof | research_only |
| `/model_performance/cv_auc_mean` | cv_oof | ok |
| `/model_performance/cv_auc_std` | cv_oof | ok |
| `/model_performance/oot_auc` | oot | ok |
| `/model_performance/calibration_curve` | **cv_oof** | ok |
| `/model_performance/brier_score` | **cv_oof** | ok |
| `/model_performance/ece` | **cv_oof** | ok |
| `/model_performance/pr_curve` | **cv_oof** | ok |
| `/model_performance/pr_auc` | **cv_oof** | ok |
| `/model_performance/precision_at_k` | oot | ok |
| `/model_performance/recommend_k` | oot | ok |
| `/model_performance/expectancy` | oot | ok |
| `/model_performance/sharpe_proxy` | oot | ok |
| `/model_performance/bootstrap_ci` | oot | ok |
| `/model_performance/predictions/train` | in_sample_research_only | deny |
| `/model_performance/predictions/oot` | oot | ok |
| `/model_performance/feature_importance` | in_sample_research_only | deny |
| `/model_performance/feature_importance_all` | in_sample_research_only | deny |
| `/model_performance/permutation_importance` | in_sample_research_only | deny |
| `/model_performance/fold_importance_stability` | cv_oof | research_only |
| `/model_performance/shap_sample` | in_sample_research_only | deny |
| `/model_performance/regime_analysis` | in_sample_research_only | deny |
| `/model_performance/cross_symbol_validation` | in_sample_research_only | deny |
> 此表為 §0.4 enum 規則的**逐欄落地表**（§0.4=規則、本表=28 path 映射）；**path=遷移後 canonical 結構**——現況 service 輸出 `predictions`/`feature_importance(_all)` 在 result 頂層（`xgboost_task_service.py:387-409`），Task 2.2 遷入 `/model_performance/*` 或 allowlist 同錄 old top-level path→new path 對照（禁頂層漏網）；Task 2.1/2.2 逐欄依此標 scope，B0.2 predeclare 為 `eval_scope_field_map`（漏欄=FAIL）。**cal/PR/Brier/ECE=cv_oof（非 oot）**。

## §B 批次執行策略（DAG：B0 → {B1,B2,B3 可並行} → B4；修改 legacy 輸出的批次一律不得早於 B0）
- **B0**（baseline+骨架;**批內鎖序 0.1→0.2→0.3**,U19:allowlist 依 §0.6-C 表、骨架依 allowlist nodeid）→ **B1**（winsorized 禁用）/**B2**（model OOT）/**B3**（條件模組）三批並行 → **B4**（mutation 全家+golden+三方 DATA-CORRECT）。
- **allowlist predeclare 流程**（§G 相容）：B0=schema+空 rows（宣告 class_enum）；B1/B2/B3 各批完成把**該批預期 diff** append 進 allowlist（隨批 review 審）；B4 validator 驗 unlisted=FAIL。「擅擴」=B4 開始後或未經雙家 review 的 append。
- **雙家 review**：每批 Grok 實作→Codex+Composer 各獨立 review（`review_quorum_check.sh` 驗前批 quorum 才發下批 token）→finding-closure（原提出方重跑反例確認關閉）→commit。

## Phase B0 — Baseline 凍結 + 測試骨架（依賴：無）
### Task 0.1 — `tests/golden/la2/gen_baseline.py` 可重現改前 baseline（SPEC B0.1）
- 目標：改前凍結五面 legacy 輸出 + 軌2 index identity；control 路徑亦凍結供 deep-equal。檔案：`tests/golden/la2/gen_baseline.py`。
- **冷啟動契約（T7，LA-1 範式）**：入口=`data_cache/feature_klines/kline_cache.h5` group key `BTCUSDT/1h`+`ETHUSDT/12h`（structured `data`）；**兩 dataset sha literal 寫死**於 gen_baseline(U6):BTC/1h rows=**20352** sha₁₆=**`1c93c37938a4917a`**;ETH/12h rows=**1696** sha₁₆=**`00d1ee985ad3f09f`**(LA-1 receipt 同源檔;`--check` 重驗)；**入口指名**（透過 orch `analyze()` API 還是 analyzer 直呼——鎖 analyzer 直呼避免 orch 副作用；每面標明 caller）；`inputs/*` layout=各面 config JSON（return_type/expanding/factor.enabled/pattern split）；**persist 隔離**（gen_baseline 禁觸發產線 persist）。
- 改法：真實 kline 跑：pattern 門檻+confidence（C-2）、regime `_fit_global`（C-1 legacy 供 removal 對照）、factor GS/PCA/exposure（enabled=True，C-3）、model 診斷+service 全矩陣（軌2，含 fit/eval index identity hash）。**winsorized 不列 baseline/mutation**（DEC-1 禁用→oracle=raises）。canonical mutation 常數內嵌：M-trunc=`int(0.75*n)`、early=`[0,int(2/3*n_keep))`。名稱 sha256+value hash+NaN mask hash+index identity hash。
- 驗證：`python tests/golden/la2/gen_baseline.py --check` exit 0（內含 assert：兩 input dataset sha literal 重驗；C-2 early-flip manifest 兩側 len>0；軌2 index identity 記錄；baseline JSON 四面鍵齊全〔winsorized 除外〕——任一不符 exit 1）。
- 邊界：短樣本（全 warmup）、跨 symbol 隔離（`SplitPlan` CrossSymbolLeakageError）、空 vol。
- 不可做：合成 fixture；aggregate-only baseline；列 winsorized 產出。

### Task 0.2 — allowlist predeclare + validator（SPEC §G）
- 目標：歸因表 schema + 洗歸因 validator。檔案：`tests/golden/la2/attribution_allowlist.json`+`attribution_validator.py`。
- 改法：allowlist schema=`schema_version`+`class_enum ["P2-1-disable","P2-2-oot","P2-2-scope-tag","P2-3a-factor-loud","P2-3a-proxy-causal","P2-3b-pattern-trainmask","P2-3b-promotion-guard","P2-3c-regime-remove"]`+`rows:[]`（B0 空）；**含 `model_performance` nested 逐欄 exact path 清單**（§0.6 邊界裁決落點）。validator：diff vs allowlist（unlisted=FAIL；row=exact JSON path+index+old/new discriminator）；≥5 wash mutation 打紅（竄改 control/軌2 全樣本標成 OOT/刪 loud 欄稱已標/wrong-class swap/擅擴 allowlist）。
- 驗證：`pytest tests/golden/la2/test_attribution_validator.py`——5 wash 各自 FAIL（可證偽：validator 放行任一則測試 FAIL）。
- 邊界：空 rows、unlisted diff、擅擴偵測。
- 不可做：validator 放水；wash 少於 5。

### Task 0.3 — `tests/momentum/test_la2_lookahead.py` 骨架（SPEC B0.2；解雞蛋）
- 目標：predeclare 全 nodeid（collect-only 非 0）。檔案：`tests/momentum/test_la2_lookahead.py`。
- 改法：predeclare **精確 12 nodeid**（T16）：`test_winsorized_disabled`/`test_model_oot_contract`/`test_model_service_oot`/`test_config_theater`/`test_calibrator_receipt`/`test_pattern_train_mask`/`test_pattern_promotion_guard`/`test_plan_identity_mismatch`/`test_regime_no_global_fit`/`test_factor_loud`/`test_adversarial_validator_diagnostic_only`/`test_analysis_status_diagnostic`（骨架 xfail，B1-B3 填實）。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py --collect-only` 列**恰 12 nodeid**（多/少→FAIL）；glob 非 0。
- 邊界：骨架 xfail 不算綠（B4 final gate 禁殘留 skip/xfail）。
- 不可做：空檔；假 pass 充綠。

## Phase B1 — winsorized 禁用（依賴：B0）
### Task 1.1 — winsorized fail-closed 三層 + 死欄位/config 移除 + engine/orch 對齊（SPEC B1.1，DEC-1）
- 目標：禁用洩漏標籤（loud，三層同 reason-code），engine 不 silent 回退。檔案：`momentum/FeatureEngineering/labels/label_generator.py:82,95`、`momentum/Analysis/ic_filter_orchestrator.py:2400`、`momentum/Analysis/ic_engine.py:1010-1016`、`momentum/Analysis/ic_config_schema.py:43-52`、`config/ic_config.yaml:27-30`。
- 改法：①`generate_returns_by_type` winsorized→raise（固定 `LOOKAHEAD_LABEL_UNSUPPORTED` reason）；schema Literal 移除 winsorized（Pydantic 422 帶同 reason）；orch fail-closed。②移除死欄位 `winsorize_returns`+yaml:27-30 winsorized/winsorize_returns 宣告（grep reader=0）。③`ic_engine._compute_returns` **不 silent 回退**：winsorized→raise；excess/risk_adjusted→統一走 `LabelGenerator` dispatch 或明確 raise（與 orch 同源）；附各 return_type 兩路徑一致行為表。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_winsorized_disabled`——winsorized 三層 raise（reason-code 一致，任一層漏→FAIL）；simple/log/excess/risk_adjusted engine==orch（atol=1e-12，禁 engine silent simple）；`winsorize_returns` reader=0+yaml 宣告移除。
- 邊界：orch override 傳 winsorized（須 raise）；schema 驗證層 422。
- 不可做：engine silent 回退；留死欄位/yaml 宣告；只測一層。

### Task 1.2 — B1 批尾：預期 diff append 進 allowlist（§B 流程；T5 raise-only）
- 目標：winsorized 禁用的歸因入 allowlist。檔案：`tests/golden/la2/attribution_allowlist.json`。
- 改法：append `P2-1-disable` row，discriminator=**raise-only**（`{class:"P2-1-disable", behavior:"raises", reason_code:"LOOKAHEAD_LABEL_UNSUPPORTED", path=**四入口各一 row**:`momentum/FeatureEngineering/labels/label_generator.py::generate_returns_by_type`、`momentum/Analysis/ic_config_schema.py::return_type Literal`、`momentum/Analysis/ic_filter_orchestrator.py:2400`、`momentum/Analysis/ic_engine.py::_compute_returns(:1010-1016,Task 1.1③ 修後亦 raise)`}`；**恰 4 rows/無 old value/無幽靈 baseline path**——B0 本就不產 winsorized baseline，SPEC:102/105）。
- 驗證：validator 對 B1 diff 0 unlisted；`--check` exit 0；winsorized row 為 raise-behavior 非數值 diff（validator 斷言此 class 不帶 old/new value）。
- 邊界：winsorized 路徑不再有數值輸出（三層 raise）。
- 不可做：擅擴非 B1 class；B4 後才 append；**造幽靈 old value/baseline path 洗綠**。

## Phase B2 — model OOT-only 契約（依賴：B0）
### Task 2.1 — analyzer 診斷 eval_scope 契約 + SplitPlan horizon check（SPEC B2.1）
- 目標：診斷曲線只能 OOT/OOF + 嚴格 horizon 邊界。檔案：`momentum/core/contracts.py`（新增 receipts+`validate_oot_label_horizon`）、`momentum/Analysis/lightgbm_analyzer.py:355-374,415-426`、`momentum/Analysis/xgboost_analyzer.py:445-465,1147-1174,1298-1343`、`momentum/Analysis/calibration_analyzer.py`。
- 改法：①`train_auc`→`in_sample_train_auc`（rename 不並存）；LGBM 含 ES-val 池化→獨立欄 `fit_pool_auc`；`overfitting_score=in_sample_train_auc−cv_auc_mean` 跟改名。②cal/PR/Brier/ECE→**依 §0.6-APPENDIX C 單值 scope=cv_oof**（U1，無擇定）+`eval_scope` 欄位；LGBM/XGB 路徑對稱。③**horizon-aware check（T8，落 `contracts.py` 公共函式）**：於 `momentum/core/contracts.py` **新增** `validate_oot_label_horizon(train_plan, eval_plan, horizon, bar_duration=None, ts: np.ndarray|None=None) -> None`（timestamp 分支必傳 ts array 供 discontinuity 檢查）（既有 **`validate_split_pair_integrity:559`**(U7 名稱改正;SPEC 凍結版寫 validate_train_test_pair:566 為幽靈名,TODO 為實作依據,SPEC errata 註記)只查 row 禁區不含 horizon，不足）：row 空間 `fit_label_end(=max(train_plan.row_index)+horizon)+embargo **<** min(eval_plan.row_index)`（嚴格 `<`）；`index_kind=timestamp` 分支 `max(fit_ts)+(horizon+embargo)*bar_duration < min(eval_ts)`;**hard-fail(U8)**:timestamp plan 且 `bar_duration=None`/`expected_freq` 缺/timestamp gap(discontinuity)→**raise**(禁 fallback 回 row check);違反→`SplitPairLeakageError`。analyzer `validate_oot` 呼此公共函式（非私有 lambda）。④skip 單一 union：違序→hard raise；缺 held-out→metrics OMITTED+status reason+deny。⑤**OofReceipt/OotReceipt**（§0.6-APPENDIX A 為 exact-struct 權威）：`verify_oof_receipt(receipt, plan, fit_idx, eval_idx, model_artifact)`/`verify_oot_receipt(receipt, train_plan, eval_plan, horizon, model_artifact)` 依 APPENDIX 四步（artifact digest+idx/plan hash 重算+**disjointness**+envelope_digest），缺/不符→raise。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_model_oot_contract`——欄位帶 `eval_scope`（三 enum 逐欄）；OOT `fit_label_end+embargo<min(eval)`（row96+h5+embargo0=101 vs eval_start=101→`101<101`False→FAIL，等號邊界可證偽）；OOF per-fold `fit_idx∩eval_idx=∅`+digest 重算（假 fit_idx_hash→FAIL；合法 OOF 不誤殺）；`in_sample_train_auc`/`fit_pool_auc` 命名+deny；缺 held-out→metrics omit。
- 邊界：無 held-out（metrics OMITTED+deny，非 pytest skip）；單 fold；LGBM early-stopping 命名；等號邊界。
- 不可做：截 bar mutation 充軌2；metric 排序；naive index-subset；`≤` 放行。

### Task 2.2 — service 全矩陣 scope + calibrator receipt + DTO/前端 migration（SPEC B2.2）
- 目標：service 全樣本指標同 OOT 契約 + calibrator fail-closed。檔案：`api/services/xgboost_task_service.py:234-409`、`api/services/xgboost_batch_service.py:734-1009`、`api/services/model_task_service.py:85-91(LGBM)`、`api/services/model_enhancement_service.py:251-275`、`momentum/Analysis/probability_calibrator.py:43-70`、`momentum/Analysis/xgboost_analyzer.py:683`+`momentum/Analysis/lightgbm_analyzer.py:651`、`api/models/pattern_analysis_models.py:554-570`、`frontend/src/lib/patternTypes.ts:158-177,287-303`、`frontend/src/app/patterns/xgboost-analysis/page.tsx:154-161`、`frontend/src/components/pattern/CreatePatternForm.tsx:109-122`。
- 改法：①**逐欄 scope=§0.6-APPENDIX C 全表**（RFC6901 每 path 標 scope；漏欄=FAIL）：涵蓋 in_sample_train_auc/fit_pool_auc/overfitting_score/precision/recall/f1_score/cv_auc_mean/cv_auc_std/oot_auc/calibration_curve/brier/ece/pr_curve/pr_auc/precision_at_k/recommend_k/expectancy/sharpe_proxy/bootstrap_ci/get_predictions(train,oot 分列)/feature_importance(_all)/permutation/fold/shap/regime_analysis/cross_symbol_validation；**cal/PR/Brier/ECE=cv_oof**（T4，非 oot）；recommend_k/expectancy/sharpe_proxy/precision@K/bootstrap→oot；importance/SHAP/regime/cross_symbol→in_sample_research_only+deny（cross_symbol 本票不做 oot 分支，對齊 §N；batch:907-933 全路徑）；LGBM `model_task_service:85-91` 同步。②**CalibratorReceipt**（§0.6-APPENDIX A，**非 OofReceipt**——calibrator 用 `calib_idx_hash`/`train_idx_hash` 證不交疊，無 fold/eval_idx）：`fit`+`fit_from_predictions` 兩分支共用 `verify_calibrator_receipt()`；signal-facing 缺 receipt→fail-closed（非 warn）；calibrator receipt 寫入 `task_result["calibrator_receipt"]`（具名 key，同 oot_receipt 鏈）。③**OotReceipt 寫入鏈(U11)**:`xgboost_task_service` 於 train+OOT 驗證完成時產 `OotReceipt` envelope 寫入 `task_result["oot_receipt"]`(供 Task 3.2 promotion lookup;B2→B3 依賴);**batch(`xgboost_batch_service.py:976-1001`)與 LGBM `model_task_service` 同鏈寫入**——未寫入 receipt 的結果=**不可晉升**(promotion lookup 無 receipt→拒,fail-closed 自然覆蓋)。④**DTO/前端 migration(U13,附 old→new map)**：`train_auc`→`in_sample_train_auc`（+`fit_pool_auc`）rename（不並存）;實作端附 old→new RFC6901 對照(`/model_performance/train_auc`→`/model_performance/in_sample_train_auc`;TS `patternTypes.ts` `train_auc`→`in_sample_train_auc`;`brier_score` 沿用此名=§0.6-C canonical)+DTO/TS/UI/CreatePatternForm 同步,禁雙名並存。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_model_service_oot`——全矩陣逐欄 scope；recommend_k OOT（餵全樣本→FAIL）；importance/shap research_only+deny；LGBM 路徑同標；`::test_calibrator_receipt`——兩分支缺 receipt→raise；DTO rename 不破前端（migration 測試）。
- 邊界：LGBM/XGB 對稱；calibrator pred-only 分支；前端舊欄。
- 不可做：warn 代 fail-closed；漏 feature_importance/LGBM/recommend_k；train_auc 並存。

### Task 2.3 — config 債（calibrator/sample_weight 假啟用）標註（SPEC B2.2，DEC-2；T12 placement 定案）
- 目標：config `enabled≠wired` 可見。檔案：`config/model_config.yaml:47-74`、`momentum/Analysis/model_config.py:66-88`（reader/DTO 加 `wired` 欄）、前端 `frontend/src/components/pattern/EngineConfigPanel.tsx`（顯示 `wired=false` 標記）。
- 改法（**DEC-2 placement 本輪委員會定案=歸 B2.2**，與 model service/config reader 相鄰；**無「委員會可調」逃生句**）：`probability_calibration`/`sample_weight` enabled=true 但 `train_model` 無 wiring→`model_config.py` reader/DTO 加 `wired: bool` 欄位（runtime 未接線→`wired=false`）+ UI 顯性標「已宣告未接線」+測試證（runtime 行為不受 yaml enabled 控）。sample_weight 若未來接線需 train-only provenance（`compute_time_decay` 用 `parsed.max()` 全資料最新 ts=洩漏、return 權重恐用 future label）——**記債**，完整接線另立 productionization epic（本票不接線）。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_config_theater`（新增或併 service_oot）——config `enabled=true,wired=false` 標記存在+UI 可見；runtime 行為不受 yaml 控斷言。
- 邊界：yaml enabled=true 但 runtime path 無呼叫。
- 不可做：完整接線 sample_weight（另票）；silent 假啟用不標。

### Task 2.4 — B2 批尾：預期 diff append 進 allowlist（§B 流程）
- 目標：軌2 scope 改動歸因。檔案：`attribution_allowlist.json`。
- 改法：append `P2-2-oot`/`P2-2-scope-tag` rows（train_auc→in_sample_train_auc rename、**cal/PR/Brier/ECE 改 cv_oof 值**〔T4，非 oot〕、oot_auc/precision@K/recommend_k/expectancy→oot、service 逐欄 scope 標，依 §0.6-APPENDIX C）。
- 驗證：validator 對 B2 diff 0 unlisted。
- 邊界：軌2 值由全樣本→OOT/OOF（歸因非 deep-equal）。
- 不可做：把軌2 全樣本值標成已修 OOT（wash）。

## Phase B3 — 條件模組（依賴：B0；可與 B1/B2 並行）
### Task 3.1 — regime `_fit_global` 硬移除 + 逐測試遷移（SPEC B3.1，C-1）
- 目標：徹底移除全期 fit 逃生口。檔案：`momentum/Analysis/regime_detector.py:111-146,217-230`。
- 改法：**移除 `expanding` 參數 + `_fit_global` 方法**（非 or raise）；`detect` 固定 PIT Segment-causal（承 LA-1 B1.3）；`detect_phases_for_index` 移除傳 expanding=True（參數不存在）。
- **逐 nodeid 遷移表（T13/U9，嵌入實列；Claude 2026-07-18 實跑 rg；禁只 mark skip）**：
  | nodeid（`tests/test_regime_detector.py`） | 改法 |
  |---|---|
  | `test_detect_3_clusters`/`test_detect_with_volume`/`test_deterministic_labels`/`test_cluster_stats_sum_to_100`/`test_cluster_stats_have_volatility`/`test_high_vol_label_has_highest_volatility`/`test_to_dict_structure` | 移除 `expanding=False` 參→走 PIT 預設呼法（斷言語意改 PIT 行為） |
  | `test_detect_global_fit` | 整測改寫=「`expanding` 參數不存在 + `_fit_global` 屬性不存在」正向 removal 斷言 |
  | `test_detect_expanding_fit`（:94，`expanding=True`） | 移除 `expanding=True` 傳參→PIT 預設呼法（參數刪除後傳參必 TypeError，須遷移） |
  | `test_fallback_on_tiny_data`/`test_fallback_labels_are_semantic`/`test_all_nan_data`/`test_nan_heavy_data`/`test_constant_price`/`test_single_value_after_dropna`/`test_volume_all_nan` | 移除 `expanding=False`→PIT 呼法（fallback/邊界語意不變） |
  | `tests/momentum/test_la1_lookahead.py::test_regime_pit` 系（:575-628 內 5 處 expanding=False 呼法，實作時 `rg` 取精確行） | 改「參數不存在/`_fit_global` 不可達」斷言（驗 removal，非驗 False 行為；**全檔其餘 expanding 呼法一併掃遷**） |
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_regime_no_global_fit`——`detect(expanding=False)` 參數不存在+`_fit_global` 直呼不可達（正向斷言已移除，可證偽：能全期 fit→FAIL）；產線 caller deep-equal（atol=1e-12）；遷移後 `pytest tests/test_regime_detector.py tests/momentum/test_la1_lookahead.py` 全綠（非 skip）。
- 邊界：產線 caller（IC/XGB）不變；legacy test 遷移。
- 不可做：保留雙路徑；只 public raise 留 `_fit_global`；靜默 skip 舊測試。

### Task 3.2 — pattern train-mask + SplitPlan caller + train-y 統計 + 晉升 server 閉環（SPEC B3.2，C-2）
- 目標：pattern 門檻不再全樣本 + 晉升 server 權威。檔案：`momentum/Analysis/pattern_extractor.py:58-66,119,149,165,199`、`api/services/xgboost_task_service.py:249`、`api/services/xgboost_batch_service.py:751`、`api/services/pattern_management_service.py:34,68,82,190-229`、`api/models/pattern_management_models.py:12-29`、`api/routes/pattern_management.py:34-48,129-139`、`frontend/src/app/patterns/xgboost-analysis/page.tsx:408,417`、`frontend/src/lib/patternTypes.ts`、`frontend/src/components/pattern/CreatePatternForm.tsx:109-122`。
- 改法：①caller 契約：`extract_decision_rules` 加 `split: SplitPlan`（必填，`split_label='train'` 硬鎖，plan identity）；mask≡`train_model` 時序 train 段（固定絕對 cutoff，禁 random/比例重切/禁傳 test/OOT）；缺→fail-closed。②train-y 統計：quantile 門檻+`base_prob@:119`+`confidence@:165`+lift **一律 train-y-only**（非或 OOT；晉升另計 OOT lift）。③**晉升 server 閉環（create+PUT，T10）**：`CreatePatternRequest` 移除 client `rules`/`performance_metrics`/`xgboost_importance`/`case_id`/`metadata`→帶 `task_id`；**`UpdatePatternRequest`（`pattern_management_models.py:60-66`）亦移除 client `status`/`metadata`**（PUT `pattern_management.py:129-140`→service`:228-233` 直改路徑鎖）；server 從 `task_result["oot_receipt"]`（`PatternOotReceipt`=OotReceipt 別名，§0.6-A）lookup+`verify_oot_receipt` 重建 rules/performance/scope；status='active' **iff verify 通過**（create+PUT 兩路徑）;**model promotion（U10 收口）**:現況無獨立 model 晉升 API/surface(模型結果不落 active 狀態)→本票晉升閉環=pattern_management 路徑;§N 記錄「未來若加 model 晉升 API 須同 receipt 契約」,不虛構檔案；`in_sample_rules` server 推導；compound rule DTO：`PatternRuleRequest:12-17`→`feature_conditions[]`（鎖 connective=AND/順序/空集拒/逐條 round-trip；`page.tsx:417` 壓單 feature 修正）；threshold=condition 分位值（非 confidence）；持久化 `in_sample_train_auc` 帶 scope。④**plan identity（T11）**：pattern/model/calibrator 消費同一 `SplitPlan`/`plan_hash`；跨模組 mismatch→fail-closed。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_pattern_train_mask`——缺 split/傳非 train split→fail-closed；trunc 未來→門檻/confidence early_equal（train-y-only 改後 flip=0）；`::test_pattern_promotion_guard`——偽造 client metadata/importance/status POST**及 PUT**→拒（server 級）；缺/假 OOT receipt（`verify_oot_receipt` digest 不符）→status≠active；**晉升 OOT lift 來源斷言（N4）**：promote 時 lift 值必來自 OOT 段計算（餵 train-段 lift→FAIL）；threshold=分位值；compound round-trip；`::test_plan_identity_mismatch`——pattern/model 三 cutoff 同但 row_index 不同→fail-closed（可證偽）。
- 邊界：無 held-out（in_sample_rules=true 禁晉升）；pattern UI 顯示不破；compound 空集/OR/丟 description。
- 不可做：等同 IC-gate 全族 PIT；純 loud 無 train-mask；信前端 metadata；confidence 用 OOT 逃生；**LGBM batch（`xgboost_batch_service.py:748` `if lightgbm: rules=[]`）跳過 pattern=記錄性 asymmetry，禁順手接線 LGBM pattern 晉升（U15，§N 記債）**。

### Task 3.3 — factor typed loud + market_proxy 因果化（SPEC B3.3，C-3+DEC-3）
- 目標：factor loud 標註（不改算法）+ 修 forward-label proxy。檔案：`momentum/Analysis/factor_orthogonalizer.py gram_schmidt:25-68`、`momentum/Analysis/factor_exposure_analyzer.py:46-73`、`momentum/Analysis/ic_filter_orchestrator.py:2082-2115,3119-3133`、`api/models/ic_models.py:219-226`、`api/services/ic_analysis_service.py:255-265`。
- 改法：①C-3 typed loud：factor module result=typed contract（非 `Dict[str,Any]`，discriminated union）含 `oos_guarantees=false`/`fit_scope="full_sample"`；root `ok_oos`+nested degraded→consumer/export deny gate（recursive）；GS/PCA 算法不改；orthogonalized 矩陣 advanced export→research_only deny。②**close carrier（T-close key/型別/對齊）**：`_ic_cache`（orch:3119-3133）未存 close→新增 cache key **`_ic_cache["close_series"]: pd.Series`**（index 對齊 `features_df.index`，同 symbol/TF，禁塞錯 index）；③DEC-3 proxy（獨立 class）：`_run_factor_exposure market_proxy=label_series`（forward,:2107）→`_ic_cache["close_series"].pct_change().shift(1)`（lag≥1，decision-ts=前一 bar close，不見當根 close，NaN drop 對齊 factor index）；exposure 數值變歸 `P2-3a-proxy-causal`；typed=`FactorModuleResult`（§0.6-B）。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_factor_loud`——enabled=True→typed payload 含 `oos_guarantees=false`/`fit_scope`（無則 FAIL）；root ok_oos+nested degraded→consumer deny；GS/PCA deep-equal（算法不改，atol=1e-12）；factor OFF control deep-equal；market_proxy 不含 forward label（lag≥1 不見當根 close）+exposure 變歸 proxy-causal class。
- 邊界：factor OFF control；close carrier NaN；export research_only。
- 不可做：blanket PIT 重寫；proxy 數值變混進 loud class；`Dict[str,Any]` 無 typed gate。

### Task 3.4 — B3 批尾：預期 diff append + adversarial_validator 最小標註（§B 流程+SPEC §N）
- 目標：B3 歸因入 allowlist + adversarial_validator diagnostic_only。檔案：`attribution_allowlist.json`、`momentum/Analysis/adversarial_validator.py`。
- 改法：append `P2-3a-factor-loud`/`P2-3a-proxy-causal`/`P2-3b-pattern-trainmask`/`P2-3b-promotion-guard`/`P2-3c-regime-remove` rows；`adversarial_validator` 標 `diagnostic_only`（train∪test 域分類刻意，非交易 signal）+B4 一條 `analysis_status` 斷言 nodeid。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py::test_adversarial_validator_diagnostic_only`——`diagnostic_only` 標記存在（可證偽:未標→FAIL）；`::test_analysis_status_diagnostic`——adversarial_validator 輸出 `analysis_status=diagnostic_only` 且 **root ok_oos 時仍 deny 進 signal**（marker 綁 consumer deny，非 marker-only；U18 獨立驗收）；validator 對 B3 diff 0 unlisted。
- 邊界：proxy-causal 與 factor-loud 分行歸因（wrong-class swap 打紅）。
- 不可做：把 proxy 數值變當 loud；adversarial_validator 當 signal。

## Phase B4 — mutation 全家 + golden + 三方 DATA-CORRECT（依賴：B1,B2,B3；4.1→4.2）
### Task 4.1 — mutation 全套 + golden 重基準 + validator 收口 + final gate（SPEC B4.1）
- 目標：三類 + 軌2 mutation 全打紅 + control deep-equal + 跨 symbol 隔離。檔案：`tests/momentum/test_la2_lookahead.py`、`tests/golden/la2/*`。
- 改法：C-1（winsorized 三層 raise/regime 移除不可達）、C-2（pattern 門檻/confidence early flip 改後=0 + 晉升 provenance）、C-3（loud 欄位存在+control deep-equal + proxy-causal 數值歸因）、軌2（SplitPlan provenance oracle：OOT 嚴格 `<`/OOF per-fold disjoint+digest/research_only deny）全入庫；golden 重基準（control byte-equal，歸因表 0 unexpected）；validator ≥5 wash 打紅；ETHUSDT/12h 隔離；**cross_symbol B4 抽查（T14/U17 具體化）**：batch cross_symbol 輸出取**排序後前 2 個 eligible symbol**（eligible=該 symbol ≥ batch min rows〔現碼 batch:907-931 每 symbol <10 跳過〕；deterministic 排序；不足 2 eligible→測試以 fixture 準備 BTC+ETH 兩組保證 ≥2），斷言皆標 `in_sample_research_only`+consumer deny（golden 斷言或併 `test_model_service_oot`；對齊 §N，本票無 LOSO receipt 生成、非 oot 分支）；**final gate 禁 skip/xfail/--runxfail**+mutation coverage（`--collect-only` 恰 12 nodeid，全非 skip/xfail）。
- 驗證：`pytest tests/momentum/test_la2_lookahead.py tests/golden/la2/` 全綠（0 skip/xfail）；歸因表 0 unexpected；control deep-equal（atol=1e-12）；C-1/C-2 mutation 全紅+C-3 loud oracle+軌2 provenance oracle 全紅。
- 邊界：☑空DF ☑全NaN ☑無 held-out ☑短樣本 ☑跨 symbol ☑winsorized 三層 ☑regime 逃生口 ☑pattern 缺 split ☑偽造 metadata 晉升被拒 ☑OOF 不誤殺 ☑embargo/等號邊界被擋。
- 不可做：sanitized fixture；廉價綠燈；taxonomy 跨類混用；殘留 skip 充綠。

### Task 4.2 — 三方 DATA-CORRECT 簽核（編排端執行，SPEC B4.1）
- 目標：Claude+Codex+Composer 三方獨立簽「資料正確」（a,d 高風險；Grok=實作者不簽）。檔案：`handoffs/LA2-B42-DATACORRECT-{claude,codex,composer}.md`。
- 改法：各自 adversarial 讀碼+親自 mutate 驗三類洩漏可證偽（winsorized raise/pattern 門檻 flip/regime 移除/OOT 嚴格 `<`/factor proxy 因果）；真實 kline BTC+ETH partition；任一方有疑→不通過。
- 驗證：三方各 PASS（綠測+code-level 洩漏真除+mutation 可證偽 receipt）；歸因表 0 unexpected；`reconcile_stamps_check.sh` 補正式戳記過機檢。
- 邊界：三方獨立方法互審（byte 級/PIT 無 look-ahead/跨 symbol 隔離/合併前後守恆）。
- 不可做：sanitized fixture；一方簽核代替三方；廉價綠燈。

## SPEC ID 100% 覆蓋追溯表（一錨點一列）
| SPEC 錨點 | 對應 Task |
|---|---|
| §RISK（大/a,b,c,d/adversarial 必跑） | 本檔頭+§0.2 taxonomy+Task 4.2 三方 |
| §C-基本（RULING-3/oos_guarantees/§MS min_samples=100） | §0 第1條+§0 第10條(min_samples=100)+Task 3.3（factor loud oos_guarantees） |
| §C plan identity（plan_hash mismatch deny） | §0.6-A+Task 3.2④+`test_plan_identity_mismatch` |
| §C timestamp 空間 OOT | Task 2.1③（`validate_oot_label_horizon` timestamp 分支） |
| §C LOSO receipt 安全語義 | §0（cross_symbol research_only）+Task 4.1 cross_symbol B4 |
| §C 邊界裁決 exact struct（dataclass/envelope/checker/path/union） | §0.6-APPENDIX A/B/C |
| §A engine/orch return_type 分歧（M5） | Task 1.1③ |
| §V TEST_DESIGN_CHARTER 引用 | Task 4.1（mutation 設計引章程） |
| §G inputs/*+dataset sha 寫死 | Task 0.1 冷啟動契約 |
| §N cross_symbol_validator B4 抽樣複查 | Task 4.1（T14） |
| §N LGBM batch pattern asymmetry 記債 | Task 3.2「不可做」（T15） |
| §RISK taxonomy C-1 | Task 1.1（winsorized）+Task 3.1（regime） |
| §RISK taxonomy C-2 | Task 3.2 |
| §RISK taxonomy C-3 | Task 3.3 |
| §RISK 軌2 | Task 2.1+2.2 |
| §A FACT winsorized leak+零產線 | Task 0.1（不列）+Task 1.1 |
| §A FACT model 全樣本診斷 | Task 2.1 |
| §A FACT service 全矩陣 | Task 2.2 |
| §A FACT config 債 | Task 2.3 |
| §A FACT factor+proxy | Task 3.3 |
| §A FACT pattern | Task 3.2 |
| §A FACT regime _fit_global | Task 3.1 |
| §A DEC-1 禁用 | Task 1.1 |
| §A DEC-2 config 債（已定案歸 B2.2/Task 2.3） | Task 2.3 |
| §A DEC-3 proxy 因果 | Task 3.3 |
| §C-OOT/OOF 契約（SplitPlan 嚴格<） | Task 2.1（§0.3）|
| §C 欄位級 allowlist 表 | Task 2.1+2.2（§0.4）|
| §C 邊界裁決（安全語義/結構 TODO） | Task 2.1 OOF dataclass+Task 0.2 nested path（§0.6）|
| §C 晉升 server 權威 | Task 3.2（§0.5）|
| §C-下游消費者 | Task 2.2（DTO/前端）+Task 3.2（pattern UI）|
| §G control deep-equal | Task 0.1+Task 4.1 |
| §G 兩軌 oracle | Task 2.1（軌2）+Task 3.3（C-3）+Task 1.1/3.1（C-1）+Task 3.2（C-2）|
| §G 歸因表 class_enum+≥5 wash | Task 0.2+各批尾 append+Task 4.1 |
| §G mutation canonical 可重放 | Task 0.1+Task 4.1 |
| §P B0 | Task 0.1/0.2/0.3 |
| §P B1 | Task 1.1/1.2 |
| §P B2 | Task 2.1/2.2/2.3/2.4 |
| §P B3 | Task 3.1/3.2/3.3/3.4 |
| §P B4 | Task 4.1/4.2 |
| §V 三類 mutation+final gate 禁 skip | Task 4.1 |
| §V 邊界目錄 | Task 4.1 邊界 |
| §R 回退 | §0.8 |
| §N sample_weight defer/adversarial_validator/cross_symbol/feature winsorize/factor 矩陣 | Task 2.3（sample_weight）+Task 3.4（adversarial_validator）+§0（cross_symbol research_only）|
| §N 收官 _fit_global | Task 3.1 |
