"""EVTALIGN Task 1.1（B）：label 生成前把 close 裁到 feature 尾——守衛一字不改。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 1.1　TODO：Task 1.1

## 🔴 scaffold 狀態（Task 0.1）

本檔目前為 placeholder：`pytest.skip`。**skip 不是綠**——
`bash scripts/evtalign_phase_gate.sh 1` 會因本檔仍有 skip 而 rc≠0。
Task 1.1 實作時**覆寫**本檔為真實斷言（覆寫＝預期，見 TODO Task 0.1 覆蓋風險）。

## 實作後本檔須含（逐條對應 TODO Task 1.1 驗證）
- 截短案例之 label 與同尾案例 **逐值 ==**（NaN 位置與數值皆同）
- `inspect.getsource(validate_alignment)` 之 sha256 與改前相同（守衛未動）
- spy：stage0 與 stage2 各恰呼叫 `_coterminalize_close` 一次
- purge／embargo／split_row_fingerprint／retained_event_ids 與 golden 逐值 ==
"""

import pytest


def test_scaffold_placeholder_task_1_1():
    pytest.skip("EVTALIGN Task 1.1 尚未實作——本 skip 由 scripts/evtalign_phase_gate.sh 判為未通過")
