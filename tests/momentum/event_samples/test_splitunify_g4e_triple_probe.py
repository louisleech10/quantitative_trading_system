"""(G-4e) 第三份判準之殘餘邊界探針——以 pytest 承載，使結論可重跑、改壞會紅。

🔴 本檔驗的不是產品行為，而是**規格層的一個事實**：`docs/SPLITUNIFY_SPEC.D-002.md`
§G 之 (G-4e) 只在第三份判準**獨立實作**時有效；三份同錯時三者仍會全綠，而把錯誤的
切分成員集凍結進 golden。SPEC 據此把它登記為「殘餘誠實邊界」（散文紀律、非機械保證）。

探針本體在 `handoffs/20260912-splitunify-b9-probe-g4e-triple.py`（純函式、不 import 任何
專案模組）。本檔以 importlib 載入該檔並呼叫其 `run_case`，**刻意不重寫**那些判側函式——
重寫就變成同一邏輯的第三份編碼，而那正是本探針要證明會失效的模式。

反例來源：R9／R10 三家各自給出之 `decision != cutoff` 且落在隔離帶的事件。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PROBE_PATH = (
    Path(__file__).resolve().parents[3]
    / "handoffs"
    / "20260912-splitunify-b9-probe-g4e-triple.py"
)

# 三家反例：(decision_at_ms, feature_cutoff_ms, train_last_ms, test_start_ms)
_CASES = [
    pytest.param(250, 200, 200, 300, id="composer-decision-250"),
    pytest.param(950, 900, 900, 1000, id="grok-gapX-decision-950"),
]


def _load_probe():
    """載入探針模組；找不到即 fail-closed，不得靜默跳過。"""
    assert _PROBE_PATH.is_file(), f"探針檔不存在: {_PROBE_PATH}"
    spec = importlib.util.spec_from_file_location("splitunify_g4e_probe", _PROBE_PATH)
    assert spec is not None and spec.loader is not None, f"探針載入失敗: {_PROBE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("decision, cutoff, train_last, test_start", _CASES)
def test_g4e_independent_third_judgment_catches_correlated_pair(
    decision: int, cutoff: int, train_last: int, test_start: int
) -> None:
    """情形 A：投影與 oracle 同錯、第三份獨立實作 ⇒ G-3b 放行而 (G-4e) 攔下。"""
    probe = _load_probe()
    g3b_pass, g4e_pass, membership_correct = probe.run_case(
        "A",
        decision=decision,
        cutoff=cutoff,
        train_last=train_last,
        test_start=test_start,
        expected_uses_decision=True,
    )
    assert g3b_pass is True, "兩邊同錯時 G-3b 本就會放行；此前提若變，反例已失效"
    assert g4e_pass is False, "第三份若真獨立實作，必須在此攔下"
    assert membership_correct is False, "本案成員集本就是錯的，否則反例不成立"


@pytest.mark.parametrize("decision, cutoff, train_last, test_start", _CASES)
def test_g4e_three_way_same_error_still_passes(
    decision: int, cutoff: int, train_last: int, test_start: int
) -> None:
    """情形 B：三份同錯 ⇒ 三者全綠而成員集仍錯，即須具名登記的殘餘邊界。"""
    probe = _load_probe()
    g3b_pass, g4e_pass, membership_correct = probe.run_case(
        "B",
        decision=decision,
        cutoff=cutoff,
        train_last=train_last,
        test_start=test_start,
        expected_uses_decision=False,
    )
    assert g3b_pass is True
    assert g4e_pass is True, "三份同錯時 (G-4e) 仍放行——這正是殘餘誠實邊界的證據"
    assert membership_correct is False
