import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_filter import EventFilter
from momentum.core.exceptions import InvalidQueryError


def test_apply_filter_query_simple():
    """Query 模式可正確過濾。"""
    df = pd.DataFrame(
        {
            "open": [100, 100, 100, 100],
            "close": [102, 104, 101, 99],
        }
    )
    event_filter = EventFilter(
        {"min_events": 1, "sample_size_tiers": {"low_confidence": 1}}
    )

    filtered, info = event_filter.apply_filter(df, query="close > open * 1.03")

    assert len(filtered) == 1
    assert info["mode"] == "query"
    assert info["tier"] in {"sufficient", "marginal", "low_confidence"}


def test_apply_filter_query_complex():
    """複合 Query 可正確解析。"""
    df = pd.DataFrame(
        {
            "close": [10, 20, 30, 40],
            "close_EMA_55": [12, 18, 25, 35],
            "close_ADX_14": [10, 30, 40, 20],
        }
    )
    event_filter = EventFilter({"min_events": 1})

    filtered, _ = event_filter.apply_filter(
        df, query="(close > close_EMA_55) & (close_ADX_14 > 25)"
    )

    assert filtered.index.tolist() == [1, 2]


def test_validate_query_rejects_exec_and_unknown_column():
    """validate_query 可拒絕危險關鍵字與不存在欄位。"""
    df = pd.DataFrame({"close": [1, 2, 3], "open": [1, 1, 1]})
    event_filter = EventFilter({})

    assert event_filter.validate_query("__import__('os')", df.columns.tolist()) is False
    assert event_filter.validate_query("exec('x')", df.columns.tolist()) is False
    assert event_filter.validate_query("unknown > 0", df.columns.tolist()) is False

    with pytest.raises(InvalidQueryError):
        event_filter.apply_filter(df, query="unknown > 0")


def test_timestamps_mode_and_insufficient_tier():
    """timestamps 模式應正確過濾並回報 insufficient。"""
    df = pd.DataFrame({"value": [1, 2, 3, 4]}, index=[10, 20, 30, 40])
    event_filter = EventFilter({"min_events": 30, "sample_size_tiers": {"low_confidence": 30}})

    filtered, info = event_filter.apply_filter(df, timestamps=[10, 30])

    assert filtered.index.tolist() == [10, 30]
    assert info["mode"] == "timestamps"
    assert info["tier"] == "insufficient"
    assert np.isnan(info["adjusted_p_threshold"])


def test_apply_filter_requires_df():
    """df 為 None 應觸發錯誤。"""
    event_filter = EventFilter({})

    with pytest.raises(ValueError):
        event_filter.apply_filter(None)


def test_apply_filter_invalid_query_eval_error(monkeypatch):
    """Query 評估失敗應拋出 InvalidQueryError。"""
    df = pd.DataFrame({"close": [1.0, 2.0], "open": [1.0, 1.0]})
    event_filter = EventFilter({})

    def _raise(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(df, "eval", _raise)

    with pytest.raises(InvalidQueryError):
        event_filter.apply_filter(df, query="close > open")


def test_apply_filter_invalid_query_mask(monkeypatch):
    """非布林 mask 應拋出 InvalidQueryError。"""
    df = pd.DataFrame({"close": [1.0, 2.0], "open": [1.0, 1.0]})
    event_filter = EventFilter({})

    def _bad_mask(*_args, **_kwargs):
        return pd.Series([1, 2])

    monkeypatch.setattr(df, "eval", _bad_mask)

    with pytest.raises(InvalidQueryError):
        event_filter.apply_filter(df, query="close > open")


def test_timestamps_mode_uses_index_when_no_column():
    """timestamps 分支應使用 index。"""
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0]}, index=[10, 20, 30])
    event_filter = EventFilter({"min_events": 1, "sample_size_tiers": {"low_confidence": 1}})

    filtered, info = event_filter.apply_filter(df, timestamps=[20, 30])

    assert info["mode"] == "timestamps"
    assert filtered.index.tolist() == [20, 30]


def test_check_sample_size_tiers():
    """樣本數分級與門檻回傳正確。"""
    config = {"sample_size_tiers": {"sufficient": 5, "marginal": 3, "low_confidence": 2}, "min_events": 2}
    event_filter = EventFilter(config)

    assert event_filter.check_sample_size(1, config)[0] == "insufficient"
    assert event_filter.check_sample_size(2, config)[0] == "low_confidence"
    assert event_filter.check_sample_size(3, config)[0] == "marginal"
    assert event_filter.check_sample_size(5, config)[0] == "sufficient"


def test_timestamps_mode_uses_timestamp_column():
    """timestamp 欄位分支應被使用。"""
    df = pd.DataFrame({"timestamp": [1, 2, 3], "value": [10, 20, 30]})
    event_filter = EventFilter({"min_events": 1, "sample_size_tiers": {"low_confidence": 1}})

    filtered, info = event_filter.apply_filter(df, timestamps=[2])

    assert info["mode"] == "timestamps"
    assert filtered["timestamp"].tolist() == [2]


def test_validate_query_length_limit():
    """過長 query 應被拒絕。"""
    df = pd.DataFrame({"close": [1.0, 2.0]})
    event_filter = EventFilter({})
    long_query = "a" * 501

    assert event_filter.validate_query(long_query, df.columns.tolist()) is False


def test_validate_query_rejects_dunder_column():
    """欄位名為 __* 應被拒絕。"""
    df = pd.DataFrame({"__bad": [1.0, 2.0]})
    event_filter = EventFilter({})

    assert event_filter.validate_query("__bad > 0", df.columns.tolist()) is False


def test_validate_query_allows_keywords_and_columns():
    """合法關鍵字與欄位應通過驗證。"""
    df = pd.DataFrame({"close": [1.0], "open": [1.0]})
    event_filter = EventFilter({})

    assert event_filter.validate_query("close > 0 and open > 0", df.columns.tolist()) is True


def test_validate_query_allows_uppercase_keywords_and_columns():
    """大寫關鍵字仍可通過驗證。"""
    df = pd.DataFrame({"close": [1.0], "volume": [1.0]})
    event_filter = EventFilter({})

    assert (
        event_filter.validate_query("close > 0 AND volume > 0", df.columns.tolist()) is True
    )


def test_validate_query_column_continue_branch():
    """欄位存在時應走 columns 分支。"""
    event_filter = EventFilter({})

    assert event_filter.validate_query("price > 0", ["price"]) is True


def test_validate_query_columns_contains_called():
    """columns __contains__ 分支應被使用。"""
    class _Columns(list):
        def __init__(self, *args):
            super().__init__(*args)
            self.contains_calls: list[str] = []

        def __contains__(self, item):
            self.contains_calls.append(item)
            return super().__contains__(item)

    columns = _Columns(["price"])
    event_filter = EventFilter({})

    assert event_filter.validate_query("price > 0", columns) is True
    assert "price" in columns.contains_calls


def test_validate_query_columns_always_true_branch():
    """columns 永遠回 True 時應走 continue 分支。"""
    class _ColumnsAlwaysTrue:
        def __contains__(self, _item):
            return True

    event_filter = EventFilter({})
    assert event_filter.validate_query("price > 0", _ColumnsAlwaysTrue()) is True
