"""
功能包裝器 - 將函數式指標包裝成類並註冊

此模組提供 register_functional_indicator 函數，允許 AI Agent 以簡單的函數式風格
實作新指標，系統自動將其包裝成繼承 BaseIndicator 的類並註冊到 IndicatorEngine。

設計理念：
- AI 只需寫純函數（calculate + validate）
- 系統自動提供錯誤處理、性能監控、日誌記錄
- 保持與類裝飾器架構的兼容性

Author: Claude (Sonnet 4.5)
Date: 2025-12-04
"""

from typing import Callable, Dict, Any, Optional
import logging

from .base_indicator import BaseIndicator

logger = logging.getLogger(__name__)


def register_functional_indicator(
    name: str,
    calculate_fn: Callable,
    validate_fn: Callable,
    default_params: Dict[str, Any],
    description: str = ""
) -> Callable:
    """
    將函數式指標包裝成類並註冊到 IndicatorEngine

    此函數動態生成一個繼承 BaseIndicator 的類，自動獲得：
    - 統一的錯誤處理（BaseIndicator.safe_calculate）
    - 數據驗證（BaseIndicator.validate_data）
    - 性能監控（計算時間記錄）
    - 日誌記錄
    - 自動註冊到 IndicatorEngine

    Args:
        name: 指標名稱（如 "ema", "rsi"）
        calculate_fn: 計算函數
                     簽名：(data: pd.Series, **params) -> pd.Series
        validate_fn: 驗證函數
                    簽名：(**params) -> bool
                    應在參數無效時拋出 ValueError
        default_params: 默認參數字典（如 {"period": 14}）
        description: 指標描述（可選）

    Returns:
        Callable: 返回原始的 calculate_fn，可直接使用

    Raises:
        ValueError: 如果 name 為空或包含無效字符
        TypeError: 如果 calculate_fn 或 validate_fn 不是可調用對象

    Example:
        >>> def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        ...     # RSI 計算邏輯
        ...     return result
        >>>
        >>> def validate_rsi_params(period: int = 14) -> bool:
        ...     if not isinstance(period, int):
        ...         raise ValueError("period must be int")
        ...     return True
        >>>
        >>> register_functional_indicator(
        ...     name="rsi",
        ...     calculate_fn=calculate_rsi,
        ...     validate_fn=validate_rsi_params,
        ...     default_params={"period": 14},
        ...     description="相對強弱指標"
        ... )
        >>>
        >>> # 指標已自動註冊，可通過 IndicatorEngine 調用
        >>> engine = IndicatorEngine()
        >>> result = engine.calculate_indicator("rsi", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=14)

    Note:
        - 生成的類名為 {NAME}Indicator（如 RSIIndicator）
        - 生成的類自動繼承 BaseIndicator 的所有功能
        - 可以通過 IndicatorEngine 調用，也可以直接調用原函數
    """
    # 參數驗證
    if not name or not isinstance(name, str):
        raise ValueError(f"name must be a non-empty string, got {type(name).__name__}")

    if not name.replace("_", "").isalnum():
        raise ValueError(
            f"name must contain only alphanumeric characters and underscores, got '{name}'"
        )

    if not callable(calculate_fn):
        raise TypeError(
            f"calculate_fn must be callable, got {type(calculate_fn).__name__}"
        )

    if not callable(validate_fn):
        raise TypeError(
            f"validate_fn must be callable, got {type(validate_fn).__name__}"
        )

    if not isinstance(default_params, dict):
        raise TypeError(
            f"default_params must be dict, got {type(default_params).__name__}"
        )

    # 動態生成類
    class FunctionalIndicator(BaseIndicator):
        """
        自動生成的函數式指標包裝類

        此類由 register_functional_indicator 動態生成，
        將函數式指標包裝成繼承 BaseIndicator 的類。
        """

        # 設置 docstring
        __doc__ = description or f"{name} indicator (functional wrapper)"

        @classmethod
        def get_indicator_name(cls) -> str:
            """返回指標名稱"""
            return name

        @classmethod
        def get_default_params(cls) -> Dict[str, Any]:
            """返回默認參數（深拷貝）"""
            # 深拷貝避免修改原始字典
            import copy
            return copy.deepcopy(default_params)

        def calculate(self, data, **params):
            """
            調用原始計算函數

            此方法將調用委託給 calculate_fn，
            BaseIndicator.safe_calculate 提供錯誤處理包裝。
            """
            return calculate_fn(data, **params)

        def validate_params(self, **params):
            """
            調用原始驗證函數

            此方法將驗證委託給 validate_fn。
            """
            return validate_fn(**params)

    # 設置類名（用於日誌和調試）
    class_name = f"{name.upper()}Indicator"
    FunctionalIndicator.__name__ = class_name
    FunctionalIndicator.__qualname__ = class_name

    # 註冊到 IndicatorEngine
    # 延遲導入避免循環依賴
    from .indicator_engine import IndicatorEngine

    try:
        IndicatorEngine.register(name, FunctionalIndicator)
        logger.info(
            f"Registered functional indicator: '{name}' -> {class_name} "
            f"(calculate_fn={calculate_fn.__name__}, validate_fn={validate_fn.__name__})"
        )
    except Exception as e:
        logger.error(
            f"Failed to register functional indicator '{name}': {e}",
            exc_info=True
        )
        raise

    # 返回原函數，允許直接調用
    return calculate_fn


def unregister_functional_indicator(name: str) -> None:
    """
    取消註冊函數式指標

    Args:
        name: 指標名稱

    Example:
        >>> unregister_functional_indicator("rsi")
    """
    from .indicator_engine import IndicatorEngine

    try:
        IndicatorEngine.unregister(name)
        logger.info(f"Unregistered functional indicator: '{name}'")
    except Exception as e:
        logger.warning(f"Failed to unregister functional indicator '{name}': {e}")
