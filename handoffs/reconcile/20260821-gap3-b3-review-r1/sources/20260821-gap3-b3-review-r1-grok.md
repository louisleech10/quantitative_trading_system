# GAP-3 B3 review R1 — grok

task-id: 20260821-GAP3-B3-REVIEW-R1
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b3-review-brief.md
diff: `git diff dced9d66..HEAD -- momentum/ tests/`（e72af21c B3.1／da1e6872 B3.2／5074bc04 B3.3）

## Verdict：可進 B4（無 P0 BLOCKING）；建議 stamp 前修 P1（G6 `prevalence_learn` 分母），P2 命名 backstop 可並行

### 必答（逐條）

1. **逐 Task 對 TODO**：B3.1–B3.3 之驗證／邊界／不可做與實作＋測試對得上。白名單 diff 最小：`event_filter.py` 僅薄 adapter＋keyword-only `condition_spec`；`operator_registry.py` 僅五行註冊。未改白名單外既有檔。
2. **D3 角色隔離（B3.1）**：safe-subset 對 Attribute／Subscript／lambda／f-string／walrus／BinOp／`getattr` 等 bypass 實測皆拒。W6 雙案例＋`future_*` 小寫 backstop＋trigger_outcome 拒收成立。**洞**：大小寫變體 `Future_Return` 在 registry 誤登 `pit_feature` 時可過（見 P2）。canonical digest：異白／And-Or 排序／常數翻側／鏈式＝顯式 and／`1`≡`1.0`／`not` 下排序／Eq 翻側皆同 digest；巢狀 `(a and b) and c` vs flat 不同 digest＝結構正規化（保守、不誤併異式），不另開 finding。
3. **W6＋M6**：同式只差 role 雙案例測試鎖死。M6 seam＝`_role_violation`（production `parse_condition` 唯一角色判定點）；mutation 後收下 future 欄 ⇒ 斷言紅。未見第二路徑讓 mutation 仍綠。
4. **B3.2 G1–G6**：(a) eligibility／label 真復用 `_is_eligible`／`_label_from_rule`；(b) `k>0` 時 `mask.shift(-k)` 與 `evaluate_all_bars` 之 `score@ot[i−k]`／label `close[i]→close[i+h]` 映射一致（有測）；(c) 記帳守恆有 raise；(d) 0 命中 loud 空／單類別 `missing_control_group` fail-closed；(e) 全列 `control_kind=platform_same_trigger_rule`（含正例）符合契約「同觸發規則平台產」設計（label=0＝控制組）；(f) `label_value` signed、`trigger_return`／`future_return_h` raw——docstring 已寫；short＋以 raw 結果欄選樣屬使用者語意腳槍，本輪不升 finding。**缺陷**：G6 `prevalence_learn` 取去重前事件基率，與回傳 primary 集不一致且鎖定測 `abs=1.0` 近乎空殼（P1）。
5. **§G-1**：`condition_spec is None` 時走原 `query`／`timestamps`／`none` 分支；測鎖 legacy info 無 `condition_digest`。新 import 單向（`event_filter`→`condition_engine`），無循環；R1 無 `api` import。
6. **B3.3 五算子（adversarial＋手跑）**：閉區間含當根、嚴格變號、`d=0` 不計、無事件 NaN／`cross_count=0`、warmup L vs L−1、禁 `shift(-n)`（源碼無未來 shift）均成立。手跑：經 0 不變號、同號不計、當根交叉⇒0、上穿需嚴格 `<thr`、分母≤0⇒NaN、窗內 NaN⇒整窗 NaN（pandas rolling，測鎖）。`consecutive_run` O(n) 可接受。真實 kline 因果截斷＋history-start 測綠。
7. **可進 B4？** 可以（無 P0）。P1 建議 stamp 前修；不阻塞 B4 開工但會讓 G6 揭露基率誤導。

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 證據 |
|------|------|------|
| fact-verified: B3 Gate＋180＋golden | **本輪複驗 Gate 三測成立；golden 引主委 receipt** | pytest condition/generator 49＋state_counters 17＋M6 1＝全綠；golden 未重跑（brief 禁並行），引 `handoffs/run_receipts/20260821T133500Z-gap3-b3-gate.log` rc_golden=0 |
| assumed: 引擎字面另立 `condition_engine_contract.json` 不違 §0-5 | **成立** | TODO §0-5 限定**事件欄位**字面住 `event_import_contract.json`；引擎 role／AST／failure_reasons／`allowed_filtering_params` 非事件欄位 |
| assumed: `event_source`／`kind_source`／`meta.generator` 為 optional 合法 | **成立** | 契約 `optional_fields`：`event_source` 自由 str、`kind_source`∈{user,platform_auto}、`meta` object；未用以補 conditional_required |
| assumed: G6 對 selection_predicate 仍跑＋`estimand_note` 即足 | **成立（不推翻）** | 用途＝標籤重算；`selection_uses_outcome_columns`＋note 已 loud；拒跑非本批 SPEC 要求 |
| assumed: `condition_spec` 只收 feature＝D3-4 充分；orchestrator 留 B5 | **成立（誠實邊界）** | adapter 拒非 feature；`assert_no_outcome_columns` 出口已備、匯出斷言屬 B5 接線 |
| assumed: 對齊層 `warmup_insufficient_*` 二次丟棄可接受 | **成立** | generator 註解＋記帳把對齊丟棄併入 `n_dropped_by_reason` 並重過 validator |

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
