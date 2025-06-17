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
                    'prior_volatility': float(case.get('prior_volatility', 0)),
                    'prior_range': float(case.get('prior_range', 0)),
                    'prior_abs_change_sum': float(case.get('prior_abs_change_sum', 0)),
                    'future72_max_drawdown': float(case.get('future_max_drawdown', 0)),
                    'future24_close': float(case.get('future24_close', 0)),
                    'future24_low': float(case.get('future24_low', 0)),
                    'signal_type': signal_type,
                    'base_std': float(base_std)
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
            data = self._add_calculated_columns(data)

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
    
    def _add_calculated_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        #添加計算列，如漲幅、未來回報等#
        try:
            # 創建數據副本
            df = data.copy()
            
            # 計算當前K線漲幅 (close/previous_close - 1)
            df['price_change'] = df['close'].pct_change()
            self.logger.debug(f"price_change NaN數量: {df['price_change'].isna().sum()}")

            # 計算未來1根K線的收盤價回報
            df['future1_close_return'] = (df['close'].shift(-1)-df['close']) / df['close']
            
            # 計算未來2根K線的收盤價回報
            df['future2_close_return'] = (df['close'].shift(-2)-df['close']) / df['close']
            
            # 計算未來4根K線的收盤價回報
            df['future4_close_return'] = (df['close'].shift(-4)-df['close']) / df['close']
            
            # 計算未來6根K線的收盤價回報
            df['future6_close_return'] = (df['close'].shift(-6)-df['close']) / df['close']
            
            # 未來24小時價格（假設是未來6根4小時K線）
            df['future24_close'] = df['close'].shift(-2)
            df['future24_low'] = df.iloc[:, df.columns.get_loc('low')].rolling(window=2, min_periods=1).min().shift(-2)

            # 計算前期波動性 (前N根K線的價格變化標準差)
            lookback_periods = 6  # 前6根K線（如果是12小時K線，相當於3天）

            # 計算前N根K線的價格變動百分比的標準差
            df['prior_volatility'] = df['price_change'].rolling(window=lookback_periods).std()
            self.logger.debug(f"prior_volatility NaN數量: {df['prior_volatility'].isna().sum()}")
            
            # 計算前N根K線的價格變動範圍（最高價/最低價 - 1）
            df['prior_range'] = df['high'].rolling(window=lookback_periods).max() / df['low'].rolling(window=lookback_periods).min() - 1
            
            # 計算前N根K線的絕對價格變化總和
            df['prior_abs_change_sum'] = df['price_change'].abs().rolling(window=lookback_periods).sum()
            
            # 計算未來K線中的最大回報和最大回撤
            lookahead = 6  # 向前看的K線數
            
            # 初始化列
            df['future_max_return'] = np.nan
            df['future_max_drawdown'] = np.nan
            
            # 逐行計算
            for i in range(len(df) - lookahead):
                current_close = df['close'].iloc[i]
                future_slice = df.iloc[i+1:i+lookahead+1]
                
                # 最大回報: 未來最高價/當前收盤價 - 1
                max_high = future_slice['high'].max()
                max_return = max_high / current_close - 1
                df.loc[df.index[i], 'future_max_return'] = max_return
                
                # 最大回撤: 未來最低價/當前收盤價 - 1
                min_low = future_slice['low'].min()
                max_drawdown = min_low / current_close - 1
                df.loc[df.index[i], 'future_max_drawdown'] = max_drawdown
            
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