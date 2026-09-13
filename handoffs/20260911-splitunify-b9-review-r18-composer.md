# SPLITUNIFY b9 — Task 9.1 實作碼審 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R18`  
**family**: composer  
**findings-round**: R18  
**審查標的**: commit `0bd91069`；current block＝`split_projection.py`／`pipeline.py`／`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.1  
**禁改碼**：review-only。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 692 passed | **fact-verified** | `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/ tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → **692 passed** rc=0 |
| brief fact-verified: M-SU-D2-01 三紅／M-SU-D2-02 一紅 | **fact-verified** | 本輪重跑：刪 `_build_summary` 之 `discarded_rows_by_feature_tf` 鍵 ⇒ **3 failed**；`_derive_single_symbol` 之 `_build_summary` 呼叫改 `discarded_rows_by_feature_tf={}` ⇒ **1 failed**；皆已還原 |
| brief assumed: `discarded` 批次級、不需逐 symbol 相加 | **fact-verified（實作對）** | `pipeline.py:747-754` 對整批 `receipts` 呼叫一次 `build_event_keys`；多 symbol 分支 `split_projection.py:685-688` 原樣傳遞、不重呼 producer；逐 symbol 相加會重複計數 |
| brief assumed: `value_counts()` 對所有 dtype 正確 | **部分推翻** | `str`／`Categorical`（含未出現類別）無零值偽項；`per_tf.timeframe=NaN` 之 dropped 列 ⇒ 鍵 `'nan'`（見必答 3） |
| brief assumed: 多 symbol 分支 summary 帶 discarded | **fact-verified** | 探針實跑 `_interleaved_case()` + `discarded_rows_by_feature_tf={"4h":7,"12h":2}` ⇒ summary 值相等（見必答 2） |

---

## 必答 1 — 「逐 symbol 相加」vs「批次級原樣傳遞」

### (1a)

**實作對；TODO 條文字面錯。**

`discarded` 在 `build_event_keys` 對**整批** `receipts.per_tf` 一次計數，不是 per-symbol 分量。`pipeline.py` 僅一處呼叫（`grep -n build_event_keys momentum/Analysis/event_samples/pipeline.py` → import + L747）；多 symbol 分派器只切 `event_keys` 與 `manifest`，不重呼 producer。若照 TODO「逐 symbol 相加」，同一 TF 列數會被乘上 symbol 數——與 producer 語意矛盾。

### (1b)

**建議 TODO Task 9.1 實作要點 2 改字**（doc-literal-only，不阻 9.2）：

> 多 symbol 分派器將 producer 之 `discarded_rows_by_feature_tf` **原樣**寫入合併後 `EventSplitPlan.summary`（批次級；**不得**逐 symbol 重算或相加）。

---

## 必答 2 — 多 symbol 分支 discarded 傳遞

### (2a)

**帶到了。** 反例實跑（`/tmp/r18-composer-probes.py`）：

```text
multi-symbol summary discarded: {'4h': 7, '12h': 2}
equals producer: True
```

機制：`derive_event_split_from_plans` Mapping 分支在 `split_projection.py:677-688` 呼叫 `_build_summary(..., discarded_rows_by_feature_tf=discarded_rows_by_feature_tf)`；per-symbol 迴圈（L654-658）**不**傳 discarded（正確——批次級）。

### (2b)

