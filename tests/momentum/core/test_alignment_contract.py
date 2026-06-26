"""IC AlignmentSpec 契約測試。"""

from __future__ import annotations

import pytest

from momentum.core.contracts import AlignmentSpec, validate_alignment


def test_alignment_spec_fields() -> None:
    spec = AlignmentSpec(
        feature_ts_col="feature_ts",
        target_ts_col="target_ts",
        lag=1,
        freq="1h",
    )

    assert spec.feature_ts_col == "feature_ts"
    assert spec.target_ts_col == "target_ts"
    assert spec.lag == 1
    assert spec.freq == "1h"


def test_validate_alignment_signature() -> None:
    spec = AlignmentSpec(
        feature_ts_col="feature_ts",
        target_ts_col="target_ts",
        lag=1,
        freq="1h",
    )

    assert callable(validate_alignment)
    with pytest.raises(NotImplementedError, match="1-align"):
        validate_alignment(None, None, spec)


def test_alignment_spec_rejects_negative_lag() -> None:
    with pytest.raises(ValueError, match="lag"):
        AlignmentSpec(
            feature_ts_col="feature_ts",
            target_ts_col="target_ts",
            lag=-1,
            freq="1h",
        )


def test_alignment_spec_rejects_invalid_freq() -> None:
    with pytest.raises(ValueError, match="freq"):
        AlignmentSpec(
            feature_ts_col="feature_ts",
            target_ts_col="target_ts",
            lag=1,
            freq="not-a-frequency",
        )
