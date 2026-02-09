import pandas as pd

from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


def test_align_high_frequency_to_primary():
    source_ts = pd.Series([i * 3600 * 1000 for i in range(13)])
    source_df = pd.DataFrame({"value": list(range(13))}, index=source_ts)
    primary_ts = pd.Series([0, 12 * 3600 * 1000, 24 * 3600 * 1000])

    aligned = TimeframeAligner.align_to_primary(source_df, "1h", primary_ts, "12h")
    assert aligned.index.size == 3
    assert aligned["value"].iloc[1] == 12
    assert aligned["value"].iloc[2] == 12
    assert TimeframeAligner.validate_no_future_leak(aligned, primary_ts)


def test_align_low_frequency_to_primary():
    source_ts = pd.Series([0, 24 * 3600 * 1000, 48 * 3600 * 1000])
    source_df = pd.DataFrame({"value": [1, 2, 3]}, index=source_ts)
    primary_ts = pd.Series([12 * 3600 * 1000, 36 * 3600 * 1000])

    aligned = TimeframeAligner.align_to_primary(source_df, "1d", primary_ts, "12h")
    assert aligned.index.size == 2
    assert aligned["value"].iloc[0] == 1
    assert aligned["value"].iloc[1] == 2


def test_validate_no_future_leak_detects_future():
    primary_ts = pd.Series([0, 12 * 3600 * 1000])
    aligned = pd.DataFrame({"value": [1.0, 2.0]})
    aligned.attrs["source_timestamps"] = pd.to_datetime(primary_ts + 3600 * 1000, unit="ms")
    assert not TimeframeAligner.validate_no_future_leak(aligned, primary_ts)
