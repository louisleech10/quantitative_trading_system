# SPLITUNIFY b9 — review-r20（B9B Task 9.2＋9.2a）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R20`  
**family**: composer  
**findings-round**: R20  
**審查標的**: commit `9e87386f`；current block＝brief 指定之 `split_projection.py`／`pipeline.py`／`freeze_splitunify_golden.py`／`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.2／9.2a  
**禁改碼**：review-only。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 705 passed | **fact-verified** | `venv/bin/python -m pytest -q`（brief 六檔路徑）→ **705 passed** rc=0 |
| brief fact-verified: 五種破壞各自轉紅 | **未獨立重跑** | 依 receipt `20260913T165740Z-splitunify-b9b-task92-92a`；本輪未 mutate |
| brief assumed: 多 TF 不會出現 purged+assign 混態 | **推翻（有條件）** | `/tmp/r20-composer-probe1b.py`：`cutoff` 不同時 `mixed_purged_assign=True`（見必答 1） |
| brief assumed: 多 symbol 三計數正確 | **fact-verified** | `/tmp/r20-composer-verify.py` probe2：`counts_match=true` |
| brief assumed: 多 symbol 空子批 concat 欄集 | **fact-verified（路徑不可達）** | `event_symbols != plan_keys` 先擋；單標空批欄集 probe2 已驗 |

---

## 必答 1 — cutoff 不同的多 feature TF 反例

### (1a)

**會。** 現行碼逐列用 `feature_cutoff_ms` 判側（`split_projection.py:607-640`），`cutoff` 不同 ⇒ 同 `event_id` 可異側或跨表混態。

實跑（`/tmp/r20-composer-probe1b.py`）：

| 反例 | 結果 |
|------|------|
| `train_leak_1h_plus_test_4h` | `e_a`：`1h`→`purged`，`4h`→`assign/test`；`mixed_purged_assign=True` |
| `gap_1h_plus_test_4h` | `e_b`：同上形態 |
| `opposite_sides_no_purge`（probe1） | `e_mix`：`1h`→test、`4h`→train；兩列皆在 `assignments` |

### (1b)

**屬 `Task 9.2b`，非本批 BLOCKING。** TODO `Task 9.2a` L533-537 明定判側仍 `feature_cutoff_ms`、異側 `AlignmentViolationError` 與事件級錨定屬 `9.2b`；碼註 `split_projection.py:617-619` 亦指跨表互斥待 `9.2b`。現行混態是**已知過渡行為**，應由 `9.2b` 廣播＋`(3.2)` 擋下，不在 `9.2a` 補最小修法。

---

## 必答 2 — 多 symbol 分支三計數

### (2a)

**正確。** `_interleaved_case` 擴成雙 feature TF（12 列／6 事件），`derive_event_split_from_plans(plans, …)`：

- `n_events=6`＝`event_id.nunique()`
- `n_event_tf_rows=12`＝`len(event_keys)`
- `n_event_tf_rows_purged=0`＝`len(purged)`；`n_purged` 同值
- `assign_cols`／`purged_cols` 含 `feature_timeframe`

### (2b)

**該補。** 建議：`test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`——在 `_interleaved_case` 雙 TF fixture 上斷言三鍵與 `len(purged)`；現僅 `test_summary_has_n_events_and_n_event_tf_rows` 覆蓋單標的路徑（P2-01）。

---

## 必答 3 — 全 repo `event_keys` 建構點

### (3a)

| 位置 | 角色 | `feature_timeframe` |
|------|------|---------------------|
| `split_projection.py:259` `build_event_keys` | 唯一 producer | ✅ L324-326 rename |
| `pipeline.py:756` | 唯一生產 caller | ✅ 經 producer |
| `scripts/freeze_splitunify_golden.py:93` `_event_keys` | golden fixture | ✅ L108-111 |
| `tests/.../test_splitunify_derive.py:116` `_event_keys` | 測試 helper | ✅ L137 |
| `handoffs/20260911-splitunify-b9-probe-multitf.py` | 探針 | ✅ 呼叫 `build_event_keys`，不手建表 |
| `api/` | — | **0** 建構點 |

### (3b)

**無阻擋項。** 無生產路徑缺欄；測試 helper 與 golden 已同步。

---

## 必答 4 — golden 逐值比對

### (4a)

**11 個頂層鍵逐值未變。** `git show 9e87386f^` vs `9e87386f` 之 `tests/golden/splitunify/splitunify_golden.json`：`diff -q` 無差異（1740 bytes 相同）。

### (4b)

**N/A**（無變動鍵）。

---

## 必答 5 — NaN fail-closed 全欄提前

### (5a)

**會誤殺。** `selected_timeframe="1h"`、缺值只在 `4h`（未選中）列：`build_event_keys` → `ValueError: …timeframe 欄有缺值…`（`/tmp/r20-composer-verify.py` probe5）。

### (5b)

**預期。** `split_projection.py:298-304` 與 TODO `Task 9.2` 明定檢查提前到**全欄**——全量模式無「被丟棄側」，單選亦不得讓未選中列藏 NaN 假 TF。非回歸缺陷。

---

## 必答 6 — 第六種破壞

### (6a)

**有。** TODO `Task 9.2a` §驗證第 6 條要求之 `test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）**完全未落地**：

