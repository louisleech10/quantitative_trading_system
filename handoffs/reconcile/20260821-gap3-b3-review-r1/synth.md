# Reconcile — 20260821-gap3-b3-review-r1

**來源** 20260821-gap3-b3-review-r1-codex.md, 20260821-gap3-b3-review-r1-composer.md, 20260821-gap3-b3-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；全部寫回，condition_engine＋generator_adapters 64 passed、state_counters 17、M6、golden --check PASS、含 callers 256 passed；receipt `handoffs/run_receipts/20260821T140500Z-gap3-b3-r1-fix-gate.log`）

**Verdict**: 需修補後合併——9 條 findings 全數採納修補（已落檔；CODEX-R1-P2-04 之 `requests.py` 半條屬 api/ B5 白名單，登記 B5 follow-up）；R2 由原提出方重跑同一反例閉合，全 CLOSED 後三家 RECONCILE-STAMP → B3 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| X1 去重逐 label_id | CODEX-R1-P1-01 | **採納**：`generate_events` 對每個 label_id 以其事件子集各建 `AlignmentReceipts`→`build_event_manifest`，primary 保留集取聯集；provenance `manifests{label_id}`／`dedupe{label_id}`；測試：預設 C 情境雙 label 皆存、各 label_id 簇首唯一、逐 label_id 結果＝單獨跑 |
| X2 label 角色純結果欄 | CODEX-R1-P1-02 | **採納**：`_role_violation`（M6 seam 同一點）增 `label` 分支——`pit_feature` ⇒ `role_isolation_violation`；測試：混合式 label 拒／selection 過／feature 拒 |
| X3 control_kind 不可覆寫 | CODEX-R1-P1-03 | **採納**：移除 `GeneratorConfig.control_kind` 欄，寫死 `PLATFORM_CONTROL_KIND`（入口對契約 `accepted` 對證）；測試：帶 control_kind 建構 ⇒ TypeError |
| X4 契約快取不可變＋Protocol 同步 | CODEX-R1-P2-04, CODEX-R1-P2-05 | **採納（momentum 層）**：`load_condition_engine_contract` 每次 `deepcopy`（測試：改寫回傳不污染）；`IEventFilter.apply_filter` 增 `condition_spec` keyword-only 宣告。`api/models/requests.py` 改用契約出口＝B5 白名單範圍，登記 follow-up 不於本批動 |
| X5 邏輯恆真／恆假 parse-time 拒 | COMPOSER-R1-P1-01 | **採納**：`_fold` 三值常數摺疊（and/or/not/cmp＋排中律／矛盾律）⇒ `constant_expression`；8 式 parametrize 拒、含常數子式但依資料者仍過 |
| X6 raw 結果欄 vs signed label_value 揭露 | COMPOSER-R1-P2-02 | **採納**：provenance `outcome_columns_are_raw_unsigned=True`／`label_value_is_signed=True`；short＋結果欄選樣 `logger.warning` loud；short 測試手算 signed |
| X7 prevalence_learn 對齊回傳集 | GROK-R1-P1-01 | **採納（方案①）**：`prevalence_learn`＝去重後 primary 集該 label_id 正例率；報告增 `prevalence_learn_scope=primary_after_dedupe`；測試 `abs=1e-12` 對回傳 `ev` 與 `overall.prevalence_learn` |
| X8 future_* backstop 忽略大小寫 | GROK-R1-P2-01 | **採納**：`casefold()` 比對；測試 `Future_Return`／`FUTURE_X`／`fUtUrE_y` 誤登皆拒 |

