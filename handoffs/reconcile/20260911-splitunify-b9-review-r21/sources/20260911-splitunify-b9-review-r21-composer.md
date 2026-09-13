# SPLITUNIFY b9 — review-r21（D1／D2 閉合再驗證）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R21`  
**family**: composer  
**findings-round**: R21  
**審查標的**: commit `ef4d0664`；current block＝`tests/momentum/Analysis/test_splitunify_derive.py` 檔末兩條新測試；`docs/SPLITUNIFY_TODO.md` §C-9 `Task 9.2a` 驗證段  
**禁改碼**：review-only。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: xfail 命令得 `1 xfailed` | **fact-verified** | `venv/bin/python -m pytest -rxX "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0 |
| brief fact-verified: 六路回歸 706 passed、1 xfailed | **fact-verified** | 同 brief 六檔路徑 `-rxX` → **706 passed, 1 xfailed** rc=0（70.29s） |
| brief assumed: 9.2b 完成後測試自然 pass | **fact-verified（需同步拿掉 xfail）** | 探針 `/tmp/r21-composer-probe-opposite.py` 現行 `NO_EXCEPTION`，兩列異側靜默進 `assignments`；9.2b 實作 `AlignmentViolationError` 後 `pytest.raises` 會綠，但 **decorator 未移除 ⇒ strict xfail 轉 XPASS 而紅**（設計意圖） |
| brief assumed: `xfail(strict=True)` 是最佳表達 | **fact-verified** | TODO §驗證第 6 條逐字要求 `1 xfailed`、禁 `--deselect`；`skip` 無法在 9.2b 完成時機械擋「仍紅」 |

---

## 必答 1 — 本家 R20 反例重跑（§B8）

### (1a)

| finding | 判定 |
|---------|------|
| `COMPOSER-R20-P1-01`（xfail 錨點測試缺席） | **CLOSED** |
| `COMPOSER-R20-P2-01`（多 symbol 三計數無具名測試） | **CLOSED** |

### (1b)

- **P1-01**：`rg -n test_multi_feature_tf_opposite_sides_must_fail_closed tests/` → `test_splitunify_derive.py:1616`；`pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **`1 xfailed`**（非 `passed`／`no tests ran`）。fixture 用事件級 `_manifest(keys.drop_duplicates("event_id"))`（:1634），兩 TF cutoff 分落 train／test 段（:1629-1631）。
- **P2-01**：`pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_summary_counts_are_named` → **1 passed** rc=0。MUTATION（多 symbol 分支 `:768-770` 三 kwargs 省略，`/tmp/r21-composer-mutation2.py`）→ **1 failed** `assert 0 == 6`（已還原）。

---

## 必答 2 — xfail 測試是否因「異側」而紅

### (2a)

**是（紅因＝未 raise，非錯誤例外）。** 去掉 xfail 後等價探針 `/tmp/r21-composer-probe-opposite.py`：

```
NO_EXCEPTION
assignments: [{'event_id': 'e_x', 'feature_timeframe': '1h', 'split_label': 'train'},
              {'event_id': 'e_x', 'feature_timeframe': '4h', 'split_label': 'test'}]
purged: []
```

現行碼對同一 `event_id` 兩列給出**異側** `split_label` 且**不 raise** ⇒ `pytest.raises(...)` 得到 `Failed: DID NOT RAISE` ⇒ xfail。非 manifest 重複、非複合鍵碰撞（鍵 `(e_x,1h)`／`(e_x,4h)` 唯一）。

### (2b)

**不必收緊成僅 `AlignmentViolation`；可選在 9.2b 改為型別斷言。** 理由：①現行失敗模式是「沒 raise」，match 字串尚不參與；②TODO `Task 9.2b` 只要求訊息含 `event_id`，不保證含 `AlignmentViolation` 子串——若實作者訊息全中文，僅 `AlignmentViolation` 反而可能 XPASS 失敗；③寬 match `同一事件|異側|同側|AlignmentViolation` 是 consult-r2 起沿用的 fail-safe。9.2b 施工時更佳寫法：

```python
from momentum.core.contracts import AlignmentViolationError  # 或實際定義模組

with pytest.raises(AlignmentViolationError, match=r"e_x"):
    derive_event_split_from_plans(...)
```

並**同 PR 移除** `@pytest.mark.xfail`。本輪不列 BLOCKING——屬 9.2b 施工細節，非 D1 閉合缺口。

---

## 必答 3 — `xfail(strict=True)` 交接摩擦

### (3a)

