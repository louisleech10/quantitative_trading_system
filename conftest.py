"""
Pytest configuration file

設定測試環境和 Python 路徑
"""

import sys
import importlib.util
from pathlib import Path
from api.models.training_window_config import TrainingWindowConfig

# 將專案根目錄加入 Python 路徑
project_root = Path(__file__).parent.absolute()
tests_path = project_root / "tests"

# 移除 tests 路徑，避免與專案模組命名衝突
if str(tests_path) in sys.path:
    sys.path.remove(str(tests_path))

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
else:
    sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

# 不再加入 tests 路徑，避免 momentum 命名衝突
    
print(f"[conftest.py] Python path configured: {project_root}")
print(f"[conftest.py] sys.path[0]: {sys.path[0]}")


def _patch_numpy_reload_compatibility() -> None:
    """修補 numpy 重載情境下 _NoValue sentinel 不相容問題。"""
    import numpy as np
    from numpy.core import _methods as np_methods

    if getattr(np_methods, "_qts_reload_compat_patched", False):
        return

    original_amax = np_methods._amax
    original_amin = np_methods._amin

    def _is_default_initial(value) -> bool:
        return value is np._NoValue or type(value).__name__ == "_NoValueType"

    def _is_default_where(value) -> bool:
        if value is True:
            return True
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        return False

    def _safe_amax(a, axis=None, out=None, keepdims=False, initial=np._NoValue, where=True):
        if _is_default_initial(initial) and _is_default_where(where):
            return np_methods.umr_maximum(a, axis, None, out, keepdims)
        return original_amax(a, axis=axis, out=out, keepdims=keepdims, initial=initial, where=where)

    def _safe_amin(a, axis=None, out=None, keepdims=False, initial=np._NoValue, where=True):
        if _is_default_initial(initial) and _is_default_where(where):
            return np_methods.umr_minimum(a, axis, None, out, keepdims)
        return original_amin(a, axis=axis, out=out, keepdims=keepdims, initial=initial, where=where)

    np_methods._amax = _safe_amax
    np_methods._amin = _safe_amin
    np_methods._qts_reload_compat_patched = True


def _patch_numpy_dtypes_compatibility() -> None:
    """補齊 numpy 1.26/重載情境下缺失的 np.dtypes.*DType 介面。"""
    import numpy as np

    if not hasattr(np, "dtypes"):
        return

    float32_dtype_type = type(np.dtype(np.float32))
    float64_dtype_type = type(np.dtype(np.float64))

    if not hasattr(np.dtypes, "Float32DType"):
        np.dtypes.Float32DType = float32_dtype_type
    if not hasattr(np.dtypes, "Float64DType"):
        np.dtypes.Float64DType = float64_dtype_type


_patch_numpy_reload_compatibility()
_patch_numpy_dtypes_compatibility()


import pytest


@pytest.fixture
def training_window():
    """提供通用訓練窗口配置給整合測試使用"""
    return TrainingWindowConfig(
        start_date="2024-01-01",
        end_date="2024-12-31",
        timeframe="1h"
    )


@pytest.fixture
def pipeline_id():
    """提供前端整合測試用的 pipeline_id 佔位值"""
    return "TEST_PIPELINE_ID"


def _load_simple_kline_service_class():
    module_path = project_root / "tests" / "test_kline_data_service.py"
    spec = importlib.util.spec_from_file_location("test_kline_data_service", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("無法載入 test_kline_data_service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SimpleKlineDataService


@pytest.fixture(scope="module")
def test_cache_dir(tmp_path_factory):
    """提供 kline data service 測試用的快取目錄"""
    cache_path = tmp_path_factory.mktemp("kline_data_service_cache")
    return str(cache_path)


@pytest.fixture(scope="module")
def service(test_cache_dir):
    """提供 kline data service 測試用的服務實例"""
    SimpleKlineDataService = _load_simple_kline_service_class()
    return SimpleKlineDataService(cache_dir=test_cache_dir, default_source="binance")


@pytest.fixture(scope="session")
def synthetic_training_data():
    """合成二分類訓練資料（測試獨立，不依賴外部資料來源）。"""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    n_samples = 220
    n_features = 12
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    linear = X["feature_0"] * 0.7 - X["feature_1"] * 0.3 + X["feature_2"] * 0.2
    y = (linear > np.median(linear)).astype(int).to_numpy()
    return X, y, X.columns.tolist()


@pytest.fixture(scope="session")
def trained_lightgbm(synthetic_training_data):
    """已訓練 LightGBM 模型。"""
    from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer

    X, y, feature_names = synthetic_training_data
    analyzer = LightGBMAnalyzer(params={"n_estimators": 25, "num_leaves": 15})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    return analyzer


@pytest.fixture(scope="session")
def trained_xgboost(synthetic_training_data):
    """已訓練 XGBoost 模型。"""
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

    X, y, feature_names = synthetic_training_data
    analyzer = XGBoostAnalyzer(params={"n_estimators": 25, "max_depth": 4})
    analyzer.train_model(X, y, feature_names=feature_names, cv_folds=3)
    return analyzer


@pytest.fixture
def model_config_manager():
    """ModelConfigManager 實例。"""
    from momentum.Analysis.model_config import ModelConfigManager

    return ModelConfigManager()


@pytest.fixture
def mock_prices():
    """Phase 4.1 Strategy 測試用 OHLC。"""
    import numpy as np
    import pandas as pd

    dates = pd.date_range("2025-01-01", periods=100, freq="12h")
    np.random.seed(42)
    close = 40000 + np.cumsum(np.random.randn(100) * 500)
    open_prices = close + np.random.randn(100) * 100
    highs = np.maximum(open_prices, close) + np.abs(np.random.randn(100) * 300)
    lows = np.minimum(open_prices, close) - np.abs(np.random.randn(100) * 300)

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": open_prices,
            "high": highs,
            "low": lows,
            "close": close,
        }
    )


@pytest.fixture
def mock_predicted_proba():
    """Phase 4.1 Strategy 測試用機率序列。"""
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    return pd.Series(np.random.uniform(0.3, 0.9, 100))


@pytest.fixture
def mock_atr():
    """Phase 4.1 Strategy 測試用 ATR 序列。"""
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    return pd.Series(np.random.uniform(500, 2000, 100))


@pytest.fixture
def mock_strategy_params():
    """Phase 4.1 Strategy 測試用預設參數。"""
    return {
        "entry_threshold": 0.7,
        "exit_threshold": 0.4,
        "stop_loss_atr": 2.0,
        "take_profit_ratio": 3.0,
        "position_sizing_method": "fixed",
        "position_size": 0.1,
        "kelly_fraction": 0.5,
        "max_position_size": 0.25,
        "cooldown_bars": 5,
        "trailing_stop_activation": 0.05,
    }
