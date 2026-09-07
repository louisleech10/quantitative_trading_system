"""EVTALIGN Task 2.1（D）：驗證對象＝實際被消費的 label；`label_kind` 由 `label_source` 綁定。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 2.1　TODO：Task 2.1

## 🔴 scaffold 狀態（Task 0.1）
placeholder：`pytest.skip`。**skip 不是綠**——phase gate 1 會因此 rc≠0。

## 實作後本檔須含
- 同尾事件模式之合法密集 label（tail_nans=0）⇒ **通過**（不得誤判，GROK-R1-P0-02）
- 事件 label 與 feature index 錯位 ⇒ 仍 raise
- `(event_id, timestamp, label_value)` 三元組整批平移一格 ⇒ raise（R2 三家：現行三檢查抓不到）
- `label_source` 缺席 ⇒ raise，不得預設（§C-7）
- 標成 `event_given` 但 `label_source != "event_label_value"` ⇒ raise
"""

import pytest


def test_scaffold_placeholder_task_2_1():
    pytest.skip("EVTALIGN Task 2.1 尚未實作——本 skip 由 scripts/evtalign_phase_gate.sh 判為未通過")