白名單檢視：改動限 `condition_engine.py`／`generator.py`（新檔）、`event_filter.py`（§0-6-③）與兩個測試檔；`operator_registry.py`／`state_counters.py` 本輪未動。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: G2 的預設 `scenario="C"` 會在同一 dedupe cluster 只留一列，可能刪掉不同 `label_id` 的合法事件。
**碼證**: `generator.py:254-258` 接受 manifest 的 `in_primary`；`dedupe.py:118-123` 以 cluster 取首列；實跑 `MULTILABEL_C 124 30 ['up1']`（`up5` 全被去掉）。
**來源摘要**: momentum/Analysis/event_samples/generator.py#3a17e7319b19; momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0；正文：信心度 High。修法：dedupe 保留每個 `label_id` 或明確改成 label-aware policy；RECHECK：真實 ETHUSDT 多 label、預設 C 應逐 label_id 留存，並重跑 generator adapters。
## CODEX-R1-P1-02

**斷言**: D3 的 `label` 角色只要求含 outcome，未拒絕混入 `pit_feature`，因此 label 可同時引用特徵與結果欄。
**碼證**: `condition_engine.py:80-85,230-235` `_role_violation` 只判 `feature`；實跑 `parse_condition("f > 0 and future_x > 0", ..., "label")` → `LABEL_ROLE_ACCEPTED {'f': 'pit_feature', 'future_x': 'future_outcome'}`。
**來源摘要**: momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b; momentum/Analysis/contracts/condition_engine_contract.json#110d3196292f；正文：信心度 High。修法：label 僅允許 outcome roles（或另定明確 result-only validator）；RECHECK：混合 role、純 future、feature/selection 雙案例與 M6 seam 均須分別拒收/通過。
## CODEX-R1-P1-03

**斷言**: 平台產生器接受任意 `GeneratorConfig.control_kind`，可產出 `user_labeled_other` 但仍標 `kind_source=platform_auto`、`event_source=platform_generator`。
**碼證**: `generator.py:56-70,197-216` 直接寫入設定值；實跑 override probe → `OVERRIDE_CONTROL_KIND 41 ['user_labeled_other'] ['platform_auto'] ['platform_generator']`。
**來源摘要**: momentum/Analysis/event_samples/generator.py#3a17e7319b19; momentum/Analysis/event_samples/import_contract.py#58c331ca3d5d；正文：信心度 High。修法：平台路徑強制 `platform_same_trigger_rule`，user kinds 僅由 import path 接受；RECHECK：正負 label 全列同值，override 應 loud fail，並驗 validator/provenance。
## CODEX-R1-P2-04

**斷言**: 引擎契約快取是可變 module singleton；任一 caller 可改寫 SoT，且 `allowed_filtering_params` 尚未封閉為單一 API 來源。
**碼證**: `condition_engine.py:34,37-43` 返回原 dict；mutation probe → `MUTABLE_CONTRACT_CACHE ...` 並改變 role prefix；`requests.py:46-53` 仍硬編碼 `{'price_change'}`。
**來源摘要**: momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b; api/models/requests.py#938ff6900fed；正文：信心度 High。修法：深度不可變映射/防禦性 copy，並讓 request validator 使用契約出口；同步 `event_filter.py:53-62` Protocol 的 `condition_spec` keyword。RECHECK：mutation regression、API allowed-list、typing/adapter tests；屬 B5 follow-up，非本批 B4 blocker。
## CODEX-R1-P2-05

**斷言**: `IEventFilter` Protocol 未宣告實作已提供的 `condition_spec` keyword-only 參數，型別契約與 runtime adapter 不一致。
**碼證**: `event_filter.py:53-62` Protocol 只有 query/timestamps；`event_filter.py:90-97` concrete method 才有 `condition_spec`；既有 `test_event_filter.py` 僅覆蓋 runtime legacy/adapter。
**來源摘要**: momentum/Analysis/event_filter.py#b74d2dea231f；正文：信心度 Medium。修法：Protocol 與 concrete signature 同步並補型別層呼叫測試；RECHECK：`venv/bin/python -m pytest tests/momentum/test_event_filter.py -q` 及 type-check。屬介面完整性問題，不單獨阻擋 B4。
## COMPOSER-R1-P1-01

