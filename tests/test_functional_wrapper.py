"""
測試函數式指標包裝器

驗證 functional_wrapper 和 EMA 函數式版本的功能

Author: Claude (Sonnet 4.5)
Date: 2025-12-04

TESTREG b5：原為模組層腳本（print + sys.exit，pytest 收集 0 項），改寫為 pytest 函式，
保留原 Test 1–8 之全部檢查。
"""

import numpy as np
import pandas as pd
import pytest

from momentum.Indicators import (
    DataSourceEnum,  # noqa: F401  (Test 1：公開 API 可匯入)
    EMAIndicator,
    IndicatorEngine,
    register_functional_indicator,  # noqa: F401  (Test 1：公開 API 可匯入)
)
from momentum.Indicators.ema import calculate_ema, ema, validate_ema_params


def _series(n: int = 100, seed: int = 0) -> pd.Series:
    return pd.Series(np.random.default_rng(seed).uniform(100, 200, n))


def test_ema_functional_auto_registered() -> None:
    """Test 2：EMA 函數式版本自動註冊至 IndicatorEngine。"""
    engine = IndicatorEngine()
    assert "ema" in engine.list_indicators()


def test_calculate_ema_direct_call() -> None:
    """Test 3：直接呼叫 calculate_ema，長度一致且非全 NaN。"""
    data = _series()
    result = calculate_ema(data, period=20)
    assert len(result) == len(data), f"長度不匹配: {len(result)} vs {len(data)}"
    assert result.isna().sum() < len(data), "結果全是 NaN"


def test_validate_ema_params() -> None:
    """Test 4：有效參數通過；字串型別、period=1、period=300 皆拒絕。"""
    assert validate_ema_params(period=20) is True
    with pytest.raises(ValueError):
        validate_ema_params(period="20")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        validate_ema_params(period=1)
    with pytest.raises(ValueError):
        validate_ema_params(period=300)


def test_ema_convenience_function() -> None:
    """Test 5：ema 便利函數長度一致。"""
    data = _series()
    result = ema(data, period=20)
    assert len(result) == len(data)


def test_calculate_ema_insufficient_data_all_nan() -> None:
    """Test 6：資料長度不足 period 時回傳全 NaN。"""
    data = pd.Series([1, 2, 3])
    result = calculate_ema(data, period=20)
    assert len(result) == 3
    assert result.isna().all(), "期望全部為 NaN"


def test_ema_indicator_info() -> None:
    """Test 7：指標元資訊之 name 與 default_params。"""
    info = IndicatorEngine().get_indicator_info("ema")
    assert info["name"] == "ema"
    assert info["default_params"] == {"period": 20}


def test_class_and_functional_versions_both_compute() -> None:
    """Test 8：類裝飾器版本與函數式版本皆可計算同一序列。

    原腳本只印出兩版差異、任何差值皆視為通過（`ema.py` 註明刻意不用 pandas_ta，
    兩版 seeding 不同），故此處保留原檢查強度：兩版皆成功計算、長度與索引一致。
    """
    data = _series()
    result_class = EMAIndicator().calculate(data, period=20)
    result_func = calculate_ema(data, period=20)
    assert len(result_class) == len(data)
    assert len(result_func) == len(data)
    assert result_class.index.equals(result_func.index)
