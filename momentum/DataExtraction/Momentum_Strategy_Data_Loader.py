import asyncio
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import h5py
from pathlib import Path

# 匯入新的資料提供者和案例搜索引擎
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from data_loader_momentum import DataLoader
from case_search_engine import CaseSearchEngine, SearchConfiguration, FilterCondition

# 保留相容性匯入
from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
from momentum.DataExtraction.Momentum_classifier import MomentumClassifier

class MomentumDataLoader:
    """
    動能策略數據加載器
    使用新的數據提供者抽象基類和案例搜索引擎
    """
    def __init__(self, cache_dir: str = "data_cache"):
        """初始化動能數據加載器"""
        self.data_loader = DataLoader(cache_dir=cache_dir)
        self.search_engine = CaseSearchEngine(self.data_loader)
        self.logger = logging.getLogger(__name__)
        self._first_trade_cache = {}  # 緩存首次交易時間
        self.classifier = MomentumClassifier()
        
        # 配置日誌
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    async def scan_for_momentum(self, 
                             start_date: str,
                             end_date: str,
                             timeframe: str = '12h',
                             batch_size: int = 20) -> List[Dict]:
        """
        掃描所有有效交易對尋找動能信號
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            timeframe: K線時間間隔
            batch_size: 批處理大小
            
        Returns:
            List[Dict]: 動能信號列表
        """
        try:
            # 創建搜索配置
            config = SearchConfiguration(
                name="Momentum Scanner",
                description=f"尋找{timeframe}時間週期的動能信號",
                timeframe=timeframe,
                lookback_periods=100,
                forward_periods=6,  # 24小時 (假設12h時間週期)
                time_range=(start_date, end_date)
            )
            
            # 添加初始條件
            price_change_threshold = 0.10 if timeframe == '12h' else 0.15
            config.add_initial_condition(
                FilterCondition(
                    condition_type="price",
                    parameter="price_change",
                    operator=">=",
                    value=price_change_threshold,
                    description=f"K線漲幅 >= {price_change_threshold*100}%"
                )
            )
            
            # 添加成交量條件
            volume_threshold = 1000000 if timeframe == '12h' else 2000000
            config.add_initial_condition(
                FilterCondition(
                    condition_type="volume",
                    parameter="volume",
                    operator=">=",
                    value=volume_threshold,
                    description=f"成交量 >= {volume_threshold}"
                )
            )
            
            # 使用搜索引擎搜索案例
            cases = await self.search_engine.search_cases(
                config=config,
                batch_size=batch_size,
                save_results=True
            )
            
            # 轉換搜索結果為動能信號格式
            signals = self._convert_to_momentum_signals(cases, timeframe)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"掃描過程中發生錯誤: {str(e)}")
            return []

    def _convert_to_momentum_signals(self, 
                                   cases: List[Dict], 
                                   timeframe: str) -> List[Dict]:
        """轉換搜索結果為動能信號格式"""
        try:
            signals = []
            
            for case in cases:
                # 獲取原始K線數據以進行信號分類
                symbol = case['symbol']
                timestamp = pd.to_datetime(case['timestamp'])
                start_time = pd.to_datetime(case['time_range']['start'])
                
                data = self.data_loader.get_historical_data(
                    symbol=symbol,
                    start_time=start_time - timedelta(days=10),  # 多獲取一些數據用於分類
                    end_time=timestamp + timedelta(days=2),
                    interval=timeframe
                )
                
                if data.empty:
                    self.logger.warning(f"無法獲取 {symbol} 的數據用於信號分類")
                    continue
                
                # 找到觸發K線的索引
                trigger_idx = None
                for i, idx in enumerate(data.index):
                    if idx == timestamp:
                        trigger_idx = i
                        break
                
                if trigger_idx is None:
                    self.logger.warning(f"無法在數據中找到觸發時間: {timestamp}")
                    continue
                
                # 對信號進行分類
                signal_type = self.classifier.classify_signal(data, trigger_idx)
                base_std = self.classifier.get_volatility_threshold(data.iloc[trigger_idx-20:trigger_idx])
                
                # 創建信號記錄
                signal = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': float(data['open'].iloc[trigger_idx]),
                    'high': float(data['high'].iloc[trigger_idx]),
                    'low': float(data['low'].iloc[trigger_idx]),
                    'close': float(data['close'].iloc[trigger_idx]),
                    'volume': float(data['volume'].iloc[trigger_idx]),
                    'price_change': float(case.get('price_change', 0)),
                    'market_phase': case.get('market_phase', 'UNKNOWN'),
                    'timeframe': timeframe,
                    'future24_close_return': float(case.get('future2_close_return', 0)),
                    'future48_close_return': float(case.get('future4_close_return', 0)),
                    'future72_max_return': float(case.get('future_max_return', 0)),
                    'future72_max_drawdown': float(case.get('future_max_drawdown', 0)),
                    'future24_close': float(case.get('future24_close', 0)),
                    'future24_low': float(case.get('future24_low', 0))
                }
                
                signals.append(signal)
                
            self.logger.info(f"共轉換 {len(signals)} 個動能信號")
            return signals
            
        except Exception as e:
            self.logger.error(f"轉換動能信號時出錯: {str(e)}")
            return []

    def _get_first_trade_time(self, symbol: str) -> Optional[datetime]:
        """獲取交易對的首次交易時間"""
        try:
            # 檢查緩存
            if symbol in self._first_trade_cache:
                return self._first_trade_cache[symbol]

            # 使用新的數據提供者接口獲取交易對信息
            info = self.data_loader.get_symbol_info(symbol)
            
            if not info:
                self.logger.warning(f"未找到交易對信息: {symbol}")
                return None
                
            # 提取上線時間戳(毫秒)
            listing_time = info.get('listingDate')
            
            if not listing_time:
                self.logger.warning(f"未找到上線時間: {symbol}")
                return None

            # 轉換為datetime並緩存
            first_trade = datetime.fromtimestamp(listing_time / 1000)
            self._first_trade_cache[symbol] = first_trade
            
            self.logger.info(f"{symbol} 上線時間: {first_trade}")
            return first_trade

        except Exception as e:
            self.logger.error(f"獲取首次交易時間出錯: {str(e)}")
            return None
            
    def save_results(self, signals: List[Dict], filename: str) -> None:
        """將掃描結果保存為HDF5格式"""
        try:
            # 轉換為DataFrame
            df = pd.DataFrame(signals)
            df['save_time'] = pd.Timestamp.now()
            
            # 添加排序
            df = df.sort_values(['timestamp', 'symbol'])
            
            # 保存為HDF5，使用table格式以支持查詢
            df.to_hdf(
                filename,
                key='momentum_signals',
                mode='w',
                format='table',
                data_columns=['symbol', 'timestamp', 'market_phase', 'timeframe']
            )
            
            self.logger.info(f"保存了 {len(signals)} 條信號到 {filename}")
            
        except Exception as e:
            self.logger.error(f"保存結果時出錯: {str(e)}")
            raise
            
    def load_results(self, filename: str) -> pd.DataFrame:
        """從HDF5文件加載動能信號"""
        try:
            return pd.read_hdf(filename, 'momentum_signals')
        except Exception as e:
            self.logger.error(f"加載結果時出錯: {str(e)}")
            return pd.DataFrame()
    
    async def analyze_single_pair(self, 
                                symbol: str,
                                start_date: str,
                                end_date: str,
                                timeframe: str = '12h') -> List[Dict]:
        """分析單個交易對的動能信號（向後兼容）"""
        try:
            # 獲取首次交易時間
            first_trade = self._get_first_trade_time(symbol)
            if first_trade is None:
                self.logger.warning(f"無法獲取首次交易時間: {symbol}")
                return []

            # 檢查是否在新上市期間
            if (pd.Timestamp(start_date) - pd.Timestamp(first_trade)).days < 7:
                return []

            # 獲取K線數據
            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=start_date,
                end_time=end_date,
                interval=timeframe
            )

            if data.empty:
                self.logger.warning(f"沒有可用數據: {symbol}")
                return []

            # 添加計算列
            data = self._add_calculated_columns(data, timeframe)

            signals = []
            criteria = MarketConfig.CRITERIA[timeframe]

            # 分析每個時間點
            for i in range(1, len(data)-4):
                current_time = data.index[i]
                current_row = data.iloc[i]
                prev_row = data.iloc[i-1]

                next_two_bars = data.iloc[i+1:i+3]
                next_four_bars = data.iloc[i+1:i+5]

                price_change = (current_row['close'] - prev_row['close']) / prev_row['close']
                volume = current_row['volume']

                if price_change >= criteria['price_change']:
                    future_close_return = (next_two_bars['close'].iloc[-1] - current_row['close']) / current_row['close']
                    future_max_return = (next_two_bars['high'].max() - current_row['close']) / current_row['close']
                    future_max_drawdown = (next_two_bars['low'].min() - current_row['close']) / current_row['close']
                    future48_close_return = (next_four_bars['close'].iloc[-1] - current_row['close']) / current_row['close']
                    future24_close = next_two_bars['close'].iloc[-1]
                    future24_low = next_two_bars['low'].iloc[-1]
                    signal_type = self.classifier.classify_signal(data, i)
                    base_std = self.classifier.get_volatility_threshold(data.iloc[i-20:i])

                    signal = {
                        'symbol': symbol,
                        'timestamp': current_time,
                        'open': float(current_row['open']),
                        'high': float(current_row['high']),
                        'low': float(current_row['low']),
                        'close': float(current_row['close']),
                        'volume': float(volume),
                        'price_change': float(price_change),
                        'market_phase': MarketConfig.get_market_phase(current_time),
                        'timeframe': timeframe,
                        'future24_close_return': float(future_close_return),
                        'future48_close_return': float(future48_close_return),
                        'future72_max_return': float(future_max_return),
                        'future72_max_drawdown': float(future_max_drawdown),
                        'future24_close': float(future24_close),
                        'future24_low': float(future24_low),
                        'signal_type': signal_type,
                        'base_std': float(base_std)
                    }
                    signals.append(signal)
                    self.logger.info(
                        f"Found signal: {symbol} at {current_time}, "
                        f"change: {price_change:.2%}, volume: {volume:,.0f}, "
                        f"future24_close: {future_close_return:.2%}, "
                        f"future48_close: {future48_close_return:.2%}, "
                        f"future72_max: {future_max_return:.2%}, "
                        f"future72_drawdown: {future_max_drawdown:.2%}"
                    )

            return signals

        except Exception as e:
            self.logger.error(f"分析 {symbol} 時發生錯誤: {str(e)}")
            return []
    
    # 在 momentum/DataExtraction/Momentum_Strategy_Data_Loader.py 中