**斷言**: B3.1 邊界②「表達式恆真 ⇒ loud 拒收」可被 `True or <col> …`／`False and <col> …`／排中律 tautology 繞過——`parse_condition` 只拒 structural constant（`_is_constant_tree`／`_is_trivial_compare`），不拒 logical tautology。

**碼證**: `condition_engine.py:227-228` 僅 `_is_constant_tree`＋`_is_trivial_compare`；探針 `venv/bin/python /tmp/gap3_b3_review_probe.py`（本輪自跑）→ `'True or feat > 0'`、`'feat > 0 or True'` **ACCEPTED**，`evaluate_condition` mask 全 True；`'False and feat > 0'` mask 全 False；`'not (feat > 0 or not feat > 0)'` mask 全 False。對照：`('1 < 2', 'constant_expression')`、`('rsi_14 == rsi_14', 'constant_expression')` 已在 `test_condition_engine.py:74-84` 拒收。TODO B3.1 邊界②＋SPEC D3 邊界②原文「恆真 ⇒ loud」。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b

[MAJOR] 信心度=High。失敗模式：使用者提交表面「有特徵條件」、實為全列命中／全列拒的選樣式；`generate_events` 僅 runtime `always_true` warning（`generator.py:181-182`），非 parse fail-closed，與同 Task 對 `1<2` 的處理不一致，選樣偏差風險（RISK-a）。

**修法**（逐條對碼）:
1. 在 `parse_condition` canonical 後新增 `_is_logical_tautology(canon)`：對 bool AST 做 constant folding（`and`/`or`/`not`/`cmp` 在可判定時求值；含 `col` 的子式標 unknown）；恒真／恒假 ⇒ `ConditionError('constant_expression', …)`。
2. `tests/momentum/event_samples/test_condition_engine.py` 新增 parametrize：`True or rsi_14 > 0`、`False and rsi_14 > 0`、`rsi_14 > 0 or not rsi_14 > 0` ⇒ `constant_expression`。
3. （可選）generator 對 logical tautology 仍保留 `always_true` warning 作第二道。

**RECHECK**: `venv/bin/python -m pytest tests/momentum/event_samples/test_condition_engine.py -q` rc=0 且上述三式 pytest.raises。

---

## COMPOSER-R1-P2-02

**斷言**: `build_evaluation_frame` 注入之 `future_return_*`／`trigger_return` 為 **raw**（未乘 direction），而 `label_value` 為 signed；short 方向下 `selection_predicate` 若寫 `future_return_h > thr`，語意為「未來價格上漲」而非「空頭方向有利」，與 signed label 不對齊，且產生器未 loud 標示。

**碼證**: `generator.py:82-94` docstring 明寫 raw；`:207` `label_value=float(sign * (close[i+h]/close[i]-1))`；`:146-146` 條件 evaluate 用 raw 欄。測試 `test_G1_cat10_combination_with_future_column` 僅 `direction=long`（`test_generator_adapters.py:84-90`）。brief 必答 4(f) 假設未在 UI／provenance 層標 signed-vs-raw。

**來源摘要**: momentum/Analysis/event_samples/generator.py#807b9e3d；tests/momentum/event_samples/test_generator_adapters.py#807b9e3d

[MINOR] 信心度=High。失敗模式：short 策略研究員用 raw future 閾值選樣，以為與 label 同向語意，造成選樣條件解讀錯誤（非 silent numeric bug，屬 estimand 文件缺口）。

**修法**:
1. `generate_events` provenance 增 `outcome_columns_are_raw_unsigned: true`（或 selection 含 future/trigger 欄時 warning log）。
2. `build_evaluation_frame` docstring 交叉引用 SPEC short 範例；`test_generator_adapters.py` 增 short＋`future_return_*` 一則 assert provenance 旗標。

**RECHECK**: `venv/bin/python -m pytest tests/momentum/event_samples/test_generator_adapters.py -q -k G1` rc=0。

---

## GROK-R1-P1-01

