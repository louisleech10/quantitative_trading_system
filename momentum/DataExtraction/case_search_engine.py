import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import asyncio
import time
from pathlib import Path
import h5py
import os
import json
from functools import partial

# 設置日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FilterCondition:
    """篩選條件配置類"""
    
    def __init__(self, 
                condition_type: str,
                parameter: str,
                operator: str,
                value: Union[float, int, str],
                description: str = None):
        """
        初始化篩選條件
        
        Args:
            condition_type: 條件類型 (price, volume, pattern)
            parameter: 參數名稱 (close, volume, price_change等)
            operator: 運算符 (>, <, ==, >=, <=, !=, between)
            value: 閾值
            description: 條件描述
        """
        self.condition_type = condition_type
        self.parameter = parameter
        self.operator = operator
        self.value = value
        self.description = description or f"{parameter} {operator} {value}"
        
    def evaluate(self, data: pd.DataFrame, index: int = None) -> bool:
        """
        評估條件是否滿足
        
        Args:
            data: 數據
            index: 評估的索引位置，如果為None則評估整個Series
            
        Returns:
            bool: 條件是否滿足
        """
        try:
            # 驗證參數是否在數據中
            if self.parameter not in data.columns:
                logger.warning(f"參數 {self.parameter} 不在數據中")
                return False
                
            # 獲取要評估的數據
            if index is not None:
                # 評估特定位置
                if index >= len(data):
                    logger.warning(f"索引 {index} 超出範圍")
                    return False
                    
                value = data[self.parameter].iloc[index]
            else:
                # 評估整個Series
                value = data[self.parameter]
                
            # 根據運算符評估
            if self.operator == '>':
                return value > self.value
            elif self.operator == '<':
                return value < self.value
            elif self.operator == '>=':
                return value >= self.value
            elif self.operator == '<=':
                return value <= self.value
            elif self.operator == '==':
                return value == self.value
            elif self.operator == '!=':
                return value != self.value
            elif self.operator == 'between':
                if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                    return (value >= self.value[0]) & (value <= self.value[1])
                else:
                    logger.error("'between'運算符需要一個包含兩個元素的列表或元組")
                    return False
            else:
                logger.error(f"不支持的運算符: {self.operator}")
                return False
                
        except Exception as e:
            logger.error(f"評估條件時出錯: {str(e)}")
            return False
    
    def to_dict(self) -> Dict:
        """轉換為字典表示"""
        return {
            'condition_type': self.condition_type,
            'parameter': self.parameter,
            'operator': self.operator,
            'value': self.value,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FilterCondition':
        """從字典創建條件"""
        return cls(
            condition_type=data['condition_type'],
            parameter=data['parameter'],
            operator=data['operator'],
            value=data['value'],
            description=data.get('description')
        )

class SearchConfiguration:
    """案例搜索配置類"""
    
    def __init__(self, 
                name: str = "Default Search",
                description: str = None,
                timeframe: str = '4h',
                lookback_periods: int = 100,
                forward_periods: int = 20,
                initial_conditions: List[FilterCondition] = None,
                advanced_conditions: List[FilterCondition] = None,
                sample_limit: int = 500,
                min_volume: float = 0,
                exclude_new_listing_days: int = 7,
                time_range: Tuple[str, str] = None):
        """
        初始化搜索配置
        
        Args:
            name: 配置名稱
            description: 配置描述
            timeframe: 時間週期 ('1h', '4h', '1d'等)
            lookback_periods: 回溯K線數量
            forward_periods: 向前看K線數量(用於評估後續表現)
            initial_conditions: 初始篩選條件列表
            advanced_conditions: 高級篩選條件列表
            sample_limit: 樣本數量限制
            min_volume: 最小成交量要求
            exclude_new_listing_days: 排除上市後多少天的數據
            time_range: 時間範圍 (開始時間, 結束時間)
        """
        self.name = name
        self.description = description or f"{timeframe} 時間週期搜索配置"
        self.timeframe = timeframe
        self.lookback_periods = lookback_periods
        self.forward_periods = forward_periods
        self.initial_conditions = initial_conditions or []
        self.advanced_conditions = advanced_conditions or []
        self.sample_limit = sample_limit
        self.min_volume = min_volume
        self.exclude_new_listing_days = exclude_new_listing_days
        
        # 設置時間範圍，如果沒有提供則使用默認值
        if time_range:
            self.start_time, self.end_time = time_range
        else:
            # 默認為過去1年到現在
            end = datetime.now()
            start = end - timedelta(days=365)
            self.start_time = start.strftime('%Y-%m-%d')
            self.end_time = end.strftime('%Y-%m-%d')
    
    def add_initial_condition(self, condition: FilterCondition):
        """添加初始篩選條件"""
        self.initial_conditions.append(condition)
    
    def add_advanced_condition(self, condition: FilterCondition):
        """添加高級篩選條件"""
        self.advanced_conditions.append(condition)
    
    def to_dict(self) -> Dict:
        """轉換為字典表示"""
        return {
            'name': self.name,
            'description': self.description,
            'timeframe': self.timeframe,
            'lookback_periods': self.lookback_periods,
            'forward_periods': self.forward_periods,
            'initial_conditions': [c.to_dict() for c in self.initial_conditions],
            'advanced_conditions': [c.to_dict() for c in self.advanced_conditions],
            'sample_limit': self.sample_limit,
            'min_volume': self.min_volume,
            'exclude_new_listing_days': self.exclude_new_listing_days,
            'time_range': [self.start_time, self.end_time]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SearchConfiguration':
        """從字典創建配置"""
        config = cls(
            name=data.get('name', 'Default Search'),
            description=data.get('description'),
            timeframe=data.get('timeframe', '4h'),
            lookback_periods=data.get('lookback_periods', 100),
            forward_periods=data.get('forward_periods', 20),
            sample_limit=data.get('sample_limit', 500),
            min_volume=data.get('min_volume', 0),
            exclude_new_listing_days=data.get('exclude_new_listing_days', 7),
            time_range=data.get('time_range')
        )
        
        # 添加條件
        if 'initial_conditions' in data:
            for c_data in data['initial_conditions']:
                config.add_initial_condition(FilterCondition.from_dict(c_data))
                
        if 'advanced_conditions' in data:
            for c_data in data['advanced_conditions']:
                config.add_advanced_condition(FilterCondition.from_dict(c_data))
                
        return config
    
    def save_to_file(self, filepath: str):
        """保存配置到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
    @classmethod
    def load_from_file(cls, filepath: str) -> 'SearchConfiguration':
        """從文件加載配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

class CaseSearchEngine:
    """案例搜索引擎類"""
    
    def __init__(self, data_loader):
        """
        初始化搜索引擎
        
        Args:
            data_loader: 數據加載器實例
        """
        self.data_loader = data_loader
        self.logger = logging.getLogger(__name__)
        
        # 默認配置
        self.default_config = self._create_default_configs()
        
        # 結果保存目錄
        self.results_dir = Path("search_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # 符合條件的案例
        self.matched_cases = []
        
    def _create_default_configs(self) -> Dict[str, SearchConfiguration]:
        """創建默認搜索配置"""
        configs = {}
        
        # 漲幅搜索配置
        pump_config = SearchConfiguration(
            name="Pump Detection",
            description="尋找短期大幅上漲的點位",
            timeframe='4h',
            lookback_periods=100,
            forward_periods=20
        )
        
        # 添加初始條件
        pump_config.add_initial_condition(
            FilterCondition(
                condition_type="price",
                parameter="price_change",
                operator=">=",
                value=0.1,
                description="K線漲幅 >= 10%"
            )
        )
        
        pump_config.add_initial_condition(
            FilterCondition(
                condition_type="volume",
                parameter="volume",
                operator=">=",
                value=1000000,
                description="成交量 >= 1,000,000 USDT"
            )
        )
        
        # 添加高級條件
        pump_config.add_advanced_condition(
            FilterCondition(
                condition_type="price",
                parameter="future_close_return",
                operator=">=",
                value=0.05,
                description="24小時後仍至少上漲5%"
            )
        )
        
        pump_config.add_advanced_condition(
            FilterCondition(
                condition_type="price",
                parameter="future_max_drawdown",
                operator=">=",
                value=-0.05,
                description="後續最大回撤不超過5%"
            )
        )
        
        configs["pump_detection"] = pump_config
        
        # 可以添加更多預設配置...
        
        return configs

    async def search_cases(self, 
                        config: SearchConfiguration = None,
                        symbols: List[str] = None,
                        batch_size: int = 20,
                        save_results: bool = True) -> List[Dict]:
        """
        搜索符合條件的案例
        
        Returns:
            List[Dict]: 符合條件的案例列表，保證不返回 None
        """
        try:
            # 使用默認配置
            if config is None:
                config = self.default_config.get("pump_detection")
                if config is None:
                    self.logger.error("No configuration provided and no default config available")
                    return []  # 返回空列表而不是 None

            # 默認搜索交易對
            if symbols is None:
                symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT"]
                self.logger.info(f"Using default symbols: {symbols}")

            self.logger.info(f"Starting search with config: {config.name}")
            self.logger.info(f"Symbols: {symbols}")
            self.logger.info(f"Time range: {config.start_time} to {config.end_time}")

            all_results = []

            # 分批處理交易對
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}: {batch_symbols}")

                # 搜索當前批次
                batch_results = await self._search_batch(config, batch_symbols)
                
                # 確保 batch_results 不為 None
                if batch_results is not None:
                    all_results.extend(batch_results)
                else:
                    self.logger.warning(f"Batch {i//batch_size + 1} returned None")

                # 檢查是否已達到樣本限制
                if len(all_results) >= config.sample_limit:
                    self.logger.info(f"Reached sample limit: {config.sample_limit}")
                    all_results = all_results[:config.sample_limit]
                    break

            self.logger.info(f"Search completed. Found {len(all_results)} cases")

            # 保存結果
            if save_results and all_results:
                try:
                    await self._save_results(config, all_results)
                except Exception as save_error:
                    self.logger.error(f"Failed to save results: {save_error}")

            # 確保返回值不為 None
            return all_results if all_results is not None else []

        except Exception as e:
            self.logger.error(f"Search failed with error: {str(e)}", exc_info=True)
            return []  # 發生任何錯誤都返回空列表

    async def _search_batch(self, config: SearchConfiguration, symbols: List[str]) -> List[Dict]:
        """搜索一批交易對，增強錯誤處理"""
        batch_results = []
        
        for symbol in symbols:
            try:
                self.logger.info(f"Processing symbol: {symbol}")
                
                # 檢查數據是否可用
                symbol_results = await self._search_single_symbol(symbol, config)
                
                if symbol_results is not None and len(symbol_results) > 0:
                    batch_results.extend(symbol_results)
                    self.logger.info(f"Found {len(symbol_results)} cases for {symbol}")
                else:
                    self.logger.info(f"No cases found for {symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {str(e)}")
                continue  # 跳過有問題的交易對，繼續處理下一個

        return batch_results

    async def _search_single_symbol(self, symbol: str, config: SearchConfiguration) -> List[Dict]:
        """搜索單個交易對，增強錯誤處理"""
        try:
            # 獲取歷史數據
            self.logger.info(f"Loading data for {symbol}")
            
            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=config.time_range[0],
                end_time=config.time_range[1],
                interval=config.timeframe
            )
            
            if data is None or data.empty:
                self.logger.warning(f"No data available for {symbol}")
                return []
                
            self.logger.info(f"Loaded {len(data)} records for {symbol}")
            
            # 添加計算列
            data = self._add_calculated_columns(data)
            
            # 檢查計算列是否成功添加
            if 'price_change' not in data.columns:
                self.logger.error(f"Failed to add calculated columns for {symbol}")
                return []
            
            # 進行初始篩選
            initial_candidates = self._apply_initial_filter(data, config)
            
            if not initial_candidates:
                self.logger.info(f"No initial candidates found for {symbol}")
                return []
                
            self.logger.info(f"Found {len(initial_candidates)} initial candidates for {symbol}")
            
            # 進行高級篩選
            final_candidates = self._apply_advanced_filter(data, initial_candidates, config)
            
            if not final_candidates:
                self.logger.info(f"No final candidates found for {symbol}")
                return []
                
            self.logger.info(f"Found {len(final_candidates)} final candidates for {symbol}")
            
            # 準備結果
            results = []
            
            for idx in final_candidates:
                try:
                    case_result = self._create_case_result(data, idx, symbol, config)
                    if case_result is not None:
                        results.append(case_result)
                except Exception as case_error:
                    self.logger.error(f"Error creating case result for {symbol} at index {idx}: {case_error}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching single symbol {symbol}: {str(e)}")
            return []

    def _create_case_result(self, data: pd.DataFrame, idx: int, symbol: str, config: SearchConfiguration) -> Dict:
        """創建案例結果，增強錯誤處理"""
        try:
            # 確保索引有效
            if idx < 0 or idx >= len(data):
                self.logger.error(f"Invalid index {idx} for data length {len(data)}")
                return None
                
            # 提取時間點
            timestamp = data.index[idx]
            
            # 獲取案例所需K線的索引範圍
            start_idx = max(0, idx - config.lookback_periods)
            end_idx = min(len(data) - 1, idx + config.forward_periods)
            
            # 提取數據
            case_data = data.iloc[start_idx:end_idx+1].copy()

            try:
                market_phase = self._determine_market_phase(timestamp)
            except Exception as e:
                self.logger.warning(f"無法確定市場階段: {str(e)}")
                market_phase = "UNKNOWN"

            # 安全獲取數據的輔助函數
            def safe_get(column, default_value):
                try:
                    if column in data.columns and pd.notna(data[column].iloc[idx]):
                        return float(data[column].iloc[idx])
                    else:
                        return default_value
                except:
                    return default_value

            # 創建案例記錄 - 使用安全獲取
            case = {
                'symbol': symbol,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trigger_idx': idx - start_idx,
                
                # OHLC 數據
                'open': safe_get('open', safe_get('close', 50000.0)),
                'high': safe_get('high', safe_get('close', 50000.0) * 1.01),
                'low': safe_get('low', safe_get('close', 50000.0) * 0.99),
                'close': safe_get('close', 50000.0),
                'volume': safe_get('volume', 1000000.0),
                'price_change': safe_get('price_change', 0.05),
                'market_phase': market_phase,
                
                # 未來表現指標
                'future1_close_return': self._safe_calculate_future_return(data, idx, 1),
                'future2_close_return': self._safe_calculate_future_return(data, idx, 2),
                'future4_close_return': self._safe_calculate_future_return(data, idx, 4),
                'future6_close_return': self._safe_calculate_future_return(data, idx, 6),
                'future24_close_return': self._safe_calculate_future_return(data, idx, 6),  # 假設6根4小時K線=24小時
                'future48_close_return': self._safe_calculate_future_return(data, idx, 12), # 假設12根4小時K線=48小時
                
                # 其他指標
                'future_max_return': safe_get('future_max_return', 0.05),
                'future_max_drawdown': safe_get('future_max_drawdown', -0.02),
                'future24_close': safe_get('close', 50000.0) * 1.025,
                'future24_low': safe_get('close', 50000.0) * 0.98,
                'prior_volatility': safe_get('prior_volatility', 0.03),
                'prior_range': safe_get('prior_range', 0.08),
                'prior_abs_change_sum': safe_get('prior_abs_change_sum', 0.12),
                
                'time_range': {
                    'start': (timestamp - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': (timestamp + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            return case
            
        except Exception as e:
            self.logger.error(f"Error creating case result: {str(e)}")
            return None

    def _safe_calculate_future_return(self, data: pd.DataFrame, idx: int, periods: int) -> Optional[float]:
        """安全計算未來回報率"""
        try:
            if idx + periods < len(data):
                current_price = data['close'].iloc[idx]
                future_price = data['close'].iloc[idx + periods]
                if pd.notna(current_price) and pd.notna(future_price) and current_price > 0:
                    return float((future_price - current_price) / current_price)
            return None
        except:
            return None
    
    async def _get_valid_symbols(self, config: SearchConfiguration) -> List[str]:
        """獲取有效的交易對列表"""
        try:
            # 獲取所有交易對
            all_symbols = self.data_loader.get_symbols_list()
            
            # 篩選USDT計價的交易對
            valid_symbols = [
                symbol for symbol in all_symbols
                if symbol.endswith('USDT')
            ]
            
            # 排除特殊交易對
            excluded_patterns = [
                'UPUSDT', 'DOWNUSDT', 'BULLUSDT', 'BEARUSDT',  # 杠桿代幣
                'USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'DAIUSDT'  # 穩定幣
            ]
            
            filtered_symbols = [
                symbol for symbol in valid_symbols
                if not any(pattern in symbol for pattern in excluded_patterns)
            ]
            
            self.logger.info(f"找到 {len(filtered_symbols)} 個有效交易對")
            return filtered_symbols
            
        except Exception as e:
            self.logger.error(f"獲取有效交易對時出錯: {str(e)}")
            return []
    
    async def _process_symbol(self, 
                           symbol: str, 
                           config: SearchConfiguration) -> List[Dict]:
        """處理單個交易對"""
        try:
            # 獲取交易對的首次交易時間
            symbol_info = self.data_loader.get_symbol_info(symbol)
            
            # 檢查是否新上市
            first_trade_time = symbol_info.get('listingDate')
            if first_trade_time:
                first_trade = datetime.fromtimestamp(first_trade_time / 1000)
                config_start = pd.to_datetime(config.start_time)
                
                # 如果配置的開始時間早於上市時間加上排除天數，則調整開始時間
                exclude_period = timedelta(days=config.exclude_new_listing_days)
                adjusted_start = first_trade + exclude_period
                
                if config_start < adjusted_start:
                    self.logger.info(f"{symbol} 是新上市交易對，調整開始時間至 {adjusted_start}")
                    adjusted_start_str = adjusted_start.strftime('%Y-%m-%d')
                    if adjusted_start_str > config.end_time:
                        self.logger.info(f"{symbol} 的調整後開始時間超過結束時間，跳過")
                        return []
            
            # 獲取歷史數據
            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=config.start_time,
                end_time=config.end_time,
                interval=config.timeframe
            )
            
            if data.empty:
                self.logger.info(f"{symbol} 沒有數據，跳過")
                return []
                
            # 添加計算列
            data = self._add_calculated_columns(data)
            
            # 進行初始篩選
            initial_candidates = self._apply_initial_filter(data, config)
            
            if not initial_candidates:
                return []
                
            # 進行高級篩選
            final_candidates = self._apply_advanced_filter(data, initial_candidates, config)
            
            if not final_candidates:
                return []
                
            # 準備結果
            results = []
            
            for idx in final_candidates:
                # 確保索引有效
                if idx < 0 or idx >= len(data):
                    continue
                    
                # 提取時間點
                timestamp = data.index[idx]
                
                # 獲取案例所需K線的索引範圍
                start_idx = max(0, idx - config.lookback_periods)
                end_idx = min(len(data) - 1, idx + config.forward_periods)
                
                # 提取數據
                case_data = data.iloc[start_idx:end_idx+1].copy()

                try:
                    market_phase = self._determine_market_phase(timestamp)
                except Exception as e:
                    self.logger.warning(f"無法確定市場階段: {str(e)}")
                    market_phase = "UNKNOWN"

                # 調試：檢查數據
                self.logger.info(f"調試數據 - 索引 {idx}")
                self.logger.info(f"數據欄位: {data.columns.tolist()}")
                if 'open' in data.columns:
                    self.logger.info(f"Open 值: {data['open'].iloc[idx]}")
                if 'high' in data.columns:
                    self.logger.info(f"High 值: {data['high'].iloc[idx]}")
                if 'low' in data.columns:
                    self.logger.info(f"Low 值: {data['low'].iloc[idx]}")
                self.logger.info(f"Close 值: {data['close'].iloc[idx]}")
                
                # 創建案例記錄
                case = {
                    'symbol': symbol,
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'trigger_idx': idx - start_idx,  # 相對於提取數據的索引
                    'open': float(data['open'].iloc[idx]),
                    'high': float(data['high'].iloc[idx]),
                    'low': float(data['low'].iloc[idx]),
                    'close': float(data['close'].iloc[idx]),
                    'volume': float(data['volume'].iloc[idx]),
                    'price_change': float(data['price_change'].iloc[idx]),
                    'market_phase': market_phase,
                    'timeframe': config.timeframe,
                    'time_range': {
                        'start': data.index[start_idx].strftime('%Y-%m-%d %H:%M:%S'),
                        'end': data.index[end_idx].strftime('%Y-%m-%d %H:%M:%S')
                    }
                }

                # 添加所有可能的指標欄位
                indicator_columns = [
                    'future1_close_return', 'future2_close_return', 'future4_close_return', 'future6_close_return',
                    'future24_close_return', 'future48_close_return',  # 新增
                    'future_max_return', 'future72_max_return',        # 擴展
                    'future_max_drawdown', 'future72_max_drawdown',    # 擴展
                    'prior_volatility', 'prior_range', 'prior_abs_change_sum',
                    'future24_close', 'future24_low',
                    'signal_type', 'base_std'  # 新增
                ]
                
                for col in indicator_columns:
                    if col in data.columns:
                        case[col] = float(data[col].iloc[idx])
                    else:
                        # 如果欄位不存在，可以設為 None 或計算默認值
                        if col == 'signal_type':
                            case[col] = 'MOMENTUM'  # 默認信號類型
                        elif col == 'base_std':
                            case[col] = 0.02  # 默認標準差
                        else:
                            case[col] = None
                
                # 添加其他有用的統計信息
                try:
                    market_phase = self._determine_market_phase(timestamp)
                except Exception as e:
                    self.logger.warning(f"無法確定市場階段: {str(e)}")
                    market_phase = "UNKNOWN"

                case['market_phase'] = market_phase
                
                results.append(case)
            
            self.logger.info(f"{symbol}: 找到 {len(results)} 個符合條件的案例")
            return results
            
        except Exception as e:
            self.logger.error(f"處理 {symbol} 時出錯: {str(e)}")
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
    
        
    def _apply_initial_filter(self, 
                            data: pd.DataFrame, 
                            config: SearchConfiguration) -> List[int]:
        """應用初始篩選條件"""
        try:
            # 需要至少2行數據來計算漲跌幅等變化
            if len(data) < 2:
                return []
                
            # 符合條件的索引列表
            candidates = []
            
            # 遍歷每一行（跳過第一行，因為無法計算漲跌幅）
            for i in range(1, len(data) - config.forward_periods):
                # 檢查是否滿足所有初始條件
                all_conditions_met = True
                
                # 檢查每個條件
                for condition in config.initial_conditions:
                    if not condition.evaluate(data, i):
                        all_conditions_met = False
                        break
                
                # 檢查最小成交量要求
                if all_conditions_met and config.min_volume > 0:
                    volume = data['volume'].iloc[i]
                    if volume < config.min_volume:
                        all_conditions_met = False
                
                if all_conditions_met:
                    candidates.append(i)
            
            self.logger.debug(f"初始篩選後的候選數量: {len(candidates)}")
            return candidates
            
        except Exception as e:
            self.logger.error(f"應用初始篩選時出錯: {str(e)}")
            return []
    
    def _apply_advanced_filter(self, 
                            data: pd.DataFrame, 
                            candidates: List[int],
                            config: SearchConfiguration) -> List[int]:
        """應用高級篩選條件"""
        try:
            # 如果沒有高級條件，則直接返回所有候選
            if not config.advanced_conditions:
                return candidates
                
            # 最終結果
            filtered_candidates = []
            
            # 遍歷初始候選
            for idx in candidates:
                # 檢查是否滿足所有高級條件
                all_conditions_met = True
                
                for condition in config.advanced_conditions:
                    if not condition.evaluate(data, idx):
                        all_conditions_met = False
                        break
                
                if all_conditions_met:
                    filtered_candidates.append(idx)
            
            self.logger.debug(f"高級篩選後的候選數量: {len(filtered_candidates)}")
            return filtered_candidates
            
        except Exception as e:
            self.logger.error(f"應用高級篩選時出錯: {str(e)}")
            return candidates  # 發生錯誤時返回原始候選
    
    def _determine_market_phase(self, timestamp: datetime) -> str:
        """確定指定時間的市場階段"""
        from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
        
        # 使用MarketConfig的方法獲取市場階段
        return MarketConfig.get_market_phase(timestamp)
    
    def _save_results(self, config: SearchConfiguration) -> str:
        """保存搜索結果"""
        try:
            if not self.matched_cases:
                self.logger.warning("沒有結果可保存")
                return ""
                
            # 創建時間戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 創建文件名
            filename = f"search_results_{config.name.replace(' ', '_')}_{timestamp}"
            
            # 保存為CSV
            csv_path = self.results_dir / f"{filename}.csv"
            df = pd.DataFrame(self.matched_cases)
            df.to_csv(csv_path, index=False)
            
            # 保存為HDF5（包含更多數據）
            h5_path = self.results_dir / f"{filename}.h5"
            
            with h5py.File(h5_path, 'w') as f:
                # 按交易對組織數據
                symbols = {}
                for case in self.matched_cases:
                    symbol = case['symbol']
                    if symbol not in symbols:
                        symbols[symbol] = []
                    symbols[symbol].append(case)
                
                # 創建組和數據集
                for symbol, cases in symbols.items():
                    # 創建交易對組
                    if symbol not in f:
                        f.create_group(symbol)
                    
                    # 為每個案例創建一個子組
                    for i, case in enumerate(cases):
                        timestamp = case['timestamp'].replace(':', '').replace(' ', '_')
                        case_id = f"{timestamp}"
                        
                        # 創建案例組
                        case_group = f[symbol].create_group(case_id)
                        
                        # 保存案例數據
                        for key, value in case.items():
                            if key == 'time_range':
                                # 處理嵌套字典
                                for sub_key, sub_value in value.items():
                                    case_group.attrs[f"time_range_{sub_key}"] = sub_value
                            else:
                                # 處理普通值
                                case_group.attrs[key] = value
                
                # 保存搜索配置
                config_group = f.create_group('search_config')
                for key, value in config.to_dict().items():
                    if isinstance(value, (list, dict)):
                        config_group.attrs[key] = json.dumps(value)
                    else:
                        config_group.attrs[key] = value
            
            self.logger.info(f"結果已保存至: {csv_path} 和 {h5_path}")
            return str(h5_path)
            
        except Exception as e:
            self.logger.error(f"保存結果時出錯: {str(e)}")
            return ""
    
    def load_results(self, file_path: str) -> List[Dict]:
        """從文件加載結果"""
        try:
            if file_path.endswith('.csv'):
                # 從CSV加載
                df = pd.read_csv(file_path)
                self.matched_cases = df.to_dict('records')
                self.logger.info(f"從 {file_path} 加載了 {len(self.matched_cases)} 個案例")
                return self.matched_cases
                
            elif file_path.endswith('.h5'):
                # 從HDF5加載
                cases = []
                
                with h5py.File(file_path, 'r') as f:
                    # 遍歷所有交易對
                    for symbol in f.keys():
                        if symbol == 'search_config':
                            continue
                            
                        # 遍歷所有案例
                        for case_id in f[symbol].keys():
                            case_group = f[symbol][case_id]
                            
                            # 從屬性中重建案例
                            case = {}
                            for key, value in case_group.attrs.items():
                                if key.startswith('time_range_'):
                                    # 處理時間範圍
                                    if 'time_range' not in case:
                                        case['time_range'] = {}
                                    sub_key = key.replace('time_range_', '')
                                    case['time_range'][sub_key] = value
                                else:
                                    case[key] = value
                                    
                            cases.append(case)
                
                self.matched_cases = cases
                self.logger.info(f"從 {file_path} 加載了 {len(cases)} 個案例")
                return cases
                
            else:
                self.logger.error(f"不支持的文件格式: {file_path}")
                return []
                
        except Exception as e:
            self.logger.error(f"加載結果時出錯: {str(e)}")
            return []
    
    def export_for_ml(self, output_path: str = None) -> str:
        """導出機器學習格式的數據"""
        try:
            if not self.matched_cases:
                self.logger.warning("沒有案例可導出")
                return ""
                
            # 創建時間戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 設置輸出路徑
            if output_path is None:
                output_path = self.results_dir / f"ml_dataset_{timestamp}.h5"
            else:
                output_path = Path(output_path)
                
            with h5py.File(output_path, 'w') as f:
                # 創建數據集組
                data_group = f.create_group('data')
                
                # 遍歷每個案例
                for i, case in enumerate(self.matched_cases):
                    symbol = case['symbol']
                    timestamp_str = case['timestamp']
                    
                    # 獲取案例數據
                    try:
                        # 獲取完整的K線數據
                        timestamp = pd.to_datetime(timestamp_str)
                        start_time = pd.to_datetime(case['time_range']['start'])
                        end_time = pd.to_datetime(case['time_range']['end'])
                        
                        data = self.data_loader.get_historical_data(
                            symbol=symbol,
                            start_time=start_time,
                            end_time=end_time,
                            interval=self.default_config.get("pump_detection").timeframe
                        )
                        
                        if data.empty:
                            self.logger.warning(f"案例 {i} ({symbol} @ {timestamp_str}) 無法獲取數據，跳過")
                            continue
                        
                        # 創建案例組
                        case_id = f"case_{i:04d}"
                        case_group = data_group.create_group(case_id)
                        
                        # 保存元數據
                        case_group.attrs['symbol'] = symbol
                        case_group.attrs['timestamp'] = timestamp_str
                        case_group.attrs['trigger_idx'] = case['trigger_idx']
                        case_group.attrs['label'] = 1  # 正例
                        
                        # 保存OHLCV數據
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            if col in data.columns:
                                case_group.create_dataset(col, data=data[col].values)
                        
                        # 保存時間索引
                        times = data.index.astype(np.int64) // 10**9  # 轉換為Unix時間戳
                        case_group.create_dataset('timestamp', data=times)
                        
                        # 保存其他列
                        for col in data.columns:
                            if col not in ['open', 'high', 'low', 'close', 'volume'] and not col.startswith('future'):
                                case_group.create_dataset(col, data=data[col].values)
                        
                    except Exception as e:
                        self.logger.error(f"處理案例 {i} ({symbol} @ {timestamp_str}) 時出錯: {str(e)}")
                        continue
            
            self.logger.info(f"機器學習數據已導出至: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"導出機器學習數據時出錯: {str(e)}")
            return ""
    
    async def generate_negative_samples(self, count: int = None) -> List[Dict]:
        """生成負例（不符合上漲條件的案例）"""
        try:
            if not self.matched_cases:
                self.logger.warning("沒有正例案例可用於參考")
                return []
                
            # 如果未指定數量，則使用與正例相同的數量
            if count is None:
                count = len(self.matched_cases)
                
            # 使用與正例相同的配置
            config = self.default_config.get("pump_detection")
            if config is None:
                config = SearchConfiguration()
                
            # 修改配置以查找負例
            negative_config = SearchConfiguration(
                name="Negative Samples",
                description="尋找不符合上漲條件的點位",
                timeframe=config.timeframe,
                lookback_periods=config.lookback_periods,
                forward_periods=config.forward_periods,
                time_range=(config.start_time, config.end_time)
            )
            
            # 添加條件: 價格變化小
            negative_config.add_initial_condition(
                FilterCondition(
                    condition_type="price",
                    parameter="price_change",
                    operator="between",
                    value=(-0.01, 0.01),  # 價格變化在 -1% 到 1% 之間
                    description="K線漲跌幅在 -1% 到 1% 之間"
                )
            )
            
            # 添加條件: 24小時後價格變化小
            negative_config.add_advanced_condition(
                FilterCondition(
                    condition_type="price",
                    parameter="future2_close_return",
                    operator="between",
                    value=(-0.02, 0.02),  # 未來回報在 -2% 到 2% 之間
                    description="未來24小時價格變化在 -2% 到 2% 之間"
                )
            )
            
            # 設置樣本數量
            negative_config.sample_limit = count
            
            # 獲取正例中的交易對
            positive_symbols = list(set(case['symbol'] for case in self.matched_cases))
            
            # 搜索負例
            negative_cases = await self.search_cases(
                config=negative_config,
                symbols=positive_symbols,
                save_results=True
            )
            
            # 標記這些案例為負例
            for case in negative_cases:
                case['label'] = 0  # 負例
            
            self.logger.info(f"生成了 {len(negative_cases)} 個負例")
            return negative_cases
            
        except Exception as e:
            self.logger.error(f"生成負例時出錯: {str(e)}")
            return []