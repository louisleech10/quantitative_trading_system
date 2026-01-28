"""
Strategy Registry - 策略註冊系統

解決問題：
1. 硬編碼 if-else 策略判斷 → 動態註冊機制
2. 未來擴充策略（MACD, RSI, Bollinger Bands）無需修改核心程式碼
3. 策略參數驗證自動化
4. 支援策略組合（多策略特徵融合）

Author: AI Agent
Date: 2026-01-11
"""

from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import pandas as pd
import logging

# 嘗試匯入 api.core.logging，失敗則使用標準 logging
try:
    from api.core.logging import get_logger
    logger = get_logger(__name__)
except (ImportError, ModuleNotFoundError):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


@dataclass
class StrategyDefinition:
    """策略定義"""
    name: str  # 策略名稱（e.g., 'ema_three_line', 'macd', 'rsi'）
    description: str  # 策略描述
    required_params: List[str]  # 必要參數列表
    optional_params: Dict[str, any] = field(default_factory=dict)  # 可選參數及預設值
    extractor_func: Optional[Callable] = None  # 特徵提取函式
    validator_func: Optional[Callable] = None  # 參數驗證函式


class BaseStrategyExtractor(ABC):
    """
    策略特徵提取器基類
    
    所有新策略都應該繼承此類並實作 extract() 方法
    """
    
    @abstractmethod
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取策略特徵
        
        Args:
            df: K線數據 DataFrame
            params: 策略參數字典
            data_source: 數據源（預設 'close'）
        
        Returns:
            (features_df, feature_names): 特徵 DataFrame 和特徵名稱列表
        """
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict) -> None:
        """
        驗證參數有效性
        
        Args:
            params: 策略參數字典
        
        Raises:
            ValueError: 參數無效時
        """
        pass


class StrategyRegistry:
    """
    策略註冊表
    
    特點：
    - 動態註冊：新增策略無需修改核心程式碼
    - 自動驗證：檢查策略參數完整性
    - 策略組合：支援多策略特徵融合
    
    使用範例：
    ```python
    # 註冊新策略
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        extractor=RSIExtractor()
    )
    
    # 提取特徵
    features_df, feature_names = registry.extract_features(
        strategy_name='rsi',
        df=kline_data,
        params={'period': 14}
    )
    ```
    """
    
    _instance = None  # Singleton 實例
    
    def __new__(cls):
        """實作 Singleton 模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化註冊表（只執行一次）"""
        if self._initialized:
            return
        
        self._strategies: Dict[str, StrategyDefinition] = {}
        self._extractors: Dict[str, BaseStrategyExtractor] = {}
        self._register_default_strategies()
        self._initialized = True
    
    def _register_default_strategies(self):
        """註冊預設策略（當前系統支援的）"""
        # 延遲導入避免循環依賴
        try:
            from momentum.FeatureEngineering.indicators import EMAExtractor
            
            # EMA 三線策略
            self.register_strategy(
                name='ema_three_line',
                description='EMA 三線順勢策略',
                required_params=['ema_short', 'ema_mid', 'ema_long', 'volume_threshold'],
                extractor=EMAExtractor()
            )
            logger.info("✅ 成功註冊 EMAExtractor")
        except ImportError as e:
            logger.warning(f"無法導入 EMAExtractor: {e}")
            # 回退到只註冊定義（不提供提取器）
            self.register_strategy(
                name='ema_three_line',
                description='EMA 三線順勢策略',
                required_params=['ema_short', 'ema_mid', 'ema_long', 'volume_threshold']
            )
    
    def register_strategy(
        self,
        name: str,
        description: str,
        required_params: List[str],
        optional_params: Optional[Dict[str, any]] = None,
        extractor: Optional[BaseStrategyExtractor] = None,
        validator: Optional[Callable] = None
    ):
        """
        註冊新策略
        
        Args:
            name: 策略名稱
            description: 策略描述
            required_params: 必要參數列表
            optional_params: 可選參數及預設值
            extractor: 策略特徵提取器實例
            validator: 自訂參數驗證函式
        """
        if name in self._strategies:
            logger.warning(f"策略 '{name}' 已經註冊，將被覆蓋")
        
        self._strategies[name] = StrategyDefinition(
            name=name,
            description=description,
            required_params=required_params,
            optional_params=optional_params or {},
            validator_func=validator
        )
        
        if extractor:
            self._extractors[name] = extractor
    
    def get_strategy(self, name: str) -> Optional[StrategyDefinition]:
        """獲取策略定義"""
        return self._strategies.get(name)
    
    def is_registered(self, name: str) -> bool:
        """檢查策略是否已註冊"""
        return name in self._strategies
    
    def list_strategies(self) -> List[str]:
        """列出所有已註冊策略"""
        return list(self._strategies.keys())
    
    def extract_features(
        self,
        strategy_name: str,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        動態提取策略特徵（核心方法）
        
        Args:
            strategy_name: 策略名稱
            df: K線數據 DataFrame
            params: 策略參數
            data_source: 數據源
        
        Returns:
            (features_df, feature_names): 特徵 DataFrame 和特徵名稱列表
        
        Raises:
            ValueError: 策略未註冊或未提供提取器
        """
        if not self.is_registered(strategy_name):
            available = ', '.join(self.list_strategies())
            raise ValueError(
                f"不支持的策略類型: '{strategy_name}'\n"
                f"可用的策略: {available}\n"
                f"提示：使用 StrategyRegistry().register_strategy() 註冊新策略"
            )
        
        # 獲取提取器
        extractor = self._extractors.get(strategy_name)
        if not extractor:
            raise ValueError(
                f"策略 '{strategy_name}' 已註冊但未提供特徵提取器\n"
                f"提示：註冊時需傳入 extractor 參數"
            )
        
        # 驗證參數
        self.validate_params(strategy_name, params)
        
        # 執行提取
        logger.info(f"使用 {strategy_name} 提取器提取特徵 (data_source={data_source})")
        return extractor.extract(df, params, data_source)
    
    def validate_params(self, strategy_name: str, params: Dict) -> None:
        """
        驗證策略參數
        
        Args:
            strategy_name: 策略名稱
            params: 參數字典
        
        Raises:
            ValueError: 參數無效時
        """
        if not self.is_registered(strategy_name):
            available = ', '.join(self.list_strategies())
            raise ValueError(
                f"不支持的策略類型: '{strategy_name}'\n"
                f"可用的策略: {available}\n"
                f"提示：使用 StrategyRegistry().register_strategy() 註冊新策略"
            )
        
        definition = self.get_strategy(strategy_name)
        
        # 檢查必要參數
        missing_params = [p for p in definition.required_params if p not in params]
        if missing_params:
            raise ValueError(
                f"策略 '{strategy_name}' 缺少必要參數: {missing_params}\n"
                f"必要參數: {definition.required_params}"
            )
        
        # 填充可選參數預設值
        for param, default_value in definition.optional_params.items():
            if param not in params:
                params[param] = default_value
        
        # 自訂驗證
        if definition.validator_func:
            definition.validator_func(params)
        
        # 使用提取器的驗證方法
        if strategy_name in self._extractors:
            self._extractors[strategy_name].validate_params(params)
    
    def extract_features(
        self,
        strategy_name: str,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取策略特徵
        
        Args:
            strategy_name: 策略名稱
            df: K線數據 DataFrame
            params: 策略參數
            data_source: 數據源
        
        Returns:
            (features_df, feature_names): 特徵 DataFrame 和特徵名稱列表
        """
        # 驗證參數
        self.validate_params(strategy_name, params)
        
        # 檢查提取器是否存在
        if strategy_name not in self._extractors:
            raise NotImplementedError(
                f"策略 '{strategy_name}' 尚未實作特徵提取器\n"
                f"請使用 register_strategy() 時提供 extractor 參數"
            )
        
        # 提取特徵
        extractor = self._extractors[strategy_name]
        return extractor.extract(df, params, data_source)


# 全域實例（Singleton）
strategy_registry = StrategyRegistry()


# ==================== 擴充範例 ====================

class MACDExtractor(BaseStrategyExtractor):
    """MACD 策略特徵提取器（範例）"""
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """提取 MACD 特徵"""
        features_df = df.copy()
        feature_names = []
        
        fast = params['fast_period']
        slow = params['slow_period']
        signal = params['signal_period']
        
        # 計算 EMA
        ema_fast = features_df[data_source].ewm(span=fast, adjust=False).mean()
        ema_slow = features_df[data_source].ewm(span=slow, adjust=False).mean()
        
        # MACD 線
        features_df['macd'] = ema_fast - ema_slow
        feature_names.append('macd')
        
        # Signal 線
        features_df['macd_signal'] = features_df['macd'].ewm(span=signal, adjust=False).mean()
        feature_names.append('macd_signal')
        
        # Histogram
        features_df['macd_histogram'] = features_df['macd'] - features_df['macd_signal']
        feature_names.append('macd_histogram')
        
        # 交叉信號
        features_df['macd_cross_signal'] = (
            (features_df['macd'] > features_df['macd_signal']) & 
            (features_df['macd'].shift(1) <= features_df['macd_signal'].shift(1))
        ).astype(int)
        feature_names.append('macd_cross_signal')
        
        return features_df, feature_names
    
    def validate_params(self, params: Dict) -> None:
        """驗證 MACD 參數"""
        fast = params.get('fast_period', 0)
        slow = params.get('slow_period', 0)
        signal = params.get('signal_period', 0)
        
        if fast >= slow:
            raise ValueError(f"fast_period ({fast}) 必須小於 slow_period ({slow})")
        
        if signal <= 0:
            raise ValueError(f"signal_period ({signal}) 必須大於 0")


class RSIExtractor(BaseStrategyExtractor):
    """RSI 策略特徵提取器（範例）"""
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """提取 RSI 特徵"""
        features_df = df.copy()
        feature_names = []
        
        period = params['period']
        
        # 計算價格變化
        delta = features_df[data_source].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 計算平均漲跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 計算 RS 和 RSI
        rs = avg_gain / avg_loss
        features_df['rsi'] = 100 - (100 / (1 + rs))
        feature_names.append('rsi')
        
        # RSI 超買超賣信號
        overbought = params.get('overbought_level', 70)
        oversold = params.get('oversold_level', 30)
        
        features_df['rsi_overbought'] = (features_df['rsi'] > overbought).astype(int)
        features_df['rsi_oversold'] = (features_df['rsi'] < oversold).astype(int)
        feature_names.extend(['rsi_overbought', 'rsi_oversold'])
        
        return features_df, feature_names
    
    def validate_params(self, params: Dict) -> None:
        """驗證 RSI 參數"""
        period = params.get('period', 0)
        
        if period <= 0:
            raise ValueError(f"period ({period}) 必須大於 0")
        
        overbought = params.get('overbought_level', 70)
        oversold = params.get('oversold_level', 30)
        
        if overbought <= oversold:
            raise ValueError(
                f"overbought_level ({overbought}) 必須大於 oversold_level ({oversold})"
            )


def register_advanced_strategies():
    """註冊進階策略（未來擴充）"""
    registry = StrategyRegistry()
    
    # MACD 策略
    registry.register_strategy(
        name='macd',
        description='Moving Average Convergence Divergence',
        required_params=['fast_period', 'slow_period', 'signal_period'],
        optional_params={'overbought_level': 0, 'oversold_level': 0},
        extractor=MACDExtractor()
    )
    
    # RSI 策略
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        optional_params={'overbought_level': 70, 'oversold_level': 30},
        extractor=RSIExtractor()
    )
    
    # Bollinger Bands 策略（待實作）
    registry.register_strategy(
        name='bollinger_bands',
        description='Bollinger Bands',
        required_params=['period', 'std_dev'],
        optional_params={'use_sma': True}
    )


# 使用範例
if __name__ == '__main__':
    # 獲取註冊表
    registry = StrategyRegistry()
    
    # 列出所有策略
    print("預設策略:", registry.list_strategies())
    
    # 註冊進階策略
    register_advanced_strategies()
    print("\n註冊進階策略後:")
    print("所有策略:", registry.list_strategies())
    
    # 驗證參數
    try:
        registry.validate_params('macd', {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        })
        print("\n✅ MACD 參數驗證通過")
    except ValueError as e:
        print(f"\n❌ MACD 參數驗證失敗: {e}")
