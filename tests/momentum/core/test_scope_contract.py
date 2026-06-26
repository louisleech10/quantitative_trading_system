"""IC SelectionScope 契約測試。"""

from __future__ import annotations

import pytest

from momentum.core.contracts import SelectionScope


def test_selection_scope_fields() -> None:
    scope = SelectionScope(
        scope_id="scope-1",
        universe_features=["f1", "f2", "f3"],
        split_label="train",
        evaluated_features=["f1", "f3"],
        n_tests=2,
        method="benjamini_hochberg",
        base_universe_hash="hash-1",
    )

    assert scope.scope_id == "scope-1"
    assert scope.split_label == "train"
    assert scope.n_tests == 2
    assert scope.method == "benjamini_hochberg"
    assert scope.base_universe_hash == "hash-1"


def test_scope_n_tests_matches_evaluated() -> None:
    scope = SelectionScope(
        scope_id="scope-empty",
        universe_features=["f1", "f2"],
        split_label="test",
        evaluated_features=[],
        n_tests=0,
        method="none",
        base_universe_hash="hash-1",
    )

    assert scope.n_tests == len(scope.evaluated_features)


def test_scope_rejects_evaluated_outside_universe() -> None:
    with pytest.raises(ValueError, match="evaluated_features"):
        SelectionScope(
            scope_id="scope-2",
            universe_features=["f1", "f2"],
            split_label="val",
            evaluated_features=["f1", "f3"],
            n_tests=2,
            method="benjamini_hochberg",
            base_universe_hash="hash-1",
        )


def test_scope_rejects_n_tests_mismatch() -> None:
    with pytest.raises(ValueError, match="n_tests"):
        SelectionScope(
            scope_id="scope-3",
            universe_features=["f1", "f2"],
            split_label="test",
            evaluated_features=["f1"],
            n_tests=2,
            method="benjamini_hochberg",
            base_universe_hash="hash-1",
        )