# 找到 _add_calculated_columns 方法（大約第380行）並完全替換為：

    def _add_calculated_columns(self, data: pd.DataFrame, timeframe: str = '12h') -> pd.DataFrame:
        """添加計算列，根據時間框架正確計算未來指標"""
        try:
            # 創建數據副本
            df = data.copy()
            
            # 時間框架到小時的映射
            timeframe_hours = {
                '1h': 1, '2h': 2, '3h': 3, '4h': 4, '6h': 6, '8h': 8, '12h': 12, 
                '1d': 24, '3d': 72, '1w': 168, '1M': 720
            }
            
            # 獲取單根K線代表的小時數
            hours_per_candle = timeframe_hours.get(timeframe, 12)  # 默認12小時
            
            # 計算不同時間段需要的K線數量
            periods_24h = max(1, 24 // hours_per_candle)    # 24小時需要的K線數
            periods_48h = max(1, 48 // hours_per_candle)    # 48小時需要的K線數
            periods_72h = max(1, 72 // hours_per_candle)    # 72小時需要的K線數
            
            self.logger.info(f"時間框架: {timeframe}, 每根K線: {hours_per_candle}小時")
            self.logger.info(f"計算週期 - 24h: {periods_24h}根, 48h: {periods_48h}根, 72h: {periods_72h}根")
            
            # 計算當前K線漲幅 (close/previous_close - 1)
            df['price_change'] = df['close'].pct_change()
            
            # === 基本未來回報計算 ===
            df['future1_close_return'] = (df['close'].shift(-1) - df['close']) / df['close']
            df['future2_close_return'] = (df['close'].shift(-2) - df['close']) / df['close']
            df['future4_close_return'] = (df['close'].shift(-4) - df['close']) / df['close']
            df['future6_close_return'] = (df['close'].shift(-6) - df['close']) / df['close']
            
            # === 時間基礎的未來回報計算 ===
            # 24小時回報
            df['future24_close_return'] = (df['close'].shift(-periods_24h) - df['close']) / df['close']
            
            # 48小時回報
            df['future48_close_return'] = (df['close'].shift(-periods_48h) - df['close']) / df['close']
            
            # 72小時回報
            df['future72_close_return'] = (df['close'].shift(-periods_72h) - df['close']) / df['close']
            
            # === 未來價格數據 ===
            df['future24_close'] = df['close'].shift(-periods_24h)
            
            # 24小時內的最低價（在指定期間內的rolling min）
            if periods_24h > 1:
                df['future24_low'] = df['low'].rolling(window=periods_24h, min_periods=1).min().shift(-periods_24h)
            else:
                df['future24_low'] = df['low'].shift(-periods_24h)
            
            
            # === 未來最大回報和最大回撤計算 ===
            # 使用72小時作為標準分析期間
            lookahead_periods = periods_72h
            
            # 初始化列
            df['future_max_return'] = np.nan
            df['future_max_drawdown'] = np.nan
            df['future72_max_return'] = np.nan
            df['future72_max_drawdown'] = np.nan
            
            # 逐行計算（向量化會更快，但這樣更清晰）
            for i in range(len(df) - lookahead_periods):
                current_close = df['close'].iloc[i]
                
                # 獲取未來72小時的數據切片
                future_slice_72h = df.iloc[i+1:i+lookahead_periods+1]
                
                if len(future_slice_72h) > 0 and current_close > 0:
                    # === 72小時最大回報和回撤 ===
                    max_high_72h = future_slice_72h['high'].max()
                    min_low_72h = future_slice_72h['low'].min()
                    
                    max_return_72h = (max_high_72h / current_close - 1) if pd.notna(max_high_72h) else np.nan
                    max_drawdown_72h = (min_low_72h / current_close - 1) if pd.notna(min_low_72h) else np.nan
                    
                    df.loc[df.index[i], 'future72_max_return'] = max_return_72h
                    df.loc[df.index[i], 'future72_max_drawdown'] = max_drawdown_72h
                    
                    # === 標準6根K線的最大回報和回撤（保持向後兼容） ===
                    standard_lookahead = min(6, len(future_slice_72h))
                    future_slice_standard = df.iloc[i+1:i+standard_lookahead+1]
                    
                    if len(future_slice_standard) > 0:
                        max_high_std = future_slice_standard['high'].max()
                        min_low_std = future_slice_standard['low'].min()
                        
                        max_return_std = (max_high_std / current_close - 1) if pd.notna(max_high_std) else np.nan
                        max_drawdown_std = (min_low_std / current_close - 1) if pd.notna(min_low_std) else np.nan
                        
                        df.loc[df.index[i], 'future_max_return'] = max_return_std
                        df.loc[df.index[i], 'future_max_drawdown'] = max_drawdown_std
            
            # === 數據質量檢查 ===
            self.logger.info(f"計算完成統計:")
            self.logger.info(f"  - price_change NaN數量: {df['price_change'].isna().sum()}")
            self.logger.info(f"  - future24_close_return NaN數量: {df['future24_close_return'].isna().sum()}")
            self.logger.info(f"  - future48_close_return NaN數量: {df['future48_close_return'].isna().sum()}")
            self.logger.info(f"  - future72_max_return NaN數量: {df['future72_max_return'].isna().sum()}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"添加計算列時出錯: {str(e)}")
            return data

    def export_data_to_csv(self, 
                         signals: List[Dict],
                         output_dir: str = "exported_data") -> str:
        """
        將信號導出為CSV文件
        
        Args:
            signals: 信號列表
            output_dir: 輸出目錄
            
        Returns:
            str: CSV文件路徑
        """
        try:
            if not signals:
                self.logger.warning("沒有信號可導出")
                return ""
                
            # 創建輸出目錄
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"momentum_signals_{timestamp}.csv"
            file_path = output_path / filename
            
            # 將信號轉換為DataFrame並保存
            df = pd.DataFrame(signals)
            df.to_csv(file_path, index=False)
            
            self.logger.info(f"信號已導出到: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"導出數據失敗: {str(e)}")
            return ""
    
    async def scan_for_momentum_with_config(self, 
                                    config: SearchConfiguration,
                                    batch_size: int = 20) -> List[Dict]:
        """
        使用自定義配置掃描市場動能信號
        
        Args:
            config: 自定義搜索配置
            batch_size: 批處理大小
            
        Returns:
            List[Dict]: 動能信號列表
        """
        try:
            # 使用搜索引擎搜索案例
            cases = await self.search_engine.search_cases(
                config=config,
                batch_size=batch_size,
                save_results=True
            )
            
            # 轉換搜索結果為動能信號格式
            signals = self._convert_to_momentum_signals(cases, config.timeframe)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"使用自定義配置掃描過程中發生錯誤: {str(e)}")
            return []
    
    def _safe_calculate_future_return(self, data: pd.DataFrame, idx: int, periods: int) -> Optional[float]:
        """安全計算未來回報率，加強錯誤檢查"""
        try:
            if idx + periods >= len(data):
                return None
                
            current_price = data['close'].iloc[idx]
            future_price = data['close'].iloc[idx + periods]
            
            # 檢查數據有效性
            if pd.isna(current_price) or pd.isna(future_price) or current_price <= 0:
                return None
                
            return float((future_price - current_price) / current_price)
            
        except Exception as e:
            self.logger.error(f"計算未來回報時出錯: {str(e)}")
            return None

    def _get_timeframe_periods(self, timeframe: str) -> dict:
        """根據時間框架獲取標準化的期間數"""
        timeframe_hours = {
            '1h': 1, '2h': 2, '3h': 3, '4h': 4, '6h': 6, '8h': 8, '12h': 12, 
            '1d': 24, '3d': 72, '1w': 168, '1M': 720
        }
        
        hours_per_candle = timeframe_hours.get(timeframe, 4)
        
        return {
            'hours_per_candle': hours_per_candle,
            'periods_24h': max(1, 24 // hours_per_candle),
            'periods_48h': max(1, 48 // hours_per_candle),
            'periods_72h': max(1, 72 // hours_per_candle),
            'periods_1w': max(1, 168 // hours_per_candle)
        }