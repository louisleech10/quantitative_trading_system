"""IC AlignmentSpec 契約測試。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import (
    AlignmentReport,
    AlignmentSpec,
    AlignmentViolationError,
    validate_alignment,
)


def _spec(lag: int = 1, freq: str = "1h") -> AlignmentSpec:
    return AlignmentSpec(
        feature_ts_col="feature_ts",
        target_ts_col="target_ts",
        lag=lag,
        freq=freq,
    )


def _close(index: pd.Index) -> pd.Series:
    return pd.Series(np.linspace(100.0, 130.0, len(index)), index=index, name="close")


def _labels_from_close(close: pd.Series, lag: int) -> pd.Series:
    labels = np.log(close.shift(-lag) / close) if lag else pd.Series(0.0, index=close.index)
    return pd.Series(labels, index=close.index, name=f"return_{lag}")


def test_alignment_spec_fields() -> None:
    spec = _spec()

    assert spec.feature_ts_col == "feature_ts"
    assert spec.target_ts_col == "target_ts"
    assert spec.lag == 1
    assert spec.freq == "1h"


def test_validate_alignment_passes_datetime_axis_with_bar_ordinal_oracle() -> None:
    index = pd.date_range("2025-01-01", periods=24, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)

    report = validate_alignment(features, labels, _spec(), close=close)

    assert isinstance(report, AlignmentReport)
    assert report.gap_count == 0
    assert report.gap_rate == 0.0
    assert report.checked_samples >= 8


def test_validate_alignment_accepts_int64_epoch_seconds() -> None:
    dt_index = pd.date_range("2025-01-01", periods=24, freq="1h")
    int_index = pd.Index(dt_index.view("int64") // 1_000_000_000, name="timestamp")
    features = pd.DataFrame({"factor": np.arange(len(int_index), dtype=float)}, index=int_index)
    close = _close(int_index)
    labels = _labels_from_close(close, lag=1)

    report = validate_alignment(features, labels, _spec(), close=close)

    assert report.checked_samples >= 8


def test_validate_alignment_gap_counts_but_passes_cadence() -> None:
    index = pd.date_range("2025-01-01", periods=25, freq="1h").delete(10)
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)

    report = validate_alignment(features, labels, _spec(), close=close)

    assert report.gap_count == 1
    assert report.checked_samples >= 8


def test_validate_alignment_gap_boundary_single_point_mismatch_raises() -> None:
    index = pd.date_range("2025-01-01", periods=180, freq="1h").delete(90)
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)
    shifted = labels.copy()
    shifted.iloc[90] = labels.iloc[91]

    with pytest.raises(AlignmentViolationError, match="label mismatch"):
        validate_alignment(features, shifted, _spec(), close=close, sample_size=8)


def test_validate_alignment_m1_shifted_label_raises() -> None:
    index = pd.date_range("2025-01-01", periods=24, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)
    shifted = labels.copy()
    shifted.iloc[:-1] = np.roll(labels.iloc[:-1].to_numpy(), -1)
    shifted.iloc[-1] = np.nan

    with pytest.raises(AlignmentViolationError, match="label mismatch"):
        validate_alignment(features, shifted, _spec(), close=close)


def test_validate_alignment_m1_single_point_misalignment_raises() -> None:
    index = pd.date_range("2025-01-01", periods=200, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)
    shifted = labels.copy()
    shifted.iloc[100] = labels.iloc[101]

    with pytest.raises(AlignmentViolationError, match="label mismatch"):
        validate_alignment(features, shifted, _spec(), close=close, sample_size=16)


def test_validate_alignment_low_label_coverage_raises() -> None:
    index = pd.date_range("2025-01-01", periods=100, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=5)
    labels.iloc[10:90] = np.nan

    with pytest.raises(AlignmentViolationError, match="coverage too low"):
        validate_alignment(features, labels, _spec(lag=5), close=close)


def test_validate_alignment_missing_close_positions_skip_oracle() -> None:
    index = pd.date_range("2025-01-01", periods=300, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    full_close = _close(index)
    labels = _labels_from_close(full_close, lag=1)
    labels.iloc[100] = np.nan
    close_with_hole = full_close.drop(index=index[100])

    report = validate_alignment(features, labels, _spec(), close=close_with_hole)

    assert report.checked_samples >= 8


def test_validate_alignment_m3_rangeindex_raises() -> None:
    index = pd.RangeIndex(24)
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    labels = pd.Series([0.0] * 23 + [np.nan], index=index, name="return_1")

    with pytest.raises(AlignmentViolationError, match="RangeIndex"):
        validate_alignment(features, labels, _spec())


def test_validate_alignment_m4_wrong_frequency_raises() -> None:
    index = pd.date_range("2025-01-01", periods=24, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=1)

    with pytest.raises(AlignmentViolationError, match="cadence mismatch"):
        validate_alignment(features, labels, _spec(freq="12h"), close=close)


def test_validate_alignment_lag_zero_passes_without_trailing_nan() -> None:
    index = pd.date_range("2025-01-01", periods=12, freq="1h")
    features = pd.DataFrame({"factor": np.arange(len(index), dtype=float)}, index=index)
    close = _close(index)
    labels = _labels_from_close(close, lag=0)

    report = validate_alignment(features, labels, _spec(lag=0), close=close)

    assert report.checked_samples >= 8


def test_validate_alignment_millisecond_index_raises() -> None:
    dt_index = pd.date_range("2025-01-01", periods=24, freq="1h")
    ms_index = pd.Index(dt_index.view("int64") // 1_000_000, name="timestamp")
    features = pd.DataFrame({"factor": np.arange(len(ms_index), dtype=float)}, index=ms_index)
    labels = pd.Series([0.0] * 23 + [np.nan], index=ms_index, name="return_1")

    with pytest.raises(AlignmentViolationError, match="milliseconds"):
        validate_alignment(features, labels, _spec())


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
