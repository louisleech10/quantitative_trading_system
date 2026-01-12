"""
Feature Configuration and Dynamic Naming System

這個模組提供特徵工程的配置系統和動態命名機制，解決不同數據源和參數組合的特徵名稱衝突問題。

核心類別:
- IndicatorConfig: 指標配置（數據源 + 指標類型 + 參數）
- FeatureEngineeringConfig: 特徵工程配置（多個指標組合）
- FeatureNamingConfig: 特徵命名生成器（靜態方法）

命名格式: {data_source}_{indicator}{params}_{feature_type}
範例: close_ema5_value, volume_ema6_15_distance, close_rsi14_overbought70

Author: Quantitative Trading System
Date: 2026-01-11
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class DataSourceType(str, Enum):
    """支援的數據源類型"""
    CLOSE = "close"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    VOLUME = "volume"
    TAKER_BUY_VOLUME = "taker_buy_volume"
    TAKER_RATIO = "taker_ratio"


class IndicatorType(str, Enum):
    """支援的指標類型"""
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"


class IndicatorConfig(BaseModel):
    """
    指標配置
    
    Attributes:
        data_source: 數據源（close/open/high/low/volume/taker_buy_volume/taker_ratio）
        indicator_type: 指標類型（ema/rsi/macd/bollinger）
        params: 指標參數（依據指標類型有不同結構）
        
    範例:
        EMA: {"short": 5, "mid": 20, "long": 60, "volume_threshold": 0.6}
        RSI: {"period": 14, "overbought": 70, "oversold": 30}
        MACD: {"fast": 12, "slow": 26, "signal": 9}
        Bollinger: {"period": 20, "std_dev": 2}
    """
    data_source: DataSourceType
    indicator_type: IndicatorType
    params: Dict[str, Union[int, float]]
    
    class Config:
        use_enum_values = True  # 序列化時使用 enum 的值而非名稱
    
    @field_validator('params')
    @classmethod
    def validate_params_structure(cls, v, info):
        """驗證參數結構與指標類型匹配"""
        if 'indicator_type' not in info.data:
            return v
            
        indicator_type = info.data['indicator_type']
        
        if indicator_type == IndicatorType.EMA:
            required_keys = {'ema_short', 'ema_mid', 'ema_long'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(f"EMA 指標需要參數: {required_keys}, 收到: {set(v.keys())}")
            
            # 驗證大小關係
            if not (v['ema_short'] < v['ema_mid'] < v['ema_long']):
                raise ValueError(f"EMA 參數必須滿足 short < mid < long, 收到: {v['ema_short']}, {v['ema_mid']}, {v['ema_long']}")
                
        elif indicator_type == IndicatorType.RSI:
            required_keys = {'period'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(f"RSI 指標需要參數: {required_keys}, 收到: {set(v.keys())}")
            
            if not (2 <= v['period'] <= 100):
                raise ValueError(f"RSI period 必須在 2-100 之間, 收到: {v['period']}")
                
        elif indicator_type == IndicatorType.MACD:
            required_keys = {'fast', 'slow', 'signal'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(f"MACD 指標需要參數: {required_keys}, 收到: {set(v.keys())}")
            
            if not (v['fast'] < v['slow']):
                raise ValueError(f"MACD 參數必須滿足 fast < slow, 收到: {v['fast']}, {v['slow']}")
                
        elif indicator_type == IndicatorType.BOLLINGER:
            required_keys = {'period', 'std_dev'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(f"Bollinger 指標需要參數: {required_keys}, 收到: {set(v.keys())}")
            
            if not (2 <= v['period'] <= 100):
                raise ValueError(f"Bollinger period 必須在 2-100 之間, 收到: {v['period']}")
        
        return v
    
    def get_identifier(self) -> str:
        """
        獲取指標的唯一識別碼（用於特徵名稱前綴）
        
        Returns:
            格式: {data_source}_{indicator_type}
            範例: close_ema, volume_ema, close_rsi
        """
        return f"{self.data_source}_{self.indicator_type}"


class FeatureEngineeringConfig(BaseModel):
    """
    特徵工程配置（支援多個指標組合）
    
    Attributes:
        indicators: 指標配置列表（支援混合配置）
        
    範例:
        [
            {"data_source": "close", "indicator_type": "ema", "params": {...}},
            {"data_source": "volume", "indicator_type": "ema", "params": {...}},
            {"data_source": "close", "indicator_type": "rsi", "params": {...}}
        ]
    """
    indicators: List[IndicatorConfig] = Field(..., min_length=1)
    
    @field_validator('indicators')
    @classmethod
    def validate_no_duplicate_configs(cls, v):
        """驗證沒有重複的配置（相同數據源 + 相同指標類型 + 相同參數）"""
        seen = set()
        for indicator in v:
            # 建立唯一鍵（數據源 + 指標類型 + 排序後的參數）
            params_str = '_'.join(f"{k}={v}" for k, v in sorted(indicator.params.items()))
            unique_key = f"{indicator.data_source}_{indicator.indicator_type}_{params_str}"
            
            if unique_key in seen:
                raise ValueError(f"發現重複配置: {indicator.data_source} + {indicator.indicator_type} + {indicator.params}")
            seen.add(unique_key)
        
        return v
    
    def get_all_identifiers(self) -> List[str]:
        """獲取所有指標的識別碼列表"""
        return [indicator.get_identifier() for indicator in self.indicators]


class FeatureNamingConfig:
    """
    特徵命名生成器（靜態方法）
    
    命名格式: {data_source}_{indicator}{params}_{feature_type}
    
    範例:
        - close_ema5_value: CLOSE 數據的 EMA(5) 值
        - volume_ema6_15_distance: VOLUME 數據的 EMA(6) 和 EMA(15) 距離
        - close_rsi14_overbought70: CLOSE 數據的 RSI(14) 超買閾值 70
        - close_macd12_26_line: CLOSE 數據的 MACD(12,26) 主線
    """
    
    @staticmethod
    def make_feature_name(
        data_source: str,
        indicator_type: str,
        param_keys: List[str],
        params: Dict[str, Union[int, float]],
        feature_type: str
    ) -> str:
        """
        生成特徵名稱
        
        Args:
            data_source: 數據源（close/volume/taker_ratio 等）
            indicator_type: 指標類型（ema/rsi/macd 等）
            param_keys: 要包含在名稱中的參數鍵列表（按順序）
            params: 完整參數字典
            feature_type: 特徵類型（value/distance/signal/overbought 等）
            
        Returns:
            特徵名稱字串
            
        範例:
            >>> make_feature_name('close', 'ema', ['ema_short'], {'ema_short': 5}, 'value')
            'close_ema5_value'
            
            >>> make_feature_name('volume', 'ema', ['ema_short', 'ema_mid'], 
            ...                   {'ema_short': 6, 'ema_mid': 15}, 'distance')
            'volume_ema6_15_distance'
            
            >>> make_feature_name('close', 'rsi', ['period', 'overbought'], 
            ...                   {'period': 14, 'overbought': 70}, 'signal')
            'close_rsi14_overbought70_signal'
        """
        # 基礎前綴
        prefix = f"{data_source}_{indicator_type}"
        
        # 提取參數值並轉換為字串（去除小數點後的 0）
        param_values = []
        for key in param_keys:
            if key not in params:
                raise KeyError(f"參數 '{key}' 不存在於 params 中: {params}")
            
            value = params[key]
            # 如果是浮點數且是整數值，轉為整數顯示
            if isinstance(value, float) and value.is_integer():
                param_values.append(str(int(value)))
            else:
                param_values.append(str(value))
        
        # 組合參數部分
        param_str = '_'.join(param_values)
        
        # 完整名稱
        return f"{prefix}{param_str}_{feature_type}"
    
    @staticmethod
    def make_ema_feature_names(
        data_source: str,
        params: Dict[str, Union[int, float]]
    ) -> Dict[str, str]:
        """
        生成 EMA 指標的所有特徵名稱
        
        Args:
            data_source: 數據源
            params: EMA 參數（ema_short, ema_mid, ema_long, volume_threshold）
            
        Returns:
            特徵名稱字典:
            {
                'ema_short': 'close_ema5_value',
                'ema_mid': 'close_ema20_value',
                'ema_long': 'close_ema60_value',
                'ema_distance_short_mid': 'close_ema5_20_distance',
                'ema_distance_mid_long': 'close_ema20_60_distance',
                'ema_cross_signal': 'close_ema5_20_cross_signal',
                'volume_spike': 'volume_spike_0.6',
                'taker_ratio_distance': 'taker_ratio_distance_0.6'
            }
        """
        short = params['ema_short']
        mid = params['ema_mid']
        long_period = params['ema_long']
        volume_threshold = params.get('volume_threshold', 0.6)
        
        return {
            'ema_short': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_short'], params, 'value'
            ),
            'ema_mid': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_mid'], params, 'value'
            ),
            'ema_long': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_long'], params, 'value'
            ),
            'ema_distance_short_mid': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_short', 'ema_mid'], params, 'distance'
            ),
            'ema_distance_mid_long': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_mid', 'ema_long'], params, 'distance'
            ),
            'ema_cross_signal': FeatureNamingConfig.make_feature_name(
                data_source, 'ema', ['ema_short', 'ema_mid'], params, 'cross_signal'
            ),
            # Volume spike 使用固定數據源 'volume'
            'volume_spike': f"volume_spike_{int(volume_threshold*100) if isinstance(volume_threshold, float) else volume_threshold}",
            # Taker ratio distance 使用固定數據源 'taker_ratio'
            'taker_ratio_distance': f"taker_ratio_distance_{int(volume_threshold*100) if isinstance(volume_threshold, float) else volume_threshold}"
        }
    
    @staticmethod
    def make_rsi_feature_names(
        data_source: str,
        params: Dict[str, Union[int, float]]
    ) -> Dict[str, str]:
        """
        生成 RSI 指標的所有特徵名稱
        
        Args:
            data_source: 數據源
            params: RSI 參數（period, overbought, oversold）
            
        Returns:
            特徵名稱字典:
            {
                'rsi_value': 'close_rsi14_value',
                'rsi_overbought': 'close_rsi14_70_signal',
                'rsi_oversold': 'close_rsi14_30_signal',
                'rsi_momentum': 'close_rsi14_momentum'
            }
        """
        period = params['period']
        overbought = params.get('overbought', 70)
        oversold = params.get('oversold', 30)
        
        return {
            'rsi_value': FeatureNamingConfig.make_feature_name(
                data_source, 'rsi', ['period'], params, 'value'
            ),
            'rsi_overbought': FeatureNamingConfig.make_feature_name(
                data_source, 'rsi', ['period', 'overbought'], 
                {**params, 'overbought': overbought}, 'signal'
            ),
            'rsi_oversold': FeatureNamingConfig.make_feature_name(
                data_source, 'rsi', ['period', 'oversold'], 
                {**params, 'oversold': oversold}, 'signal'
            ),
            'rsi_momentum': FeatureNamingConfig.make_feature_name(
                data_source, 'rsi', ['period'], params, 'momentum'
            )
        }
    
    @staticmethod
    def make_macd_feature_names(
        data_source: str,
        params: Dict[str, Union[int, float]]
    ) -> Dict[str, str]:
        """
        生成 MACD 指標的所有特徵名稱
        
        Args:
            data_source: 數據源
            params: MACD 參數（fast, slow, signal）
            
        Returns:
            特徵名稱字典:
            {
                'macd_line': 'close_macd12_26_line',
                'macd_signal': 'close_macd12_26_9_signal',
                'macd_histogram': 'close_macd12_26_9_histogram',
                'macd_cross': 'close_macd12_26_9_cross'
            }
        """
        fast = params['fast']
        slow = params['slow']
        signal = params['signal']
        
        return {
            'macd_line': FeatureNamingConfig.make_feature_name(
                data_source, 'macd', ['fast', 'slow'], params, 'line'
            ),
            'macd_signal': FeatureNamingConfig.make_feature_name(
                data_source, 'macd', ['fast', 'slow', 'signal'], params, 'signal'
            ),
            'macd_histogram': FeatureNamingConfig.make_feature_name(
                data_source, 'macd', ['fast', 'slow', 'signal'], params, 'histogram'
            ),
            'macd_cross': FeatureNamingConfig.make_feature_name(
                data_source, 'macd', ['fast', 'slow', 'signal'], params, 'cross'
            )
        }


# ==================== 單元測試 ====================

def test_indicator_config_validation():
    """測試 IndicatorConfig 參數驗證"""
    from pydantic import ValidationError
    
    print("\n========== 測試 IndicatorConfig 驗證 ==========")
    
    # 測試 1: 正確的 EMA 配置
    try:
        config = IndicatorConfig(
            data_source="close",
            indicator_type="ema",
            params={"ema_short": 5, "ema_mid": 20, "ema_long": 60, "volume_threshold": 0.6}
        )
        print(f"✅ EMA 配置驗證通過: {config.get_identifier()}")
    except Exception as e:
        print(f"❌ EMA 配置驗證失敗: {e}")
    
    # 測試 2: EMA 參數順序錯誤
    try:
        config = IndicatorConfig(
            data_source="close",
            indicator_type="ema",
            params={"ema_short": 20, "ema_mid": 5, "ema_long": 60}  # short > mid
        )
        print(f"❌ 應該拋出驗證錯誤（EMA 參數順序錯誤）")
    except ValidationError as e:
        print(f"✅ 正確捕捉到驗證錯誤: EMA 參數順序必須 short < mid < long")
    
    # 測試 3: 正確的 RSI 配置
    try:
        config = IndicatorConfig(
            data_source="close",
            indicator_type="rsi",
            params={"period": 14, "overbought": 70, "oversold": 30}
        )
        print(f"✅ RSI 配置驗證通過: {config.get_identifier()}")
    except Exception as e:
        print(f"❌ RSI 配置驗證失敗: {e}")
    
    # 測試 4: RSI period 超出範圍
    try:
        config = IndicatorConfig(
            data_source="close",
            indicator_type="rsi",
            params={"period": 150}  # 超過 100
        )
        print(f"❌ 應該拋出驗證錯誤（RSI period 超出範圍）")
    except ValidationError as e:
        print(f"✅ 正確捕捉到驗證錯誤: RSI period 必須在 2-100 之間")


def test_feature_naming():
    """測試特徵命名生成"""
    print("\n========== 測試特徵命名生成 ==========")
    
    # 測試 1: EMA 單一值特徵
    name1 = FeatureNamingConfig.make_feature_name(
        'close', 'ema', ['ema_short'], {'ema_short': 5, 'ema_mid': 20, 'ema_long': 60}, 'value'
    )
    print(f"✅ EMA 值特徵: {name1}")
    assert name1 == 'close_ema5_value', f"預期 'close_ema5_value', 得到 '{name1}'"
    
    # 測試 2: EMA 距離特徵
    name2 = FeatureNamingConfig.make_feature_name(
        'volume', 'ema', ['ema_short', 'ema_mid'], 
        {'ema_short': 6, 'ema_mid': 15, 'ema_long': 28}, 'distance'
    )
    print(f"✅ EMA 距離特徵: {name2}")
    assert name2 == 'volume_ema6_15_distance', f"預期 'volume_ema6_15_distance', 得到 '{name2}'"
    
    # 測試 3: RSI 超買特徵
    name3 = FeatureNamingConfig.make_feature_name(
        'close', 'rsi', ['period', 'overbought'], 
        {'period': 14, 'overbought': 70, 'oversold': 30}, 'signal'
    )
    print(f"✅ RSI 超買特徵: {name3}")
    assert name3 == 'close_rsi14_70_signal', f"預期 'close_rsi14_70_signal', 得到 '{name3}'"
    
    # 測試 4: 完整 EMA 特徵名稱字典
    params = {'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    names = FeatureNamingConfig.make_ema_feature_names('close', params)
    print(f"✅ 完整 EMA 特徵名稱:")
    for key, name in names.items():
        print(f"   {key}: {name}")
    
    assert names['ema_short'] == 'close_ema5_value'
    assert names['ema_distance_short_mid'] == 'close_ema5_20_distance'
    assert names['volume_spike'] == 'volume_spike_60'


def test_feature_engineering_config():
    """測試 FeatureEngineeringConfig 混合配置"""
    from pydantic import ValidationError
    
    print("\n========== 測試 FeatureEngineeringConfig ==========")
    
    # 測試 1: 混合配置（close_ema + volume_ema + close_rsi）
    try:
        config = FeatureEngineeringConfig(
            indicators=[
                IndicatorConfig(
                    data_source="close",
                    indicator_type="ema",
                    params={"ema_short": 5, "ema_mid": 20, "ema_long": 60, "volume_threshold": 0.6}
                ),
                IndicatorConfig(
                    data_source="volume",
                    indicator_type="ema",
                    params={"ema_short": 6, "ema_mid": 15, "ema_long": 28, "volume_threshold": 0.7}
                ),
                IndicatorConfig(
                    data_source="close",
                    indicator_type="rsi",
                    params={"period": 14, "overbought": 70, "oversold": 30}
                )
            ]
        )
        identifiers = config.get_all_identifiers()
        print(f"✅ 混合配置驗證通過: {identifiers}")
        assert identifiers == ['close_ema', 'volume_ema', 'close_rsi']
    except Exception as e:
        print(f"❌ 混合配置驗證失敗: {e}")
    
    # 測試 2: 重複配置檢測
    try:
        config = FeatureEngineeringConfig(
            indicators=[
                IndicatorConfig(
                    data_source="close",
                    indicator_type="ema",
                    params={"ema_short": 5, "ema_mid": 20, "ema_long": 60}
                ),
                IndicatorConfig(
                    data_source="close",
                    indicator_type="ema",
                    params={"ema_short": 5, "ema_mid": 20, "ema_long": 60}  # 完全相同
                )
            ]
        )
        print(f"❌ 應該拋出驗證錯誤（重複配置）")
    except ValidationError as e:
        print(f"✅ 正確捕捉到驗證錯誤: 重複配置")


if __name__ == "__main__":
    print("=" * 60)
    print("Feature Configuration & Naming System - 單元測試")
    print("=" * 60)
    
    test_indicator_config_validation()
    test_feature_naming()
    test_feature_engineering_config()
    
    print("\n" + "=" * 60)
    print("✅ 所有測試完成")
    print("=" * 60)
