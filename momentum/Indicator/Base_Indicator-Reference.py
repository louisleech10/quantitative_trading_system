from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from datetime import datetime

@dataclass
class IndicatorParams:
    """指標參數配置基類"""
    lookback: int = 100  # 回溯周期
    
    def validate(self) -> None:
        """驗證參數有效性"""
        if self.lookback <= 0:
            raise ValueError("回溯周期必須大於0")
    
    def to_dict(self) -> Dict:
        """轉換參數為字典格式"""
        return {
            'lookback': self.lookback
        }

class BaseIndicator(ABC):
    """指標基礎類"""
    
    def __init__(self, params: IndicatorParams):
        self.params = params
        self.params.validate()  # 驗證參數
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self._calculation_time = None
        self._last_error = None

        # 確保有控制台處理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
        
    def validate_data(self, data: pd.DataFrame) -> None:
        """驗證輸入數據的完整性和有效性
        
        Args:
            data: 輸入的DataFrame
            
        Raises:
            ValueError: 當數據不符合要求時
        """
        # 基本數據檢查
        if data.empty:
            raise ValueError("輸入數據為空")
            
        # 檢查必要的列
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        missing_columns = required_columns - set(data.columns)
        if missing_columns:
            raise ValueError(f"數據缺少必要列: {missing_columns}")
            
        # 檢查數據類型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if not np.issubdtype(data[col].dtype, np.number):
                raise ValueError(f"列 {col} 必須是數值型")
                
        # 檢查數據範圍
        if data['high'].min() < data['low'].min():
            raise ValueError("最高價不能低於最低價")
        if (data['volume'] < 0).any():
            raise ValueError("成交量不能為負")
            
        # 檢查時間序列
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("數據索引必須是時間類型")
            
        # 檢查數據量是否足夠
        if len(data) < self.params.lookback:
            raise ValueError(f"數據量不足，需要至少 {self.params.lookback} 根K線")

    def calculate_volume_ratios(self, data: pd.DataFrame) -> pd.Series:
        """計算成交量相關比率
        
        Args:
            data: 包含volume和taker_buy_base_asset_volume的DataFrame
            
        Returns:
            pd.Series: 計算得到的比率序列
        """
        try:
            # 計算taker買入比率
            if 'taker_buy_base_asset_volume' in data.columns:
                taker_ratio = data['taker_buy_base_asset_volume'] / data['volume']
                # 處理無效值
                taker_ratio = np.clip(taker_ratio.fillna(0), 0, 1)
            else:
                self.logger.warning("無法計算taker比率：缺少必要數據")
                taker_ratio = pd.Series(0, index=data.index)
                
            return taker_ratio
            
        except Exception as e:
            self.logger.error(f"計算成交量比率時出錯: {str(e)}")
            raise

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """計算指標值
        
        Args:
            data: 包含OHLCV數據的DataFrame
            
        Returns:
            Dict[str, pd.Series]: 指標計算結果
        """
        pass
        
    @abstractmethod
    def get_signal_names(self) -> List[str]:
        """返回所有可能的信號名稱列表"""
        pass
        
    @abstractmethod
    def get_signal_description(self, signal_name: str) -> str:
        """返回信號的描述
        
        Args:
            signal_name: 信號名稱
            
        Returns:
            str: 信號的描述文字
        """
        pass

    @abstractmethod
    def get_signal_colors(self) -> Dict[str, str]:
        """返回信號的顏色映射
        
        Returns:
            Dict[str, str]: 信號名稱到顏色的映射
        """
        pass
        
    @abstractmethod
    def analyze_pattern(self, data: pd.DataFrame, 
                       indicator_values: Dict[str, pd.Series]) -> Dict[str, Any]:
        """分析Pattern並識別信號
        
        Args:
            data: 原始OHLCV數據
            indicator_values: 計算得到的指標值
            
        Returns:
            Dict: 包含識別出的信號和分析結果
        """
        pass

    def format_output(self, results: Dict[str, pd.Series]) -> pd.DataFrame:
        """將計算結果轉換為統一格式
        
        Args:
            results: 計算得到的指標值
            
        Returns:
            pd.DataFrame: 標準格式的結果
        """
        try:
            # 將所有序列合併為DataFrame
            df = pd.DataFrame(results)
            
            # 添加計算信息
            df.attrs['indicator_type'] = self.__class__.__name__
            df.attrs['params'] = self.params.to_dict()
            df.attrs['calculation_time'] = self._calculation_time
            
            return df
            
        except Exception as e:
            self.logger.error(f"格式化輸出時出錯: {str(e)}")
            raise

    def get_error_info(self) -> Optional[str]:
        """獲取最近的錯誤信息"""
        return self._last_error

    def safe_calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """帶有錯誤處理的安全計算方法
        
        Args:
            data: 輸入數據
            
        Returns:
            Dict[str, pd.Series]: 計算結果
        """
        try:
            start_time = datetime.now()
            self.validate_data(data)
            results = self.calculate(data)

            # 檢測有效K線位置
            self._valid_starts = self._detect_valid_start(results)

            self._calculation_time = datetime.now()
            self.logger.info(f"計算完成，耗時: {self._calculation_time - start_time}")
            return results
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"計算過程出錯: {str(e)}")
            raise

    def get_performance_info(self) -> Dict[str, Any]:
        """獲取性能相關信息
        
        Returns:
            Dict: 包含計算時間等性能指標
        """
        return {
            'calculation_time': self._calculation_time,
            'indicator_type': self.__class__.__name__,
            'params': self.params.to_dict()
        }
    
    def _detect_valid_start(self, indicator_values: Dict[str, pd.Series]) -> Dict[str, int]:
        """
        檢測每個指標序列的有效起始K線
        
        Args:
            indicator_values: 指標計算結果字典
            
        Returns:
            Dict[str, int]: 每個指標序列的有效起始K線位置
        """
        valid_starts = {}
        for name, series in indicator_values.items():
            # 查找第一個有效值的位置
            #valid_mask = ~(series.isna() | series.isin([np.inf, -np.inf]))
            valid_mask = ~(pd.isna(series) | series.isin([np.inf, -np.inf]))
            if valid_mask.any():
                first_valid_idx = valid_mask.values.argmax() #0116new
                valid_starts[name] = first_valid_idx #0116new
                #valid_starts[name] = valid_mask.idxmax()
                self.logger.info(f"指標 {name} 的第一個有效值在 K{first_valid_idx}")
                self.logger.info(f"前5個值: {series.head().tolist()}")
            else:
                valid_starts[name] = 0
                self.logger.warning(f"指標 {name} 未找到有效值")
        return valid_starts
    
    def get_valid_range(self, indicator_name: str = None) -> Union[int, Dict[str, int]]:
        """
        獲取指標的有效計算起始位置
        
        Args:
            indicator_name: 指標名稱，如果為None則返回所有指標的起始位置
            
        Returns:
            如果指定indicator_name，返回該指標的起始位置
            否則返回所有指標的起始位置字典
        """
        if not hasattr(self, '_valid_starts'):
            return 0 if indicator_name else {}
            
        if indicator_name:
            return self._valid_starts.get(indicator_name, 0)
        return self._valid_starts
    
    def get_signal_valid_range(self, signal_name: str) -> int:
        """
        獲取指定信號的有效起始K線位置
        每個子類必須實作這個方法來解析自己的信號名稱
        """
        raise NotImplementedError("子類必須實作此方法")