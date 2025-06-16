from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, List, Union
import logging
from datetime import datetime

class DataProviderBase(ABC):
    """
    數據提供者的抽象基類，定義所有市場資料提供者必須實現的標準介面。
    """
    
    def __init__(self):
        """初始化數據提供者"""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    @abstractmethod
    def get_historical_data(self, 
                          symbol: str,
                          start_time: Union[str, datetime],
                          end_time: Optional[Union[str, datetime]] = None,
                          interval: str = '1h') -> pd.DataFrame:
        """
        獲取歷史OHLCV數據的標準方法
        
        Args:
            symbol: 交易對符號
            start_time: 開始時間
            end_time: 結束時間，預設為當前時間
            interval: K線時間間隔
            
        Returns:
            pd.DataFrame: 包含OHLCV數據的DataFrame
        """
        pass
    
    @abstractmethod
    def get_symbols_list(self) -> List[str]:
        """
        獲取市場中所有可用的交易對列表
        
        Returns:
            List[str]: 可用交易對的列表
        """
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        獲取特定交易對的詳細信息
        
        Args:
            symbol: 交易對符號
            
        Returns:
            Dict: 包含交易對詳細信息的字典
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        驗證數據的有效性和完整性
        
        Args:
            data: OHLCV數據
            
        Returns:
            bool: 數據是否有效
        """
        try:
            # 檢查是否為空
            if data.empty:
                self.logger.warning("數據為空")
                return False
                
            # 檢查必要的列
            required_columns = {'open', 'high', 'low', 'close', 'volume'}
            missing_columns = required_columns - set(data.columns)
            if missing_columns:
                self.logger.warning(f"數據缺少必要列: {missing_columns}")
                return False
                
            # 檢查時間索引
            if not isinstance(data.index, pd.DatetimeIndex):
                self.logger.warning("數據索引不是時間類型")
                return False
                
            # 檢查數值列
            for col in required_columns:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    self.logger.warning(f"列 {col} 不是數值類型")
                    return False
                    
            # 數據有效性檢查
            if (data['low'] > data['high']).any():
                self.logger.warning("存在最低價高於最高價的異常數據")
                return False
                
            if (data['volume'] < 0).any():
                self.logger.warning("存在負成交量的異常數據")
                return False
                
            # 檢查數據連續性
            time_diff = pd.Series(data.index).diff()[1:]
            if time_diff.nunique() > 1:
                self.logger.warning("數據時間間隔不一致")
                # 這裡不直接返回False，因為某些情況下時間間隔可能合理地變化
                
            return True
            
        except Exception as e:
            self.logger.error(f"數據驗證時出錯: {str(e)}")
            return False
    
    def handle_request_error(self, error, retry_count=0, max_retries=3):
        """
        處理API請求錯誤
        
        Args:
            error: 捕獲的異常
            retry_count: 當前重試次數
            max_retries: 最大重試次數
            
        Returns:
            bool: 是否應該重試請求
        """
        if retry_count >= max_retries:
            self.logger.error(f"達到最大重試次數 ({max_retries}): {str(error)}")
            return False
            
        # 分析錯誤類型，決定是否重試
        if "timeout" in str(error).lower() or "connection" in str(error).lower():
            retry_delay = 2 ** retry_count  # 指數退避
            self.logger.warning(f"網絡錯誤，{retry_delay}秒後重試 ({retry_count+1}/{max_retries}): {str(error)}")
            return True
            
        if "rate limit" in str(error).lower() or "too many requests" in str(error).lower():
            retry_delay = 5 * (2 ** retry_count)  # 更長的延遲
            self.logger.warning(f"限速錯誤，{retry_delay}秒後重試 ({retry_count+1}/{max_retries}): {str(error)}")
            return True
            
        # 其他錯誤可能不適合重試
        self.logger.error(f"請求錯誤（不重試）: {str(error)}")
        return False

    def format_output(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        確保輸出數據的格式一致性
        
        Args:
            data: 原始OHLCV數據
            
        Returns:
            pd.DataFrame: 格式化後的數據
        """
        try:
            if data.empty:
                return pd.DataFrame()
                
            # 確保所有市場提供者返回的數據具有一致的格式
            result = data.copy()
            
            # 確保列名統一
            column_mapping = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            
            result = result.rename(columns=column_mapping)
            
            # 確保有必要的列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in result.columns:
                    self.logger.warning(f"輸出數據缺少 {col} 列，使用NaN填充")
                    result[col] = float('nan')
            
            # 確保數值類型一致
            for col in required_cols:
                result[col] = pd.to_numeric(result[col], errors='coerce')
                
            # 僅保留必要和常用列
            keep_cols = required_cols + ['number_of_trades', 'taker_buy_base_asset_volume', 
                                        'taker_buy_quote_asset_volume', 'quote_asset_volume']
            keep_cols = [col for col in keep_cols if col in result.columns]
            result = result[keep_cols]
            
            return result
            
        except Exception as e:
            self.logger.error(f"格式化輸出時出錯: {str(e)}")
            return data  # 發生錯誤時返回原始數據