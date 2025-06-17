import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dataclasses import dataclass
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import pandas_ta as ta
from momentum.Indicator.Base_Indicator_Reference import BaseIndicator, IndicatorParams

@dataclass
class MAParams(IndicatorParams):
    """MA指標特定參數"""
    short_period: int = 5    
    mid_period: int = 10     
    long_period: int = 20    
    lookback: int = 100
    shortovermid_threshold: float = 1.05 
    midoverlong_threshold: float = 1.02

class AdvancedMA(BaseIndicator):
    def __init__(self, params: MAParams):
        super().__init__(params)
        self.params: MAParams = params
        self._last_results = None

    def get_signal_names(self) -> List[str]:
        """返回所有可能的信號名稱"""
        ma_types = ['ema', 'dema', 'tema']
        data_types = ['close', 'volume', 'taker_volume', 'taker_ratio']
        base_signals = ['golden_cross', 'bullish_alignment']#, 'death_cross','bearish_alignment']
        
        signals = []
        # 為每個MA類型和數據類型生成信號組合
        for ma_type in ma_types:
            for data_type in data_types:
                for signal in base_signals:
                    signals.append(f"{signal}_{data_type}_{ma_type}")
        
        # KAMA特有信號
        signals.extend(['kama_trend_cross_up', 'kama_trend_cross_down'])
        
        return signals
    
    def get_signal_description(self, signal_name: str) -> str:
        """返回信號的描述"""
        try:
            # 解析信號名稱
            if signal_name.startswith('kama'):
                if signal_name == 'kama_trend_cross_up':
                    return 'KAMA趨勢向上交叉'
                elif signal_name == 'kama_trend_cross_down':
                    return 'KAMA趨勢向下交叉'
                return '未知KAMA信號'
                
            # 解析一般MA信號
            parts = signal_name.split('_')
            if len(parts) < 3:
                return '無效信號名稱'
            
            signal_type = parts[0]  # 現在是第一個部分
            data_type = parts[1]    # 第二個部分
            ma_type = parts[2]      # 第三個部分
                
            data_type, ma_type, *signal_parts = parts
            signal_type = '_'.join(signal_parts)
            
            # 數據類型描述
            data_desc = {
                'close': '收盤價',
                'volume': '成交量',
                'taker_volume': '主動成交量',
                'taker_ratio': '主動比率'
            }.get(data_type, '未知數據')
            
            # MA類型描述
            ma_desc = {
                'ema': 'EMA',
                'dema': 'DEMA',
                'tema': 'TEMA'
            }.get(ma_type, '未知均線')
            
            # 信號類型描述
            signal_desc = {
                'golden_cross': '黃金交叉',
                'death_cross': '死亡交叉',
                'bullish_alignment': '多頭排列',
                'bearish_alignment': '空頭排列'
            }.get(signal_type, '未知信號')
            
            return f'{data_desc}的{ma_desc}{signal_desc}'
            
        except Exception as e:
            self.logger.error(f"生成信號描述時出錯: {str(e)}")
            return '無效信號'

    def get_signal_colors(self) -> Dict[str, str]:
        """返回信號顏色映射"""
        colors = {}
        data_types = ['close', 'volume', 'taker_volume', 'taker_ratio']
        
        # 基本顏色配置
        base_colors = {
            'ema': {'golden_cross': 'gold', 'bullish_alignment': 'green'}, # 'death_cross': 'red', 'bearish_alignment': 'darkred'},
            'dema': {'golden_cross': 'orange', 'bullish_alignment': 'lime'}, # 'death_cross': 'crimson', 'bearish_alignment': 'maroon'},
            'tema': {'golden_cross': 'yellow', 'bullish_alignment': 'lightgreen'} #, 'death_cross': 'firebrick', 'bearish_alignment': 'brown'}
        }
        
        # 為每種數據類型生成顏色
        for ma_type, type_colors in base_colors.items():
            for data_type in data_types:
                for signal, color in type_colors.items():
                    colors[f"{signal}_{data_type}_{ma_type}"] = color
        
        # KAMA信號顏色
        colors.update({
            'kama_trend_cross_up': 'cyan',
            'kama_trend_cross_down': 'purple'
        })
        
        return colors
    
    def _check_ma_signals(self, data_type: str, ma_type: str, 
                         values: Dict[str, pd.Series], index: int) -> List[str]:
        """檢查指定數據類型和MA類型的信號
        
        Args:
            data_type: 數據類型 (close/volume/taker_volume/taker_ratio)
            ma_type: MA類型 (ema/dema/tema)
            values: 計算結果字典
            index: 當前K線索引
        """
        signals = []
        signal_prefix = f"{data_type}_{ma_type}"
        
        try:
            short = values[f'{data_type}_{ma_type}_short']
            mid = values[f'{data_type}_{ma_type}_mid']
            long = values[f'{data_type}_{ma_type}_long']
            
            # 黃金交叉
            if (short.iloc[index] > long.iloc[index] and 
                short.iloc[index-1] <= long.iloc[index-1]):
                signals.append(f"golden_cross_{signal_prefix}")

            # 多頭排列
            if short.iloc[index] > mid.iloc[index]*self.params.shortovermid_threshold > long.iloc[index]*self.params.midoverlong_threshold:
                signals.append(f"bullish_alignment_{signal_prefix}")
                
            '''# 死亡交叉
            if (short.iloc[index] < long.iloc[index] and 
                short.iloc[index-1] >= long.iloc[index-1]):
                signals.append(f"death_cross_{signal_prefix}")
                
            # 空頭排列
            elif short.iloc[index] < mid.iloc[index] < long.iloc[index]:
                signals.append(f"bearish_alignment_{signal_prefix}")
            '''
                
        except Exception as e:
            self.logger.error(f"檢查{data_type}_{ma_type}信號時出錯: {str(e)}")
            
        return signals

    def _check_kama_signals(self, values: Dict[str, pd.Series], 
                           data: pd.DataFrame, index: int) -> List[str]:
        """檢查KAMA特有的信號"""
        signals = []
        kama = values['close_kama']
        price = data['close']
        
        if (price.iloc[index] > kama.iloc[index] and 
            price.iloc[index-1] <= kama.iloc[index-1]):
            signals.append('kama_trend_cross_up')
        elif (price.iloc[index] < kama.iloc[index] and 
              price.iloc[index-1] >= kama.iloc[index-1]):
            signals.append('kama_trend_cross_down')
            
        return signals
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """計算所有類型的MA指標值"""
        try:
            self.validate_data(data)
            results = {}

            # 保存原始數據
            base_columns = ['close', 'open', 'high', 'low', 'volume', 
                        'taker_buy_base_asset_volume']
            for col in base_columns:
                if col in data.columns:
                    results[col] = data[col]

            # 計算taker比率
            taker_ratio = self.calculate_volume_ratios(data)
            results['taker_ratio'] = taker_ratio

            # 待分析的數據序列
            series_dict = {
                'close': data['close'],
                'volume': data['volume'],
                'taker_volume': data['taker_buy_base_asset_volume'],
                'taker_ratio': taker_ratio
            }

            # 為每個序列計算不同週期的MA
            for series_name, series_data in series_dict.items():
                # 使用pandas_ta計算不同週期的指標
                for period_name, period in [
                    ('short', self.params.short_period),
                    ('mid', self.params.mid_period),
                    ('long', self.params.long_period)
                ]:
                    # EMA
                    results[f'{series_name}_ema_{period_name}'] = ta.ema(series_data, length=period)
                    
                    # DEMA
                    results[f'{series_name}_dema_{period_name}'] = ta.dema(series_data, length=period)
                    
                    # TEMA
                    results[f'{series_name}_tema_{period_name}'] = ta.tema(series_data, length=period)
                
                # KAMA (使用mid_period作為預設週期)
                results[f'{series_name}_kama'] = ta.kama(series_data, length=self.params.mid_period)

            self._last_results = results
            return results

        except Exception as e:
            self.logger.error(f"計算指標時出錯: {str(e)}")
            raise

    def analyze_pattern(self, data: pd.DataFrame, 
                       indicator_values: Dict[str, pd.Series] = None) -> Dict[str, Any]:
        """分析Pattern並記錄信號位置"""
        if indicator_values is None:
            indicator_values = self._last_results
            if indicator_values is None:
                raise ValueError("需要先調用calculate()計算指標值")
        
        patterns = {
            'signals': {},
            'analysis': {}
        }
        
        try:
            # 定義數據類型和MA類型
            data_types = ['close', 'volume', 'taker_volume', 'taker_ratio']
            ma_types = ['ema', 'dema', 'tema']
            
            # 遍歷每根K線
            for i in range(1, len(data)):
                k_line_signals = []
                
                # 檢查每種數據類型和MA類型的組合
                for data_type in data_types:
                    for ma_type in ma_types:
                        try:
                            signals = self._check_ma_signals(
                                data_type, ma_type, indicator_values, i)
                            k_line_signals.extend(signals)
                        except Exception as e:
                            self.logger.error(
                                f"處理{data_type}_{ma_type}時出錯: {str(e)}")
                            continue
                
                # 檢查KAMA信號
                kama_signals = self._check_kama_signals(indicator_values, data, i)
                k_line_signals.extend(kama_signals)
                
                # 記錄信號
                if k_line_signals:
                    patterns['signals'][i] = {
                        'timestamp': data.index[i],
                        'signals': k_line_signals,
                        'k_line_number': i
                    }
                    #self.logger.info(f"K線 {i} 發現信號: {k_line_signals}") #Debug Using
                    
        except Exception as e:
            self.logger.error(f"分析Pattern時出錯: {str(e)}")
            
        return patterns
    
    def get_signal_valid_range(self, signal_name: str) -> int:
        """獲取指定信號的有效起始K線位置"""
        try:
            parts = signal_name.split('_')
            if 'kama' in signal_name:  # kama_trend_cross_up/down
                valid_start = self._valid_starts.get('close_kama', 0)
                self.logger.debug(f"KAMA signal {signal_name} using start position from close_kama: {valid_start}")
                return valid_start
                
            # 最後兩個部分是指標類型和週期
            ma_type = parts[-1]  # ema/dema/tema
            series_type = parts[-2]  # close/volume/ratio
            if parts[-3] == "taker":  # taker_volume/taker_ratio
                series_type = f"taker_{series_type}"
                
            # 先嘗試取得長週期的起始位置
            indicator_key = f"{series_type}_{ma_type}_long"
            return self._valid_starts.get(indicator_key, 0)
            
        except Exception as e:
            self.logger.warning(f"解析信號名稱失敗 {signal_name}: {str(e)}")
            return 0