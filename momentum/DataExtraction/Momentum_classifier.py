import logging
import pandas as pd

class MomentumClassifier:
    """動能信號分類器"""
    def __init__(self, lookback_days: int = 10):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)

    def calculate_price_changes(self, data: pd.DataFrame) -> pd.Series:
        """計算價格變化百分比的絕對值"""
        return abs((data['close'] - data['open']) / data['open'])

    def get_volatility_threshold(self, data: pd.DataFrame) -> float:
        """
        使用IQR方法清理數據並計算標準差
        
        Args:
            data: 包含OHLCV數據的DataFrame
            
        Returns:
            float: 清理後數據的標準差
        """
        try:
            # 計算每根K線的價格變化絕對值
            price_changes = self.calculate_price_changes(data)
            
            # 計算IQR
            q1 = price_changes.quantile(0.25)
            q3 = price_changes.quantile(0.75)
            iqr = q3 - q1
            
            # 定義異常值界限
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # 過濾掉異常值
            clean_changes = price_changes[
                (price_changes >= lower_bound) & 
                (price_changes <= upper_bound)
            ]
            
            # 計算標準差
            return clean_changes.std()
            
        except Exception as e:
            self.logger.error(f"計算波動閾值時出錯: {str(e)}")
            raise

    def classify_signal(self, data: pd.DataFrame, signal_idx: int) -> str:
        """
        分類信號為'initial'或'trend'
        
        Args:
            data: OHLCV數據
            signal_idx: 信號K線的索引
            
        Returns:
            str: 'initial'或'trend'
        """
        try:
            if signal_idx < 8:
                return 'few day for calculation'  # 數據不足以判斷
                
            # 獲取前10天的數據計算波動基準
            lookback_window = min(self.lookback_days * 2, signal_idx)  # 12小時K線，一天2根
            volatility_data = data.iloc[signal_idx-lookback_window:signal_idx]
            base_std = self.get_volatility_threshold(volatility_data)

            violation_count = 0
            max_violations = 3
            
            # 檢查前8根K線
            for i in range(8):
                k_idx = signal_idx - 8 + i
                change = self.calculate_price_changes(data.iloc[k_idx:k_idx+1]).iloc[0]
                
                # 根據位置設定不同的閾值倍數
                if i <= 3:  # i-8到i-4
                    threshold = 2.5 * base_std
                elif i == 4:  # i-3
                    threshold = 2.7 * base_std
                elif i == 5:  # i-2
                    threshold = 2.9 * base_std
                else:  # i-1
                    threshold = 3.0 * base_std
                
                if change > threshold:
                    violation_count += 1
                    if violation_count > max_violations:
                        return 'trend'
                    
            return 'initial'
            
        except Exception as e:
            self.logger.error(f"分類信號時出錯: {str(e)}")
            return 'trend'  # 發生錯誤時保守分類為trend