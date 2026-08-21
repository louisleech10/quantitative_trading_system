# GAP-3 B3 review R1（COMPOSER）

TASK_ID: 20260821-GAP3-B3-REVIEW-R1  
FAMILY: COMPOSER  
SCOPE: brief 指定 B3.1–B3.3 實作／測試／diff；review-only，未改程式碼。

## Verdict：需修補後派工（P1 修復或 reconcile 裁決後可進 B4）

B3 Gate 四命令與 adversarial 探針本輪複驗 rc=0；B3.1–B3.3 主線（角色隔離、G6 復用 B2.5、五算子 W7、§G-1 golden）整體對齊 FROZEN TODO。**一項 P1**：`parse_condition` 對「引用欄位但邏輯恆真／恆假」的 tautology 未落 TODO 邊界②之 parse-time 拒收（見 COMPOSER-R1-P1-01）。**一項 P2**：short 方向下 selection 用 raw `future_return_*` 與 signed `label_value` 語意未在產生器層 loud 揭露（見 COMPOSER-R1-P2-02）。其餘 brief 必答項與 assumed 前提見下文；無 P0。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 摘要 |
|------|------|------|
| 引擎字面另立 `condition_engine_contract.json` | **成立** | TODO §0-5 限「事件欄位」JSON SoT；引擎 AST／reason 分檔合理，程式只讀契約、禁複列。 |
| `event_source`/`meta.generator` 非 meta 補洞 | **成立** | 契約 optional 欄；值為平台枚舉＋digest，非繞 validator。 |
| G6 對 selection_predicate 引用結果欄只標 `estimand_note` | **成立（B3 範圍內）** | 全 K 線重算本為標籤重算；note 誠實；預測力評估留 B5 orchestrator。 |
| `event_filter` condition_spec⊥query＋只收 feature＝D3-4 | **成立（adapter 層）** | `apply_condition_spec`/`apply_filter` 雙重拒 selection_predicate；FF 特徵表 export 接線留 B5。 |
| 對齊層二次丟棄 vs B2.5 eligibility 兩層分母 | **成立** | `accounting_ok` 守恆＋對齊 reason 記帳；設計可接受。 |

---

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

## 必答逐項（摘要）

1. **TODO 驗收 B3.1–3**：B3.1 AST 白名單／digest／W6／M6 seam 對齊；**漏**：logical tautology（P1-01）。B3.2 G1–G6、記帳、fail-closed、G6 呼叫 `_ab.evaluate_all_bars`＋`_is_eligible`/`_label_from_rule` 直接 import 確認；`event_filter`/`operator_registry` diff 最小（白名單內）。B3.3 五算子 W7 手算＋真實 kline history-start 測試齊；registry 僅五行。
2. **D3 隔離**：subscript/attr/lambda/f-string/walrus/import 探針全 `disallowed_*`；`future_*` 命名 backstop＋registry 角色雙檢；digest And/Or 排序、常數翻側、`1`/`1.0` 同 digest 探針 OK；`not` 下排序未見不等價碰撞。`event_filter` D3-4 adapter 成立；`assert_no_outcome_columns` 僅測試／export helper，FF 主徑 B5。
3. **W6＋M6**：`test_condition_engine.py:38-62` 雙案例；M6 唯一 seam=`_role_violation`（`condition_engine.py:80-85`），`test_M6_*` monkeypatch 該函式必紅，無第二生產路徑。
4. **B3.2 語意**：(a) eligibility/label 復用 B2.5 私有函式，非平行。(b) G6 `_rule` 用 `mask.shift(-k)`，`evaluate_all_bars` 在 `i` 取 `scores[i-k]`（`all_bars_eval.py:170-171`），與觸發根 `i` 一致，未偷渡未來。(c) `accounting_ok` 雙段守恆。(d) 0 命中 `status=empty`；單類別 validator raise。(e) `platform_same_trigger_rule` 全列同值含 control=0 過 validator（測試覆蓋）。(f) raw vs signed：P2-02。
5. **§G-1**：`condition_spec=None` 預設走 legacy query；新 import 無循環；`grep -r "from api\." momentum/` 未跑但 `event_filter→condition_engine` 單向；golden `--check` PASS sha 163c4cec…。
6. **B3.3 adversarial**：手造序列探針—`d=0` 不計交叉、窗 exclusive、NaN 斷 pair、warmup L vs L−1 與 metadata 一致；無 `shift(-n)`；`consecutive_run` O(n) 可接受。未發現算子數值錯誤。
7. **進 B4**：P1-01 修復或 committee 裁決 runtime warning 足夠後可 stamp；無 P0。

---

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters" → 49 passed rc=0
venv/bin/python -m pytest tests/momentum/feature_engineering/ -q -k state_counters → 17 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M6 → 1 passed rc=0
venv/bin/python scripts/gap3_freeze_golden.py --check → CHECK PASS canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463
venv/bin/python /tmp/gap3_b3_review_probe.py → AST bypass 全拒；tautology ACCEPT（P1 證據）
```

ASSUMPTIONS_VERIFIED: 上述命令＋`git diff dced9d66..HEAD -- momentum/ tests/` 三 commit 範圍＋`all_bars_eval.py:45-88`／`generator.py:192-273` 對讀。  
TESTS_RUN: 見 VERIFY。  
FAILURES_SEEN: none（gate 全綠；P1 為規格缺口非 pytest 紅）。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: review-only；指出 tautology 可致全列選樣（行為缺口，非本輪改動）。

OUTPUT_PATH: handoffs/20260821-gap3-b3-review-r1-composer.md

STATUS: DONE
