"""
Feature Extractor - 動態特徵生成引擎

根據 Optuna 優化後的策略參數動態生成交易特徵
支持多種策略（EMA, MACD, RSI 等）透過策略註冊系統擴展

Version: 2.0 (整合註冊系統)
Author: AI Agent
Date: 2026-01-11
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

from api.core.logging import get_logger
from momentum.FeatureEngineering.data_source_registry import DataSourceRegistry
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
from momentum.FeatureEngineering.feature_config import FeatureNamingConfig

logger = get_logger(__name__)


@dataclass
class StrategyParams:
    """
    策略參數配置
    
    Version 2.0: 使用註冊系統進行驗證
    """
    strategy_type: str  # 策略類型（e.g., 'ema_three_line', 'macd', 'rsi'）
    params: Dict  # 動態參數
    data_source: str = 'close'  # 數據源
    
    def validate(self) -> None:
        """
        驗證參數有效性（使用註冊系統）
        
        優點：
        - 自動驗證新註冊的策略和數據源
        - 無需修改此函式
        """
        # 使用策略註冊系統驗證
        strategy_registry = StrategyRegistry()
        strategy_registry.validate_params(self.strategy_type, self.params)
        
        # 使用數據源註冊系統驗證
        data_source_registry = DataSourceRegistry()
        if not data_source_registry.is_registered(self.data_source):
            available = ', '.join(data_source_registry.list_sources())
            raise ValueError(
                f"無效的數據源: '{self.data_source}'\n"
                f"可用的數據源: {available}\n"
                f"提示：使用 DataSourceRegistry().register() 註冊新數據源"
            )


class FeatureExtractor:
    """
    特徵提取引擎 - 動態特徵生成
    
    Version 2.0 特點：
    - 支援多種策略（透過策略註冊系統）
    - 支援多種數據源（透過數據源註冊系統）
    - 可擴展架構（新增策略/數據源無需修改此類）
    """
    
    def __init__(self):
        self.logger = logger
        self.data_source_registry = DataSourceRegistry()
        self.strategy_registry = StrategyRegistry()
    
    def extract_features_from_strategy(
        self,
        df: pd.DataFrame,
        strategy_params: StrategyParams,
        include_basic_features: bool = True
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        根據策略參數提取特徵
        
        Args:
            df: K線數據 DataFrame (必須包含 OHLCV 和 taker volume)
            strategy_params: 策略參數配置
            include_basic_features: 是否包含通用價格/成交量特徵
            
        Returns:
            (features_df, feature_names) - 特徵 DataFrame 和特徵名稱列表
        """
        strategy_params.validate()
        self._validate_input_data(df)
        
        self.logger.info(f"開始提取特徵 - 策略: {strategy_params.strategy_type}, "
                        f"數據行數: {len(df)}")
        
        # 複製數據避免修改原始 df
        features_df = df.copy()
        feature_names = []
        
        # Stage 1: 通用價格特徵
        if include_basic_features:
            features_df, price_features = self.extract_price_features(features_df)
            feature_names.extend(price_features)
            self.logger.info(f"提取價格特徵: {len(price_features)} 個")
        
        # Stage 2: 通用成交量特徵
        if include_basic_features:
            features_df, volume_features = self.extract_volume_features(features_df)
            feature_names.extend(volume_features)
            self.logger.info(f"提取成交量特徵: {len(volume_features)} 個")
        
        # Stage 3: 策略參數化特徵 (完全動態)
        try:
            features_df, strategy_features = self.strategy_registry.extract_features(
                strategy_name=strategy_params.strategy_type,
                df=features_df,
                params=strategy_params.params,
                data_source=strategy_params.data_source
            )
            feature_names.extend(strategy_features)
            self.logger.info(
                f"提取 {strategy_params.strategy_type} 策略特徵: {len(strategy_features)} 個 "
                f"(數據源: {strategy_params.data_source})"
            )
        except Exception as e:
            self.logger.error(f"提取策略特徵失敗: {e}")
            raise
        
        # Stage 4: 信號組合特徵 (可選)
        if self._has_signal_features(strategy_params.strategy_type):
            features_df, signal_features = self.extract_signal_features(
                features_df, strategy_params
            )
            feature_names.extend(signal_features)
            self.logger.info(f"提取信號特徵: {len(signal_features)} 個")
        
        # 移除不必要的原始欄位，只保留特徵
        keep_columns = ['timestamp'] + feature_names
        features_df = features_df[keep_columns]
        
        self.logger.info(f"特徵提取完成 - 總共 {len(feature_names)} 個特徵")
        
        return features_df, feature_names
    
    def extract_price_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取通用價格特徵 (Stage 1)
        
        這些特徵不依賴策略參數
        """
        feature_names = []
        
        # 1. 價格變化百分比
        df['price_change_pct'] = (df['close'] / df['open'] - 1)
        feature_names.append('price_change_pct')
        
        # 2. 高低價範圍百分比
        df['high_low_range_pct'] = (df['high'] - df['low']) / df['open']
        feature_names.append('high_low_range_pct')
        
        # 3. 收盤價在高低範圍的位置
        df['close_position_in_range'] = (
            (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        )
        feature_names.append('close_position_in_range')
        
        # 4. 5期價格波動率
        df['price_volatility_5'] = (
            df['close'].rolling(5).std() / (df['close'].rolling(5).mean() + 1e-10)
        )
        feature_names.append('price_volatility_5')
        
        # 5. 3期價格動量
        df['price_momentum_3'] = df['close'] - df['close'].shift(3)
        feature_names.append('price_momentum_3')
        
        # 6. 上影線百分比
        df['upper_shadow_pct'] = (
            (df['high'] - df[['open', 'close']].max(axis=1)) / df['open']
        )
        feature_names.append('upper_shadow_pct')
        
        # 7. 下影線百分比
        df['lower_shadow_pct'] = (
            (df[['open', 'close']].min(axis=1) - df['low']) / df['open']
        )
        feature_names.append('lower_shadow_pct')
        
        # 8. K線實體百分比
        df['body_pct'] = abs(df['close'] - df['open']) / df['open']
        feature_names.append('body_pct')
        
        return df, feature_names
    
    def extract_volume_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取通用成交量特徵 (Stage 2)
        
        這些特徵不依賴策略參數
        """
        feature_names = []
        
        # 1. 成交量變化百分比
        df['volume_change_pct'] = df['volume'] / (df['volume'].shift(1) + 1e-10) - 1
        feature_names.append('volume_change_pct')
        
        # 2. 成交量與5期均量比
        df['volume_ma_ratio_5'] = (
            df['volume'] / (df['volume'].rolling(5).mean() + 1e-10)
        )
        feature_names.append('volume_ma_ratio_5')
        
        # 3. 主動買入比例 (taker_ratio)
        # 注意: taker_ratio 已經在 HDF5 中計算好了
        df['taker_buy_ratio'] = df['taker_ratio']
        feature_names.append('taker_buy_ratio')
        
        # 4. 主動買入金額比例
        # 計算方式: taker_buy_quote_volume / quote_volume
        # 估算: taker_buy_volume * close / quote_volume
        df['taker_buy_value_ratio'] = (
            (df['taker_buy_volume'] * df['close']) / (df['quote_volume'] + 1e-10)
        )
        feature_names.append('taker_buy_value_ratio')
        
        # 5. 5期量價相關性
        df['volume_price_correlation_5'] = (
            df['volume'].rolling(5).corr(df['close'])
        )
        feature_names.append('volume_price_correlation_5')
        
        # 6. 異常成交量標記
        volume_ma_20 = df['volume'].rolling(20).mean()
        df['abnormal_volume_flag'] = (df['volume'] > 2 * volume_ma_20).astype(float)
        feature_names.append('abnormal_volume_flag')
        
        return df, feature_names
    
    def extract_ema_features(
        self, 
        df: pd.DataFrame, 
        ema_params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取 EMA 策略特徵 (Stage 3 - 參數化)
        
        根據 Optuna 優化的 EMA 參數動態生成特徵
        支持從任意數據源計算 EMA（與 Optuna 設計一致）
        使用動態命名系統確保特徵唯一性
        
        Args:
            df: K線數據
            ema_params: {'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
            data_source: 數據源 (close/open/high/low/volume/taker_buy_volume/taker_ratio)
                        默認 'close'，但應從 StrategyParams 傳入 Optuna 優化的結果
        """
        feature_names = []
        
        short = ema_params['ema_short']
        mid = ema_params['ema_mid']
        long = ema_params['ema_long']
        volume_threshold = ema_params['volume_threshold']
        
        # 驗證數據源存在
        if data_source not in df.columns:
            raise ValueError(f"數據源 '{data_source}' 不存在於 DataFrame 中。可用欄位: {df.columns.tolist()}")
        
        # 1-3. 計算三條 EMA（使用指定的數據源）
        self.logger.info(f"使用數據源 '{data_source}' 計算 EMA 特徵")
        
        # 使用動態命名系統生成所有特徵名稱
        feature_name_mapping = FeatureNamingConfig.make_ema_feature_names(data_source, ema_params)
        
        # 1. EMA short 值
        ema_short_col = feature_name_mapping['ema_short']
        df[ema_short_col] = df[data_source].ewm(span=short, adjust=False).mean()
        feature_names.append(ema_short_col)
        
        # 2. EMA mid 值
        ema_mid_col = feature_name_mapping['ema_mid']
        df[ema_mid_col] = df[data_source].ewm(span=mid, adjust=False).mean()
        feature_names.append(ema_mid_col)
        
        # 3. EMA long 值
        ema_long_col = feature_name_mapping['ema_long']
        df[ema_long_col] = df[data_source].ewm(span=long, adjust=False).mean()
        feature_names.append(ema_long_col)
        
        # 4. EMA(short) 與 EMA(mid) 距離
        ema_dist_short_mid_col = feature_name_mapping['ema_distance_short_mid']
        df[ema_dist_short_mid_col] = (
            (df[ema_short_col] - df[ema_mid_col]) / (df[ema_mid_col] + 1e-10)
        )
        feature_names.append(ema_dist_short_mid_col)
        
        # 5. EMA(mid) 與 EMA(long) 距離
        ema_dist_mid_long_col = feature_name_mapping['ema_distance_mid_long']
        df[ema_dist_mid_long_col] = (
            (df[ema_mid_col] - df[ema_long_col]) / (df[ema_long_col] + 1e-10)
        )
        feature_names.append(ema_dist_mid_long_col)
        
        # 6. EMA 趨勢對齊（使用 data_source 作為前綴）
        ema_trend_col = f"{data_source}_ema_trend_aligned"
        df[ema_trend_col] = (
            (df[ema_short_col] > df[ema_mid_col]) & 
            (df[ema_mid_col] > df[ema_long_col])
        ).astype(float)
        feature_names.append(ema_trend_col)
        
        # 7. EMA(short) 穿越 EMA(mid) 信號
        ema_cross_col = feature_name_mapping['ema_cross_signal']
        ema_short_above = (df[ema_short_col] > df[ema_mid_col]).astype(bool)
        ema_short_above_prev = ema_short_above.shift(1).fillna(False)
        df[ema_cross_col] = (
            ema_short_above & (~ema_short_above_prev)
        ).astype(float)
        feature_names.append(ema_cross_col)
        
        # 8. Volume Threshold 特徵 - 成交量激增
        volume_spike_col = feature_name_mapping['volume_spike']
        df[volume_spike_col] = (
            df['taker_ratio'] > volume_threshold
        ).astype(float)
        feature_names.append(volume_spike_col)
        
        # 9. 主動買入比例與閾值距離
        taker_dist_col = feature_name_mapping['taker_ratio_distance']
        df[taker_dist_col] = (
            df['taker_ratio'] - volume_threshold
        )
        feature_names.append(taker_dist_col)
        
        return df, feature_names
    
    def extract_signal_features(
        self,
        df: pd.DataFrame,
        strategy_params: StrategyParams
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取信號組合特徵 (Stage 4)
        
        基於策略邏輯生成的組合特徵
        使用動態命名系統確保與 extract_ema_features 一致
        """
        feature_names = []
        
        if strategy_params.strategy_type == 'ema_three_line':
            params = strategy_params.params
            data_source = strategy_params.data_source
            short = params['ema_short']
            mid = params['ema_mid']
            volume_threshold = params['volume_threshold']
            
            # 獲取特徵名稱映射（與 extract_ema_features 保持一致）
            feature_name_mapping = FeatureNamingConfig.make_ema_feature_names(data_source, params)
            
            # 1. 進場信號分數 (組合 EMA 趨勢 + 成交量條件)
            # 滿足 3 個條件得 1 分，滿足 2 個得 0.66 分，以此類推
            ema_trend_col = f"{data_source}_ema_trend_aligned"
            condition1 = df[ema_trend_col]  # EMA 順勢排列
            condition2 = df[feature_name_mapping['volume_spike']]  # 成交量激增
            condition3 = df[feature_name_mapping['ema_cross_signal']]  # 黃金交叉
            
            entry_score_col = f"{data_source}_ema_entry_signal_score"
            df[entry_score_col] = (condition1 + condition2 + condition3) / 3.0
            feature_names.append(entry_score_col)
            
            # 2. 5期趨勢一致性 (連續5期都是EMA順勢)
            trend_consistency_col = f"{data_source}_ema_trend_consistency_5"
            df[trend_consistency_col] = (
                df[ema_trend_col].rolling(5).sum() / 5.0
            )
            feature_names.append(trend_consistency_col)
            
            # 3. 信號強度 (多個條件的加權)
            # 權重: EMA距離(40%) + 成交量(30%) + 趨勢一致性(30%)
            ema_dist_normalized = df[feature_name_mapping['ema_distance_short_mid']].clip(lower=0, upper=0.1) / 0.1
            volume_normalized = df[feature_name_mapping['taker_ratio_distance']].clip(lower=0, upper=0.4) / 0.4
            trend_normalized = df[trend_consistency_col]
            
            signal_strength_col = f"{data_source}_ema_signal_strength"
            df[signal_strength_col] = (
                0.4 * ema_dist_normalized +
                0.3 * volume_normalized +
                0.3 * trend_normalized
            )
            feature_names.append(signal_strength_col)
        
        return df, feature_names
    
    def _has_signal_features(self, strategy_type: str) -> bool:
        """
        檢查策略是否支援信號組合特徵
        
        目前只有 ema_three_line 支援信號特徵
        未來可擴展到其他策略
        """
        return strategy_type in ['ema_three_line']
    
    def _validate_input_data(self, df: pd.DataFrame) -> None:
        """驗證輸入數據完整性"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 
                          'volume', 'taker_buy_volume', 'taker_ratio', 'quote_volume']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必要欄位: {missing_columns}")
        
        if len(df) == 0:
            raise ValueError("數據為空")
        
        # 檢查是否有 NaN
        nan_columns = df[required_columns].columns[df[required_columns].isna().any()].tolist()
        if nan_columns:
            self.logger.warning(f"發現 NaN 值的欄位: {nan_columns}")
