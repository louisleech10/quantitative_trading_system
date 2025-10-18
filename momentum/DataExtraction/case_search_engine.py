import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union, Tuple, Callable, Any
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
                sample_limit: int = 999999,
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
    
    def __init__(self, data_loader, enable_parallel: bool = True, num_workers: Optional[int] = None):
        """
        初始化搜索引擎

        Args:
            data_loader: 數據加載器實例
            enable_parallel: 是否啟用並行處理（默認True，利用多核加速）
            num_workers: 並行worker數量（None=自動偵測，可手動指定以覆蓋自動偵測）
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

        # 並行處理引擎（Phase 1優化）
        self.enable_parallel = enable_parallel
        if enable_parallel:
            try:
                from momentum.DataExtraction.parallel_search_engine import ParallelSearchEngine
                self.parallel_engine = ParallelSearchEngine(
                    case_search_engine=self,
                    enable_parallel=True,
                    num_workers=num_workers  # ✅ 傳遞 num_workers 參數
                )
                self.logger.info("並行搜索引擎已啟用")
            except ImportError as e:
                self.logger.warning(f"無法導入並行引擎，退回串行模式: {e}")
                self.parallel_engine = None
                self.enable_parallel = False
        else:
            self.parallel_engine = None
            self.logger.info("並行處理已禁用，使用串行模式")
        
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

        Args:
            config: 搜索配置
            symbols: 交易對列表
            batch_size: 批次大小（並行模式下此參數被忽略）
            save_results: 是否保存結果

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

            # Phase 1優化：使用並行處理引擎（如果啟用）
            if self.enable_parallel and self.parallel_engine is not None:
                self.logger.info("使用並行處理模式")
                all_results = await self.parallel_engine.search_cases_parallel(
                    config=config,
                    symbols=symbols,
                    save_results=save_results
                )
                return all_results if all_results is not None else []

            # 串行處理模式（原有邏輯）
            self.logger.info("使用串行處理模式")
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

            self.logger.info(f"Search completed. Found {len(all_results)} cases")

            # 保存結果
            if save_results and all_results:
                try:
                    self.matched_cases = all_results
                    self._save_results(config)
                except Exception as save_error:
                    self.logger.error(f"Failed to save results: {save_error}", exc_info=True)

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
            # DEBUG: 確認此函數被調用
            self.logger.warning(f"🔍 DEBUG: _search_single_symbol 被調用 - symbol={symbol}, timeframe={config.timeframe}")

            # 獲取歷史數據
            self.logger.info(f"Loading data for {symbol}")
            
            # 修正：正確傳遞時間範圍參數
            if hasattr(config, 'time_range') and config.time_range:
                start_time, end_time = config.time_range
            else:
                start_time, end_time = config.start_time, config.end_time
                
            data = self.data_loader.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=config.timeframe
            )
            
            if data is None or data.empty:
                self.logger.warning(f"No data available for {symbol}")
                return []
                
            self.logger.info(f"Loaded {len(data)} records for {symbol}")
            
            # 添加計算列
            data = self._add_calculated_columns(data, config.timeframe)
            
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

    # 改進的數據處理邏輯 - 避免虛擬數據污染
    def _create_case_result(self, data: pd.DataFrame, idx: int, symbol: str, config: SearchConfiguration) -> Dict:
        """創建案例結果，改進的數據處理邏輯"""
        try:
            # DEBUG: 確認此函數被調用並檢查參數是否在columns中
            past_params = ['past_24hr_max_single_move', 'past_48hr_price_range', 'past_72hr_avg_bar_volatility',
                          'past_48hr_directional_movement', 'past_24hr_volume_stability']
            missing_params = [p for p in past_params if p not in data.columns]
            if missing_params:
                self.logger.error(f"🔍 DEBUG: _create_case_result - 缺少參數: {missing_params}")
            else:
                self.logger.warning(f"🔍 DEBUG: _create_case_result - 所有歷史穩定度參數都在columns中")

            # 確保索引有效
            if idx < 0 or idx >= len(data):
                self.logger.error(f"Invalid index {idx} for data length {len(data)}")
                return None
                
            # 提取時間點
            timestamp = data.index[idx]
            
            # 安全獲取數據的輔助函數 - 改進版本
            def safe_get(column, default_value=None, require_valid=True):
                try:
                    if column in data.columns and pd.notna(data[column].iloc[idx]):
                        value = data[column].iloc[idx]

                        # DEBUG: 追蹤5個歷史穩定度參數的實際值
                        if 'past_' in column:
                            self.logger.error(f"🔍 TRACE: {column} - raw_value={value}, type={type(value)}, is_nan={pd.isna(value)}")

                        # 如果是百分比字符串，轉換為數值
                        if isinstance(value, str) and value.endswith('%'):
                            return float(value[:-1]) / 100

                        final_value = float(value) if not pd.isna(value) else default_value

                        # DEBUG: 追蹤最終返回值
                        if 'past_' in column:
                            self.logger.error(f"🔍 TRACE: {column} - final_value={final_value}, returning to case dict")

                        return final_value
                    else:
                        # DEBUG: 記錄歷史穩定度參數的NaN情況
                        if 'past_' in column and column in data.columns:
                            actual_value = data[column].iloc[idx]
                            self.logger.error(f"🔍 DEBUG: {column} 值是NaN - actual_value={actual_value}, type={type(actual_value)}")

                        if require_valid and default_value is None:
                            # 如果要求有效數據但沒有，記錄警告並返回 None
                            self.logger.warning(f"Missing required data: {column} for {symbol} at {timestamp}")
                            return None
                        return default_value
                except Exception as e:
                    self.logger.debug(f"Error getting {column}: {e}")
                    return default_value

            # 檢查基礎 OHLCV 數據的完整性
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            missing_fields = []
            
            for field in required_fields:
                if safe_get(field, require_valid=True) is None:
                    missing_fields.append(field)
            
            # 如果缺少關鍵數據，直接跳過這個案例
            if missing_fields:
                self.logger.warning(f"Skipping case {symbol}@{timestamp}: missing critical data: {missing_fields}")
                return None

            # 獲取市場階段
            try:
                market_phase = self._determine_market_phase(timestamp)
            except Exception as e:
                self.logger.warning(f"無法確定市場階段: {str(e)}")
                market_phase = "UNKNOWN"

            # 創建案例記錄 - 只使用真實數據，不使用虛擬數據
            case = {
                # ===== 基本識別資訊 =====
                'symbol': symbol,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trigger_idx': idx,
                
                # ===== OHLCV 基礎數據 - 只使用真實數據 =====
                'open': safe_get('open'),
                'high': safe_get('high'),
                'low': safe_get('low'),
                'close': safe_get('close'),
                'volume': safe_get('volume'),
                'price_change': safe_get('price_change'),
                'market_phase': market_phase,
                
                # ===== 基礎觸發條件參數 =====
                'timeframe': safe_get('timeframe', config.timeframe),
                'closing_strength': safe_get('closing_strength'),
                'price_position': safe_get('price_position'),
                'volume_multiplier': safe_get('volume_multiplier'),
                'taker_buy_ratio': safe_get('taker_buy_ratio'),
                
                # ===== 未來收益參數 (1-12根K線) =====
                'future_1bar_return': safe_get('future_1bar_return'),
                'future_2bar_return': safe_get('future_2bar_return'),
                'future_3bar_return': safe_get('future_3bar_return'),
                'future_4bar_return': safe_get('future_4bar_return'),
                'future_5bar_return': safe_get('future_5bar_return'),
                'future_6bar_return': safe_get('future_6bar_return'),
                'future_7bar_return': safe_get('future_7bar_return'),
                'future_8bar_return': safe_get('future_8bar_return'),
                'future_9bar_return': safe_get('future_9bar_return'),
                'future_10bar_return': safe_get('future_10bar_return'),
                'future_11bar_return': safe_get('future_11bar_return'),
                'future_12bar_return': safe_get('future_12bar_return'),
                
                # ===== 未來回撤參數 (1-12根K線) =====
                'future_1bar_max_drawdown': safe_get('future_1bar_max_drawdown'),
                'future_2bar_max_drawdown': safe_get('future_2bar_max_drawdown'),
                'future_3bar_max_drawdown': safe_get('future_3bar_max_drawdown'),
                'future_4bar_max_drawdown': safe_get('future_4bar_max_drawdown'),
                'future_5bar_max_drawdown': safe_get('future_5bar_max_drawdown'),
                'future_6bar_max_drawdown': safe_get('future_6bar_max_drawdown'),
                'future_7bar_max_drawdown': safe_get('future_7bar_max_drawdown'),
                'future_8bar_max_drawdown': safe_get('future_8bar_max_drawdown'),
                'future_9bar_max_drawdown': safe_get('future_9bar_max_drawdown'),
                'future_10bar_max_drawdown': safe_get('future_10bar_max_drawdown'),
                'future_11bar_max_drawdown': safe_get('future_11bar_max_drawdown'),
                'future_12bar_max_drawdown': safe_get('future_12bar_max_drawdown'),
                
                # ===== 時間描述參數 =====
                'hour_of_day': safe_get('hour_of_day'),
                'day_of_week': safe_get('day_of_week'),
                
                # ===== 向後兼容的現有參數 =====
                'future1_close_return': safe_get('future1_close_return'),
                'future2_close_return': safe_get('future2_close_return'),
                'future4_close_return': safe_get('future4_close_return'),
                'future6_close_return': safe_get('future6_close_return'),
                'future24_close_return': safe_get('future24_close_return'),
                'future48_close_return': safe_get('future48_close_return'),
                'future72_close_return': safe_get('future72_close_return'),
                'future_max_return': safe_get('future_max_return'),
                'future_max_drawdown': safe_get('future_max_drawdown'),
                'future72_max_return': safe_get('future72_max_return'),
                'future72_max_drawdown': safe_get('future72_max_drawdown'),
                'future24_close': safe_get('future24_close'),
                'future24_low': safe_get('future24_low'),
                'prior_volatility': safe_get('prior_volatility'),
                'prior_range': safe_get('prior_range'),
                'prior_abs_change_sum': safe_get('prior_abs_change_sum'),

                # ===== 未來收益參數 (1-12根K線) =====
                'future_1bar_return': safe_get('future_1bar_return'),
                'future_2bar_return': safe_get('future_2bar_return'),
                'future_3bar_return': safe_get('future_3bar_return'),
                'future_4bar_return': safe_get('future_4bar_return'),
                'future_5bar_return': safe_get('future_5bar_return'),
                'future_6bar_return': safe_get('future_6bar_return'),
                'future_7bar_return': safe_get('future_7bar_return'),
                'future_8bar_return': safe_get('future_8bar_return'),
                'future_9bar_return': safe_get('future_9bar_return'),
                'future_10bar_return': safe_get('future_10bar_return'),
                'future_11bar_return': safe_get('future_11bar_return'),
                'future_12bar_return': safe_get('future_12bar_return'),

                # ===== 未來回撤參數 (1-12根K線) =====
                'future_1bar_max_drawdown': safe_get('future_1bar_max_drawdown'),
                'future_2bar_max_drawdown': safe_get('future_2bar_max_drawdown'),
                'future_3bar_max_drawdown': safe_get('future_3bar_max_drawdown'),
                'future_4bar_max_drawdown': safe_get('future_4bar_max_drawdown'),
                'future_5bar_max_drawdown': safe_get('future_5bar_max_drawdown'),
                'future_6bar_max_drawdown': safe_get('future_6bar_max_drawdown'),
                'future_7bar_max_drawdown': safe_get('future_7bar_max_drawdown'),
                'future_8bar_max_drawdown': safe_get('future_8bar_max_drawdown'),
                'future_9bar_max_drawdown': safe_get('future_9bar_max_drawdown'),
                'future_10bar_max_drawdown': safe_get('future_10bar_max_drawdown'),
                'future_11bar_max_drawdown': safe_get('future_11bar_max_drawdown'),
                'future_12bar_max_drawdown': safe_get('future_12bar_max_drawdown'),

                # ===== 時間描述參數 =====
                'hour_of_day': safe_get('hour_of_day'),
                'day_of_week': safe_get('day_of_week'),

                # ===== 歷史穩定度參數 (5個) =====
                'past_24hr_max_single_move': safe_get('past_24hr_max_single_move', default_value=0.0, require_valid=False),
                'past_48hr_price_range': safe_get('past_48hr_price_range', default_value=0.0, require_valid=False),
                'past_72hr_avg_bar_volatility': safe_get('past_72hr_avg_bar_volatility', default_value=0.0, require_valid=False),
                'past_48hr_directional_movement': safe_get('past_48hr_directional_movement', default_value=0.0, require_valid=False),
                'past_24hr_volume_stability': safe_get('past_24hr_volume_stability', default_value=0.0, require_valid=False),

                # ===== 數據品質標記 =====
                'data_quality': {
                    'has_complete_ohlcv': all(safe_get(field) is not None for field in required_fields),
                    'missing_fields': [field for field in required_fields if safe_get(field) is None],
                    'data_source': 'binance_api',
                    'data_timestamp': timestamp.isoformat()
                },
                
                # ===== 時間範圍 =====
                'time_range': {
                    'start': (timestamp - timedelta(days=4)).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': (timestamp + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            return case
            
        except Exception as e:
            self.logger.error(f"Error creating case result for {symbol} at index {idx}: {str(e)}")
            return None

    # 額外的數據驗證函數
    def validate_case_data_quality(cases: List[Dict]) -> Dict[str, Any]:
        """驗證案例數據品質"""
        if not cases:
            return {"total_cases": 0, "quality_score": 0, "issues": ["No cases found"]}
        
        total_cases = len(cases)
        complete_cases = 0
        missing_data_issues = []
        
        for case in cases:
            if case.get('data_quality', {}).get('has_complete_ohlcv', False):
                complete_cases += 1
            else:
                missing_fields = case.get('data_quality', {}).get('missing_fields', [])
                if missing_fields:
                    missing_data_issues.extend(missing_fields)
        
        quality_score = complete_cases / total_cases if total_cases > 0 else 0
        
        return {
            "total_cases": total_cases,
            "complete_cases": complete_cases,
            "incomplete_cases": total_cases - complete_cases,
            "quality_score": quality_score,
            "completion_rate": f"{quality_score * 100:.1f}%",
            "common_missing_fields": list(set(missing_data_issues)),
            "issues": missing_data_issues if missing_data_issues else ["All cases have complete data"]
        }
    
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
            data = self._add_calculated_columns(data, config.timeframe)

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
                '''
                indicator_columns = [
                    'future1_close_return', 'future2_close_return', 'future4_close_return', 'future6_close_return',
                    'future24_close_return', 'future48_close_return',  # 新增
                    'future_max_return', 'future72_max_return',        # 擴展
                    'future_max_drawdown', 'future72_max_drawdown',    # 擴展
                    'future24_close', 'future24_low'
                ]
                '''
                indicator_columns = [
                    # 現有參數
                    'future1_close_return', 'future2_close_return', 'future4_close_return', 'future6_close_return',
                    'future24_close_return', 'future48_close_return', 'future72_close_return',
                    'future_max_return', 'future72_max_return',
                    'future_max_drawdown', 'future72_max_drawdown',
                    'future24_close', 'future24_low',

                    # 新增的基礎觸發條件參數
                    'closing_strength', 'price_position', 'volume_multiplier', 'taker_buy_ratio',

                    # 新增的未來收益參數 (1-12根K線)
                    'future_1bar_return', 'future_2bar_return', 'future_3bar_return', 'future_4bar_return',
                    'future_5bar_return', 'future_6bar_return', 'future_7bar_return', 'future_8bar_return',
                    'future_9bar_return', 'future_10bar_return', 'future_11bar_return', 'future_12bar_return',

                    # 新增的未來回撤參數 (1-12根K線)
                    'future_1bar_max_drawdown', 'future_2bar_max_drawdown', 'future_3bar_max_drawdown', 'future_4bar_max_drawdown',
                    'future_5bar_max_drawdown', 'future_6bar_max_drawdown', 'future_7bar_max_drawdown', 'future_8bar_max_drawdown',
                    'future_9bar_max_drawdown', 'future_10bar_max_drawdown', 'future_11bar_max_drawdown', 'future_12bar_max_drawdown',

                    # 新增的時間描述參數
                    'hour_of_day', 'day_of_week',

                    # ===== 改寫：分類特徵參數 (9個) =====
                    # 數值參數（3個）
                    'past_3day_max_volatility',   # 過去3天最大波動度(%)
                    'past_3day_direction',         # 過去3天方向性(%)
                    'past_3day_volume_cv',         # 過去3天量能CV

                    # 分類參數（6個）
                    'volatility_class',    # L/M/H/X
                    'direction_class',     # D/S/U/V
                    'volume_class',        # A/B/C
                    'market_class',        # C1-C12
                    'market_class_name',   # 平靜橫盤等
                    'difficulty_level'     # 簡單/中等/困難
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
                            # Debug: 記錄缺失的歷史穩定度參數
                            if 'past_' in col:
                                self.logger.warning(f"歷史穩定度參數 '{col}' 不在 data.columns 中")
                
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

    def _calculate_past_stability_features(
        self,
        df: pd.DataFrame,
        periods_24h: int,
        periods_48h: int,
        periods_72h: int
    ) -> pd.DataFrame:
        """
        計算分類特徵（完全改寫版本）

        ⚠️ 重要：從T-1 bar開始往前看3天，不包含T

        Args:
            df: 包含OHLCV數據的DataFrame，必須包含 open, high, low, close, volume 列
            periods_24h: 24小時對應的bar數量（保留參數，向後兼容）
            periods_48h: 48小時對應的bar數量（保留參數，向後兼容）
            periods_72h: 72小時對應的bar數量（用於3天lookback）

        Returns:
            添加9個新列的DataFrame:

            【3個數值參數】
            - past_3day_max_volatility: 過去3天最大波動度(%)
            - past_3day_direction: 過去3天方向性(%)
            - past_3day_volume_cv: 過去3天量能變異係數

            【6個分類參數】
            - volatility_class: L/M/H/X
            - direction_class: D/S/U/V
            - volume_class: A/B/C
            - market_class: C1-C12
            - market_class_name: 平靜橫盤等
            - difficulty_level: 簡單/中等/困難

        注意：
            - 100%向量化操作（使用np.select避免.apply）
            - 從T-1開始往前看（使用 .shift(1)）
            - 前N根bar會產生NaN（正常且預期）
            - 所有除法操作都有除零保護（+ 1e-10）
        """
        try:
            lookback_bars = periods_72h  # 3天

            # ===== 參數1: past_3day_max_volatility =====
            # 計算每根bar的波動度：(High - Low) / Open * 100
            bar_volatility = np.where(
                df['open'] > 0,
                (df['high'] - df['low']) / df['open'],
                0.0
            )

            # 從T-1往前看lookback_bars根（不包含T）
            # 使用 .shift(1) 將數據向下移1位，再取.rolling()
            bar_volatility_shifted = pd.Series(bar_volatility, index=df.index).shift(1)
            past_volatility = bar_volatility_shifted.rolling(
                window=lookback_bars,
                min_periods=max(1, lookback_bars // 2)
            ).max() * 100  # 轉為百分比

            df['past_3day_max_volatility'] = past_volatility

            # 波動度分類 L/M/H/X（向量化版本）
            conditions_vol = [
                past_volatility < 2,
                (past_volatility >= 2) & (past_volatility < 5),
                (past_volatility >= 5) & (past_volatility < 10)
            ]
            choices_vol = ['L', 'M', 'H']
            df['volatility_class'] = np.select(conditions_vol, choices_vol, default='X')

            # ===== 參數2: past_3day_direction =====
            # 從T-1的close到T-1-lookback_bars的close的變化百分比
            close_shifted = df['close'].shift(1)  # T-1的close
            close_start = df['close'].shift(lookback_bars + 1)  # T-1-lookback_bars的close

            direction_pct = np.where(
                close_start > 0,
                (close_shifted - close_start) / close_start * 100,
                np.nan
            )

            df['past_3day_direction'] = direction_pct

            # 方向性分類 D/S/U/V（向量化版本）
            conditions_dir = [
                direction_pct < -3,
                (direction_pct >= -3) & (direction_pct < 3),
                (direction_pct >= 3) & (direction_pct < 8)
            ]
            choices_dir = ['D', 'S', 'U']
            df['direction_class'] = np.select(conditions_dir, choices_dir, default='V')

            # ===== 參數3: past_3day_volume_cv =====
            # 變異係數 = std / mean（從T-1往前看）
            volume_shifted = df['volume'].shift(1)

            volume_mean = volume_shifted.rolling(
                window=lookback_bars,
                min_periods=max(1, lookback_bars // 2)
            ).mean()

            volume_std = volume_shifted.rolling(
                window=lookback_bars,
                min_periods=max(1, lookback_bars // 2)
            ).std()

            volume_cv = np.where(
                volume_mean > 0,
                volume_std / (volume_mean + 1e-10),
                np.nan
            )

            df['past_3day_volume_cv'] = volume_cv

            # 量能分類 A/B/C（向量化版本）
            conditions_vol_cls = [
                volume_cv < 0.5,
                (volume_cv >= 0.5) & (volume_cv < 1.0)
            ]
            choices_vol_cls = ['A', 'B']
            df['volume_class'] = np.select(conditions_vol_cls, choices_vol_cls, default='C')

            # ===== 應用市場分類（向量化版本）=====
            # 初始化為C11（預設）
            df['market_class'] = 'C11'
            df['market_class_name'] = '其他組合'
            df['difficulty_level'] = '混合'

            # 按優先順序應用規則（使用布林遮罩）
            # C1: 平靜橫盤
            mask_c1 = (df['volatility_class'] == 'L') & (df['direction_class'] == 'S') & (df['volume_class'] == 'A')
            df.loc[mask_c1, ['market_class', 'market_class_name', 'difficulty_level']] = ['C1', '平靜橫盤', '中等']

            # C8: 縮量橫盤
            mask_c8 = (df['volatility_class'] == 'L') & (df['direction_class'] == 'S') & (df['volume_class'] == 'C')
            df.loc[mask_c8, ['market_class', 'market_class_name', 'difficulty_level']] = ['C8', '縮量橫盤', '中等']

            # C2: 正常橫盤
            mask_c2 = (df['volatility_class'].isin(['L', 'M'])) & (df['direction_class'] == 'S') & (df['volume_class'] == 'B')
            df.loc[mask_c2, ['market_class', 'market_class_name', 'difficulty_level']] = ['C2', '正常橫盤', '中等']

            # C6: 極端波動
            mask_c6 = df['volatility_class'].isin(['H', 'X'])
            df.loc[mask_c6, ['market_class', 'market_class_name', 'difficulty_level']] = ['C6', '極端波動', '簡單']

            # C9: 恐慌下跌
            mask_c9 = (df['volatility_class'].isin(['H', 'X'])) & (df['direction_class'] == 'D') & (df['volume_class'] == 'C')
            df.loc[mask_c9, ['market_class', 'market_class_name', 'difficulty_level']] = ['C9', '恐慌下跌', '簡單']

            # C3: 下跌趨勢
            mask_c3 = (df['volatility_class'].isin(['M', 'H'])) & (df['direction_class'] == 'D')
            df.loc[mask_c3, ['market_class', 'market_class_name', 'difficulty_level']] = ['C3', '下跌趨勢', '簡單']

            # C5: 假突破
            mask_c5 = (df['volatility_class'] == 'M') & (df['direction_class'] == 'U') & (df['volume_class'] == 'C')
            df.loc[mask_c5, ['market_class', 'market_class_name', 'difficulty_level']] = ['C5', '假突破', '困難']

            # C7: 溫和上漲中
            mask_c7 = (df['volatility_class'] == 'M') & (df['direction_class'] == 'U') & (df['volume_class'].isin(['A', 'B']))
            df.loc[mask_c7, ['market_class', 'market_class_name', 'difficulty_level']] = ['C7', '溫和上漲中', '困難']

            # C4: 高位震盪
            mask_c4 = (df['volatility_class'].isin(['M', 'H'])) & (df['direction_class'].isin(['U', 'V'])) & (df['volume_class'].isin(['B', 'C']))
            df.loc[mask_c4, ['market_class', 'market_class_name', 'difficulty_level']] = ['C4', '高位震盪', '中等']

            # C10: 放量震盪
            mask_c10 = (df['volatility_class'].isin(['M', 'H'])) & (df['direction_class'] == 'S') & (df['volume_class'] == 'C')
            df.loc[mask_c10, ['market_class', 'market_class_name', 'difficulty_level']] = ['C10', '放量震盪', '中等']

            self.logger.info("分類特徵計算完成（9個參數，100%向量化）")

            return df

        except Exception as e:
            self.logger.error(f"計算分類特徵時出錯: {str(e)}", exc_info=True)
            # 確保欄位存在（避免後續處理失敗）
            for col in ['past_3day_max_volatility', 'past_3day_direction',
                        'past_3day_volume_cv', 'volatility_class',
                        'direction_class', 'volume_class', 'market_class',
                        'market_class_name', 'difficulty_level']:
                if col not in df.columns:
                    df[col] = np.nan
            return df

    def _add_calculated_columns(self, data: pd.DataFrame, timeframe: str = '4h') -> pd.DataFrame:
        """
        添加計算列，擴充版本支援完整的20個參數

        包含:
        1. 基礎觸發條件參數 (6個)
        2. 未來表現驗證參數 (12個) 
        3. 時間和市場描述參數
        """
        # DEBUG: 確認此函數被調用
        self.logger.warning(f"🔍 DEBUG: _add_calculated_columns 被調用 - timeframe={timeframe}, rows={len(data)}")

        try:
            self.logger.info("開始添加擴充計算列...")
            df = data.copy()
            
            # ===== 時間框架配置 =====
            periods_info = self._get_timeframe_periods(timeframe)
            hours_per_candle = periods_info['hours_per_candle']
            periods_24h = periods_info['periods_24h']
            periods_48h = periods_info['periods_48h']
            periods_72h = periods_info['periods_72h']
            
            self.logger.info(f"時間框架: {timeframe}, 每根K線: {hours_per_candle}小時")
            self.logger.info(f"計算週期 - 24h: {periods_24h}根, 48h: {periods_48h}根, 72h: {periods_72h}根")
            
            # ===== 1. 基礎觸發條件參數 (6個) =====
            
            # 1.1 timeframe (已有)
            df['timeframe'] = timeframe
            
            # 1.2 price_change - 當前K線相對前一根的漲跌幅
            df['price_change'] = df['close'].pct_change()
            
            # 1.3 closing_strength - 收盤強度 = (close - low) / (high - low)
            df['closing_strength'] = np.where(
                (df['high'] - df['low']) != 0,
                (df['close'] - df['low']) / (df['high'] - df['low']),
                np.nan  # 如果沒有價格變化，設為中性值
            )
            
            # 1.4 price_position - 價格位置 (近期20根K線的位置)
            lookback_periods = 20
            df['recent_high'] = df['high'].rolling(window=lookback_periods, min_periods=1).max()
            df['recent_low'] = df['low'].rolling(window=lookback_periods, min_periods=1).min()
            df['price_position'] = np.where(
                (df['recent_high'] - df['recent_low']) != 0,
                (df['close'] - df['recent_low']) / (df['recent_high'] - df['recent_low']),
                np.nan  # 如果沒有範圍，設為中性值
            )
            
            # 1.5 volume_multiplier - 成交量倍數 (相對於近期20根K線平均)
            df['volume_avg_20'] = df['volume'].rolling(window=lookback_periods, min_periods=1).mean()
            df['volume_multiplier'] = np.where(
                df['volume_avg_20'] != 0,
                df['volume'] / df['volume_avg_20'],
                np.nan  # 如果沒有歷史數據，設為1
            )
            
            # 1.6 taker_buy_ratio - 主動買入比例
            if 'taker_buy_base_asset_volume' in df.columns:
                # 使用真實的taker buy volume數據
                df['taker_buy_ratio'] = np.where(
                    df['volume'] != 0,
                    df['taker_buy_base_asset_volume'] / df['volume'],
                    np.nan  # 成交量為0時設為NaN
                )
                self.logger.info("使用真實的 taker_buy_base_asset_volume 數據計算taker_buy_ratio")
            elif 'taker_buy_volume' in df.columns:
                # 兼容其他可能的欄位名稱
                df['taker_buy_ratio'] = np.where(
                    df['volume'] != 0,
                    df['taker_buy_volume'] / df['volume'],
                    np.nan  # 成交量為0時設為NaN
                )
                self.logger.info("使用 taker_buy_volume 數據計算taker_buy_ratio")
            else:
                # 完全沒有taker volume數據時設為NaN
                df['taker_buy_ratio'] = np.nan
                self.logger.warning("缺少 taker buy volume 數據，taker_buy_ratio 設為 NaN")
            
            
            # ===== 2. 未來表現驗證參數 (12個) =====
            
            # 2.1 未來1-12根K線收益率
            for bar in range(1, 13):
                col_name = f'future_{bar}bar_return'
                df[col_name] = (df['close'].shift(-bar) - df['close']) / df['close']
            
            # 2.2 未來1-12根K線最大回撤（向量化版本 - Phase 2優化）
            self.logger.info("開始計算未來最大回撤（向量化）...")
            for bar in range(1, 13):
                col_name = f'future_{bar}bar_max_drawdown'

                # 向量化計算：使用 expanding() + shift() 實現正向未來窗口
                #
                # 原循環邏輯：對於位置i，計算 df.iloc[i+1:i+bar+1]['low'].min()
                # 向量化方法：
                # 1. 反轉數據（這樣 rolling 就變成往未來看）
                # 2. 應用 rolling().min()
                # 3. 再反轉回來

                # 更簡單的方法：直接使用 shift + min
                # 對每個 bar，創建一個 bar 長度的窗口
                min_values = []
                for offset in range(1, bar + 1):
                    min_values.append(df['low'].shift(-offset))

                # 取所有offset的最小值（逐元素）
                if min_values:
                    future_min_low = pd.concat(min_values, axis=1).min(axis=1)
                else:
                    future_min_low = pd.Series(np.nan, index=df.index)

                # 計算最大回撤（向量化）
                df[col_name] = np.where(
                    df['close'] > 0,  # 避免除以0
                    (future_min_low / df['close'] - 1),
                    np.nan
                )
            
            # ===== 3. 時間相關描述參數 =====
            
            # 3.1 hour_of_day - 觸發時的小時 (0-23)
            df['hour_of_day'] = pd.to_datetime(df.index).hour
            
            # 3.2 day_of_week - 觸發時的星期 (1-7, 1=Monday)
            df['day_of_week'] = pd.to_datetime(df.index).dayofweek + 1
            
            # ===== 4. 市場階段計算 =====
            if 'market_phase' not in df.columns:
                # 使用價格動量和波動率來估算市場階段
                df['price_momentum'] = df['close'].pct_change(periods=5).rolling(window=5).mean()
                df['volatility'] = df['close'].pct_change().rolling(window=20).std()
                
                # 根據動量和波動率分類市場階段
                df['market_phase'] = np.where(
                    (df['price_momentum'] > 0.02) & (df['volatility'] > 0.03), 'GREED',
                    np.where(
                        (df['price_momentum'] < -0.02) & (df['volatility'] > 0.03), 'FEAR',
                        np.where(df['volatility'] > 0.05, 'EXTREME', 'NEUTRAL')
                    )
                )
            
            # ===== 5. 保持現有的標準化時間計算 (向後兼容) =====
            
            # 基本未來回報計算
            df['future1_close_return'] = (df['close'].shift(-1) - df['close']) / df['close']
            df['future2_close_return'] = (df['close'].shift(-2) - df['close']) / df['close']
            df['future4_close_return'] = (df['close'].shift(-4) - df['close']) / df['close']
            df['future6_close_return'] = (df['close'].shift(-6) - df['close']) / df['close']
            
            # 時間基礎的未來回報計算
            df['future24_close_return'] = (df['close'].shift(-periods_24h) - df['close']) / df['close']
            df['future48_close_return'] = (df['close'].shift(-periods_48h) - df['close']) / df['close']
            df['future72_close_return'] = (df['close'].shift(-periods_72h) - df['close']) / df['close']
            
            # 未來價格數據
            df['future24_close'] = df['close'].shift(-periods_24h)
            if periods_24h > 1:
                df['future24_low'] = df['low'].rolling(window=periods_24h, min_periods=1).min().shift(-periods_24h)
            else:
                df['future24_low'] = df['low'].shift(-periods_24h)
            
            # ===== 6. 72小時最大回報和回撤計算（向量化版本 - Phase 2優化）=====
            lookahead_periods = periods_72h

            self.logger.info("開始計算72小時最大回報和回撤（向量化）...")

            # 72小時窗口：向量化計算（使用 shift + min/max）
            # 計算未來窗口內的最高價和最低價
            high_values_72h = []
            low_values_72h = []
            for offset in range(1, lookahead_periods + 1):
                high_values_72h.append(df['high'].shift(-offset))
                low_values_72h.append(df['low'].shift(-offset))

            future_max_high_72h = pd.concat(high_values_72h, axis=1).max(axis=1) if high_values_72h else pd.Series(np.nan, index=df.index)
            future_min_low_72h = pd.concat(low_values_72h, axis=1).min(axis=1) if low_values_72h else pd.Series(np.nan, index=df.index)

            # 計算72小時最大回報和回撤（向量化）
            df['future72_max_return'] = np.where(
                df['close'] > 0,
                (future_max_high_72h / df['close'] - 1),
                np.nan
            )

            df['future72_max_drawdown'] = np.where(
                df['close'] > 0,
                (future_min_low_72h / df['close'] - 1),
                np.nan
            )

            # 標準6根K線窗口：向量化計算（保持向後兼容）
            standard_lookahead = 6

            high_values_std = []
            low_values_std = []
            for offset in range(1, standard_lookahead + 1):
                high_values_std.append(df['high'].shift(-offset))
                low_values_std.append(df['low'].shift(-offset))

            future_max_high_std = pd.concat(high_values_std, axis=1).max(axis=1) if high_values_std else pd.Series(np.nan, index=df.index)
            future_min_low_std = pd.concat(low_values_std, axis=1).min(axis=1) if low_values_std else pd.Series(np.nan, index=df.index)

            df['future_max_return'] = np.where(
                df['close'] > 0,
                (future_max_high_std / df['close'] - 1),
                np.nan
            )

            df['future_max_drawdown'] = np.where(
                df['close'] > 0,
                (future_min_low_std / df['close'] - 1),
                np.nan
            )

            # ===== 6. 歷史穩定度特徵參數 (5個) =====
            self.logger.info("開始計算歷史穩定度特徵參數...")
            df = self._calculate_past_stability_features(df, periods_24h, periods_48h, periods_72h)

            # ===== 7. 數據質量報告 =====
            self.logger.info("=== 擴充參數計算完成統計 ===")
            
            # 基礎觸發條件參數
            basic_params = ['price_change', 'closing_strength', 'price_position', 'volume_multiplier', 'taker_buy_ratio']
            self.logger.info("基礎觸發條件參數:")
            for param in basic_params:
                if param in df.columns:
                    nan_count = df[param].isna().sum()
                    valid_count = len(df) - nan_count
                    self.logger.info(f"  - {param}: {valid_count}/{len(df)} 有效值 ({nan_count} NaN)")
            
            # 未來收益參數
            self.logger.info("未來收益參數 (1-12根K線):")
            for bar in range(1, 13):
                param = f'future_{bar}bar_return'
                if param in df.columns:
                    nan_count = df[param].isna().sum()
                    valid_count = len(df) - nan_count
                    self.logger.info(f"  - {param}: {valid_count}/{len(df)} 有效值")
            
            # 未來回撤參數
            self.logger.info("未來回撤參數 (1-12根K線):")
            for bar in range(1, 13):
                param = f'future_{bar}bar_max_drawdown'
                if param in df.columns:
                    nan_count = df[param].isna().sum()
                    valid_count = len(df) - nan_count
                    self.logger.info(f"  - {param}: {valid_count}/{len(df)} 有效值")
            
            # 時間和市場參數
            time_params = ['hour_of_day', 'day_of_week', 'market_phase', 'timeframe']
            self.logger.info("時間和市場參數:")
            for param in time_params:
                if param in df.columns:
                    nan_count = df[param].isna().sum()
                    valid_count = len(df) - nan_count
                    unique_count = df[param].nunique()
                    self.logger.info(f"  - {param}: {valid_count}/{len(df)} 有效值, {unique_count} 唯一值")

            # 歷史穩定度參數
            past_params = [
                'past_24hr_max_single_move',
                'past_48hr_price_range',
                'past_72hr_avg_bar_volatility',
                'past_48hr_directional_movement',
                'past_24hr_volume_stability'
            ]
            self.logger.info("歷史穩定度參數:")
            for param in past_params:
                if param in df.columns:
                    nan_count = df[param].isna().sum()
                    valid_count = len(df) - nan_count
                    self.logger.info(f"  - {param}: {valid_count}/{len(df)} 有效值 ({nan_count} NaN)")

            # 總參數統計
            total_new_params = len(basic_params) + 12 + 12 + len(time_params) + len(past_params)
            self.logger.info(f"=== 總計新增/更新了 {total_new_params} 個參數欄位 ===")
            
            return df
            
        except Exception as e:
            self.logger.error(f"添加計算列時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return data

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

    