**摩擦低且可接受。** 9.2b 完成當下實作者須做兩件事：(1) 落地 `AlignmentViolationError`；(2) 移除 xfail decorator。若只做 (1) 不做 (2)，`strict=True` 使 XPASS 轉 fail——正是 TODO 要的 fail-closed，避免「碼已對、標記仍 xfail」靜默漂移。

### (3b)

**現行最好，不建議改 `skip`。** TODO 機械驗收第 6 條以 `1 xfailed` 為通過條件；`skip` 會變成 `skipped` 而非 `xfailed`，與條文衝突。若強行替代：

```python
@pytest.mark.skip(reason="Task 9.2b 未實作 AlignmentViolationError")
def test_multi_feature_tf_opposite_sides_must_fail_closed(): ...
```

會失去「9.2b 完成後必須轉 pass」的 strict 鉗制。**維持 xfail(strict=True)**。

---

## 必答 4 — 第四處 `event_keys` 漏網

### (4a)

**無第四處缺欄建構點。** 全 repo 掃描（`rg 'build_event_keys|def _event_keys|def _keys' --glob '*.py'`）：

| 位置 | 角色 | `feature_timeframe` |
|------|------|---------------------|
| `split_projection.py:259` `build_event_keys` | 唯一 producer | ✅ rename 自 `per_tf.timeframe` |
| `pipeline.py:756` | 唯一生產 caller | ✅ 經 producer |
| `scripts/freeze_splitunify_golden.py:93` `_event_keys` | golden 工具 | ✅ L108-111 |
| `tests/.../test_splitunify_derive.py:116` `_event_keys` | 測試 helper | ✅ L137 |
| `handoffs/20260911-splitunify-b9-probe-multitf.py` | 探針 | ✅ 呼叫 `build_event_keys` |
| `handoffs/20260911-probe-splitunify-negative-injection.py:48` `_keys` | 探針 | ✅ L56（R20 已補） |
| `handoffs/20260911-splitunify-b2b-mutate.py` | mutation 腳本 | N/A（只 mutate `split_projection.py`，不手建表） |
| `api/` | — | **0** 建構點 |

### (4b)

**N/A**（無漏網項、無阻擋）。

**誠實邊界（不阻 9.2b）**：`test_multi_symbol_branch_summary_counts_are_named` 未覆蓋「某 symbol 子批 purged 為空」之 concat 欄集；但 `split_projection.py:741-749` 已具名空批欄集，且 `event_symbols != plan_keys` 會先擋 symbol 集合不一致——殘留風險低，可於 9.2b／golden 階段再補，非本輪 BLOCKING。

---

## 必答 5 — 可否進 `Task 9.2b`（B9C）

### (5a)

**可以進 `Task 9.2b`（批次 B9C）。** 無 BLOCKING finding。

### (5b)

已檢查：本家 R20 兩條反例 CLOSED；xfail 錨點機械驗收 `1 xfailed`；異側探針確認紅因為靜默放行；多 symbol 三計數測試＋多 symbol 分支 mutation 鑑別力；六路回歸 **706 passed、1 xfailed**；全 repo `event_keys` 建構點無第四處漏欄；TODO `Task 9.2a` 驗證段（:549-565）與現行測試名／mutation 字面一致。

---

## §1 必查（摘要）

1. 矛盾/互斥：無
2. 漏项/端到端：無（D1／D2 已閉）
3–11：無

---

## COMPOSER-R21-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；本家 R20 兩條反例均已 CLOSED，brief 兩條 assumed（9.2b 自然 pass、xfail 最佳）經探針與條文對讀確認可接受。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0；六路回歸 `-rxX` → **706 passed, 1 xfailed** rc=0；`/tmp/r21-composer-probe-opposite.py` → `NO_EXCEPTION`＋異側 assignments；`/tmp/r21-composer-mutation2.py`（省略多 symbol 三 kwargs）→ **1 failed** `assert 0 == 6`（已還原）；`rg build_event_keys|def _event_keys|def _keys` 全 repo 無第四處缺 `feature_timeframe`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#6dd7a70a9b0d

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: xfail 1 xfailed；706+1xfail 回歸；異側探針 NO_EXCEPTION；多 symbol mutation 轉紅；event_keys 全掃無第四處；match／xfail 交接分析
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；六路 `pytest -q … -rxX` → 706 passed 1 xfailed；`pytest -q …::test_multi_symbol_branch_summary_counts_are_named` → 1 passed；`/tmp/r21-composer-probe-opposite.py`；`/tmp/r21-composer-mutation2.py` → MUTATION_RC=1 後還原
FAILURES_SEEN: none（review-only；mutation 預期失敗已還原）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r21-composer.md

STATUS: DONE
