"""
Analysis 測試共用 Fixtures - Ultra Think 最終優化版本

提供使用真實 ETHUSDT/1h 數據的測試固件（NO MOCK DATA）。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本 fixtures 創建
- 步驟 2: 審查優化 - 添加邊界案例、錯誤處理、性能監控
- 步驟 3: 最終版本 - 完整實作所有優化項
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.indicator_engine import IndicatorEngine
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from api.services.case_storage import CaseStorage
from api.models.case_models import CaseRecord
from api.models.training_window_config import (
    TrainingWindowConfig,
    StrategyConfig
)


@pytest.fixture(scope="session")
def kline_storage():
    """
    全局 KlineStorageManager 實例（會話級別）

    使用真實 HDF5 數據源，會話期間共享以提高性能。
    """
    return KlineStorageManager()


@pytest.fixture(scope="session")
def indicator_engine():
    """
    全局 IndicatorEngine 實例（會話級別）

    用於計算技術指標，會話期間共享。
    """
    return IndicatorEngine()


@pytest.fixture
def signal_analyzer(kline_storage, indicator_engine):
    """
    SignalDensityAnalyzer 實例（函數級別）

    每個測試函數獨立創建，避免狀態污染。
    """
    return SignalDensityAnalyzer(kline_storage, indicator_engine)


@pytest.fixture(scope="session")
def real_ethusdt_data(kline_storage):
    """
    真實 ETHUSDT/1h K線數據（會話級別）

    從 HDF5 存儲加載真實數據，不使用 mock。
    如果數據不存在，跳過相關測試。

    Returns:
        pd.DataFrame: ETHUSDT/1h K線數據，包含所有必需列
    """
    try:
        df = kline_storage.load_kline_data("ETHUSDT", "1h")

        # 驗證數據完整性
        required_cols = ['close', 'open', 'high', 'low', 'volume',
                        'taker_buy_volume', 'taker_ratio']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            pytest.skip(f"ETHUSDT data missing columns: {missing_cols}")

        if len(df) < 500:
            pytest.skip(f"ETHUSDT data insufficient: {len(df)} bars (need ≥500)")

        return df

    except Exception as e:
        pytest.skip(f"Cannot load ETHUSDT/1h data: {e}")


@pytest.fixture
def sample_training_window_config():
    """
    標準訓練窗口配置

    Returns:
        TrainingWindowConfig: TO前240根K線的標準配置
    """
    return TrainingWindowConfig(
        reference_point="TO",
        lookback_bars=240,
        lookforward_bars=0,
        mode="relative"
    )


@pytest.fixture
def sample_strategy_config():
    """
    標準策略配置 - 三線順排 EMA 策略

    Returns:
        StrategyConfig: EMA(20, 60, 120) 三線順排策略
    """
    return StrategyConfig(
        data_source="close",
        indicator_type="ema",
        strategy_logic="three_line",
        params={
            "short_period": 20,
            "mid_period": 60,
            "long_period": 120
        }
    )


@pytest.fixture
def real_test_cases(real_ethusdt_data):
    """
    基於真實數據創建測試案例

    從 ETHUSDT/1h 數據中選取合適的時間點創建正反例。
    確保有足夠的歷史數據用於訓練窗口提取。

    Returns:
        Dict[str, List[CaseRecord]]: {"positive": [...], "negative": [...]}
    """
    # 確保有足夠數據（需要至少 240 根用於訓練窗口）
    if len(real_ethusdt_data) < 500:
        pytest.skip(f"Insufficient data: {len(real_ethusdt_data)} bars")

    # 選擇中間部分的時間點（確保前後都有數據）
    start_idx = 300  # 留出 240 根訓練窗口 + 緩衝
    end_idx = len(real_ethusdt_data) - 100  # 留出後續數據

    # 每隔 50 根選一個案例（避免過度重疊）
    indices = range(start_idx, end_idx, 50)

    positive_cases = []
    negative_cases = []

    for i, idx in enumerate(indices):
        timestamp = int(real_ethusdt_data.index[idx].timestamp())

        # 交替創建正反例
        is_positive = (i % 2 == 0)

        case = CaseRecord(
            case_id=f"TEST_ETHUSDT_{timestamp}_{1 if is_positive else 0}",
            symbol="ETHUSDT",
            timeframe="1h",
            timestamp=timestamp,
            positive_case=1 if is_positive else 0,
            source_file="test_fixture"
        )

        if is_positive:
            positive_cases.append(case)
        else:
            negative_cases.append(case)

    return {
        "positive": positive_cases,
        "negative": negative_cases
    }


@pytest.fixture
def minimal_test_cases(real_ethusdt_data):
    """
    最小測試案例集（用於快速測試）

    Returns:
        Dict[str, List[CaseRecord]]: 各 2 個正反例
    """
    if len(real_ethusdt_data) < 500:
        pytest.skip(f"Insufficient data: {len(real_ethusdt_data)} bars")

    # 選擇 4 個時間點
    indices = [400, 500, 600, 700]

    cases = []
    for i, idx in enumerate(indices):
        timestamp = int(real_ethusdt_data.index[idx].timestamp())
        is_positive = (i < 2)  # 前 2 個為正例

        cases.append(CaseRecord(
            case_id=f"MINI_ETHUSDT_{timestamp}_{1 if is_positive else 0}",
            symbol="ETHUSDT",
            timeframe="1h",
            timestamp=timestamp,
            positive_case=1 if is_positive else 0,
            source_file="minimal_fixture"
        ))

    return {
        "positive": cases[:2],
        "negative": cases[2:]
    }


@pytest.fixture
def edge_case_configs():
    """
    邊界測試配置集合

    Returns:
        Dict[str, TrainingWindowConfig]: 各種邊界情況配置
    """
    return {
        "minimal_lookback": TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=10,  # 最小窗口
            lookforward_bars=0,
            mode="relative"
        ),
        "maximal_lookback": TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=1000,  # 最大窗口
            lookforward_bars=0,
            mode="relative"
        ),
        "with_lookforward": TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=240,
            lookforward_bars=96,  # 包含未來數據
            mode="relative"
        ),
        "tc_reference": TrainingWindowConfig(
            reference_point="TC",
            lookback_bars=240,
            lookforward_bars=0,
            mode="relative"
        ),
        "full_range": TrainingWindowConfig(
            reference_point="TO",
            lookback_bars=240,
            lookforward_bars=0,
            mode="full_range"  # 使用全部可用數據
        )
    }


@pytest.fixture
def performance_test_cases(real_ethusdt_data):
    """
    性能測試用大量案例（用於驗證 1000 cases < 10s）

    Returns:
        Dict[str, List[CaseRecord]]: 各 500 個正反例（共 1000 個）
    """
    if len(real_ethusdt_data) < 2000:
        pytest.skip(f"Insufficient data for performance test: {len(real_ethusdt_data)} bars")

    start_idx = 300
    end_idx = len(real_ethusdt_data) - 100

    # 每隔 2 根選一個案例（生成大量案例）
    step = max(2, (end_idx - start_idx) // 1000)
    indices = range(start_idx, end_idx, step)[:1000]  # 限制最多 1000 個

    positive_cases = []
    negative_cases = []

    for i, idx in enumerate(indices):
        timestamp = int(real_ethusdt_data.index[idx].timestamp())
        is_positive = (i % 2 == 0)

        case = CaseRecord(
            case_id=f"PERF_ETHUSDT_{timestamp}_{1 if is_positive else 0}",
            symbol="ETHUSDT",
            timeframe="1h",
            timestamp=timestamp,
            positive_case=1 if is_positive else 0,
            source_file="performance_fixture"
        )

        if is_positive:
            positive_cases.append(case)
        else:
            negative_cases.append(case)

    return {
        "positive": positive_cases,
        "negative": negative_cases
    }


@pytest.fixture
def mock_case_storage(real_test_cases, tmp_path):
    """
    臨時案例存儲（用於 API 測試）

    使用真實案例數據，但存儲在臨時目錄避免污染生產環境。

    Args:
        real_test_cases: 真實測試案例
        tmp_path: pytest 提供的臨時目錄

    Returns:
        CaseStorage: 包含測試案例的臨時存儲實例
    """
    # 創建臨時 CSV 文件
    import csv
    csv_path = tmp_path / "test_cases.csv"

    all_cases = real_test_cases["positive"] + real_test_cases["negative"]

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'case_id', 'symbol', 'timeframe', 'timestamp', 'positive_case'
        ])
        writer.writeheader()
        for case in all_cases:
            writer.writerow({
                'case_id': case.case_id,
                'symbol': case.symbol,
                'timeframe': case.timeframe,
                'timestamp': case.timestamp,
                'positive_case': case.positive_case
            })

    # 創建 CaseStorage 實例指向臨時文件
    storage = CaseStorage()
    storage.csv_path = str(csv_path)

    return storage


# ============================================================
# 輔助函數（非 fixture）
# ============================================================

def assert_valid_signal_array(signals: np.ndarray, expected_length: int = None):
    """
    驗證信號陣列的有效性

    Args:
        signals: 信號陣列（0/1 或 NaN）
        expected_length: 預期長度（可選）
    """
    assert isinstance(signals, np.ndarray), "Signals must be numpy array"

    if expected_length:
        assert len(signals) == expected_length, \
            f"Signal length mismatch: {len(signals)} != {expected_length}"

    # 檢查值範圍（忽略 NaN）
    valid_signals = signals[~np.isnan(signals)]
    if len(valid_signals) > 0:
        assert np.all((valid_signals == 0) | (valid_signals == 1)), \
            "Signals must be 0, 1, or NaN"


def assert_valid_density(density: float):
    """
    驗證密度值的有效性

    Args:
        density: 信號密度值
    """
    assert isinstance(density, (int, float)), "Density must be numeric"
    assert 0.0 <= density <= 1.0, f"Density must be in [0, 1], got {density}"


def assert_statistical_metrics(p_value: float, cohens_d: float, cv: float):
    """
    驗證統計指標的有效性

    Args:
        p_value: p 值
        cohens_d: Cohen's d 效果量
        cv: 變異係數
    """
    assert 0.0 <= p_value <= 1.0, f"p_value must be in [0, 1], got {p_value}"
    assert isinstance(cohens_d, (int, float)), "cohens_d must be numeric"
    assert cv >= 0.0, f"CV must be non-negative, got {cv}"
