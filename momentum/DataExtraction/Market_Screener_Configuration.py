from typing import Dict, List, Set, Tuple, Optional
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MarketPhase:
    """
    Defines a market phase with its start and end dates
    
    Attributes:
        start_date: Beginning of the phase
        end_date: End of the phase
        description: Description of the market phase
    """
    start_date: str
    end_date: str
    description: str

class MarketConfig:
    """
    Configuration settings for market screening
    
    This class contains all the configuration parameters needed for the market screening process,
    including market phases, target pairs, and filtering criteria.
    
    新增功能：
    - 動態市場階段管理
    - 按需數據更新
    - 快取機制
    """
    
    # 保持現有的靜態市場階段定義以確保向後兼容性
    # 注意：這些將被動態數據覆蓋，僅作為備用
    MARKET_PHASES: Dict[str, MarketPhase] = {
        'EXTREME_FEAR_20191118': MarketPhase('2019-11-18', '2019-11-24', 'EXTREME_FEAR'),
        'FEAR_20191125': MarketPhase('2019-11-25', '2019-12-08', 'FEAR'),
        'EXTREME_FEAR_20191209': MarketPhase('2019-12-09', '2019-12-22', 'EXTREME_FEAR'),
        'FEAR_20191223': MarketPhase('2019-12-23', '2020-01-12', 'FEAR'),
        'NEUTRAL_20200113': MarketPhase('2020-01-13', '2020-02-02', 'NEUTRAL'),
        'GREED_20200203': MarketPhase('2020-02-03', '2020-02-16', 'GREED'),
        'NEUTRAL_20200217': MarketPhase('2020-02-17', '2020-02-23', 'NEUTRAL'),
        'FEAR_20200224': MarketPhase('2020-02-24', '2020-03-08', 'FEAR'),
        'EXTREME_FEAR_20200309': MarketPhase('2020-03-09', '2020-04-26', 'EXTREME_FEAR'),
        # ... 其他靜態定義作為備用
    }
    
    # Target quote currencies
    TARGET_QUOTES: List[str] = ['USDT']
    
    # Patterns to exclude from analysis
    EXCLUDED_PATTERNS: Set[str] = {
        # Stablecoin pairs
        '*USDC*', '*BUSD*', '*DAI*',
        # Leveraged tokens
        '*UP/*', '*DOWN/*', '*BULL*', '*BEAR*',
        # Inverse pairs
        'USDT/*', 'FDUSD/*'
    }
    
    # Screening criteria
    CRITERIA = {
        '12h': {
            'price_change': 0.10,  # 10% change in 12 hours
            'min_volume': 1000000  # Minimum volume in USDT
        },
        '24h': {
            'price_change': 0.15,  # 15% change in 24 hours
            'min_volume': 2000000  # Minimum volume in USDT
        }
    }
    
    # 動態市場階段管理器實例（懶加載）
    _sentiment_manager = None
    
    @classmethod
    def _get_sentiment_manager(cls):
        """懶加載市場情緒管理器"""
        if cls._sentiment_manager is None:
            try:
                # 動態導入以避免循環依賴
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                from market_sentiment_manager import MarketSentimentManager
                cls._sentiment_manager = MarketSentimentManager()
                logger.info("市場情緒管理器初始化成功")
            except Exception as e:
                logger.warning(f"無法初始化市場情緒管理器: {str(e)}")
                logger.warning("將使用靜態市場階段數據")
                cls._sentiment_manager = None
        return cls._sentiment_manager
    
    @staticmethod
    def get_market_phase(timestamp: datetime) -> str:
        """
        基於恐懼貪婪指數確定指定時間的市場階段
        
        Args:
            timestamp: 要檢查的時間點
            
        Returns:
            str: 市場階段名稱 (EXTREME_FEAR, FEAR, NEUTRAL, GREED, EXTREME_GREED)
        """
        # 嘗試使用動態管理器
        sentiment_manager = MarketConfig._get_sentiment_manager()
        if sentiment_manager:
            try:
                phase = sentiment_manager.get_market_phase(timestamp)
                if phase != 'UNKNOWN':
                    return phase
                logger.warning(f"動態查詢返回UNKNOWN，將使用靜態數據查詢")
            except Exception as e:
                logger.error(f"動態市場階段查詢失敗: {str(e)}")
        
        # 備用方案：使用靜態定義
        return MarketConfig._get_static_market_phase(timestamp)
    
    @staticmethod
    def _get_static_market_phase(timestamp: datetime) -> str:
        """使用靜態定義查詢市場階段（備用方案）"""
        try:
            # 使用完整的年月日格式進行比較
            timestamp_date = timestamp.date()
            
            for phase_name, phase_data in MarketConfig.MARKET_PHASES.items():
                start = pd.to_datetime(phase_data.start_date).date()
                end = pd.to_datetime(phase_data.end_date).date()
                
                if start <= timestamp_date <= end:
                    # 提取階段基本名稱（去除日期後綴）
                    base_phase = phase_name.split('_')[0]
                    return base_phase
                    
            return 'UNKNOWN'
        except Exception as e:
            logger.error(f"靜態市場階段查詢失敗: {str(e)}")
            return 'UNKNOWN'
    
    @staticmethod
    def get_current_market_phase() -> str:
        """
        獲取當前市場階段
        
        Returns:
            str: 當前市場階段名稱
        """
        sentiment_manager = MarketConfig._get_sentiment_manager()
        if sentiment_manager:
            try:
                return sentiment_manager.get_current_market_phase()
            except Exception as e:
                logger.error(f"獲取當前市場階段失敗: {str(e)}")
        
        # 備用方案
        return MarketConfig.get_market_phase(datetime.now())
    
    @staticmethod
    def get_market_phases_in_range(start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
        """
        獲取指定時間範圍內的所有市場階段
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            Dict: 市場階段字典
        """
        sentiment_manager = MarketConfig._get_sentiment_manager()
        if sentiment_manager:
            try:
                return sentiment_manager.get_market_phases_in_range(start_date, end_date)
            except Exception as e:
                logger.error(f"獲取時間範圍市場階段失敗: {str(e)}")
        
        # 備用方案：使用靜態數據
        return MarketConfig._get_static_phases_in_range(start_date, end_date)
    
    @staticmethod
    def _get_static_phases_in_range(start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
        """使用靜態定義獲取時間範圍內的市場階段（備用方案）"""
        try:
            target_start = start_date.date()
            target_end = end_date.date()
            
            filtered_phases = {}
            for phase_key, phase_data in MarketConfig.MARKET_PHASES.items():
                phase_start = pd.to_datetime(phase_data.start_date).date()
                phase_end = pd.to_datetime(phase_data.end_date).date()
                
                # 檢查是否有重疊
                if phase_start <= target_end and phase_end >= target_start:
                    filtered_phases[phase_key] = {
                        'start_date': phase_data.start_date,
                        'end_date': phase_data.end_date,
                        'description': phase_data.description
                    }
            
            return filtered_phases
        except Exception as e:
            logger.error(f"靜態時間範圍查詢失敗: {str(e)}")
            return {}
    
    @staticmethod
    def update_market_data(force_update: bool = False) -> bool:
        """
        更新市場情緒數據
        
        Args:
            force_update: 是否強制更新
            
        Returns:
            bool: 更新是否成功
        """
        sentiment_manager = MarketConfig._get_sentiment_manager()
        if sentiment_manager:
            try:
                return sentiment_manager.update_data(force_update=force_update)
            except Exception as e:
                logger.error(f"更新市場數據失敗: {str(e)}")
                return False
        else:
            logger.warning("市場情緒管理器不可用，無法更新數據")
            return False
    
    @staticmethod
    def get_market_data_info() -> Dict:
        """
        獲取市場數據快取資訊
        
        Returns:
            Dict: 快取資訊字典
        """
        sentiment_manager = MarketConfig._get_sentiment_manager()
        if sentiment_manager:
            try:
                return sentiment_manager.get_cache_info()
            except Exception as e:
                logger.error(f"獲取市場數據資訊失敗: {str(e)}")
                return {}
        else:
            return {
                'status': 'static_mode',
                'message': '使用靜態市場階段數據'
            }
    
    @staticmethod
    def validate_pair(symbol: str) -> bool:
        """
        Validate if a trading pair should be included in analysis
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            bool: True if the pair should be included, False otherwise
        """
        # Check if pair ends with valid quote currency
        if not any(symbol.endswith(quote) for quote in MarketConfig.TARGET_QUOTES):
            return False
            
        # Check if pair matches any exclusion pattern
        from fnmatch import fnmatch
        return not any(fnmatch(symbol, pattern) for pattern in MarketConfig.EXCLUDED_PATTERNS)
    
    @staticmethod
    def is_new_listing(first_trade_time: datetime, pump_time: datetime) -> bool:
        """
        Check if a price surge happens during the new listing period
        
        Args:
            first_trade_time: First trading time of the pair
            pump_time: Time when the price surge occurs
            
        Returns:
            bool: True if the surge happens during first 7 days of listing
        """
        days_since_listing = (pump_time - first_trade_time).days
        return days_since_listing < 7  # Only first 7 days are considered new listing period

    @staticmethod
    def get_minimum_volume(timeframe: str) -> float:
        """
        Get minimum volume requirement for a given timeframe
        
        Args:
            timeframe: Time period to check ('12h' or '24h')
            
        Returns:
            float: Minimum volume requirement in USDT
        """
        return MarketConfig.CRITERIA.get(timeframe, {}).get('min_volume', 1000000)

# 向後兼容性：保持原有的模組級別函數
def get_market_phase(timestamp: datetime) -> str:
    """向後兼容的模組級別函數"""
    return MarketConfig.get_market_phase(timestamp)

def get_current_market_phase() -> str:
    """向後兼容的模組級別函數"""
    return MarketConfig.get_current_market_phase()

# 使用示例和測試函數
def main():
    """測試函數"""
    print("=== MarketConfig 動態市場階段測試 ===")
    
    # 測試數據更新
    print("\n1. 測試數據更新")
    update_success = MarketConfig.update_market_data()
    print(f"數據更新結果: {update_success}")
    
    # 測試快取資訊
    print("\n2. 測試快取資訊")
    cache_info = MarketConfig.get_market_data_info()
    for key, value in cache_info.items():
        print(f"  {key}: {value}")
    
    # 測試當前市場階段
    print("\n3. 測試當前市場階段")
    current_phase = MarketConfig.get_current_market_phase()
    print(f"當前市場階段: {current_phase}")
    
    # 測試歷史階段查詢
    print("\n4. 測試歷史階段查詢")
    test_dates = [
        datetime(2020, 3, 15),  # COVID崩盤期
        datetime(2021, 2, 10),  # 牛市高峰
        datetime(2022, 6, 15),  # 熊市底部
        datetime(2024, 11, 15), # 最近的情況
    ]
    
    for test_date in test_dates:
        phase = MarketConfig.get_market_phase(test_date)
        print(f"  {test_date.strftime('%Y-%m-%d')}: {phase}")
    
    # 測試時間範圍查詢
    print("\n5. 測試時間範圍查詢")
    range_phases = MarketConfig.get_market_phases_in_range(
        datetime(2021, 1, 1), 
        datetime(2021, 6, 30)
    )
    print(f"2021年上半年包含 {len(range_phases)} 個市場階段:")
    for i, (phase_key, phase_info) in enumerate(list(range_phases.items())[:3]):
        print(f"  {i+1}. {phase_key}: {phase_info['start_date']} ~ {phase_info['end_date']} ({phase_info['description']})")
        if i >= 2:  # 只顯示前3個
            break
    
    print("\n=== 測試完成 ===")

if __name__ == "__main__":
    main()