**斷言**: G6 寫入 `evaluate_all_bars` 的 `prevalence_learn` 取自去重前（align 後、primary 前）事件集之正例率，與產生器回傳的 primary／deduped 事件基率可系統性偏離；鎖定測用 `abs=1.0` 無法抓住該偏離。

**碼證**: `generator.py` 於 `build_event_manifest`／`deduped=…in_primary` 之後仍用前置之 `events` 算 `prevalence_learn`（約 L267–268）；`test_G6_calls_evaluate_all_bars_not_parallel` 註解寫「去重前」但断言對 `ev`（deduped）`pytest.approx(..., abs=1.0)`。手跑 ETHUSDT 12h `ret_1<0` scenario=C：`n_raw=188`／`n_deduped=26`，`prevalence_learn≈0.404` vs primary `label.mean≈0.346`（差≈0.058）。`RECHECK:` 同手跑或把 `abs` 收緊至 `1e-12` 並改期望為 raw 或改碼用 `deduped`。

**來源摘要**: momentum/Analysis/event_samples/generator.py#3a17e7319b19; tests/momentum/event_samples/test_generator_adapters.py#4347205f1316; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

正文：[MAJOR] 信心度=High。失敗模式：case-control 揭露基率與下游實際學習／回傳樣本不一致 ⇒ lift／基率解讀偏誤。修法：① `prevalence_learn = float(deduped[deduped.label_definition…].label.mean())`（與回傳集對齊），或 ② 維持去重前但在 `estimand_note`／provenance 明文 `prevalence_learn_scope=pre_dedupe` 且測試鎖 raw 均值、`abs≤1e-12`。優先 ①。

## GROK-R1-P2-01

**斷言**: D3 命名 backstop `column.startswith("future_")` 區分大小寫；registry 誤將 `Future_Return`（或其它非小寫 `future_*`）標成 `pit_feature` 時，`expression_role=feature` 仍可 parse 通過。

**碼證**: `_role_violation`（`condition_engine.py` L80–85）僅 `startswith(contract["future_column_prefix"])`；契約字面 `"future_"`。實跑：`parse_condition("Future_Return>0", {"Future_Return":"pit_feature"}, "feature")` **允許**；對照 `future_x` 誤登仍拒。`RECHECK:` 同上一行；修後應 `role_isolation_violation`。

**來源摘要**: momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b; momentum/Analysis/contracts/condition_engine_contract.json#110d3196292f; tests/momentum/event_samples/test_condition_engine.py#ae13e582b587

正文：[MAJOR] 信心度=High（洞存在）；真實 FF 欄多為小寫 ⇒ 產品路徑風險 Medium。修法：backstop 改 `column.casefold().startswith(prefix.casefold())`（或契約加 `future_column_prefix_ignore_case: true`）＋測試加 `Future_*`／`FUTURE_*` 誤登案例。主防禦仍是 registry 角色；本條補命名防呆。

ASSUMPTIONS_VERIFIED: §0-5 事件欄位 vs 引擎契約分離；optional meta/event_source/kind_source；G6 selection_predicate+note；D3-4 adapter 角色門＋B5 匯出；對齊二次丟棄記帳；Gate 49+17+M6 綠；W7 手跑反例；safe-subset bypass 拒；digest 翻側/1≡1.0；G6 shift(-k) 映射一致；control_kind 全列同值
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters"` → 49 passed rc=0；`…/feature_engineering/ -q -k state_counters` → 17 passed rc=0；`…/test_mutation_guard.py -q -k M6` → 1 passed rc=0；golden `--check` 本輪未重跑（brief 禁並行），引主委 receipt rc_golden=0／sha 163c4ce…；手跑 prevalence 偏離＋Future_Return 洞＋W7 反例序列
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；觀察到 prevalence_learn 揭露與 primary 基率可偏 ~6pp，未改產品碼）
OUTPUT: handoffs/20260821-gap3-b3-review-r1-grok.md

STATUS: DONE