- `rg test_multi_feature_tf_opposite tests/` → 0 hits
- `pytest …::test_multi_feature_tf_opposite_sides_must_fail_closed` → `no tests ran`

705 綠**不能**證明該機械閘存在；刪掉（或從未寫）此測試亦全綠——與五種 mutation 不同類的**驗收空心化**（見 P1-01）。

### (6b)

**先修 P1-01 再進 `Task 9.2b`。** 缺 xfail 锚点 ⇒ 9.2a 契約未閉合；混態／異側行為本身可留待 `9.2b` 修法，但**測試殼**必在進 `9.2b` 前補上（fixture 修 ① 已完成語意，只差測試檔）。

---

## COMPOSER-R20-P1-01

**斷言**: `Task 9.2a` 機械驗收第 6 條要求之 `test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）未存在，使 opposite-side／混態回歸可被刪除而全套仍綠。

**碼證**: `docs/SPLITUNIFY_TODO.md:539-542` 逐字要求 node id 與 `1 xfailed`；`rg -n test_multi_feature_tf_opposite_sides tests/` → 0；`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → `no tests ran`。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:539
MUTATION: 刪除（或從未添加）該測試函式 → 現行 `pytest -q tests/momentum/Analysis/test_splitunify_derive.py` 仍 **全綠**（已實測 705 含 derive 子集）

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。TODO 明文「缺此則刪掉該測試也不會紅」——本輪實證為真。

**修法**: 在 `test_splitunify_derive.py` 新增該測試：fixture 用事件級 `_manifest`（① 已修）、兩 feature TF 不同 `feature_cutoff_ms` 構造異側；`@pytest.mark.xfail(strict=True, reason="Task 9.2b: event-level anchor + AlignmentViolationError")`；預期現行碼不 raise ⇒ xfailed。

**可行性**: 依 probe1／probe1b 反例可穩定構造；`pytest -rxX` 應輸出 `1 xfailed` 後 derive 全套仍 rc=0。

---

## COMPOSER-R20-P2-01

**斷言**: 多 symbol（Mapping）分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 無具名測試，子批計數錯誤可靜默過 705 綠。

**碼證**: `split_projection.py:767-770` 三鍵以整批 `event_keys` 計算；`/tmp/r20-composer-verify.py` probe2 `counts_match=true`；`rg test_multi_symbol.*n_event_tf tests/` → 0；僅 `test_summary_has_n_events_and_n_event_tf_rows` 走單標的 `_multi_feature_tf_case`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High。計數邏輯本輪探針正確，缺口在測試覆蓋。

**修法**: 新增 `test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`：`_interleaved_case`＋雙 TF 擴展，斷言三鍵與 `len(purged)`、`n_symbols==2`。

---

## §1 必查（摘要）

1. 矛盾/互斥：無（TODO 9.2a 要求 xfail 測試與實作落差見 P1-01）
2. 漏項/端到端：P1-01（機械驗收）、P2-01（多 symbol 計數測試）
3–5,7–11：無
6. Agent 可執行性：P1-01 使 9.2a 驗收命令第 6 條不可執行

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R20-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: 705 passed；probe1/1b 混態與異側；probe2 多 symbol 計數；probe5 NaN 全欄；golden byte-identical；event_keys 建構點掃描；xfail 測試缺失
TESTS_RUN: `pytest -q`（brief 六檔）→ 705 passed；`/tmp/r20-composer-verify.py`；`/tmp/r20-composer-probe1b.py`；`pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → no tests ran；`diff -q` golden before/after
FAILURES_SEEN: none（review-only）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r20-composer.md

STATUS: DONE
