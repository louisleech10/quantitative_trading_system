"""EVTLABEL `[A-3]`（SPEC ASSUME-3）：`validate_event_given` 對 0/1 float 是否可重用。

否證觀測：對合法 0/1 輸入 raise，或對錯位輸入**不** raise。
本探針兩個方向都跑，rc=0 才算成立。
"""
from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, ".")
from momentum.core.contracts import (  # noqa: E402
    AlignmentViolationError,
    derive_label_kind,
    validate_consumed_label,
)


def _frame(ms):
    idx = pd.to_datetime(list(ms), unit="ms")
    return pd.DataFrame({"f1": [0.1] * len(ms)}, index=idx)


def main() -> int:
    ms = [1_700_000_000_000, 1_700_003_600_000, 1_700_007_200_000]
    expected = {ms[0]: 1.0, ms[1]: 0.0, ms[2]: 1.0}
    owners = {ms[0]: "e0", ms[1]: "e1", ms[2]: "e2"}
    feats = _frame(ms)
    target = pd.Series([1.0, 0.0, 1.0], index=feats.index)

    res = validate_consumed_label(
        feats, target,
        label_kind=derive_label_kind("imported_binary_label"),
        expected_values=expected, event_owners=owners,
    )
    assert res["label_kind"] == "event_given", res
    assert res["checked_samples"] == 3, res
    assert res["consumed_event_labels"] == {"e0": 1.0, "e1": 0.0, "e2": 1.0}, res
    print(f"A3-POSITIVE ok: checked={res['checked_samples']} consumed={res['consumed_event_labels']}")

    # 反向①：值被掉包（1 → 0）必須 raise
    bad = pd.Series([0.0, 0.0, 1.0], index=feats.index)
    try:
        validate_consumed_label(feats, bad, label_kind="event_given",
                                expected_values=expected, event_owners=owners)
    except AlignmentViolationError as exc:
        print(f"A3-NEGATIVE-value ok: {str(exc)[:70]}")
    else:
        print("A3-NEGATIVE-value FAIL: 掉包未被擋")
        return 1

    # 反向②：整條錯位一格（index 平移）必須 raise
    shifted = _frame([ms[1], ms[2], 1_700_010_800_000])
    try:
        validate_consumed_label(shifted, pd.Series([0.0, 1.0, 1.0], index=shifted.index),
                                label_kind="event_given",
                                expected_values=expected, event_owners=owners)
    except AlignmentViolationError as exc:
        print(f"A3-NEGATIVE-shift ok: {str(exc)[:70]}")
    else:
        print("A3-NEGATIVE-shift FAIL: 錯位未被擋")
        return 1

    # 值域：本函式**不**驗值域（0/1 之外照收）——值域閘由 Task 3.3 在 staging 負責
    off = {ms[0]: 7.0, ms[1]: 0.0, ms[2]: 1.0}
    r2 = validate_consumed_label(feats, pd.Series([7.0, 0.0, 1.0], index=feats.index),
                                 label_kind="event_given", expected_values=off, event_owners=owners)
    print(f"A3-DOMAIN note: 非 0/1 照收（checked={r2['checked_samples']}）⇒ 值域閘必須留在 staging")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