**應補具名測試**（見 `COMPOSER-R18-P2-01`）。現有 `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 只走單 symbol wrapper，多 symbol 專屬破壞可全綠。

---

## 必答 3 — `value_counts()` 與 dtype

### (3a)

| dtype | 試法 | 結果 |
|-------|------|------|
| `str`（fixture 同型） | 基線 fixture | `{'4h': 2, '12h': 1}`，值為 Python `int` |
| `Categorical`（categories 含未出現的 `12h` 在 schema、實際有 12h 列） | 同 fixture 轉 Categorical | 同基線，**無**計數為 0 的幽靈鍵 |
| `object` + `NaN` timeframe（dropped 列） | 額外插入 NaN 列 | `{'4h': 2, '12h': 1, 'nan': 1}`——鍵字面 `'nan'` |

`int(n)` 轉換覆蓋 `build_event_keys`（L295-296）與 `_build_summary`（L762-763）兩條寫入路徑。

### (3b)

**不阻 9.2**；若上游可能出現 NaN timeframe，最小修法：在 `value_counts` 前 `dropna()` 或過濾 `dropped_tf[dropped_tf != 'nan']`。現行對齊路徑未見 NaN timeframe 為合法輸入，屬邊界誠實性缺口（P3，見 `COMPOSER-R18-P3-01`）。

---

## 必答 4 — 全 repo `build_event_keys` 呼叫端

### (4a)

`grep -rn "build_event_keys" --include='*.py' .`（生產 + 測試 + handoffs）：

| 路徑 | 狀態 |
|------|------|
| `momentum/Analysis/event_samples/pipeline.py:747` | ✅ tuple unpack + 傳遞 |
| `tests/momentum/Analysis/test_splitunify_derive.py` | ✅ 全改 tuple unpack |
| `handoffs/20260911-splitunify-b9-probe-multitf.py:47` | ❌ 仍 `out = build_event_keys(...)` 單值；實跑 **TypeError** |
| `handoffs/20260911-splitunify-b2b-mutate.py` | 僅字串引用 mutation 說明，非呼叫 |

### (4b)

**probe 不阻 9.2**（非生產路徑），但破壞 `docs/SPLITUNIFY_SPEC.D-002.md` §A FACT-RECEIPT 可複驗性（P2，見 `COMPOSER-R18-P2-02`）。`b2b-mutate.py` 不阻。

---

## 必答 5 — mutation 鑑別力

### (5a)

**有鑑別力**（本輪重跑確認）：

- `M-SU-D2-01`（刪 summary 鍵）⇒ `test_summary_has_all_thirteen_keys` + `test_summary_carries_...` + `test_discarded_layer_is_independently_revertible` **3 failed**
- `M-SU-D2-02`（`_derive_single_symbol` 路徑改傳 `{}`）⇒ `test_summary_carries_...` **1 failed**

### (5b)

**第三種破壞（多 symbol 專屬）**：僅將 `split_projection.py:688` 改為 `discarded_rows_by_feature_tf={}`（單 symbol 路徑不動）⇒ **692 passed 全綠**。根因：無多 symbol + discarded 具名測試。見 `COMPOSER-R18-P2-01`。

---

## 必答 6 — 可否進 Task 9.2

### (6a)

**可以進 `Task 9.2`**（`VERDICT: proceed`）。無 P0/P1 產品缺陷；記帳資料流在單 symbol 與多 symbol 路徑行為正確，mutation 01/02 有效。

### (6b)

已檢查：commit diff 三檔、`build_event_keys` 全 repo 呼叫、692 測試、M-SU-D2-01/02 重跑、多 symbol discarded 反例實跑、`value_counts` 三種 dtype、summary 鍵數掃描（無下游寫死 12 鍵；`_build_summary` docstring 仍寫「12 鍵」為過期註解 doc-literal-only）。

**建議最小閉合（不阻 9.2，宜與 9.2 同批或緊接）**：

1. 補 `test_per_symbol_summary_carries_discarded_rows_by_feature_tf`（多 symbol Mapping 路徑）
2. 修 `handoffs/20260911-splitunify-b9-probe-multitf.py` tuple unpack（恢復 FACT-RECEIPT）

---

## COMPOSER-R18-P2-01

**斷言**: 多 symbol Mapping 分支之 `discarded_rows_by_feature_tf` 無具名測試；僅破壞 `split_projection.py:688` 為 `{}` 時 **692 passed 全綠**，記帳可在多 symbol 路徑靜默失效。

**碼證**: `split_projection.py:677-688` 多 symbol `_build_summary` 傳遞 discarded；per-symbol 迴圈 L654-658 不傳。`test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 只用 `_basic_case()` 單 symbol。第三 mutation 實跑：`awk 'NR==688{sub(/discarded_rows_by_feature_tf=discarded_rows_by_feature_tf/,"discarded_rows_by_feature_tf={}")}1' split_projection.py` → 全套 692 passed。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d9674adea08c

[P2] 修法：在 `test_splitunify_derive.py` 增 `test_per_symbol_summary_carries_discarded_rows_by_feature_tf`——用 `_interleaved_case()` + 非空 `discarded_rows_by_feature_tf` 斷言 summary 值相等。可行性：沿用既有 `_interleaved_case` fixture，無新腳本；加後第三 mutation 必紅。信心度=High。

---

## COMPOSER-R18-P2-02

**斷言**: `handoffs/20260911-splitunify-b9-probe-multitf.py` 未隨 Task 9.1 tuple 回傳更新，實跑 case A 即 `TypeError`，§A FACT-RECEIPT 不可複驗。

**碼證**: `handoffs/20260911-splitunify-b9-probe-multitf.py:47-52` 仍 `out = build_event_keys(...); len(out)`；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → `TypeError: tuple indices must be integers or slices, not str`。

**來源摘要**: handoffs/20260911-splitunify-b9-probe-multitf.py#probe-broken

[P2] 修法：`keys, discarded = build_event_keys(...)` 並在 case C 印出 `discarded`。可行性：單檔兩行；不動生產碼。信心度=High。不阻 9.2。

---

## COMPOSER-R18-P3-01

**斷言**: `per_tf["timeframe"]` 為 NaN 之 dropped 列會產生 `discarded` 鍵 `'nan'`，可能誤導呼叫端。

**碼證**: `/tmp/r18-composer-probes.py` 插入 NaN timeframe 列 ⇒ `discarded={'4h': 2, '12h': 1, 'nan': 1}`；`split_projection.py:294-296` 無 `dropna`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d9674adea08c

[P3] doc-literal-only 邊界。修法：計數前 `dropna()` 或排除 `str(tf)=='nan'`。現行對齊路徑未見 NaN 為合法輸入；不阻 9.2。信心度=Medium。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: 692 passed；M-SU-D2-01 三紅／M-SU-D2-02 一紅；多 symbol discarded 反例；value_counts 三 dtype；全 repo build_event_keys 掃描；第三 mutation 692 綠  
TESTS_RUN: 全套 692 pytest rc=0；M-SU-D2-01/02 mutation 重跑；`/tmp/r18-composer-probes.py`；第三 mutation（僅 L688）692 綠；`handoffs/...-probe-multitf.py` TypeError  
FAILURES_SEEN: none（mutation 預期失敗已還原）  
SCOPE_CHANGES: none（review-only；/tmp 探針已清）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
