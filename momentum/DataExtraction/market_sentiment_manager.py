import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import os
import sys

# 添加父目錄到路徑以便導入
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from crypto_sentiment_collector import CryptoSentimentCollector

# 設置日誌
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketSentimentManager:
    """市場情緒管理器 - 提供快取和按需更新功能"""
    
    def __init__(self, cache_dir="market_data"):
        """初始化管理器"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 快取檔案路徑
        self.daily_cache_path = self.cache_dir / "fear_greed_daily_cache.csv"
        self.weekly_cache_path = self.cache_dir / "fear_greed_weekly_cache.csv"
        self.phases_cache_path = self.cache_dir / "market_phases_cache.json"
        self.metadata_path = self.cache_dir / "cache_metadata.json"
        
        # 初始化採集器
        self.collector = CryptoSentimentCollector(output_dir=cache_dir)
        
        # 載入快取元數據
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict[str, Any]:
        """載入快取元數據"""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                logger.info(f"載入快取元數據: 最後更新 {metadata.get('last_update', 'N/A')}")
                return metadata
            except Exception as e:
                logger.warning(f"載入元數據失敗: {str(e)}")
        
        # 預設元數據
        return {
            'last_update': None,
            'data_start_date': None,
            'data_end_date': None,
            'total_records': 0,
            'cache_version': '1.0'
        }
    
    def _save_metadata(self):
        """保存快取元數據"""
        try:
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logger.info("快取元數據已更新")
        except Exception as e:
            logger.error(f"保存元數據失敗: {str(e)}")
    
    def _is_cache_stale(self, max_age_hours: int = 24) -> bool:
        """檢查快取是否過期"""
        if not self.metadata.get('last_update'):
            return True
            
        try:
            last_update = datetime.fromisoformat(self.metadata['last_update'])
            age_hours = (datetime.now() - last_update).total_seconds() / 3600
            is_stale = age_hours > max_age_hours
            
            if is_stale:
                logger.info(f"快取已過期 ({age_hours:.1f}小時，超過{max_age_hours}小時限制)")
            else:
                logger.info(f"快取仍然有效 ({age_hours:.1f}小時前更新)")
                
            return is_stale
        except Exception as e:
            logger.warning(f"檢查快取時間失敗: {str(e)}")
            return True
    
    def _cache_exists(self) -> bool:
        """檢查必要的快取檔案是否存在"""
        required_files = [
            self.daily_cache_path,
            self.weekly_cache_path,
            self.phases_cache_path
        ]
        
        exists = all(f.exists() for f in required_files)
        if not exists:
            missing = [f.name for f in required_files if not f.exists()]
            logger.info(f"缺少快取檔案: {missing}")
        else:
            logger.info("所有快取檔案存在")
            
        return exists
    
    def _load_cached_data(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[Dict]]:
        """從快取載入數據"""
        try:
            # 載入日級別數據
            daily_data = None
            if self.daily_cache_path.exists():
                daily_data = pd.read_csv(self.daily_cache_path, index_col='date', parse_dates=True)
                logger.info(f"載入日級別快取數據: {len(daily_data)} 筆記錄")
            
            # 載入週級別數據
            weekly_data = None
            if self.weekly_cache_path.exists():
                weekly_data = pd.read_csv(self.weekly_cache_path, index_col='week_start', parse_dates=True)
                logger.info(f"載入週級別快取數據: {len(weekly_data)} 筆記錄")
            
            # 載入市場階段數據
            phases_data = None
            if self.phases_cache_path.exists():
                with open(self.phases_cache_path, 'r', encoding='utf-8') as f:
                    phases_data = json.load(f)
                logger.info(f"載入市場階段快取數據: {len(phases_data)} 個階段")
            
            return daily_data, weekly_data, phases_data
            
        except Exception as e:
            logger.error(f"載入快取數據失敗: {str(e)}")
            return None, None, None
    
    def _save_to_cache(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame, phases_data: Dict):
        """將數據保存到快取"""
        try:
            # 保存日級別數據
            daily_data.to_csv(self.daily_cache_path)
            logger.info(f"日級別數據已快取: {len(daily_data)} 筆記錄")
            
            # 保存週級別數據
            weekly_data.to_csv(self.weekly_cache_path)
            logger.info(f"週級別數據已快取: {len(weekly_data)} 筆記錄")
            
            # 保存市場階段數據
            with open(self.phases_cache_path, 'w', encoding='utf-8') as f:
                json.dump(phases_data, f, indent=2, ensure_ascii=False)
            logger.info(f"市場階段數據已快取: {len(phases_data)} 個階段")
            
            # 更新元數據
            self.metadata.update({
                'last_update': datetime.now().isoformat(),
                'data_start_date': daily_data.index.min().strftime('%Y-%m-%d'),
                'data_end_date': daily_data.index.max().strftime('%Y-%m-%d'),
                'total_records': len(daily_data)
            })
            self._save_metadata()
            
        except Exception as e:
            logger.error(f"保存快取失敗: {str(e)}")
    
    def update_data(self, force_update: bool = False) -> bool:
        """更新市場情緒數據"""
        try:
            # 檢查是否需要更新
            if not force_update and self._cache_exists() and not self._is_cache_stale():
                logger.info("快取有效，跳過更新")
                return True
            
            logger.info("開始更新市場情緒數據...")
            
            # 抓取最新數據
            daily_data = self.collector.fetch_fear_greed_index(limit=2000)
            if daily_data.empty:
                logger.error("無法獲取新數據")
                return False
            
            # 生成週級別數據
            self.collector.sentiment_data = daily_data
            weekly_data = self.collector.aggregate_to_weekly()
            
            # 生成市場階段數據
            phases_df = self.collector.identify_market_phases(weekly_data)
            
            # 轉換市場階段為字典格式
            phases_data = {}
            for _, row in phases_df.iterrows():
                phase = row['phase']
                start = row['start_date'].strftime('%Y-%m-%d')
                end = row['end_date'].strftime('%Y-%m-%d')
                
                phase_key = f"{phase}_{start.replace('-', '')}"
                phases_data[phase_key] = {
                    'start_date': start,
                    'end_date': end,
                    'description': phase
                }
            
            # 保存到快取
            self._save_to_cache(daily_data, weekly_data, phases_data)
            
            logger.info("市場情緒數據更新完成")
            return True
            
        except Exception as e:
            logger.error(f"更新數據失敗: {str(e)}")
            return False
    
    def get_market_phase(self, date: datetime) -> str:
        """獲取指定日期的市場階段"""
        try:
            # 確保數據是最新的
            if not self.update_data():
                logger.warning("無法更新數據，使用快取數據")
            
            # 載入市場階段數據
            _, _, phases_data = self._load_cached_data()
            if not phases_data:
                logger.error("無法載入市場階段數據")
                return 'UNKNOWN'
            
            # 查找匹配的市場階段
            target_date = date.date() if isinstance(date, datetime) else date
            
            for phase_key, phase_info in phases_data.items():
                start_date = datetime.strptime(phase_info['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(phase_info['end_date'], '%Y-%m-%d').date()
                
                if start_date <= target_date <= end_date:
                    phase_name = phase_info['description']
                    logger.info(f"日期 {target_date} 對應市場階段: {phase_name}")
                    return phase_name
            
            logger.warning(f"未找到日期 {target_date} 對應的市場階段")
            return 'UNKNOWN'
            
        except Exception as e:
            logger.error(f"獲取市場階段失敗: {str(e)}")
            return 'UNKNOWN'
    
    def get_current_market_phase(self) -> str:
        """獲取當前市場階段"""
        return self.get_market_phase(datetime.now())
    
    def get_market_phases_in_range(self, start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
        """獲取指定時間範圍內的所有市場階段"""
        try:
            # 確保數據是最新的
            if not self.update_data():
                logger.warning("無法更新數據，使用快取數據")
            
            # 載入市場階段數據
            _, _, phases_data = self._load_cached_data()
            if not phases_data:
                return {}
            
            # 篩選時間範圍內的階段
            target_start = start_date.date() if isinstance(start_date, datetime) else start_date
            target_end = end_date.date() if isinstance(end_date, datetime) else end_date
            
            filtered_phases = {}
            for phase_key, phase_info in phases_data.items():
                phase_start = datetime.strptime(phase_info['start_date'], '%Y-%m-%d').date()
                phase_end = datetime.strptime(phase_info['end_date'], '%Y-%m-%d').date()
                
                # 檢查是否有重疊
                if phase_start <= target_end and phase_end >= target_start:
                    filtered_phases[phase_key] = phase_info
            
            logger.info(f"時間範圍 {target_start} 到 {target_end} 包含 {len(filtered_phases)} 個市場階段")
            return filtered_phases
            
        except Exception as e:
            logger.error(f"獲取時間範圍市場階段失敗: {str(e)}")
            return {}
    
    def get_cache_info(self) -> Dict[str, Any]:
        """獲取快取資訊"""
        info = {
            'cache_exists': self._cache_exists(),
            'cache_stale': self._is_cache_stale(),
            'metadata': self.metadata.copy()
        }
        
        if self._cache_exists():
            try:
                daily_data, weekly_data, phases_data = self._load_cached_data()
                if daily_data is not None:
                    info['records_count'] = len(daily_data)
                if weekly_data is not None:
                    info['weeks_count'] = len(weekly_data)
                if phases_data is not None:
                    info['phases_count'] = len(phases_data)
            except Exception as e:
                logger.warning(f"獲取快取統計失敗: {str(e)}")
        
        return info
    
    def clear_cache(self):
        """清理所有快取"""
        try:
            cache_files = [
                self.daily_cache_path,
                self.weekly_cache_path,
                self.phases_cache_path,
                self.metadata_path
            ]
            
            for cache_file in cache_files:
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"已刪除快取檔案: {cache_file.name}")
            
            # 重置元數據
            self.metadata = {
                'last_update': None,
                'data_start_date': None,
                'data_end_date': None,
                'total_records': 0,
                'cache_version': '1.0'
            }
            
            logger.info("快取清理完成")
            
        except Exception as e:
            logger.error(f"清理快取失敗: {str(e)}")

def main():
    """測試函數"""
    manager = MarketSentimentManager()
    
    # 顯示快取資訊
    print("=== 快取資訊 ===")
    cache_info = manager.get_cache_info()
    for key, value in cache_info.items():
        print(f"{key}: {value}")
    
    # 更新數據
    print("\n=== 更新數據 ===")
    success = manager.update_data()
    print(f"更新結果: {success}")
    
    # 獲取當前市場階段
    print("\n=== 當前市場階段 ===")
    current_phase = manager.get_current_market_phase()
    print(f"當前市場階段: {current_phase}")
    
    # 獲取特定日期的市場階段
    print("\n=== 歷史市場階段 ===")
    test_date = datetime(2021, 5, 19)  # COVID崩盤後恢復期
    historical_phase = manager.get_market_phase(test_date)
    print(f"{test_date.strftime('%Y-%m-%d')} 的市場階段: {historical_phase}")
    
    # 獲取時間範圍內的市場階段
    print("\n=== 時間範圍市場階段 ===")
    range_phases = manager.get_market_phases_in_range(
        datetime(2021, 1, 1), 
        datetime(2021, 12, 31)
    )
    print(f"2021年包含 {len(range_phases)} 個市場階段")
    for phase_key, phase_info in list(range_phases.items())[:3]:  # 只顯示前3個
        print(f"  {phase_key}: {phase_info['start_date']} ~ {phase_info['end_date']}")

if __name__ == "__main__":
    main()