"""EVTALIGN Task 2.2：跨模式不變式——被驗的 series ＝ 被 IC 消費的 series。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 2.2　TODO：Task 2.2

## 🔴 scaffold 狀態（Task 0.1）
placeholder：`pytest.skip`。phase gate 2 會因此 rc≠0。

## 實作後本檔須含
- 以**實際可觸發的情境**參數化：`global_with_labels`／`global_without_labels`／`event`／`cross_sectional`
  🔴 **不得照後端 enum**（`longitudinal`/`cross_sectional` 兩值）——那會整個漏掉事件模式。
- 每情境：spy 記錄「傳給 `validate_alignment` 的 series」與「進入 IC 計算的 series」，斷言同一份。
- `cross_sectional` ⇒ 標 `not_applicable` 並寫明理由（EA-RESID-2：模組未完工），不得靜默跳過。
- 情境清單為模組級常數；新增模式未列入 ⇒ 測試紅。
"""

import pytest

#: 情境清單（模組級常數；新增模式必須加在這裡，否則不變式測試不涵蓋它）
SCENARIOS = ("global_with_labels", "global_without_labels", "event", "cross_sectional")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scaffold_placeholder_task_2_2(scenario):
    pytest.skip(f"EVTALIGN Task 2.2 尚未實作（{scenario}）——本 skip 由 phase gate 判為未通過")
