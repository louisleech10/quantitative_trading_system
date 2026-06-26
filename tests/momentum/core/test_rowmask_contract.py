"""IC RowMaskPlan 契約測試。"""

from __future__ import annotations

import numpy as np
import pytest

from momentum.core.contracts import RowMaskPlan


def test_rowmask_roundtrip() -> None:
    idx = np.array([0, 2, 4])
    plan = RowMaskPlan(
        row_index=idx,
        index_kind="positional",
        source="split",
        base_universe_hash="hash-1",
        length=5,
        symbol="BTCUSDT",
    )

    mask = plan.to_mask(5)
    restored = RowMaskPlan.from_mask(
        mask,
        index_kind="positional",
        source="split",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    assert plan.n_selected == 3
    assert restored.n_selected == 3
    assert (restored.row_index == idx).all()


def test_rowmask_requires_index_kind() -> None:
    mask = np.array([True, False, True])
    with pytest.raises(ValueError, match="index_kind"):
        RowMaskPlan.from_mask(
            mask,
            source="feature_filter",
            base_universe_hash="hash-1",
        )


def test_rowmask_all_false_has_zero_selected() -> None:
    plan = RowMaskPlan.from_mask(
        np.array([False, False, False]),
        index_kind="positional",
        source="feature_filter",
        base_universe_hash="hash-1",
    )

    assert plan.n_selected == 0
    assert plan.to_mask(3).tolist() == [False, False, False]


def test_rowmask_length_mismatch_raises() -> None:
    plan = RowMaskPlan(
        row_index=np.array([1]),
        index_kind="positional",
        source="event",
        base_universe_hash="hash-1",
        length=3,
    )

    with pytest.raises(ValueError, match="length"):
        plan.to_mask(4)
