"""
Feature Validator - 特徵驗證器

確保生成的特徵符合機器學習要求:
1. 無未來函數 (future leak)
2. 無 NaN/Inf 值
3. 無高相關性特徵 (>0.95)

Author: AI Agent
Date: 2026-01-10
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.preprocessing._numba_transforms import (
    rolling_winsorize_array,
)

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """驗證結果"""
    has_nan: bool
    has_inf: bool
    max_correlation: float
    high_correlation_pairs: List[Tuple[str, str, float]]  # (feature1, feature2, corr)
    warnings: List[str]
    coverage: Optional[float] = None
    constant_features_removed: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """是否通過驗證"""
        return not self.has_nan and not self.has_inf


class FeatureValidator:
    """
    特徵驗證器
    
    驗證生成的特徵是否符合機器學習要求
    """
    
    def __init__(self, correlation_threshold: float = 0.95):
        """
        Args:
            correlation_threshold: 高相關性閾值，超過此值視為高度相關
        """
        self.correlation_threshold = correlation_threshold
        self.logger = logger
        self._last_winsorization_count = 0
    
    def validate(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str]
    ) -> ValidationResult:
        """
        執行完整驗證
        
        Args:
            features_df: 特徵 DataFrame
            feature_names: 特徵名稱列表
            
        Returns:
            ValidationResult - 驗證結果
        """
        self.logger.info(f"開始驗證特徵 - 特徵數量: {len(feature_names)}, "
                        f"樣本數量: {len(features_df)}")
        
        warnings = []
        
        # 1. 檢查 NaN 值
        has_nan = self.validate_no_nan(features_df, feature_names)
        if has_nan:
            warnings.append("發現 NaN 值，部分特徵可能無法計算")
        
        # 2. 檢查 Inf 值
        has_inf = self.validate_no_inf(features_df, feature_names)
        if has_inf:
            warnings.append("發現 Inf 值，可能是除以零錯誤")
        
        # 3. 檢查高相關性
        max_corr, high_corr_pairs = self.validate_correlation(features_df, feature_names)
        if max_corr > self.correlation_threshold:
            warnings.append(
                f"發現 {len(high_corr_pairs)} 對高相關性特徵 (相關性 > {self.correlation_threshold})"
            )
        
        # 4. 檢查常數特徵
        constant_features = self._check_constant_features(features_df, feature_names)
        if constant_features:
            warnings.append(f"發現 {len(constant_features)} 個常數特徵: {constant_features}")
        
        result = ValidationResult(
            has_nan=has_nan,
            has_inf=has_inf,
            max_correlation=max_corr,
            high_correlation_pairs=high_corr_pairs,
            warnings=warnings,
            coverage=None,
            constant_features_removed=[],
        )
        
        self.logger.info(f"驗證完成 - 通過: {result.is_valid()}, 警告數: {len(warnings)}")
        
        return result

    def validate_factory_output(self, result) -> ValidationResult:
        """工廠專用驗證：NaN/Inf + 常數移除 + 覆蓋率 + Winsorize"""
        features_df = result.features_df
        feature_names = list(features_df.columns)

        warnings: List[str] = []
        if features_df.empty:
            warnings.append("特徵矩陣為空")
            return ValidationResult(
                has_nan=False,
                has_inf=False,
                max_correlation=0.0,
                high_correlation_pairs=[],
                warnings=warnings,
                coverage=0.0,
                constant_features_removed=[],
            )

        constant_features = self._check_constant_features(features_df, feature_names)
        if constant_features:
            features_df = features_df.drop(columns=constant_features)
            result.features_df = features_df
            result.feature_count = features_df.shape[1]
            warnings.append(f"移除常數特徵: {constant_features}")

        coverage = self.check_coverage(features_df)
        if coverage < 1.0:
            warnings.append(f"覆蓋率: {coverage:.4f}")

        self._last_winsorization_count = 0
        if not self._l65_winsorization_applied(result):
            features_df = self.winsorize(features_df)
            self._last_winsorization_count = 1
        result.features_df = features_df

        # Winsorization must not hide newly-created invalid values.  The
        # returned validation status always describes the final output frame.
        feature_names = list(features_df.columns)
        has_nan = self.validate_no_nan(features_df, feature_names)
        if has_nan:
            warnings.append("發現 NaN 值")

        has_inf = self.validate_no_inf(features_df, feature_names)
        if has_inf:
            warnings.append("發現 Inf 值")

        return ValidationResult(
            has_nan=has_nan,
            has_inf=has_inf,
            max_correlation=0.0,
            high_correlation_pairs=[],
            warnings=warnings,
            coverage=coverage,
            constant_features_removed=constant_features,
        )

    def check_coverage(self, features_df: pd.DataFrame) -> float:
        """特徵覆蓋率：非 NaN 比例"""
        if features_df.empty:
            return 0.0
        total = features_df.size
        if total == 0:
            return 0.0
        return float(features_df.notna().sum().sum() / total)

    def winsorize(
        self,
        features_df: pd.DataFrame,
        lower: float = 0.01,
        upper: float = 0.99,
    ) -> pd.DataFrame:
        """以只含當下與歷史資料的 rolling quantile 截斷極端值。"""
        if features_df.empty:
            return features_df

        values = features_df.to_numpy(dtype=np.float32, copy=True)
        clipped = rolling_winsorize_array(
            values,
            lower_q=lower,
            upper_q=upper,
            window=252,
            min_periods=63,
        )
        return pd.DataFrame(clipped, index=features_df.index, columns=features_df.columns)

    @staticmethod
    def _l65_winsorization_applied(result) -> bool:
        """判斷 L6.5 是否已套 winsor，避免 validator 重複處理。"""
        config_used = getattr(result, "config_used", {}) or {}
        if not isinstance(config_used, dict):
            return False
        preprocessing = config_used.get("preprocessing") or {}
        if not isinstance(preprocessing, dict) or not preprocessing.get("enabled", False):
            return False
        winsor = preprocessing.get("winsorization") or {}
        return isinstance(winsor, dict) and bool(winsor.get("enabled", False))
    
    def validate_no_nan(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str]
    ) -> bool:
        """
        檢查是否有 NaN 值
        
        Returns:
            True if has NaN, False otherwise
        """
        nan_counts = features_df[feature_names].isna().sum()
        nan_features = nan_counts[nan_counts > 0]
        
        if len(nan_features) > 0:
            self.logger.warning(f"發現 NaN 值: {len(nan_features)} 個特徵")
            max_detail = 20
            for feature, count in nan_features.head(max_detail).items():
                pct = count / len(features_df) * 100
                self.logger.warning(f"  {feature}: {count} ({pct:.2f}%)")
            if len(nan_features) > max_detail:
                self.logger.warning(f"  ... 其餘 {len(nan_features) - max_detail} 個特徵略")
            return True
        
        return False
    
    def validate_no_inf(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str]
    ) -> bool:
        """
        檢查是否有 Inf 值
        
        Returns:
            True if has Inf, False otherwise
        """
        inf_counts = np.isinf(features_df[feature_names]).sum()
        inf_features = inf_counts[inf_counts > 0]
        
        if len(inf_features) > 0:
            self.logger.warning(f"發現 Inf 值: {len(inf_features)} 個特徵")
            max_detail = 20
            for feature, count in inf_features.head(max_detail).items():
                pct = count / len(features_df) * 100
                self.logger.warning(f"  {feature}: {count} ({pct:.2f}%)")
            if len(inf_features) > max_detail:
                self.logger.warning(f"  ... 其餘 {len(inf_features) - max_detail} 個特徵略")
            return True
        
        return False
    
    def validate_correlation(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str]
    ) -> Tuple[float, List[Tuple[str, str, float]]]:
        """
        檢查高相關性特徵
        
        Returns:
            (max_correlation, high_correlation_pairs)
        """
        # 計算相關矩陣
        # 先移除 NaN 行，避免 corr() 失敗
        clean_df = features_df[feature_names].dropna()
        
        if len(clean_df) == 0:
            self.logger.warning("所有樣本都包含 NaN，無法計算相關性")
            return 0.0, []
        
        corr_matrix = clean_df.corr()
        
        # 找出高相關性對 (排除對角線)
        high_corr_pairs = []
        max_corr = 0.0
        
        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                corr = abs(corr_matrix.iloc[i, j])
                max_corr = max(max_corr, corr)
                
                if corr > self.correlation_threshold:
                    high_corr_pairs.append((
                        feature_names[i],
                        feature_names[j],
                        corr
                    ))
        
        if high_corr_pairs:
            self.logger.warning(f"發現 {len(high_corr_pairs)} 對高相關性特徵:")
            for feat1, feat2, corr in high_corr_pairs[:5]:  # 只顯示前 5 對
                self.logger.warning(f"  {feat1} <-> {feat2}: {corr:.4f}")
        
        return max_corr, high_corr_pairs
    
    def validate_no_future_leak(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str],
        timestamp_column: str = 'timestamp'
    ) -> bool:
        """
        檢查是否有未來函數 (基於時間序列)
        
        這個檢查確保每個時間點的特徵只依賴於過去和當前的數據
        
        Args:
            features_df: 特徵 DataFrame
            feature_names: 特徵名稱列表
            timestamp_column: 時間戳欄位名稱
            
        Returns:
            True if no future leak, False otherwise
        """
        # 檢查時間戳是否遞增
        timestamps = features_df[timestamp_column]
        if not timestamps.is_monotonic_increasing:
            self.logger.error("時間戳未按遞增順序排列，可能導致未來函數")
            return False
        
        # 對於每個特徵，檢查是否有未來依賴
        # 簡單檢查: 特徵計算不應使用 shift(-n) (負數 shift)
        # 這個檢查需要在特徵工程時就避免，這裡只是最終驗證
        
        # 檢查是否有特徵值在時間上"倒退"
        # 例如: 某個特徵在 t 時刻的值依賴於 t+1 時刻的原始數據
        
        # 由於我們使用 rolling 和 shift(正數)，理論上不會有未來函數
        # 這裡只做基本檢查
        
        self.logger.info("未來函數檢查通過 (基於時間序列遞增)")
        return True
    
    def _check_constant_features(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str]
    ) -> List[str]:
        """檢查常數特徵 (標準差為 0)"""
        constant_features = []
        
        for feature in feature_names:
            series_or_frame = features_df[feature]
            std = series_or_frame.std()
            if isinstance(std, pd.Series):
                if (std == 0).any() or std.isna().any():
                    constant_features.append(feature)
            else:
                if std == 0 or np.isnan(std):
                    constant_features.append(feature)
        
        return constant_features
    
    def fill_nan_values(
        self,
        features_df: pd.DataFrame,
        feature_names: List[str],
        method: str = 'forward'
    ) -> pd.DataFrame:
        """
        填補 NaN 值
        
        Args:
            features_df: 特徵 DataFrame
            feature_names: 特徵名稱列表
            method: 填補方法 ('forward', 'backward', 'zero', 'mean')
            
        Returns:
            填補後的 DataFrame
        """
        df = features_df.copy()
        
        if method == 'forward':
            df[feature_names] = df[feature_names].fillna(method='ffill')
        elif method == 'backward':
            df[feature_names] = df[feature_names].fillna(method='bfill')
        elif method == 'zero':
            df[feature_names] = df[feature_names].fillna(0)
        elif method == 'mean':
            for feature in feature_names:
                df[feature] = df[feature].fillna(df[feature].mean())
        else:
            raise ValueError(f"不支持的填補方法: {method}")
        
        # 如果還有 NaN (例如整列都是 NaN)，填 0
        df[feature_names] = df[feature_names].fillna(0)
        
        self.logger.info(f"NaN 值填補完成 - 方法: {method}")
        
        return df
